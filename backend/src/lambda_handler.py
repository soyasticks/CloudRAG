"""
Single Lambda entrypoint, routed by API Gateway proxy integration.

Two logical handlers live here (upload_handler, query_handler) plus a
health_handler. Kept in one file for a project this size — split into
separate Lambdas only if cold-start isolation or IAM scoping actually
requires it (see README "Future Improvements").
"""

import base64
import json
import uuid

from .config import Config
from .logger import get_logger, RequestContext
from .s3_service import S3Service
from .rag_service import answer_question
from .validation import validate_upload, ValidationError

_logger = get_logger("cloudrag")

_CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "OPTIONS,POST,GET",
}


def _response(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {**_CORS_HEADERS, "Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def _error_response(status: int, message: str, field: str = None) -> dict:
    payload = {"error": message}
    if field:
        payload["field"] = field
    return _response(status, payload)


def health_handler(event, context):
    missing = Config.validate()
    if missing:
        return _response(503, {"status": "unhealthy", "missing_config": missing})
    return _response(200, {"status": "ok"})


def upload_handler(event, context):
    request_id = str(uuid.uuid4())
    log = RequestContext(_logger, request_id)
    log.info("upload request received")

    missing = Config.validate()
    if missing:
        log.error("missing required config: %s", missing)
        return _error_response(500, "Server misconfigured")

    try:
        body = event.get("body", "")
        if event.get("isBase64Encoded"):
            raw_bytes = base64.b64decode(body)
        else:
            raw_bytes = body.encode("utf-8")

        headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
        content_type = headers.get("content-type", "application/pdf")
        filename = (event.get("queryStringParameters") or {}).get("filename", "upload.pdf")

        validate_upload(filename, content_type, len(raw_bytes))

        document_id = str(uuid.uuid4())
        s3_key_name = f"{document_id}_{filename}"

        s3 = S3Service()
        full_key = s3.upload_document(s3_key_name, raw_bytes, content_type)

        log.info("upload completed key=%s size=%d bytes", full_key, len(raw_bytes))

        return _response(
            200,
            {
                "documentId": document_id,
                "s3Key": full_key,
                "status": "uploaded",
                "message": "Document uploaded. Ingestion into the knowledge base runs on the next sync.",
            },
        )

    except ValidationError as exc:
        log.warning("upload validation failed: %s", exc.message)
        return _error_response(400, exc.message, field=exc.field)
    except RuntimeError as exc:
        log.exception("upload failed")
        return _error_response(502, "Upload failed, please try again")
    except Exception:
        log.exception("unexpected error during upload")
        return _error_response(500, "Internal server error")


def query_handler(event, context):
    request_id = str(uuid.uuid4())
    log = RequestContext(_logger, request_id)
    log.info("query request received")

    missing = Config.validate()
    if missing:
        log.error("missing required config: %s", missing)
        return _error_response(500, "Server misconfigured")

    try:
        raw_body = event.get("body", "{}") or "{}"
        payload = json.loads(raw_body)
        question = payload.get("question")

        log.info("processing question of length %d", len(question) if question else 0)

        result = answer_question(question)

        log.info(
            "query completed sources=%d latency_ms=%d",
            len(result["sources"]),
            result["total_latency_ms"],
        )

        return _response(
            200,
            {
                "answer": result["answer"],
                "sources": result["sources"],
                "latencyMs": result["total_latency_ms"],
                "requestId": request_id,
            },
        )

    except json.JSONDecodeError:
        log.warning("malformed JSON body")
        return _error_response(400, "Request body must be valid JSON")
    except ValidationError as exc:
        log.warning("query validation failed: %s", exc.message)
        return _error_response(400, exc.message, field=exc.field)
    except RuntimeError as exc:
        log.exception("bedrock call failed")
        return _error_response(502, "Unable to generate an answer right now, please try again")
    except Exception:
        log.exception("unexpected error during query")
        return _error_response(500, "Internal server error")
