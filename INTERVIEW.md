# Interview Preparation

For each question: what you should understand conceptually, a short
answer you could say out loud in 15-20 seconds, and a deeper explanation
for follow-ups. Fill in specifics from *your own* debugging experience
where indicated — a generic answer is weaker than "I actually hit this."

---

### What is RAG?

**Understand:** RAG augments an LLM's answer with retrieved external
context at inference time, instead of relying only on what the model
learned during training.

**Short answer:** "Retrieval-Augmented Generation retrieves relevant
document chunks for a query and feeds them to the LLM as context, so the
answer is grounded in your actual data instead of the model's training
data."

**Deeper:** The model's parametric knowledge is frozen at training time
and can't reflect private/internal documents. RAG sidesteps that by
doing a retrieval step (semantic search over embedded chunks) before
generation, injecting the retrieved text into the prompt. This also gives
you citations "for free," since you know exactly which chunks were used.

---

### Why RAG instead of fine-tuning?

**Understand:** Fine-tuning bakes knowledge into model weights; RAG keeps
knowledge external and swappable.

**Short answer:** "Fine-tuning is expensive to update and doesn't easily
give you per-answer citations. RAG lets me add or change documents
without retraining anything, and I get grounded citations naturally."

**Deeper:** Policy documents change often — fine-tuning would mean
retraining every time a policy updates. RAG just means re-ingesting the
changed document. Fine-tuning is better suited to teaching a model a
*style* or *behavior*, not injecting frequently-changing *facts*. Also
worth mentioning: fine-tuning doesn't reduce hallucination risk the way
grounding retrieved text does.

---

### What is an embedding?

**Understand:** A dense numeric vector representing the semantic meaning
of text, such that similar meanings end up close together in vector
space.

**Short answer:** "It's a numeric representation of text where semantic
similarity translates into geometric closeness, so I can find relevant
chunks by comparing vectors instead of matching keywords."

**Deeper:** Be ready to explain that embeddings capture meaning, not
exact words — "annual leave" and "vacation days" should embed close
together. Know roughly how similarity is computed (cosine similarity /
inner product on normalized vectors, as used in the local FAISS
implementation in this project).

---

### How does vector retrieval work?

**Understand:** Query text is embedded with the same model used for
documents, then compared against stored document embeddings to find the
nearest neighbors.

**Short answer:** "The question gets embedded the same way the document
chunks were, then I do a nearest-neighbor search — locally with FAISS,
or in the cloud version through Bedrock Knowledge Base's managed vector
store — and return the top-k closest chunks."

**Deeper:** Mention top-k as a tunable parameter with a real tradeoff:
too low and you miss relevant context; too high and you dilute the
prompt with irrelevant chunks (and increase cost/latency). You should be
able to say what top-k this project uses and why — including whether you
had to change it.

---

### Why use Bedrock (and Bedrock Knowledge Bases specifically)?

**Understand:** Bedrock gives managed access to foundation models plus a
managed RAG pipeline (chunking, embedding, vector store, retrieval) via
Knowledge Bases, without self-hosting infrastructure.

**Short answer:** "Bedrock Knowledge Bases handle chunking, embedding,
and vector storage for me in a managed way, and integrate directly with
Bedrock's LLMs through RetrieveAndGenerate — so I'm not running my own
vector database in production."

**Deeper:** Be ready for "why not just run FAISS in production too?" —
the honest answer is operational: no server to manage, IAM-based access
control instead of a separate auth system, and it's what a lot of real
companies actually use rather than self-hosting. The local FAISS version
in this project exists specifically so you *understand* what Bedrock KB
is doing, not because it's what you'd deploy.

---

### Why use S3?

**Short answer:** "S3 is the durable, cheap object store for the raw
PDFs, and it's also the required data source type for a Bedrock
Knowledge Base — there wasn't really an alternative that made sense."

---

### Why Lambda?

**Short answer:** "Traffic for this project is bursty and low-volume —
paying for an always-on server would be wasteful. Lambda's pay-per-
invocation model fits, and it's the standard serverless pairing with API
Gateway."

**Deeper:** Know the tradeoff — cold starts, 15-minute max execution,
and that this wouldn't necessarily be the right call at high sustained
traffic (where a container-based service might make more sense).

---

### Why API Gateway?

**Short answer:** "It gives me a managed HTTPS endpoint with routing,
CORS, and request validation in front of Lambda, without hand-rolling a
web server."

---

### What is a Knowledge Base (in Bedrock terms)?

**Short answer:** "It's the managed component that owns ingestion
(chunking + embedding) from an S3 data source and exposes Retrieve /
RetrieveAndGenerate APIs backed by a vector store — OpenSearch Serverless
in this project."

---

### What happens during document ingestion?

**Short answer:** "The PDF lands in S3 via the upload Lambda, then the
Knowledge Base's ingestion job — either on a sync schedule or triggered
manually — parses it, splits it into chunks, embeds each chunk, and
writes the vectors plus metadata into the vector store."

**Deeper:** Be honest here about what's actually automated vs. manual in
your deployment — did you wire up automatic sync-on-upload, or is sync
manual/scheduled? Don't claim automation you didn't build.

---

### What happens when a user asks a question?

**Short answer:** "The question goes to API Gateway, into the query
Lambda, which calls Bedrock's RetrieveAndGenerate — that embeds the
question, retrieves the top-k nearest chunks, builds a prompt with them,
and calls the LLM. The Lambda reshapes the citations into a simple
document/page/excerpt structure and returns it to the frontend."

---

### How does the system reduce hallucinations?

**Short answer:** "The prompt explicitly instructs the model to answer
only from retrieved context and to say when the answer isn't present,
rather than guessing. Grounding in retrieved text is the main lever —
it's not perfect."

**Deeper:** Be honest about the limits — the model can still misread
context, and this project has no automated faithfulness scoring beyond a
crude keyword check in `evaluate.py`. Don't overclaim.

---

### How do citations work?

**Short answer:** "Bedrock returns citation metadata alongside the
generated answer — which retrieved chunks contributed to the response,
and where they came from in S3. The Lambda maps that into a
document-name-and-page structure for the frontend."

**Deeper:** You should be able to explain what happens when metadata is
missing or malformed — this project has a real, discoverable bug in
exactly this area (see `DEBUGGING_CHALLENGES.md`). Talking through how
you found and fixed it is a genuinely strong interview answer.

---

### How would you improve retrieval?

Reasonable answers: tune top-k and chunk size/overlap based on real
eval results; try hybrid search (keyword + vector); add re-ranking; use
better chunk boundaries (e.g. respecting paragraph/section structure
instead of fixed character counts); add metadata filtering (e.g. by
document type).

---

### How would you reduce latency?

Reasonable answers: cache repeated/similar queries; reduce top-k if it's
higher than needed; use a smaller/faster model for simpler questions;
warm Lambda with provisioned concurrency if cold starts are the
bottleneck (check CloudWatch to confirm before "fixing" this, though).

---

### How would you scale the system?

Reasonable answers: API Gateway + Lambda already scale automatically for
request volume; the real scaling question is usually the Knowledge
Base/vector store and cost, plus adding queuing for very large ingestion
batches rather than synchronous upload-triggers-everything.

---

### How would you secure it?

Reasonable answers already implemented: IAM roles (no hardcoded creds),
least-privilege S3/Bedrock policies, input validation, CORS restricted to
a specific origin, no document content in logs. Reasonable *next* steps
to mention honestly as not-yet-done: Cognito-based user auth, per-user
document isolation, rate limiting beyond API Gateway defaults.

---

### What are the limitations of this project?

Be honest and specific — this is what separates a student project from a
fake "production-ready" claim:
- Evaluation is a heuristic keyword-match smoke test, not a validated
  accuracy benchmark.
- No user authentication — anyone with the API URL can upload/query.
- No automated ingestion trigger wired to S3 events by default (sync
  timing depends on your KB configuration).
- Retrieval and generation latency can't be measured separately when
  using `RetrieveAndGenerate` as a single call.
- Chat history is frontend-only/session-based, not persisted.
- Only tested against a small, self-authored sample document set.
