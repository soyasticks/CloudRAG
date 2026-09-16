"""
Centralized configuration for CloudRAG backend Lambdas.

All values come from environment variables set in the Lambda console /
SAM template — nothing is hardcoded, and nothing sensitive is committed
to source control.
"""

import os


class Config:
    # S3
    DOCUMENT_BUCKET: str = os.environ.get("DOCUMENT_BUCKET", "")
    UPLOAD_PREFIX: str = os.environ.get("UPLOAD_PREFIX", "documents/")

    # Bedrock
    KNOWLEDGE_BASE_ID: str = os.environ.get("KNOWLEDGE_BASE_ID", "")
    BEDROCK_MODEL_ARN: str = os.environ.get(
        "BEDROCK_MODEL_ARN",
        "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-haiku-20240307-v1:0",
    )
    AWS_REGION: str = os.environ.get("AWS_REGION", "us-east-1")

    # Retrieval tuning
    RETRIEVAL_TOP_K: int = int(os.environ.get("RETRIEVAL_TOP_K", "1"))

    # Upload limits
    MAX_FILE_SIZE_BYTES: int = int(os.environ.get("MAX_FILE_SIZE_BYTES", str(10 * 1024 * 1024)))  # 10 MB
    ALLOWED_CONTENT_TYPES = {"application/pdf"}

    # Question limits
    MAX_QUESTION_LENGTH: int = int(os.environ.get("MAX_QUESTION_LENGTH", "500"))

    @classmethod
    def validate(cls) -> list:
        """Returns a list of missing required config values (empty = OK)."""
        missing = []
        if not cls.DOCUMENT_BUCKET:
            missing.append("DOCUMENT_BUCKET")
        if not cls.KNOWLEDGE_BASE_ID:
            missing.append("KNOWLEDGE_BASE_ID")
        return missing
