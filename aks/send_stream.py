import hydra
from hydra.utils import instantiate
import json
from omegaconf import DictConfig
from kafka import KafkaProducer
import pandas as pd
import os
import os.path as osp
import time

def on_send_success(record_metadata):
    print(record_metadata.topic)
    print(record_metadata.partition)
    print(record_metadata.offset)

@hydra.main(version_base=None, config_path="../conf", config_name="config")
def main(config: DictConfig):
    INPUT_DATA_CONFIG = instantiate(config["data"])

    series = pd.read_csv(
        osp.join(INPUT_DATA_CONFIG.base_path, INPUT_DATA_CONFIG.filename),
        index_col = INPUT_DATA_CONFIG.index_col
    )

    time.sleep(5)
    producer = KafkaProducer(
        bootstrap_servers=os.environ["KAFKA_BOOTSTRAP_HOST"],
        value_serializer=lambda m: json.dumps(m).encode('ascii'),
        retries=5
    )

    while True:
        for i, v in series.T.items():
            time.sleep(INPUT_DATA_CONFIG.delay)
            producer.send(
                INPUT_DATA_CONFIG.name,
                {
                    'index': i,
                    'value': v.item()
                }
            ).add_callback(on_send_success)

        producer.flush()

if __name__ == "__main__":
    main()
