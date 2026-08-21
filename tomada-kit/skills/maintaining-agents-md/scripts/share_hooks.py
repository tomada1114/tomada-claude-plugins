#!/usr/bin/env python3
"""share_hooks.py — Move hook scripts to .agents/hooks/ and wire both hosts to them.

Usage:
    share_hooks.py [<root>] [--dry-run] [--check] [--json]
                            [--no-snapshot] [--max-depth N]

<root> defaults to the git toplevel of the current directory, else the current
directory. The script is idempotent: a second run changes nothing.

Steps, each reported as an action:
    relocate          every file under .claude/hooks/ moves to .agents/hooks/,
                      keeping its relative layout (tracked files move with the
                      version-control command so history follows them)
    rewrite-wiring    every hook command in .claude/settings.json that resolves
                      its script through the project variable, a cwd-relative
                      path, or the retired directory is rewritten to
                      "$(git rev-parse --show-toplevel)/.agents/hooks/<script>"
    create-codex      .codex/hooks.json is generated from the shareable subset
    overwrite-codex   .codex/hooks.json existed and differed; it is generated
                      output, so it is replaced
    claude-only-event (info) an event only one host fires; its wiring stays in
                      .claude/settings.json
    adapt-script      (info) the script reads one host's payload fields only

Everything else in .claude/settings.json (permissions, env, ...) is preserved,
keys keep their order, and the personal settings file is never read or written.

Flags:
    --dry-run      print the plan, write nothing; exit 1 when work is pending
    --check        same, terse, for continuous integration
    --no-snapshot  refused when a move, a rewiring, or an overwrite is pending,
                   because the snapshot is the recovery path for those
    --max-depth    directory levels below .claude/hooks/ to relocate

Every file that is moved, rewritten, or overwritten is snapshotted first (see
snapshot.py); newly created files are recorded in the manifest as `created`.

Exit codes:
    0 = applied, or nothing left to do
    1 = work is pending (with --check/--dry-run)
    2 = bad invocation, nothing to share, invalid JSON, or a destination
        conflict that has to be resolved by hand
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import inventory  # noqa: E402
from snapshot import SnapshotError, save_snapshot  # noqa: E402

WRITE_KINDS = ("relocate", "rewrite-wiring", "create-codex", "overwrite-codex")
# Kinds that put a file back only from the snapshot, so --no-snapshot is refused.
DESTRUCTIVE_KINDS = ("relocate", "rewrite-wiring", "overwrite-codex")
# Caches are rebuilt by the interpreter; they never move with the scripts.
IGNORED_DIRS = ("__pycache__",)


class ShareError(Exception):
    """Bad input the caller has to fix (reported to stderr, exit 2)."""


@dataclass
class Action:
    kind: str
    path: str
    detail: str = ""

    def to_dict(self) -> Dict[str, str]:
        return {"kind": self.kind, "path": self.path, "detail": self.detail}


@dataclass
class Move:
    src: str
    dst: str
    duplicate: bool = False  # destination already holds the same bytes


@dataclass
class Plan:
    root: str
    state: str = "none"
    actions: List[Action] = field(default_factory=list)
    moves: List[Move] = field(default_factory=list)
    settings_text: Optional[str] = None
    codex_text: Optional[str] = None
    codex_existed: bool = False
    snapshot_dir: Optional[str] = None
    dry_run: bool = False
    check: bool = False

    @property
    def pending(self) -> List[Action]:
        return [a for a in self.actions if a.kind in WRITE_KINDS]

    @property
    def destructive(self) -> List[Action]:
        return [a for a in self.actions if a.kind in DESTRUCTIVE_KINDS]

    def to_dict(self) -> Dict[str, object]:
        return {
            "root": self.root,
            "state": self.state,
            "dry_run": self.dry_run,
            "check": self.check,
            "snapshot_dir": self.snapshot_dir,
            "pending": len(self.pending),
            "actions": [a.to_dict() for a in self.actions],
        }


# --- rewriting ---------------------------------------------------------------
# A hook command's script argument, with an optional quote and an optional root
# prefix around the retired directory. The lookbehind keeps the match off paths
# that only end in the same segments (a personal `~/.claude/hooks/...`).
LEGACY_COMMAND_RE = re.compile(
    r"(?<![^\s=(])(?P<q>[\"']?)"
    r"(?:\$\{CLAUDE_PROJECT_DIR\}/|\$CLAUDE_PROJECT_DIR/"
    r"|\$\(\s*git\s+rev-parse\s+--show-toplevel\s*\)/|\./)?"
    r"\.claude/hooks/(?P<rest>[^\"'\s]+)(?P=q)"
)


def rewrite_command(command: str) -> str:
    """Point one hook command at the shared directory through the portable root.

    Quotes are re-applied around the whole path, so a command that named the
    script bare comes out quoted and survives a project path with a space.
    """
    def replace(match) -> str:
        return '"{}/{}/{}"'.format(
            inventory.TOPLEVEL_EXPR, inventory.SHARED_HOOKS_REL, match.group("rest"))

    return LEGACY_COMMAND_RE.sub(replace, command)


def rewrite_hooks(hooks: Dict[str, object]) -> int:
    """Rewrite every command in a `hooks` mapping in place; return how many changed."""
    changed = 0
    for entries in hooks.values():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict) or not isinstance(entry.get("hooks"), list):
                continue
            for hook in entry["hooks"]:
                if not isinstance(hook, dict):
                    continue
                command = hook.get("command")
                if not isinstance(command, str):
                    continue
                rewritten = rewrite_command(command)
                if rewritten != command:
                    hook["command"] = rewritten
                    changed += 1
    return changed


# --- planning ----------------------------------------------------------------
def legacy_files(root: Path, max_depth: int) -> List[str]:
    """Files under the retired hook directory, relative to the project root."""
    legacy = root / inventory.LEGACY_HOOKS_REL
    if not legacy.is_dir():
        return []
    found: List[str] = []
    for current, dirnames, filenames in os.walk(legacy):
        rel_parts = Path(current).relative_to(legacy).parts
        if len(rel_parts) >= max_depth:
            dirnames[:] = []
            continue
        dirnames[:] = sorted(d for d in dirnames if d not in IGNORED_DIRS)
        for name in sorted(filenames):
            found.append(inventory.rel_of(root, Path(current) / name))
    return sorted(found)


def _read_json(root: Path, rel: str) -> Optional[Dict[str, object]]:
    path = root / rel
    if not path.is_file():
        return None
    data, error = inventory.load_json_object(path)
    if error:
        raise ShareError(
            "{} is not valid JSON ({}). Fix it by hand, then re-run "
            "share_hooks.py.".format(rel, error))
    return data


def build_plan(root: Path, max_depth: int = inventory.DEFAULT_MAX_DEPTH) -> Plan:
    """The whole plan for a project. Reads only; raises ShareError on bad input."""
    info, _ = inventory.analyze_hooks(root)
    plan = Plan(root=str(root), state=info.state)

    settings = _read_json(root, inventory.CLAUDE_SETTINGS_REL)
    claude_hooks = inventory.hooks_of(settings)
    moves_src = legacy_files(root, max_depth)

    if not claude_hooks and not (root / inventory.LEGACY_HOOKS_REL).is_dir():
        raise ShareError(
            "Nothing to share: {} has no hooks and there is no {}/ directory under {}. "
            "Wire the hooks on one host first, then re-run share_hooks.py.".format(
                inventory.CLAUDE_SETTINGS_REL, inventory.LEGACY_HOOKS_REL, root))

    # 1. relocate
    for src in moves_src:
        rel_inside = src[len(inventory.LEGACY_HOOKS_REL) + 1:]
        dst = "{}/{}".format(inventory.SHARED_HOOKS_REL, rel_inside)
        dst_path = root / dst
        if dst_path.exists():
            if dst_path.is_dir() or dst_path.read_bytes() != (root / src).read_bytes():
                raise ShareError(
                    "{} already exists and differs from {}. Merge the two by hand (or "
                    "delete the stale one), then re-run share_hooks.py.".format(dst, src))
            plan.moves.append(Move(src=src, dst=dst, duplicate=True))
            plan.actions.append(Action(
                "relocate", src, "{} already holds the same bytes; the retired copy is "
                "removed".format(dst)))
        else:
            plan.moves.append(Move(src=src, dst=dst))
            plan.actions.append(Action("relocate", src, "-> {}".format(dst)))

    # 2. rewrite-wiring
    if claude_hooks:
        changed = rewrite_hooks(claude_hooks)
        if changed:
            plan.settings_text = inventory.dump_json(settings)
            plan.actions.append(Action(
                "rewrite-wiring", inventory.CLAUDE_SETTINGS_REL,
                "{} command(s) rewritten to the {} form".format(
                    changed, inventory.TOPLEVEL_EXPR)))

    # 3. generate-codex, from the rewritten wiring
    generated = inventory.shareable_hooks(claude_hooks)
    codex_rel = inventory.CODEX_HOOKS_REL
    existing_codex = _read_json(root, codex_rel)
    plan.codex_existed = (root / codex_rel).is_file()
    if generated:
        desired = {"hooks": generated}
        if not plan.codex_existed:
            plan.codex_text = inventory.dump_json(desired)
            plan.actions.append(Action(
                "create-codex", codex_rel,
                "{} event(s) generated from {}".format(
                    len(generated), inventory.CLAUDE_SETTINGS_REL)))
        elif existing_codex != desired:
            plan.codex_text = inventory.dump_json(desired)
            plan.actions.append(Action(
                "overwrite-codex", codex_rel,
                "differs from the generated content; regenerated from {}".format(
                    inventory.CLAUDE_SETTINGS_REL)))
    elif plan.codex_existed:
        plan.actions.append(Action(
            "skip-codex", codex_rel,
            "{} wires no shareable event; {} is left untouched".format(
                inventory.CLAUDE_SETTINGS_REL, codex_rel)))

    # 4. what the other host never sees, and scripts that still read one shape
    for event in claude_hooks:
        if event not in inventory.SHAREABLE_HOOK_EVENTS:
            plan.actions.append(Action(
                "claude-only-event", inventory.CLAUDE_SETTINGS_REL,
                "{} fires on one host only; its wiring stays here".format(event)))

    for rel in _adaptation_candidates(root, plan.moves):
        plan.actions.append(Action(
            "adapt-script", rel,
            "reads one host's payload fields but never the other's patch format; "
            "adapt it with the hook_payload helper"))

    return plan


def _adaptation_candidates(root: Path, moves: Sequence[Move]) -> List[str]:
    """Shared-directory scripts that still look host-specific, after the moves."""
    sources: Dict[str, Path] = {}
    shared = root / inventory.SHARED_HOOKS_REL
    if shared.is_dir():
        for path in shared.rglob("*"):
            if path.is_file() and path.name.endswith(inventory.HOOK_SCRIPT_SUFFIXES):
                sources[inventory.rel_of(root, path)] = path
    for move in moves:
        if move.dst.endswith(inventory.HOOK_SCRIPT_SUFFIXES):
            sources[move.dst] = root / move.src
    out = []
    for rel in sorted(sources):
        try:
            text = inventory.read_text(sources[rel])
        except OSError:
            continue
        if inventory.host_specific_script(text):
            out.append(rel)
    return out


# --- applying ----------------------------------------------------------------
def _git_ok(root: Path, *args: str) -> bool:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root)] + list(args),
            capture_output=True, text=True, check=False,
        )
    except (OSError, ValueError):
        return False
    return proc.returncode == 0


def _relocate(root: Path, move: Move) -> None:
    src, dst = root / move.src, root / move.dst
    if move.duplicate:
        if _git_ok(root, "ls-files", "--error-unmatch", "--", move.src):
            if _git_ok(root, "rm", "-q", "-f", "--", move.src):
                return
        src.unlink()
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if _git_ok(root, "ls-files", "--error-unmatch", "--", move.src):
        if _git_ok(root, "mv", "--", move.src, move.dst):
            return
    os.replace(str(src), str(dst))


def _prune_legacy_dir(root: Path) -> bool:
    """Remove the retired hook directory once only rebuildable caches are left."""
    legacy = root / inventory.LEGACY_HOOKS_REL
    if not legacy.is_dir():
        return False
    for path in legacy.rglob("*"):
        parts = path.relative_to(legacy).parts
        if path.is_file() and not any(part in IGNORED_DIRS for part in parts):
            return False
    shutil.rmtree(str(legacy))
    return True


def apply_plan(root: Path, plan: Plan, snapshot: bool = True) -> Optional[Path]:
    """Snapshot, then carry out the plan. Returns the snapshot directory, if any."""
    if not plan.pending:
        return None
    snap_dir: Optional[Path] = None
    if snapshot:
        modified = [m.src for m in plan.moves]
        created = [m.dst for m in plan.moves if not m.duplicate]
        if plan.settings_text is not None:
            modified.append(inventory.CLAUDE_SETTINGS_REL)
        if plan.codex_text is not None:
            (modified if plan.codex_existed else created).append(inventory.CODEX_HOOKS_REL)
        snap_dir = save_snapshot(root, modified, label="hooks", created=created)

    for move in plan.moves:
        _relocate(root, move)
    if plan.moves:
        _prune_legacy_dir(root)

    if plan.settings_text is not None:
        inventory.write_text(root / inventory.CLAUDE_SETTINGS_REL, plan.settings_text)
    if plan.codex_text is not None:
        codex = root / inventory.CODEX_HOOKS_REL
        codex.parent.mkdir(parents=True, exist_ok=True)
        inventory.write_text(codex, plan.codex_text)
    return snap_dir


# --- output ------------------------------------------------------------------
def format_text(plan: Plan) -> str:
    mode = "check" if plan.check else ("dry-run" if plan.dry_run else "apply")
    if plan.check:
        out = ["root: {}".format(plan.root), "mode: check", "state: {}".format(plan.state)]
        for action in plan.pending:
            out.append("  {:<17} {}".format(action.kind, action.path))
        out.append("{} pending action(s)".format(len(plan.pending)))
        return "\n".join(out)

    out = ["root: {}".format(plan.root), "mode: {}".format(mode),
           "state: {}".format(plan.state), ""]
    for action in plan.actions:
        suffix = " — {}".format(action.detail) if action.detail else ""
        out.append("  {:<17} {}{}".format(action.kind, action.path, suffix))
    if not plan.actions:
        out.append("  (hooks are already shared)")
    out.append("")
    verb = "would change" if plan.dry_run else "changed"
    out.append("{} {} file(s)".format(verb, len(plan.pending)))
    if plan.snapshot_dir:
        out.append("snapshot: {}".format(plan.snapshot_dir))
    return "\n".join(out)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="share_hooks.py",
        description="Move hook scripts to the shared directory and wire both hosts to them.",
        epilog=("Exit codes:\n" + textwrap.dedent(__doc__.split("Exit codes:", 1)[1]).strip("\n"))
        if __doc__ and "Exit codes:" in __doc__ else None,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("root", nargs="?", default=None,
                        help="project root (default: git toplevel of cwd, else cwd)")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the plan, write nothing; exit 1 when work is pending")
    parser.add_argument("--check", action="store_true",
                        help="write nothing, terse output; exit 1 when work is pending")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--no-snapshot", action="store_true",
                        help="do not snapshot the files about to change")
    parser.add_argument("--max-depth", type=int, default=inventory.DEFAULT_MAX_DEPTH,
                        help="directory levels below the retired hook directory to "
                             "relocate (default: %(default)s)")
    args = parser.parse_args(list(argv) if argv is not None else None)

    root = Path(args.root).expanduser() if args.root else inventory.default_root()
    if not root.is_dir():
        print("Project root not found: {}. Pass an existing directory as the first "
              "argument.".format(root), file=sys.stderr)
        return 2
    if args.max_depth < 1:
        print("--max-depth must be at least 1 (got {}).".format(args.max_depth), file=sys.stderr)
        return 2
    root = root.resolve()

    preview = args.check or args.dry_run
    try:
        plan = build_plan(root, args.max_depth)
    except ShareError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    plan.dry_run = args.dry_run
    plan.check = args.check

    if not preview:
        if args.no_snapshot and plan.destructive:
            print("share_hooks.py moves, rewrites, or replaces {} file(s), so it needs the "
                  "snapshot as the recovery path. Drop --no-snapshot (or use --dry-run to "
                  "preview).".format(len(plan.destructive)), file=sys.stderr)
            return 2
        try:
            snap_dir = apply_plan(root, plan, snapshot=not args.no_snapshot)
        except SnapshotError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        except OSError as exc:
            print("Could not share the hooks under {}: {}. Check the file permissions "
                  "and re-run.".format(root, exc), file=sys.stderr)
            return 2
        plan.snapshot_dir = str(snap_dir) if snap_dir else None

    if args.json:
        print(json.dumps(plan.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(format_text(plan))

    if preview:
        return 1 if plan.pending else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
