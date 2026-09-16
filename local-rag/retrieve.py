"""
Local retrieval: embed a query, search the FAISS index, return top-k chunks
with their metadata.
"""

import pickle

import faiss
import numpy as np

from ingest import _get_model, EMBEDDING_MODEL  # noqa: F401 (kept for reference)


def load_index(index_dir: str):
    index = faiss.read_index(f"{index_dir}/index.faiss")
    with open(f"{index_dir}/metadata.pkl", "rb") as f:
        metadata = pickle.load(f)
    return index, metadata


def retrieve(query: str, index_dir: str, top_k: int = 4) -> list:
    """
    Returns the top_k most similar chunks to the query, each as:
    { text, document, page, score }
    """
    model = _get_model()
    index, metadata = load_index(index_dir)

    query_vec = model.encode([query], normalize_embeddings=True)
    query_vec = np.array(query_vec, dtype="float32")

    scores, indices = index.search(query_vec, top_k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue
        chunk = metadata[idx]
        results.append(
            {
                "text": chunk["text"],
                "document": chunk["document"],
                "page": chunk["page"],
                "score": float(score),
            }
        )
    return results
