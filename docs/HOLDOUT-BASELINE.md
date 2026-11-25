# Holdout baseline for stock Pi

Of the 50 frozen tasks, stock Pi had **9 confirmed passes**. The reference patch validated the environment on 48 tasks, and 45 model attempts have a determinate outcome. The later B regression comparison can include up to 9 baseline passes.

## Cohort and accounting

The holdout spans five Python repositories with ten tasks each. It was frozen independently of A success. Each eligible task received one attempt using Pi 1.6.0, gpt-4.1-mini-2025-04-14, a 64-request cap and a 900-second agent timeout. A separate grader checked each reference patch before the model saw the issue. All 50 IDs appear in the [per-task results](../results/holdout50-a.csv).

| Repository | Frozen | Model attempted | Valid outcome | Confirmed pass | Reference unavailable | Model grade unavailable |
|---|---:|---:|---:|---:|---:|---:|
| django/django | 10 | 10 | 9 | 1 | 0 | 1 |
| pydata/xarray | 10 | 10 | 9 | 2 | 0 | 1 |
| pytest-dev/pytest | 10 | 10 | 10 | 2 | 0 | 0 |
| sphinx-doc/sphinx | 10 | 8 | 7 | 1 | 2 | 1 |
| sympy/sympy | 10 | 10 | 10 | 3 | 0 | 0 |
| **Total** | **50** | **48** | **45** | **9** | **2** | **3** |

Among gradable runs that stopped naturally, 9/33 passed. Across all valid outcomes including forced stops and empty patches, 9/45 passed. Missing grades remain unknown.

| Agent stop status | Model attempts | Graded or empty patch | Passed |
|---|---:|---:|---:|
| agent_error | 1 | 1 | 0 |
| completed | 35 | 33 | 9 |
| limit_hit | 8 | 7 | 0 |
| timeout | 4 | 4 | 0 |

1,507 provider requests were sent. Known input was 23,089,351 tokens including 21,458,816 cached tokens. Known output was 101,375 tokens. Known estimated cost was **USD 2.960296** at the pinned list prices. Usage was unavailable for 25 sent requests. 32/48 attempts have complete provider usage for a future paired cost comparison. Costs include failed and capped attempts.

## Interpretation

If B is evaluated on every A pass and regresses on zero, the two-sided 95% Clopper–Pearson upper bound on the conditional regression fraction would be 33.6%. This describes the best-case precision of this cohort. A-only outcomes cannot estimate the effect of short previews.

Two early attempts (pytest-7324 and sphinx-8265) timed out after a truncated upstream response interrupted the relay. Both remain in the dataset. The relay now records an upstream failure and returns control to the client. No model attempts were repeated to improve their outcomes.

Official grader retries reused the saved prediction and identical patch bytes in a fresh grading container when installation failed transiently. Two retries produced valid failing grades. One retry again timed out while downloading build dependencies. Three Pi startup crashes were recovered before the first model request. Task environments ran on linux/amd64 under emulation. Reference checks and missing grades can affect the mix of repositories with comparable results.

[Frozen task IDs and image digests](../bench/tasks/holdout50.json) · [Protocol and issue categories](HOLDOUT.md) · [Per-task outcomes and first-request cache use](../results/holdout50-a.csv)

## Recovery and missing outcomes

| Instance | Final stage | Evidence |
|---|---|---|
| django__django-16333 | infra | Official grader reported patch_successfully_applied=false. The official outcome was unresolved. |
| pytest-dev__pytest-10081 | graded | Fresh grader after a transient installation failure. The initial grade was unavailable. |
| pytest-dev__pytest-7571 | Startup recovery | Pi crashed before the first request. The preserved journal was empty. |
| sympy__sympy-18199 | Startup recovery | Pi crashed before the first request. The preserved journal was empty. |
| pytest-dev__pytest-10051 | Startup recovery | Pi crashed before the first request. The preserved journal was empty. |
| sphinx-doc__sphinx-8475 | Reference unavailable | Three PASS_TO_PASS tests failed. |
| pydata__xarray-7229 | graded | Fresh grader after a transient installation failure. The initial grade was unavailable. |
| sphinx-doc__sphinx-10435 | Reference unavailable | One PASS_TO_PASS test failed. |
| sphinx-doc__sphinx-9602 | infra | Official grader reported patch_successfully_applied=false. The official outcome was unresolved. |
| pydata__xarray-6721 | infra | Fresh grader after a transient installation failure. The initial grade was unavailable. |
