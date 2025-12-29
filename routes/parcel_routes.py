import base64
import json
import logging
import math
from typing import List, Optional, Tuple
from fastapi import APIRouter, Depends, HTTPException, Query
from boto3.dynamodb.conditions import Key, Attr
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone as dt_timezone
from db import get_session
from services import parcel_service as search_parcel
from models import ParcelResponse, AdjacencyCheckRequest

logger = logging.getLogger(__name__)
search_router = APIRouter(prefix="/search", tags=["Search"])


@search_router.get("/parcel", response_model=List[ParcelResponse])
async def search_parcel_by_id(
    prop_id: Optional[str] = None,
    county: Optional[str] = None,
    db_sess: AsyncSession = Depends(get_session),
):
    try:
        results = await search_parcel.get_by_filters(db_sess, prop_id, county)
        return results
    except Exception as e:
        logger.error(f"Error searching parcels: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@search_router.get("/parcel/coordinates", response_model=List[ParcelResponse])
async def search_parcel_by_coordinates(
    latitude: float = Query(..., description="Latitude in decimal degrees"),
    longitude: float = Query(..., description="Longitude in decimal degrees"),
    db_sess: AsyncSession = Depends(get_session),
):
    try:
        results = await search_parcel.get_by_coordinates(db_sess, latitude, longitude)
        return results
    except Exception as e:
        logger.error(f"Error searching parcels by coordinates: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@search_router.post("/adjacency")
async def check_adjacency(
    request: AdjacencyCheckRequest,
    db_sess: AsyncSession = Depends(get_session),
):
    try:
        result = await search_parcel.check_adjacency(db_sess, request.gids)
        return result
    except Exception as e:
        logger.error(f"Error checking adjacency: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@search_router.get("/parcel/owner", response_model=List[ParcelResponse])
async def search_parcel_by_owner(
    owner_name: str,
    county: Optional[str] = None,
    db_sess: AsyncSession = Depends(get_session),
):
    try:
        results = await search_parcel.get_by_owner_name(db_sess, owner_name, county)
        return results
    except Exception as e:
        logger.error(f"Error searching parcels by owner: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@search_router.get("/parcel/propid")
async def search_parcel_by_propid(
    prop_id: str,
    county: Optional[str] = None,
    db_sess: AsyncSession = Depends(get_session),
):
    try:
        results = await search_parcel.get_by_filters(db_sess, prop_id, county)
        return results
    except Exception as e:
        logger.error(f"Error searching parcels by property ID: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# @search_router.get("/parcel/dynamo", summary="List Analysis Results")
# async def get_parcels_data_dynamo(
#     page_size: int = Query(24, ge=1, le=200),
#     order_by: str = Query("updated_at"),
#     order_dir: str = Query("desc", pattern="^(?i)(asc|desc)$"),
#     page_token: Optional[str] = None,
# ):
#     """
#     List analysis results from DynamoDB.
#     Note: Standard DynamoDB Scan does not support efficient arbitrary sorting/pagination.
#     This uses the service's list_items which performs a Scan + Sort (suitable for smaller datasets).
#     """
#     try:
#         # Use the existing list_items method which handles scanning and sorting
#         # For production with large datasets, you should add GSIs for sorting fields.
#         items = dynamo_service.list_items(
#             limit=page_size, 
#             order_by=order_by, 
#             desc=(order_dir.lower() == "desc")
#         )
        
#         # Simple implementation: Returns list. 
#         # True pagination in DynamoDB requires LastEvaluatedKey logic which isn't 
#         # fully wrapped in list_items yet, so we return the simple batch.
#         return {
#             "items": items,
#             "next_page_token": None, # Implement LastEvaluatedKey encoding if needed
#             "page_size": len(items)
#         }

#     except Exception as e:
#         logger.error(f"Error getting parcel data from DynamoDB: {e}")
#         raise HTTPException(status_code=500, detail=str(e))


# @search_router.delete("/parcel/dynamo/{doc_id}", summary="Delete Analysis Result")
# async def delete_parcel_data_dynamo(doc_id: str):
#     try:
#         success = dynamo_service.delete_item(doc_id)
#         if success:
#             return {"message": "Parcel data deleted successfully"}
#         else:
#             raise HTTPException(status_code=404, detail="Item not found")
#     except Exception as e:
#         logger.error(f"Error deleting parcel data: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))


# @search_router.get("/parcel/dynamo/count", summary="Count Analysis Results")
# async def get_parcel_count_dynamo():
#     try:
#         # DynamoDB item_count is approximate (updated every ~6 hours)
#         # For exact count of scan, use: 
#         # count = dynamo_service.table.scan(Select='COUNT')['Count']
#         count = await dynamo_service.get_count()
#         return {"count": count}
#     except Exception as e:
#         logger.error(f"Error getting parcel count: {e}")
#         raise HTTPException(status_code=500, detail=str(e))

# @search_router.get("/parcel/dynamo/propid")
# async def search_parcel_dynamo_by_propid(
#     prop_id: str = Query(..., min_length=1),
#     county: Optional[str] = None,
#     limit: int = Query(100, ge=1, le=500),
# ):
#     """
#     Search by 'parcels.prop_id' in DynamoDB.
#     """
#     try:
#         filter_expr = Attr("parcels.prop_id").eq(prop_id)
        
#         if county:
#             filter_expr = filter_expr & Attr("parcels.county").eq(county)

#         response = dynamo_service.table.scan(
#             FilterExpression=filter_expr,
#             Limit=limit
#         )
        
#         items = response.get('Items', [])
#         # Sanitize Decimals back to float/int
#         items = [dynamo_service._desanitize_from_dynamodb(item) for item in items]

#         return {"items": items, "count": len(items)}
#     except Exception as e:
#         logger.error(f"Error DynamoDB search by prop_id: {e}")
#         raise HTTPException(status_code=500, detail=str(e))


# @search_router.get("/parcel/dynamo/owner")
# async def search_parcel_dynamo_by_owner(
#     owner_name: str = Query(..., min_length=1, description="Owner name"),
#     county: Optional[str] = None,
#     match: str = Query("exact", pattern="^(?i)(exact|contains)$"),
#     limit: int = Query(100, ge=1, le=500),
# ):
#     """
#     Search by 'parcels.owner_name' in DynamoDB.
#     Note: DynamoDB Scan 'contains' is case-sensitive. 
#     """
#     try:
#         key = "parcels.owner_name"
        
#         if match.lower() == "contains":
#             filter_expr = Attr(key).contains(owner_name)
#         else:
#             filter_expr = Attr(key).eq(owner_name)

#         if county:
#             filter_expr = filter_expr & Attr("parcels.county").eq(county)

#         response = dynamo_service.table.scan(
#             FilterExpression=filter_expr,
#             Limit=limit
#         )
        
#         items = response.get('Items', [])
#         items = [dynamo_service._desanitize_from_dynamodb(item) for item in items]

#         return {"items": items, "count": len(items)}
#     except Exception as e:
#         logger.error(f"Error DynamoDB search by owner: {e}")
#         raise HTTPException(status_code=500, detail=str(e))


# def _bounding_box(lat: float, lon: float, radius_m: float) -> Tuple[float, float, float, float]:
#     """Helper to calculate lat/lon bounds"""
#     lat_deg_m = 111_320.0
#     lon_deg_m = 111_320.0 * math.cos(math.radians(lat))
#     dlat = radius_m / lat_deg_m
#     dlon = radius_m / max(lon_deg_m, 1e-6)
#     return lat - dlat, lat + dlat, lon - dlon, lon + dlon


# @search_router.get("/parcel/dynamo/coordinates")
# async def search_parcel_dynamo_by_coordinates(
#     latitude: float = Query(..., description="Latitude in decimal degrees"),
#     longitude: float = Query(..., description="Longitude in decimal degrees"),
#     radius_m: float = Query(200.0, ge=1.0, le=50_000.0, description="Search radius in meters"),
#     county: Optional[str] = None,
#     limit: int = Query(200, ge=1, le=1000),
# ):
#     """
#     Coordinate proximity via bounding box in DynamoDB using Scan.
#     Filters on PropertyLatitude and PropertyLongitude.
#     """
#     try:
#         lat_min, lat_max, lon_min, lon_max = _bounding_box(latitude, longitude, radius_m)
        
#         # Note: DynamoDB stores numbers as Decimal. 
#         # Ensure your batch ingestion converts these to Decimal or float compatible types.
#         # We search 'PropertyLatitude' and 'PropertyLongitude' (from your batch CSV structure)
        
#         # 1. Latitude Filter
#         filter_expr = Attr("PropertyLatitude").between(str(lat_min), str(lat_max))
        
#         # 2. Longitude Filter
#         filter_expr = filter_expr & Attr("PropertyLongitude").between(str(lon_min), str(lon_max))

#         if county:
#             filter_expr = filter_expr & Attr("parcels.county").eq(county)

#         response = dynamo_service.table.scan(
#             FilterExpression=filter_expr,
#             Limit=limit
#         )

#         items = response.get('Items', [])
#         items = [dynamo_service._desanitize_from_dynamodb(item) for item in items]

#         return {"items": items, "count": len(items), "radius_m": radius_m}
#     except Exception as e:
#         logger.error(f"Error DynamoDB search by coordinates: {e}")
#         raise HTTPException(status_code=500, detail=str(e))