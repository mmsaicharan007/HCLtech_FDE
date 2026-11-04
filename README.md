# HCLTech Support — Support Ticket Assistant

## Problem

## Running the initial backend

The implementation now includes JSON-backed BM25 and hybrid retrieval using `all-MiniLM-L6-v2` embeddings, cosine similarity, and reciprocal rank fusion. Keyword mode remains the default pending successful model installation and evaluation; set `$env:SEARCH_MODE = 'hybrid'` in PowerShell to enable hybrid retrieval. Supabase persistence and calibrated no-match decisions remain subsequent milestones.

The first hybrid startup downloads the model. Models and content-keyed historical embeddings are cached under `.cache/`. Query and historical text use the same model. Run `.venv/Scripts/python.exe -m backend.evaluate` to compare the supplied examples. Only the chart and duplicate-billing examples have direct-match labels; the password-email and Snowflake cases require applicability review. Four examples cannot establish general retrieval quality.

From the repository root in PowerShell:

```powershell
python -m venv .venv
python -m pip --python .venv/Scripts/python.exe install -r backend/requirements.txt
.venv/Scripts/python.exe -m uvicorn backend.main:app --reload
```

Open http://127.0.0.1:8000/docs to try `POST /search`. Supply `subject`, `description`, optional `category`, and `limit` (1–50). Other endpoints: `GET /health`, `GET /examples`, and `GET /tickets/{ticket_id}`.

The demo's 12-month window ends at the latest historical ticket date. Set `HISTORY_REFERENCE_DATE` to an ISO date to override it. Outcomes remain explicitly unknown until separate synthetic feedback is supplied. Keyword candidates require agent review, including for the unfamiliar Snowflake example.

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

