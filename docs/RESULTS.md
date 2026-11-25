# Five-task paired results

> The 30-row extract is in [`results/paired5.csv`](../results/paired5.csv). Raw `runs/` directories are not committed.

All five tasks come from the Django subset that stock Pi had solved at least once. Each task has two independent rounds; each round runs A, B, C once. A = stock Pi; B = 128-token tail; C = the same budget split between head and tail. Fixed Pi 1.6.0, `gpt-4.1-mini-2025-04-14`, 64 requests, 900 s. The official SWE-bench Verified harness graded every run; every patch and build record was inspected.

**Across these five tasks ×2 rounds, tail-only B matched A's 8 passes, cutting total input 22.7% and estimated cost 27.6%. Head+tail C passed 9, with 9.2% lower input than A and 17.4% higher input than B. C's only extra pass is 11292 round 2. At the same 128-token budget, the value of keeping the head varies by task. All five tasks were selected from A-solved tasks; the sample cannot establish an accuracy improvement or statistical non-inferiority.**

## Per-task comparison

Each cell is: passes (out of two), mean total input over the two rounds, mean estimated cost in USD. Input includes cache reads. Costs use $0.40 / $0.10 / $1.60 per million uncached input / cache read / output.

| Django task | A stock | B tail | C head+tail |
|---|---:|---:|---:|
| 11066 | 2/2 · 30,097.0 · 0.00633 | 2/2 · 110,164.0 · 0.01724 | 2/2 · 12,296.5 · 0.00307 |
| 11133 | 2/2 · 188,210.5 · 0.02684 | 2/2 · 70,085.5 · 0.01133 | 2/2 · 139,228.5 · 0.01896 |
| 11163 | 2/2 · 180,629.0 · 0.02715 | 2/2 · 142,894.5 · 0.02097 | 2/2 · 19,844.5 · 0.00408 |
| 11292 | 0/2 · 384,967.5 · 0.06241 | 0/2 · 217,062.5 · 0.03162 | 1/2 · 333,815.0 · 0.04556 |
| 11603 | 2/2 · 70,213.0 · 0.01332 | 2/2 · 120,226.0 · 0.01740 | 2/2 · 270,479.0 · 0.03814 |

| Arm | Confirmed pass / all | Natural-completion decidable | Cap stop | Grading missing | Total input | Total cost USD | Successful previews / fallbacks | Archive readbacks |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 8/10 | 8/10 | 0 | 0 | 1,708,234 | 0.272094 | 0/0 | 0 |
| B | 8/10 | 8/10 | 0 | 0 | 1,320,865 | 0.197111 | 74/0 | 0 |
| C | 9/10 | 9/9 | 1 | 0 | 1,551,327 | 0.219604 | 82/0 | 1 |

The 30 runs forwarded 797 model requests, all with usage records; the standard-price estimate is $0.688809. Cost per confirmed pass: A $0.03401, B $0.02464, C $0.02440. All 20 B/C runs triggered the preview. On 11133 round 2, C used `tail -60` on the archive and received 559 bytes; the trace supports that the model used the archive, but cannot establish that this caused the pass.

## Paired differences

Inputs and costs are averaged over the two rounds per task; the median is over the five task-level differences. Win/loss counts are paired by task and round; only pairs with a grade on both sides are included.

| Variant − control | Median input difference | Median cost difference USD | Variant-only pass | Control-only pass | Both pass | Both fail | Missing pairs |
|---|---:|---:|---:|---:|---:|---:|---:|
| C − B | +69,143.0 | +0.007628 | 1 | 0 | 8 | 1 | 0 |
| C − A | -48,982.0 | -0.007884 | 1 | 0 | 8 | 1 | 0 |
| B − A | -37,734.5 | -0.006178 | 0 | 0 | 8 | 2 | 0 |

The three C−B input differences are +90,287, −21,313, −4,195; the mean is +21,593, the median −4,195, and the total +64,779 (+18.0%). The cost median is +$0.000271, the total +13.9%. On 10999, C uses less total input but more uncached input and output, so its cost is slightly higher.

## Preview and readback

| Task / arm | Multi-trigger total: original displayed → actual preview tokens (single trigger ≤ T=128) | Per-trigger tokens | Self / Pi archive | Ordinary read: unmatched archive path | Observed archive readback |
|---|---|---:|---:|---:|---:|
| 10554 / A | — | — | 0 / 0 | 22 | 0 |
| 10554 / B | 829 → 255 | [127, 128] | 2 / 0 | 12 | 0 |
| 10554 / C | 5,532 → 383 | [127, 128, 128] | 3 / 0 | 24 | 0 |
| 10880 / A | — | — | 0 / 0 | 25 | 0 |
| 10880 / B | 12,218 → 384 | [128, 128, 128] | 3 / 0 | 25 | 0 |
| 10880 / C | 10,288 → 383 | [128, 127, 128] | 3 / 0 | 24 | 0 |
| 10999 / A | — | — | 0 / 0 | 1 | 0 |
| 10999 / B | 653 → 128 | [128] | 1 / 0 | 4 | 0 |
| 10999 / C | 12,677 → 256 | [128, 128] | 1 / 1 | 4 | 0 |

Every attempt's first known cache read was 0. Unmatched archive paths in ordinary reads range from 1 to 25, the minimum being 10999 A; B and C have 4 each.

The original display includes Pi's random temporary path and truncation notice. A local token difference describes one tool message; whole-task cost also includes all later turns and cache behavior. A keeps Pi's native tools, so its preview replacement count is zero. Read matching handles testbed-relative paths, `~/`, and known native archive aliases; other paths are stored in `unmatched_reads`. Bash access through variables or arbitrary links can be missed.

This is a fixed set of three Django tasks, one run per arm per task. It has no cross-repository sample and no repeats, so it cannot estimate stable accuracy or claim non-inferiority.

On 10554, B stopped after 19 calls and C used all 32; both produced empty patches, and this single pair's input delta exceeds the net total. On 10999, all three arms submitted date-parsing patches; the official report has two FAIL_TO_PASS failures for each. No task passes, so cost per solved task is undefined.

## Did the preview precede an edit?

Using the 20 B/C event streams, we compared the first successful bash preview with successful Pi `edit` and `write` calls by model turn. A preview can inform a tool choice on a later turn. This timing check does not capture file changes made through shell commands.

| First preview | B runs | C runs |
|---|---:|---:|
| Before the first successful edit/write turn | 9 | 6 |
| After edits had started, with a later edit/write turn | 1 | 1 |
| After the final successful edit/write turn | 0 | 3 |

In the only C-only pass (11292, round 2), C edited `django/core/management/base.py` on turn 16. Its four previews occurred on turns 18, 19, 21 and 27. The retained head could have influenced verification or stopping. It could not have guided the earlier edit. Treat the extra pass as an observed outcome with an unresolved cause.

## Per-run evidence

| Task | Round | Arm | Stop / grade | Resolved | Requests | Uncached input | Cache read | Output | Cost USD | Previews | Archive readbacks | Unmatched reads | Cap |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| django__django-11066 | r1 | A | completed / graded | True | 9 | 15871 | 35072 | 377 | 0.0104588 | 0 | 0 | 2 | False |
| django__django-11066 | r1 | B | completed / graded | True | 17 | 4274 | 34176 | 540 | 0.0059912 | 3 | 0 | 2 | False |
| django__django-11066 | r1 | C | completed / graded | True | 7 | 5232 | 9728 | 335 | 0.0036016 | 2 | 0 | 2 | False |
| django__django-11066 | r2 | A | completed / graded | True | 5 | 2723 | 6528 | 281 | 0.0021916 | 0 | 0 | 2 | False |
| django__django-11066 | r2 | B | completed / graded | True | 42 | 20982 | 160896 | 2502 | 0.0284856 | 11 | 0 | 7 | False |
| django__django-11066 | r2 | C | completed / graded | True | 5 | 3873 | 5760 | 260 | 0.0025412 | 1 | 0 | 2 | False |
| django__django-11133 | r1 | A | completed / graded | True | 11 | 18175 | 118656 | 624 | 0.020134 | 0 | 0 | 5 | False |
| django__django-11133 | r1 | B | completed / graded | True | 15 | 8393 | 43136 | 975 | 0.0092308 | 3 | 0 | 7 | False |
| django__django-11133 | r1 | C | completed / graded | True | 39 | 12152 | 191360 | 1655 | 0.0266448 | 8 | 0 | 16 | False |
| django__django-11133 | r2 | A | completed / graded | True | 17 | 27622 | 211968 | 813 | 0.0335464 | 0 | 0 | 9 | False |
| django__django-11133 | r2 | B | completed / graded | True | 28 | 8898 | 79744 | 1182 | 0.0134248 | 5 | 0 | 8 | False |
| django__django-11133 | r2 | C | completed / graded | True | 23 | 7745 | 67200 | 906 | 0.0112676 | 8 | 1 | 7 | False |
| django__django-11163 | r1 | A | completed / graded | True | 47 | 43537 | 298240 | 1515 | 0.0496628 | 0 | 0 | 32 | False |
| django__django-11163 | r1 | B | completed / graded | True | 40 | 24603 | 185088 | 1250 | 0.03035 | 9 | 0 | 18 | False |
| django__django-11163 | r1 | C | completed / graded | True | 9 | 5711 | 12032 | 435 | 0.0041836 | 2 | 0 | 3 | False |
| django__django-11163 | r2 | A | completed / graded | True | 10 | 6425 | 13056 | 475 | 0.0046356 | 0 | 0 | 3 | False |
| django__django-11163 | r2 | B | completed / graded | True | 20 | 9154 | 66944 | 773 | 0.0115928 | 4 | 0 | 11 | False |
| django__django-11163 | r2 | C | completed / graded | True | 11 | 3770 | 18176 | 411 | 0.0039832 | 3 | 0 | 3 | False |
| django__django-11292 | r1 | A | completed / graded | False | 32 | 51743 | 411904 | 13693 | 0.0837964 | 0 | 0 | 15 | False |
| django__django-11292 | r1 | B | completed / graded | False | 28 | 10922 | 106240 | 1384 | 0.0172072 | 7 | 0 | 12 | False |
| django__django-11292 | r1 | C | limit_hit / graded | False | 64 | 40549 | 491264 | 4533 | 0.0725988 | 16 | 0 | 33 | True |
| django__django-11292 | r2 | A | completed / graded | False | 34 | 25968 | 280320 | 1629 | 0.0410256 | 0 | 0 | 11 | False |
| django__django-11292 | r2 | B | completed / graded | False | 59 | 32803 | 284160 | 2808 | 0.04603 | 20 | 0 | 10 | False |
| django__django-11292 | r2 | C | completed / graded | True | 28 | 11017 | 124800 | 1016 | 0.0185124 | 4 | 0 | 14 | False |
| django__django-11603 | r1 | A | completed / graded | True | 17 | 18157 | 43392 | 1126 | 0.0134036 | 0 | 0 | 3 | False |
| django__django-11603 | r1 | B | completed / graded | True | 42 | 16242 | 188800 | 1563 | 0.0278776 | 7 | 0 | 19 | False |
| django__django-11603 | r1 | C | completed / graded | True | 55 | 31310 | 298752 | 2139 | 0.0458216 | 16 | 0 | 15 | False |
| django__django-11603 | r2 | A | completed / graded | True | 20 | 12317 | 66560 | 1035 | 0.0132388 | 0 | 0 | 5 | False |
| django__django-11603 | r2 | B | completed / graded | True | 16 | 7506 | 27904 | 705 | 0.0069208 | 5 | 0 | 3 | False |
| django__django-11603 | r2 | C | completed / graded | True | 47 | 21968 | 188928 | 1731 | 0.0304496 | 22 | 0 | 5 | False |
