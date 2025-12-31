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
    analysis_service: Optional[AnalysisService] = AnalysisService()

    def __new__(cls) -> "BatchService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.analysis_service = AnalysisService()
        return cls._instance

    async def create_job_with_file(
        self,
        file: UploadFile,
        db: AsyncSession,
        user_id: str,
        username: str,
        priority: JobPriority = JobPriority.NORMAL
    ) -> Tuple[BatchJob, str]:
        """
        Saves the uploaded file and creates the initial Job record.
        Returns the job object and the path to the saved file.
        """
        job_id = uuid.uuid4().hex
        temp_dir = os.getenv("UPLOAD_DIR", "/tmp/uploads")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Save file locally
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
        
        return new_job, file_path

    async def process_job_background(
        self, 
        job_id: str, 
        file_path: str, 
        column_mapping: Optional[Dict[str, str]], 
        dry_run: bool
    ):
        """
        Background task logic: updates status, runs analysis, saves CSV.
        Replaces the old Celery worker logic.
        """
        async def on_progress(completed, total):
            # Update DB every 10 rows or at finish
            if completed % 10 == 0 or completed == total:
                async with SessionLocal() as db:
                    job = await db.get(BatchJob, job_id)
                    # Stop updating if cancelled
                    if job and job.status != JobStatus.CANCELLED:
                        job.completed_rows = completed
                        job.total_rows = total
                        db.add(job)
                        await db.commit()

        async with SessionLocal() as db:
            try:
                # 1. Start Processing
                job = await db.get(BatchJob, job_id)
                if not job or job.status == JobStatus.CANCELLED:
                    return

                job.status = JobStatus.PROCESSING
                job.started_at = datetime.utcnow()
                db.add(job)
                await db.commit()

                # 2. Run Analysis
                result = await self.analyze_file(
                    file_path=file_path,
                    db=db,
                    job_id=job_id,
                    column_mapping=column_mapping,
                    dry_run=dry_run,
                    progress_callback=on_progress
                )

                # 3. Check Cancellation before saving
                await db.refresh(job)
                if job.status == JobStatus.CANCELLED:
                    return

                # 4. Save Results to CSV
                flattened = self.flatten_analysis_results(result["results"])
                df = pd.DataFrame(flattened)
                
                output_dir = "/tmp/exports"
                os.makedirs(output_dir, exist_ok=True)
                output_path = f"{output_dir}/results_{job_id}.csv"
                df.to_csv(output_path, index=False)

                # 5. Complete Job
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.utcnow()
                job.completed_rows = len(flattened)
                job.total_rows = len(flattened)
                job.result_url = output_path
                db.add(job)
                await db.commit()

            except Exception as e:
                batch_logger.error(f"Job {job_id} failed: {e}")
                # Rollback and mark failed
                await db.rollback()
                async with SessionLocal() as err_db:
                    job = await err_db.get(BatchJob, job_id)
                    if job and job.status != JobStatus.CANCELLED:
                        job.status = JobStatus.FAILED
                        job.error_message = f"Processing Error: {str(e)}"
                        job.completed_at = datetime.utcnow()
                        err_db.add(job)
                        await err_db.commit()
            finally:
                # Cleanup input file
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except:
                        pass

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
                        # Note: We create a new session per row or share one?
                        # Sharing 'db' passed in is unsafe if concurrency is high and asyncpg driver limits.
                        # Using SessionLocal() per row is safer for concurrent gathered tasks.
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