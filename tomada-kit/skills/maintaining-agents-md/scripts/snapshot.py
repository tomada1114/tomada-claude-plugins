#!/usr/bin/env python3
"""snapshot.py — Copy rule files aside before editing them, and put them back.

Usage:
    snapshot.py save <root> <file>... [--label X] [--created <file>...] [--json]
    snapshot.py list <root> [--json]
    snapshot.py restore <root> <snapshot-id> [--dry-run] [--force]
                                            [--delete-created] [--json]

<file> paths may be absolute or relative to <root>; they must live inside <root>.
A file that does not exist yet is recorded as `absent`, or as `created` when it
is named in --created (i.e. the caller is about to create it), so that restore
can offer to delete it again.

Snapshots live outside the project, under
    ${AGENT_SKILL_STATE_DIR:-$HOME/.local/state/agent-skills}
      /maintaining-agents-md/<basename>__<sha1-8 of abs root>/snapshots/<id>/
where <id> is a UTC timestamp (YYYYMMDDTHHMMSSZ) plus -<label> when given.
Each snapshot holds the files at their original relative paths plus manifest.json.

restore refuses a file that is both modified in git and different from the
snapshot, unless --force; it never deletes anything unless --delete-created.

Exit codes:
    0 = done
    1 = nothing restored / a file was refused
    2 = bad invocation (path outside the root, unknown snapshot id, ...)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence

SKILL_STATE_NAME = "maintaining-agents-md"
# Collisions only happen when two snapshots are taken inside the same second,
# so a handful of suffixes is plenty before something is badly wrong.
MAX_ID_SUFFIX = 50


class SnapshotError(Exception):
    """Bad input that the caller has to fix (reported to stderr, exit 2)."""


def state_dir() -> Path:
    """Root of the shared agent-skill state directory (env override honoured)."""
    env = os.environ.get("AGENT_SKILL_STATE_DIR")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".local" / "state" / "agent-skills"


def repo_slug(root: Path) -> str:
    """<basename>__<first 8 hex of sha1(absolute root)> — stable, collision-safe."""
    abs_root = str(Path(root).expanduser().resolve())
    digest = hashlib.sha1(abs_root.encode("utf-8")).hexdigest()[:8]
    name = Path(abs_root).name or "root"
    return "{}__{}".format(name, digest)


def snapshots_dir(root: Path) -> Path:
    return state_dir() / SKILL_STATE_NAME / repo_slug(root) / "snapshots"


def sha1_of(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def _sanitize_label(label: str) -> str:
    keep = [c if (c.isalnum() or c in "._-") else "-" for c in label.strip()]
    return "".join(keep).strip("-") or "label"


def new_snapshot_id(base_dir: Path, label: Optional[str] = None, now: Optional[datetime] = None) -> str:
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    if label:
        stamp = "{}-{}".format(stamp, _sanitize_label(label))
    candidate = stamp
    for n in range(2, MAX_ID_SUFFIX + 2):
        if not (base_dir / candidate).exists():
            return candidate
        candidate = "{}-{}".format(stamp, n)
    raise SnapshotError(
        "Could not allocate a snapshot id under {}: {} variants of {} already exist. "
        "Remove old snapshots or pass a different --label.".format(base_dir, MAX_ID_SUFFIX, stamp)
    )


def relative_to_root(root: Path, target: Path) -> str:
    """POSIX path of `target` inside `root`; raises when it escapes the root."""
    root = root.resolve()
    candidate = target if target.is_absolute() else root / target
    # resolve() only where the file exists; otherwise resolve the parent so a
    # not-yet-created file still normalizes correctly.
    if candidate.exists():
        resolved = candidate.resolve()
    else:
        resolved = candidate.parent.resolve() / candidate.name
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError:
        raise SnapshotError(
            "{} is outside the project root {}. Snapshot only files inside the "
            "project.".format(resolved, root)
        )


@dataclass
class FileRecord:
    rel: str
    status: str  # copied | created | absent
    sha1: Optional[str] = None


@dataclass
class Manifest:
    root: str
    created_at: str
    label: str
    files: List[FileRecord] = field(default_factory=list)


def save_snapshot(
    root: Path,
    files: Sequence[object],
    label: Optional[str] = None,
    created: Sequence[object] = (),
) -> Path:
    """Copy `files` into a fresh snapshot directory and return that directory.

    `created` names files the caller is about to create; they are recorded with
    status "created" so restore knows they did not exist before. Files that are
    missing and not listed in `created` are recorded as "absent".
    """
    root = Path(root).expanduser().resolve()
    if not root.is_dir():
        raise SnapshotError("Project root not found: {}.".format(root))

    created_rels = {relative_to_root(root, Path(str(f))) for f in created}
    rels: List[str] = []
    for f in list(files) + list(created):
        rel = relative_to_root(root, Path(str(f)))
        if rel not in rels:
            rels.append(rel)

    base = snapshots_dir(root)
    base.mkdir(parents=True, exist_ok=True)
    snap_id = new_snapshot_id(base, label)
    snap_dir = base / snap_id
    snap_dir.mkdir(parents=True)

    records: List[FileRecord] = []
    for rel in rels:
        src = root / rel
        if src.is_file():
            dest = snap_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src), str(dest))
            records.append(FileRecord(rel=rel, status="copied", sha1=sha1_of(src)))
        else:
            records.append(
                FileRecord(rel=rel, status="created" if rel in created_rels else "absent")
            )

    manifest = Manifest(
        root=str(root),
        created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        label=label or "",
        files=records,
    )
    (snap_dir / "manifest.json").write_text(
        json.dumps(asdict(manifest), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return snap_dir


def load_manifest(snap_dir: Path) -> Manifest:
    path = snap_dir / "manifest.json"
    if not path.is_file():
        raise SnapshotError(
            "{} has no manifest.json; it is not a snapshot directory.".format(snap_dir)
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    return Manifest(
        root=data.get("root", ""),
        created_at=data.get("created_at", ""),
        label=data.get("label", ""),
        files=[FileRecord(**f) for f in data.get("files", [])],
    )


def list_snapshots(root: Path) -> List[Dict[str, object]]:
    """Newest last, matching the sortable timestamp ids."""
    base = snapshots_dir(root)
    if not base.is_dir():
        return []
    out: List[Dict[str, object]] = []
    for d in sorted(p for p in base.iterdir() if p.is_dir()):
        try:
            manifest = load_manifest(d)
        except (SnapshotError, ValueError):
            continue
        out.append({
            "id": d.name,
            "path": str(d),
            "created_at": manifest.created_at,
            "label": manifest.label,
            "files": [r.rel for r in manifest.files],
        })
    return out


def git_is_dirty(root: Path, rel: str) -> bool:
    """True when git reports the path modified/untracked. False when git is absent."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--", rel],
            capture_output=True, text=True, check=False,
        )
    except (OSError, ValueError):
        return False
    if proc.returncode != 0:
        return False
    return bool(proc.stdout.strip())


@dataclass
class RestoreAction:
    rel: str
    action: str  # restore | delete | kept | refused | skip
    reason: str = ""


def plan_restore(
    root: Path,
    manifest: Manifest,
    snap_dir: Path,
    force: bool = False,
    delete_created: bool = False,
) -> List[RestoreAction]:
    """Decide, without touching anything, what restore would do per file."""
    actions: List[RestoreAction] = []
    for record in manifest.files:
        target = root / record.rel
        if record.status == "copied":
            saved = snap_dir / record.rel
            if not saved.is_file():
                actions.append(RestoreAction(record.rel, "skip", "missing from the snapshot"))
                continue
            if target.is_file() and target.read_bytes() == saved.read_bytes():
                actions.append(RestoreAction(record.rel, "kept", "already identical"))
                continue
            if not force and target.is_file() and git_is_dirty(root, record.rel):
                actions.append(RestoreAction(
                    record.rel, "refused",
                    "modified in git and different from the snapshot; commit or stash it, "
                    "or re-run with --force"))
                continue
            actions.append(RestoreAction(record.rel, "restore", ""))
        elif record.status == "created":
            if not target.exists():
                actions.append(RestoreAction(record.rel, "skip", "already gone"))
            elif delete_created:
                actions.append(RestoreAction(record.rel, "delete", "created by the run"))
            else:
                actions.append(RestoreAction(
                    record.rel, "kept",
                    "created by the run; pass --delete-created to remove it"))
        else:  # absent
            actions.append(RestoreAction(record.rel, "skip", "did not exist when saved"))
    return actions


def apply_restore(root: Path, snap_dir: Path, actions: Sequence[RestoreAction]) -> None:
    for action in actions:
        target = root / action.rel
        if action.action == "restore":
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(snap_dir / action.rel), str(target))
        elif action.action == "delete":
            target.unlink()


def _resolve_root(raw: str) -> Path:
    root = Path(raw).expanduser()
    if not root.is_dir():
        raise SnapshotError(
            "Project root not found: {}. Pass an existing directory.".format(root)
        )
    return root.resolve()


def _cmd_save(args: argparse.Namespace) -> int:
    root = _resolve_root(args.root)
    snap_dir = save_snapshot(root, args.files, label=args.label, created=args.created)
    manifest = load_manifest(snap_dir)
    if args.json:
        print(json.dumps(
            {"snapshot_dir": str(snap_dir), "id": snap_dir.name, "manifest": asdict(manifest)},
            indent=2, ensure_ascii=False))
    else:
        print("saved snapshot {}".format(snap_dir.name))
        print("  dir: {}".format(snap_dir))
        for record in manifest.files:
            print("  {} — {}".format(record.rel, record.status))
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    root = _resolve_root(args.root)
    snaps = list_snapshots(root)
    if args.json:
        print(json.dumps({"root": str(root), "snapshots": snaps}, indent=2, ensure_ascii=False))
    elif not snaps:
        print("no snapshots for {} (looked in {})".format(root, snapshots_dir(root)))
    else:
        for snap in snaps:
            print("{}  {}  {} file(s){}".format(
                snap["id"], snap["created_at"], len(snap["files"]),
                "  label={}".format(snap["label"]) if snap["label"] else ""))
    return 0


def _cmd_restore(args: argparse.Namespace) -> int:
    root = _resolve_root(args.root)
    snap_dir = snapshots_dir(root) / args.snapshot_id
    if not snap_dir.is_dir():
        known = [s["id"] for s in list_snapshots(root)]
        raise SnapshotError(
            "Unknown snapshot id {!r} for {}. Known ids: {}".format(
                args.snapshot_id, root, ", ".join(known) if known else "(none)")
        )
    manifest = load_manifest(snap_dir)
    actions = plan_restore(root, manifest, snap_dir, force=args.force,
                           delete_created=args.delete_created)
    if not args.dry_run:
        apply_restore(root, snap_dir, actions)

    payload = {
        "root": str(root),
        "snapshot_dir": str(snap_dir),
        "dry_run": args.dry_run,
        "actions": [asdict(a) for a in actions],
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        head = "restore plan" if args.dry_run else "restored"
        print("{} from {}".format(head, snap_dir))
        for action in actions:
            suffix = " ({})".format(action.reason) if action.reason else ""
            print("  {} — {}{}".format(action.rel, action.action, suffix))
    return 1 if any(a.action == "refused" for a in actions) else 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="snapshot.py",
        description="Save and restore copies of rule files before editing them.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_save = sub.add_parser("save", help="copy files into a new snapshot")
    p_save.add_argument("root")
    p_save.add_argument("files", nargs="+")
    p_save.add_argument("--label", default=None, help="suffix for the snapshot id")
    p_save.add_argument("--created", nargs="*", default=[],
                        help="files the caller is about to create (recorded, not copied)")
    p_save.add_argument("--json", action="store_true")
    p_save.set_defaults(func=_cmd_save)

    p_list = sub.add_parser("list", help="list snapshots for a project")
    p_list.add_argument("root")
    p_list.add_argument("--json", action="store_true")
    p_list.set_defaults(func=_cmd_list)

    p_restore = sub.add_parser("restore", help="copy a snapshot's files back")
    p_restore.add_argument("root")
    p_restore.add_argument("snapshot_id")
    p_restore.add_argument("--dry-run", action="store_true")
    p_restore.add_argument("--force", action="store_true",
                           help="restore even over a file modified in git")
    p_restore.add_argument("--delete-created", action="store_true",
                           help="delete files the snapshot recorded as created")
    p_restore.add_argument("--json", action="store_true")
    p_restore.set_defaults(func=_cmd_restore)

    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        return args.func(args)
    except SnapshotError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
