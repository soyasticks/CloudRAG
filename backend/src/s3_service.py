"""
Thin wrapper around S3 operations used by the upload handler.

Lambda's execution role provides credentials via IAM — no access keys
are ever read from environment variables or code here.
"""

import boto3
from botocore.exceptions import ClientError

from .config import Config


class S3Service:
    def __init__(self):
        self.client = boto3.client("s3", region_name=Config.AWS_REGION)
        self.bucket = Config.DOCUMENT_BUCKET

    def upload_document(self, key: str, body: bytes, content_type: str) -> str:
        """
        Uploads a document to S3 under the configured prefix.
        Returns the full S3 key.
        """
        full_key = f"{Config.UPLOAD_PREFIX}{key}"
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=full_key,
                Body=body,
                ContentType=content_type,
            )
        except ClientError as exc:
            raise RuntimeError(f"S3 upload failed: {exc.response['Error']['Code']}") from exc

        return full_key

    def object_exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as exc:
            if exc.response["Error"]["Code"] in ("404", "NoSuchKey"):
                return False
            raise
