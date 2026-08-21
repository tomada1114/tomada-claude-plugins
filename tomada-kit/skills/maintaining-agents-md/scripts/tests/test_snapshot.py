#!/usr/bin/env python3
"""Tests for snapshot.py. Stdlib-only (unittest).

Every test points AGENT_SKILL_STATE_DIR at a temporary directory, so nothing is
written outside the test's own tempdir.

Run: python3 -m unittest discover -s scripts/tests -p 'test_*.py'
     (from the maintaining-agents-md skill directory)
"""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import snapshot as snap  # noqa: E402


def has_git() -> bool:
    return shutil.which("git") is not None


def run_main(argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = snap.main(argv)
    return code, out.getvalue(), err.getvalue()


class SnapshotCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name).resolve()
        self.root = base / "project"
        self.root.mkdir()
        self.state = base / "state"
        patcher = mock.patch.dict(os.environ, {"AGENT_SKILL_STATE_DIR": str(self.state)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def write(self, rel: str, text: str) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path


class TestPaths(SnapshotCase):
    def test_state_dir_from_env(self):
        self.assertEqual(snap.state_dir(), self.state)

    def test_state_dir_default_is_under_home(self):
        with mock.patch.dict(os.environ, {"HOME": str(self.root)}, clear=False):
            os.environ.pop("AGENT_SKILL_STATE_DIR", None)
            self.assertEqual(snap.state_dir(), Path(self.root) / ".local/state/agent-skills")

    def test_repo_slug_is_name_plus_digest(self):
        slug = snap.repo_slug(self.root)
        self.assertTrue(slug.startswith("project__"))
        self.assertEqual(len(slug.split("__")[1]), 8)
        self.assertEqual(slug, snap.repo_slug(self.root))

    def test_snapshots_dir_layout(self):
        d = snap.snapshots_dir(self.root)
        self.assertEqual(d.parent.parent, self.state / "maintaining-agents-md")
        self.assertEqual(d.name, "snapshots")

    def test_relative_to_root_accepts_absolute_and_relative(self):
        self.write("CLAUDE.md", "x")
        self.assertEqual(snap.relative_to_root(self.root, Path("CLAUDE.md")), "CLAUDE.md")
        self.assertEqual(snap.relative_to_root(self.root, self.root / "CLAUDE.md"), "CLAUDE.md")

    def test_relative_to_root_allows_a_file_that_does_not_exist_yet(self):
        self.assertEqual(snap.relative_to_root(self.root, Path("pkg/CLAUDE.md")), "pkg/CLAUDE.md")

    def test_relative_to_root_rejects_escapes(self):
        with self.assertRaises(snap.SnapshotError) as ctx:
            snap.relative_to_root(self.root, Path("/etc/hosts"))
        self.assertIn("outside the project root", str(ctx.exception))

    def test_new_snapshot_id_shape_and_collisions(self):
        base = snap.snapshots_dir(self.root)
        base.mkdir(parents=True)
        now = datetime(2026, 8, 20, 9, 30, 0)
        first = snap.new_snapshot_id(base, None, now)
        self.assertEqual(first, "20260820T093000Z")
        (base / first).mkdir()
        self.assertEqual(snap.new_snapshot_id(base, None, now), first + "-2")

    def test_label_is_sanitized(self):
        base = snap.snapshots_dir(self.root)
        base.mkdir(parents=True)
        sid = snap.new_snapshot_id(base, "sync/run 1", datetime(2026, 8, 20, 9, 30, 0))
        self.assertEqual(sid, "20260820T093000Z-sync-run-1")

    def test_id_exhaustion_raises(self):
        base = snap.snapshots_dir(self.root)
        base.mkdir(parents=True)
        now = datetime(2026, 8, 20, 9, 30, 0)
        stamp = "20260820T093000Z"
        (base / stamp).mkdir()
        for n in range(2, snap.MAX_ID_SUFFIX + 2):
            (base / "{}-{}".format(stamp, n)).mkdir()
        with self.assertRaises(snap.SnapshotError):
            snap.new_snapshot_id(base, None, now)


class TestSave(SnapshotCase):
    def test_save_copies_and_records(self):
        self.write("CLAUDE.md", "old body\n")
        snap_dir = snap.save_snapshot(self.root, ["CLAUDE.md"],
                                      created=["packages/api/CLAUDE.md"], label="sync")
        self.assertTrue(snap_dir.name.endswith("-sync"))
        self.assertEqual((snap_dir / "CLAUDE.md").read_text(), "old body\n")
        manifest = snap.load_manifest(snap_dir)
        by_rel = {f.rel: f for f in manifest.files}
        self.assertEqual(by_rel["CLAUDE.md"].status, "copied")
        self.assertEqual(len(by_rel["CLAUDE.md"].sha1 or ""), 40)
        self.assertEqual(by_rel["packages/api/CLAUDE.md"].status, "created")
        self.assertEqual(manifest.root, str(self.root))
        self.assertEqual(manifest.label, "sync")

    def test_missing_file_is_absent(self):
        snap_dir = snap.save_snapshot(self.root, ["gone.md"])
        self.assertEqual(snap.load_manifest(snap_dir).files[0].status, "absent")

    def test_duplicate_paths_are_recorded_once(self):
        self.write("CLAUDE.md", "x\n")
        snap_dir = snap.save_snapshot(self.root, ["CLAUDE.md", str(self.root / "CLAUDE.md")])
        self.assertEqual(len(snap.load_manifest(snap_dir).files), 1)

    def test_nested_paths_keep_their_relative_layout(self):
        self.write("packages/api/CLAUDE.md", "api\n")
        snap_dir = snap.save_snapshot(self.root, ["packages/api/CLAUDE.md"])
        self.assertEqual((snap_dir / "packages/api/CLAUDE.md").read_text(), "api\n")

    def test_save_rejects_a_bad_root(self):
        with self.assertRaises(snap.SnapshotError):
            snap.save_snapshot(self.root / "nope", ["CLAUDE.md"])

    def test_load_manifest_requires_the_file(self):
        with self.assertRaises(snap.SnapshotError):
            snap.load_manifest(self.root)


class TestList(SnapshotCase):
    def test_empty(self):
        self.assertEqual(snap.list_snapshots(self.root), [])

    def test_lists_and_ignores_junk_dirs(self):
        self.write("CLAUDE.md", "x\n")
        snap_dir = snap.save_snapshot(self.root, ["CLAUDE.md"], label="one")
        (snap_dir.parent / "not-a-snapshot").mkdir()
        listed = snap.list_snapshots(self.root)
        self.assertEqual([s["id"] for s in listed], [snap_dir.name])
        self.assertEqual(listed[0]["label"], "one")
        self.assertEqual(listed[0]["files"], ["CLAUDE.md"])


class TestRestore(SnapshotCase):
    def save_one(self, body="old body\n", **kwargs):
        self.write("CLAUDE.md", body)
        return snap.save_snapshot(self.root, ["CLAUDE.md"], **kwargs)

    def actions(self, snap_dir, **kwargs):
        manifest = snap.load_manifest(snap_dir)
        return {a.rel: a for a in snap.plan_restore(self.root, manifest, snap_dir, **kwargs)}

    def test_restore_puts_the_file_back(self):
        snap_dir = self.save_one()
        self.write("CLAUDE.md", "clobbered\n")
        acts = self.actions(snap_dir)
        self.assertEqual(acts["CLAUDE.md"].action, "restore")
        snap.apply_restore(self.root, snap_dir, list(acts.values()))
        self.assertEqual((self.root / "CLAUDE.md").read_text(), "old body\n")

    def test_identical_file_is_kept(self):
        snap_dir = self.save_one()
        self.assertEqual(self.actions(snap_dir)["CLAUDE.md"].action, "kept")

    def test_missing_snapshot_payload_is_skipped(self):
        snap_dir = self.save_one()
        (snap_dir / "CLAUDE.md").unlink()
        self.assertEqual(self.actions(snap_dir)["CLAUDE.md"].action, "skip")

    def test_created_file_is_kept_by_default_and_deleted_on_request(self):
        snap_dir = snap.save_snapshot(self.root, [], created=["NEW.md"])
        self.write("NEW.md", "written by the run\n")
        self.assertEqual(self.actions(snap_dir)["NEW.md"].action, "kept")
        acts = self.actions(snap_dir, delete_created=True)
        self.assertEqual(acts["NEW.md"].action, "delete")
        snap.apply_restore(self.root, snap_dir, list(acts.values()))
        self.assertFalse((self.root / "NEW.md").exists())

    def test_created_file_already_gone_is_skipped(self):
        snap_dir = snap.save_snapshot(self.root, [], created=["NEW.md"])
        self.assertEqual(self.actions(snap_dir, delete_created=True)["NEW.md"].action, "skip")

    def test_absent_file_is_skipped(self):
        snap_dir = snap.save_snapshot(self.root, ["gone.md"])
        self.assertEqual(self.actions(snap_dir)["gone.md"].action, "skip")

    @unittest.skipUnless(has_git(), "git is not installed")
    def test_dirty_target_is_refused_without_force(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True, capture_output=True)
        snap_dir = self.save_one()
        self.write("CLAUDE.md", "edited by hand\n")
        self.assertEqual(self.actions(snap_dir)["CLAUDE.md"].action, "refused")
        self.assertEqual(self.actions(snap_dir, force=True)["CLAUDE.md"].action, "restore")

    def test_git_is_dirty_is_false_outside_a_repo(self):
        self.write("CLAUDE.md", "x\n")
        self.assertFalse(snap.git_is_dirty(self.root, "CLAUDE.md"))

    def test_git_is_dirty_handles_a_missing_git_binary(self):
        with mock.patch("snapshot.subprocess.run", side_effect=OSError):
            self.assertFalse(snap.git_is_dirty(self.root, "CLAUDE.md"))


class TestCli(SnapshotCase):
    def test_save_text_and_json(self):
        self.write("CLAUDE.md", "body\n")
        code, out, _ = run_main(["save", str(self.root), "CLAUDE.md", "--label", "manual"])
        self.assertEqual(code, 0)
        self.assertIn("saved snapshot", out)
        self.assertIn("CLAUDE.md — copied", out)

        code, out, _ = run_main(["save", str(self.root), "CLAUDE.md", "--json"])
        data = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(data["manifest"]["files"][0]["rel"], "CLAUDE.md")

    def test_save_outside_root_exits_2(self):
        code, _, err = run_main(["save", str(self.root), "/etc/hosts"])
        self.assertEqual(code, 2)
        self.assertIn("outside the project root", err)

    def test_save_bad_root_exits_2(self):
        code, _, err = run_main(["save", str(self.root / "nope"), "CLAUDE.md"])
        self.assertEqual(code, 2)
        self.assertIn("Project root not found", err)

    def test_list_text_json_and_empty(self):
        code, out, _ = run_main(["list", str(self.root)])
        self.assertEqual(code, 0)
        self.assertIn("no snapshots", out)

        self.write("CLAUDE.md", "body\n")
        snap.save_snapshot(self.root, ["CLAUDE.md"], label="one")
        code, out, _ = run_main(["list", str(self.root)])
        self.assertIn("label=one", out)
        code, out, _ = run_main(["list", str(self.root), "--json"])
        self.assertEqual(len(json.loads(out)["snapshots"]), 1)

    def test_restore_dry_run_then_apply(self):
        self.write("CLAUDE.md", "old\n")
        snap_dir = snap.save_snapshot(self.root, ["CLAUDE.md"])
        self.write("CLAUDE.md", "new\n")

        code, out, _ = run_main(["restore", str(self.root), snap_dir.name, "--dry-run"])
        self.assertEqual(code, 0)
        self.assertIn("restore plan", out)
        self.assertEqual((self.root / "CLAUDE.md").read_text(), "new\n")

        code, out, _ = run_main(["restore", str(self.root), snap_dir.name, "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["actions"][0]["action"], "restore")
        self.assertEqual((self.root / "CLAUDE.md").read_text(), "old\n")

    def test_restore_unknown_id_exits_2(self):
        code, _, err = run_main(["restore", str(self.root), "nope"])
        self.assertEqual(code, 2)
        self.assertIn("Unknown snapshot id", err)

    @unittest.skipUnless(has_git(), "git is not installed")
    def test_restore_refusal_exits_1(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True, capture_output=True)
        self.write("CLAUDE.md", "old\n")
        snap_dir = snap.save_snapshot(self.root, ["CLAUDE.md"])
        self.write("CLAUDE.md", "hand edit\n")
        code, out, _ = run_main(["restore", str(self.root), snap_dir.name])
        self.assertEqual(code, 1)
        self.assertIn("refused", out)
        self.assertEqual((self.root / "CLAUDE.md").read_text(), "hand edit\n")


if __name__ == "__main__":
    unittest.main()
