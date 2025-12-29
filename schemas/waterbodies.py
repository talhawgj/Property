from typing import Optional
from sqlmodel import SQLModel, Field
from geoalchemy2 import Geometry
from sqlalchemy import Column

class WaterBodies(SQLModel, table=True):
    __tablename__ = "tx_water_bodies"

    gid: Optional[int] = Field(default=None, primary_key=True)
    body_typ: Optional[str] = Field(default=None, index=True)
    body_nm: Optional[str] = None
    acres: Optional[float] = None
    grid_op: Optional[str] = None
    create_dt: Optional[str] = None
    create_nm: Optional[str] = None
    edit_dt: Optional[str] = None
    edit_nm: Optional[str] = None
    shape_leng: Optional[float] = None
    shape_area: Optional[float] = None

    geom: Optional[str] = Field(
        sa_column=Column(Geometry("MULTIPOLYGONZM", srid=4326))
    )

class Pond(SQLModel, table=True):
    __tablename__ = "ponds"

    gid: Optional[int] = Field(default=None, primary_key=True)
    pond_type: Optional[str] = None
    geom: Optional[str] = Field(
        sa_column=Column(Geometry("MULTIPOLYGON", srid=4326))
    )


class Lake(SQLModel, table=True):
    __tablename__ = "texas_lakes_projected"

    gid: Optional[int] = Field(default=None, primary_key=True)
    geom: Optional[str] = Field(
        sa_column=Column(Geometry("MULTIPOLYGON", srid=4326))
    )

class Stream(SQLModel,table=True):
    """Represents streams in PostGIS."""
    __tablename__ = "stream"  

    gid : Optional[int] = Field(default=None, primary_key=True)
    geom :  Optional[str] = Field(
        sa_column=Column(Geometry("MULTIPOLYGONZM", srid=4326))
    )

class SeaOcean(SQLModel, table=True):
    __tablename__ = "texas_sea_ocean_project"

    gid: Optional[int] = Field(default=None, primary_key=True)
    geom: Optional[str] = Field(
        sa_column=Column(Geometry("MULTILINESTRING", srid=4326))
    )