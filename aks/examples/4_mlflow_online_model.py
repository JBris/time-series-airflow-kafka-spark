import bentoml
from pydoc import locate
import hydra
from hydra.utils import instantiate
import mlflow
from mlflow.models import infer_signature
import numpy as np
from omegaconf import DictConfig
import os 
import os.path as osp
import pandas as pd
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json
from pyspark.sql.types import StringType, StructField, StructType, FloatType

class OnlineModel(mlflow.pyfunc.PythonModel):
    def __init__(self):
        self.model = None
        
    def load_context(self, context):
        import pickle

        model_file = context.artifacts["model"]
        with open(model_file, 'rb') as f:
            self.model = pickle.load(f)

    def predict(self, context, model_input):
        import numpy as np

        if self.model is None:
            raise ValueError(
                "The model has not been loaded."
            )
        
        forecast = np.array(
            self.model.forecast(horizon=1) 
        )
        for y in model_input:
            self.model.learn_one(y)
            
        return forecast
    
@hydra.main(version_base=None, config_path="../../conf", config_name="config")
def main(config: DictConfig):
    EXPERIMENT_CONFIG = instantiate(config["experiment"])
    INPUT_DATA_CONFIG = instantiate(config["data"])
    TIME_SERIES_CONFIG = instantiate(config["time_series"])
    METRICS_CONFIG = instantiate(config["metrics"])

    mlflow.set_tracking_uri(EXPERIMENT_CONFIG.tracking_uri)
    experiment_name = EXPERIMENT_CONFIG.name
    existing_exp = mlflow.get_experiment_by_name(experiment_name)
    if not existing_exp:
        mlflow.create_experiment(experiment_name)
    mlflow.set_experiment(experiment_name)
    mlflow.set_tag("task", "ts_airflow_kafka_spark")

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
        .config("spark.streaming.stopGracefullyOnShutdown", "true")
        .master(os.environ["SPARK_MASTER_URL"])
        .getOrCreate()
    )

    json_schema = (StructType([
        StructField('index', StringType(), True), 
        StructField('value', FloatType(), True)
    ]))

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

    json_df = df.selectExpr("cast(value as string) as value")
    json_expanded_df = (
            json_df
            .withColumn("value", from_json(json_df["value"], json_schema))
            .select("value.*") 
    )
    
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

    try:
        query = (
            json_expanded_df
            .writeStream
            .foreachBatch(process_batch)
            .start()
        )
        query.awaitTermination(TIME_SERIES_CONFIG.training_time)
    except:
        pass

    query.stop()
    spark.stop()

    sig = np.repeat([1.0], 3)
    signature = infer_signature(sig, sig)
    
    model_name = f"online_{TIME_SERIES_CONFIG.name}"
    online_model = OnlineModel()

    import pickle
    fname = osp.join("outdir", f"{model_name}.pkl")
    with open(fname, 'wb') as f:
        pickle.dump(model, f)

    logged_model = mlflow.pyfunc.log_model(
        python_model = online_model, 
        artifact_path = model_name, 
        artifacts={"model": fname},
        signature = signature
    )
    model_uri = logged_model.model_uri
    mlflow.register_model(model_uri, model_name)

    bentoml.mlflow.import_model(
        model_name, 
        model_uri,
        labels=mlflow.active_run().data.tags,
        metadata={
            "metrics": mlflow.active_run().data.metrics,
            "params": mlflow.active_run().data.params,
        }
    )

    loaded_model = mlflow.pyfunc.load_model(model_uri)
    preds = loaded_model.predict(
        np.array([100.0, 110.0])
    )
    print(preds)

    mlflow.end_run()

if __name__ == "__main__":
    main()
    