from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from db import get_session
from models import (
    PropertyCreate, PropertyUpdate, PropertyResponse, 
    PropertySearchResponse, PropertyStatsResponse
)
from services import PropertyCatalogueService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/catalogue", tags=["Property Catalogue"])
service = PropertyCatalogueService()

@router.post("/properties", response_model=Dict[str, str])
async def create_property(
    property_data: PropertyCreate,
    db: AsyncSession = Depends(get_session)
):
    try:
        property_id = await service.create_property(db, property_data)
        return {
            "property_id": property_id,
            "message": "Property created and saved successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Create failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/properties", response_model=PropertySearchResponse)
async def list_properties(
    limit: int = Query(500, ge=1, le=10000, description="Maximum results to return (default 500)"),
    offset: int = Query(0, ge=0, description="Number of results to skip for pagination"),
    desc: bool = Query(True, description="Descending order if True"),
    db: AsyncSession = Depends(get_session)
):
    """List all properties with pagination and ordering."""
    try:
        result = await service.list_properties(
            db=db, limit=limit, offset=offset, desc_order=desc
        )
        return result
    except Exception as e:
        logger.error(f"Error listing properties: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
 
@router.get("/search", response_model=PropertySearchResponse)
async def search_properties(
    status: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    min_acres: Optional[float] = Query(None),
    max_acres: Optional[float] = Query(None),
    county: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = 0,
    db: AsyncSession = Depends(get_session)
):
    return await service.search_properties(
        db, status, min_price, max_price, min_acres, max_acres, county, limit, offset
    )

@router.get("/properties/{property_id}", response_model=PropertyResponse)
async def get_property(property_id: str, db: AsyncSession = Depends(get_session)):
    result = await service.get_property(db, property_id)
    if not result:
        raise HTTPException(status_code=404, detail="Property not found")
    return result

@router.put("/properties/{property_id}", response_model=PropertyResponse)
async def update_property(
    property_id: str, 
    update_data: PropertyUpdate, 
    db: AsyncSession = Depends(get_session)
):
    result = await service.update_property(db, property_id, update_data)
    if not result:
        raise HTTPException(status_code=404, detail="Property not found")
    return result

@router.delete("/properties/{property_id}")
async def delete_property(property_id: str, db: AsyncSession = Depends(get_session)):
    success = await service.delete_property(db, property_id)
    if not success:
        raise HTTPException(status_code=404, detail="Property not found")
    return {"message": "Deleted successfully"}

@router.get("/statistics", response_model=PropertyStatsResponse)
async def get_statistics(db: AsyncSession = Depends(get_session)):
    return await service.get_statistics(db)