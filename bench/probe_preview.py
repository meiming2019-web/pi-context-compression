"""Use real Pi and a scripted local model. No paid calls or task scores."""
import argparse
from email.message import Message
import io
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.error import HTTPError
from unittest.mock import patch

import m0
import relay


class LocalResponse(io.BytesIO):
    status = 200
    headers = Message()
    headers["Content-Type"] = "text/event-stream"


def stream(tool, inputs, turn):
    delta = {"role": "assistant", "content": "done"}
    if tool:
        delta = {"role": "assistant", "tool_calls": [{"index": 0, "type": "function",
                 "id": f"call_{turn}", "function": {"name": tool, "arguments": json.dumps(inputs)}}]}
    events = [{"id": f"probe-{turn}", "object": "chat.completion.chunk", "created": 100,
               "model": relay.MODEL, "choices": [{"index": 0, "delta": block, "finish_reason": finish}]}
              for block, finish in [(delta, None), ({}, "tool_calls" if tool else "stop")]]
    events.append({"choices": [], "usage": {"prompt_tokens": 64, "completion_tokens": 8}})
    body = b"".join(b"data: " + json.dumps(e).encode() + b"\n\n" for e in events)
    return LocalResponse(body + b"data: [DONE]\n\n")


def probe(arm, args):
    turns = []
    path = None
    resuming = False
    errors = []

    def respond(request, **kwargs):
        nonlocal path
        messages = json.loads(request.data)["messages"]
        results = [m["content"] for m in messages if m["role"] == "tool"]
        assert results[:len(turns)] == turns, "earlier tool message changed on the wire"
        turns[:] = results
        turn = len(results)
        if resuming:
            if turn < 4:
                raise ValueError("The resumed session lost its previous tool history")
            if turn == 4:
                source = results[0] if arm != "A" else results[1]
                archive = re.search(r"(?:Full output: |read )(/[^\s\]]+)", source)[1]
                return stream("read", {"path": archive, "offset": 100, "limit": 2}, turn)
            return stream(None, {}, turn)
        if turn in (0, 1):
            count = [400, 3100][turn]
            return stream("bash", {"command": f"echo HEAD_SENTINEL; seq 1 {count}; echo TAIL_SENTINEL; exit 7"}, turn)
        if turn == 2:
            text = results[-1]
            match = re.search(r"(?:Full output: |read )(/[^\s\]]+)", text)
            if not match:
                raise ValueError(f"Missing archive in {arm} preview: {text[-240:]}")
            path = match[1]
        if turn in (2, 3):
            return stream("read", {"path": path, "offset": 100, "limit": 2}, turn)
        return stream(None, {}, turn)

    def endpoint(request, **kwargs):
        try:
            return respond(request, **kwargs)
        except Exception as exc:
            errors.append(str(exc))
            raise HTTPError(request.full_url, 400, "fixture assertion", {}, None) from exc

    out = args.output.resolve() / arm
    run = subprocess.run

    def run_with_resume(cmd, *pos, **kw):
        nonlocal resuming
        result = run(cmd, *pos, **kw)
        if result.returncode == 0 and m0.CLI in cmd and "-p" in cmd:
            resuming = True
            with (out / "resume-events.jsonl").open("wb") as events:
                resumed = [*cmd[:-2], "--continue", "-p", "Read the saved log again."]
                run(resumed, *pos, **{**kw, "stdout": events, "check": True})
        return result
    argv = ["m0", str(args.first_rows), str(args.pi_linux), str(out),
            "--arm", arm, "--preview-tokens", "128"]
    with patch.dict("os.environ", OPENAI_API_KEY="local-fixture"), patch.object(sys, "argv", argv), \
            patch.object(relay.urllib.request, "urlopen", side_effect=endpoint), \
            patch.object(subprocess, "run", side_effect=run_with_resume):
        m0.main()
    meta = json.loads((out / "run.json").read_text())
    assert meta["status"] == "completed" and meta["grade_status"] == "empty_patch", meta
    assert not errors, errors
    assert resuming and len(turns) == 5 and turns[2] == turns[3]
    assert all("99\n100" in text for text in turns[2:])
    assert all("TAIL_SENTINEL" in text for text in turns[:2])
    assert ["HEAD_SENTINEL" in text for text in turns[:2]] == {
        "A": [True, False], "B": [False, False], "C": [True, True]}[arm]
    assert [r["repeated"] for r in meta["readbacks"]] == [False, True]
    if arm != "A":
        assert [p["route"] for p in meta["previews"]] == ["self_archive", "pi_archive"]
        assert all(p["tokens"] <= 128 for p in meta["previews"])
        assert all("exit 7" in text for text in turns[:2])
    summary = {"arm": arm, "preview_tokens": [p["tokens"] for p in meta["previews"]],
            "readback_text": turns[2], "wire_history_stable": True, "resume_read_verified": True}
    (out / "probe.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["first_rows", "pi_linux", "output"]:
        parser.add_argument(name, type=Path)
    parser.add_argument("--arms", choices=["A", "B", "C"], nargs="+", default=["A", "B", "C"])
    args = parser.parse_args()
    print(json.dumps([probe(arm, args) for arm in args.arms], indent=2))
