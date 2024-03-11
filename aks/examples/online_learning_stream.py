from pydoc import locate
import hydra
from omegaconf import DictConfig
from hydra.utils import instantiate
import pandas as pd
from pyspark.sql import SparkSession
import os 
from pyspark.sql.functions import from_json
from pyspark.sql.types import StringType, StructField, StructType, FloatType

@hydra.main(version_base=None, config_path="../../conf", config_name="config")
def main(config: DictConfig):
    INPUT_DATA_CONFIG = instantiate(config["data"])
    TIME_SERIES_CONFIG = instantiate(config["time_series"])
    METRICS_CONFIG = instantiate(config["metrics"])

    spark = (
        SparkSession
        .builder
        .appName("AKS")
        .config("spark.shuffle.spill.compress", "true")
        .config("spark.shuffle.compress", "true")
        .config("spark.sql.shuffle.partitions", "3000")
        .config("spark.io.compression.lz4.blockSize", "16k")
        .config("spark.memory.offHeap.enabled","true")
        .config("spark.memory.offHeap.size","10g")
        .master(os.environ["SPARK_MASTER_URL"])
        .getOrCreate()
    )

    json_schema = (StructType([
        StructField('index', StringType(), True), 
        StructField('value', FloatType(), True)
    ]))

    try:
        df = (
            spark.readStream
                .format("kafka")
                .option("kafka.bootstrap.servers", os.environ["KAFKA_BOOTSTRAP_HOST"])
                .option("subscribe", INPUT_DATA_CONFIG.name)
                .option("startingOffsets", "latest")  
                .option("poll", "1000")  
                .load()
        )

        module = locate(TIME_SERIES_CONFIG.module)
        model = module(
            *TIME_SERIES_CONFIG.args, **TIME_SERIES_CONFIG.kwargs
        )
        metrics = {
            k: locate(v)() 
            for k, v in METRICS_CONFIG.metrics.items()
        }

        def process_batch(batch_list, batch_id):
            rows = batch_list.collect()
            if len(rows) == 0:
                return
            
            row_dicts = [ row.asDict() for row in rows ]
            df = pd.DataFrame.from_records(row_dicts, index="index")
            df.index = pd.to_datetime(df.index).to_period(INPUT_DATA_CONFIG.period)
            df.sort_index(inplace=True)
            
            for v in df.value:
                forecast = model.forecast(horizon=1)[0]
                model.learn_one(v)

                print(f"Actual: {v}")
                print(f"Predicted: {forecast}")
                for k, metric in metrics.items():
                    metric.update(v, forecast)
                    print(f"{k}: {metric.get()}")

        json_df = df.selectExpr("cast(value as string) as value")
        json_expanded_df = (
             json_df
             .withColumn("value", from_json(json_df["value"], json_schema))
             .select("value.*") 
        )
        
        query = (
            json_expanded_df 
            .writeStream 
            .foreachBatch(process_batch)
            .start()
        )

        query.awaitTermination()

    finally:
        spark.stop()

if __name__ == "__main__":
    main()
    