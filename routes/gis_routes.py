from fastapi import APIRouter, Depends, HTTPException
from services import gis_service
from db import get_session
from sqlalchemy.ext.asyncio import AsyncSession
import logging
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/gis", tags=["GIS Analysis"])

@router.get("/buildable", summary="Perform GIS Analysis")
async def buildable_area_analysis(gid: int,db: AsyncSession = Depends(get_session)):
    """
    Perform buildable area analysis based on the provided GID.
    """
    try:
        results = await gis_service.analyze_buildable_area(session=db, gid=gid)
        return results
    except Exception as e:
        logger.error(f"Buildable area analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Buildable area analysis failed: {str(e)}")
@router.get("/road-frontage", summary="Perform Road Frontage Analysis")
async def road_frontage_analysis(gid: int,db: AsyncSession = Depends(get_session)):
    """
    Perform road frontage analysis based on the provided GID.
    """
    try:
        results = await gis_service.analyze_road_frontage(session=db, gid=gid)
        return results
    except Exception as e:
        logger.error(f"Road frontage analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Road frontage analysis failed: {str(e)}")
@router.get("/elevation-change", summary="Perform Elevation Change Analysis")
async def elevation_change_analysis(gid: int,db: AsyncSession = Depends(get_session)):
    """
    Perform elevation change analysis based on the provided GID.
    """
    try:
        results = await gis_service.analyze_elevation_change(session=db, gid=gid)
        return results
    except Exception as e:
        logger.error(f"Elevation change analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Elevation change analysis failed: {str(e)}")
@router.get("/slope", summary="Perform Slope Analysis")
async def slope_analysis(gid: int,db: AsyncSession = Depends(get_session)):
    """
    Perform slope analysis based on the provided GID.
    """
    try:
        results = await gis_service.analyze_slope(session=db, gid=gid)
        return results
    except Exception as e:
        logger.error(f"Slope analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Slope analysis failed: {str(e)}")
@router.get("/electric-lines", summary="Perform Electric Lines Analysis")
async def electric_lines_analysis(gid: int,db: AsyncSession = Depends(get_session)):
    """
    Perform electric lines analysis based on the provided GID.
    """
    try:
        results = await gis_service.analyze_electric_lines(session=db, gid=gid)
        return results
    except Exception as e:
        logger.error(f"Electric lines analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Electric lines analysis failed: {str(e)}")
@router.get("/gas-pipelines", summary="Perform Gas Pipelines Analysis")
async def gas_pipelines_analysis(gid: int,db: AsyncSession = Depends(get_session)):
    """
    Perform gas pipelines analysis based on the provided GID.
    """
    try:
        results = await gis_service.analyze_gas_pipelines(session=db, gid=gid)
        return results
    except Exception as e:
        logger.error(f"Gas pipelines analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Gas pipelines analysis failed: {str(e)}")
@router.get("/tree-coverage", summary="Perform Tree Coverage Analysis")
async def tree_coverage_analysis(gid: int,db: AsyncSession = Depends(get_session)):
    """
    Perform tree coverage analysis based on the provided GID.
    """
    try:
        results = await gis_service.analyze_tree_coverage(session=db, gid=gid)
        return results
    except Exception as e:
        logger.error(f"Tree coverage analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Tree coverage analysis failed: {str(e)}")
