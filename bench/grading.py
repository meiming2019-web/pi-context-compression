"""Official grading with one fresh-container retry for transient install failures."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import uuid

from outcomes import grade_result


def transient_install_failure(log):
    if not log.is_file():
        return False
    blocks = re.findall(r"^\+ (?:python\S* -m )?pip\S* install [^\n]*\n(.*?)(?=^\+ |\Z)",
                        log.read_text(errors="replace"), re.M | re.S)
    return any(re.search(r"ReadTimeoutError|Read timed out|Connection reset by peer|"
                         r"Temporary failure in name resolution|exit code: -11\b|"
                         r"internal compiler error: Segmentation fault", block) for block in blocks)


def official_grade(out, run_id, model, instance, log_name):
    with (out / log_name).open("wb") as log:
        code = subprocess.run([sys.executable, "-m", "swebench.harness.run_evaluation",
            "--dataset_name", str(out / "grader-input.json"), "--predictions_path",
            str(out / "predictions.jsonl"), "--instance_ids", instance, "--run_id", run_id,
            "--max_workers", "1"], cwd=out, stdout=log, stderr=subprocess.STDOUT).returncode
    return grade_result(out, run_id, model, instance, code)


def retry_transient_grade(out, meta, model):
    if meta["grade_status"] != "infra" or meta["env_build_ok"] is True or "grading_retry" in meta:
        return {}
    instance = meta["instance_id"]
    log = out / "logs/run_evaluation" / meta["run_id"] / model / instance / "test_output.txt"
    if not transient_install_failure(log):
        return {}
    patch = (out / "model.patch").read_bytes()
    prediction = json.loads((out / "predictions.jsonl").read_text())
    if (prediction["model_patch"].encode() != patch or
            hashlib.sha256(patch).hexdigest() != meta["patch_sha256"]):
        raise ValueError("Patch differs from the original attempt")
    retry_id = "retry-" + uuid.uuid4().hex[:12]
    retry = official_grade(out, retry_id, model, instance, "grader-retry.log")
    first = {key: meta[key] for key in retry}
    return dict(retry, grade_run_id=retry_id, grading_retry={"first": first, "retry": retry})
