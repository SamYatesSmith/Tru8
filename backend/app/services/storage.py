"""
File storage service with S3/MinIO and local fallback support.

This module provides a unified interface for file storage operations,
supporting both cloud storage (S3/MinIO) and local filesystem storage.

boto3 is optional - falls back to local storage if not installed.
"""

import logging
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO

import aiofiles

from app.core.config import settings

logger = logging.getLogger(__name__)

# Optional boto3 import - S3 storage disabled if not installed
try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    logger.info("boto3 not installed - S3 storage disabled, using local storage")


class StorageBackend(ABC):
    """Abstract base class for storage backends."""

    @abstractmethod
    async def upload(
        self,
        file_data: bytes,
        filename: str,
        content_type: str,
    ) -> str:
        """
        Upload a file and return its storage path/URL.

        Args:
            file_data: Raw file bytes
            filename: Original filename (used for extension)
            content_type: MIME type of the file

        Returns:
            Storage path or URL for the uploaded file
        """
        pass

    @abstractmethod
    async def download(self, file_path: str) -> bytes:
        """Download a file by its storage path."""
        pass

    @abstractmethod
    async def delete(self, file_path: str) -> bool:
        """Delete a file by its storage path."""
        pass

    @abstractmethod
    async def exists(self, file_path: str) -> bool:
        """Check if a file exists."""
        pass


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage backend for development."""

    def __init__(self, base_dir: str = "uploads"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)

    async def upload(
        self,
        file_data: bytes,
        filename: str,
        content_type: str,
    ) -> str:
        file_id = str(uuid.uuid4())
        extension = Path(filename).suffix.lower()
        storage_filename = f"{file_id}{extension}"
        file_path = self.base_dir / storage_filename

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_data)

        logger.info("File uploaded to local storage: %s", file_path)
        return str(file_path)

    async def download(self, file_path: str) -> bytes:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        async with aiofiles.open(path, "rb") as f:
            return await f.read()

    async def delete(self, file_path: str) -> bool:
        path = Path(file_path)
        if path.exists():
            path.unlink()
            logger.info("File deleted from local storage: %s", file_path)
            return True
        return False

    async def exists(self, file_path: str) -> bool:
        return Path(file_path).exists()


class S3StorageBackend(StorageBackend):
    """S3/MinIO storage backend for production."""

    def __init__(
        self,
        bucket: str,
        access_key: str,
        secret_key: str,
        endpoint_url: str | None = None,
        region: str = "us-east-1",
    ):
        self.bucket = bucket
        self.endpoint_url = endpoint_url

        # Configure boto3 client
        config = Config(
            retries={"max_attempts": 3, "mode": "adaptive"},
            connect_timeout=5,
            read_timeout=30,
        )

        client_kwargs = {
            "service_name": "s3",
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
            "region_name": region,
            "config": config,
        }

        # Add endpoint for MinIO or S3-compatible storage
        if endpoint_url:
            client_kwargs["endpoint_url"] = endpoint_url

        self.client = boto3.client(**client_kwargs)

        # Ensure bucket exists
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        """Create bucket if it doesn't exist."""
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code == "404":
                try:
                    self.client.create_bucket(Bucket=self.bucket)
                    logger.info("Created S3 bucket: %s", self.bucket)
                except ClientError as create_error:
                    logger.error("Failed to create bucket: %s", create_error)
                    raise
            else:
                raise

    async def upload(
        self,
        file_data: bytes,
        filename: str,
        content_type: str,
    ) -> str:
        file_id = str(uuid.uuid4())
        extension = Path(filename).suffix.lower()
        key = f"uploads/{file_id}{extension}"

        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=file_data,
                ContentType=content_type,
            )
            logger.info("File uploaded to S3: %s/%s", self.bucket, key)

            # Return S3 URL or key based on configuration
            if self.endpoint_url:
                return f"{self.endpoint_url}/{self.bucket}/{key}"
            return f"s3://{self.bucket}/{key}"

        except ClientError as e:
            logger.error("S3 upload failed: %s", e)
            raise

    async def download(self, file_path: str) -> bytes:
        key = self._extract_key(file_path)

        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read()
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code == "NoSuchKey":
                raise FileNotFoundError(f"File not found: {file_path}")
            raise

    async def delete(self, file_path: str) -> bool:
        key = self._extract_key(file_path)

        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
            logger.info("File deleted from S3: %s/%s", self.bucket, key)
            return True
        except ClientError as e:
            logger.error("S3 delete failed: %s", e)
            return False

    async def exists(self, file_path: str) -> bool:
        key = self._extract_key(file_path)

        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            return False

    def _extract_key(self, file_path: str) -> str:
        """Extract S3 key from various path formats."""
        # Handle s3://bucket/key format
        if file_path.startswith("s3://"):
            parts = file_path[5:].split("/", 1)
            return parts[1] if len(parts) > 1 else ""

        # Handle http(s)://endpoint/bucket/key format
        if file_path.startswith("http"):
            # Remove protocol and endpoint
            parts = file_path.split("/")
            # Find bucket in URL and get everything after it
            try:
                bucket_idx = parts.index(self.bucket)
                return "/".join(parts[bucket_idx + 1 :])
            except ValueError:
                pass

        # Assume it's already a key
        return file_path


class StorageService:
    """
    Unified storage service that selects the appropriate backend.

    Uses S3/MinIO in production when credentials are provided,
    falls back to local storage in development.
    """

    _instance: "StorageService | None" = None
    _backend: StorageBackend | None = None

    def __new__(cls) -> "StorageService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def backend(self) -> StorageBackend:
        if self._backend is None:
            self._backend = self._create_backend()
        return self._backend

    def _create_backend(self) -> StorageBackend:
        """Create the appropriate storage backend based on configuration."""
        # Use S3 if boto3 is available and credentials are provided
        if BOTO3_AVAILABLE and settings.S3_ACCESS_KEY and settings.S3_SECRET_KEY:
            logger.info(
                "Using S3 storage backend (bucket=%s, endpoint=%s)",
                settings.S3_BUCKET,
                settings.S3_ENDPOINT or "AWS S3",
            )
            return S3StorageBackend(
                bucket=settings.S3_BUCKET,
                access_key=settings.S3_ACCESS_KEY,
                secret_key=settings.S3_SECRET_KEY,
                endpoint_url=settings.S3_ENDPOINT or None,
            )

        # Fall back to local storage
        if not BOTO3_AVAILABLE:
            logger.info("Using local storage backend (boto3 not installed)")
        else:
            logger.info("Using local storage backend (no S3 credentials)")
        return LocalStorageBackend()

    async def upload(
        self,
        file_data: bytes,
        filename: str,
        content_type: str,
    ) -> str:
        """Upload a file to storage."""
        return await self.backend.upload(file_data, filename, content_type)

    async def download(self, file_path: str) -> bytes:
        """Download a file from storage."""
        return await self.backend.download(file_path)

    async def delete(self, file_path: str) -> bool:
        """Delete a file from storage."""
        return await self.backend.delete(file_path)

    async def exists(self, file_path: str) -> bool:
        """Check if a file exists in storage."""
        return await self.backend.exists(file_path)


# Singleton instance
storage_service = StorageService()
