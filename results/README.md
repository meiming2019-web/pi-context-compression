# Paired results

`paired5.csv` is the compact 30-row extract of the five-task paired evaluation: one row per task / round / arm.

Columns: task, round, arm, stop status, grading status, resolved, requests, uncached input, cache read, output, total input, estimated cost, previews, archive readbacks, unmatched reads, cap hit, cap value.

The full `runs/` directories (request journals, Pi event streams, patches, grader logs) are not committed.

## Cross-repository baseline

[`holdout50-a.csv`](holdout50-a.csv) contains one row per frozen task. It includes the reference check, agent stop status, official and validated outcomes, model request count, known usage and cost, first-request cache use, and any recovery. Empty fields indicate unavailable values. A valid empty patch is an unsuccessful attempt. The input and cache columns are disjoint. When `calls_without_usage` is positive, `known_cost_usd` covers only requests that returned usage. Issue type and Verified difficulty are included for descriptive comparisons. See the [baseline report](../docs/HOLDOUT-BASELINE.md).
