"""Run the preselected Verified pilot on stock Pi, then grade its patch."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import uuid

from outcomes import account, collect, grade_result
from relay import MAX_CALLS, MODEL, forward

INSTANCE = "astropy__astropy-12907"
BASE = "d16bfe05a744909de4b27f5875fe0d4ed41ce607"
IMAGE = "swebench/sweb.eval.x86_64.astropy_1776_astropy-12907:latest"
MANIFEST = "sha256:7485c1e3c8861efd0c6a4a78b952857592e541031039000d25e9481f045dc4a3"
CONFIG = "sha256:9b1cabf7bcd83a28469f67e3852d8e2207e90d45aa71f436bb7e600bdee8bae2"
NODE = "/opt/pi/bin/node"
CLI = "/opt/pi/node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js"
ENV_PATH = "/opt/pi/bin:/opt/miniconda3/envs/testbed/bin:/usr/local/bin:/usr/bin:/bin"

WALL_SECONDS = 900
CONTEXT_WINDOW = 128000
PI_FLAGS = ("--offline", "--no-extensions", "--no-mcp", "--no-skills", "--no-context-files",
            "--no-prompt-templates", "--no-approve", "--tools", "read,bash,edit,write",
            "--provider", "pilot", "--model", MODEL, "--mode", "json")


def run(*cmd, **kwargs):
    return subprocess.run(cmd, check=True, **kwargs)


def write_json(path, data):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=2) + "\n")
    temp.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("first_rows", type=Path, help="Verified test split, HF first-rows response")
    parser.add_argument("pi_linux", type=Path, help="Linux bin/node and Pi node_modules")
    parser.add_argument("output", type=Path, help="New directory for this attempt")
    args = parser.parse_args()
    if not os.environ.get("OPENAI_API_KEY"):
        parser.error("Set OPENAI_API_KEY on the host")
    item = next(i for i in json.loads(args.first_rows.read_text())["rows"]
                if i["row"]["instance_id"] == INSTANCE)
    row = item["row"]
    if item["truncated_cells"] or row["base_commit"] != BASE or row["image"] != IMAGE:
        raise ValueError("Incomplete or unexpected pilot record")
    image = run("docker", "image", "inspect", "-f", "{{.Id}}", IMAGE,
                capture_output=True, text=True).stdout.strip()
    if image not in (MANIFEST, CONFIG):
        raise ValueError(f"Unexpected image ID {image}")
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    run_id = "m0-" + uuid.uuid4().hex[:12]
    model_name = "pi-1.6.0-A-" + MODEL
    write_json(out / "grader-input.json", [row])
    prompt = ("Fix the reported bug in this repository. Run relevant local tests to verify "
              "your change before finishing.\n\n" + row["problem_statement"])
    (out / "prompt.txt").write_text(prompt)
    meta = dict(instance_id=INSTANCE, base_commit=BASE, image_id=image, pi="1.6.0",
                model=MODEL, arm="A", run_id=run_id, network="none", wall_limit_seconds=WALL_SECONDS,
                max_calls=MAX_CALLS, context_window=CONTEXT_WINDOW, status="setup", grade_status="pending",
                env_build_ok=None, resolved=None)
    write_json(out / "run.json", meta)
    container = run("docker", "run", "-d", "--network", "none", "--platform", "linux/amd64",
                    "--security-opt", "no-new-privileges", "--mount",
                    f"type=bind,src={args.pi_linux.resolve()},dst=/opt/pi,readonly",
                    IMAGE, "sleep", "infinity", capture_output=True, text=True).stdout.strip()
    docker = ["docker", "exec", "-i"]
    agent = [*docker, "-u", "nonroot", "-e", "HOME=/home/nonroot", "-e", "PATH=" + ENV_PATH,
             "-e", "PI_CODING_AGENT_DIR=/home/nonroot/pi",
             "-e", "PI_PREVIEW_ARCHIVE_DIR=/home/nonroot/pi-preview-archive", "-w", "/testbed", container]
    try:
        # The image has a setup commit and additional Git refs. Expose only the task base.
        run(*docker, container, "bash", "-euc", """
            chmod 700 /root
            mv .git /root/image.git
            git init -q
            git fetch -q --depth 1 file:///root/image.git "$1"
            git checkout -qf --detach FETCH_HEAD
            test "$(git rev-parse HEAD)" = "$1"
            test "$(git rev-list --all --count)" = 1
            test -z "$(git status --porcelain)"
            chown -R nonroot:nonroot /testbed
        """, "setup", BASE)
        version = run(*agent, NODE, CLI, "--version", capture_output=True, text=True)
        if version.stdout.strip() != "1.6.0":
            raise ValueError("Unexpected Pi version")
        config = {"providers": {"pilot": {"baseUrl": "http://127.0.0.1:9741/v1",
                  "api": "openai-completions", "apiKey": "local-only", "models": [
                      {"id": MODEL, "contextWindow": CONTEXT_WINDOW, "maxTokens": 4096,
                       "compat": {"supportsUsageInStreaming": True}}]}}}
        run(*agent, "sh", "-ec", "mkdir -p ~/pi ~/pi-preview-archive && cat > ~/pi/models.json",
            input=json.dumps(config).encode())
        run("docker", "cp", str(Path(__file__).with_name("relay.py")), container + ":/tmp/relay.py")
        with (
            (out / "requests.jsonl").open("w") as journal,
            (out / "relay.log").open("wb") as relay_log,
            subprocess.Popen([*docker, container, "/usr/bin/python3", "-u", "/tmp/relay.py"],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=relay_log) as relay,
        ):
            if relay.stdout.readline() != b"ready\n":
                raise RuntimeError("Local model endpoint did not start")
            worker = threading.Thread(target=forward, args=(relay, journal))
            worker.start()
            try:
                command = [*agent, "timeout", "--kill-after=5s", f"{WALL_SECONDS}s",
                           NODE, CLI, *PI_FLAGS, "-p", prompt]
                with (out / "events.jsonl").open("wb") as events, (out / "pi.stderr").open("wb") as err:
                    start = time.monotonic()
                    try:
                        result = subprocess.run(command, stdout=events, stderr=err, timeout=WALL_SECONDS + 15)
                        code = result.returncode
                        timed_out = code == 124 or (code == 137 and time.monotonic() - start >= WALL_SECONDS)
                    except subprocess.TimeoutExpired:
                        code, timed_out = None, True
            finally:
                freeze = subprocess.run([*docker, container, "sh", "-c",
                                         "pkill -STOP -u nonroot || test $? = 1"])
                relay.terminate()
                relay.wait()
                worker.join()
        meta.update(account(out, code, timed_out))
        write_json(out / "run.json", meta)
        try:
            # Stop orphaned bash tools before snapshotting their working tree.
            freeze.check_returncode()
            patch, patch_info = collect(agent, BASE, out)
        except subprocess.CalledProcessError as exc:
            meta.update(grade_status="patch_collection_error", collection_exit_code=exc.returncode)
            write_json(out / "run.json", meta)
            return
        meta.update(patch_info)
        if patch == "":
            meta.update(grade_status="empty_patch", resolved=False)
        write_json(out / "run.json", meta)
        if not patch:
            print(f"{INSTANCE}: {meta['status']}, {meta['grade_status']}")
            return
        prediction = dict(instance_id=INSTANCE, model_name_or_path=model_name, model_patch=patch)
        (out / "predictions.jsonl").write_text(json.dumps(prediction) + "\n")
    finally:
        run("docker", "rm", "-f", container, stdout=subprocess.DEVNULL)
    with (out / "grader.log").open("wb") as log:
        grader = subprocess.run([sys.executable, "-m", "swebench.harness.run_evaluation", "--dataset_name",
            str(out / "grader-input.json"), "--predictions_path", str(out / "predictions.jsonl"),
            "--instance_ids", INSTANCE, "--run_id", run_id, "--max_workers", "1"],
            cwd=out, stdout=log, stderr=subprocess.STDOUT)
    meta.update(grade_result(out, run_id, model_name, INSTANCE, grader.returncode))
    write_json(out / "run.json", meta)
    print(f"{INSTANCE}: {meta['status']}, {meta['grade_status']}, resolved={meta['resolved']}")


if __name__ == "__main__":
    main()
