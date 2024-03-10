import hydra
from omegaconf import DictConfig
from hydra.utils import instantiate
from pyspark.sql import SparkSession
from kafka import KafkaProducer
from kafka import KafkaConsumer
from kafka import TopicPartition
import os.path as osp

@hydra.main(version_base=None, config_path="../conf", config_name="config")
def main():
    
if __name__ == "__main__":
    main()
    # from sktime.datasets import load_airline

    # y = load_airline()
    # y.to_csv(
    #     osp.join("data", "airline.csv") 
    # )
    # print(y)

    # producer = KafkaProducer(bootstrap_servers='localhost:9092')

    # consumer = KafkaConsumer(
    #'foobar', bootstrap_servers='localhost:9092', consumer_timeout_ms=10000
    #)
    #consumer.subscribe(pattern='^foobar.*')
    
    # msg = next(consumer)

    # for _ in range(1):
    #     producer.send('foobar', b'some_message_bytes')



    # spark = SparkSession.builder.remote("sc://localhost:7077").getOrCreate()
    # spark.stop()

