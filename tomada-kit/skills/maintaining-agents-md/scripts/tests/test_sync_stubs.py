#!/usr/bin/env python3
"""Tests for sync_stubs.py. Stdlib-only (unittest).

Every test points AGENT_SKILL_STATE_DIR at a temporary directory, so snapshots
never touch the real home directory.

Run: python3 -m unittest discover -s scripts/tests -p 'test_*.py'
     (from the maintaining-agents-md skill directory)
"""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import inventory as inv  # noqa: E402
import snapshot as snap  # noqa: E402
import sync_stubs as sync  # noqa: E402

STUB = inv.MANAGED_BLOCK
LEGACY_BODY = "# Project\n\nRun `npm test` before pushing.\n"


def run_main(argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = sync.main(argv)
    return code, out.getvalue(), err.getvalue()


class SyncCase(unittest.TestCase):
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

    def write(self, rel: str, data) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data.encode("utf-8") if isinstance(data, str) else data)
        return path

    def plan(self, **kwargs):
        return {i.path: i for i in sync.plan_sync(self.root, **kwargs)}

    def read(self, rel: str) -> bytes:
        return (self.root / rel).read_bytes()


class TestPlan(SyncCase):
    def test_missing_stub_is_created(self):
        self.write("AGENTS.md", "# Root\n")
        item = self.plan()["CLAUDE.md"]
        self.assertEqual((item.state, item.action), ("missing", "create"))
        self.assertEqual(item.desired, STUB)

    def test_compliant_stub_is_unchanged(self):
        self.write("AGENTS.md", "# Root\n")
        self.write("CLAUDE.md", STUB)
        self.assertEqual(self.plan()["CLAUDE.md"].action, "unchanged")

    def test_stub_with_extras_is_unchanged(self):
        self.write("AGENTS.md", "# Root\n")
        self.write("CLAUDE.md", STUB + "\n# Claude Code specifics\n\n- hooks\n")
        self.assertEqual(self.plan()["CLAUDE.md"].action, "unchanged")

    def test_blank_lines_inside_the_block_are_not_drift(self):
        # A markdown formatter puts a blank line between the comment and the import.
        self.write("AGENTS.md", "# Root\n")
        self.write("CLAUDE.md", "{}\n\n{}\n\n{}\n\n# Extras\n".format(
            inv.MANAGED_BEGIN, inv.IMPORT_LINE, inv.MANAGED_END))
        item = self.plan()["CLAUDE.md"]
        self.assertEqual((item.state, item.action), ("stub+extras", "unchanged"))

    def test_leading_blank_lines_are_drift(self):
        self.write("AGENTS.md", "# Root\n")
        self.write("CLAUDE.md", "\n\n" + STUB)
        item = self.plan()["CLAUDE.md"]
        self.assertEqual((item.state, item.action), ("stub", "rewrite-block"))
        self.assertEqual(item.desired, STUB)

    def test_padded_import_line_is_drift(self):
        self.write("AGENTS.md", "# Root\n")
        self.write("CLAUDE.md", inv.MANAGED_BEGIN + "\n   @AGENTS.md  \n" + inv.MANAGED_END + "\n")
        item = self.plan()["CLAUDE.md"]
        self.assertEqual((item.state, item.action), ("stub", "rewrite-block"))

    def test_legacy_import_is_adopted(self):
        self.write("AGENTS.md", "# Root\n")
        self.write("CLAUDE.md", "@AGENTS.md\n\n# Claude Code Specifics\n\n- hooks\n")
        item = self.plan()["CLAUDE.md"]
        self.assertEqual((item.state, item.action), ("legacy-import", "adopt"))
        self.assertEqual(item.desired, STUB + "\n# Claude Code Specifics\n\n- hooks\n")

    def test_legacy_is_skipped_and_forced(self):
        self.write("AGENTS.md", "# Root\n")
        self.write("CLAUDE.md", LEGACY_BODY)
        item = self.plan()["CLAUDE.md"]
        self.assertEqual(item.action, "skip")
        self.assertIn("migrate", item.reason)
        forced = self.plan(force=True)["CLAUDE.md"]
        self.assertEqual(forced.action, "rewrite-block")
        self.assertEqual(forced.desired, STUB)

    def test_empty_legacy_file_needs_no_force(self):
        self.write("AGENTS.md", "# Root\n")
        self.write("CLAUDE.md", "\n\n")
        item = self.plan()["CLAUDE.md"]
        self.assertEqual(item.action, "create")
        self.assertEqual(item.desired, STUB)

    def test_malformed_repairable(self):
        self.write("AGENTS.md", "# Root\n")
        self.write("CLAUDE.md", "# Title\n\n" + STUB + "\ntail\n")
        item = self.plan()["CLAUDE.md"]
        self.assertEqual((item.state, item.action), ("malformed", "repair"))
        self.assertEqual(item.desired, STUB + "\n# Title\n\ntail\n")

    def test_malformed_unrepairable_is_skipped(self):
        self.write("AGENTS.md", "# Root\n")
        self.write("CLAUDE.md", inv.MANAGED_BEGIN + "\n@AGENTS.md\n")
        item = self.plan()["CLAUDE.md"]
        self.assertEqual(item.action, "skip")
        self.assertIn("markers", item.reason)

    def test_orphan_is_reported_and_never_touched(self):
        self.write("docs/CLAUDE.md", "# Docs\n")
        item = self.plan()["docs/CLAUDE.md"]
        self.assertEqual((item.state, item.action), ("orphan", "skip"))

    def test_subdirectory_gets_its_own_stub(self):
        self.write("AGENTS.md", "# Root\n")
        self.write("CLAUDE.md", STUB)
        self.write("packages/api/AGENTS.md", "# API\n")
        plan = self.plan()
        self.assertEqual(plan["packages/api/CLAUDE.md"].action, "create")


class TestApply(SyncCase):
    def test_create_and_snapshot_manifest(self):
        self.write("AGENTS.md", "# Root\n")
        self.write("CLAUDE.md", "@AGENTS.md\n\n# Claude\n")
        self.write("packages/api/AGENTS.md", "# API\n")
        items = sync.plan_sync(self.root)
        snap_dir = sync.apply_plan(self.root, items)

        self.assertEqual(self.read("CLAUDE.md").decode(), STUB + "\n# Claude\n")
        self.assertEqual(self.read("packages/api/CLAUDE.md").decode(), STUB)
        manifest = snap.load_manifest(snap_dir)
        by_rel = {f.rel: f.status for f in manifest.files}
        self.assertEqual(by_rel["CLAUDE.md"], "copied")
        self.assertEqual(by_rel["packages/api/CLAUDE.md"], "created")
        self.assertEqual((snap_dir / "CLAUDE.md").read_bytes(), b"@AGENTS.md\n\n# Claude\n")

    def test_no_pending_writes_takes_no_snapshot(self):
        self.write("AGENTS.md", "# Root\n")
        self.write("CLAUDE.md", STUB)
        self.assertIsNone(sync.apply_plan(self.root, sync.plan_sync(self.root)))
        self.assertEqual(snap.list_snapshots(self.root), [])

    def test_no_snapshot_flag(self):
        self.write("AGENTS.md", "# Root\n")
        sync.apply_plan(self.root, sync.plan_sync(self.root), snapshot=False)
        self.assertEqual(snap.list_snapshots(self.root), [])
        self.assertEqual(self.read("CLAUDE.md").decode(), STUB)

    def test_free_section_survives_byte_for_byte(self):
        self.write("AGENTS.md", "# Root\n")
        free = b"\n# Claude Code specifics\r\n\r\n- CRLF line\r\n\ttab\n\xe6\x97\xa5\xe6\x9c\xac\xe8\xaa\x9e\n"
        self.write("CLAUDE.md", b"\n\n" + STUB.encode() + free)
        sync.apply_plan(self.root, sync.plan_sync(self.root))
        self.assertEqual(self.read("CLAUDE.md"), STUB.encode() + free)

    def test_second_run_is_a_no_op(self):
        self.write("AGENTS.md", "# Root\n")
        self.write("CLAUDE.md", "@AGENTS.md\n\n# Claude\n")
        sync.apply_plan(self.root, sync.plan_sync(self.root))
        first = self.read("CLAUDE.md")
        items = sync.plan_sync(self.root)
        self.assertEqual(items[0].action, "unchanged")
        sync.apply_plan(self.root, items)
        self.assertEqual(self.read("CLAUDE.md"), first)

    def test_legacy_body_is_untouched_without_force(self):
        self.write("AGENTS.md", "# Root\n")
        self.write("CLAUDE.md", LEGACY_BODY)
        sync.apply_plan(self.root, sync.plan_sync(self.root))
        self.assertEqual(self.read("CLAUDE.md").decode(), LEGACY_BODY)

    def test_force_keeps_the_old_body_in_the_snapshot(self):
        self.write("AGENTS.md", "# Root\n")
        self.write("CLAUDE.md", LEGACY_BODY)
        items = sync.plan_sync(self.root, force=True)
        snap_dir = sync.apply_plan(self.root, items)
        self.assertEqual(self.read("CLAUDE.md").decode(), STUB)
        self.assertEqual((snap_dir / "CLAUDE.md").read_text(), LEGACY_BODY)


    def test_apply_refuses_a_plan_item_with_no_content(self):
        item = sync.PlanItem("CLAUDE.md", "missing", "create", "bad plan", None)
        with self.assertRaises(ValueError) as ctx:
            sync.apply_plan(self.root, [item], snapshot=False)
        self.assertIn("no content", str(ctx.exception))


class TestCli(SyncCase):
    def test_check_reports_drift_without_writing(self):
        self.write("AGENTS.md", "# Root\n")
        code, out, _ = run_main([str(self.root), "--check"])
        self.assertEqual(code, 1)
        self.assertIn("would change 1 file(s)", out)
        self.assertFalse((self.root / "CLAUDE.md").exists())

    def test_check_is_clean_when_in_sync(self):
        self.write("AGENTS.md", "# Root\n")
        self.write("CLAUDE.md", STUB)
        code, out, _ = run_main([str(self.root), "--check"])
        self.assertEqual(code, 0)
        self.assertIn("mode: check", out)

    def test_dry_run_prints_the_plan_without_writing(self):
        self.write("AGENTS.md", "# Root\n")
        self.write("CLAUDE.md", LEGACY_BODY)
        code, out, _ = run_main([str(self.root), "--dry-run"])
        self.assertEqual(code, 1)
        self.assertIn("skip", out)
        self.assertIn("(was: legacy)", out)
        self.assertEqual(self.read("CLAUDE.md").decode(), LEGACY_BODY)

    def test_apply_json_output(self):
        self.write("AGENTS.md", "# Root\n")
        code, out, _ = run_main([str(self.root), "--json"])
        data = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(data["changed"], 1)
        self.assertEqual(data["items"][0]["action"], "create")
        self.assertNotIn("desired", data["items"][0])
        self.assertTrue(data["snapshot_dir"].startswith(str(self.state)))

    def test_apply_text_output_names_the_snapshot(self):
        self.write("AGENTS.md", "# Root\n")
        self.write("CLAUDE.md", "@AGENTS.md\n")
        code, out, _ = run_main([str(self.root)])
        self.assertEqual(code, 0)
        self.assertIn("snapshot: {}".format(self.state), out)
        self.assertIn("adopt", out)

    def test_apply_exit_1_when_something_was_skipped(self):
        self.write("AGENTS.md", "# Root\n")
        self.write("CLAUDE.md", LEGACY_BODY)
        code, out, _ = run_main([str(self.root)])
        self.assertEqual(code, 1)
        self.assertIn("changed 0 file(s), skipped 1", out)

    def test_force_with_no_snapshot_is_refused(self):
        (self.root / "AGENTS.md").write_text("# rules\n")
        (self.root / "CLAUDE.md").write_text("# legacy body\n")
        code, _, err = run_main([str(self.root), "--force", "--no-snapshot"])
        self.assertEqual(code, 2)
        self.assertIn("--no-snapshot", err)
        self.assertEqual((self.root / "CLAUDE.md").read_text(), "# legacy body\n")
        # preview forms are still allowed together
        code, _, _ = run_main([str(self.root), "--force", "--no-snapshot", "--dry-run"])
        self.assertIn(code, (0, 1))

    def test_no_snapshot_flag_via_cli(self):
        self.write("AGENTS.md", "# Root\n")
        code, out, _ = run_main([str(self.root), "--no-snapshot", "--json"])
        self.assertEqual(code, 0)
        self.assertIsNone(json.loads(out)["snapshot_dir"])

    def test_empty_project_reports_nothing_to_do(self):
        code, out, _ = run_main([str(self.root)])
        self.assertEqual(code, 0)
        self.assertIn("no AGENTS.md", out)

    def test_missing_root_exits_2(self):
        code, _, err = run_main([str(self.root / "nope")])
        self.assertEqual(code, 2)
        self.assertIn("Pass an existing directory", err)

    def test_bad_max_depth_exits_2(self):
        code, _, err = run_main([str(self.root), "--max-depth", "0"])
        self.assertEqual(code, 2)
        self.assertIn("--max-depth", err)

    def test_snapshot_error_exits_2(self):
        self.write("AGENTS.md", "# Root\n")
        with mock.patch("sync_stubs.save_snapshot",
                        side_effect=sync.SnapshotError("state dir unwritable")):
            code, _, err = run_main([str(self.root)])
        self.assertEqual(code, 2)
        self.assertIn("state dir unwritable", err)

    def test_write_failure_exits_2(self):
        self.write("AGENTS.md", "# Root\n")
        with mock.patch("sync_stubs.inventory.write_text",
                        side_effect=OSError("Read-only file system")):
            code, _, err = run_main([str(self.root), "--no-snapshot"])
        self.assertEqual(code, 2)
        self.assertIn("Read-only file system", err)

    def test_default_root_when_omitted(self):
        cwd = os.getcwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, cwd)
        self.write("AGENTS.md", "# Root\n")
        code, _, _ = run_main(["--json"])
        self.assertEqual(code, 0)
        self.assertEqual(self.read("CLAUDE.md").decode(), STUB)


if __name__ == "__main__":
    unittest.main()
