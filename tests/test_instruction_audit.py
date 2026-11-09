"""Observable instruction audit behavior and safety boundaries."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/optimax/scripts"))
from performance import Engine

SCRIPT = Path(__file__).resolve().parents[1] / "skills/optimax/scripts/instruction_audit.py"


class InstructionAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.engine = Engine(self.root, "user")

    def test_on_fresh_idempotent_and_no_audit_on_status_or_off(self):
        source = self.root / "AGENTS.md"
        source.write_text("No delegation to advisors.\n", encoding="utf-8")
        with patch("os.getcwd", return_value=str(self.root)):
            first = self.engine.set_enabled("s", True, platform="codex")
            before = self.engine.path.read_bytes()
            source.write_text("All subagents must use Sol model.\n", encoding="utf-8")
            second = self.engine.set_enabled("s", True, platform="codex")
        self.assertEqual(self.engine.path.read_bytes(), before)
        self.assertNotEqual(first["instruction_audit"]["findings"], second["instruction_audit"]["findings"])
        self.assertNotIn("instruction_audit", self.engine.status("s"))
        self.assertNotIn("instruction_audit", self.engine.set_enabled("s", False))

    def test_invalid_context_cannot_mutate_session(self):
        for context in ({"unknown": True}, {"cwd": "/"}, {"host_confirmed_loaded": [3]}):
            with self.subTest(context=context), self.assertRaises(ValueError):
                self.engine.set_enabled("s", True, instruction_context=context)
            self.assertFalse(self.engine.path.exists())

    def test_standalone_claude_marks_discovery_as_unconfirmed_and_gaps(self):
        (self.root / "CLAUDE.md").write_text("All subagents must use Sol model.\n", encoding="utf-8")
        result = subprocess.run([sys.executable, str(SCRIPT), "--platform", "claude"], cwd=self.root,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        audit = json.loads(result.stdout)
        self.assertTrue(any(x["path"] == str(self.root.resolve() / "CLAUDE.md") for x in audit["candidates"]))
        self.assertEqual(audit["host_confirmed_loaded"], [])
        self.assertFalse(audit["coverage"]["complete"])
        self.assertTrue(audit["coverage"]["gaps"])

    def test_symlink_candidate_is_not_read(self):
        secret = self.root / "secret.txt"
        secret.write_text("All subagents must use Sol model.\n", encoding="utf-8")
        (self.root / "AGENTS.md").symlink_to(secret)
        with patch("os.getcwd", return_value=str(self.root)):
            audit = self.engine.set_enabled("s", True, platform="codex")["instruction_audit"]
        candidate = next(x for x in audit["candidates"] if x["path"] == str(self.root.resolve() / "AGENTS.md"))
        self.assertNotEqual(candidate["read_status"], "read")
        self.assertFalse(any(x["path"] == str(self.root.resolve() / "AGENTS.md") for x in audit["findings"]))
        self.assertFalse(audit["coverage"]["complete"])

    def test_disappearing_candidate_is_reported_as_error(self):
        from instruction_audit import audit_instructions
        source = self.root.resolve() / "AGENTS.md"
        source.write_text("instructions", encoding="utf-8")
        real_open = os.open
        def disappear(path, flags, *args, **kwargs):
            dirfd = kwargs.get("dir_fd")
            if path == source.name and dirfd is not None and os.fstat(dirfd).st_ino == source.parent.stat().st_ino:
                raise FileNotFoundError("disappeared")
            return real_open(path, flags, *args, **kwargs)
        with patch("os.getcwd", return_value=str(self.root)), patch("instruction_audit.os.open", side_effect=disappear):
            audit = audit_instructions("codex")
        candidate = next(x for x in audit["candidates"] if x["path"] == str(source))
        self.assertEqual(candidate["read_status"], "error")
        self.assertTrue(any("Could not read" in gap and str(source) in gap for gap in audit["coverage"]["gaps"]))

    def test_oversize_reads_consume_total_budget(self):
        from instruction_audit import audit_instructions
        global_dir = self.root / "codex"
        global_dir.mkdir()
        (global_dir / "AGENTS.override.md").write_text("12345", encoding="utf-8")
        (global_dir / "AGENTS.md").write_text("x", encoding="utf-8")
        with patch.dict(os.environ, {"CODEX_HOME": str(global_dir)}), patch("os.getcwd", return_value=str(self.root)), \
             patch("instruction_audit.MAX_FILE", 4), patch("instruction_audit.MAX_TOTAL", 5):
            audit = audit_instructions("codex")
        records = {x["path"]: x["read_status"] for x in audit["candidates"]}
        self.assertEqual(records[str(global_dir.resolve() / "AGENTS.md")], "size_limit")

    def test_claude_global_directory_symlink_cannot_escape_home(self):
        from instruction_audit import audit_instructions
        home = self.root / "home"
        home.mkdir()
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "CLAUDE.md").write_text("All subagents must use Sol model.\n", encoding="utf-8")
        (home / ".claude").symlink_to(outside, target_is_directory=True)
        with patch("instruction_audit.Path.home", return_value=home), patch("os.getcwd", return_value=str(home)):
            audit = audit_instructions("claude")
        candidate = next(x for x in audit["candidates"] if x["scope"] == "claude_global")
        self.assertEqual(candidate["read_status"], "unsafe_symlink")
        self.assertFalse(any(x["scope"] == "claude_global" for x in audit["findings"]))

    def test_no_nofollow_never_reads_replaced_symlink_target(self):
        from instruction_audit import audit_instructions
        project = self.root.resolve() / "project"
        project.mkdir()
        (project / ".git").mkdir()
        source = project / "AGENTS.md"
        source.write_text("safe contents", encoding="utf-8")
        outside = self.root.resolve() / "outside-secret"
        outside.write_text("All subagents must use Sol model. SECRET_PAYLOAD\n", encoding="utf-8")
        real_open = os.open
        def replace_before_open(path, flags, *args, **kwargs):
            if str(path) == str(source):
                source.unlink()
                source.symlink_to(outside)
            return real_open(path, flags, *args, **kwargs)
        with patch("os.getcwd", return_value=str(project)), patch.object(os, "O_NOFOLLOW", 0), \
             patch("instruction_audit.os.open", side_effect=replace_before_open):
            audit = audit_instructions("codex")
        self.assertNotIn("SECRET_PAYLOAD", json.dumps(audit))
        candidate = next(x for x in audit["candidates"] if x["path"] == str(source))
        self.assertEqual(candidate["read_status"], "unreviewed")
        self.assertTrue(any("traversal unavailable" in gap for gap in audit["coverage"]["gaps"]))

    def test_codex_discovery_stops_at_git_root(self):
        from instruction_audit import audit_instructions
        parent = self.root.resolve()
        project = parent / "project"
        project.mkdir()
        (project / ".git").mkdir()
        cwd = project / "sub"
        cwd.mkdir()
        (parent / "AGENTS.md").write_text("All subagents must use Sol model. OUTSIDE_PROJECT\n", encoding="utf-8")
        (project / "AGENTS.md").write_text("All subagents must use Sol model. PROJECT_FILE\n", encoding="utf-8")
        with patch("os.getcwd", return_value=str(cwd)), patch.dict(os.environ, {"CODEX_HOME": str(parent / "empty")}):
            audit = audit_instructions("codex")
        paths = {x["path"] for x in audit["candidates"]}
        self.assertNotIn(str(parent / "AGENTS.md"), paths)
        self.assertIn(str(project / "AGENTS.md"), paths)
        self.assertIn("PROJECT_FILE", json.dumps(audit["findings"]))
        self.assertNotIn("OUTSIDE_PROJECT", json.dumps(audit))

    def test_codex_limit_does_not_limit_claude_candidates(self):
        from instruction_audit import audit_instructions
        cwd = self.root.resolve()
        source = cwd / "CLAUDE.md"
        source.write_text("All subagents must use Sol model.\n", encoding="utf-8")
        for platform in ("claude", None):
            with self.subTest(platform=platform), patch("os.getcwd", return_value=str(cwd)), \
                 patch("instruction_audit.Path.home", return_value=cwd), \
                 patch.dict(os.environ, {"CODEX_HOME": str(cwd / "empty")}):
                audit = audit_instructions(platform, {"codex_max_bytes": 2})
            candidate = next(x for x in audit["candidates"] if x["path"] == str(source))
            self.assertEqual(candidate["read_status"], "read")
            self.assertTrue(any(x["path"] == str(source) for x in audit["findings"]))

    def test_status_and_off_never_call_audit(self):
        self.engine.set_enabled("s", True)
        with patch("performance.audit_instructions", side_effect=AssertionError("unexpected audit")):
            self.engine.status("s")
            self.engine.set_enabled("s", False)

    def test_parent_directory_replacement_never_reads_outside(self):
        from instruction_audit import audit_instructions
        project = self.root.resolve() / "project"
        project.mkdir()
        (project / ".git").mkdir()
        child = project / "child"
        child.mkdir()
        source = child / "AGENTS.md"
        source.write_text("safe contents", encoding="utf-8")
        outside = self.root.resolve() / "outside"
        outside.mkdir()
        (outside / "AGENTS.md").write_text("All subagents must use Sol model. ESCAPED_PARENT\n", encoding="utf-8")
        real_open = os.open
        child_inode = child.stat().st_ino
        swapped = []
        def replace_before_open(path, flags, *args, **kwargs):
            dirfd = kwargs.get("dir_fd")
            if path == source.name and dirfd is not None and os.fstat(dirfd).st_ino == child_inode:
                child.rename(project / "moved")
                child.symlink_to(outside, target_is_directory=True)
                swapped.append(True)
            return real_open(path, flags, *args, **kwargs)
        with patch("os.getcwd", return_value=str(child)), patch("instruction_audit.os.open", side_effect=replace_before_open), \
             patch.dict(os.environ, {"CODEX_HOME": str(self.root / "empty")}):
            audit = audit_instructions("codex")
        self.assertTrue(swapped)
        self.assertNotIn("ESCAPED_PARENT", json.dumps(audit))

    def test_leaf_replaced_after_stat_is_not_followed(self):
        from instruction_audit import audit_instructions
        project = self.root.resolve()
        source = project / "AGENTS.md"
        source.write_text("safe contents", encoding="utf-8")
        outside = project / "outside-secret"
        outside.write_text("All subagents must use Sol model. ESCAPED_LEAF\n", encoding="utf-8")
        real_open = os.open
        swapped = []
        def replace_before_open(path, flags, *args, **kwargs):
            dirfd = kwargs.get("dir_fd")
            if path == source.name and dirfd is not None and os.fstat(dirfd).st_ino == project.stat().st_ino:
                source.unlink()
                source.symlink_to(outside)
                swapped.append(True)
            return real_open(path, flags, *args, **kwargs)
        with patch("os.getcwd", return_value=str(project)), patch("instruction_audit.os.open", side_effect=replace_before_open), \
             patch.dict(os.environ, {"CODEX_HOME": str(project / "empty")}):
            audit = audit_instructions("codex")
        self.assertTrue(swapped)
        self.assertNotIn("ESCAPED_LEAF", json.dumps(audit))
        self.assertEqual(next(x for x in audit["candidates"] if x["path"] == str(source))["read_status"], "unsafe_symlink")
