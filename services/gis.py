import os
import json
import logging
import math
import numpy as np
import rasterio
from rasterio.mask import mask
from shapely.geometry import shape, mapping
from shapely import wkt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text
from typing import Dict, Any, Optional, Tuple
import ee
from config import config

logger = logging.getLogger(__name__)

class GISAnalysisService:
    """
    Centralized, optimized service for all GIS analysis (Vector & Raster).
    Capable of analyzing based on Database GID OR Raw Geometry input.
    """

    def __init__(self):
        self.dem_path = os.environ.get("ELEVATION_FILE", "/mnt/land200/gis-data/tx_terrain/Texas_DEM.vrt")
        self.tree_path = os.environ.get("TREE_COVERAGE_PATH", "/mnt/land200/gis-data/tx_treecoverage")
    async def _get_target_geometry(
        self, 
        session: AsyncSession, 
        gid: Optional[int] = None, 
        geom_input: Optional[str] = None
    ) -> Tuple[str, Any]:
        """
        Internal Helper: Resolves the target geometry to WKT and Shapely object.
        
        Args:
            session: DB session
            gid: Parcel ID
            geom_input: WKT or GeoJSON string
            
        Returns:
            Tuple(wkt_string, shapely_object)
        """
        if geom_input:
            try:
                input_str = geom_input.strip()
                if input_str.startswith("{"):
                    shapely_geom = shape(json.loads(input_str))
                else:
                    shapely_geom = wkt.loads(input_str)
                
                return shapely_geom.wkt, shapely_geom
            except Exception as e:
                logger.error(f"Failed to parse provided geometry: {e}")
                raise ValueError(f"Invalid geometry format provided: {e}")
        if gid:
            try:
                query = text("SELECT ST_AsText(geom) FROM parcels WHERE gid = :gid")
                result = await session.execute(query, {"gid": gid})
                row = result.fetchone()
                if not row:
                    raise ValueError(f"Parcel GID {gid} not found.")
                
                shapely_geom = wkt.loads(row[0])
                return row[0], shapely_geom
            except Exception as e:
                logger.error(f"Database error fetching GID {gid}: {e}")
                raise

        raise ValueError("Either 'gid' or 'geom_input' must be provided.")
    async def analyze_gas_pipelines(self, session: AsyncSession, gid: Optional[int] = None, geom: Optional[str] = None) -> Dict[str, Any]:
        """Checks intersection with Gas Pipelines using optimized spatial query."""
        target_wkt, _ = await self._get_target_geometry(session, gid, geom)
        sql = text("""
            SELECT oper_nm, sys_nm, diameter, commodity1, pline_id, subsys_nm, cmdty_desc
            FROM gas_pipelines 
            WHERE ST_Intersects(geom, ST_SetSRID(ST_GeomFromText(:wkt), 4326))
        """)
        res = await session.execute(sql, {"wkt": target_wkt})
        rows = res.fetchall()
        pipelines = [
            {
                "Operator": r[0], 
                "System": r[1], 
                "Diameter": r[2], 
                "Commodity": r[3],
                "PipelineID": r[4],
                "Subsystem": r[5],
                "Description": r[6]
            } for r in rows
        ]
        if not pipelines:
            nearest_sql = text("""
                SELECT oper_nm, sys_nm, diameter, commodity1, 
                       ST_Distance(ST_SetSRID(ST_GeomFromText(:wkt), 4326)::geography, geom::geography) as dist
                FROM gas_pipelines
                ORDER BY geom <-> ST_SetSRID(ST_GeomFromText(:wkt), 4326)
                LIMIT 1
            """)
            near_res = await session.execute(nearest_sql, {"wkt": target_wkt})
            nearest = near_res.fetchone()
            nearest_info = None
            if nearest:
                nearest_info = {
                    "Operator": nearest[0],
                    "System": nearest[1],
                    "Diameter": nearest[2],
                    "Distance_Meters": round(nearest[4], 2)
                }
            return {"intersects": False, "count": 0, "details": [], "nearest": nearest_info}

        return {
            "intersects": True,
            "count": len(pipelines),
            "details": pipelines
        }
    async def analyze_electric_lines(self, session: AsyncSession, gid: Optional[int] = None, geom: Optional[str] = None) -> Dict[str, Any]:
        """Checks intersection with Electric Transmission Lines."""
        target_wkt, _ = await self._get_target_geometry(session, gid, geom)
        sql = text("""
            SELECT owner, voltage, type, volt_class, naics_desc
            FROM electric_transmission_lines 
            WHERE ST_Intersects(geom, ST_SetSRID(ST_GeomFromText(:wkt), 4326))
        """)
        res = await session.execute(sql, {"wkt": target_wkt})
        rows = res.fetchall()
        lines = [
            {
                "Owner": r[0], 
                "Voltage": r[1], 
                "Type": r[2], 
                "Class": r[3],
                "Description": r[4]
            } for r in rows
        ]
        if not lines:
             nearest_sql = text("""
                SELECT owner, voltage, type,
                       ST_Distance(ST_SetSRID(ST_GeomFromText(:wkt), 4326)::geography, geom::geography) as dist
                FROM electric_transmission_lines
                ORDER BY geom <-> ST_SetSRID(ST_GeomFromText(:wkt), 4326)
                LIMIT 1
            """)
             near_res = await session.execute(nearest_sql, {"wkt": target_wkt})
             nearest = near_res.fetchone()
             nearest_info = None
             if nearest:
                 nearest_info = {
                     "Owner": nearest[0],
                     "Voltage": nearest[1],
                     "Type": nearest[2],
                     "Distance_Meters": round(nearest[3], 2)
                 }
             return {"intersects": False, "count": 0, "details": [], "nearest": nearest_info}

        return {
            "intersects": True,
            "count": len(lines),
            "details": lines
        }
    
    async def analyze_road_frontage(self, session: AsyncSession, gid: Optional[int] = None, geom: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculates road frontage in feet.
        Returns a list containing a single result dict to satisfy BatchService's iteration logic.
        """
        target_wkt, _ = await self._get_target_geometry(session, gid, geom)
        sql = text("""
            WITH parcel_geom_tab AS (
                SELECT ST_Transform(ST_SetSRID(ST_GeomFromText(:wkt), 4326), 3083) as geom
            ),
            nearby_roads AS (
                SELECT ST_Transform(wkb_geometry, 3083) as geom
                FROM frontage_analysis_roads, parcel_geom_tab p
                WHERE ST_DWithin(ST_Transform(wkb_geometry, 3083), p.geom, 25)
            ),
            merged_roads AS (
                SELECT ST_Union(geom) as geom FROM nearby_roads
            ),
            raw_frontage AS (
                SELECT 
                    CASE 
                        WHEN mr.geom IS NULL THEN 0
                        ELSE ST_Length(ST_Intersection(ST_Boundary(p.geom), ST_Buffer(mr.geom, 25))) 
                    END as len_m
                FROM parcel_geom_tab p
                LEFT JOIN merged_roads mr ON true
            ),
            interior_roads AS (
                SELECT COALESCE(SUM(ST_Length(ST_Intersection(nr.geom, p.geom))), 0) as len_m
                FROM nearby_roads nr, parcel_geom_tab p
                WHERE ST_Intersects(nr.geom, p.geom)
            )
            SELECT 
                rf.len_m * 3.28084 as frontage_ft, 
                ir.len_m * 3.28084 as interior_ft,
                (SELECT COUNT(*) FROM nearby_roads) as access_count
            FROM raw_frontage rf, interior_roads ir
        """)
        try:
            res = await session.execute(sql, {"wkt": target_wkt})
            row = res.fetchone()
            raw_frontage = float(row[0]) if row else 0.0
            interior_len = float(row[1]) if row else 0.0
            access_count = row[2] if row else 0
            adjusted_frontage = max(raw_frontage - interior_len, 0.0)
            return {
                "length_ft": round(adjusted_frontage, 2),
                "intersects": adjusted_frontage > 0,
                "road_in_parcel_feet": round(interior_len, 2),
                "road_access_count": access_count,
                "raw_boundary_feet": round(raw_frontage, 2)
            }
        except Exception as e:
            logger.error(f"Road frontage analysis failed      : {e}")
            return {}
    async def analyze_buildable_area(self, session: AsyncSession, gid: Optional[int] = None, geom: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculates buildable area by subtracting Flood Zones and Wetlands from Total Area.
        Uses EPSG:3083 for accurate area calculation in Texas.
        FIX: Handles SRID mismatch by enforcing SRID on empty geometry fallback.
        """
        target_wkt, _ = await self._get_target_geometry(session, gid, geom)
        query = text("""
            WITH target AS (
                SELECT ST_Transform(ST_SetSRID(ST_GeomFromText(:wkt), 4326), 3083) as geom
            ),
            constraints AS (
                -- Combine Flood and Wetlands
                SELECT ST_Union(geom) as geom FROM (
                    SELECT ST_Transform(geom, 3083) as geom FROM tx_fld_haz 
                    WHERE ST_Intersects(geom, ST_Transform(ST_SetSRID(ST_GeomFromText(:wkt), 4326), 3083))
                    UNION ALL
                    SELECT ST_Transform(geom, 3083) as geom FROM wetlands 
                    WHERE ST_Intersects(geom, ST_Transform(ST_SetSRID(ST_GeomFromText(:wkt), 4326), 3083))
                    UNION ALL
                    SELECT ST_Transform(geom, 3083) as geom FROM radcorp_water
                    WHERE ST_Intersects(geom, ST_Transform(ST_SetSRID(ST_GeomFromText(:wkt), 4326), 3083))
                ) as combined
            )
            SELECT 
                ST_Area(target.geom) / 4046.86 as total_acres,
                -- Fix: Explicitly set SRID for the empty collection fallback to match target (3083)
                ST_Area(ST_Intersection(target.geom, COALESCE(constraints.geom, ST_SetSRID('GEOMETRYCOLLECTION EMPTY'::geometry, 3083)))) / 4046.86 as unbuildable_acres
            FROM target LEFT JOIN constraints ON true;
        """)
        try:
            res = await session.execute(query, {"wkt": target_wkt})
            row = res.fetchone()
            
            total_acres = float(row[0]) if row and row[0] else 0.0
            unbuildable_acres = float(row[1]) if row and row[1] else 0.0
            buildable_acres = max(0.0, total_acres - unbuildable_acres)
            return {
                "total_acres": round(total_acres, 2),
                "unbuildable_acres": round(unbuildable_acres, 2),
                "buildable_acres": round(buildable_acres, 2),
                "buildable_percentage": round((buildable_acres / total_acres * 100), 1) if total_acres > 0 else 0
            }
        except Exception as e:
            logger.error(f"Buildable area analysis failed: {e}")
            return {"error": str(e)}
    async def analyze_elevation_change(self, session: AsyncSession, gid: Optional[int] = None, geom: Optional[str] = None) -> Dict[str, Any]:
        """Calculates Min, Max, and Change in elevation using local DEM raster."""
        _, shapely_geom = await self._get_target_geometry(session, gid, geom)

        if not os.path.exists(self.dem_path):
            return {"error": f"Elevation file not found: {self.dem_path}"}
        try:
            import geopandas as gpd
            with rasterio.open(self.dem_path) as src:
                raster_crs = src.crs
                gdf = gpd.GeoDataFrame({'geometry': [shapely_geom]}, crs="EPSG:4326")
                gdf_proj = gdf.to_crs(raster_crs)
                proj_geom = gdf_proj.geometry.values[0]

                out_image, _ = mask(src, [mapping(proj_geom)], crop=True, nodata=-9999)
                data = out_image[0]
                valid_data = data[data != -9999]

                if valid_data.size == 0:
                    return {"elevation_change_feet": 0.0, "status": "No data in bounds"}

                min_elev = float(np.min(valid_data))
                max_elev = float(np.max(valid_data))
                METERS_TO_FEET = 3.28084
                return {
                    "min_elevation_feet": round(min_elev * METERS_TO_FEET, 2),
                    "max_elevation_feet": round(max_elev * METERS_TO_FEET, 2),
                    "elevation_change_feet": round((max_elev - min_elev) * METERS_TO_FEET, 2)
                }
        except Exception as e:
            logger.error(f"Elevation analysis failed: {e}")
            return {"error": str(e)}
    
        """
        Calculates Slope using Google Earth Engine (USGS 3DEP).
        """
        _, shapely_geom = await self._get_target_geometry(session, gid, geom)
        try:
            geojson = mapping(shapely_geom)
            ee_geom = ee.Geometry(geojson)

            dem = ee.Image("USGS/3DEP/10m")
            slope_img = ee.Terrain.slope(dem).clip(ee_geom)
            
            # Reduce region to get mean and max
            stats = slope_img.reduceRegion(
                reducer=ee.Reducer.mean().combine(ee.Reducer.max(), sharedInputs=True),
                geometry=ee_geom,
                scale=10,
                maxPixels=1e9
            ).getInfo()

            mean_deg = stats.get('slope_mean', 0)
            max_deg = stats.get('slope_max', 0)

            def deg_to_pct(d): 
                return round(math.tan(math.radians(d)) * 100, 2)

            return {
                "mean_slope_degrees": round(mean_deg, 2),
                "mean_slope_percentage": deg_to_pct(mean_deg),
                "max_slope_degrees": round(max_deg, 2),
                "max_slope_percentage": deg_to_pct(max_deg)
            }
        except Exception as e:
            logger.error(f"Slope analysis failed: {e}")
            return {"error": f"Slope analysis failed: {str(e)}"}
    async def analyze_tree_coverage(self, session: AsyncSession, gid: Optional[int] = None, geom: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculates tree coverage percentage using local COG files.
        """
        _, shapely_geom = await self._get_target_geometry(session, gid, geom)

        if not os.path.exists(self.tree_path):
             return {"error": "Tree coverage data not found"}

        try:
            import geopandas as gpd
            target_epsg = 3857 
            gdf = gpd.GeoDataFrame({'geometry': [shapely_geom]}, crs="EPSG:4326")
            gdf_proj = gdf.to_crs(epsg=target_epsg)
            proj_geom = gdf_proj.geometry.values[0]
            bbox = proj_geom.bounds
            total_pixels = 0
            tree_pixels = 0
            brush_pixels = 0
            processed_any = False
            for f in os.listdir(self.tree_path):
                if f.endswith(".tif"):
                    fpath = os.path.join(self.tree_path, f)
                    with rasterio.open(fpath) as src:
                        if not (src.bounds.right < bbox[0] or src.bounds.left > bbox[2] or 
                                src.bounds.bottom > bbox[3] or src.bounds.top < bbox[1]):
                            try:
                                out_image, _ = mask(src, [mapping(proj_geom)], crop=True, nodata=0)
                                data = out_image[0]
                                valid_pixels = data[data != 0]
                                total_pixels += valid_pixels.size
                                tree_pixels += np.sum(valid_pixels >= 3)
                                brush_pixels += np.sum((valid_pixels > 0) & (valid_pixels < 3))
                                processed_any = True
                            except ValueError:
                                continue
            if not processed_any or total_pixels == 0:
                return {
                    "tree_percentage": 0.0,
                    "brush_percentage": 0.0,
                    "message": "No tree coverage data found for this area"
                }
            return {
                "tree_percentage": round((tree_pixels / total_pixels) * 100, 2),
                "brush_percentage": round((brush_pixels / total_pixels) * 100, 2)
            }
        except Exception as e:
            logger.error(f"Tree coverage analysis failed: {e}")
            return {"error": str(e)}