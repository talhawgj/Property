"""
Routes for accessing scrubbed CSV files from S3.

These endpoints allow the dashboard to list and download CSV files
that have been scrubbed and stored in the attom-scrubber-data S3 bucket.
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

from services.s3 import s3_scrub_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/s3-scrub", tags=["S3 Scrubbed Files"])


class FileInfo(BaseModel):
    """Model for file information."""

    key: str
    name: str
    relative_path: str
    size: int
    last_modified: str


class FileListResponse(BaseModel):
    """Response model for file listing."""

    files: list[FileInfo]
    total_count: int
    directory: Optional[str] = None


class DirectoryListResponse(BaseModel):
    """Response model for directory listing."""

    directories: list[str]
    total_count: int


class PresignedUrlResponse(BaseModel):
    """Response model for presigned URL."""

    url: str
    file_path: str
    expires_in: int


class UploadResponse(BaseModel):
    """Response model for file upload."""

    key: str
    bucket: str
    filename: str
    size: int
    url: str
    content_type: str
    message: str


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(..., description="CSV file to upload"),
    subdirectory: Optional[str] = Query(None, description="Optional subdirectory within uploads/"),
) -> UploadResponse:
    """
    Upload a CSV file to the S3 uploads folder.

    Args:
        file: The CSV file to upload.
        subdirectory: Optional subdirectory (defaults to current date).

    Returns:
        Upload details including the S3 key and URL.
    """
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    if not file.filename.lower().endswith(('.csv', '.xlsx')):
        raise HTTPException(status_code=400, detail="Only CSV and XLSX files are allowed")

    try:
        # Read file in chunks to handle large files better
        chunks = []
        total_size = 0
        CHUNK_SIZE = 1024 * 1024  # 1MB chunks for reading
        
        while True:
            chunk = await file.read(CHUNK_SIZE)
            if not chunk:
                break
            chunks.append(chunk)
            total_size += len(chunk)
            
        content = b''.join(chunks)

        if total_size == 0:
            raise HTTPException(status_code=400, detail="File is empty")

        logger.info(f"Read file {file.filename}: {total_size} bytes")

        # Use current date as subdirectory if not provided
        if not subdirectory:
            subdirectory = datetime.now().strftime("%Y-%m-%d")

        # Determine content type
        content_type = "text/csv" if file.filename.lower().endswith('.csv') else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

        # Upload to S3
        result = s3_scrub_service.upload_file(
            file_content=content,
            filename=file.filename,
            content_type=content_type,
            subdirectory=subdirectory,
        )

        logger.info(f"File uploaded successfully: {result['key']}")

        return UploadResponse(
            **result,
            message=f"File '{file.filename}' uploaded successfully to {result['key']}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


@router.get("/uploads", response_model=FileListResponse)
async def list_uploaded_files(
    prefix: Optional[str] = Query(None, description="Filter by subdirectory"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of files to return"),
) -> FileListResponse:
    """
    List all uploaded files in S3.

    Args:
        prefix: Optional subdirectory to filter by.
        limit: Maximum number of files to return.

    Returns:
        List of uploaded file metadata.
    """
    try:
        files = s3_scrub_service.list_uploaded_files(prefix=prefix)
        limited_files = files[:limit]

        return FileListResponse(
            files=[FileInfo(**f) for f in limited_files],
            total_count=len(files),
            directory=prefix,
        )

    except Exception as e:
        logger.error(f"Failed to list uploaded files: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@router.get("/files", response_model=FileListResponse)
async def list_scrubbed_files(
    directory: Optional[str] = Query(None, description="Filter by date directory (e.g., '2025-01-06')"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of files to return"),
) -> FileListResponse:
    """
    List all scrubbed CSV files in S3.

    Args:
        directory: Optional date directory to filter by.
        limit: Maximum number of files to return.

    Returns:
        List of file metadata including name, size, and last modified date.
    """
    try:
        files = s3_scrub_service.list_scrubbed_files(prefix=directory)

        # Apply limit
        limited_files = files[:limit]

        return FileListResponse(
            files=[FileInfo(**f) for f in limited_files],
            total_count=len(files),
            directory=directory,
        )

    except Exception as e:
        logger.error(f"Failed to list scrubbed files: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@router.get("/directories", response_model=DirectoryListResponse)
async def list_directories() -> DirectoryListResponse:
    """
    List all date directories in the scrubbed folder.

    Returns:
        List of directory names sorted by date (newest first).
    """
    try:
        directories = s3_scrub_service.list_directories()
        return DirectoryListResponse(
            directories=directories,
            total_count=len(directories),
        )

    except Exception as e:
        logger.error(f"Failed to list directories: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list directories: {str(e)}")


@router.get("/download/{file_path:path}")
async def download_file(file_path: str) -> StreamingResponse:
    """
    Download a specific scrubbed CSV file.

    Args:
        file_path: Relative path to the file (e.g., '2025-01-06/scrubbed_part_1.csv').

    Returns:
        StreamingResponse with the CSV file content.
    """
    try:
        # Check if file exists
        if not s3_scrub_service.file_exists(file_path):
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

        # Get file stream
        file_stream = s3_scrub_service.get_file_stream(file_path)

        # Extract filename for Content-Disposition
        filename = file_path.split("/")[-1]

        return StreamingResponse(
            file_stream,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    except Exception as e:
        logger.error(f"Failed to download file {file_path}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")


@router.get("/presigned-url/{file_path:path}", response_model=PresignedUrlResponse)
async def get_presigned_url(
    file_path: str,
    expiration: int = Query(3600, ge=60, le=86400, description="URL expiration in seconds"),
) -> PresignedUrlResponse:
    """
    Get a presigned URL for direct file download.

    This is useful for large files where streaming through the API
    might not be ideal.

    Args:
        file_path: Relative path to the file.
        expiration: URL expiration time in seconds (1 min to 24 hours).

    Returns:
        Presigned URL that can be used for direct S3 download.
    """
    try:
        if not s3_scrub_service.file_exists(file_path):
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

        url = s3_scrub_service.get_presigned_url(file_path, expiration=expiration)

        return PresignedUrlResponse(
            url=url,
            file_path=file_path,
            expires_in=expiration,
        )

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    except Exception as e:
        logger.error(f"Failed to generate presigned URL for {file_path}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate URL: {str(e)}")


@router.delete("/files/{file_path:path}")
async def delete_file(file_path: str) -> JSONResponse:
    """
    Delete a specific file from S3.

    Args:
        file_path: Relative path to the file to delete.

    Returns:
        Success message.
    """
    try:
        if not s3_scrub_service.file_exists(file_path):
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

        s3_scrub_service.delete_file(file_path)

        return JSONResponse(
            content={
                "status": "success",
                "message": f"File '{file_path}' deleted successfully",
            }
        )

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    except Exception as e:
        logger.error(f"Failed to delete file {file_path}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")


@router.delete("/directories/{directory}")
async def delete_directory(directory: str) -> JSONResponse:
    """
    Delete all files in a specific directory.

    Args:
        directory: Directory name to delete (e.g., '2025-01-06').

    Returns:
        Success message with count of deleted files.
    """
    try:
        deleted_count = s3_scrub_service.delete_directory(directory)

        if deleted_count == 0:
            return JSONResponse(
                content={
                    "status": "success",
                    "message": f"No files found in directory '{directory}'",
                    "deleted_count": 0,
                }
            )

        return JSONResponse(
            content={
                "status": "success",
                "message": f"Deleted {deleted_count} files from directory '{directory}'",
                "deleted_count": deleted_count,
            }
        )

    except Exception as e:
        logger.error(f"Failed to delete directory {directory}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete directory: {str(e)}")


@router.get("/health")
async def health_check() -> JSONResponse:
    """
    Check S3 connectivity and bucket access.

    Returns:
        Health status and bucket information.
    """
    try:
        # Try to list a few files to verify connectivity
        files = s3_scrub_service.list_scrubbed_files()
        directories = s3_scrub_service.list_directories()

        return JSONResponse(
            content={
                "status": "healthy",
                "bucket": s3_scrub_service.bucket,
                "region": s3_scrub_service.region,
                "prefix": s3_scrub_service.prefix,
                "file_count": len(files),
                "directory_count": len(directories),
            }
        )

    except Exception as e:
        logger.error(f"S3 health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "bucket": s3_scrub_service.bucket,
                "region": s3_scrub_service.region,
            },
        )
