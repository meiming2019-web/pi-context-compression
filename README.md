# Pi Context Compression

Reversible, token-budgeted compression of long tool output for the [Pi](https://github.com/badlogic/pi-mono) coding agent.

[50-task comparison](docs/HOLDOUT-RESULTS.md) · [Paired pilot](docs/RESULTS.md) · [Stock baseline](docs/HOLDOUT-BASELINE.md) · [Architecture](docs/ARCHITECTURE.md) · [Runner](docs/RUNNER.md)

## What it does

Pi puts every bash result into the conversation, and long outputs are re-billed on every later turn. This extension intercepts the `tool_result` boundary:

- **Pass through** when the result fits a token budget `T`.
- **Compress once** otherwise: archive the full log and replace the tool result with a `T`-token preview. `B` keeps the tail; `C` splits the same budget between head and tail.
- **Stay reversible**: the preview carries the exit code, archive path, and a `read` hint; the model retrieves omitted lines with Pi's existing `read` tool.
- **Fail open**: if archival or rendering fails, Pi's original result is returned.

No summarizer model, no extra retrieval tool, and no rewriting of persisted history.

## Cross-repository result

On the frozen 50-task SWE-bench Verified sample, stock Pi and the 128-token short tail each attempted 48 issues. The short tail retained **5 of 9** baseline passes end to end. Two B runs reached the request cap, one completed with a failing patch, and one received HTTP 502 on every request before any preview could run. Excluding that outage, the post hoc policy analysis gives **5 of 8 retained**.

On the **31 pairs with complete usage**, B used **1.4% less total input** and cost **6.7% more** at standard prices. Fifteen pairs used fewer input tokens and sixteen used more. The extension emitted 270 previews within budget across 45 tasks. These results support keeping the fixed short tail optional. [Paired report](docs/HOLDOUT-RESULTS.md) · [50-row CSV](results/holdout50-ab.csv).

## Five-task pilot

Five Django tasks from a conditional A-solved subset, two independent rounds per arm, 30 official-graded SWE-bench Verified runs. Fixed Pi 1.6.0, `gpt-4.1-mini-2025-04-14`, `T=128`, 64-request cap.

| Arm | Pass | Total input | Estimated cost | vs A |
|---|---:|---:|---:|---:|
| A · stock Pi | 8/10 | 1,708,234 | $0.2721 | — |
| **B · 128-token tail** | **8/10** | **1,320,865** | **$0.1971** | **−22.7% input / −27.6% cost** |
| C · 128-token head+tail | 9/10 | 1,551,327 | $0.2196 | −9.2% / −19.3% |

**B retained all eight A passes in this pilot.** B used more input on two of the five tasks. The pilot’s combination of lower cost and full retention did not replicate on the 50-task holdout.

C gained one pass (`11292`, round 2) and lost none, but it also hit the 64-request cap once. Its all-run input is +17.4% versus B, and that total is 34% one cap failure; completed-only C is 9/9, 1,019,514 tokens, $0.1470, which is cheaper per pass than B. The first head+tail preview in that run arrived after C's first successful edit, so the head cannot explain that fix; treat the extra pass as unresolved. It is **n=1**, not a stable head+tail advantage. [Full decomposition](docs/RESULTS.md).

## Quick demo

Requires Node.js 24 and npm; no model key.

```sh
cd extension
npm ci
npm run demo
```

The demo feeds a 323-line test log through the real preview functions and reads the omitted middle from the archive:

```text
Sample log: 323 lines, 2261 tokens, exit 1
B · tail · 128/128 tokens
...
Archive line 162: AssertionError: expected two cart items, received one
C · head+tail · 128/128 tokens
...
```

A real run also used the archive: on task `11133`, the model ran `tail -60` on the archived log (559 bytes). The report keeps that trace; it does not attribute the pass to the readback.

## Why this is not just truncation

- Reversible: the full log is on disk and addressable by line; nothing is summarized.
- Budgeted: exit code, archive path, and read hint are counted against `T`; the final text is re-counted with the model tokenizer.
- Native-archive aware: when Pi already truncated and saved a log, the extension hard-links or symlinks that archive and reads only its edges, instead of copying a multi-gigabyte file.
- Cache-aware: replacement happens once at tool-result entry; the persisted message is not rewritten on later turns.
- Fail-open: a missing archive or token-budget overrun returns Pi's original result.

## Repository

```text
extension/   Pi extension, offline demo, extension tests
bench/       runner, task lists, patch collection, official-grader integration, Python tests
results/     five-task pilot, stock baseline, and 50-task paired CSVs
docs/        RESULTS, ARCHITECTURE, RUNNER
```

`runs/` is intentionally not committed (large raw traces); the `results/` directory contains the compact extracts.

## Tests

```sh
(cd extension && npm ci && npm test && npm run demo)
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=bench python3.12 -m unittest discover -s bench -v
```

The suite covers 3 extension tests and 13 Python tests.

## Limitations

- Five tasks from an A-solved conditional subset, two repeats; this is a pilot, not a population estimate or a non-inferiority proof.
- The policy analysis excludes pytest-7571 because all four B requests returned HTTP 502. Its denominator is eight baseline passes, with one attempt per arm per issue, so the regression estimate is imprecise.
- C's extra pass is one run; its cap failure and per-task variance mean head+tail is not a stable win at `T=128`.
- Pi 1.6.0 / `gpt-4.1-mini` / `T=128`; results are harness- and model-specific.
- The 22.7% is a five-task total; on two tasks the short tail uses more input than stock Pi.

## License

MIT. See [LICENSE](LICENSE).
