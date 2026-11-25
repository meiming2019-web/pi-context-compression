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

    def test_every_editable_install_needs_success_evidence(self):
        log = self.out / "test_output.txt"
        cmd = "+ pip install --editable .\n"
        ok = cmd + "Successfully installed example-1.0\n"
        failed = cmd + "ERROR: Failed building editable for example\n"
        unknown = cmd + "  Successfully installed build-deps\n"
        for text, expected in [(ok + ok, True), (ok + failed, False), (failed + ok, False),
                               (ok + unknown, None), (unknown + ok, None)]:
            with self.subTest(text=text):
                log.write_text(text)
                self.assertIs(build_check(log), expected)

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

class CollectionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.out = Path(temp.name)
        self.repo = self.out / "repo"
        self.repo.mkdir()
        self.agent = ["env", "TMPDIR=" + str(self.out), "sh", "-c",
                      'cd "$0" && exec "$@"', str(self.repo)]
        self.git("init", "-q")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.org")
        self.git("commit", "--allow-empty", "-qm", "base")
        self.base = self.git("rev-parse", "HEAD").decode().strip()

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args])

    def write(self, name, content="fixture"):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def test_new_modules_data_docs_and_tests_with_locked_index(self):
        (self.repo / ".git/index.lock").touch()
        paths = ["src/foo.py", "pkg/mod.py", "lib/config.yaml", "astropy/data/new.json",
                 "docs/new file.rst", "examples/notes.txt", "tests/test_model.py"]
        for path in paths:
            self.write(path)
        patch, info = collect(self.agent, self.base, self.out)
        self.assertEqual(info["added_paths"], sorted(paths))
        self.assertEqual(info["test_files"], ["tests/test_model.py"])
        clean = self.out / "apply"
        subprocess.run(["git", "clone", "-q", str(self.repo), str(clean)], check=True)
        subprocess.run(["git", "-C", str(clean), "apply", "--index", "-"], input=patch.encode(), check=True)
        for path in paths:
            self.assertEqual((clean / path).read_text(), "fixture")

    def test_ignore_rules_do_not_change_patch(self):
        paths = [".pytest_cache/v/cache/nodeids", "pkg/__pycache__/x.pyc",
                 "nested/.pytest_cache/v/cache/lastfailed"]
        self.write("src/foo.py")
        for path in paths:
            self.write(path)
        patch, info = collect(self.agent, self.base, self.out)
        self.assertEqual(info["excluded_cache_paths"], sorted(paths))
        self.assertEqual(info["changed_paths"], ["src/foo.py"])
        self.assertNotIn("cache", patch)
        self.write(".gitignore", ".pytest_cache/\n__pycache__/\n")
        self.git("add", ".gitignore")
        self.git("commit", "-qm", "repo ignore rules")
        ignored_patch, ignored_info = collect(self.agent, "HEAD", self.out)
        self.assertEqual(ignored_patch, patch)
        self.assertEqual(ignored_info, info)

    def test_staged_and_committed_caches_and_cache_only_patch(self):
        staged, committed = "pkg/__pycache__/a.pyc", ".pytest_cache/v/cache/committed"
        self.write(committed)
        self.git("add", "-f", committed)
        self.git("commit", "-qm", "test cache")
        self.write(staged)
        self.git("add", "-f", staged)
        patch, info = collect(self.agent, self.base, self.out)
        self.assertEqual(patch, "")
        self.assertEqual(info["changed_paths"], [])
        self.assertEqual(info["excluded_cache_paths"], sorted([staged, committed]))

    def test_reserved_archive_still_quarantines_mixed_patch(self):
        self.write("pkg/mod.py")
        self.write(".pi/trace")
        self.write(".pytest_cache/v/cache/test")
        patch, info = collect(self.agent, self.base, self.out)
        self.assertIsNone(patch)
        self.assertEqual(info["grade_status"], "patch_contaminated")
        self.assertEqual(info["artifact_paths"], [".pi/trace"])
        self.assertEqual(info["excluded_cache_paths"], [".pytest_cache/v/cache/test"])
