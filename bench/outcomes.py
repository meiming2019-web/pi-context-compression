"""Evidence for a pilot attempt, independent of its stopping condition."""
import hashlib
import json
from pathlib import PurePosixPath
import re
import subprocess


def records(path):
    with path.open("rb") as stream:
        for line in stream:
            # Only a trailing, unterminated event can be interrupted by the timeout.
            try:
                yield json.loads(line)
            except (ValueError, UnicodeDecodeError):
                if line.endswith(b"\n"):
                    raise


def account(out, exit_code, timed_out):
    turns = compact = 0
    pi = dict(input=0, cacheRead=0, cacheWrite=0, output=0)
    stop = None
    for e in records(out / "events.jsonl"):
        if e["type"] == "compaction_start":
            compact += 1
        message = e.get("message", {})
        if e["type"] == "message_end" and message.get("role") == "assistant":
            stop = message.get("stopReason")
            turns += 1
            for key in pi:
                pi[key] += message.get("usage", {}).get(key, 0)
    ledger = list(records(out / "requests.jsonl"))
    calls = sum(e["event"] == "sent" for e in ledger)
    limit_hit = any(e["event"] == "limit_hit" for e in ledger)
    known = [e["usage"] for e in ledger if e.get("usage") is not None]
    usage = {k: sum(u[k] for u in known) for k in ("input", "cacheRead", "output")}
    # USD per million, standard gpt-4.1-mini list prices. Cache reads are disjoint.
    estimate = round((usage["input"] * .40 + usage["cacheRead"] * .10
                      + usage["output"] * 1.60) / 1_000_000, 9)
    status = "completed" if exit_code == 0 and stop == "stop" else "agent_error"
    if limit_hit:
        status = "limit_hit"
    if timed_out:
        status = "timeout"
    return dict(status=status, limit_hit=limit_hit, relay_calls=calls, model_turns=turns,
                compaction_events=compact, pi_usage=pi, provider_usage_known=usage,
                calls_without_usage=calls-len(known), known_cost_usd=estimate,
                cost_usd=estimate if len(known) == calls else None)


def collect(agent, base, out):
    # A timed-out tool can leave its original index.lock behind. Work on a private copy.
    index = subprocess.check_output([*agent, "sh", "-ec",
        'idx=$(mktemp); cp "$(git rev-parse --git-path index)" "$idx"; echo "$idx"'],
        text=True).strip()

    def git(*args):
        return subprocess.check_output([*agent, "env", "GIT_INDEX_FILE=" + index, "git", *args])

    cache_globs = ["**/.pytest_cache", "**/.pytest_cache/**", "**/__pycache__", "**/__pycache__/**"]
    cache_paths = [":(glob)" + pattern for pattern in cache_globs]
    omit_caches = [":(exclude,glob)" + pattern for pattern in cache_globs]

    def filenames(raw):
        return [name.decode("utf-8", "surrogateescape") for name in raw.split(b"\0") if name]

    # Include ignored files in this inventory. pytest can write its own .gitignore.
    untracked_caches = git("ls-files", "--others", "-z", "--", *cache_paths)
    changed_caches = git("diff", "--no-renames", "--name-only", "-z", base, "--", *cache_paths)
    excluded = sorted(set(filenames(untracked_caches) + filenames(changed_caches)))

    git("add", "-A", "--", *omit_caches)
    # A cache may already be staged or committed by the agent. Filter the diff too.
    diff = ("diff", "--cached")
    paths = filenames(git(*diff, "--no-renames", "--name-only", "-z", base, "--", *omit_caches))
    added = filenames(git(*diff, "--diff-filter=A", "--no-renames", "--name-only", "-z",
                          base, "--", *omit_caches))
    patch = git(*diff, "--binary", base, "--", *omit_caches)
    (out / "model.patch").write_bytes(patch)
    reserved = {".pi", ".pi-preview", "pi-preview-archive"}
    artifacts = [s for s in paths if reserved.intersection(PurePosixPath(s).parts)]
    tests = [s for s in map(PurePosixPath, paths) if {"test", "tests"}.intersection(s.parts)
             or s.name.startswith("test_") or s.name.endswith("_test.py") or s.name == "conftest.py"]
    info = dict(added_paths=added, changed_paths=paths, excluded_cache_paths=excluded,
                test_files=[str(p) for p in tests], artifact_paths=artifacts,
                patch_sha256=hashlib.sha256(patch).hexdigest())
    if artifacts:
        return None, dict(info, grade_status="patch_contaminated", resolved=None)
    try:
        return patch.decode("utf-8"), info
    except UnicodeDecodeError:
        return None, dict(info, grade_status="patch_encoding_error", resolved=None)


def build_check(log):
    """Recognize the pilot's traced editable pip install, ending at the next shell command."""
    if not log.is_file():
        return None
    blocks = re.findall(r"^\+ (?:python\S* -m )?pip\S* install [^\n]*"
                        r"(?:-e |--editable )[^\n]*\n(.*?)(?=^\+ |\Z)",
                        log.read_text(errors="replace"), re.M | re.S)
    verdicts = []
    for block in blocks:
        if re.search(r"^\s*(?:ERROR:|Failed to build |gcc: internal compiler error:)", block, re.M):
            return False
        verdicts.append(bool(re.search(r"^Successfully installed .+", block, re.M)))
    return True if blocks and all(verdicts) else None


def grade_result(out, run_id, model, instance, code):
    task = out / "logs/run_evaluation" / run_id / model / instance
    env_ok = build_check(task / "test_output.txt")
    result = dict(env_build_ok=env_ok, official_resolved=None, resolved=None, grade_status="infra")
    report = out / f"{model}.{run_id}.json"
    if not report.is_file():
        return result
    summary = json.loads(report.read_text())
    if instance in summary["resolved_ids"] + summary["unresolved_ids"]:
        result["official_resolved"] = instance in summary["resolved_ids"]
    detail_file = task / "report.json"
    detail = json.loads(detail_file.read_text()).get(instance, {}) if detail_file.is_file() else {}
    applied = task / "patch.diff"
    if (code == 0 and env_ok is True and result["official_resolved"] is not None
            and detail.get("patch_successfully_applied") and not detail.get("infra_failure", True)
            and detail.get("resolved") == result["official_resolved"]
            and applied.exists() and applied.read_bytes() == (out / "model.patch").read_bytes()):
        result.update(grade_status="graded", resolved=result["official_resolved"])
    return result
