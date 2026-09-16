"""
Local, non-AWS ingestion pipeline: PDF -> text -> chunks -> embeddings -> FAISS index.

This is NOT a mock of AWS — it's a genuinely separate, simpler local RAG
implementation used for offline development and for understanding what
Bedrock Knowledge Bases do internally. It does not pretend to call AWS.

Requires: pypdf, sentence-transformers, faiss-cpu, numpy
    pip install pypdf sentence-transformers faiss-cpu numpy
"""

import os
import pickle

import faiss
import numpy as np
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

CHUNK_SIZE = 800       # characters per chunk
CHUNK_OVERLAP = 100    # character overlap between consecutive chunks
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

_model = None


def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def load_pdf_pages(path: str) -> list:
    """Returns a list of {page_number, text} for a single PDF."""
    reader = PdfReader(path)
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages.append({"page_number": i + 1, "text": text})
    return pages


def chunk_pages(pages: list, document_name: str) -> list:
    """
    Splits page text into overlapping chunks, preserving page number and
    source document as metadata on each chunk. This is what a managed
    service like Bedrock KB does for you in the cloud version.
    """
    chunks = []
    for page in pages:
        text = page["text"]
        start = 0
        while start < len(text):
            end = start + CHUNK_SIZE
            chunk_text = text[start:end]
            if chunk_text.strip():
                chunks.append(
                    {
                        "text": chunk_text,
                        "document": document_name,
                        "page": page["page_number"],
                    }
                )
            start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


def build_index(pdf_dir: str, index_dir: str):
    """
    Reads all PDFs in pdf_dir, chunks them, embeds each chunk, and writes
    a FAISS index + metadata sidecar file to index_dir.
    """
    os.makedirs(index_dir, exist_ok=True)
    model = _get_model()

    all_chunks = []
    for filename in sorted(os.listdir(pdf_dir)):
        if not filename.lower().endswith(".pdf"):
            continue
        path = os.path.join(pdf_dir, filename)
        pages = load_pdf_pages(path)
        chunks = chunk_pages(pages, filename)
        all_chunks.extend(chunks)
        print(f"[ingest] {filename}: {len(pages)} pages -> {len(chunks)} chunks")

    if not all_chunks:
        raise RuntimeError(f"No PDF files found in {pdf_dir}")

    texts = [c["text"] for c in all_chunks]
    embeddings = model.encode(texts, show_progress_bar=True, normalize_embeddings=True)
    embeddings = np.array(embeddings, dtype="float32")

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # inner product on normalized vectors = cosine similarity
    index.add(embeddings)

    faiss.write_index(index, os.path.join(index_dir, "index.faiss"))
    with open(os.path.join(index_dir, "metadata.pkl"), "wb") as f:
        pickle.dump(all_chunks, f)

    print(f"[ingest] Indexed {len(all_chunks)} chunks from {pdf_dir} -> {index_dir}")


if __name__ == "__main__":
    build_index(pdf_dir="data/sample_policies", index_dir="data/index")
