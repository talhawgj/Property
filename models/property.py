from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class PropertyCreate(BaseModel):
    """
    Schema for creating a new property.
    Maps PascalCase Source JSON to internal fields.
    """
    model_config = ConfigDict(populate_by_name=True)
    gid: Optional[int] = Field(None, description="The Parcel GID")
    prop_id: Optional[str] = Field(None, alias="PropertyId")
    status: str = Field(default="activelisting", description="Property status")
    owner_name: Optional[str] = Field(None, alias="PartyOwner1NameFull")
    situs_addr: Optional[str] = Field(None, alias="StreetAddress")
    city: Optional[str] = Field(None, alias="City")
    state: Optional[str] = Field(None, alias="State")
    zip_code: Optional[Union[int, str]] = Field(None, alias="Zip")
    county: Optional[str] = Field(None, alias="County")
    latitude: Optional[float] = Field(None, alias="PropertyLatitude")
    longitude: Optional[float] = Field(None, alias="PropertyLongitude")
    seller_name: Optional[str] = Field(None, alias="AgentName")
    seller_email: Optional[str] = Field(None, alias="AgentEmail")
    seller_phone: Optional[str] = Field(None, alias="AgentPhone")
    seller_office: Optional[str] = Field(None, alias="AgentOffice")
    sell_price: Optional[float] = Field(None, alias="Price")
    price_per_acre: Optional[float] = Field(None, alias="PPA")
    acreage: Optional[float] = Field(None, alias="Acres")
    lot_size: Optional[int] = Field(None, alias="LotSize")
    property_type: Optional[str] = Field(None, alias="Type")
    beds: Optional[Union[float, str]] = Field(None, alias="Beds")
    baths: Optional[Union[float, str]] = Field(None, alias="Baths")
    built_in: Optional[int] = Field(None, alias="BuiltIn")
    days_on_market: Optional[int] = Field(None, alias="DaysOnMarket")
    description: Optional[str] = Field(None)
    images: Optional[Dict[str, Any]] = Field(default_factory=dict)
    analysis: Optional[Dict[str, Any]] = Field(None, description="Analysis results from /analyze/{gid}")
    user_name: Optional[str] = Field(None, description="User who added the property")


class PropertyUpdate(BaseModel):
    """Schema for updating property fields."""
    status: Optional[str] = None
    situs_addr: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[Union[int, str]] = None
    county: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    acreage: Optional[float] = None
    sell_price: Optional[float] = None
    price_per_acre: Optional[float] = None
    seller_name: Optional[str] = None
    seller_email: Optional[str] = None
    seller_phone: Optional[str] = None
    seller_office: Optional[str] = None
    owner_name: Optional[str] = None
    property_type: Optional[str] = None
    beds: Optional[Union[float, str]] = None
    baths: Optional[Union[float, str]] = None
    built_in: Optional[int] = None
    lot_size: Optional[int] = None
    days_on_market: Optional[int] = None
    description: Optional[str] = None
    images: Optional[Dict[str, Any]] = None
    analysis: Optional[Dict[str, Any]] = None
    source_data: Optional[Dict[str, Any]] = None


class PropertyResponse(BaseModel):
    """Unified response model merging Source and Analysis data."""
    property_id: Optional[str] = None  # mapped to GID
    gid: Optional[int] = None
    status: Optional[str] = None
    
    # Location
    situs_addr: Optional[str] = None
    city: Optional[str] = None
    county: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[Union[int, str]] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    # Details
    acreage: Optional[float] = None
    sell_price: Optional[float] = None
    price_per_acre: Optional[float] = None
    seller_name: Optional[str] = None
    seller_email: Optional[str] = None
    seller_phone: Optional[str] = None
    seller_office: Optional[str] = None
    owner_name: Optional[str] = None
    property_type: Optional[str] = None
    beds: Optional[Union[float, str]] = None
    baths: Optional[Union[float, str]] = None
    built_in: Optional[int] = None
    lot_size: Optional[int] = None
    days_on_market: Optional[int] = None
    description: Optional[str] = None
    
    # Data
    images: Optional[Dict[str, Any]] = None
    analysis: Optional[Dict[str, Any]] = None  # The full analysis result
    source_data: Optional[Dict[str, Any]] = None  # The full source CSV data
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PropertySearchResponse(BaseModel):
    properties: List[PropertyResponse]
    total: int
    limit: int
    offset: int
    has_more: bool


class PropertyStatsResponse(BaseModel):
    total_properties: int
    active_properties: int
    total_acres: float
    average_price: float