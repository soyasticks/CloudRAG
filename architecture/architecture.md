# CloudRAG — Serverless Enterprise Policy Document Q&A
## Phase 1: Architecture & Design

## 1. High-Level Architecture

```
┌─────────────┐     HTTPS      ┌──────────────┐
│   React UI   │ ─────────────▶│ API Gateway  │
│ (upload,     │◀───────────── │ (REST API)   │
│  ask, view)  │                └──────┬───────┘
└─────────────┘                        │
                                        ▼
                              ┌──────────────────┐
                              │   AWS Lambda      │
                              │ (2-3 functions)   │
                              └────┬─────────┬────┘
                                   │         │
                    ┌──────────────┘         └──────────────┐
                    ▼                                        ▼
          ┌──────────────────┐                    ┌────────────────────┐
          │   Amazon S3        │                   │ Bedrock Knowledge  │
          │ (raw PDF storage)  │◀── ingestion ─────│ Base (managed RAG) │
          └──────────────────┘                     │ + vector store     │
                                                     └─────────┬──────────┘
                                                               ▼
                                                     ┌────────────────────┐
                                                     │  Bedrock LLM        │
                                                     │ (e.g. Claude/Titan) │
                                                     └─────────┬──────────┘
                                                               ▼
                                                  Grounded answer + citations
                                                               │
                                                               ▼
                                                        back through
                                                     Lambda → API GW → React
```

Two Lambda functions only:

1. **`upload-handler`** — receives a PDF (or a pre-signed S3 URL request), stores it in S3, triggers ingestion into the Bedrock Knowledge Base.
2. **`query-handler`** — receives a user question, calls the Bedrock Knowledge Base `Retrieve`/`RetrieveAndGenerate` API, formats the response with citations, returns JSON to the frontend.

Resist the urge to add more Lambdas just to look sophisticated — an interviewer will ask why each one exists.

---

## 2. Folder Structure

```
cloudrag/
├── local-rag/                  # Phase 2: local MVP (no AWS)
│   ├── ingest.py                # load PDF → chunk → embed → store in FAISS
│   ├── retrieve.py              # query → embed → similarity search
│   ├── generate.py              # prompt construction + LLM call
│   ├── pipeline.py               # ties ingest/retrieve/generate together
│   └── data/
│       └── sample_policies/      # test PDFs
│
├── backend/                    # Phase 3: AWS Lambda code
│   ├── upload_handler/
│   │   ├── handler.py
│   │   └── requirements.txt
│   ├── query_handler/
│   │   ├── handler.py
│   │   └── requirements.txt
│   └── shared/                   # shared utils (logging, response formatting)
│
├── infra/                      # IaC (start manual in console, then codify)
│   ├── template.yaml             # SAM or CDK — added once manual setup works
│   └── README.md                 # documents manual console steps taken first
│
├── frontend/                   # Phase 4: React app
│   ├── src/
│   │   ├── components/
│   │   │   ├── UploadPanel.jsx
│   │   │   ├── QueryBox.jsx
│   │   │   ├── AnswerDisplay.jsx
│   │   │   └── SourceCitations.jsx
│   │   ├── api/
│   │   │   └── client.js
│   │   └── App.jsx
│   └── package.json
│
├── eval/                       # Phase 5
│   ├── eval_questions.json       # ~20 Q&A pairs w/ expected sources
│   ├── run_eval.py               # retrieval + faithfulness + latency scoring
│   └── results/
│
├── docs/
│   ├── architecture.md           # this file
│   └── decisions.md              # "why I chose X over Y" — useful for interviews
│
└── README.md
```

`local-rag/` stays alive even after moving to AWS — it's the fast iteration/debug environment and proof you understand what Bedrock is doing under the hood, not just calling an API blindly.

---

## 3. Component Responsibilities

| Component | Responsibility | Why it's needed |
|---|---|---|
| React frontend | Upload PDFs, submit questions, render answers + citations, show loading/error states | User-facing interface; makes the project demo-able |
| API Gateway | HTTPS entrypoint, routes `/upload` and `/query`, CORS, request validation | Decouples frontend from Lambda; gives throttling, auth hooks, a stable contract |
| Lambda (upload) | Accepts file, writes to S3, kicks off KB ingestion | Serverless = no server to manage, pay-per-invocation |
| Lambda (query) | Accepts question, calls Bedrock KB retrieve+generate, shapes response | Keeps business logic out of API Gateway |
| S3 | Durable storage of raw PDFs | Source of truth for documents; required data source type for Bedrock KB |
| Bedrock Knowledge Base | Manages chunking, embedding, vector store, retrieval | The "managed RAG" piece |
| Bedrock LLM | Generates grounded answer from retrieved chunks | The "G" in RAG |
| CloudWatch Logs | Logging/observability for both Lambdas | Debugging + the basic logging requirement |

---

## 4. AWS Services Used, and Why

- **S3** — cheapest, most durable place to store raw documents; also the required data source type for a Bedrock Knowledge Base.
- **Lambda** — document/query volume for a student project is bursty and near-zero most of the time. Paying for an always-on server would be wasteful; Lambda's pay-per-invocation model fits the actual traffic pattern.
- **API Gateway** — managed HTTPS endpoint with routing, request validation, and CORS config, standard pairing with Lambda.
- **Bedrock Knowledge Bases** — the managed version of what's built by hand locally (chunking + embedding + vector index + retrieval API). Using it demonstrates operating within a managed enterprise AI service — what most companies actually use — while the local FAISS version proves understanding of what's happening underneath. Using both is intentional, not redundant.
- **Bedrock LLM** — single-vendor consistency with the Knowledge Base (same IAM boundary, same billing, native `RetrieveAndGenerate` integration), avoiding a separate LLM API key/vendor.

**Deliberately excluded:** DynamoDB, Step Functions, SQS/SNS, Cognito (initially), CloudFront, ECS/EKS. None are needed for the core loop; adding them just to look "enterprise" invites an interview question you can't defend. Some (e.g. Cognito, DynamoDB for chat history) can return later as *justified* extensions.

---

## 5. Data Flow

**Ingestion (upload) path:**
1. User selects PDF in React UI → frontend requests a pre-signed S3 URL (or sends directly to `upload-handler`)
2. `upload-handler` Lambda stores file in S3 under a `documents/` prefix
3. Lambda triggers (or the KB's scheduled sync picks up) a Bedrock Knowledge Base ingestion job
4. Bedrock KB chunks the document, generates embeddings, stores them in its managed vector store
5. Frontend should be able to poll/display ingestion status ("processing")

**Query path:**
1. User types a question in React UI → POST to API Gateway `/query`
2. `query-handler` Lambda calls Bedrock KB `RetrieveAndGenerate` (or `Retrieve` + separate LLM call — decide deliberately, don't default)
3. Bedrock retrieves top-k relevant chunks, LLM generates an answer grounded in those chunks
4. Lambda formats response: `{ answer, sources: [{document, page, excerpt}], latency_ms }`
5. React renders answer + citation list

---

## 6. Request/Response Contract (draft)

```
POST /query
Request:  { "question": "What is the remote work policy after 90 days?" }
Response: {
  "answer": "...",
  "sources": [
    { "document": "hr_policy_v2.pdf", "page": 4, "excerpt": "..." }
  ],
  "latency_ms": 842
}
```

Keeping this contract documented early matters — one of the intentional debugging bugs later is a frontend/backend field-name mismatch, and having a written "intended" contract is how it gets caught.

---

## 7. Security Considerations

- No hardcoded credentials — Lambda uses IAM execution roles, not access keys.
- Least-privilege IAM — `upload-handler` gets `s3:PutObject` scoped to its bucket/prefix; `query-handler` gets `bedrock:Retrieve`/`RetrieveAndGenerate` only.
- API Gateway validates input (file type/size limits on upload, question length limits on query) to avoid abuse and runaway Bedrock costs.
- CORS explicitly configured (classic real bug source).
- No public S3 bucket — access only via pre-signed URLs or Lambda's IAM role.
- Auth: an API key on API Gateway (usage plan) is a reasonable, honest scope for a portfolio project. Full Cognito auth is legitimate "future work," not something to fake now.
- PII/sensitive docs: worth a README note on how sensitive content would be handled (e.g. not logging full document text, redaction) even if not fully implemented.

---

## 8. Cost Considerations

- **S3**: negligible for a handful of PDFs (~cents/month).
- **Lambda**: free tier covers 1M requests/month.
- **API Gateway**: free tier covers 1M calls/month (first 12 months); after that, still cents at this scale.
- **Bedrock Knowledge Base**: the cost driver to watch — underlying vector store (often OpenSearch Serverless) has an hourly minimum even at low usage, plus per-token embedding/generation costs.
- **Mitigation**: tear down the KB/OpenSearch Serverless collection when not actively developing/demoing; document exact teardown/recreation steps in `infra/README.md`.
- Set an AWS Budgets alarm on day one.

---

## 9. Local vs Cloud Split

| Stage | Local | Cloud |
|---|---|---|
| Document storage | filesystem | S3 |
| Chunking | own code (`local-rag/ingest.py`) | Bedrock KB (managed) |
| Embeddings | local embedding model or Bedrock embedding API called locally | Bedrock KB (managed) |
| Vector store | FAISS | OpenSearch Serverless (via Bedrock KB) |
| Retrieval | own cosine-similarity code | Bedrock KB `Retrieve` API |
| Generation | direct Bedrock/LLM API call from a script | Lambda → Bedrock |
| Frontend | not needed yet | React app hitting API Gateway |

Building it locally first means that when Bedrock KB does something in Phase 3 that looks like a black box, there's already a working mental model of what "chunking, embedding, retrieval" should look like underneath — making it possible to reason about whether the managed version is misbehaving or working as intended.
