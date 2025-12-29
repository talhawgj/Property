from typing import Optional
from sqlmodel import SQLModel, Field
from geoalchemy2 import Geometry
from sqlalchemy import Column

class Wetlands(SQLModel, table=True):
    __tablename__ = "wetlands"

    gid: Optional[int] = Field(default=None, primary_key=True)
    attribute: Optional[str] = None
    wetland_type: Optional[str] = Field(default=None, index=True)
    acres: Optional[float] = None
    nwi_id: Optional[str] = None
    shape_length: Optional[float] = None
    shape_area: Optional[float] = None
    geom: Optional[str] = Field(
        sa_column=Column(Geometry("MULTIPOLYGON", srid=4326))
    )
