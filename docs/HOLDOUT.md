# Cross-repository replication

The frozen sample is stored in [holdout50.json](../bench/tasks/holdout50.json). The 50 task IDs were selected before this issue-based classification. All are Python repository tasks. The five repositories have equal weight by design.

## Coverage before execution

These editorial labels describe the primary behavior named in the issue. They are exploratory and independent of patch contents, agent trajectories and grading. The numeric suffixes below are grouped by their official repository.

| Issue type | Tasks | Repository and issue suffix |
|---|---:|---|
| Behavior and API contracts | 13 | django/django: 16333, 11141, 14787; pydata/xarray: 3993; pytest-dev/pytest: 10081, 7571, 7236, 10051, 7490, 6197; sphinx-doc/sphinx: 11510; sympy/sympy: 18211, 22456 |
| Computation and query correctness | 9 | django/django: 11734, 15930; pydata/xarray: 3151; sympy/sympy: 13372, 24562, 18199, 15875, 13480, 15349 |
| Data representation and metadata | 7 | pydata/xarray: 2905, 7233, 4629, 7393, 7229, 6992, 4094 |
| Formatting, rendering and diagnostics | 13 | django/django: 14539, 12858, 11820, 13794; pytest-dev/pytest: 7432; sphinx-doc/sphinx: 8265, 10614, 7910, 8621, 10435, 9602, 9367; sympy/sympy: 19346 |
| Compatibility and integration | 6 | pytest-dev/pytest: 5840, 7324, 5809; sphinx-doc/sphinx: 8475, 7590; sympy/sympy: 14976 |
| Performance and resource use | 2 | django/django: 11333; pydata/xarray: 6721 |

Verified difficulty labels are estimates of human fix time. The counts are 20 (<15 min fix), 24 (15 min - 1 hour), 4 (1-4 hours), 2 (>4 hours).

## Comparison

Run stock Pi and the 128-token tail policy once per task, following the frozen A/B order, with the same Pi version, model, prompt, base commit, 64-call cap and 900-second timeout. Keep the five development tasks separate. Preflight each task environment and validate the repository-specific build and official grading evidence before model execution. Record infrastructure failures and incomplete usage explicitly.

Use all 50 planned pairs as the primary cohort, including zero-trigger tasks. Report total input (cached plus uncached), cost, task-level paired differences and how many tasks have lower input. For repair outcomes show A-only passes, B-only passes, joint passes, joint failures and missing pairs. Report per-repository results and how often the extension triggers. Treat issue-type and difficulty splits as descriptive, especially the two performance tasks. Report a paired interval that resamples tasks within each repository for the overall input-cost comparison. An unresolved infrastructure error or missing billable usage must not become a zero-cost run.

Extending the finding to a second model, language or terminal task family requires a separate cohort, reported separately.
