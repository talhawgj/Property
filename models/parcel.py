from pydantic import BaseModel
from typing import List, Optional

class ParcelResponse(BaseModel):
    gid: str
    prop_id: str
    geo_id: Optional[str] = None
    owner_name: Optional[str] = None
    situs_addr: Optional[str] = None
    county: Optional[str] = None
    acreage: Optional[str] = None  # Acreage from legal_area
    image_url: Optional[str] = None

    class Config:
        from_attributes = True


class AdjacencyCheckRequest(BaseModel):
    gids: List[int]
