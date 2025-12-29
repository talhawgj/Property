import json
import logging
from typing import Dict, Any, Optional, Tuple, List
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text
from shapely.geometry import shape
from shapely import wkt

logger = logging.getLogger(__name__)

class WaterAnalysisService:
    """
    Centralized service for all Water-related analysis.
    Supports analysis by Database GID OR Raw Geometry input.
    """

    async def _get_target_geometry(
        self, 
        session: AsyncSession, 
        gid: Optional[int] = None, 
        geom_input: Optional[str] = None
    ) -> Tuple[str, Any]:
        """
        Internal Helper: Resolves the target geometry to WKT and Shapely object.
        """
        # 1. Handle Raw Geometry Input
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
                raise ValueError(f"Invalid geometry format: {e}")

        # 2. Handle GID Lookup
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

    # ---------------------------------------------------------
    # 1. Water Wells Analysis
    # ---------------------------------------------------------
    async def analyze_water_wells(
        self, 
        session: AsyncSession, 
        gid: Optional[int] = None, 
        geom: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Checks intersection with Groundwater Wells. 
        If no intersection, finds the nearest well.
        """
        target_wkt, _ = await self._get_target_geometry(session, gid, geom)

        # 1. Check Intersection
        sql_intersect = text("""
            SELECT welltype, proposedus, boreholede, injuriousw 
            FROM water_wells
            WHERE ST_Intersects(geom, ST_GeomFromText(:wkt, 4326))
        """)
        
        res = await session.execute(sql_intersect, {"wkt": target_wkt})
        rows = res.fetchall()
        
        if rows:
            wells = [
                {
                    "WellType": r[0],
                    "ProposedUse": r[1],
                    "Depth": float(r[2]) if r[2] is not None else None,
                    "Injurious": r[3]
                } for r in rows
            ]
            return {"intersects": True, "count": len(wells), "wells": wells}

        # 2. Find Nearest (if no intersection)
        sql_nearest = text("""
            SELECT welltype, proposedus, boreholede, injuriousw,
                   ST_Distance(ST_GeomFromText(:wkt, 4326)::geography, geom::geography) AS distance_m
            FROM water_wells
            ORDER BY geom <-> ST_GeomFromText(:wkt, 4326)
            LIMIT 1
        """)
        
        res_near = await session.execute(sql_nearest, {"wkt": target_wkt})
        nearest = res_near.fetchone()
        
        if nearest:
            return {
                "intersects": False,
                "count": 0,
                "wells": [],
                "nearest": {
                    "WellType": nearest[0],
                    "ProposedUse": nearest[1],
                    "Depth": float(nearest[2]) if nearest[2] is not None else None,
                    "Injurious": nearest[3],
                    "distance_m": round(nearest[4], 2)
                }
            }
            
        return {"intersects": False, "count": 0, "wells": []}

    # ---------------------------------------------------------
    # 2. Wetlands Analysis
    # ---------------------------------------------------------
    async def analyze_wetlands(
        self, 
        session: AsyncSession, 
        gid: Optional[int] = None, 
        geom: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyzes NWI Wetlands intersection, calculating area and percentage.
        Uses EPSG:3083 for accurate area calculations.
        """
        target_wkt, _ = await self._get_target_geometry(session, gid, geom)

        # Calculate total parcel area first
        area_query = text("""
            SELECT ST_Area(ST_Transform(ST_GeomFromText(:wkt, 4326), 3083))
        """)
        area_res = await session.execute(area_query, {"wkt": target_wkt})
        total_area_m2 = area_res.scalar() or 0.0
        
        if total_area_m2 == 0:
            return {"error": "Invalid or zero parcel area"}

        total_area_acres = total_area_m2 / 4046.86

        # Detailed intersection query
        sql = text("""
            SELECT 
                w.wetland_type,
                ST_Area(ST_Transform(ST_Intersection(ST_GeomFromText(:wkt, 4326), w.geom), 3083)) as area_m2
            FROM wetlands w
            WHERE ST_Intersects(ST_GeomFromText(:wkt, 4326), w.geom)
        """)

        res = await session.execute(sql, {"wkt": target_wkt})
        rows = res.fetchall()

        # Aggregate results
        aggregated = defaultdict(lambda: {"area_acres": 0.0, "percentage": 0.0})
        total_wetland_acres = 0.0

        for w_type, area_m2 in rows:
            if area_m2 > 0:
                acres = area_m2 / 4046.86
                aggregated[w_type]["area_acres"] += acres
                total_wetland_acres += acres

        results = []
        for w_type, data in aggregated.items():
            pct = (data["area_acres"] / total_area_acres) * 100
            results.append({
                "wetland_type": w_type,
                "area_acres": round(data["area_acres"], 2),
                "percentage": round(pct, 2)
            })

        cleared_acres = max(total_area_acres - total_wetland_acres, 0)
        cleared_pct = (cleared_acres / total_area_acres) * 100

        return {
            "intersects": len(results) > 0,
            "wetland_analysis": results,
            "cleared_area_acres": round(cleared_acres, 2),
            "cleared_percentage": round(cleared_pct, 2)
        }

    # ---------------------------------------------------------
    # 3. Ponds Analysis
    # ---------------------------------------------------------
    async def analyze_ponds(
        self, 
        session: AsyncSession, 
        gid: Optional[int] = None, 
        geom: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyzes Ponds (LakePond <= 12 acres) from `radcorp_water`.
        Falls back to 'wetlands' if no specific pond found.
        """
        target_wkt, _ = await self._get_target_geometry(session, gid, geom)

        sql = text("""
            SELECT rw.acres, 
                   ST_Area(ST_Intersection(ST_Transform(ST_GeomFromText(:wkt, 4326), 3083), 
                                           ST_Transform(rw.geom, 3083))) as inter_m2
            FROM radcorp_water rw
            WHERE rw.ftype_str = 'LakePond'
              AND ST_Intersects(ST_GeomFromText(:wkt, 4326), rw.geom)
        """)

        res = await session.execute(sql, {"wkt": target_wkt})
        rows = res.fetchall()

        total_pond_acres = 0.0
        unique_count = 0
        
        for acres, inter_m2 in rows:
            # Definition: Pond if total acres <= 12
            if inter_m2 > 0 and (acres is None or acres <= 12):
                total_pond_acres += (inter_m2 / 4046.86)
                unique_count += 1

        if unique_count > 0:
            return {
                "intersects": True,
                "pond_area_acres": round(total_pond_acres, 2),
                "unique_pond_count": unique_count
            }
        
        return {"intersects": False, "pond_area_acres": 0.0, "unique_pond_count": 0}
    async def analyze_lakes(
        self,session: AsyncSession,gid: Optional[int] = None, geom: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyzes Lakes (LakePond > 12 acres) from `radcorp_water`.
        Calculates shared perimeter (shoreline) and area.
        """
        target_wkt, _ = await self._get_target_geometry(session, gid, geom)
        sql = text("""
            SELECT rw.acres,
                   ST_Length(ST_Intersection(
                       ST_Boundary(ST_Transform(rw.geom, 3083)),
                       ST_Transform(ST_GeomFromText(:wkt, 4326), 3083)
                   )) as perimeter_m,
                   ST_Area(ST_Intersection(
                       ST_Transform(rw.geom, 3083),
                       ST_Transform(ST_GeomFromText(:wkt, 4326), 3083)
                   )) as area_m2
            FROM radcorp_water rw
            WHERE rw.ftype_str = 'LakePond'
              AND ST_Intersects(rw.geom, ST_GeomFromText(:wkt, 4326))
              AND rw.acres > 12
        """)
        res = await session.execute(sql, {"wkt": target_wkt})
        rows = res.fetchall()
        total_perimeter_ft = 0.0
        total_area_acres = 0.0
        count = 0
        for acres, perim_m, area_m in rows:
            if area_m > 0:
                count += 1
                total_area_acres += (area_m / 4046.86)
                if perim_m:
                    total_perimeter_ft += (perim_m * 3.28084)

        return {
            "intersects": count > 0,
            "lake_area_acres": round(total_area_acres, 2),
            "lake_perimeter_ft": round(total_perimeter_ft, 2),
            "unique_lake_count": count
        }
    async def analyze_streams(self,session: AsyncSession, gid: Optional[int] = None, geom: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculates total length of streams intersecting the property.
        Uses `public.stream` table.
        """
        target_wkt, _ = await self._get_target_geometry(session, gid, geom)
        sql = text("""
            SELECT ST_Length(
                ST_Intersection(
                    ST_Transform(s.geom, 3083), 
                    ST_Transform(ST_GeomFromText(:wkt, 4326), 3083)
                )
            ) as length_m
            FROM stream s
            WHERE ST_Intersects(s.geom, ST_GeomFromText(:wkt, 4326))
        """)
        res = await session.execute(sql, {"wkt": target_wkt})
        rows = res.scalars().all()
        total_m = sum(r for r in rows if r)
        total_ft = total_m * 3.28084
        return {
            "intersects": total_ft > 0,
            "stream_length_ft": round(total_ft, 2)
        }
    async def analyze_flood_hazard(self,session: AsyncSession, gid: Optional[int] = None, geom: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyzes FEMA Flood Hazard zones intersection.
        """
        target_wkt, _ = await self._get_target_geometry(session, gid, geom)
        area_sql = text("SELECT ST_Area(ST_Transform(ST_GeomFromText(:wkt, 4326), 3083))")
        total_m2 = (await session.execute(area_sql, {"wkt": target_wkt})).scalar() or 0.0
        total_acres = total_m2 / 4046.86
        sql = text("""
            SELECT fh.fld_zone, 
                   ST_Area(ST_Transform(ST_Intersection(fh.geom, ST_GeomFromText(:wkt, 4326)), 3083)) as area_m2
            FROM tx_fld_haz fh
            WHERE ST_Intersects(fh.geom, ST_GeomFromText(:wkt, 4326))
        """)

        res = await session.execute(sql, {"wkt": target_wkt})
        rows = res.fetchall()

        flood_zones = defaultdict(float)
        hazardous_area_acres = 0.0

        for zone, area_m in rows:
            if area_m > 0 and zone != 'X':
                ac = area_m / 4046.86
                flood_zones[zone] += ac
                hazardous_area_acres += ac

        results = []
        for zone, acres in flood_zones.items():
            results.append({
                "flood_zone": zone,
                "area_acres": round(acres, 2),
                "percentage": round((acres / total_acres * 100), 2) if total_acres > 0 else 0
            })

        cleared = max(total_acres - hazardous_area_acres, 0)
        
        # Determine primary zone (simplified)
        primary_zone = results[0]["flood_zone"] if results else "X"

        return {
            "intersects": len(results) > 0,
            "flood_zone_summary": primary_zone,
            "total_flood_acres": round(hazardous_area_acres, 2),
            "cleared_area_acres": round(cleared, 2),
            "details": results
        }

    # ---------------------------------------------------------
    # 7. Sea/Ocean Analysis
    # ---------------------------------------------------------
    async def analyze_sea_ocean(
        self, 
        session: AsyncSession, 
        gid: Optional[int] = None, 
        geom: Optional[str] = None
    ) -> Dict[str, Any]:
        """Calculates intersection length with Sea/Ocean boundaries."""
        target_wkt, _ = await self._get_target_geometry(session, gid, geom)

        # Uses table 'texas_sea_ocean_project' (mapped as SeaOcean model)
        sql = text("""
            SELECT ST_Length(ST_Intersection(
                ST_Transform(s.geom, 3083),
                ST_Transform(ST_GeomFromText(:wkt, 4326), 3083)
            ))
            FROM texas_sea_ocean_project s
            WHERE ST_Intersects(s.geom, ST_GeomFromText(:wkt, 4326))
        """)

        res = await session.execute(sql, {"wkt": target_wkt})
        rows = res.scalars().all()
        total_ft = sum(r for r in rows if r) * 3.28084

        return {
            "intersects": total_ft > 0,
            "sea_ocean_length_ft": round(total_ft, 2)
        }

    # ---------------------------------------------------------
    # 8. Shoreline Types
    # ---------------------------------------------------------
    async def analyze_shoreline(
        self, 
        session: AsyncSession, 
        gid: Optional[int] = None, 
        geom: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Aggregates shoreline lengths from Wetlands (Riverine, Lake) 
        and WaterBodies (Sea/Ocean).
        """
        target_wkt, _ = await self._get_target_geometry(session, gid, geom)

        sql = text("""
            WITH parcel_geom AS (
                SELECT ST_Transform(ST_GeomFromText(:wkt, 4326), 3083) as geom
            ),
            wetland_lengths AS (
                SELECT w.wetland_type, ST_Length(ST_Intersection(p.geom, ST_Transform(w.geom, 3083))) as len_m
                FROM wetlands w, parcel_geom p
                WHERE ST_Intersects(w.geom, ST_GeomFromText(:wkt, 4326))
                AND w.wetland_type IN ('Riverine', 'Lake')
            ),
            beach_lengths AS (
                SELECT ST_Length(ST_Intersection(p.geom, ST_Transform(wb.geom, 3083))) as len_m
                FROM tx_water_bodies wb, parcel_geom p
                WHERE ST_Intersects(wb.geom, ST_GeomFromText(:wkt, 4326))
                AND wb.body_typ = 'Sea/Ocean'
            )
            SELECT 'wetland', wetland_type, len_m FROM wetland_lengths
            UNION ALL
            SELECT 'beach', 'beach', len_m FROM beach_lengths
        """)

        res = await session.execute(sql, {"wkt": target_wkt})
        
        totals = {"riverine": 0.0, "lake": 0.0, "beach": 0.0}
        
        for source, type_, len_m in res.fetchall():
            if not len_m: continue
            ft = len_m * 3.28084
            
            if source == 'beach':
                totals["beach"] += ft
            elif type_ == 'Riverine':
                totals["riverine"] += ft
            elif type_ == 'Lake':
                totals["lake"] += ft

        return {k + "_length_ft": round(v, 2) for k, v in totals.items()}