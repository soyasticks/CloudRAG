# Debugging Challenges

This codebase runs, but it was not handed to you bug-free. There are
several realistic issues seeded into it — the kind you'd actually hit
setting up a project like this, not contrived puzzles. None of them are
security vulnerabilities, and none of them can cause runaway AWS charges.

Solutions are **not** in this file, and they're not commented in the code
either. Diagnose them the way you would in a real job: read logs, inspect
network requests, read stack traces, and reason about the code.

Work through these roughly in the order you'll naturally encounter them
(deployment → upload → query → citations → retrieval quality). Use
`git blame` / a diff against a fresh clone if you get truly stuck, or come
back and ask — but try first.

---

### Challenge 1 — Deployment fails (or the query Lambda errors immediately after deploying)

After `sam deploy`, the `/query` endpoint returns a 500 on literally every
request, including the simplest possible question. CloudWatch shows an
exception being raised very early in the Lambda's execution, before it
ever gets close to calling Bedrock.

**Where to look:** CloudWatch Logs for the query Lambda, right at cold
start / first invocation. What is Python actually complaining about?

---

### Challenge 2 — The API "can't find" its configuration even though you set it

`GET /health` returns `503` with a `missing_config` field listing a
variable you're fairly sure you set. You go check the Lambda console (or
your SAM template) and the environment variable *is* there.

**Where to look:** Compare the exact variable name the Lambda console
shows against the exact variable name the code reads. Case and spelling
both matter.

---

### Challenge 3 — Upload works, querying works, but the browser blocks it anyway

Calling the API directly (curl / Postman) works fine for both `/upload`
and `/query`. From the deployed React frontend, though, the browser
console shows a request being blocked, and the network tab shows the
request never actually completing successfully.

**Where to look:** What origin is the frontend actually running on, and
what origin does the API's CORS configuration currently allow? Check both
the preflight (`OPTIONS`) response and the actual response headers —
they don't have to agree.

---

### Challenge 4 — The answer displays, but part of the citation looks broken

A question that should have a clear answer returns a good, grounded
answer, and a source document name shows up correctly. But something
about the source entry looks wrong when you inspect it closely — either
in the rendered UI or in the raw JSON response.

**Where to look:** `console.log` the full API response before it gets
rendered. Compare the shape of what Bedrock actually returns (check the
Lambda logs) against what the frontend assumes is there.

---

### Challenge 5 — A number displayed to the user doesn't match what you'd expect

Somewhere in the chat UI, a numeric value renders as something clearly
wrong (not just "off by a bit" — it looks like a type error, not a bad
calculation).

**Where to look:** Trace that specific field name from the Lambda
response, through the API Gateway response, into the frontend component
that renders it. Does the field name survive that whole trip unchanged?

---

### Challenge 6 — Retrieval quality is worse than it should be

Answers to broader questions (ones where the relevant information might
be spread across a couple of sentences, or where the most relevant chunk
isn't obviously the very first one) come back vague, incomplete, or with
only one source cited even when multiple documents plausibly contain
related information.

**Where to look:** How many chunks is the system actually asking Bedrock
to retrieve per query? Is that a reasonable number for a multi-document
knowledge base?

---

### Challenge 7 — A perfectly reasonable-looking question produces a confusing error instead of an answer

Most questions work fine. But certain input — not obviously malformed —
causes the query endpoint to return a generic 500 instead of either a
real answer or a clean "I don't have enough information" response.

**Where to look:** What exactly counts as "empty" in the input validation
logic? Try a few edge-case inputs a real user might accidentally send
(extra spaces, etc.) and see which ones pass validation but shouldn't,
or vice versa.

---

## A note on process

For each challenge:
1. Reproduce it.
2. Form a hypothesis before you go read the fix.
3. Check the hypothesis against logs/network/code.
4. Only then change code.

This is also good practice for actually talking about this project in an
interview — "I hit X, suspected Y, confirmed it in the logs, and fixed it
by Z" is a much stronger answer than "it just worked."
