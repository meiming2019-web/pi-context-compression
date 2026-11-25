# Task lists

- `pilot3.json` — three-task Django pilot (historical).
- `calibration10.json` — ten-task A calibration.
- `paired5.json` — five tasks used in the reported paired evaluation.
- `holdout50.json` — frozen 50-task cross-repository set for a future replication; it is **not** part of the reported five-task result. See the [issue-type coverage and comparison plan](../../docs/HOLDOUT.md).

The runner reads `pilot3.json` by default for non-default instances; pass `--instance` from the relevant list.
