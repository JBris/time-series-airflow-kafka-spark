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

    spark = (
        SparkSession
        .builder
        .appName("TAKS")
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

        def process_batch(batch_list, batch_id):
            rows = batch_list.collect()
            if len(rows) == 0:
                return
            
            row_dicts = [ row.asDict() for row in rows ]
            df = pd.DataFrame.from_dict(row_dicts)
            print(df)

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
    