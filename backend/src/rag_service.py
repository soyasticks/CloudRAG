"""
Orchestrates the query path: validates the question, calls Bedrock,
and shapes the raw Bedrock citation payload into the simple
{document, page, excerpt} structure the frontend expects.
"""

import time

from .bedrock_service import BedrockService
from .validation import validate_question


def _s3_uri_to_filename(uri: str) -> str:
    if not uri:
        return "unknown document"
    return uri.rstrip("/").split("/")[-1]


def _map_citations(raw_citations: list) -> list:
    """
    Bedrock's RetrieveAndGenerate response nests citations as:

    citations -> [ { retrievedReferences: [ { content, location, metadata } ] } ]

    We flatten that into a simple list of source objects for the frontend.
    """
    sources = []

    for citation in raw_citations:
        for ref in citation.get("retrievedReferences", []):
            content = ref.get("content", {}).get("text", "")
            location = ref.get("location", {}).get("s3Location", {})
            metadata = ref.get("metadata", {})

            document_name = _s3_uri_to_filename(location.get("uri", ""))
            page_number = metadata.get("page_number")  # see DEBUGGING_CHALLENGES.md

            sources.append(
                {
                    "document": document_name,
                    "page": page_number,
                    "excerpt": content[:300],
                }
            )

    return sources


def answer_question(question: str) -> dict:
    """
    Full query pipeline. Returns:
    {
        "answer": str,
        "sources": [ {document, page, excerpt}, ... ],
        "retrieval_latency_ms": int,   # approximate, see note below
        "generation_latency_ms": int,
        "total_latency_ms": int
    }

    Note: RetrieveAndGenerate is a single combined API call, so retrieval
    and generation latency cannot be measured separately without switching
    to separate Retrieve + Converse calls. We report total latency
    accurately and duplicate it into both fields with a flag, rather than
    inventing a fake split.
    """
    validate_question(question)

    start = time.time()
    bedrock = BedrockService()
    result = bedrock.retrieve_and_generate(question)
    total_ms = int((time.time() - start) * 1000)

    sources = _map_citations(result["raw_citations"])

    answer_text = result["answer"].strip()
    if not answer_text:
        answer_text = "I could not find sufficient information in the provided documents to answer this question."

    return {
        "answer": answer_text,
        "sources": sources,
        "total_latency_ms": total_ms,
        "latency_note": "retrieval+generation combined via RetrieveAndGenerate; not separately measurable",
    }
