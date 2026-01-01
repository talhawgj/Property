import os
import json
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, desc
from db import get_session 
from models import BatchJob, JobStatus, JobPriority
from services import batch_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Batch Analysis"])

@router.get("/analyze/{gid}", response_model=Optional[Dict[str, Any]])
async def parcel_analysis(gid: int,db: AsyncSession = Depends(get_session)) -> Optional[Dict[str, Any]]:
    """
    Analyze a single parcel immediately (synchronous).
    """
    service = batch_service.analysis_service
    result = await service.get_analysis(gid=gid, db=db)
    return result

@router.post("/analyze/batch", response_model=BatchJob)
async def submit_batch_job(file: UploadFile = File(...),column_mapping: Optional[str] = Form(None, description='JSON string e.g. {"Lat": "PropertyLatitude"}'),priority: JobPriority = Form(JobPriority.NORMAL),
                            dry_run: bool = Form(False), user_id: str = Form("system"),username: str = Form("system"), db: AsyncSession = Depends(get_session)):
    """
    Uploads file -> Creates Job (Queued).
    The System Scheduler (running in main.py) will pick this up automatically.
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
        new_job = await batch_service.create_job_with_file(
            file=file,
            db=db,
            user_id=user_id,
            username=username,
            priority=priority,
            column_mapping=mapping_dict,
            dry_run=dry_run
        )
        
        logger.info(f"Job {new_job.job_id} submitted to queue.")
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
    Cancels a job. The worker checks this status during processing and aborts.
    """
    job = await db.get(BatchJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status in [JobStatus.QUEUED, JobStatus.PROCESSING]:
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
    Check DB for progress.
    """
    job = await db.get(BatchJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    percent = 0
    if job.total_rows > 0:
        percent = int((job.completed_rows / job.total_rows) * 100)
    elif job.status == JobStatus.COMPLETED:
        percent = 100

    return {
        "job_id": job_id,
        "status": job.status,
        "progress": {
            "current": job.completed_rows,
            "total": job.total_rows,
            "failed": job.failed_rows, # Added visibility into failures
            "percent": percent
        },
        "error": job.error_message,
        "result_url": f"/batch/download/{job_id}" if job.status == JobStatus.COMPLETED else None
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