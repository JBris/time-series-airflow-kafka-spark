from pydantic import BaseModel

class ExperimentModel(BaseModel):
    """
    The experiment data model.

    Args:
        BaseModel (_type_): 
            The Base model class.
    """
    name: str
    tracking_uri: str

class InputDataModel(BaseModel):
    """
    The input data model.

    Args:
        BaseModel (_type_): 
            The Base model class.
    """
    name: str
    base_path: str
    filename: str
    index_col: str
    delay: float
    period: str
    
class MetricsModel(BaseModel):
    """
    The metrics data model.

    Args:
        BaseModel (_type_): 
            The Base model class.
    """
    metrics: dict

class TimeSeriesModel(BaseModel):
    """
    The time series data model.

    Args:
        BaseModel (_type_): 
            The Base model class.
    """
    name: str
    module: str
    training_time: int
    args: list
    kwargs: dict