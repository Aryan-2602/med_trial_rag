"""S3 I/O utilities for downloading and uploading files."""

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterator

import boto3
from botocore.exceptions import ClientError

from utils.logging import get_logger

logger = get_logger(__name__)


def download_if_needed(
    bucket: str,
    key: str,
    local_path: str,
    s3_client: Any = None,
    force: bool = False,
) -> bool:
    """
    Download S3 object to local path if not present or ETag differs.

    Args:
        bucket: S3 bucket name
        key: S3 object key
        local_path: Local file path
        s3_client: Boto3 S3 client (creates new if None)
        force: Force download even if file exists

    Returns:
        True if file was downloaded, False if already present
    """
    if s3_client is None:
        s3_client = boto3.client("s3")

    local_file = Path(local_path)
    local_file.parent.mkdir(parents=True, exist_ok=True)

    if not force and local_file.exists():
        # Check ETag to see if we need to update
        try:
            response = s3_client.head_object(Bucket=bucket, Key=key)
            etag = response.get("ETag", "").strip('"')
            local_etag = _compute_file_hash(local_path)
            if etag == local_etag:
                logger.debug("file_already_cached", bucket=bucket, key=key, local_path=local_path)
                return False
        except ClientError as e:
            logger.warning("etag_check_failed", error=str(e), bucket=bucket, key=key)
            # If head_object fails, try to download anyway

    try:
        logger.info("downloading_file", bucket=bucket, key=key, local_path=local_path)
        s3_client.download_file(bucket, key, local_path)
        return True
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        logger.error(
            "download_failed",
            bucket=bucket,
            key=key,
            error_code=error_code,
            error=str(e),
        )
        raise


def _compute_file_hash(filepath: str) -> str:
    """Compute MD5 hash of file (for simple ETag comparison)."""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def jsonl_iter(path: str) -> Iterator[dict[str, Any]]:
    """
    Iterate over JSONL file, yielding one JSON object per line.

    Args:
        path: Path to JSONL file

    Yields:
        Dict objects from each line
    """
    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                logger.warning("jsonl_parse_error", path=path, line=line_num, error=str(e))
                continue


def atomic_upload(
    bucket: str,
    key: str,
    local_path: str,
    s3_client: Any = None,
    metadata: dict[str, str] | None = None,
) -> None:
    """
    Upload file to S3 atomically (for indexers).

    Args:
        bucket: S3 bucket name
        key: S3 object key
        local_path: Local file path
        s3_client: Boto3 S3 client (creates new if None)
        metadata: Optional metadata dict
    """
    if s3_client is None:
        s3_client = boto3.client("s3")

    extra_args = {}
    if metadata:
        extra_args["Metadata"] = metadata

    try:
        logger.info("uploading_file", bucket=bucket, key=key, local_path=local_path)
        s3_client.upload_file(local_path, bucket, key, ExtraArgs=extra_args)
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        logger.error(
            "upload_failed",
            bucket=bucket,
            key=key,
            error_code=error_code,
            error=str(e),
        )
        raise


def get_object_json(bucket: str, key: str, s3_client: Any = None) -> dict[str, Any]:
    """
    Download and parse JSON object from S3.

    Args:
        bucket: S3 bucket name
        key: S3 object key
        s3_client: Boto3 S3 client (creates new if None)

    Returns:
        Parsed JSON dict
    """
    if s3_client is None:
        s3_client = boto3.client("s3")

    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        return json.loads(response["Body"].read().decode("utf-8"))
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        logger.error(
            "get_json_failed",
            bucket=bucket,
            key=key,
            error_code=error_code,
            error=str(e),
        )
        raise

