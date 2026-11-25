# Pi Context Compression

Reversible, token-budgeted compression of long tool output for the [Pi](https://github.com/badlogic/pi-mono) coding agent.

[Results](docs/RESULTS.md) · [Architecture](docs/ARCHITECTURE.md) · [Runner](docs/RUNNER.md) · [30-run CSV](results/paired5.csv)

## What it does

Pi puts every bash result into the conversation, and long outputs are re-billed on every later turn. This extension intercepts the `tool_result` boundary:

- **Pass through** when the result fits a token budget `T`.
- **Compress once** otherwise: archive the full log and replace the tool result with a `T`-token preview. `B` keeps the tail; `C` splits the same budget between head and tail.
- **Stay reversible**: the preview carries the exit code, archive path, and a `read` hint; the model retrieves omitted lines with Pi's existing `read` tool.
- **Fail open**: if archival or rendering fails, Pi's original result is returned.

No summarizer model, no extra retrieval tool, and no rewriting of persisted history.

## Result

Five Django tasks from a conditional A-solved subset, two independent rounds per arm, 30 official-graded SWE-bench Verified runs. Fixed Pi 1.6.0, `gpt-4.1-mini-2025-04-14`, `T=128`, 64-request cap.

| Arm | Pass | Total input | Estimated cost | vs A |
|---|---:|---:|---:|---:|
| A · stock Pi | 8/10 | 1,708,234 | $0.2721 | — |
| **B · 128-token tail** | **8/10** | **1,320,865** | **$0.1971** | **−22.7% input / −27.6% cost** |
| C · 128-token head+tail | 9/10 | 1,551,327 | $0.2196 | −9.2% / −19.3% |

**B preserved all eight A passes with zero regressions** and is the default. It is not uniformly cheaper: B is worse than A on 2 of 5 tasks, so the 22.7% is a five-task total.

C gained one pass (`11292`, round 2) and lost none, but it also hit the 64-request cap once. Its all-run input is +17.4% versus B, and that total is 34% one cap failure; completed-only C is 9/9, 1,019,514 tokens, $0.1470, which is cheaper per pass than B. The extra pass is **n=1**, so this is a tradeoff to investigate, not a stable head+tail advantage. [Full decomposition](docs/RESULTS.md).

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
results/     paired5.csv — 30-row extract of the evaluation
docs/        RESULTS, ARCHITECTURE, RUNNER
```

`runs/` is intentionally not committed (large raw traces); `results/paired5.csv` is the compact per-run extract.

## Tests

```sh
cd extension && npm ci && npm test && npm run demo
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=bench python3.12 -m unittest discover -s bench -v
```

3 extension tests + 11 Python tests; CI runs the same commands.

## Limitations

- Five tasks from an A-solved conditional subset, two repeats; this is a pilot, not a population estimate or a non-inferiority proof.
- B preserves 8/8 baseline passes in this sample; it does not improve accuracy.
- C's extra pass is one run; its cap failure and per-task variance mean head+tail is not a stable win at `T=128`.
- Pi 1.6.0 / `gpt-4.1-mini` / `T=128`; results are harness- and model-specific.
- The 22.7% is a five-task total; on two tasks the short tail uses more input than stock Pi.

## License

MIT. See [LICENSE](LICENSE).
