# CloudRAG

Serverless Retrieval-Augmented Generation (RAG) app for answering questions
over enterprise policy PDF documents, built on AWS Bedrock Knowledge Bases.

Student portfolio project — see [Limitations](#limitations) for an honest
account of what this is and isn't.

## Problem

Enterprise policy documents (employee handbooks, leave policy, IT security
policy, expense policy) are long, scattered across multiple PDFs, and
tedious to search manually. Employees end up asking HR/IT the same
questions repeatedly, or acting on outdated/half-remembered policy details.

## Solution

CloudRAG lets a user upload policy PDFs and ask natural-language questions
about them. The system retrieves the relevant passages and asks an LLM to
answer strictly from that retrieved context, returning the answer alongside
the specific document/page it came from. If nothing relevant is found, it
says so instead of guessing.

## Architecture

```
React (Vite)
     |
     v
API Gateway  --- CORS restricted to configured frontend origin
     |
     v
AWS Lambda (upload / query / health)
     |                    \
     v                     v
Amazon S3          Bedrock Knowledge Base (managed chunking/embedding/vector store)
(raw PDFs)                 |
                            v
                     Bedrock LLM (RetrieveAndGenerate)
                            |
                            v
                 Grounded answer + source citations
```

Full breakdown of components, data flow, and design tradeoffs:
[`architecture/architecture.md`](architecture/architecture.md).

## Features

- PDF upload with client-side type/size validation and progress feedback
- Documents stored in S3, ingested into a Bedrock Knowledge Base
- Natural-language question answering grounded in retrieved document chunks
- Source citations (document name + page) returned with every answer
- Follow-up questions supported via frontend-maintained chat history
- Structured error handling (no raw AWS stack traces reach the client)
- Request-ID-tagged backend logging
- A small (~20 question) evaluation set with a heuristic scoring script

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | React + Vite | Fast dev loop, no unnecessary framework overhead |
| Backend | Python on AWS Lambda | Serverless fits bursty, low-volume student-project traffic |
| API | API Gateway (REST) | Managed HTTPS, routing, CORS, request validation |
| Storage | Amazon S3 | Durable object storage; required KB data source type |
| RAG | Amazon Bedrock Knowledge Bases | Managed chunking/embedding/vector store + retrieval API |
| LLM | Bedrock foundation model (Claude 3 Haiku by default) | Native `RetrieveAndGenerate` integration, single-vendor IAM boundary |
| IaC | AWS SAM | Readable CloudFormation-based deploy for Lambda/API GW/S3/IAM |
| Local dev | FAISS + sentence-transformers | Understand the RAG pipeline without needing AWS for every iteration |

No Kubernetes, no message queues, no microservices, no separate database —
deliberately. See `architecture/architecture.md` for what was excluded and why.

## Project Structure

```
CloudRAG/
├── README.md
├── DEBUGGING_CHALLENGES.md
├── INTERVIEW.md
├── architecture/architecture.md
├── frontend/            React (Vite) app
├── backend/              Lambda handlers + services (src/), tests/
├── local-rag/            Standalone local FAISS-based RAG pipeline
├── infrastructure/       AWS SAM template + IAM policy reference
├── evaluation/            test_questions.json + evaluate.py
└── sample_documents/     Where you put your own sample policy PDFs
```

## RAG Pipeline

1. **Ingestion**: PDF uploaded → stored in S3 → Bedrock Knowledge Base syncs
   the S3 data source, chunks the document, embeds each chunk, stores
   vectors + metadata.
2. **Retrieval**: user question is embedded and compared against stored
   chunk embeddings; the top-k nearest chunks are returned (`RETRIEVAL_TOP_K`
   env var — see `infrastructure/template.yaml`).
3. **Generation**: retrieved chunks are inserted into a prompt template
   (`backend/src/bedrock_service.py`) instructing the model to answer only
   from context and to say when it can't.
4. **Citations**: Bedrock's citation metadata is mapped to a simple
   `{document, page, excerpt}` structure in `backend/src/rag_service.py`.

The `local-rag/` folder implements the same conceptual pipeline by hand
(PyPDF + sentence-transformers + FAISS) for local iteration and so the
managed Bedrock version isn't a black box.

## AWS Services (and why each one)

- **S3** — durable storage for raw PDFs; also the required data source type
  for a Bedrock Knowledge Base.
- **Lambda** — pay-per-invocation fits low, bursty traffic; no server to
  manage or patch.
- **API Gateway** — managed HTTPS entrypoint, CORS, request routing, in
  front of Lambda.
- **Bedrock Knowledge Bases** — managed chunking/embedding/vector-store/
  retrieval, so a vector database isn't self-hosted in production. The
  local FAISS pipeline exists specifically to understand what this is
  doing internally, not to duplicate it in prod.
- **Bedrock LLM** — single-vendor integration with the Knowledge Base via
  `RetrieveAndGenerate`; no separate LLM API key to manage.

## Local Setup

### Backend (local RAG pipeline, no AWS needed for iteration on chunking/retrieval)

```bash
cd local-rag
pip install pypdf sentence-transformers faiss-cpu numpy boto3
# add your PDFs to data/sample_policies/ first — see sample_documents/README.md
python ingest.py
python pipeline.py "How many annual leave days are employees entitled to?"
```

(`generate.py` calls Bedrock's Converse API directly, so this last step
does need AWS credentials configured via `aws configure` — everything
before generation is fully local.)

### Backend unit tests

```bash
cd backend
pip install -r requirements.txt pytest
python -m pytest tests/ -v
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env   # then set VITE_API_BASE_URL after deploying the backend
npm run dev
```

## AWS Setup / Deployment

1. **Create a Bedrock Knowledge Base manually first** (console or CLI) —
   S3 as the data source, OpenSearch Serverless as the vector store. SAM
   deployment of Knowledge Bases + OpenSearch Serverless collections isn't
   fully mature, so this step is deliberately manual. Note the Knowledge
   Base ID.
2. **Deploy infrastructure:**
   ```bash
   cd infrastructure
   sam build
   sam deploy --guided
   # provide KnowledgeBaseId, and AllowedOrigin matching your frontend's actual origin
   ```
3. **Upload sample documents** to the S3 bucket created by the stack (via
   the frontend's upload UI, or directly to S3), then trigger/wait for a
   Knowledge Base sync.
4. **Point the frontend** at the API Gateway URL from the stack output
   (`ApiUrl`), via `frontend/.env`.

## Environment Variables

**Backend (Lambda, set via `infrastructure/template.yaml`):**

| Variable | Purpose |
|---|---|
| `DOCUMENT_BUCKET` | S3 bucket name for uploaded PDFs |
| `KNOWLEDGE_BASE_ID` | Bedrock Knowledge Base ID |
| `BEDROCK_MODEL_ARN` | Foundation model ARN used for generation |
| `RETRIEVAL_TOP_K` | Number of chunks retrieved per query |
| `LOG_LEVEL` | Python logging level |

**Frontend (`frontend/.env`, copy from `.env.example`):**

| Variable | Purpose |
|---|---|
| `VITE_API_BASE_URL` | API Gateway invoke URL |

## Deployment

See "AWS Setup / Deployment" above. Tear down with `sam delete` from
`infrastructure/` when not actively developing — the Knowledge Base's
OpenSearch Serverless collection has an hourly cost even at low usage; see
`architecture/architecture.md` for cost notes.

## API Endpoints

### `POST /upload`
Query param: `filename`. Body: raw PDF bytes. Header: `Content-Type: application/pdf`.

Response `200`:
```json
{ "documentId": "uuid", "s3Key": "documents/uuid_file.pdf", "status": "uploaded", "message": "..." }
```
Error `400`: `{ "error": "message", "field": "filename" }`

### `POST /query`
Body: `{ "question": "string" }`

Response `200`:
```json
{
  "answer": "string",
  "sources": [ { "document": "Leave Policy.pdf", "page": 7, "excerpt": "..." } ],
  "latencyMs": 842,
  "requestId": "uuid"
}
```
Error `400`/`502`/`500`: `{ "error": "message" }`

### `GET /health`
Response `200`: `{ "status": "ok" }` or `503` with `{ "status": "unhealthy", "missing_config": [...] }`

## Evaluation

`evaluation/test_questions.json` has ~20 questions against a hypothetical
4-document policy set, including two deliberately unanswerable questions
to check graceful "not found" handling.

```bash
cd evaluation
pip install requests
python evaluate.py --api-url https://your-api.execute-api.us-east-1.amazonaws.com/prod
```

This produces keyword-match and expected-source-hit rates plus latency —
**heuristic signals, not validated accuracy metrics.** See the docstring in
`evaluate.py` for exactly what this can and can't detect.

## Security

- No hardcoded credentials anywhere; Lambda uses IAM execution roles
- Least-privilege IAM (see `infrastructure/iam/policy.json`)
- Input validation on both upload (type/size) and query (length, non-empty)
- CORS restricted to a configured origin (not left wide open in the deployed API config)
- No public S3 bucket access
- Document content not logged; only lengths/counts logged
- Raw AWS errors are not returned to the client — errors are mapped to plain messages

## Limitations

Read this before writing resume bullets:

- No user authentication — anyone with the API URL can upload or query
- Evaluation is a heuristic keyword/smoke test, not a validated benchmark
- Retrieval and generation latency aren't separable when using the
  combined `RetrieveAndGenerate` call
- Chat history is session-only in the frontend, not persisted server-side
- No automated re-ranking, hybrid search, or chunk-size tuning beyond
  what's configured
- Tested only against a small, self-authored sample document set
- Not "production-ready" — no load testing, no multi-tenant isolation,
  no SLA

## Future Improvements

- Cognito-based auth and per-user document isolation
- S3 event-triggered ingestion instead of relying on KB sync scheduling
- Hybrid (keyword + vector) retrieval and re-ranking
- Persisted chat history (DynamoDB) if genuinely needed
- Separate retrieval/generation calls for finer-grained latency metrics
- A more rigorous evaluation framework (e.g. RAGAS-style faithfulness scoring)

## Screenshots

_Add screenshots here after running the app end-to-end:_

- `docs/screenshots/upload.png` — document upload flow
- `docs/screenshots/chat.png` — question + grounded answer with citations
- `docs/screenshots/error-state.png` — an error state (e.g. unsupported file type)
