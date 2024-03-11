import numpy as np
import bentoml
from bentoml.io import NumpyNdarray

svc = bentoml.Service("online_ts")
online_model = bentoml.mlflow.load_model("online_ts:latest")

@svc.api(input=NumpyNdarray(), output=NumpyNdarray())
def predict(input_series: np.ndarray) -> np.ndarray:
    result = online_model.predict(input_series)
    return result