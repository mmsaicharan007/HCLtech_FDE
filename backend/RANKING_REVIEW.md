# Export-email case review

The original H8 query says a CSV export finished but its email did not arrive. Source T-1403 instead concerns a scheduled weekly report whose job failed after a dashboard rename. Its resolution fixes job lookup, not delivery after a successful export.

The original direct-match label was too strong. H8 is now a development example expecting related cases; T-1403 is explicitly annotated as related context. Earlier 9/10 database retrieval and 15/16 assessment reports used that flawed label and should be interpreted accordingly. Correcting a judgment is not a ranking improvement.

Live diagnosis before any ranking changes:

| Ticket | Keyword rank | Semantic rank | Cosine |
| --- | --- | --- | --- |
| T-1401 | 1 | 1 | 0.6373 |
| T-1404 | 2 | 2 | 0.4228 |
| T-1104 | 3 | 3 | 0.3911 |
| T-1402 | 4 | 5 | 0.3789 |
| T-1405 | 6 | 4 | 0.3908 |
| T-1403 | 5 | 6 | 0.3538 |

Both retrievers rank T-1403 weakly. Increasing semantic weight therefore cannot resolve this by favoring an already-strong semantic result. No ticket-specific boost or threshold reduction was applied. All candidates remain below the useful threshold, correctly requiring investigation.

Added development contrasts distinguish a missing scheduled report, missing records in a delivered CSV, and a PDF timeout. Three further synthetic cases were authored before running evaluation and marked fresh_holdout. Existing reviewed holdout cases are regression coverage, not independent unseen evidence. Thresholds remain unchanged; inspect database_evaluation_report.json for actual results. The new set remains small and manually labeled.

Live evaluation result: 22/22 assessments matched the corrected labels; all 14 directly labeled cases appeared in the top three. All three fresh synthetic holdout cases matched expectations. This reflects corrected labels and added coverage, not a measured algorithm improvement. No production-quality guarantee follows from this small set.
