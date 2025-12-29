import os
import asyncio
import logging
import pandas as pd
import uuid
from io import BytesIO
from typing import Any, Dict, List, Tuple, Optional, Callable
from datetime import datetime
from fastapi import UploadFile

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

from db import SessionLocal
from models.job import BatchJob, JobStatus, JobPriority
from .parcel_analysis import AnalysisService

batch_logger = logging.getLogger("batch_analysis")

class BatchService:
    _instance: Optional["BatchService"] = None
    analysis_service: Optional[AnalysisService] = None

    def __new__(cls) -> "BatchService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.analysis_service = AnalysisService()
        return cls._instance

    async def submit_job_to_celery(
        self,
        file: UploadFile,
        db: AsyncSession,
        user_id: str,
        username: str,
        column_mapping: Optional[Dict[str, str]] = None,
        priority: JobPriority = JobPriority.NORMAL,
        dry_run: bool = False
    ) -> BatchJob:
        
        job_id = uuid.uuid4().hex
        
        # Save file
        temp_dir = os.getenv("UPLOAD_DIR", "/tmp/uploads")
        os.makedirs(temp_dir, exist_ok=True)
        file_path = os.path.join(temp_dir, f"{job_id}_{file.filename}")
        
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        # Create DB Record
        new_job = BatchJob(
            job_id=job_id,
            user_id=user_id,
            username=username,
            filename=file.filename,
            status=JobStatus.QUEUED,
            priority=priority,
            created_at=datetime.utcnow()
        )
        db.add(new_job)
        await db.commit()
        await db.refresh(new_job)

        # Lazy Import to prevent circular dependency
        from worker import run_batch_analysis_task 
        
        # --- PRIORITY QUEUE LOGIC ---
        # Map JobPriority enum to Celery queue names
        queue_name = "normal"
        if priority == JobPriority.HIGH:
            queue_name = "high"
        elif priority == JobPriority.LOW:
            queue_name = "low"
        
        run_batch_analysis_task.apply_async(
            args=[job_id, file_path, column_mapping, user_id, dry_run],
            task_id=job_id,
            queue=queue_name  # Send to specific priority queue
        )

        return new_job

    async def _fetch_gids_bulk(self, points: List[Tuple[int, float, float]], db: AsyncSession) -> Dict[int, int]:
        results: Dict[int, int] = {}
        BATCH_SIZE = 1000  

        for i in range(0, len(points), BATCH_SIZE):
            chunk = points[i : i + BATCH_SIZE]
            values_list = [f"({idx}, {lat}, {lon})" for idx, lat, lon in chunk]
            if not values_list: continue
            
            sql = text(f"""
                WITH input_points(id, lat, lon) AS (VALUES {",".join(values_list)})
                SELECT i.id, p.gid FROM input_points i
                JOIN parcels p ON ST_Contains(p.geom, ST_SetSRID(ST_Point(i.lon, i.lat), 4326))
            """)
            try:
                res = await db.execute(sql)
                for r in res.fetchall():
                    results[int(r[0])] = int(r[1])
            except Exception as e:
                batch_logger.error(f"Bulk GID fetch failed: {e}")
        return results

    async def analyze_file(
        self,
        file_path: str,
        db: AsyncSession,
        job_id: str,
        column_mapping: Optional[Dict[str, str]] = None, 
        dry_run: bool = False,
        progress_callback: Optional[Callable[[int, int], Any]] = None
    ) -> Dict[str, Any]:
        
        try:
            with open(file_path, "rb") as f:
                file_bytes = f.read()
            
            filename = os.path.basename(file_path)
            ext = filename.lower().rsplit(".", 1)[-1]
            if ext in ("xlsx", "xls"):
                df = pd.read_excel(BytesIO(file_bytes), engine="openpyxl").fillna("")
            else:
                df = pd.read_csv(BytesIO(file_bytes)).fillna("")
        except Exception as e:
            raise ValueError(f"File parsing failed: {e}")

        if column_mapping:
            clean_map = {k.strip(): v.strip() for k, v in column_mapping.items() if k and v}
            df = df.rename(columns=clean_map)

        col_map = {}
        for col in df.columns:
            cl = col.lower()
            if cl in ["latitude", "lat"] and "PropertyLatitude" not in df.columns:
                col_map[col] = "PropertyLatitude"
            elif cl in ["longitude", "lon", "lng"] and "PropertyLongitude" not in df.columns:
                col_map[col] = "PropertyLongitude"
        if col_map:
            df = df.rename(columns=col_map)
        
        total_rows = len(df)
        
        points = []
        for idx, row in df.iterrows():
            try:
                points.append((int(idx), float(row["PropertyLatitude"]), float(row["PropertyLongitude"])))
            except: continue
            
        gid_map = await self._fetch_gids_bulk(points, db)

        sem = asyncio.Semaphore(15) 
        completed_count = 0
        
        async def _process_row(idx: int, row_data: Dict):
            nonlocal completed_count
            async with sem:
                gid = gid_map.get(int(idx))
                result_data = row_data
                
                try:
                    if not gid:
                        result_data["error"] = "No parcel found"
                    else:
                        async with SessionLocal() as session:
                            res = await self.analysis_service.get_analysis(
                                gid=gid, 
                                db=session, 
                                processing_mode="batch", 
                                batch_id=job_id, 
                                generate_images=(not dry_run),
                                csv_context=row_data
                            )
                            result_data["analysis"] = res
                except Exception as e:
                    result_data["error"] = str(e)

                completed_count += 1
                if progress_callback:
                    try:
                        await progress_callback(completed_count, total_rows)
                    except: pass
                
                return result_data

        tasks = [asyncio.create_task(_process_row(i, row.to_dict())) for i, row in df.iterrows()]
        results = await asyncio.gather(*tasks)

        return {"results": results, "batch_id": job_id}

    def flatten_analysis_results(self, results: List[Dict]) -> List[Dict]:
        flattened = []
        for row in results:
            flat = {k: v for k, v in row.items() if k != "analysis"}
            analysis = row.get("analysis", {})
            if analysis:
                flat.update(analysis.get("parcels", {}))
                flat["road_frontage_ft"] = analysis.get("road_analysis", {}).get("road_frontage_feet", 0)
                flat["buildable_acres"] = analysis.get("buildable_area", {}).get("buildable_acres", 0)
                flat["unbuildable_acres"] = analysis.get("buildable_area", {}).get("unbuildable_acres", 0)
                flat["elevation_change_ft"] = analysis.get("elevation_change", {}).get("elevation_change_feet", 0)
                flat["tree_coverage_pct"] = analysis.get("tree_coverage", {}).get("tree_percentage", 0)
                flat["flood_zone"] = analysis.get("flood_hazard", {}).get("flood_zone_summary", "X")
                flat["wetland_acres"] = sum([w.get("area_acres", 0) for w in analysis.get("wetland_analysis", {}).get("wetland_analysis", [])])
                flat["has_water_well"] = analysis.get("well_analysis", {}).get("intersects", False)
                flat["gas_pipeline"] = analysis.get("gas_lines", {}).get("intersects", False)
                flat["electric_lines"] = analysis.get("electric_lines", {}).get("intersects", False)
                flat["img_parcel"] = analysis.get("image_url")
                flat["img_flood"] = analysis.get("flood_image_url")
                flat["img_topo"] = analysis.get("contour_image_url")
            flattened.append(flat)
        return flattened