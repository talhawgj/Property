from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from typing import Any, Dict, Optional
from sqlmodel import SQLModel, Field
from geoalchemy2 import Geometry
from sqlalchemy import Column
from sqlalchemy.sql import func
class Parcel(SQLModel, table=True):
    __tablename__ = "parcels"

    gid: Optional[int] = Field(default=None, primary_key=True, index=True)
    prop_id: Optional[str] = Field(default=None, index=True)
    geo_id: Optional[str] = Field(default=None, index=True)
    owner_name: Optional[str] = None
    situs_addr: Optional[str] = None
    county: Optional[str] = None
    legal_area: Optional[str] = None
    geom: Optional[str] = Field(
        sa_column=Column(Geometry("MULTIPOLYGON", srid=4326))
    )




class AnalysisResult(SQLModel, table=True):
    __tablename__ = "analysis_results"

    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    parcel_gid: int = Field(
        sa_column=Column(
            Integer, 
            ForeignKey("parcels.gid", ondelete="CASCADE"), 
            unique=True, 
            nullable=False
        )
    )
    batch_id: Optional[str] = Field(default=None, index=True)
    processing_mode: str = Field(default="single")
    csv_source_data: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True)
    )
    result_data: Dict[str, Any] = Field(
        default={},
        sa_column=Column(JSONB, nullable=False)
    )
    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True), 
            server_default=func.now(), 
            onupdate=func.now()
        )
    )