from fastapi import APIRouter, Depends, HTTPException, Header
from services import water_service as service
from db import get_session

router = APIRouter(prefix="/water_analysis", tags=["Water Analysis"])

@router.get("/ponds")
async def analyze_ponds(gid: int ,session=Depends(get_session)):
    """
    Analyze water bodies (ponds) within the specified geometry or database GID.
    """
    try:
        result = await service.analyze_ponds(session=session, gid=gid)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.get("/water-wells")
async def analyze_water_wells(gid: int ,session=Depends(get_session)):
    """
    Analyze water wells within the specified geometry or database GID.
    """
    try:
        result = await service.analyze_water_wells(session=session, gid=gid)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.get("/flood-zones")
async def analyze_flood_zones(gid: int ,session=Depends(get_session)):
    """
    Analyze flood zones within the specified geometry or database GID.
    """
    try:
        result = await service.analyze_flood_hazard(session=session, gid=gid)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.get("/lakes")
async def analyze_lakes(gid: int ,session=Depends(get_session)):
    """
    Analyze lakes within the specified geometry or database GID.
    """
    try:
        result = await service.analyze_lakes(session=session, gid=gid)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.get("/sea-ocean")
async def analyze_sea_ocean(gid: int ,session=Depends(get_session)):
    """
    Analyze sea and ocean within the specified geometry or database GID.
    """
    try:
        result = await service.analyze_sea_ocean(session=session, gid=gid)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.get("/streams")
async def analyze_streams(gid: int ,session=Depends(get_session)):
    """
    Analyze streams within the specified geometry or database GID.
    """
    try:
        result = await service.analyze_streams(session=session, gid=gid)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.get("/shoreline")
async def analyze_shoreline(gid: int ,session=Depends(get_session)):
    """
    Analyze shoreline within the specified geometry or database GID.
    """
    try:
        result = await service.analyze_shoreline(session=session, gid=gid)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.get("/wetlands")
async def analyze_wetlands(gid: int ,session=Depends(get_session)):
    """
    Analyze wetlands within the specified geometry or database GID.
    """
    try:
        result = await service.analyze_wetlands(session=session, gid=gid)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
