"""
CLI entrypoint for the local RAG pipeline. Useful for iterating on
chunking/retrieval/prompting before touching AWS at all.

Usage:
    python ingest.py                 # build the index once
    python pipeline.py "What is the leave policy?"
"""

import sys

from retrieve import retrieve
from generate import generate_answer

INDEX_DIR = "data/index"


def ask(question: str, top_k: int = 4):
    chunks = retrieve(question, INDEX_DIR, top_k=top_k)

    if not chunks:
        print("No relevant chunks found.")
        return

    answer = generate_answer(question, chunks)

    print("\nANSWER\n" + "-" * 40)
    print(answer)
    print("\nSOURCES\n" + "-" * 40)
    for c in chunks:
        print(f"📄 {c['document']} — Page {c['page']} (score={c['score']:.3f})")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python pipeline.py "your question here"')
        sys.exit(1)
    ask(" ".join(sys.argv[1:]))
