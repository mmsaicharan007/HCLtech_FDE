# HCLTech Support — Design Document

## Overview and scope

HCLTech Support helps internal support agents investigate incoming tickets by finding relevant historical cases and their recorded resolutions. The business goal is to reduce repeated investigation and improve response consistency at an assumed intake of approximately 150 tickets per day. Agents retain responsibility for deciding whether a fix applies and responding to customers.

The prototype searches a 12-month history and uses 40 supplied synthetic tickets. `category` represents product area; `subject` and `description` represent the problem. Incoming tickets may omit category. The demo uses **2025-11-30** as its reference date so the static dataset remains searchable; database mode otherwise defaults to today's date at startup.

The chosen approach is **hybrid retrieval with case-based ranking**. Keyword search captures explicit terminology, semantic search captures similar meaning, and applicability checks qualify the results. There is no generated answer or automatic remediation. The interface presents original descriptions and resolution notes for review.

## Architecture and data

```text
React + TypeScript frontend
    → /api proxy during local Vite development
    → FastAPI → query embedding + retrieval + applicability checks
    → Supabase PostgreSQL: full-text search + pgvector
    ← ranked cases, original resolutions, provenance, and warnings
```

The frontend supports ticket entry, backend-provided examples, result filtering, and original-ticket dialogs. FastAPI exposes `POST /search`, `GET /tickets/{ticket_id}`, `GET /examples`, and `GET /health`. Search accepts subject, description, optional category, and a result limit of 1–50; at least one text field must be nonblank. The default response contains five cases.

The private `support` database schema contains three tables:

| Table | Responsibility |
| --- | --- |
| `tickets` | Source ID, problem text, category, tags, date, status, model identifier, 384-dimensional embedding, and generated full-text document |
| `resolution_attempts` | Recorded resolution notes linked to a ticket through an attempt ID |
| `outcome_feedback` | Attempt outcome and provenance: actual user feedback or synthetic demo feedback |

The importer computes normalized embeddings using `sentence-transformers/all-MiniLM-L6-v2`, then transactionally upserts stable IDs. Repeated imports update existing records without duplication. Historical embeddings are cached locally by model name and input content. Resolution text is stored separately from the embedded problem, preventing generic fix language from dominating problem similarity. Current retrieval selects the imported source attempt per ticket; chronological selection among multiple attempts is future work.

## Core backend logic

### 1. Prepare the query and retrieve candidates

The backend combines subject and description. A tokenizer extracts lowercase alphanumeric terms, removes a small stopword list, and deduplicates them. The same original problem text is embedded using the historical embedding model.

Two SQL searches operate within the configured 12-month date window:

- **Keyword retrieval:** an English `tsvector` matches an OR query through `to_tsquery`. PostgreSQL `ts_rank` orders up to 50 candidates; a GIN index supports text matching. OR matching retains cases that share only part of the query.
- **Semantic retrieval:** pgvector orders up to 50 candidates by cosine distance, restricted to the same embedding model. Similarity is `1 − cosine_distance`. Exact vector search is sufficient for the small corpus; approximate indexing is deferred until scale measurements justify it.

The union is deduplicated by ticket ID and joined with source resolutions and feedback. PostgreSQL text ranking is **not BM25**: the JSON-backed local baseline implements BM25, and database results are evaluated separately.

### 2. Fuse ranks and apply contextual weights

Keyword and semantic raw scores have different scales. Reciprocal rank fusion combines their rank positions instead:

```text
score = 1 / (60 + keyword_rank) + 1 / (60 + semantic_rank)
```

An absent rank contributes zero. Matching product area multiplies the score by **1.15**; mismatching areas remain searchable because metadata may be incorrect. Confirmed successful outcomes multiply by **1.05**, while confirmed unsuccessful outcomes multiply by **0.8**. The combined list is sorted and capped at 50 candidates before applicability classification. Ticket IDs break score ties deterministically.

The source dataset has no actual outcome feedback. Optional fixtures explicitly labeled `synthetic_demo` demonstrate this mechanism; they are disabled by default. Without eligible feedback, outcomes remain `unknown`. Database retrieval prioritizes actual user feedback over synthetic feedback when both exist. Neither historical success nor a retrieval score establishes that a fix will work for a new issue.

### 3. Assess applicability and present evidence

Regex extracts HTTP-style 4xx/5xx codes and `ERR_*` identifiers; a finite integration-name list identifies products such as Salesforce, Okta, and Snowflake. Requested signals absent from a historical problem produce difference warnings and prevent that case from being classified as useful. Category differences are warnings rather than exclusions.

For cases without signal mismatches, cosine similarity determines a provisional label: **useful candidate** at or above **0.75**, **related** from **0.25**, otherwise **weak**. A confirmed unsuccessful resolution is downgraded to related. These development-selected thresholds are dataset-specific heuristics, not calibrated probabilities.

Useful candidates are placed before related and weak cases while preserving the previous order within each group. The overall assessment is `useful_cases` when an eligible useful candidate exists, `related_cases` when eligible related evidence exists, or `no_useful_match` otherwise. Related context can still be returned when no useful match exists. Responses include the source case, recorded resolution, ranks, cosine similarity, shared terms, outcome provenance, and detected differences.

## Validation, tradeoffs, and next steps

Live Supabase checks verified repeated imports, 40 stored tickets, resolution lookup, example searches, feedback modes, request validation, and date filtering. The revised 22-case synthetic evaluation matched all expected assessments and retrieved all 14 directly labeled cases within the top three. These small authored tests do not establish production accuracy or superiority over keyword search.

Source review corrected one test: a completed export with missing email was incorrectly labeled equivalent to a failed scheduled report job. The label changed; ranking did not. The system still returns weak investigative matches for some symptom differences and does not fully model negation, execution state, product versions, or root causes.

Current boundaries include manual ingestion, no agent authentication or per-ticket authorization, no write APIs, and no public deployment. Credentials remain server-side, but production access controls are still required. Local frontend proxying also needs a production routing arrangement. Next priorities are end-to-end browser verification and deployment packaging; later work includes broader independent evaluation, improved symptom reasoning, incremental ingestion, connection pooling, and scale testing.
