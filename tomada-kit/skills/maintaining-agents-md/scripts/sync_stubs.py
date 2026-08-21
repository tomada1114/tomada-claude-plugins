#!/usr/bin/env python3
"""sync_stubs.py — Make every CLAUDE.md beside an AGENTS.md a compliant stub.

Usage:
    sync_stubs.py [<root>] [--dry-run] [--check] [--force]
                           [--no-snapshot] [--max-depth N] [--json]

<root> defaults to the git toplevel of the current directory, else the current
directory. For each directory that holds an AGENTS.md, the CLAUDE.md next to it
must start with the managed block:

    <!-- agents-md-sync:begin -->
    @AGENTS.md
    <!-- agents-md-sync:end -->

Everything after the end marker is the free, hand-maintained Claude-only
section; it is preserved byte for byte.

Actions per file:
    create         no CLAUDE.md yet -> write the block
    adopt          a bare `@AGENTS.md` line -> wrap it in markers, keep the rest
    rewrite-block  block drifted (or --force over a legacy body) -> rewrite it
    repair         markers present but broken, remainder recoverable
    unchanged      already compliant
    skip           legacy body (run migrate, or --force), unrepairable markers,
                   or an orphan CLAUDE.md with no AGENTS.md beside it

Flags:
    --dry-run      print the full plan, write nothing
    --check        write nothing; exit 1 if any write would happen (CI drift check)
    --force        also replace a legacy CLAUDE.md body with the bare stub. Use
                   only after migrate has moved that body into AGENTS.md; the
                   previous content is recoverable from the snapshot.
    --no-snapshot  do not snapshot the files about to change

Every file that is modified is snapshotted first (see snapshot.py); newly
created files are recorded in the manifest as `created`. Nothing outside the
project root is written except the snapshot directory, and nothing is deleted.

Exit codes:
    0 = nothing left to do
    1 = pending writes (with --check/--dry-run) or a skipped file
    2 = bad invocation
"""
from __future__ import annotations

import argparse
import textwrap
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import inventory  # noqa: E402
from snapshot import SnapshotError, save_snapshot  # noqa: E402

WRITE_ACTIONS = ("create", "adopt", "rewrite-block", "repair")


@dataclass
class PlanItem:
    path: str
    state: str
    action: str
    reason: str = ""
    desired: Optional[str] = None  # dropped from the report; only apply() uses it

    def to_dict(self) -> Dict[str, str]:
        return {"path": self.path, "state": self.state, "action": self.action,
                "reason": self.reason}


@dataclass
class SyncReport:
    root: str
    dry_run: bool = False
    check: bool = False
    snapshot_dir: Optional[str] = None
    items: List[PlanItem] = field(default_factory=list)

    @property
    def pending(self) -> List[PlanItem]:
        return [i for i in self.items if i.action in WRITE_ACTIONS]

    @property
    def skipped(self) -> List[PlanItem]:
        return [i for i in self.items if i.action == "skip"]

    def to_dict(self) -> Dict[str, object]:
        return {
            "root": self.root,
            "dry_run": self.dry_run,
            "check": self.check,
            "snapshot_dir": self.snapshot_dir,
            "changed": len(self.pending),
            "skipped": len(self.skipped),
            "items": [i.to_dict() for i in self.items],
        }


def plan_for_file(root: Path, entry: "inventory.ClaudeMdEntry", force: bool = False) -> PlanItem:
    """Decide the action for one CLAUDE.md. Pure: reads the file, writes nothing."""
    path = root / entry.path
    if entry.state == "orphan":
        return PlanItem(entry.path, entry.state, "skip",
                        "no AGENTS.md in this directory; sync never touches it")
    if entry.state == "missing":
        return PlanItem(entry.path, entry.state, "create", "no CLAUDE.md yet",
                        inventory.MANAGED_BLOCK)

    text = inventory.read_text(path)
    parse = inventory.parse_claude_md(text)

    if parse.state in ("stub", "stub+extras"):
        desired = inventory.compose_stub(parse.free_section)
        if desired == text or inventory.block_equivalent(text, desired):
            return PlanItem(entry.path, entry.state, "unchanged", "already compliant")
        return PlanItem(entry.path, entry.state, "rewrite-block",
                        "managed block drifted; free section preserved", desired)

    if parse.state == "legacy-import":
        desired = inventory.compose_stub(inventory.adopt_free_section(text))
        return PlanItem(entry.path, entry.state, "adopt",
                        "wrapping the existing import in markers; rest kept as the "
                        "free section", desired)

    if parse.state == "malformed":
        if parse.repairable:
            desired = inventory.compose_stub(inventory.repair_free_section(parse))
            return PlanItem(entry.path, entry.state, "repair", parse.detail, desired)
        return PlanItem(entry.path, entry.state, "skip",
                        "{}; fix the markers by hand".format(parse.detail))

    # legacy
    if not text.strip():
        return PlanItem(entry.path, entry.state, "create",
                        "file is empty; nothing to lose", inventory.MANAGED_BLOCK)
    if force:
        return PlanItem(entry.path, entry.state, "rewrite-block",
                        "--force: replacing the legacy body with the stub (previous "
                        "content is in the snapshot)", inventory.MANAGED_BLOCK)
    return PlanItem(entry.path, entry.state, "skip",
                    "legacy body; run migrate to fold it into AGENTS.md, or pass "
                    "--force once that is done")


def plan_sync(root: Path, force: bool = False,
              max_depth: Optional[int] = inventory.DEFAULT_MAX_DEPTH) -> List[PlanItem]:
    """The full per-file plan for a project, in path order."""
    inv = inventory.build_inventory(root, max_depth)
    return [plan_for_file(root, entry, force) for entry in inv.claude_md]


def apply_plan(root: Path, items: Sequence[PlanItem], snapshot: bool = True) -> Optional[Path]:
    """Snapshot, then write every pending item. Returns the snapshot dir, if any."""
    pending = [i for i in items if i.action in WRITE_ACTIONS]
    if not pending:
        return None
    snap_dir: Optional[Path] = None
    if snapshot:
        modified = [i.path for i in pending if i.action != "create"]
        created = [i.path for i in pending if i.action == "create"]
        snap_dir = save_snapshot(root, modified, label="sync", created=created)
    for item in pending:
        if item.desired is None:
            raise ValueError(
                "internal error: {} planned as {} but carries no content; re-run "
                "sync_stubs.py".format(item.path, item.action)
            )
        target = root / item.path
        target.parent.mkdir(parents=True, exist_ok=True)
        inventory.write_text(target, item.desired)
    return snap_dir


def format_text(report: SyncReport) -> str:
    out: List[str] = ["root: {}".format(report.root)]
    mode = "check" if report.check else ("dry-run" if report.dry_run else "apply")
    out.append("mode: {}".format(mode))
    out.append("")
    for item in report.items:
        suffix = " — {}".format(item.reason) if item.reason else ""
        out.append("  {:<14} {} (was: {}){}".format(item.action, item.path, item.state, suffix))
    if not report.items:
        out.append("  (no AGENTS.md and no CLAUDE.md found)")
    out.append("")
    verb = "would change" if (report.check or report.dry_run) else "changed"
    out.append("{} {} file(s), skipped {}".format(verb, len(report.pending), len(report.skipped)))
    if report.snapshot_dir:
        out.append("snapshot: {}".format(report.snapshot_dir))
    return "\n".join(out)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sync_stubs.py",
        description="Regenerate the managed @AGENTS.md block in every CLAUDE.md stub.",
        epilog=("Exit codes:\n" + textwrap.dedent(__doc__.split("Exit codes:", 1)[1]).strip("\n"))
        if __doc__ and "Exit codes:" in __doc__ else None,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("root", nargs="?", default=None,
                        help="project root (default: git toplevel of cwd, else cwd)")
    parser.add_argument("--dry-run", action="store_true", help="print the plan, write nothing; exit 1 when writes are pending (same as --check)")
    parser.add_argument("--check", action="store_true",
                        help="write nothing; exit 1 if any write would happen")
    parser.add_argument("--force", action="store_true",
                        help="also stub a legacy CLAUDE.md (run migrate first)")
    parser.add_argument("--no-snapshot", action="store_true",
                        help="do not snapshot the files about to change")
    parser.add_argument("--max-depth", type=int, default=inventory.DEFAULT_MAX_DEPTH,
                        help="directory levels below root to scan (default: no limit)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(list(argv) if argv is not None else None)

    root = Path(args.root).expanduser() if args.root else inventory.default_root()
    if not root.is_dir():
        print("Project root not found: {}. Pass an existing directory as the first "
              "argument.".format(root), file=sys.stderr)
        return 2
    if args.max_depth is not None and args.max_depth < 1:
        print("--max-depth must be at least 1 (got {}).".format(args.max_depth), file=sys.stderr)
        return 2
    root = root.resolve()
    if args.force and args.no_snapshot and not (args.check or args.dry_run):
        print("--force replaces a legacy CLAUDE.md body, so it needs the snapshot as the "
              "recovery path. Drop --no-snapshot (or use --dry-run to preview).",
              file=sys.stderr)
        return 2

    items = plan_sync(root, force=args.force, max_depth=args.max_depth)
    report = SyncReport(root=str(root), dry_run=args.dry_run, check=args.check, items=items)

    if not (args.check or args.dry_run):
        try:
            snap_dir = apply_plan(root, items, snapshot=not args.no_snapshot)
        except (SnapshotError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 2
        except OSError as exc:
            print("Could not write the stubs under {}: {}. Check the file permissions "
                  "and re-run.".format(root, exc), file=sys.stderr)
            return 2
        report.snapshot_dir = str(snap_dir) if snap_dir else None

    if args.json:
        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(format_text(report))

    if args.check or args.dry_run:
        return 1 if (report.pending or report.skipped) else 0
    return 1 if report.skipped else 0


if __name__ == "__main__":
    sys.exit(main())
