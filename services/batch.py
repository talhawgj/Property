import os
import asyncio
import logging
import pandas as pd
import uuid
from io import BytesIO
from typing import Any, Dict, List, Tuple, Optional, Callable
from datetime import datetime, timedelta
from fastapi import UploadFile

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text, select, func

from db import SessionLocal
from models.job import BatchJob, JobStatus, JobPriority
from .parcel_analysis import AnalysisService
from config import config
batch_logger = logging.getLogger("batch_analysis")

class BatchService:
    _instance: Optional["BatchService"] = None
    analysis_service: Optional[AnalysisService] = AnalysisService()

    def __new__(cls) -> "BatchService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.analysis_service = AnalysisService()
        return cls._instance
    async def recover_stuck_jobs(self):
        """
        Runs on startup. Finds jobs that were 'PROCESSING' when the server died
        and marks them as FAILED.
        """
        batch_logger.info("Checking for stuck jobs from previous run...")
        async with SessionLocal() as db:
            result = await db.execute(
                select(BatchJob).where(BatchJob.status == JobStatus.PROCESSING)
            )
            stuck_jobs = result.scalars().all()
            
            for job in stuck_jobs:
                batch_logger.warning(f"Recovering stuck job {job.job_id} -> FAILED")
                job.status = JobStatus.FAILED
                job.error_message = "System Restarted: Job interrupted unexpectedly."
                job.completed_at = datetime.utcnow()
                db.add(job)
            await db.commit()

    async def run_job_scheduler(self):
        """
        Background loop. Picks up QUEUED jobs if we are under the MAX_CONCURRENT_JOBS limit.
        """
        MAX_CONCURRENT_JOBS = 3 
        batch_logger.info("Starting Batch Job Scheduler...")

        while True:
            try:
                async with SessionLocal() as db:
                    count_query = select(func.count()).where(BatchJob.status == JobStatus.PROCESSING)
                    res = await db.execute(count_query)
                    active_count = res.scalar() or 0
                    if active_count < MAX_CONCURRENT_JOBS:
                        slots = MAX_CONCURRENT_JOBS - active_count
                        query = (
                            select(BatchJob)
                            .where(BatchJob.status == JobStatus.QUEUED)
                            .order_by(BatchJob.created_at.asc()) 
                            .limit(slots)
                        )
                        result = await db.execute(query)
                        jobs_to_run = result.scalars().all()

                        for job in jobs_to_run:
                            batch_logger.info(f"Scheduler starting job: {job.job_id}")
                            job.status = JobStatus.PROCESSING
                            job.started_at = datetime.utcnow()
                            db.add(job)
                            await db.commit()
                            asyncio.create_task(self.process_job_background(job.job_id))
            
            except Exception as e:
                batch_logger.error(f"Scheduler Loop Error: {e}")
            await asyncio.sleep(5)
    async def create_job_with_file(self,file: UploadFile,db: AsyncSession, user_id: str,username: str,priority: JobPriority,column_mapping: Optional[Dict],dry_run: bool) -> BatchJob:
        """
        Saves file and creates a QUEUED job record.
        """
        job_id = uuid.uuid4().hex
        temp_dir = os.getenv("UPLOAD_DIR", "/tmp/uploads")
        os.makedirs(temp_dir, exist_ok=True)
        file_path = os.path.join(temp_dir, f"{job_id}_{file.filename}")
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        new_job = BatchJob(
            job_id=job_id,
            user_id=user_id,
            username=username,
            filename=file.filename,
            status=JobStatus.QUEUED,
            priority=priority,
            created_at=datetime.now(),
            file_path=file_path,
            column_mapping=column_mapping or {},
            dry_run=dry_run
        )
        db.add(new_job)
        await db.commit()
        await db.refresh(new_job)
        
        return new_job

    async def process_job_background(self, job_id: str):
        """
        The worker logic. Now fetches details from DB instead of arguments.
        """
        job_state = {"cancelled": False}

        async def on_progress(completed, total, is_success=True):
            if completed % 10 == 0 or completed == total:
                async with SessionLocal() as db:
                    job = await db.get(BatchJob, job_id)
                    if not job: return
                    if job.status == JobStatus.CANCELLED:
                        job_state["cancelled"] = True
                        return
                    job.completed_rows = completed
                    job.total_rows = total
                    if not is_success:
                        job.failed_rows += 1
                    db.add(job)
                    await db.commit()
        async with SessionLocal() as db:
            try:
                job = await db.get(BatchJob, job_id)
                if not job or job.status == JobStatus.CANCELLED:
                    return
                result = await self.analyze_file(
                    file_path=job.file_path,
                    db=db,
                    job_id=job_id,
                    column_mapping=job.column_mapping,
                    dry_run=job.dry_run,
                    progress_callback=on_progress,
                    job_state=job_state # Pass cancellation context
                )
                await db.refresh(job)
                if job.status == JobStatus.CANCELLED:
                    return
                flattened = self.flatten_analysis_results(result["results"])
                df = pd.DataFrame(flattened)
                output_dir = "/tmp/exports"
                os.makedirs(output_dir, exist_ok=True)
                output_path = f"{output_dir}/results_{job_id}.csv"
                df.to_csv(output_path, index=False)
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.utcnow()
                job.completed_rows = len(flattened)
                job.total_rows = len(flattened)
                job.result_url = output_path
                db.add(job)
                await db.commit()

            except Exception as e:
                batch_logger.error(f"Job {job_id} failed: {e}")
                await db.rollback()
                async with SessionLocal() as err_db:
                    job = await err_db.get(BatchJob, job_id)
                    if job and job.status != JobStatus.CANCELLED:
                        job.status = JobStatus.FAILED
                        job.error_message = f"Error: {str(e)}"
                        job.completed_at = datetime.utcnow()
                        err_db.add(job)
                        await err_db.commit()
            finally:
                if job and job.file_path and os.path.exists(job.file_path):
                    try: os.remove(job.file_path)
                    except: pass
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
        progress_callback: Optional[Callable] = None,
        job_state: Optional[Dict] = None
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
        concurrency_limit = config.BATCH_CONCURRENCY if hasattr(config, 'BATCH_CONCURRENCY') else 10
        sem = asyncio.Semaphore(concurrency_limit)
        completed_count = 0
        async def _process_row(idx: int, row_data: Dict):
            nonlocal completed_count
            if job_state and job_state.get("cancelled"):
                return None
            async with sem:
                if job_state and job_state.get("cancelled"):
                    return None
                
                gid = gid_map.get(int(idx))
                result_data = row_data.copy()
                is_success = True
                try:
                    if not gid:
                        result_data["error"] = "No parcel found"
                        is_success = False
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
                    is_success = False

                completed_count += 1
                if progress_callback:
                    try:
                        await progress_callback(completed_count, total_rows, is_success)
                    except: pass
                
                return result_data
        tasks = [asyncio.create_task(_process_row(i, row.to_dict())) for i, row in df.iterrows()]
        results = await asyncio.gather(*tasks)
        results = [r for r in results if r is not None]

        return {"results": results, "batch_id": job_id}

    def flatten_analysis_results(self, results: List[Dict]) -> List[Dict]:
        flattened = []
        for row in results:
            flat = {k: v for k, v in row.items() if k != "analysis"}
            analysis = row.get("analysis", {})
            if analysis and "error" not in analysis:
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