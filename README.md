# Solari Analytics Support — Historical Ticket Assistant

An internal workspace that helps support agents find similar past tickets, inspect recorded resolutions, and judge whether those fixes apply to a new issue.

**Current state:** React frontend and FastAPI backend implemented; Supabase import and database API validation completed. The frontend production build passes. Full browser interaction and visual responsiveness verification remain incomplete. This is a hackathon prototype, not a production support system.

## 1. Getting started

### Prerequisites

- Python 3.13 and Node.js 22 were used during development.
- npm and a recent pip version.
- Internet access for dependency installation and the first embedding-model download.
- A Supabase PostgreSQL connection for database mode. Local JSON mode works without Supabase.

Commands below use **PowerShell**. Start in the repository root.

### Install the backend

```powershell
python -m venv .venv
python -m pip --python .venv/Scripts/python.exe install -r backend/requirements.txt
```

If `.venv` already exists, skip creating it. If virtual-environment creation fails during pip bootstrapping, the second command can install dependencies into the created environment using the system pip.

### Configure the application

Create a `.env` file at the repository root if one does not already exist. Preserve any existing credentials. For a quick local start:

```dotenv
SEARCH_BACKEND=json
SEARCH_MODE=hybrid
USE_SYNTHETIC_FEEDBACK=0
HISTORY_REFERENCE_DATE=2025-11-30
```

For Supabase, add your connection URI and change the backend setting:

```dotenv
SEARCH_BACKEND=postgres
DATABASE_URL=postgresql://USER:URL_ENCODED_PASSWORD@HOST:5432/postgres
```

Copy the actual URI from **Supabase → Connect → Session pooler**. Percent-encode special characters in the password. Keep `.env` private; the frontend never needs database credentials.

| Setting | Meaning |
| --- | --- |
| `SEARCH_BACKEND` | `json` for local files; `postgres` for Supabase |
| `SEARCH_MODE` | In JSON mode: `hybrid` or the `keyword` BM25 baseline. PostgreSQL mode always uses its hybrid adapter. |
| `HISTORY_REFERENCE_DATE` | End of the 12-month search window. Use `2025-11-30` for the supplied static dataset. |
| `USE_SYNTHETIC_FEEDBACK` | `1` enables explicitly labeled demo outcomes; `0` preserves unknown outcomes when real feedback is absent. |
| `STRONG_MATCH_THRESHOLD` | Optional useful-candidate cosine threshold; default `0.75` |
| `RELATED_MATCH_THRESHOLD` | Optional related-case threshold; default `0.25` |

Without an explicit reference date, JSON mode uses the latest historical ticket date; PostgreSQL mode uses today's date at startup. Restart the backend after configuration changes. Existing shell environment variables take precedence over `.env` values.

### Import into Supabase — database mode only

Skip this if the supplied dataset has already been imported into your project.

```powershell
.venv/Scripts/python.exe -m backend.check_connection
.venv/Scripts/python.exe -m backend.import_database --apply-schema
```

To also import the optional synthetic feedback fixtures:

```powershell
.venv/Scripts/python.exe -m backend.import_database --include-synthetic-feedback
```

Imports upsert stable IDs in one transaction. Repeating an import updates records without duplicating them. Reading synthetic feedback requires `USE_SYNTHETIC_FEEDBACK=1` separately. See [database setup](backend/DATABASE.md) for details.

### Run both services

**Terminal 1 — backend, from the repository root:**

```powershell
.venv/Scripts/python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Wait for `Application startup complete`. First hybrid startup downloads the model; subsequent runs reuse `.cache/`.

**Terminal 2 — frontend:**

```powershell
cd frontend
npm ci
npm run dev
```

Open the [agent workspace](http://127.0.0.1:5173/) or [interactive API documentation](http://127.0.0.1:8000/docs). Keep both terminals running. Stop a server with `Ctrl+C` in its terminal.

Vite forwards `/api/*` requests to `http://127.0.0.1:8000`, removing the `/api` prefix. To use another backend address, set `BACKEND_URL` in `frontend/.env.local` and restart Vite. This proxy is development/preview configuration; production needs an equivalent route or an explicitly configured API origin.

### Try the application

1. Load a provided example or enter a subject and description.
2. Optionally select the product area and result count.
3. Choose **Find similar cases**.
4. Review applicability labels, recorded fixes, feedback provenance, and differences.
5. Use **Open original case** to fetch the full historical record.

The sample buttons fetch actual starter examples from the backend. They do not use frontend mock data. Search does not create a new stored ticket.

### Troubleshooting

- **Connection reset or timeout:** run the connection checker. During development, one Wi-Fi network blocked PostgreSQL traffic; a phone hotspot worked. Also check Supabase project status and network restrictions.
- **Port already in use:** use the already-running service or stop it in its original terminal before restarting.
- **No historical tickets:** check the reference date and whether the database import completed.
- **Model download unavailable:** once cached, set `$env:HF_HUB_OFFLINE='1'`. For a model-free fallback, use JSON mode with `SEARCH_MODE=keyword`.
- **Frontend service error:** confirm the backend is running, its database is reachable, and the Vite proxy target is correct.

## 2. Problem overview

The case study assumes around 150 incoming support tickets daily. Agents sometimes repeat investigations or give inconsistent answers because they cannot easily discover similar resolved cases.

HCLTech Support provides historical evidence at the point of investigation. Support agents are the direct users; end customers benefit indirectly through potentially faster and more consistent support. The tool assists judgment rather than automatically applying fixes or sending replies.

## 3. Assumptions

- Search the latest **12 months** of available history. The prototype contains 40 synthetic historical tickets and four supplied incoming examples.
- `category` represents product area. Subjects and descriptions are available; incoming category may be missing or incorrect.
- Similar symptoms suggest candidate cases but do not establish the same root cause.
- The intended business process provides outcome feedback for resolved tickets. The actual sample data lacks it, so optional fixtures demonstrate that assumption without claiming real confirmation.
- A ticket's `resolved` status alone does not prove that its resolution succeeded.
- Returning related evidence or no useful match is acceptable. Scores are not probabilities of success.
- Agents need access-controlled historical data in production. Authentication and per-ticket authorization are **not implemented** in this prototype.
- Future growth is unspecified. Storage capacity, refresh targets, and production latency require measurement rather than assumptions based solely on ticket count.

## 4. Our approach

```text
Historical tickets → problem embeddings + searchable text + recorded resolutions
                                          ↓
New ticket → keyword and semantic retrieval → rank fusion → applicability checks
                                          ↓
                         Agent reviews source cases and recorded fixes
```

1. **Prepare history:** preserve source IDs and metadata; embed subject plus description; keep resolution notes separate.
2. **Retrieve:** get up to 50 keyword candidates and 50 semantic candidates within the history window.
3. **Combine:** deduplicate by ticket ID and fuse rank positions. Retain up to 50 combined candidates.
4. **Rank:** matching category receives a small boost. Eligible successful feedback boosts ranking; unsuccessful feedback lowers it.
5. **Assess:** identify supported integration/error signals, flag differences, and classify useful, related, or weak candidates.
6. **Present:** return five cases by default, with original descriptions, resolution notes, source lookup, and uncertainty visible.

### Implemented stack

| Layer | Technology |
| --- | --- |
| Frontend | React, TypeScript, Vite, responsive plain CSS |
| API | Python, FastAPI, Pydantic |
| Database | Supabase PostgreSQL, psycopg, pgvector |
| Embeddings | Sentence Transformers `all-MiniLM-L6-v2`, 384 dimensions |
| Evaluation | Python tests and authored synthetic relevance cases |

### API surface

| Endpoint | Purpose |
| --- | --- |
| `POST /search` | Retrieve and rank historical cases |
| `GET /tickets/{ticket_id}` | Fetch one source record within active history |
| `GET /examples` | Return the supplied incoming examples |
| `GET /health` | Report service status and active ticket count |

Example search body:

```json
{
  "subject": "Getting charged twice this month",
  "description": "Two charges appeared for a single monthly subscription payment.",
  "category": "billing",
  "limit": 5
}
```

The response includes `matches`, `assessment`, history metadata, and retrieval details. Each match includes the original ticket, ranking signals, applicability, outcome provenance, and detected differences. There are no authentication, ticket-editing, or feedback-submission endpoints yet.

## 5. Search and AI choices

**Keyword search:** the local baseline uses BM25. Database mode uses PostgreSQL English full-text search with an OR query and `ts_rank`; it is not BM25 and can order results differently. A GIN index supports text matching.

**Semantic search:** the same model embeds historical and incoming problem text. Normalized embeddings support cosine similarity. Supabase currently performs exact vector search; approximate indexing is deferred until needed.

**Rank fusion:** raw keyword and cosine scores have different scales, so candidates use reciprocal rank fusion:

```text
score = 1 / (60 + keyword_rank) + 1 / (60 + semantic_rank)
```

A missing rank contributes zero. Category agreement multiplies the score by `1.15`; confirmed successful feedback by `1.05`; confirmed unsuccessful feedback by `0.8`. Actual user feedback takes precedence over synthetic feedback in database mode. Recency currently acts through the history filter, not an additional ranking boost.

**Applicability:** regex extracts 4xx/5xx codes and `ERR_*` identifiers; a finite name list detects integrations. Missing or conflicting requested signals prevent a useful-candidate label. Otherwise, cosine thresholds of `0.75` and `0.25` distinguish useful, related, and weak cases. Unsuccessful resolutions are downgraded. These are development-tuned heuristics, not calibrated confidence estimates. Related context may remain visible even when the overall result is `no_useful_match`.

**Generation:** no LLM-generated answer is used. This is hybrid retrieval with case-based ranking. Grounded summaries are a future option if agent testing establishes a benefit.

## 6. Implementation milestones and validation

| Milestone | Status |
| --- | --- |
| Inspect samples and build BM25 baseline | Complete |
| Add embeddings, rank fusion, and model caching | Complete |
| Add applicability checks and optional synthetic outcomes | Complete, with heuristic limitations |
| Create Supabase schema and repeatable import | Complete; repeated import retained 40 records per imported table |
| Validate database search and API behavior | Complete for the tested synthetic scenarios |
| Build frontend and integrate API calls | Implemented; TypeScript and production build pass |
| Complete browser interaction and visual responsiveness QA | Pending; browser automation was blocked |
| Package and deploy publicly | Pending; hosting provider not finalized |

The latest database evaluation matched **22/22 expected assessments**, with all **14 directly labeled cases in the top three**. This small authored set does not establish production accuracy or superiority over keyword search. One original label was corrected after source review: a completed export with missing email was not equivalent to a failed scheduled report job. Correcting that label was not a ranking improvement. See [ranking review](backend/RANKING_REVIEW.md) and [database results](backend/database_evaluation_report.json).

### Run checks

From the repository root:

```powershell
.venv/Scripts/python.exe -m unittest backend.test_search backend.test_applicability -v
.venv/Scripts/python.exe -m backend.validate_api
.venv/Scripts/python.exe -m backend.validate_database_api
.venv/Scripts/python.exe -m backend.validate_database
```

`validate_api` exercises local hybrid mode. Database checks require Supabase access and the imported fixtures. `backend.evaluate` compares local retrieval and tunes thresholds on its development cases; it writes a separate local report and does not automatically change API defaults.

Build the frontend:

```powershell
cd frontend
npm run build
npm run preview
```

Preview still requires a running backend. `frontend/dist/` contains the production assets.

## 7. Future scope and open decisions

- **Quality:** stronger symptom/negation handling, version compatibility, multiple issues, and broader independently labeled evaluation. Related cases can still be poor investigative matches.
- **History maintenance:** incremental ingestion, source edits/deletions, reopened tickets, and selection across multiple resolution attempts. Current imports are manual.
- **Security:** agent authentication, authorization, sensitive-data handling, and least-privilege database access before production exposure.
- **Agent workflow:** feedback submission, resolution-attempt management, duplicate incident grouping, and integration with a real support platform.
- **Performance:** establish response-time and concurrency targets; measure memory, database pooling, cold starts, and vector-index tradeoffs.
- **Deployment:** choose a provider and budget; package the embedding model; configure secrets and production frontend/API routing. Google Cloud Run was proposed, but no deployment has been made and a zero-cost bill is not guaranteed.
- **Optional generation:** source-grounded summaries after retrieval usefulness is demonstrated. Automated customer replies and fixes remain outside the current scope.

## Repository guide

```text
frontend/                  React application, API client, styles, Vite configuration
backend/                   FastAPI, search engines, applicability, import and validation
starter_kit/data/          Original historical and incoming sample tickets
DESIGN.md                  Concise architecture and backend logic explanation
backend/DATABASE.md        Supabase setup and import details
backend/RANKING_REVIEW.md   Evaluation-label correction and ranking diagnosis
.env                       Local configuration and secrets (ignored by Git)
.cache/                    Downloaded model and cached embeddings (ignored by Git)
```
