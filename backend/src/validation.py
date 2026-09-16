"""
Input validation for CloudRAG API requests.

Kept deliberately simple and dependency-free so it can be unit tested
without any AWS SDK or network calls.
"""

from .config import Config


class ValidationError(Exception):
    def __init__(self, message: str, field: str = None):
        super().__init__(message)
        self.message = message
        self.field = field


def validate_upload(filename: str, content_type: str, size_bytes: int) -> None:
    if not filename:
        raise ValidationError("filename is required", field="filename")

    if not filename.lower().endswith(".pdf"):
        raise ValidationError("Only .pdf files are supported", field="filename")

    if content_type not in Config.ALLOWED_CONTENT_TYPES:
        raise ValidationError(
            f"Unsupported content type: {content_type}. Expected application/pdf",
            field="content_type",
        )

    if size_bytes <= 0:
        raise ValidationError("Uploaded file is empty", field="size_bytes")

    if size_bytes > Config.MAX_FILE_SIZE_BYTES:
        max_mb = Config.MAX_FILE_SIZE_BYTES / (1024 * 1024)
        raise ValidationError(f"File exceeds max size of {max_mb:.0f}MB", field="size_bytes")


def validate_question(question: str) -> None:
    if question is None:
        raise ValidationError("question is required", field="question")

    if not question.strip():
        raise ValidationError("question cannot be empty", field="question")

    if len(question) > Config.MAX_QUESTION_LENGTH:
        raise ValidationError(
            f"question exceeds max length of {Config.MAX_QUESTION_LENGTH} characters",
            field="question",
        )
