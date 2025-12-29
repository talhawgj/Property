from typing import List, Literal, Union, Optional
from pydantic import BaseModel

class WetlandAnalysisItem(BaseModel):
    wetland_type: str
    area_acres: float
    percentage: float
    wetland_geom: Optional[str]

class WetlandAnalysisResponse(BaseModel):
    intersects: Literal["Yes", "No"]
    wetland_analysis: List[WetlandAnalysisItem]
    cleared_area_acres: float
    cleared_percentage: float

class WetlandResponse(BaseModel):
    intersects: Literal["Yes", "No"]
    wetland_types_found: int

class PondAnalysisResponse(BaseModel):
    intersects: Literal["Yes", "No"]
    pond_area_acres: float
    pond_area_sqft: float
    pond_area_sqmeters: float
    pond_geoms: List[str]
    cleared_area_acres: float
    cleared_percentage: float
    unique_pond_count: int

class LakeAnalysisResponse(BaseModel):
    intersects: Literal["Yes", "No"]
    lake_area_acres: float
    lake_area_sqft: float
    lake_area_sqmeters: float
    lake_perimeter_ft: float
    lake_geoms: List[str]
    cleared_area_acres: float
    cleared_percentage: float

class StreamAnalysisResponse(BaseModel):
    intersects: str
    stream_length_ft: float
    stream_length_m: float
class ErrorResponse(BaseModel):
    error: str
