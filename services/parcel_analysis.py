import os
import asyncio
import logging
import time
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, Literal, Optional,  Tuple, Callable
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from geoalchemy2.shape import from_shape
from geoalchemy2.functions import ST_Contains
from shapely.geometry import Point
from schemas import Parcel
from config import config
from db import SessionLocal
from schemas import AnalysisResult
from .gis import GISAnalysisService
from .water import WaterAnalysisService
from .image import ImageService

analysis_logger = logging.getLogger("batch_analysis")
analysis_logger.setLevel(logging.INFO)
os.makedirs("logs", exist_ok=True)
analysis_handler = RotatingFileHandler(
    "logs/analysis.log", maxBytes=5_000_000, backupCount=5
)
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
analysis_handler.setFormatter(formatter)
analysis_logger.addHandler(analysis_handler)
analysis_logger.propagate = False

class AnalysisService:
    def __init__(self):
        try:
            analysis_logger.info("Initializing AnalysisService with Unified Services...")
            self.gis_service = GISAnalysisService()
            self.water_service = WaterAnalysisService()
            self.image_service = ImageService()
            self.semaphore = asyncio.Semaphore(20)
            analysis_logger.info("AnalysisService initialized successfully")
        except Exception as e:
            analysis_logger.error(f"Failed to initialize AnalysisService: {str(e)}")
            raise RuntimeError(f"Failed to initialize AnalysisService: {str(e)}") from e
    async def __get_parcel_data(self, gid: int, session: AsyncSession) -> Dict[str, Any]:
        """Fetches metadata and simplified geometry for analysis."""
        if not gid:
            raise ValueError("GID parameter is required")
        try:
            query = text("""
                SELECT 
                    p.prop_id,
                    p.county,
                    CASE 
                        WHEN p.legal_area IS NULL OR TRIM(p.legal_area) = '' 
                        THEN ROUND((ST_Area(ST_Transform(p.geom, 3083)) / 4046.86)::numeric, 2)
                        ELSE CAST(NULLIF(REGEXP_REPLACE(p.legal_area, '[^0-9.]', '', 'g'), '') AS FLOAT)
                    END AS acreage,
                    p.geo_id,
                    p.owner_name,
                    p.situs_addr,
                    COALESCE(c."CITY_NM", 'Outside') AS city,
                    ST_X(ST_Centroid(p.geom)) AS centroid_x,
                    ST_Y(ST_Centroid(p.geom)) AS centroid_y,
                    ST_AsText(ST_SimplifyPreserveTopology(p.geom, 0.00001)) AS geom
                FROM parcels p 
                LEFT JOIN texas_cities c 
                    ON ST_Within(p.geom, c.geometry)
                WHERE p.gid = :gid
            """)
            result = await session.execute(query, {"gid": gid})
            parcel_data = result.mappings().first()
            if not parcel_data:
                return {}
            return dict(parcel_data)
        except Exception as e:
            analysis_logger.error(f"Error fetching parcel data for GID {gid}: {e}")
            raise SQLAlchemyError(f"Failed to fetch parcel data for GID {gid}") from e
    async def get_gid_by_coordinates(self, latitude: float, longitude: float, session: AsyncSession) -> Optional[int]:
        try:
            lat, lon = float(latitude), float(longitude)
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                raise ValueError("Invalid coordinates")
            query = select(Parcel).where(
                ST_Contains(Parcel.geom, from_shape(Point(lon, lat), srid=4326))
            ).limit(1)
            result = await asyncio.wait_for(session.execute(query), timeout=10.0)
            parcel = result.scalars().first()
            return parcel.gid if parcel else None
        except Exception as e:
            analysis_logger.error(f"Coordinate lookup failed: {e}")
            raise
    async def _safe_run(self, key: str, coro) -> Tuple[str, Any]:
        try:
            return key, await coro
        except Exception as e:
            analysis_logger.error(f"Task '{key}' failed: {e}")
            return key, {"error": str(e), "status": "failed"}
    async def _exec_with_session(self, func: Callable, **kwargs) -> Any:
        async with self.semaphore:
            async with SessionLocal() as session:
                return await func(session, **kwargs)
    async def _save_results(
        self, 
        session: AsyncSession, 
        gid: int, 
        data: Dict, 
        batch_id: Optional[str], 
        mode: str,
        csv_context: Optional[Dict] = None
    ):
        """
        Upsert analysis results into the database.
        csv_context is saved to a separate JSONB column (csv_source_data) if provided.
        """
        try:
            stmt = select(AnalysisResult).where(AnalysisResult.parcel_gid == gid)
            result = await session.execute(stmt)
            existing_record = result.scalars().first()
            if existing_record:
                existing_record.result_data = data
                existing_record.batch_id = batch_id
                existing_record.processing_mode = mode
                if csv_context:
                    existing_record.csv_source_data = csv_context
                
                session.add(existing_record)
                analysis_logger.info(f"Updated analysis record for GID {gid}")
            else:
                new_record = AnalysisResult(
                    parcel_gid=gid,
                    result_data=data,
                    batch_id=batch_id,
                    processing_mode=mode,
                    csv_source_data=csv_context 
                )
                session.add(new_record)
                analysis_logger.info(f"Created new analysis record for GID {gid}")
            await session.commit()
        except Exception as e:
            analysis_logger.error(f"Failed to save analysis to DB for GID {gid}: {e}")
            await session.rollback()
    async def get_analysis(
        self, 
        gid: int, 
        db: AsyncSession, 
        processing_mode: Literal["single", "batch"] = "single", 
        batch_id: Optional[str] = None, 
        generate_images: bool = True,
        force_refresh: bool = False,       
        csv_context: Optional[Dict] = None 
    ) -> Dict[str, Any]:
        start_time = time.perf_counter()
        analysis_logger.info(f"Starting analysis for GID: {gid} | Mode: {processing_mode}")
        try:
            if not force_refresh:
                stmt = select(AnalysisResult).where(AnalysisResult.parcel_gid == gid)
                result = await db.execute(stmt)
                existing = result.scalars().first()
                if existing:
                    analysis_logger.info(f"Found existing analysis for GID {gid}. Skipping GIS.")
                    data = existing.result_data
                    if processing_mode == "batch":
                        existing.batch_id = batch_id
                        existing.processing_mode = "batch"
                        existing.result_data = data
                        if csv_context:
                            existing.csv_source_data = csv_context
                        db.add(existing)
                        await db.commit()
                    return data
            parcel_data = await self.__get_parcel_data(gid, db)
            if not parcel_data:
                return {"error": f"No parcel found with GID: {gid}"}
            parcel_geom_wkt = parcel_data.get("geom")
            analysis_tasks_map = {
                "gas_lines": self.gis_service.analyze_gas_pipelines,
                "electric_lines": self.gis_service.analyze_electric_lines,
                "road_analysis": self.gis_service.analyze_road_frontage,
                "buildable_area": self.gis_service.analyze_buildable_area,
                "elevation_change": self.gis_service.analyze_elevation_change,
                "tree_coverage": self.gis_service.analyze_tree_coverage,
                "well_analysis": self.water_service.analyze_water_wells,
                "wetland_analysis": self.water_service.analyze_wetlands,
                "pond_analysis": self.water_service.analyze_ponds,
                "lake_analysis": self.water_service.analyze_lakes,
                "stream_intersection": self.water_service.analyze_streams,
                "flood_hazard": self.water_service.analyze_flood_hazard,
                "sea_ocean_length": self.water_service.analyze_sea_ocean,
                "shoreline_analysis": self.water_service.analyze_shoreline,
            }
            image_tasks_map = {}
            if generate_images:
                image_tasks_map = {
                    "image_url": self.image_service.get_parcel_image,
                    "road_frontage_image_url": self.image_service.get_road_frontage_image,
                    "flood_image_url": self.image_service.get_flood_image,
                    "tree_image_url": self.image_service.get_tree_image,
                    "contour_image_url": self.image_service.get_contour_image,
                    "water_image_url": self.image_service.get_water_image,
                }
            futures = []
            for key, func in analysis_tasks_map.items():
                coro = self._exec_with_session(func, gid=None, geom=parcel_geom_wkt)
                futures.append(self._safe_run(key, coro))
            for key, func in image_tasks_map.items():
                coro = self._exec_with_session(func, gid=gid, geom=parcel_geom_wkt)
                futures.append(self._safe_run(key, coro))
            results_list = await asyncio.gather(*futures)
            analysis_results = {k: v for k, v in results_list}
            def recursive_sanitize(obj: Any) -> Any:
                if isinstance(obj, dict):
                    return {k: recursive_sanitize(v) for k, v in obj.items()}
                if isinstance(obj, list):
                    return [recursive_sanitize(v) for v in obj]
                if isinstance(obj, Decimal):
                    return float(obj)
                return obj

            duration = time.perf_counter() - start_time
            
            final_output = {
                "parcels": recursive_sanitize(parcel_data),
                **recursive_sanitize(analysis_results),
                "meta": {
                    "processing_mode": processing_mode,
                    "batch_id": batch_id,
                    "execution_time_seconds": round(duration, 2)
                }
            }
            await self._save_results(
                session=db, 
                gid=gid, 
                data=final_output, 
                batch_id=batch_id, 
                mode=processing_mode,
                csv_context=csv_context
            )
            return final_output
        except Exception as e:
            analysis_logger.error(f"Critical error analyzing {gid}: {e}")
            return {"error": str(e), "gid": gid}