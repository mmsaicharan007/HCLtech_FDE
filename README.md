# HCLTech Support — Support Ticket Assistant

## Problem

## Running the initial backend

### Database integration

**Evaluation correction:** source review found that H8 was incorrectly labeled a direct match: its export completed, while T-1403 describes a failed scheduled job. It now expects related evidence and belongs to development. Earlier metrics below are historical and include that label error. See [ranking review](backend/RANKING_REVIEW.md); no ranking improvement is claimed from correcting a label.

Supabase is connected and the local configuration selects `SEARCH_BACKEND=postgres`. Two imports completed without duplication: 40 tickets, 40 resolution attempts, and 40 explicitly synthetic feedback records. Database API checks passed for sample searches, resolution lookup, missing tickets, invalid inputs, feedback modes, and history filtering. Synthetic feedback remains disabled by default; enable `USE_SYNTHETIC_FEEDBACK=1` to demonstrate it.

The database evaluation matched 15/16 expected assessments and retrieved 9/10 directly labeled cases in the top three. H8 (export email missing) remains classified as related; its expected case T-1403 fell outside the database top three, whereas local hybrid ranked it third. PostgreSQL `ts_rank` differs from BM25, and this regression is an open ranking issue. Results are in `backend/database_evaluation_report.json`. The original network reset PostgreSQL connections; the phone hotspot allowed successful access.

Follow [database setup](backend/DATABASE.md) for reproducible import and validation commands. Restart the API after changing `.env`. Use `SEARCH_BACKEND=json` for the local fallback.

The implementation now includes JSON-backed BM25 and hybrid retrieval using `all-MiniLM-L6-v2` embeddings, cosine similarity, and reciprocal rank fusion. Hybrid mode is the validated default; set `$env:SEARCH_MODE = 'keyword'` in PowerShell for the baseline. Supabase persistence remains a subsequent milestone. Applicability now uses transparent heuristics with development-tuned thresholds.

Validation completed: nine search/applicability tests and hybrid API checks passed, including optional synthetic feedback provenance and failed-attempt handling. The broader evaluation has 16 manually authored synthetic cases, divided into eight development cases and eight holdout cases. Development-selected thresholds are 0.75 for useful candidates and 0.25 for related cases. They are model- and dataset-specific heuristics, not probabilities.

Development assessment accuracy was 8/8; holdout assessment accuracy was 7/8 with zero false-useful classifications. Both methods retrieved the relevant ticket in the top three for all five directly labeled holdout cases. The holdout export-email case H8 was conservatively labeled related despite a useful historical case. These small synthetic results do not establish production accuracy or a hybrid advantage. Full case-level results are in `backend/evaluation_report.json`.

Hybrid responses now include `assessment` (`useful_cases`, `related_cases`, or `no_useful_match`), per-case `applicability`, extracted `signals`, and `differences`. Related candidates remain visible even when no useful match is found; they are investigative context, not recommended fixes. A finite integration-name list and error-code regex detect some mismatches; they do not establish root causes. Version compatibility, arbitrary integration discovery, multi-issue reasoning, and resolution clustering remain future work.

Synthetic outcome fixtures are in `backend/synthetic_feedback.json`. Set `$env:USE_SYNTHETIC_FEEDBACK = '1'` before starting the API to enable them. Every fixture is invented and labeled `synthetic_demo`, with an attempt ID; T-1202 demonstrates an unsuccessful attempt. They are not inferred customer feedback. Leave this option unset to preserve unknown source outcomes. Successful fixtures receive a small ranking boost and unsuccessful attempts cannot become useful candidates. These labels demonstrate the mechanism rather than validate real-world outcome quality.

Run evaluation with `.venv/Scripts/python.exe -m backend.evaluate`, API checks with `.venv/Scripts/python.exe -m backend.validate_api`, and tests with `python -m unittest backend.test_search backend.test_applicability -v`. Override heuristic thresholds through `STRONG_MATCH_THRESHOLD` and `RELATED_MATCH_THRESHOLD` only after evaluating the effect.

The first hybrid startup downloads the model. Models and content-keyed historical embeddings are cached under `.cache/`. Query and historical text use the same model. Run `.venv/Scripts/python.exe -m backend.evaluate` to compare the supplied examples. Only the chart and duplicate-billing examples have direct-match labels; the password-email and Snowflake cases require applicability review. Four examples cannot establish general retrieval quality.

From the repository root in PowerShell:

```powershell
python -m venv .venv
python -m pip --python .venv/Scripts/python.exe install -r backend/requirements.txt
.venv/Scripts/python.exe -m uvicorn backend.main:app --reload
```

Open http://127.0.0.1:8000/docs to try `POST /search`. Supply `subject`, `description`, optional `category`, and `limit` (1–50). Other endpoints: `GET /health`, `GET /examples`, and `GET /tickets/{ticket_id}`.

The demo's 12-month window ends at the latest historical ticket date. Set `HISTORY_REFERENCE_DATE` to an ISO date to override it. Outcomes remain explicitly unknown unless optional synthetic feedback is enabled. Keyword candidates require agent review, including for the unfamiliar Snowflake example.

Run baseline checks with `python -m unittest backend.test_search -v`.

## Customer problem

HCLTech Support handles approximately 150 new support tickets per day. Agents can miss relevant past cases, leading to repeated investigation and inconsistent responses. We propose an internal tool that shows agents similar historical tickets and their recorded resolutions when they open a new ticket.

HCLTech Support is the customer purchasing the solution. Its support agents are the direct users; retail customers benefit through faster, more consistent support.

## Working assumptions

- **History:** Search the latest 12 months of available ticket history. This is our initial scope, not a claim that older data cannot be stored. Actual coverage depends on the supplied dataset.
- **Volume:** Start from approximately 150 incoming tickets per day. Future growth is expected, but its magnitude remains unspecified.
- **Input:** Tickets usually include a product area and free-text description. Missing, incorrect, or multiple product areas must be handled gracefully.
- **Similarity:** Compare issue descriptions, symptoms, product areas, and exact signals such as error codes. Similar symptoms do not establish the same root cause or guarantee that a fix applies.
- **Resolution feedback:** Every resolved ticket has explicit user feedback indicating whether the issue was actually fixed. Associate feedback with individual resolution attempts so failed suggestions are distinguishable from successful fixes. Prioritize confirmed successful resolutions; historical success does not guarantee applicability to a new ticket. Reopened tickets require reassessment.
- **Synthetic feedback:** If the supplied dataset lacks outcome feedback, add explicitly labeled synthetic feedback for the prototype rather than treating resolution notes as confirmed success.
- **Agent judgment:** Agents review the evidence and decide what action to take. The prototype does not automatically apply fixes or send customer replies.
- **Access:** Results must respect the agent's access permissions and protect sensitive ticket information.
- **Weak matches:** Returning no useful match is an acceptable outcome. The interface should make weak evidence clear.
- **Freshness:** New resolutions and edits, reopened tickets, and deletions should be reflected in searchable data. The refresh target remains to be defined.
- **Data availability:** Historical tickets are available for ingestion. Their schema, completeness, resolution quality, and source-link availability still require inspection.

## High-level approach

1. **Prepare the history.** Ingest tickets within the 12-month window, preserve source identifiers and relevant metadata, identify recorded resolutions, and group duplicate cases where possible. Keep full records accessible through source links when available.
2. **Retrieve candidate cases.** Search using the new ticket's description, symptoms, product area, and exact signals. Prioritize matching product areas, with broader retrieval when metadata is missing or results are weak. Permission restrictions always remain enforced.
3. **Rank useful evidence.** Consider relevance, resolution quality, recency, and available applicability details such as product version or integration. Recency alone should not outweigh a more applicable case.
4. **Present results to the agent.** Show a small set of useful past tickets, their recorded fixes, supporting source material, and relevant differences. Clearly indicate when no useful resolved case is found.
5. **Evaluate usefulness.** Check whether useful resolved cases appear near the top, whether misleading results are minimized, and whether weak matches are communicated clearly. Assess response time and collect agent feedback.

## Search and AI choices

We will implement hybrid retrieval with case-based ranking: combine keyword search and semantic search, then assess whether historical successful fixes are applicable. Keep keyword-only retrieval as an evaluation baseline.

Embed meaningful problem descriptions with labeled context such as product area and integration. Store resolutions separately from the problem representation to avoid generic troubleshooting advice dominating similarity. Precompute historical embeddings and regenerate them only when relevant content changes.

Use cosine similarity for semantic retrieval and rank fusion to combine keyword and semantic result lists, rather than adding their raw scores. Merge and deduplicate results into an initial candidate pool of roughly 50, then rank by relevance, exact signals, product/integration/version compatibility, confirmed success, and recency. Tune candidate counts and ranking settings through evaluation.

Show the strongest 3–5 distinct cases with recorded resolutions, feedback evidence, source links or source records, and relevant differences. Distinguish no relevant case from a relevant case without a successful resolution.

Regex can extract predictable signals such as error codes, HTTP statuses, and product versions. It is a supporting technique rather than the primary method for understanding similarity.

Retrieval delivers the core requested functionality. Defer LLM summaries until retrieval is reliable and evaluation demonstrates a need. Any future summary must remain supported by source records, preserve important conditions, and avoid inventing missing resolutions. Search similarity scores must not be presented as the probability that a fix will work.

## Finalized technology stack

| Layer | Choice | Purpose |
| --- | --- | --- |
| Frontend | React, TypeScript, Vite | Internal agent interface |
| Styling | Tailwind CSS | Ticket and result presentation |
| Backend | Python, FastAPI | Extraction, retrieval, ranking, feedback APIs |
| Database | Supabase PostgreSQL | Tickets, metadata, resolution attempts, and feedback |
| Search | PostgreSQL full-text search and pgvector | Keyword and vector retrieval in one database |
| Embeddings | Small Sentence Transformers model | Semantic representations; select model through evaluation |
| Evaluation | Python scripts and curated cases | Compare keyword-only and hybrid retrieval |

## Deployment plan

Deploy the React frontend as a Render static site, FastAPI as a Render free web service, and the database on Supabase Free. Free hosting is a prototype target, subject to current service limits and measured database size and backend memory use.

Render free web services can sleep after inactivity and have an ephemeral filesystem. Persist tickets and feedback in PostgreSQL and keep a local demo fallback. Validate embedding model memory use and startup latency before finalizing deployment. Supabase Free database capacity must be checked against ticket text, embeddings, and index sizes before claiming that a full year of production history fits.

Hosting references: [Render free services](https://render.com/docs/free) and [Supabase pricing](https://supabase.com/pricing).

## Implementation milestones

1. Inspect the starter dataset and utility code; verify fields, dates, resolution records, and feedback availability.
2. Implement ingestion, database schema, structured signal extraction, and a keyword-search baseline.
3. Add embeddings, hybrid retrieval, candidate fusion, and transparent applicability ranking.
4. Build the agent interface: incoming ticket, suggested cases, resolution evidence, and feedback.
5. Evaluate paraphrases, exact error matches, similar symptoms with different causes, incorrect metadata, duplicates, and no-match cases. Measure candidate retrieval separately from final ranking, plus response time.
6. Deploy, verify persistence and resource limits, and prepare a local demonstration fallback.

The first end-to-end milestone is: open an example ticket, retrieve useful historical cases, inspect confirmed fixes, and correctly handle the supplied unusual ticket with no strong match.

## Important edge cases

- Similar symptoms with different causes or fixes.
- Missing descriptions, incorrect product areas, or tickets containing multiple issues.
- Closed tickets without resolutions, reopened tickets, and unsuccessful suggestions within a conversation.
- Conflicting fixes, outdated workarounds, and version-specific resolutions.
- Duplicate incident tickets crowding out other useful results.
- No relevant historical case, or a relevant case without a usable resolution.
- Sensitive information, restricted tickets, and instructions embedded in ticket text; ticket content is data, not system instructions.
- Search failures, stale records, and updates or deletions in the source system.

## Prototype scope and open decisions

The prototype focuses on discovering historical cases and making their resolutions reviewable. Automatic replies, automatic fixes, incident detection, and attachment interpretation are potential future extensions.

The architecture above is agreed. Remaining decisions include embedding model selection, ranking settings and no-match criteria, response-time expectations, refresh frequency, growth scenarios, and the source system's access rules. Validate these against the supplied data and deployment constraints. Define the reference date for the 12-month window explicitly so static synthetic data is not silently excluded by the live calendar.

Business success means less repeated investigation and more appropriate, consistent responses. Prototype evaluation will focus on retrieval usefulness, resolution evidence, handling of weak matches, and response time; business impact requires validation with agents.

