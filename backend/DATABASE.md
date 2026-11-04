# Supabase setup

Live Supabase import and validation completed. Local `.env` now selects PostgreSQL; JSON remains available as a fallback. Two imports left counts at 40 tickets, 40 resolution attempts, and 40 synthetic feedback records. Database API checks passed. The 16-case evaluation achieved 15/16 matching assessments and 9/10 directly labeled cases in the top three; H8 is a known retrieval regression. See `database_evaluation_report.json`.

1. Create a free project at https://supabase.com/dashboard and save its database password.
2. Open **Connect**, choose the **Session pooler** PostgreSQL URI, and copy it. Use its actual hostname, username, and port.
3. Copy `.env.example` to `.env` in the repository root. Replace `DATABASE_URL` with that URI and its password placeholder with your URL-encoded database password. Do not paste credentials into chat or commit `.env`.
4. Leave `SEARCH_BACKEND=json` while importing. Keep `HISTORY_REFERENCE_DATE=2025-11-30` for the synthetic dataset; PostgreSQL mode otherwise uses today's date.
5. Install dependencies and run the explicit schema/import command below.
6. Change `SEARCH_BACKEND=postgres`, start FastAPI, and inspect `/health` and `/search` in `/docs`.

```powershell
python -m pip --python .venv/Scripts/python.exe install -r backend/requirements.txt
.venv/Scripts/python.exe -m backend.import_database --apply-schema
# Optional: import clearly labeled synthetic outcomes too.
.venv/Scripts/python.exe -m backend.import_database --include-synthetic-feedback
.venv/Scripts/python.exe -m uvicorn backend.main:app --reload
```

Imports run in one transaction and upsert stable source IDs. Repeating an import updates demo records without duplication; it does not delete other records. Skipping the feedback flag preserves existing feedback. Reading synthetic feedback additionally requires `USE_SYNTHETIC_FEEDBACK=1`. Actual user feedback takes precedence over demo feedback.

The private `support` schema holds tickets (including 384-dimensional embeddings), resolution attempts, and feedback. The demo currently selects the imported source attempt per ticket; supporting multiple chronological attempts in search remains future work. Schema setup enables pgvector and must run with a role permitted to create the extension and tables. Credentials remain server-side. This is a single-organization prototype; agent authentication and per-ticket authorization must be added before external production access.

Database search uses PostgreSQL `ts_rank` with an OR text query and exact pgvector cosine search. It is not BM25, so ordering may change. It combines ranks and applies the existing applicability checks. Exact vector search avoids approximate-index recall changes at demo scale. A GIN index supports text filtering; benchmark vector indexing for larger datasets.

Live validation must verify: import twice without changing counts, 40 tickets under the demo reference date, source resolutions, both outcome modes, all existing relevance cases, date filtering, and API behavior. Do not claim local JSON results as database validation.

References: [Supabase PostgreSQL connections](https://supabase.com/docs/guides/database/connecting-to-postgres), [vector columns](https://supabase.com/docs/guides/ai/vector-columns), [PostgreSQL text ranking](https://www.postgresql.org/docs/current/functions-textsearch.html).
