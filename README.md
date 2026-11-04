# HCLTech Support — Support Ticket Assistant

## Problem

HCLTech Support handles approximately 150 new support tickets per day. Agents can miss relevant past cases, leading to repeated investigation and inconsistent responses. We propose an internal tool that shows agents similar historical tickets and their recorded resolutions when they open a new ticket.

HCLTech Support is the customer purchasing the solution. Its support agents are the direct users; retail customers benefit through faster, more consistent support.

## Working assumptions

- **History:** Search the latest 12 months of available ticket history. This is our initial scope, not a claim that older data cannot be stored. Actual coverage depends on the supplied dataset.
- **Volume:** Start from approximately 150 incoming tickets per day. Future growth is expected, but its magnitude remains unspecified.
- **Input:** Tickets usually include a product area and free-text description. Missing, incorrect, or multiple product areas must be handled gracefully.
- **Similarity:** Compare issue descriptions, symptoms, product areas, and exact signals such as error codes. Similar symptoms do not establish the same root cause or guarantee that a fix applies.
- **Resolution evidence:** A closed ticket is not necessarily successfully resolved. Prefer cases with a clear recorded resolution, and expose missing or uncertain evidence.
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

Keyword search provides a baseline. Semantic search is a candidate for finding similar issues expressed in different words; we will assess whether combining the two improves retrieval on the supplied data.

Regex can extract predictable signals such as error codes, HTTP statuses, and product versions. It is a supporting technique rather than the primary method for understanding similarity.

Retrieval delivers the core requested functionality. An optional LLM layer could summarize retrieved cases and resolutions, forming a retrieval-augmented generation (RAG) workflow. Any generated summary must remain supported by source records, preserve important conditions, and avoid inventing missing resolutions. Search similarity scores must not be presented as the probability that a fix will work.

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

Before finalizing implementation, inspect the starter kit and dataset, establish a small evaluation set, and define response-time expectations, refresh frequency, growth scenarios, and the source system's access rules. Storage and indexing choices should follow those findings.

Business success means less repeated investigation and more appropriate, consistent responses. Prototype evaluation will focus on retrieval usefulness, resolution evidence, handling of weak matches, and response time; business impact requires validation with agents.

