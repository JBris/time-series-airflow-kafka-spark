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
    