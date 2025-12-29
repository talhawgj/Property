import os
import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Response
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, desc
from celery.result import AsyncResult 

from db import get_session 
from config import config
from models.job import BatchJob, JobStatus, JobPriority
from services import batch_service

# FIX: Explicit import to ensure we get the configured Celery app
from worker.worker import celery_app

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Batch Analysis"])

@router.get("/analyze/{gid}", response_model=Optional[Dict[str, Any]])
async def parcel_analysis(
    gid: int,
    db: AsyncSession = Depends(get_session)
) -> Optional[Dict[str, Any]]:
    """
    Analyze a single parcel immediately (synchronous).
    """
    service = batch_service.analysis_service
    result = await service.get_analysis(gid=gid, db=db)
    return result

@router.post("/analyze/batch", response_model=BatchJob)
async def submit_batch_job(
    file: UploadFile = File(...),
    column_mapping: Optional[str] = Form(None, description='JSON string e.g. {"Lat": "PropertyLatitude"}'),
    priority: JobPriority = Form(JobPriority.NORMAL),
    dry_run: bool = Form(False),
    user_id: str = Form("system"),
    username: str = Form("system"),
    db: AsyncSession = Depends(get_session)
):
    """
    Uploads file -> Creates Job (Queued) -> Dispatches to Celery.
    Returns Job ID immediately.
    """
    if not file.filename or not file.filename.lower().endswith(('.csv', '.xls', '.xlsx')):
        raise HTTPException(status_code=400, detail="Invalid file type. Only CSV or Excel allowed.")
    mapping_dict = {}
    if column_mapping:
        try:
            mapping_dict = json.loads(column_mapping)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON format for column_mapping")

    try:
        new_job = await batch_service.submit_job_to_celery(
            file=file,
            db=db,
            user_id=user_id,
            username=username,
            column_mapping=mapping_dict,
            priority=priority,
            dry_run=dry_run
        )
        return new_job
    except Exception as e:
        logger.error(f"Failed to submit batch job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch/cancel/{job_id}")
async def cancel_job(
    job_id: str, 
    db: AsyncSession = Depends(get_session)
):
    """
    Cancels a job if it is Queued or Processing.
    """
    job = await db.get(BatchJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status in [JobStatus.QUEUED, JobStatus.PROCESSING]:
        celery_app.control.revoke(job_id, terminate=True)
        
        job.status = JobStatus.CANCELLED
        job.error_message = "Cancelled by user"
        job.completed_at = datetime.utcnow()
        db.add(job)
        await db.commit()
        
    return {"status": "cancelled", "job_id": job_id}

@router.get("/batch/progress/{job_id}")
async def get_job_progress(
    job_id: str, 
    db: AsyncSession = Depends(get_session)
):
    """
    Checks DB first (Source of Truth). Only checks Redis if DB says processing.
    """
    # 1. Check DB Status FIRST
    job = await db.get(BatchJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # If done/cancelled, return immediately (ignore Redis)
    if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
        percent = 100 if job.status == JobStatus.COMPLETED else 0
        return {
            "job_id": job_id,
            "status": job.status,
            "progress": {
                "current": job.completed_rows,
                "total": job.total_rows,
                "percent": percent
            },
            "error": job.error_message,
            "result_url": f"/batch/download/{job_id}" if job.status == JobStatus.COMPLETED else None
        }

    # 2. If DB says PROCESSING, check Redis for live real-time updates
    # This captures the updates between the DB commits (every 10 rows)
    try:
        task_result = AsyncResult(job_id, app=celery_app)
        # Ensure we have a valid state AND valid info dictionary
        if task_result.state == 'PROGRESS' and isinstance(task_result.info, dict):
            return {
                "job_id": job_id,
                "status": "processing",
                "progress": task_result.info # {'current': x, 'total': y, 'percent': z}
            }
    except Exception as e:
        logger.warning(f"Failed to fetch Redis progress for {job_id}: {e}")

    # 3. Fallback (Redis empty/failed, use DB values)
    percent = 0
    if job.total_rows > 0:
        percent = int((job.completed_rows / job.total_rows) * 100)

    return {
        "job_id": job_id,
        "status": job.status,
        "progress": {
            "current": job.completed_rows,
            "total": job.total_rows,
            "percent": percent
        },
        "error": job.error_message,
        "result_url": None
    }

@router.get("/batch/download/{job_id}")
async def download_batch_result(
    job_id: str, 
    db: AsyncSession = Depends(get_session)
):
    """
    Downloads the final CSV if available.
    """
    job = await db.get(BatchJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail=f"Job is {job.status}, result not ready.")
    
    if not job.result_url or not os.path.exists(job.result_url):
        raise HTTPException(status_code=404, detail="Result file missing from server storage.")

    return FileResponse(
        path=job.result_url,
        filename=f"analysis_results_{job_id}.csv",
        media_type="text/csv"
    )

@router.get("/batch/jobs", response_model=List[BatchJob])
async def list_jobs(
    user_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_session)
):
    """
    List recent batch jobs.
    """
    query = select(BatchJob)
    if user_id:
        query = query.where(BatchJob.user_id == user_id)
    
    query = query.order_by(desc(BatchJob.created_at)).offset(skip).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()