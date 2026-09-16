"""
Basic evaluation harness for CloudRAG.

IMPORTANT — read this before trusting any numbers this script prints:

This is NOT a rigorous evaluation methodology. It does simple keyword
containment checks and exact source-filename matching. It cannot detect:
  - answers that are correct but phrased without the expected keywords
  - partial correctness / partially hallucinated answers
  - retrieval that found the *wrong* chunk of the *right* document
  - subtle factual errors within an otherwise plausible-sounding answer

It is a smoke test and a latency/cost sanity check for a student project,
not a substitute for human review or a proper eval framework (e.g. RAGAS).
Treat every number this prints as a rough signal, not a benchmark result.

Usage:
    python evaluate.py --api-url https://your-api.execute-api.us-east-1.amazonaws.com/prod
    python evaluate.py --local   # calls local-rag/pipeline.py instead of the API
"""

import argparse
import json
import time
import sys
import os

import requests


def load_questions(path="test_questions.json"):
    with open(path, "r") as f:
        return json.load(f)


def call_api(api_url: str, question: str) -> dict:
    start = time.time()
    try:
        response = requests.post(f"{api_url}/query", json={"question": question}, timeout=30)
        elapsed_ms = int((time.time() - start) * 1000)
        response.raise_for_status()
        data = response.json()
        return {
            "answer": data.get("answer", ""),
            "sources": data.get("sources", []),
            "client_measured_latency_ms": elapsed_ms,
            "error": None,
        }
    except Exception as exc:
        elapsed_ms = int((time.time() - start) * 1000)
        return {"answer": "", "sources": [], "client_measured_latency_ms": elapsed_ms, "error": str(exc)}


def score_question(q: dict, result: dict) -> dict:
    answer_lower = result["answer"].lower()

    keyword_hits = sum(1 for kw in q["expected_answer_contains"] if kw.lower() in answer_lower)
    keyword_score = keyword_hits / len(q["expected_answer_contains"]) if q["expected_answer_contains"] else 0

    source_found = False
    if q["expected_source"]:
        source_found = any(
            q["expected_source"].lower() in (s.get("document") or "").lower()
            for s in result["sources"]
        )
    else:
        # Expected no answer to be found — pass if the model declined appropriately
        source_found = len(result["sources"]) == 0 or keyword_score > 0

    return {
        "id": q["id"],
        "question": q["question"],
        "keyword_score": round(keyword_score, 2),
        "expected_source_found": source_found,
        "latency_ms": result["client_measured_latency_ms"],
        "error": result["error"],
    }


def run(api_url: str, questions_path: str):
    questions = load_questions(questions_path)
    results = []

    for q in questions:
        print(f"[eval] {q['id']}: {q['question']}")
        result = call_api(api_url, q["question"])
        scored = score_question(q, result)
        results.append(scored)
        if result["error"]:
            print(f"   ERROR: {result['error']}")
        else:
            print(f"   keyword_score={scored['keyword_score']} source_found={scored['expected_source_found']} latency={scored['latency_ms']}ms")

    total = len(results)
    errors = sum(1 for r in results if r["error"])
    avg_keyword_score = sum(r["keyword_score"] for r in results if not r["error"]) / max(total - errors, 1)
    source_accuracy = sum(1 for r in results if r["expected_source_found"] and not r["error"]) / max(total - errors, 1)
    avg_latency = sum(r["latency_ms"] for r in results) / total

    print("\n" + "=" * 50)
    print(f"Questions run:            {total}")
    print(f"Errors:                   {errors}")
    print(f"Avg keyword match score:  {avg_keyword_score:.2f}  (rough proxy, not accuracy)")
    print(f"Expected-source hit rate: {source_accuracy:.2f}  (rough proxy, not accuracy)")
    print(f"Avg client-measured latency: {avg_latency:.0f}ms")
    print("=" * 50)
    print("Reminder: these are heuristic signals for a student project, not")
    print("validated accuracy metrics. See docstring at the top of this file.")

    os.makedirs("results", exist_ok=True)
    out_path = f"results/eval_{int(time.time())}.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nFull results written to {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", help="Base API Gateway URL, e.g. https://xxx.execute-api.us-east-1.amazonaws.com/prod")
    parser.add_argument("--questions", default="test_questions.json")
    args = parser.parse_args()

    if not args.api_url:
        print("Error: --api-url is required (local mode not yet wired up — see README limitations).")
        sys.exit(1)

    run(args.api_url, args.questions)
