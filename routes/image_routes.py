from io import BytesIO
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from services import image_service
from db import get_session
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
router = APIRouter(prefix="/image", tags=["Images"])
@router.get("/parcel", summary="Get Aerial Parcel Image")
async def get_parcel_image(gid: Optional[int] = None, geom: Optional[str] = None, db: AsyncSession = Depends(get_session)):
    if not gid and not geom:
        raise HTTPException(status_code=400, detail="Either 'gid' or 'geom' must be provided.")
    result = await image_service.get_parcel_image(db, gid=gid, geom=geom)
    if isinstance(result, dict):
        return JSONResponse(content=result)    
    return JSONResponse(content={"image_url": result})

@router.get("/road-frontage", summary="Get Road Frontage Image")
async def get_road_image(gid: Optional[int] = None, geom: Optional[str] = None, db: AsyncSession = Depends(get_session)):
    if not gid and not geom:
        raise HTTPException(status_code=400, detail="Either 'gid' or 'geom' must be provided.")
    result = await image_service.get_road_frontage_image(db, gid=gid, geom=geom)
    if isinstance(result, dict):
        return JSONResponse(content=result)    
    return JSONResponse(content={"image_url": result})
@router.get("/flood", summary="Get Flood Hazard Image")
async def get_flood_image(gid: Optional[int] = None, geom: Optional[str] = None, db: AsyncSession = Depends(get_session)):
    if not gid and not geom:
        raise HTTPException(status_code=400, detail="Either 'gid' or 'geom' must be provided.")
    result = await image_service.get_flood_image(db, gid=gid, geom=geom)
    if isinstance(result, dict):
        return JSONResponse(content=result)    
    return JSONResponse(content={"image_url": result})

@router.get("/tree", summary="Get Tree Coverage Image")
async def get_tree_image(gid: Optional[int] = None, geom: Optional[str] = None, db: AsyncSession = Depends(get_session)):
    if not gid and not geom:
        raise HTTPException(status_code=400, detail="Either 'gid' or 'geom' must be provided.")
    result = await image_service.get_tree_image(db, gid=gid, geom=geom)
    if isinstance(result, dict):
        return JSONResponse(content=result)    
    return JSONResponse(content={"image_url": result})

@router.get("/contour", summary="Get Contour/Elevation Image")
async def get_contour_image(gid: Optional[int] = None, geom: Optional[str] = None, db: AsyncSession = Depends(get_session)):
    if not gid and not geom:
        raise HTTPException(status_code=400, detail="Either 'gid' or 'geom' must be provided.")
    result = await image_service.get_contour_image(db, gid=gid, geom=geom)
    if isinstance(result, dict):
        return JSONResponse(content=result)    
    return JSONResponse(content={"image_url": result})

@router.get("/water", summary="Get Water Features Image")
async def get_water_image(gid: Optional[int] = None, geom: Optional[str] = None, db: AsyncSession = Depends(get_session)):
    if not gid and not geom:
        raise HTTPException(status_code=400, detail="Either 'gid' or 'geom' must be provided.")
    result = await image_service.get_water_image(db, gid=gid, geom=geom)
    if isinstance(result, dict):
        return JSONResponse(content=result)    
    return JSONResponse(content={"image_url": result})