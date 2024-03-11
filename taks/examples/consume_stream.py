import hydra
from hydra.utils import instantiate
import json
from omegaconf import DictConfig
from kafka import KafkaConsumer
import os
import time

def on_send_success(record_metadata):
    print(record_metadata.topic)
    print(record_metadata.partition)
    print(record_metadata.offset)

@hydra.main(version_base=None, config_path="../../conf", config_name="config")
def main(config: DictConfig):
    INPUT_DATA_CONFIG = instantiate(config["data"])

    time.sleep(5)
    consumer = KafkaConsumer(
        bootstrap_servers=os.environ["KAFKA_BOOTSTRAP_HOST"],
        auto_offset_reset='earliest', 
        enable_auto_commit=False,
        value_deserializer=lambda m: json.loads(m.decode('ascii')),
    )

    consumer.subscribe(pattern=INPUT_DATA_CONFIG.name)

    try:
        while True:
            time.sleep(0.1)
            records = consumer.poll(100)
            if not records:
                continue
        
            record_list = []
            for _, consumer_records in records.items():
                for consumer_record in consumer_records:
                    record_list.append(consumer_record.value)

            print(record_list)    
    finally:
        consumer.close()

if __name__ == "__main__":
    main()
