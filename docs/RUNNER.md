# Runner and evaluation setup

The public reproduction path for one Pi arm on one SWE-bench Verified instance. The reported five-task pairing used `bench/tasks/paired5.json`; the runner reads `bench/tasks/pilot3.json` by default for non-default instances.

## Requirements

- Docker able to run `linux/amd64` containers.
- Python 3.12.
- npm and Node.js 24.
- `OPENAI_API_KEY` on the host.
- On Apple Silicon, use Colima with amd64 emulation and point the Docker SDK at the same daemon, for example:

```sh
export DOCKER_HOST="unix://$HOME/.colima/default/docker.sock"
```

## Setup

```sh
mkdir -p runs/setup/pi/bin
python3.12 -m venv runs/setup/venv
runs/setup/venv/bin/pip install swebench==5.0.2
curl -fLsS 'https://datasets-server.huggingface.co/first-rows?dataset=SWE-bench%2FSWE-bench_Verified&config=default&split=test' -o runs/setup/first-rows.json
npm install --prefix runs/setup/pi --ignore-scripts --no-audit --no-fund @earendil-works/pi-coding-agent@1.6.0
npm pack node-linux-x64@24.11.1 --pack-destination runs/setup
tar -xzf runs/setup/node-linux-x64-24.11.1.tgz -C runs/setup/pi/bin --strip-components 2 package/bin/node
image=swebench/sweb.eval.x86_64.astropy_1776_astropy-12907
digest=sha256:7485c1e3c8861efd0c6a4a78b952857592e541031039000d25e9481f045dc4a3
docker pull --platform linux/amd64 "$image@$digest"
docker tag "$image@$digest" "$image:latest"
```

Each run needs a fresh output directory:

```sh
runs/setup/venv/bin/python bench/runner.py \
  runs/setup/first-rows.json runs/setup/pi runs/my-run \
  --instance django__django-11066 \
  --arm B --preview-tokens 128 --max-calls 64
```

`--arm A` uses stock Pi; `B` and `C` mount the extension and select the policy through `PI_PREVIEW_ARM`. `--max-calls` defaults to 32; the paired experiment used 64. The wall limit is 900 s.

## Isolation and artifacts

Before the model starts, the runner restores the official base commit, removes the image's extra Git refs, checks a clean single-commit tree, and runs Pi as a non-root user in a `--network none` container. The model process reaches a local relay over loopback; the relay forwards requests to the provider from the host, so the key and the grader input never enter the agent container.

The output directory contains:

- `events.jsonl` — raw Pi event stream.
- `model.patch` — the diff against base, including added files.
- `predictions.jsonl` — the official grader input.
- `logs/run_evaluation/` — applied patch, test output, and per-instance report.
- `run.json` — arm, status, call count, usage, cost, previews, readbacks, grading evidence.

Patch collection uses a private Git index so a timed-out tool cannot block collection. It excludes generated test caches (`.pytest_cache`, `__pycache__`, `.mypy_cache`, `.ruff_cache`, `.hypothesis`, `.coverage`) and refuses to grade a patch containing reserved archive paths.

## Grading

The official harness runs in a separate container:

```sh
python -m swebench.harness.run_evaluation \
  --dataset_name "$PWD/grader-input.json" \
  --predictions_path "$PWD/predictions.jsonl" \
  --instance_ids <instance> --run_id <unique-id> --max_workers 1
```

The runner verifies that the collected patch and the applied patch are byte-identical. It records `env_build_ok` from the editable-install evidence and marks a run `infra` with `resolved=null` when the build or report is not trustworthy. Cap hits, timeouts, empty patches, and grading failures are retained, not silently dropped.

## Metrics

- `previews`: original display tokens, actual preview tokens, route (`self_archive` or `pi_archive`), path, fallback.
- `readbacks`: read calls against known archive paths, offset/limit, repeated range, returned bytes.
- `unmatched_reads`: ordinary reads that did not match an archive path.
- `pi_usage` and `provider_usage_known`: token accounting; `cost_usd` is null if any forwarded request lacks usage.

## Tests

```sh
npm ci --prefix extension --ignore-scripts
npm test --prefix extension
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=bench python3.12 -m unittest discover -s bench -v
```

The Python suite covers patch collection, cache exclusion, timeout/cap accounting, grading evidence, and the request-cap boundary.
