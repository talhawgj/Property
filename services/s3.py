"""
S3 Service for accessing scrubbed CSV files from S3.

Uses IAM roles for authentication (no access keys needed when deployed on EC2).
"""

import io
import logging
from typing import Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# S3 Configuration
S3_BUCKET = "attom-scrubber-data"
S3_REGION = "us-east-2"
S3_PREFIX = "scrubbed/"
S3_UPLOADS_PREFIX = "uploads/"


def get_s3_client():
    """
    Get an S3 client using IAM role credentials.

    When running on EC2, boto3 automatically uses the instance's IAM role.
    No access keys are needed.

    Returns:
        boto3.client: S3 client instance.
    """
    return boto3.client("s3", region_name=S3_REGION)


class S3ScrubService:
    """Service for managing scrubbed CSV files in S3."""

    def __init__(self) -> None:
        """Initialize the S3 scrub service."""
        self.bucket = S3_BUCKET
        self.region = S3_REGION
        self.prefix = S3_PREFIX
        self.uploads_prefix = S3_UPLOADS_PREFIX
        self._client: Optional[boto3.client] = None

    @property
    def client(self):
        """Lazy initialization of S3 client."""
        if self._client is None:
            self._client = get_s3_client()
        return self._client

    def list_scrubbed_files(self, prefix: Optional[str] = None) -> list[dict]:
        """
        List all CSV files in the scrubbed folder.

        Args:
            prefix: Optional subdirectory prefix to filter by.

        Returns:
            List of file metadata dictionaries containing:
                - key: Full S3 key
                - name: File name only
                - size: File size in bytes
                - last_modified: Last modification timestamp
        """
        search_prefix = self.prefix
        if prefix:
            search_prefix = f"{self.prefix}{prefix}/"

        try:
            paginator = self.client.get_paginator("list_objects_v2")
            files = []

            for page in paginator.paginate(Bucket=self.bucket, Prefix=search_prefix):
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    # Skip directory markers and non-CSV files
                    if key.endswith("/") or not key.lower().endswith(".csv"):
                        continue

                    # Extract just the filename (after the prefix)
                    relative_path = key[len(self.prefix) :] if key.startswith(self.prefix) else key
                    name = key.split("/")[-1]

                    files.append(
                        {
                            "key": key,
                            "name": name,
                            "relative_path": relative_path,
                            "size": obj["Size"],
                            "last_modified": obj["LastModified"].isoformat(),
                        }
                    )

            # Sort by last modified, newest first
            files.sort(key=lambda x: x["last_modified"], reverse=True)
            logger.info(f"Found {len(files)} CSV files in S3 bucket {self.bucket}/{search_prefix}")
            return files

        except ClientError as e:
            logger.error(f"Error listing files from S3: {e}")
            raise

    def list_directories(self) -> list[str]:
        """
        List all date directories in the scrubbed folder.

        Returns:
            List of directory names (e.g., ['2025-01-06', '2025-01-05']).
        """
        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket, Prefix=self.prefix, Delimiter="/"
            )

            directories = []
            for prefix_obj in response.get("CommonPrefixes", []):
                prefix_path = prefix_obj["Prefix"]
                # Extract directory name (remove trailing slash and base prefix)
                dir_name = prefix_path[len(self.prefix) :].rstrip("/")
                if dir_name:
                    directories.append(dir_name)

            directories.sort(reverse=True)  # Newest first
            logger.info(f"Found {len(directories)} directories in S3")
            return directories

        except ClientError as e:
            logger.error(f"Error listing directories from S3: {e}")
            raise

    def get_file_content(self, file_path: str) -> bytes:
        """
        Get the content of a specific file from S3.

        Args:
            file_path: Relative path to the file within the scrubbed folder.

        Returns:
            File content as bytes.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            ClientError: If there's an S3 error.
        """
        # Build the full S3 key
        if file_path.startswith(self.prefix):
            key = file_path
        else:
            key = f"{self.prefix}{file_path}"

        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            content = response["Body"].read()
            logger.info(f"Retrieved file from S3: {key} ({len(content)} bytes)")
            return content

        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                logger.error(f"File not found in S3: {key}")
                raise FileNotFoundError(f"File not found: {file_path}")
            logger.error(f"Error getting file from S3: {e}")
            raise

    def get_file_stream(self, file_path: str) -> io.BytesIO:
        """
        Get a file as a BytesIO stream for streaming downloads.

        Args:
            file_path: Relative path to the file within the scrubbed folder.

        Returns:
            BytesIO stream containing the file content.
        """
        content = self.get_file_content(file_path)
        return io.BytesIO(content)

    def get_presigned_url(self, file_path: str, expiration: int = 3600) -> str:
        """
        Generate a presigned URL for direct file download.

        Args:
            file_path: Relative path to the file within the scrubbed folder.
            expiration: URL expiration time in seconds (default: 1 hour).

        Returns:
            Presigned URL string.
        """
        if file_path.startswith(self.prefix):
            key = file_path
        else:
            key = f"{self.prefix}{file_path}"

        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expiration,
            )
            logger.info(f"Generated presigned URL for: {key}")
            return url

        except ClientError as e:
            logger.error(f"Error generating presigned URL: {e}")
            raise

    def file_exists(self, file_path: str) -> bool:
        """
        Check if a file exists in S3.

        Args:
            file_path: Relative path to the file within the scrubbed folder.

        Returns:
            True if the file exists, False otherwise.
        """
        if file_path.startswith(self.prefix):
            key = file_path
        else:
            key = f"{self.prefix}{file_path}"

        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise

    def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from S3.

        Args:
            file_path: Relative path to the file within the scrubbed folder.

        Returns:
            True if deletion was successful.
        """
        if file_path.startswith(self.prefix):
            key = file_path
        else:
            key = f"{self.prefix}{file_path}"

        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
            logger.info(f"Deleted file from S3: {key}")
            return True

        except ClientError as e:
            logger.error(f"Error deleting file from S3: {e}")
            raise

    def delete_directory(self, directory: str) -> int:
        """
        Delete all files in a directory.

        Args:
            directory: Directory name to delete.

        Returns:
            Number of files deleted.
        """
        prefix = f"{self.prefix}{directory}/"

        try:
            # List all objects with the prefix
            paginator = self.client.get_paginator("list_objects_v2")
            objects_to_delete = []

            for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
                for obj in page.get("Contents", []):
                    objects_to_delete.append({"Key": obj["Key"]})

            if not objects_to_delete:
                logger.info(f"No files found in directory: {directory}")
                return 0

            # Delete in batches of 1000 (S3 limit)
            deleted_count = 0
            for i in range(0, len(objects_to_delete), 1000):
                batch = objects_to_delete[i : i + 1000]
                self.client.delete_objects(
                    Bucket=self.bucket, Delete={"Objects": batch, "Quiet": True}
                )
                deleted_count += len(batch)

            logger.info(f"Deleted {deleted_count} files from directory: {directory}")
            return deleted_count

        except ClientError as e:
            logger.error(f"Error deleting directory from S3: {e}")
            raise

    def upload_file(
        self,
        file_content: bytes,
        filename: str,
        content_type: str = "text/csv",
        subdirectory: Optional[str] = None,
    ) -> dict:
        """
        Upload a file to the uploads folder in S3.

        Args:
            file_content: The file content as bytes.
            filename: The name of the file.
            content_type: MIME type of the file.
            subdirectory: Optional subdirectory within uploads/.

        Returns:
            Dict with upload details including the S3 key and URL.
        """
        # Build the S3 key
        if subdirectory:
            key = f"{self.uploads_prefix}{subdirectory}/{filename}"
        else:
            key = f"{self.uploads_prefix}{filename}"

        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=file_content,
                ContentType=content_type,
            )

            # Generate the S3 URL
            url = f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{key}"

            logger.info(f"Uploaded file to S3: {key} ({len(file_content)} bytes)")

            return {
                "key": key,
                "bucket": self.bucket,
                "filename": filename,
                "size": len(file_content),
                "url": url,
                "content_type": content_type,
            }

        except ClientError as e:
            logger.error(f"Error uploading file to S3: {e}")
            raise

    def list_uploaded_files(self, prefix: Optional[str] = None) -> list[dict]:
        """
        List all files in the uploads folder.

        Args:
            prefix: Optional subdirectory prefix to filter by.

        Returns:
            List of file metadata dictionaries.
        """
        search_prefix = self.uploads_prefix
        if prefix:
            search_prefix = f"{self.uploads_prefix}{prefix}/"

        try:
            paginator = self.client.get_paginator("list_objects_v2")
            files = []

            for page in paginator.paginate(Bucket=self.bucket, Prefix=search_prefix):
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    if key.endswith("/"):
                        continue

                    relative_path = key[len(self.uploads_prefix):] if key.startswith(self.uploads_prefix) else key
                    name = key.split("/")[-1]

                    files.append(
                        {
                            "key": key,
                            "name": name,
                            "relative_path": relative_path,
                            "size": obj["Size"],
                            "last_modified": obj["LastModified"].isoformat(),
                        }
                    )

            files.sort(key=lambda x: x["last_modified"], reverse=True)
            logger.info(f"Found {len(files)} files in uploads")
            return files

        except ClientError as e:
            logger.error(f"Error listing uploaded files: {e}")
            raise


# Singleton instance
s3_scrub_service = S3ScrubService()
