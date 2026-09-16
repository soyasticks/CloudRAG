"""
Local generation step: build a grounded prompt from retrieved chunks and
call an LLM. Uses Bedrock's Converse API directly if AWS credentials are
configured locally (aws configure), so this is real Bedrock usage, not a
mock — it's just not going through API Gateway/Lambda/Knowledge Base yet.
"""

import boto3

MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"

PROMPT_TEMPLATE = """You are answering questions about internal company policy documents.

Rules:
1. Answer ONLY using the context below. Do not use outside knowledge.
2. If the answer is not present in the context, say clearly that you could
   not find sufficient information in the provided documents.
3. Keep the answer concise (2-4 sentences).
4. Do not fabricate page numbers or facts not present in the context.

Context:
{context}

Question: {question}

Answer:"""


def build_context(chunks: list) -> str:
    parts = []
    for c in chunks:
        parts.append(f"[{c['document']}, page {c['page']}]\n{c['text']}")
    return "\n\n---\n\n".join(parts)


def generate_answer(question: str, chunks: list, region: str = "us-east-1") -> str:
    context = build_context(chunks)
    prompt = PROMPT_TEMPLATE.format(context=context, question=question)

    client = boto3.client("bedrock-runtime", region_name=region)
    response = client.converse(
        modelId=MODEL_ID,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 400, "temperature": 0.1},
    )

    return response["output"]["message"]["content"][0]["text"]
