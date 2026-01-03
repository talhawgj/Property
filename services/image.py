import os
import json
import logging
import time
import uuid
import hashlib
import base64
import asyncio
from io import BytesIO
from typing import Dict, Optional, Union, Tuple, List, Any
import boto3
import numpy as np
import rasterio
from rasterio.mask import mask
from PIL import Image
import folium
import geopandas as gpd
from shapely.geometry import shape, mapping
from shapely import wkt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text
from botocore.exceptions import ClientError
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utils.webdriver_pool import WebDriverPool
from config import config

logger = logging.getLogger(__name__)

class ImageService:
    """
    Centralized service for generating GIS analysis images.
    Optimized for high concurrency using WebDriverPool and in-memory rendering.
    """

    def __init__(self):
        self.s3_bucket = "radcorp-images11"
        self.s3_region = "eu-north-1"
        self.s3_base_url = f"https://{self.s3_bucket}.s3.{self.s3_region}.amazonaws.com"
        self.dem_path = os.environ.get("ELEVATION_FILE", "/mnt/land200/gis-data/tx_terrain/Texas_DEM.vrt")
        self.tree_path = os.environ.get("TREE_COVERAGE_PATH", "/mnt/land200/gis-data/tx_treecoverage")
        self._s3_client = None

    @property
    def s3(self):
        if self._s3_client is None:
            self._s3_client = boto3.client(
                "s3",
                region_name=self.s3_region,
                aws_access_key_id=config.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
            )
        return self._s3_client

    def _get_s3_key(self, gid: Optional[int], folder_name: str, geom_str: Optional[str] = None) -> str:
        if gid:
            return f"parcels/{gid}/{folder_name}_{gid}.png"
        elif geom_str:
            geom_hash = hashlib.md5(geom_str.encode('utf-8')).hexdigest()
            return f"temp/{folder_name}/{geom_hash}.png"
        else:
            return f"temp/{folder_name}/{uuid.uuid4().hex}.png"
    async def _handle_cache_or_generate( self, session: AsyncSession,gid: Optional[int], folder_name: str, generate_func: callable, geom_input: Optional[str] = None) -> Union[str, Dict[str, Any]]:
        s3_key = self._get_s3_key(gid, folder_name, geom_input)
        if not geom_input and gid:
            try:
                self.s3.head_object(Bucket=self.s3_bucket, Key=s3_key)
                return f"{self.s3_base_url}/{s3_key}"
            except ClientError as e:
                if e.response['Error']['Code'] != "404":
                    raise
        result = await generate_func(session, gid, geom_input)
        if isinstance(result, dict):
            return result
        self.s3.upload_fileobj(
            result, 
            self.s3_bucket, 
            s3_key, 
            ExtraArgs={"ContentType": "image/png"}
        )
        
        return f"{self.s3_base_url}/{s3_key}"

    async def _get_geometry_and_bounds( self, session: AsyncSession, gid: Optional[int] = None, geom_input: Optional[str] = None) -> Tuple[Any, List[float], int]:
        shapely_geom = None
        srid = 4326
        if geom_input:
            try:
                input_str = geom_input.strip()
                if input_str.startswith("{"):
                    data = json.loads(input_str)
                    shapely_geom = shape(data)
                else:
                    shapely_geom = wkt.loads(input_str)
            except Exception as e:
                raise ValueError(f"Invalid geometry input: {e}")

        elif gid:
            query = text("SELECT ST_AsGeoJSON(ST_Transform(geom, 4326)) FROM parcels WHERE gid = :gid")
            result = await session.execute(query, {"gid": gid})
            row = result.fetchone()
            if not row:
                raise ValueError(f"Parcel GID {gid} not found.")
            shapely_geom = shape(json.loads(row[0]))

        else:
            raise ValueError("Either 'gid' or 'geom_input' must be provided.")

        return shapely_geom, shapely_geom.bounds, srid

    def _create_base_map(self, bounds: List[float], padding: int = 100) -> folium.Map:
        minx, miny, maxx, maxy = bounds
        center_lat = (miny + maxy) / 2
        center_lon = (minx + maxx) / 2

        m = folium.Map(
            location=[center_lat, center_lon],
            tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
            attr="Google Satellite",
            zoom_control=False,
            attribution_control=False,
            no_touch=True
        )
        m.fit_bounds([[miny, minx], [maxy, maxx]], padding=(padding, padding))
        return m

    def _add_legend(self, m: folium.Map, items: List[str]):
        legend_content = "<br>".join(items)
        html = f"""
        <div style="
            position: fixed; bottom: 10px; right: 10px;
            background-color: rgba(255, 255, 255, 0.8);
            border-radius: 5px; padding: 10px; font-size: 12px; z-index: 1000;
        ">
            <strong>Legend</strong><br>
            {legend_content}
        </div>
        """
        m.get_root().html.add_child(folium.Element(html))
        m.get_root().html.add_child(folium.Element("""
            <style>
                .leaflet-container { opacity: 1 !important; background: none !important; }
                .leaflet-control-container, .leaflet-control-attribution { display: none !important; }
            </style>
        """))

    async def _render_and_screenshot(self, m: folium.Map, gid_ref: str) -> BytesIO:
        """
        Optimized renderer:
        1. Acquires driver from Pool (no startup cost).
        2. Injects HTML via Base64 (no disk write).
        3. Returns BytesIO directly (no disk read).
        """
        pool = WebDriverPool.get_instance()
        html_content = m.get_root().render()
        b64_html = base64.b64encode(html_content.encode('utf-8')).decode('utf-8')
        data_uri = f"data:text/html;base64,{b64_html}"
        async with pool.acquire() as driver:
            def _blocking_selenium_logic(d):
                d.set_window_size(800, 600)
                d.get(data_uri)
                WebDriverWait(d, 5).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "leaflet-container"))
                )
                time.sleep(3) 
                return d.get_screenshot_as_png()
            png_bytes = await asyncio.to_thread(_blocking_selenium_logic, driver)
            with Image.open(BytesIO(png_bytes)) as img:
                img = img.convert("RGB")
                buf = BytesIO()
                img.save(buf, format="PNG", optimize=True)
                buf.seek(0)
                return buf
    async def get_parcel_image(self, session: AsyncSession, gid: Optional[int] = None, geom: Optional[str] = None) -> Union[str, Dict]:
        return await self._handle_cache_or_generate(session, gid, "aerial", self._gen_parcel, geom)

    async def get_road_frontage_image(self, session: AsyncSession, gid: Optional[int] = None, geom: Optional[str] = None) -> Union[str, Dict]:
        return await self._handle_cache_or_generate(session, gid, "road_frontage", self._gen_road, geom)

    async def get_flood_image(self, session: AsyncSession, gid: Optional[int] = None, geom: Optional[str] = None) -> Union[str, Dict]:
        return await self._handle_cache_or_generate(session, gid, "flood_hazard", self._gen_flood, geom)

    async def get_tree_image(self, session: AsyncSession, gid: Optional[int] = None, geom: Optional[str] = None) -> Union[str, Dict]:
        return await self._handle_cache_or_generate(session, gid, "tree_coverage", self._gen_tree, geom)

    async def get_contour_image(self, session: AsyncSession, gid: Optional[int] = None, geom: Optional[str] = None) -> Union[str, Dict]:
        return await self._handle_cache_or_generate(session, gid, "contour", self._gen_contour, geom)

    async def get_water_image(self, session: AsyncSession, gid: Optional[int] = None, geom: Optional[str] = None) -> Union[str, Dict]:
        return await self._handle_cache_or_generate(session, gid, "water_features", self._gen_water, geom)

    async def get_pipeline_image(self, session: AsyncSession, gid: Optional[int] = None, geom: Optional[str] = None) -> Union[str, Dict]:
        return await self._handle_cache_or_generate(session, gid, "gas_pipelines", self._gen_pipeline, geom)

    async def get_electric_image(self, session: AsyncSession, gid: Optional[int] = None, geom: Optional[str] = None) -> Union[str, Dict]:
        return await self._handle_cache_or_generate(session, gid, "electric_lines", self._gen_electric, geom)
    async def _gen_parcel(self, session: AsyncSession, gid: Optional[int], geom: Optional[str] = None) -> BytesIO:
        shapely_geom, bounds, _ = await self._get_geometry_and_bounds(session, gid, geom)
        m = self._create_base_map(bounds)
        folium.GeoJson(
            gpd.GeoDataFrame(geometry=[shapely_geom], crs="EPSG:4326"),
            style_function=lambda x: {'color': 'red', 'weight': 3, 'fillOpacity': 0, 'opacity': 1}
        ).add_to(m)
        self._add_legend(m, ["<svg width='16' height='16' style='vertical-align:middle;margin-right:6px;'><polygon points='2,2 14,2 14,14 2,14' style='fill:none;stroke:red;stroke-width:2'/></svg> Property Boundary"])
        return await self._render_and_screenshot(m, str(gid) if gid else "geom")
    
    async def _gen_road(self, session: AsyncSession, gid: Optional[int], geom: Optional[str] = None) -> Union[BytesIO, Dict]:
        shapely_geom, bounds, _ = await self._get_geometry_and_bounds(session, gid, geom)
        wkt_str = shapely_geom.wkt
        sql = text("""
            SELECT ST_AsGeoJSON(geom) 
        FROM public.osm_roads
        WHERE ST_DWithin(
            geom_3083, 
            ST_Transform(ST_SetSRID(ST_GeomFromText(:wkt), 4326), 3083), 
            50
        )        """)
        result = await session.execute(sql, {"wkt": wkt_str})
        rows = result.fetchall()

        if not rows:
            return {"message": "No road frontage detected within 50m.", "status": "no_data"}

        m = self._create_base_map(bounds)
        folium.GeoJson(gpd.GeoDataFrame(geometry=[shapely_geom], crs="EPSG:4326"), style_function=lambda x: {'color': 'red', 'weight': 3, 'fillOpacity': 0}).add_to(m)
        
        for row in rows:
            road_geom = shape(json.loads(row[0]))
            folium.GeoJson(gpd.GeoDataFrame(geometry=[road_geom], crs="EPSG:4326"), style_function=lambda x: {'color': 'green', 'weight': 3, 'opacity': 0.8}).add_to(m)
        
        self._add_legend(m, [
            "<svg width='16' height='16' style='vertical-align:middle;margin-right:6px;'><polygon points='2,2 14,2 14,14 2,14' style='fill:none;stroke:red;stroke-width:2'/></svg> Property Boundary",
            "<svg width='16' height='16' style='vertical-align:middle;margin-right:6px;'><line x1='2' y1='8' x2='14' y2='8' style='stroke:green;stroke-width:3'/></svg> Nearby Roads"
        ])
        return await self._render_and_screenshot(m, str(gid) if gid else "geom")

    async def _gen_flood(self, session: AsyncSession, gid: Optional[int], geom: Optional[str] = None) -> Union[BytesIO, Dict]:
        shapely_geom, bounds, _ = await self._get_geometry_and_bounds(session, gid, geom)
        
        sql = text("""SELECT ST_AsGeoJSON(ST_Transform(geom, 4326)), fld_zone FROM tx_fld_haz WHERE ST_Intersects(geom, ST_SetSRID(ST_GeomFromText(:wkt, 4326), 4326))""")
        result = await session.execute(sql, {"wkt": shapely_geom.wkt})
        rows = result.fetchall()
        
        # Filter hazardous zones
        hazardous = [r for r in rows if r[1] not in ['AREA NOT INCLUDED', 'OPEN WATER', 'X']]
        
        if not hazardous:
            return {"message": "No flood hazards detected on property.", "status": "no_data"}

        m = self._create_base_map(bounds)
        colors = {'A': '#0000FF', 'AE': '#4169E1', 'AH': '#87CEEB', 'AO': '#00CED1', 'VE': '#1E90FF', 'X_0.2PCT': '#006400', 'X_MINIMAL': '#90EE90'}
        
        for row in hazardous:
            color = colors.get(row[1], '#808080')
            folium.GeoJson(gpd.GeoDataFrame(geometry=[shape(json.loads(row[0]))], crs="EPSG:4326"), style_function=lambda x, c=color: {'color': c, 'fillColor': c, 'weight': 1, 'fillOpacity': 0.5}).add_to(m)
        
        folium.GeoJson(gpd.GeoDataFrame(geometry=[shapely_geom], crs="EPSG:4326"), style_function=lambda x: {'color': 'red', 'weight': 3, 'fillOpacity': 0}).add_to(m)
        self._add_legend(m, ["<svg width='16' height='16' style='vertical-align:middle;margin-right:6px;'><polygon points='2,2 14,2 14,14 2,14' style='fill:none;stroke:red;stroke-width:2'/></svg> Property Boundary", "<svg width='16' height='16' style='vertical-align:middle;margin-right:6px;'><rect x='2' y='2' width='12' height='12' style='fill:#4169E1;stroke:#4169E1;stroke-width:2'/></svg> Flood Zones"])
        return await self._render_and_screenshot(m, str(gid) if gid else "geom")

    async def _gen_pipeline(self, session: AsyncSession, gid: Optional[int], geom: Optional[str] = None) -> Union[BytesIO, Dict]:
        shapely_geom, bounds, _ = await self._get_geometry_and_bounds(session, gid, geom)
        
        sql = text("SELECT ST_AsGeoJSON(ST_Transform(geom, 4326)) FROM gas_pipelines WHERE ST_Intersects(geom, ST_SetSRID(ST_GeomFromText(:wkt, 4326), 4326))")
        res = await session.execute(sql, {"wkt": shapely_geom.wkt})
        rows = res.fetchall()

        if not rows:
            return {"message": "No gas pipelines detected.", "status": "no_data"}

        m = self._create_base_map(bounds)
        for row in rows:
            folium.GeoJson(gpd.GeoDataFrame(geometry=[shape(json.loads(row[0]))], crs="EPSG:4326"), style_function=lambda x: {'color': 'orange', 'weight': 3, 'dashArray': '5, 5'}).add_to(m)
        
        folium.GeoJson(gpd.GeoDataFrame(geometry=[shapely_geom], crs="EPSG:4326"), style_function=lambda x: {'color': 'red', 'weight': 3, 'fillOpacity': 0}).add_to(m)
        self._add_legend(m, ["<svg width='16' height='16' style='vertical-align:middle;margin-right:6px;'><polygon points='2,2 14,2 14,14 2,14' style='fill:none;stroke:red;stroke-width:2'/></svg> Property Boundary", "<svg width='16' height='16' style='vertical-align:middle;margin-right:6px;'><line x1='2' y1='8' x2='14' y2='8' style='stroke:orange;stroke-width:3;stroke-dasharray:5,5'/></svg> Gas Pipeline"])
        return await self._render_and_screenshot(m, str(gid) if gid else "geom")

    async def _gen_electric(self, session: AsyncSession, gid: Optional[int], geom: Optional[str] = None) -> Union[BytesIO, Dict]:
        shapely_geom, bounds, _ = await self._get_geometry_and_bounds(session, gid, geom)
        sql = text("SELECT ST_AsGeoJSON(ST_Transform(geom, 4326)) FROM electric_transmission_lines WHERE ST_Intersects(geom, ST_SetSRID(ST_GeomFromText(:wkt, 4326), 4326))")
        res = await session.execute(sql, {"wkt": shapely_geom.wkt})
        rows = res.fetchall()
        if not rows:
            return {"message": "No electric transmission lines detected.", "status": "no_data"}
        m = self._create_base_map(bounds)
        for row in rows:
            folium.GeoJson(gpd.GeoDataFrame(geometry=[shape(json.loads(row[0]))], crs="EPSG:4326"), style_function=lambda x: {'color': 'yellow', 'weight': 3}).add_to(m)
        folium.GeoJson(gpd.GeoDataFrame(geometry=[shapely_geom], crs="EPSG:4326"), style_function=lambda x: {'color': 'red', 'weight': 3, 'fillOpacity': 0}).add_to(m)
        self._add_legend(m, ["<svg width='16' height='16' style='vertical-align:middle;margin-right:6px;'><polygon points='2,2 14,2 14,14 2,14' style='fill:none;stroke:red;stroke-width:2'/></svg> Property Boundary", "<svg width='16' height='16' style='vertical-align:middle;margin-right:6px;'><line x1='2' y1='8' x2='14' y2='8' style='stroke:yellow;stroke-width:3'/></svg> Electric Line"])
        return await self._render_and_screenshot(m, str(gid) if gid else "geom")
    
    async def _gen_tree(self, session: AsyncSession, gid: Optional[int], geom: Optional[str] = None) -> Union[BytesIO, Dict]:
        shapely_geom, bounds, _ = await self._get_geometry_and_bounds(session, gid, geom)
        has_trees = False
        m = self._create_base_map(bounds)
        if os.path.exists(self.tree_path):
            try:
                gdf = gpd.GeoDataFrame(geometry=[shapely_geom], crs="EPSG:4326").to_crs(epsg=3857)
                proj_geom = gdf.geometry[0]
                bbox = proj_geom.bounds
                for f in os.listdir(self.tree_path):
                    if f.endswith(".tif"):
                        fpath = os.path.join(self.tree_path, f)
                        with rasterio.open(fpath) as src:
                            if not (src.bounds.right < bbox[0] or src.bounds.left > bbox[2] or src.bounds.bottom > bbox[3] or src.bounds.top < bbox[1]):
                                try:
                                    out_image, _ = mask(src, [mapping(proj_geom)], crop=True, nodata=0)
                                    if np.any(out_image[0] > 1):
                                        has_trees = True
                                        data = out_image[0]
                                        mask_arr = data > 1
                                        rgba = np.zeros((mask_arr.shape[0], mask_arr.shape[1], 4), dtype=np.uint8)
                                        rgba[mask_arr] = [0, 100, 0, 153]
                                        img_buf = BytesIO()
                                        Image.fromarray(rgba).save(img_buf, format='PNG')
                                        img_b64 = base64.b64encode(img_buf.getvalue()).decode('utf-8')
                                        img_uri = f"data:image/png;base64,{img_b64}"

                                        folium.raster_layers.ImageOverlay(
                                            img_uri, 
                                            bounds=[[bounds[1], bounds[0]], [bounds[3], bounds[2]]], 
                                            opacity=0.6
                                        ).add_to(m)
                                        break
                                except: continue
            except Exception: pass

        if not has_trees:
            return {"message": "No significant tree coverage detected.", "status": "no_data"}

        folium.GeoJson(gpd.GeoDataFrame(geometry=[shapely_geom], crs="EPSG:4326"), style_function=lambda x: {'color': 'red', 'weight': 3, 'fillOpacity': 0}).add_to(m)
        self._add_legend(m, ["<svg width='16' height='16' style='vertical-align:middle;margin-right:6px;'><polygon points='2,2 14,2 14,14 2,14' style='fill:none;stroke:red;stroke-width:2'/></svg> Property Boundary", "<svg width='16' height='16' style='vertical-align:middle;margin-right:6px;'><rect x='2' y='2' width='12' height='12' style='fill:#006400;stroke:#006400;stroke-width:2'/></svg> Tree Coverage"])
        return await self._render_and_screenshot(m, str(gid) if gid else "geom")

    async def _gen_contour(self, session: AsyncSession, gid: Optional[int], geom: Optional[str] = None) -> Union[BytesIO, Dict]:
        shapely_geom, bounds, _ = await self._get_geometry_and_bounds(session, gid, geom)
        sql = text("""SELECT ST_AsGeoJSON(ST_Transform(shape, 4326)), contourelevation FROM tx_contour WHERE ST_Intersects(shape, ST_Buffer(ST_SetSRID(ST_GeomFromText(:wkt, 4326), 4326)::geography, 20)::geometry)""")
        result = await session.execute(sql, {"wkt": shapely_geom.wkt})
        rows = result.fetchall()
        
        if not rows:
            return {"message": "No contour lines detected.", "status": "no_data"}

        m = self._create_base_map(bounds)
        for row in rows:
            c_geom = shape(json.loads(row[0]))
            folium.GeoJson(gpd.GeoDataFrame(geometry=[c_geom], crs="EPSG:4326"), style_function=lambda x: {'color': '#8B4513', 'weight': 2}).add_to(m)
        
        folium.GeoJson(gpd.GeoDataFrame(geometry=[shapely_geom], crs="EPSG:4326"), style_function=lambda x: {'color': 'red', 'weight': 3, 'fillOpacity': 0}).add_to(m)
        self._add_legend(m, ["<svg width='16' height='16' style='vertical-align:middle;margin-right:6px;'><polygon points='2,2 14,2 14,14 2,14' style='fill:none;stroke:red;stroke-width:2'/></svg> Property Boundary", "<span style='display:inline-block;width:15px;height:0;border-top:3px solid #8B4513;vertical-align:middle;margin-right:6px;'></span> Contour Line"])
        return await self._render_and_screenshot(m, str(gid) if gid else "geom")

    async def _gen_water(self, session: AsyncSession, gid: Optional[int], geom: Optional[str] = None) -> Union[BytesIO, Dict]:
        shapely_geom, bounds, _ = await self._get_geometry_and_bounds(session, gid, geom)
        has_water = False
        m = self._create_base_map(bounds)
        
        for tbl, style in {"radcorp_water": {"c": "blue", "l": "Pond/Lake"}, "stream": {"c": "cyan", "l": "Stream"}}.items():
            sql = text(f"SELECT ST_AsGeoJSON(ST_Transform(geom, 4326)) FROM {tbl} WHERE ST_Intersects(geom, ST_SetSRID(ST_GeomFromText(:wkt, 4326), 4326))")
            res = await session.execute(sql, {"wkt": shapely_geom.wkt})
            rows = res.fetchall()
            if rows:
                has_water = True
                for row in rows:
                    folium.GeoJson(gpd.GeoDataFrame(geometry=[shape(json.loads(row[0]))], crs="EPSG:4326"), style_function=lambda x, c=style['c']: {'color': c, 'fillColor': c, 'fillOpacity': 0.5, 'weight': 2}).add_to(m)
        if not has_water:
            return {"message": "No water features detected.", "status": "no_data"}
        folium.GeoJson(gpd.GeoDataFrame(geometry=[shapely_geom], crs="EPSG:4326"), style_function=lambda x: {'color': 'red', 'weight': 3, 'fillOpacity': 0}).add_to(m)
        self._add_legend(m, ["<svg width='16' height='16' style='vertical-align:middle;margin-right:6px;'><polygon points='2,2 14,2 14,14 2,14' style='fill:none;stroke:red;stroke-width:2'/></svg> Property Boundary", "<span style='color:blue;'>■</span> Water Features"])
        return await self._render_and_screenshot(m, str(gid) if gid else "geom")