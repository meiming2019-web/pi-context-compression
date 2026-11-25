import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from outcomes import account, build_check, collect, grade_result
from relay import provider_usage


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.out = Path(temp.name)

    def test_timeout_keeps_partial_usage_and_marks_missing_response(self):
        assistant = {"type": "message_end", "message": {"role": "assistant", "stopReason": "toolUse",
                                                       "usage": {"input": 6, "cacheRead": 4, "output": 3}}}
        usage = provider_usage(b'data: {"usage":{"prompt_tokens":10,"completion_tokens":3,'
                               b'"prompt_tokens_details":{"cached_tokens":4}}}\n\ndata: [DONE]\n')
        self.assertEqual(usage, assistant["message"]["usage"])
        ledger = [{"event": "sent", "call": 1}, {"event": "response", "call": 1, "usage": usage},
                  {"event": "sent", "call": 2}]
        (self.out / "requests.jsonl").write_text("".join(json.dumps(e) + "\n" for e in ledger))
        (self.out / "events.jsonl").write_text(json.dumps(assistant) + '\n{"type":"compaction_start"}\n{"type":')
        meta = account(self.out, None, True)
        self.assertEqual((meta["status"], meta["compaction_events"], meta["relay_calls"]),
                         ("timeout", 1, 2))
        self.assertEqual(meta["pi_usage"]["input"], 6)
        self.assertEqual(meta["calls_without_usage"], 1)
        self.assertEqual(meta["known_cost_usd"], 0.0000076)
        self.assertIsNone(meta["cost_usd"])

    def test_build_is_checked_only_inside_the_install_step(self):
        log = self.out / "test_output.txt"
        install = "+ python -m pip install -e '.[test]' --verbose\n"
        log.write_text(install + "  Successfully installed wheel\n+ pytest\n15 passed\n")
        self.assertIsNone(build_check(log))
        log.write_text(install + "ERROR: Failed building editable for astropy\n+ pytest\n15 passed\n")
        self.assertFalse(build_check(log))
        log.write_text(install + "Successfully installed astropy-5.1\n+ pytest\nERROR: bad test\n")
        self.assertTrue(build_check(log))

    def test_collect_with_original_index_locked(self):
        repo = self.out / "repo"
        repo.mkdir()
        agent = ["env", "TMPDIR=" + str(self.out), "sh", "-c",
                 'cd "$0" && exec "$@"', str(repo)]

        def git(*args):
            subprocess.run([*agent, "git", *args], check=True, capture_output=True)

        git("init", "-q")
        git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.org",
            "commit", "--allow-empty", "-qm", "base")
        (repo / ".git/index.lock").touch()
        new = repo / "astropy/tests/test_model.py"
        new.parent.mkdir(parents=True)
        new.write_text("def test_result(): pass")
        patch, meta = collect(agent, "HEAD", self.out)
        self.assertIn("test_model.py", patch)
        self.assertEqual(meta["test_files"], ["astropy/tests/test_model.py"])
        (repo / "trace.json").write_text("{}")
        patch, meta = collect(agent, "HEAD", self.out)
        self.assertIsNone(patch)
        self.assertEqual(meta["grade_status"], "patch_needs_review")
        (repo / ".pi").mkdir()
        (repo / ".pi/trace").touch()
        patch, meta = collect(agent, "HEAD", self.out)
        self.assertIsNone(patch)
        self.assertEqual(meta["artifact_paths"], [".pi/trace"])

    def test_official_pass_requires_build_and_identical_patch(self):
        task = self.out / "logs/run_evaluation/id/model/task"
        task.mkdir(parents=True)
        (self.out / "model.id.json").write_text('{"resolved_ids":["task"],"unresolved_ids":[]}')
        (task / "report.json").write_text('{"task":{"patch_successfully_applied":true,'
                                          '"resolved":true,"infra_failure":false}}')
        (self.out / "model.patch").write_bytes(b"before")
        (task / "patch.diff").write_bytes(b"before")
        install = "+ python -m pip install -e .\n"
        (task / "test_output.txt").write_text(install + "ERROR: Failed to build astropy\n")
        result = grade_result(self.out, "id", "model", "task", 0)
        self.assertTrue(result["official_resolved"])
        self.assertIsNone(result["resolved"])
        (task / "test_output.txt").write_text(install + "Successfully installed astropy-5\n")
        self.assertTrue(grade_result(self.out, "id", "model", "task", 0)["resolved"])
        (task / "patch.diff").write_bytes(b"other")
        self.assertIsNone(grade_result(self.out, "id", "model", "task", 0)["resolved"])
