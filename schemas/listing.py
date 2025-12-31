from typing import Optional, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field, JSON
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB

class PropertyListing(SQLModel, table=True):
    __tablename__ = "property_listings"

    # Primary Keys & Links
    id: Optional[int] = Field(default=None, primary_key=True)
    gid: int = Field(index=True)  # Link to Parcel Geometry
    batch_id: Optional[str] = Field(default=None, index=True) # To track which file this came from

    # Searchable Columns (Indexed for speed)
    # We extract these common fields from the CSV for fast filtering
    status: str = Field(default="Active", index=True)
    price: Optional[float] = Field(default=None, index=True)
    acreage: Optional[float] = Field(default=None, index=True)
    county: Optional[str] = Field(default=None, index=True)
    
    # Metadata
    list_agent: Optional[str] = Field(default=None)
    owner_name: Optional[str] = Field(default=None)
    street_address: Optional[str] = Field(default=None)
    city: Optional[str] = Field(default=None)
    
    # Store the ENTIRE raw CSV row + Analysis Summary here
    # This ensures you never lose data even if it doesn't fit a column
    source_data: Dict[str, Any] = Field(default={}, sa_column=Column(JSONB))

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)