import os
import asyncio
import time
import logging
import pandas as pd
from datetime import datetime, timedelta
from celery import Celery
from kombu import Queue
from asgiref.sync import async_to_sync
from sqlalchemy import select

from db import SessionLocal
from models import BatchJob, JobStatus
from services.batch import BatchService

# Configure Logging
logger = logging.getLogger("worker")

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_app = Celery("batch_worker", broker=redis_url, backend=redis_url)

# --- 1. PRIORITY QUEUES CONFIGURATION ---
celery_app.conf.task_queues = (
    Queue('high', routing_key='high'),
    Queue('normal', routing_key='normal'),
    Queue('low', routing_key='low'),
)
celery_app.conf.task_default_queue = 'normal'

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

@celery_app.task(bind=True)
def run_batch_analysis_task(self, job_id: str, file_path: str, column_mapping: dict, user_id: str, dry_run: bool):
    """
    Celery wrapper that runs the async analysis logic.
    """
    return async_to_sync(execute_batch)(self, job_id, file_path, column_mapping, user_id, dry_run)

# --- 2. AUTOMATIC CLEANUP TASK ---
@celery_app.task
def cleanup_old_exports():
    """
    Deletes export files older than 24 hours.
    """
    export_dir = "/tmp/exports"
    retention_period = 86400  # 24 hours
    now = time.time()

    if not os.path.exists(export_dir):
        return "Export directory does not exist."

    deleted_count = 0
    for filename in os.listdir(export_dir):
        file_path = os.path.join(export_dir, filename)
        if os.path.isfile(file_path) and os.path.getmtime(file_path) < now - retention_period:
            try:
                os.remove(file_path)
                deleted_count += 1
            except Exception as e:
                logger.error(f"Failed to delete {filename}: {e}")
    
    return f"Cleaned up {deleted_count} old files."

# --- 3. STUCK JOB DETECTION TASK ---
@celery_app.task
def recover_stuck_jobs():
    """
    Finds jobs stuck in PROCESSING state for > 2 hours.
    """
    async def _recover():
        timeout_threshold = datetime.utcnow() - timedelta(hours=2)
        async with SessionLocal() as db:
            query = select(BatchJob).where(
                BatchJob.status == JobStatus.PROCESSING,
                BatchJob.started_at < timeout_threshold
            )
            result = await db.execute(query)
            stuck_jobs = result.scalars().all()

            count = 0
            for job in stuck_jobs:
                job.status = JobStatus.FAILED
                job.error_message = "Job timed out or worker process crashed."
                job.completed_at = datetime.utcnow()
                db.add(job)
                count += 1
            
            if count > 0:
                await db.commit()
            return count

    count = async_to_sync(_recover)()
    return f"Recovered {count} stuck jobs."

async def execute_batch(task, job_id, file_path, column_mapping, user_id, dry_run):
    service = BatchService()
    
    async def on_progress(completed, total):
        # Prevent division by zero and ensure integers
        if total > 0:
            pct = int((completed / total) * 100)
        else:
            pct = 0
            
        # Update Celery state (Redis) for real-time UI
        task.update_state(
            state='PROGRESS',
            meta={'current': completed, 'total': total, 'percent': pct}
        )
        
        # Update DB every 10 rows or at finish for persistence
        if completed % 10 == 0 or completed == total:
             async with SessionLocal() as db:
                 job = await db.get(BatchJob, job_id)
                 if job and job.status != JobStatus.CANCELLED:
                     job.completed_rows = completed
                     db.add(job)
                     await db.commit()

    async with SessionLocal() as db:
        try:
            job = await db.get(BatchJob, job_id)
            
            if job.status == JobStatus.CANCELLED:
                return {"status": "cancelled"}

            job.status = JobStatus.PROCESSING
            job.started_at = datetime.utcnow()
            db.add(job)
            await db.commit()

            result = await service.analyze_file(
                file_path=file_path,
                db=db,
                job_id=job_id,
                column_mapping=column_mapping,
                dry_run=dry_run,
                progress_callback=on_progress
            )
            
            # Check for cancellation again
            await db.refresh(job)
            if job.status == JobStatus.CANCELLED:
                 return {"status": "cancelled"}

            flattened = service.flatten_analysis_results(result["results"])
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
            
            return {"status": "completed", "rows": len(flattened)}

        except Exception as e:
            await db.rollback()
            
            async with SessionLocal() as err_db:
                job = await err_db.get(BatchJob, job_id)
                # Ensure we don't overwrite a user cancellation
                if job and job.status != JobStatus.CANCELLED:
                    job.status = JobStatus.FAILED
                    job.error_message = f"Processing Error: {str(e)}"
                    job.completed_at = datetime.utcnow()
                    err_db.add(job)
                    await err_db.commit()
            raise e
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)