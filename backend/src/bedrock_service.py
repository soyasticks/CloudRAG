"""
Wrapper around Amazon Bedrock Agent Runtime (Knowledge Base retrieval +
generation).

Uses RetrieveAndGenerate so Bedrock handles combining retrieved chunks
with the foundation model call — keeps this Lambda thin.
"""

import boto3
from botocore.exceptions import ClientError

from .config import Config

RAG_PROMPT_TEMPLATE = """You are answering questions about internal company policy documents.

Rules:
1. Answer ONLY using the retrieved context below. Do not use outside knowledge.
2. If the answer is not present in the context, say clearly that you could not
   find sufficient information in the provided documents. Do not guess.
3. Keep the answer concise (2-4 sentences) but complete enough to be useful.
4. Do not fabricate policy numbers, dates, or page references.

Context:
$search_results$

Question: $query$

Answer:"""


class BedrockService:
    def __init__(self):
        self.client = boto3.client("bedrock-agent-runtime", region_name=Config.AWS_REGION)

    def retrieve_and_generate(self, question: str) -> dict:
        """
        Calls Bedrock Knowledge Base RetrieveAndGenerate.

        Returns a dict: { "answer": str, "raw_citations": list }
        """
        try:
            response = self.client.retrieve_and_generate(
                input={"text": question},
                retrieveAndGenerateConfiguration={
                    "type": "KNOWLEDGE_BASE",
                    "knowledgeBaseConfiguration": {
                        "knowledgeBaseId": Config.KNOWLEDGE_BASE_ID,
                        "modelArn": Config.BEDROCK_MODEL_ARN,
                        "retrievalConfiguration": {
                            "vectorSearchConfiguration": {
                                "numberOfResults": Config.RETRIEVAL_TOP_K
                            }
                        },
                        "generationConfiguration": {
                            "promptTemplate": {"textPromptTemplate": RAG_PROMPT_TEMPLATE}
                        },
                    },
                },
            )
        except ClientError as exc:
            raise RuntimeError(f"Bedrock call failed: {exc.response['Error']['Code']}") from exc

        answer = response.get("output", {}).get("text", "")
        citations = response.get("citations", [])

        return {"answer": answer, "raw_citations": citations}
