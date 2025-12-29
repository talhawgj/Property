from typing import Optional
from geoalchemy2 import Geometry
from sqlalchemy import Column
from sqlmodel import Field, SQLModel


class TexasFloodHazard(SQLModel, table=True):
    __tablename__ = "tx_fld_haz"

    gid: Optional[int] = Field(default=None, primary_key=True)
    dfirm_id: Optional[str] = None
    version_id: Optional[str] = None
    fld_ar_id: Optional[str] = None
    study_typ: Optional[str] = None
    fld_zone: Optional[str] = None
    zone_subty: Optional[str] = None
    sfha_tf: Optional[str] = None
    static_bfe: Optional[str] = None
    v_datum: Optional[str] = None
    depth: Optional[str] = None
    len_unit: Optional[str] = None
    velocity: Optional[str] = None
    vel_unit: Optional[str] = None
    ar_revert: Optional[str] = None
    ar_subtrv: Optional[str] = None
    bfe_revert: Optional[str] = None
    dep_revert: Optional[str] = None
    dual_zone: Optional[str] = None
    source_cit: Optional[str] = None
    grid: Optional[str] = None
    shape_length: Optional[float] = None
    shape_area: Optional[float] = None
    geom: Optional[str] = Field(
        sa_column=Column(Geometry("MULTIPOLYGON", srid=4326))
    )
