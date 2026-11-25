# Short-tail holdout on SWE-bench Verified

B retained **5 of 8 baseline passes** in a post hoc policy analysis excluding one provider outage. Of the three observed policy regressions, two reached the request cap and one completed with a failing patch. The preregistered end-to-end result was **5 of 9** retained, including the outage as an unsuccessful attempt. On **31** complete usage pairs, aggregate input fell **1.4%** and estimated cost rose **6.7%** relative to A. The five-task pilot’s joint savings and retention did not replicate on this sample.

The frozen holdout contains 50 tasks across five Python repositories. Stock Pi (A) ran first. The 128-token short-tail extension (B) made 48 model attempts. Both arms used Pi 1.6.0, gpt-4.1-mini-2025-04-14, one attempt per eligible task, a 64-request cap and a 900-second timeout. Two failed reference preflights remain in the extract.

## Repair outcomes

Both arms returned a validated outcome on 44 tasks. B passed two tasks that A failed. B also passed django-16333, whose A grade was unavailable, bringing B to eight confirmed passes on 47 valid outcomes.

| Cohort | Both pass | A only | B only | Both fail | Missing |
|---|---:|---:|---:|---:|---:|
| Frozen cohort | 5 | 4 | 2 | 33 | 6 |
| Both completed with valid outcomes | 5 | 1 | 2 | 19 | 0 |
| django/django | 0 | 1 | 0 | 7 | 2 |
| pydata/xarray | 1 | 1 | 0 | 7 | 1 |
| pytest-dev/pytest | 1 | 1 | 0 | 8 | 0 |
| sphinx-doc/sphinx | 1 | 0 | 0 | 6 | 3 |
| sympy/sympy | 2 | 1 | 2 | 5 | 0 |

On pytest-7571, all four B requests returned HTTP 502. The agent received zero successful responses and emitted zero previews. The runner recorded an empty patch and a failed outcome. The post hoc policy analysis excludes that task from both the paired test and the baseline-pass denominator. It includes capped runs and runs with no preview when the model received a successful response.

| Analysis | Valid pairs | A passes retained | A passes lost (exact 95% CI on loss fraction) | A only / B only | Exact McNemar p |
|---|---:|---:|---|---:|---:|
| Preregistered end-to-end, including the outage | 44 | 5/9 | 4/9 (13.7%–78.8%) | 4 / 2 | 0.6875 |
| Post hoc policy analysis, excluding the outage | 43 | 5/8 | 3/8 (8.5%–75.5%) | 3 / 2 | 1.0000 |

Both intervals are two-sided Clopper–Pearson intervals. Both paired tests are two-sided. Of the three policy losses, xarray-7233 and sympy-15875 reached the 64-request cap with empty patches. Django-11333 completed naturally and its patch failed testing. These outcomes describe one attempt per arm on each issue.

## Whole-task input and estimated cost

The A ledger is complete on 32 tasks including five A passes. Each delta below requires full usage from both arms and equals B minus A. Frozen tasks with unavailable usage remain in the CSV. Input includes both cached and uncached tokens. Costs use standard model prices.

### Input tokens

| Cohort | Pairs | B < A | B = A | B > A | Median delta | Sum of deltas |
|---|---:|---:|---:|---:|---:|---:|
| All complete pairs | 31 | 15 | 0 | 16 | 8,827.0 | -158,344.0 |
| Baseline passes | 5 | 2 | 0 | 3 | 19,418.0 | 602,806.0 |
| Both pass | 2 | 1 | 0 | 1 | -14,566.5 | -29,133.0 |
| Both completed and gradable | 20 | 12 | 0 | 8 | -27,152.5 | -927,976.0 |
| B preview emitted | 30 | 14 | 0 | 16 | 14,122.5 | -151,479.0 |
| No B preview emitted | 1 | 1 | 0 | 0 | -6,865.0 | -6,865.0 |
| django/django | 7 | 5 | 0 | 2 | -32,453.0 | -1,005,035.0 |
| pydata/xarray | 7 | 3 | 0 | 4 | 402,592.0 | 763,228.0 |
| pytest-dev/pytest | 6 | 2 | 0 | 4 | 43,234.0 | 47,653.0 |
| sphinx-doc/sphinx | 4 | 2 | 0 | 2 | 11,743.0 | 145,891.0 |
| sympy/sympy | 7 | 3 | 0 | 4 | 131,364.0 | -110,081.0 |

### Estimated USD

| Cost accounting | A | B | Paired comparison |
|---|---:|---:|---|
| Sent requests missing usage | 25 / 1,507 | 5 / 1,794 | 31 tasks have complete usage in both arms |
| Estimated cost on those 31 tasks | $1.470505 | $1.569347 | +6.7% |

| Cohort | Pairs | B < A | B = A | B > A | Median delta | Sum of deltas |
|---|---:|---:|---:|---:|---:|---:|
| All complete pairs | 31 | 15 | 0 | 16 | 0.003126 | 0.098842 |
| Baseline passes | 5 | 2 | 0 | 3 | 0.003126 | 0.079988 |
| Both pass | 2 | 1 | 0 | 1 | -0.003778 | -0.007556 |
| Both completed and gradable | 20 | 12 | 0 | 8 | -0.003009 | -0.062946 |
| B preview emitted | 30 | 14 | 0 | 16 | 0.004125 | 0.099197 |
| No B preview emitted | 1 | 1 | 0 | 0 | -0.000356 | -0.000356 |
| django/django | 7 | 5 | 0 | 2 | -0.003938 | -0.079825 |
| pydata/xarray | 7 | 3 | 0 | 4 | 0.057213 | 0.118917 |
| pytest-dev/pytest | 6 | 2 | 0 | 4 | 0.005574 | 0.032778 |
| sphinx-doc/sphinx | 4 | 2 | 0 | 2 | 0.000572 | 0.016926 |
| sympy/sympy | 7 | 3 | 0 | 4 | 0.019493 | 0.010046 |

Across complete pairs A used 11,258,379 input tokens at USD 1.470505, and B used 11,100,035 at USD 1.569347. B made 1,253 requests to A’s 824. B used 504,320 fewer cached input tokens, 345,976 more uncached input tokens and 6,802 more output tokens. At the fixed rates of USD 0.10, 0.40 and 1.60 per million respectively, these changes explain the higher estimated cost. Django-11820 was the sole task with complete A usage and incomplete B usage.

Within-repository paired task bootstrap, 10,000 replicates with seed 20261125. The percentile 95% intervals for mean B minus A per complete pair are -175,006 to 141,300 input tokens and USD -0.016854 to 0.020481. The complete-case analysis is conditional on observed usage.

### Nine baseline passes

| Task | B outcome | B stop | Paired input delta | Paired USD delta |
|---|---|---|---:|---:|
| sympy__sympy-19346 | True | completed | — | — |
| pytest-dev__pytest-7571 | False | agent_error | — | — |
| pydata__xarray-7233 | False | limit_hit | 402592 | 0.057213 |
| pydata__xarray-4629 | True | completed | — | — |
| sympy__sympy-15875 | False | limit_hit | 261800 | 0.039461 |
| sympy__sympy-13480 | True | completed | -48551 | -0.010681 |
| django__django-11333 | False | completed | -32453 | -0.009130 |
| sphinx-doc__sphinx-9367 | True | completed | — | — |
| pytest-dev__pytest-5809 | True | completed | 19418 | 0.003126 |

## Triggering, stops and accounting

B emitted at least one preview on 45/48 attempts. The extension emitted 270 previews, recorded 0 fallbacks and observed 2 archive readbacks through the instrumented paths. Independent trajectories can use different whole-task token counts even with no preview.

| Arm | Natural stop | Request limit | Timeout | Agent error | Sent | Requests missing usage | Complete ledgers | Known USD | First request cold / warm / unknown |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| A | 35 | 8 | 4 | 1 | 1507 | 25 | 32 | 2.960296 | 47 / 0 / 1 |
| B | 37 | 8 | 2 | 1 | 1794 | 5 | 46 | 2.099376 | 47 / 0 / 1 |

| Arm | Known uncached input | Known cached input | Known total input | Known output |
|---|---:|---:|---:|---:|
| A | 1,630,535 | 21,458,816 | 23,089,351 | 101,375 |
| B | 1,612,059 | 13,050,368 | 14,662,427 | 93,447 |

These totals cover different amounts of missing usage in A and B. Use the 31 complete pairs above to compare costs.

Both phases used the same pinned images and grader, with B executed later. The first-request cache counts capture one aspect of cache reuse. Provider drift, later-turn caching, missing usage and variation between single attempts limit the cost and repair conclusions.

[Preregistered protocol](HOLDOUT.md) · [All 50 paired rows](../results/holdout50-ab.csv) · [Stock baseline](HOLDOUT-BASELINE.md)

### Attempts without a successful provider response

The following B attempts stayed in the registered denominators according to their grades. A run with zero successful responses cannot demonstrate an effect of preview content. Its cost can be unknown.

| Task | HTTP 502 / sent | B previews | A outcome | B outcome |
|---|---:|---:|---|---|
| pytest-dev__pytest-7571 | 4 / 4 | 0 | True | False |

## Coverage by repository and issue type

These are descriptive counts. Each row shows the number of B attempts with a rendered preview, the paired grade counts and the whole-task input delta only where both usage ledgers are complete.

| Group | Planned | B attempted | B triggered | Graded pairs | A passes in pairs | B passes in pairs | Complete costs | Input delta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| django/django | 10 | 10 | 10 | 8 | 1 | 0 | 7 | -1,005,035 |
| pydata/xarray | 10 | 10 | 10 | 9 | 2 | 1 | 7 | 763,228 |
| pytest-dev/pytest | 10 | 10 | 9 | 10 | 2 | 1 | 6 | 47,653 |
| sphinx-doc/sphinx | 10 | 8 | 7 | 7 | 1 | 1 | 4 | 145,891 |
| sympy/sympy | 10 | 10 | 9 | 10 | 3 | 4 | 7 | -110,081 |
| Behavior and API contracts | 13 | 13 | 12 | 12 | 1 | 0 | 10 | -2,015,824 |
| Compatibility and integration | 6 | 5 | 5 | 5 | 1 | 1 | 2 | 129,839 |
| Computation and query correctness | 9 | 9 | 8 | 8 | 2 | 3 | 8 | 54,330 |
| Data representation and metadata | 7 | 7 | 7 | 7 | 2 | 1 | 4 | 2,609,535 |
| Formatting, rendering and diagnostics | 13 | 12 | 11 | 11 | 2 | 2 | 5 | -698,125 |
| Performance and resource use | 2 | 2 | 2 | 1 | 1 | 0 | 2 | -238,099 |
| 1-4 hours | 4 | 4 | 4 | 4 | 0 | 0 | 4 | -1,268,336 |
| 15 min - 1 hour | 24 | 24 | 21 | 21 | 4 | 2 | 13 | 411,518 |
| <15 min fix | 20 | 18 | 18 | 17 | 5 | 5 | 13 | 588,053 |
| >4 hours | 2 | 2 | 2 | 2 | 0 | 0 | 1 | 110,421 |

## One regression trace

On sympy-15875, A made 26 model requests, issued 16 source reads and one edit, and passed. B emitted two short-tail previews and issued 61 read calls. It reached the 64-request cap with an empty patch. Neither preview led to a recorded archive read. This trajectory illustrates why the budget for one tool result does not bound the cost of completing a task. A single pair does not establish why the model chose that trajectory.
