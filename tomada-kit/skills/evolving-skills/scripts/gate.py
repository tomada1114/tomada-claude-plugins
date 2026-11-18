#!/usr/bin/env python3
"""gate.py — the mechanical gate that decides whether an automatic skill edit lands.

Edits are made in a staging copy. The gate compares the staging copy (head/)
against the committed version (base/): file diff, path guard, size budget,
validators, and a behavioral eval before and after. Only a passing change is
copied into the real tree and committed, so a failing change never touches
the real files.

Usage:
    gate.py stage  --root <git-root> [--path <rel> ...] [--new-path <rel> ...] [--state-dir D]
    gate.py check  --run RUN [--tags gate ...] [--final] [--runs 3]
                   [--max-cost-usd 5] [--skip-eval] [--validators-dir DIR]
                   [--claude-bin claude] [--protect GLOB ...] [--leak-chars 32]
                   [--timeout-seconds 1800]
    gate.py land   --run RUN --message-file F [--allow-unmeasured]
    gate.py revert --root ROOT --commit SHA

Subcommands:
    stage   Copy the tracked files of the given paths into a new run directory
            <state>/runs/<UTC stamp>-<hex>/ as base/ and head/, refusing when
            those paths have uncommitted changes. --new-path names a path that
            does not exist yet (head/ gets an empty directory, base/ nothing).
            Edit files under head/ only.
    check   Verify base/ against git (exit 3 `base-tampered` on mismatch), then
            run diff -> guard -> validators -> eval, stop at the first step that
            does not pass, write RUN/verdict.json and print it.
    land    Copy a passing head/ into the repository and commit only the changed
            files. Refuses unless the verdict, digest and repository still match.
    revert  `git revert` a landed commit, refusing when its files are dirty.

State directory:
    $AGENT_SKILL_STATE_DIR (default ~/.local/state/agent-skills) / evolving-skills,
    overridable per command with --state-dir.

Exit codes:
    0 = pass (check) / success (stage, land, revert)
    1 = check verdict fail
    2 = check verdict blocked (guard violation)
    3 = bad invocation, missing run, or a refused precondition
    4 = check verdict unmeasured or inconclusive
    5 = git commit / revert failed after the change was applied
"""
from __future__ import annotations

import argparse
import difflib
import fnmatch
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------- constants

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_BLOCKED = 2
EXIT_USAGE = 3
EXIT_UNMEASURED = 4
EXIT_GIT = 5

VERDICT_EXIT = {
    "pass": EXIT_PASS,
    "fail": EXIT_FAIL,
    "blocked": EXIT_BLOCKED,
    "unmeasured": EXIT_UNMEASURED,
    "inconclusive": EXIT_UNMEASURED,
}

PROTECTED_SEGMENTS = ("evals", "hooks")
PROTECTED_SUBDIR = ("scripts", "tests")
PROTECTED_NAME_GLOBS = (
    "test_*.py",
    "validate*.py",
    "audit*.py",
    "check*.py",
    "guard*.py",
    "gate.py",
    "*lint*",
    "lint-config*",
    "*.calibration.json",
)

SKILL_BODY_BUDGET = 150
REFERENCE_LINES_BUDGET = 400

# Directories never compared, digested, or landed (bytecode from running tests).
IGNORED_DIR_NAMES = ("__pycache__",)
EVAL_IGNORED_DIRS = ("results", "calibration")

# Eval pass rules.
RULE_R1 = "R1"  # mean score of existing cases on head >= mean on base
RULE_R2 = "R2"  # no existing case drops by more than R2_MAX_DROP
RULE_R3 = "R3"  # every new case improves and reaches PASS_SCORE on head
RULE_R4 = "R4"  # (--final only) holdout-tagged mean on head >= on base
RULE_NEW_SKILL = "new-skill"  # brand-new skill: every case >= PASS_SCORE on head
R2_MAX_DROP = 0.34
PASS_SCORE = 0.66  # two passing runs out of three (0.667) must pass
GATE_TAG = "gate"
RULE_NEW_CASE_UNTAGGED = "new-case-untagged"
HOLDOUT_TAG = "holdout"
MAX_RETAKES = 1

DEFAULT_STATE_ROOT = "~/.local/state/agent-skills"
SKILL_NAME = "evolving-skills"

TOP_LEVEL_KEY_RE = re.compile(r"^[A-Za-z_][\w.-]*\s*:")
LOCATION_LINE_RE = re.compile(r"(?::\d+)+$")
SELF_CHECK_RE = re.compile(r"^## Self-check\b", re.IGNORECASE)


class UsageError(Exception):
    """Bad invocation or refused precondition (exit 3)."""


class GateArgumentParser(argparse.ArgumentParser):
    def error(self, message: str):  # type: ignore[override]
        raise UsageError(message)


# ---------------------------------------------------------------- helpers


def run_cmd(argv: List[str], cwd=None, timeout=None) -> subprocess.CompletedProcess:
    """Single choke point for every external process (patched in tests)."""
    return subprocess.run(
        argv, cwd=None if cwd is None else str(cwd), timeout=timeout, capture_output=True, text=True
    )


def default_state_dir() -> Path:
    return Path(os.environ.get("AGENT_SKILL_STATE_DIR", DEFAULT_STATE_ROOT)).expanduser() / SKILL_NAME


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def emit(obj) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def git(args: List[str], cwd: Path, timeout=None) -> subprocess.CompletedProcess:
    return run_cmd(["git"] + args, cwd=cwd, timeout=timeout)


def git_ok(args: List[str], cwd: Path) -> str:
    proc = git(args, cwd)
    if proc.returncode != 0:
        raise UsageError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def iter_files(top: Path) -> Dict[str, Path]:
    """Map repo-relative posix path -> file for every file under top."""
    out: Dict[str, Path] = {}
    if not top.is_dir():
        return out
    for dirpath, dirnames, filenames in os.walk(top):
        dirnames[:] = sorted(d for d in dirnames if d not in IGNORED_DIR_NAMES)
        for name in filenames:
            p = Path(dirpath) / name
            out[p.relative_to(top).as_posix()] = p
    return out


def head_digest(head: Path) -> str:
    h = hashlib.sha256()
    for rel, path in sorted(iter_files(head).items()):
        data = path.read_bytes()
        h.update(rel.encode("utf-8") + b"\0")
        h.update(str(len(data)).encode("ascii") + b"\0")
        h.update(data)
    return h.hexdigest()


def read_text(path: Path) -> Optional[str]:
    try:
        return path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def split_frontmatter(text: str) -> Tuple[List[str], List[str]]:
    """Return (frontmatter lines without the fences, body lines)."""
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return lines[1:i], lines[i + 1:]
    return [], lines


def frontmatter_value(fm: List[str], key: str) -> Optional[str]:
    for line in fm:
        m = re.match(rf"^{re.escape(key)}\s*:\s*(.*)$", line)
        if m:
            return m.group(1).strip().strip("'\"")
    return None


def parse_tags(lines: List[str]) -> List[str]:
    """Top-level `tags:` as an inline [a, b] list or a block `- a` list."""
    for i, line in enumerate(lines):
        m = re.match(r"^tags\s*:\s*(.*)$", line)
        if not m:
            continue
        rest = m.group(1).strip()
        if rest.startswith("["):
            inner = rest.strip("[]")
            return [t.strip().strip("'\"") for t in inner.split(",") if t.strip()]
        if rest:
            return [rest.strip("'\"")]
        tags = []
        for nxt in lines[i + 1:]:
            mm = re.match(r"^\s*-\s*(.+?)\s*$", nxt)
            if mm:
                tags.append(mm.group(1).strip("'\""))
            elif nxt.strip() == "":
                continue
            else:
                break
        return tags
    return []


def hooks_block(fm: List[str]) -> Optional[List[str]]:
    for i, line in enumerate(fm):
        if line.startswith("hooks:"):
            block = [line]
            for nxt in fm[i + 1:]:
                if TOP_LEVEL_KEY_RE.match(nxt):
                    break
                block.append(nxt)
            return block
    return None


def self_check_section(lines: List[str]) -> Optional[List[str]]:
    """The `## Self-check` section (heading included) up to the next `## ` heading."""
    for i, line in enumerate(lines):
        if SELF_CHECK_RE.match(line):
            block = [line]
            for nxt in lines[i + 1:]:
                if nxt.startswith("## "):
                    break
                block.append(nxt)
            return block
    return None


def pure_additions(old: List[str], new: List[str]) -> bool:
    sm = difflib.SequenceMatcher(None, old, new, autojunk=False)
    return all(tag in ("equal", "insert") for tag, *_ in sm.get_opcodes())


def added_lines(old: List[str], new: List[str]) -> List[Tuple[int, str]]:
    """(1-based line number in new, text) for lines present in new but not old."""
    out = []
    sm = difflib.SequenceMatcher(None, old, new, autojunk=False)
    for tag, _i1, _i2, j1, j2 in sm.get_opcodes():
        if tag in ("insert", "replace"):
            for j in range(j1, j2):
                out.append((j + 1, new[j]))
    return out


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def is_protected(rel: str, extra_globs: List[str]) -> bool:
    parts = rel.split("/")
    if any(p in PROTECTED_SEGMENTS for p in parts):
        return True
    for i in range(len(parts) - 2):
        if (parts[i], parts[i + 1]) == PROTECTED_SUBDIR:
            return True
    name = parts[-1]
    if any(fnmatch.fnmatchcase(name, g) for g in PROTECTED_NAME_GLOBS):
        return True
    return any(fnmatch.fnmatchcase(rel, g) for g in extra_globs)


def load_run(run_arg: str) -> Tuple[Path, dict]:
    run = Path(run_arg).expanduser().resolve()
    meta_path = run / "run.json"
    if not meta_path.is_file() or not (run / "head").is_dir() or not (run / "base").is_dir():
        raise UsageError(f"not a gate run directory: {run}")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta.setdefault("new_paths", [])
    return run, meta


def all_paths(meta: dict) -> List[str]:
    return list(meta["paths"]) + list(meta.get("new_paths") or [])


def git_blob_id(data: bytes, hexlen: int) -> str:
    """Object id git gives these bytes as a blob (sha1, or sha256 repositories)."""
    algo = hashlib.sha256 if hexlen == 64 else hashlib.sha1
    return algo(b"blob %d\0" % len(data) + data).hexdigest()


def base_mismatches(run: Path, meta: dict) -> List[str]:
    """Files under base/ that differ from the tracked files at base_commit.

    The judged agent can write to the run directory, and every comparison rests
    on base/, so base/ is re-derived from git rather than trusted.
    """
    expected: Dict[str, str] = {}
    if meta["paths"]:
        proc = git(["ls-tree", "-r", "-z", meta["base_commit"], "--"] + list(meta["paths"]), Path(meta["root"]))
        if proc.returncode != 0:
            return [f"git ls-tree {meta['base_commit']} failed: {proc.stderr.strip()}"]
        for entry in proc.stdout.split("\0"):
            if not entry:
                continue
            info, path = entry.split("\t", 1)
            _mode, kind, oid = info.split()
            if kind == "blob" and not any(p in IGNORED_DIR_NAMES for p in path.split("/")):
                expected[path] = oid
    actual = iter_files(run / "base")
    bad = set(expected) ^ set(actual)
    for rel in set(expected) & set(actual):
        p = actual[rel]
        data = os.readlink(p).encode("utf-8") if p.is_symlink() else p.read_bytes()
        if git_blob_id(data, len(expected[rel])) != expected[rel]:
            bad.add(rel)
    return sorted(bad)


def compute_diff(run: Path) -> Dict[str, List[str]]:
    base = iter_files(run / "base")
    head = iter_files(run / "head")
    added = sorted(set(head) - set(base))
    removed = sorted(set(base) - set(head))
    modified = sorted(r for r in set(base) & set(head) if base[r].read_bytes() != head[r].read_bytes())
    return {"added": added, "removed": removed, "modified": modified}


# ---------------------------------------------------------------- stage


def validate_rel(root: Path, rel: str) -> str:
    if Path(rel).is_absolute() or ".." in Path(rel).parts:
        raise UsageError(f"--path must be relative to root without '..': {rel}")
    target = (root / rel).resolve()
    if target != root and root not in target.parents:
        raise UsageError(f"--path is outside root: {rel}")
    if not target.exists():
        raise UsageError(f"--path does not exist: {rel}")
    rel_posix = target.relative_to(root).as_posix()
    return rel_posix if rel_posix else "."


def validate_new_rel(root: Path, rel: str) -> str:
    if Path(rel).is_absolute() or ".." in Path(rel).parts:
        raise UsageError(f"--new-path must be relative to root without '..': {rel}")
    rel_posix = Path(os.path.normpath(rel)).as_posix()
    if rel_posix in ("", "."):
        raise UsageError(f"--new-path must name a path below root: {rel}")
    target = root / rel_posix
    parent = target.parent.resolve()
    if parent != root and root not in parent.parents:
        raise UsageError(f"--new-path is outside root: {rel}")
    if os.path.lexists(target):
        raise UsageError(f"--new-path already exists: {rel}")
    return rel_posix


def cmd_stage(args) -> int:
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        raise UsageError(f"--root is not a directory: {root}")
    top = git_ok(["rev-parse", "--show-toplevel"], root).strip()
    if Path(top).resolve() != root:
        raise UsageError(f"--root must be the work tree top level ({top})")
    paths = [validate_rel(root, p) for p in (args.path or [])]
    new_paths = [validate_new_rel(root, p) for p in (args.new_path or [])]
    if not paths and not new_paths:
        raise UsageError("give at least one --path or --new-path")
    for np in new_paths:
        if git_ok(["ls-files", "--", np], root).strip():
            raise UsageError(f"--new-path is tracked in git: {np}")
    files: List[str] = []
    if paths:
        dirty = git_ok(["status", "--porcelain", "--"] + paths, root)
        if dirty.strip():
            sys.stderr.write("refusing: uncommitted changes under the staged paths:\n" + dirty)
            return EXIT_USAGE
        files = [f for f in git_ok(["ls-files", "-z", "--"] + paths, root).split("\0") if f]
    base_commit = git_ok(["rev-parse", "HEAD"], root).strip()

    state = Path(args.state_dir).expanduser() if args.state_dir else default_state_dir()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = state / "runs" / f"{stamp}-{secrets.token_hex(2)}"
    for side in ("base", "head"):
        (run / side).mkdir(parents=True)
        for rel in files:
            src = root / rel
            dst = run / side / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst, follow_symlinks=False)
    for np in new_paths:
        (run / "head" / np).mkdir(parents=True, exist_ok=True)
    meta = {
        "root": str(root),
        "paths": paths,
        "new_paths": new_paths,
        "base_commit": base_commit,
        "created": now_iso(),
    }
    (run / "run.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    emit({"run": str(run), "head": str(run / "head"), "base": str(run / "base")})
    return EXIT_PASS


# ---------------------------------------------------------------- guard


def under_paths(rel: str, paths: List[str]) -> bool:
    return any(p == "." or rel == p or rel.startswith(p + "/") for p in paths)


def guard(run: Path, diff: Dict[str, List[str]], protect: List[str], leak_chars: int,
          paths: Optional[List[str]] = None) -> List[dict]:
    base, head = run / "base", run / "head"
    violations: List[dict] = []
    changed = diff["added"] + diff["modified"]

    # Only the staged paths may change; land would otherwise commit anything under head/.
    if paths is not None:
        for rel in sorted(changed + diff["removed"]):
            if not under_paths(rel, paths):
                violations.append({"kind": "outside-staged-paths", "file": rel})

    # Protected files.
    for rel in diff["removed"]:
        if is_protected(rel, protect):
            violations.append({"kind": "protected-removed", "file": rel})
    for rel in diff["modified"]:
        if not is_protected(rel, protect):
            continue
        old, new = read_text(base / rel), read_text(head / rel)
        if old is None or new is None or not pure_additions(old.splitlines(), new.splitlines()):
            violations.append({"kind": "protected-modified", "file": rel})

    # Frontmatter hooks and size budget.
    for rel in changed:
        name = rel.split("/")[-1]
        new_text = read_text(head / rel)
        old_text = read_text(base / rel) if rel in diff["modified"] else None
        if new_text is None:
            continue
        if name == "SKILL.md":
            new_fm, new_body = split_frontmatter(new_text)
            old_fm, old_body = split_frontmatter(old_text) if old_text is not None else ([], [])
            old_hooks = hooks_block(old_fm)
            if old_hooks is not None:
                new_hooks = hooks_block(new_fm) or []
                if not pure_additions(old_hooks, new_hooks):
                    violations.append(
                        {"kind": "protected-modified", "file": rel, "detail": "frontmatter hooks"}
                    )
            # The self-check section holds the skill's acceptance criteria: append-only.
            old_check = self_check_section(old_text.splitlines()) if old_text is not None else None
            if old_check is not None:
                new_check = self_check_section(new_text.splitlines()) or []
                if not pure_additions(old_check, new_check):
                    violations.append(
                        {"kind": "protected-modified", "file": rel, "detail": "self-check section"}
                    )
            limit = max(SKILL_BODY_BUDGET, len(old_body)) if old_text is not None else SKILL_BODY_BUDGET
            if len(new_body) > limit:
                violations.append(
                    {
                        "kind": "budget",
                        "file": rel,
                        "detail": f"SKILL.md body {len(new_body)} lines > limit {limit}"
                        f" (base {len(old_body) if old_text is not None else 'none'})",
                    }
                )
        elif name.endswith(".md") and "references" in rel.split("/"):
            new_n = len(new_text.splitlines())
            old_n = len(old_text.splitlines()) if old_text is not None else 0
            limit = max(REFERENCE_LINES_BUDGET, old_n)
            if new_n > limit:
                violations.append(
                    {
                        "kind": "budget",
                        "file": rel,
                        "detail": f"reference {new_n} lines > limit {limit} (base {old_n})",
                    }
                )

    # Leak of eval prompt wording into the edit.
    windows = set()
    for rel, path in iter_files(head).items():
        if path.name == "prompt.md" and "evals" in rel.split("/")[:-1]:
            text = read_text(path)
            if text is None:
                continue
            body = normalize("\n".join(split_frontmatter(text)[1]))
            for i in range(len(body) - leak_chars + 1):
                windows.add(body[i:i + leak_chars])
    if windows:
        for rel in changed:
            if is_protected(rel, protect):
                continue
            new_text = read_text(head / rel)
            if new_text is None:
                continue
            old_text = read_text(base / rel) if rel in diff["modified"] else ""
            for lineno, line in added_lines((old_text or "").splitlines(), new_text.splitlines()):
                norm = normalize(line)
                for i in range(len(norm) - leak_chars + 1):
                    if norm[i:i + leak_chars] in windows:
                        violations.append(
                            {"kind": "leak", "file": rel, "line": lineno, "text": norm[i:i + leak_chars]}
                        )
                        break
    return violations


# ---------------------------------------------------------------- validators


def staged_skill_dirs(run: Path, paths: List[str]) -> List[str]:
    return [p for p in paths if (run / "head" / p / "SKILL.md").is_file()]


def _findings_from(payload) -> List[dict]:
    if not isinstance(payload, dict):
        raise ValueError("validator output is not a JSON object")
    if "validate" in payload or "audit" in payload:
        found = list((payload.get("validate") or {}).get("findings") or [])
        found += list(payload.get("audit") or [])
        return found
    return list(payload.get("findings") or [])


def _norm_location(loc: str, skill_dirs: List[Path]) -> str:
    loc = loc or ""
    for d in skill_dirs:
        for prefix in (str(d), str(d.resolve())):
            if loc.startswith(prefix + os.sep):
                loc = loc[len(prefix) + 1:]
    return LOCATION_LINE_RE.sub("", loc)


def run_validator(script: Path, target: Path, timeout: int) -> Tuple[Optional[List[dict]], str]:
    """Return (findings, error). Exit 0/1 with JSON are both normal results."""
    try:
        proc = run_cmd(["python3", str(script), str(target), "--json"], timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, f"{script.name}: {e}"
    if proc.returncode not in (0, 1):
        return None, f"{script.name} exited {proc.returncode}: {proc.stderr.strip()[:500]}"
    try:
        return _findings_from(json.loads(proc.stdout)), ""
    except ValueError as e:
        return None, f"{script.name} output unparsable: {e}"


def step_validators(run: Path, meta: dict, diff: Dict[str, List[str]], vdir: Path, timeout: int) -> dict:
    skills = staged_skill_dirs(run, all_paths(meta))
    result: dict = {"status": "pass", "skills": {}}
    if not skills:
        result["note"] = "no staged skill directory"
        return result
    scripts = {n: vdir / f"{n}.py" for n in ("validate_skill", "audit_skill", "check_scripts")}
    missing = [str(p) for p in scripts.values() if not p.is_file()]
    if missing:
        return {"status": "unavailable", "missing": missing}
    changed = diff["added"] + diff["modified"] + diff["removed"]
    failed = False
    for rel in skills:
        head_dir = run / "head" / rel
        base_dir = run / "base" / rel
        has_base = (base_dir / "SKILL.md").is_file()
        dirs = [head_dir, base_dir]
        info: dict = {"has_base": has_base}
        err_counts = {"base": Counter(), "head": Counter()}
        warn_counts = {"base": 0, "head": 0}
        for script_name in ("validate_skill", "audit_skill"):
            for side, target in (("base", base_dir), ("head", head_dir)):
                if side == "base" and not has_base:
                    continue
                found, err = run_validator(scripts[script_name], target, timeout)
                if found is None:
                    return {"status": "unavailable", "error": err, "skills": result["skills"]}
                for f in found:
                    if f.get("level") == "error":
                        err_counts[side][(f.get("code", ""), _norm_location(f.get("location", ""), dirs))] += 1
                    elif f.get("level") == "warning":
                        warn_counts[side] += 1
        new_errors = sorted(f"{c}@{loc}" for (c, loc) in (err_counts["head"] - err_counts["base"]).elements())
        info.update(
            {
                "new_errors": new_errors,
                "warnings": {"base": warn_counts["base"], "head": warn_counts["head"]},
            }
        )
        # A brand-new skill has nothing to compare warnings with; only errors fail it.
        if new_errors or (has_base and warn_counts["head"] > warn_counts["base"]):
            info["reason"] = "validator-regression"
            failed = True
        prefix = "" if rel == "." else rel + "/"
        if (head_dir / "scripts").is_dir() and any(c.startswith(prefix + "scripts/") for c in changed):
            # Run on a scratch copy so test bytecode never lands in head/.
            scratch = run / "scripts-check" / (rel.replace("/", "__") or "root")
            if scratch.exists():
                shutil.rmtree(scratch)
            shutil.copytree(head_dir, scratch, ignore=shutil.ignore_patterns(*IGNORED_DIR_NAMES))
            found, err = run_validator(scripts["check_scripts"], scratch, timeout)
            if found is None:
                return {"status": "unavailable", "error": err, "skills": result["skills"]}
            errs = sorted(f"{f.get('code')}@{f.get('location', '')}" for f in found if f.get("level") == "error")
            info["scripts_check_errors"] = errs
            if errs:
                info.setdefault("reason", "scripts-check")
                info["scripts_check"] = "fail"
                failed = True
        result["skills"][rel] = info
    if failed:
        result["status"] = "fail"
        reasons = sorted({i["reason"] for i in result["skills"].values() if "reason" in i})
        if any(i.get("scripts_check") == "fail" for i in result["skills"].values()):
            reasons = sorted(set(reasons) | {"scripts-check"})
        result["reasons"] = reasons
    return result


# ---------------------------------------------------------------- eval


def find_cases(evals: Path) -> Dict[str, Path]:
    """Map case path (relative to evals/, posix) -> case directory."""
    out: Dict[str, Path] = {}
    if not evals.is_dir():
        return out
    for dirpath, dirnames, filenames in os.walk(evals):
        here = Path(dirpath)
        dirnames[:] = sorted(
            d for d in dirnames if not (here == evals and d in EVAL_IGNORED_DIRS) and d not in IGNORED_DIR_NAMES
        )
        if here != evals and ("prompt.md" in filenames or "case.yaml" in filenames):
            out[here.relative_to(evals).as_posix()] = here
    return out


def case_tags(case_dir: Path) -> List[str]:
    prompt = case_dir / "prompt.md"
    if prompt.is_file():
        tags = parse_tags(split_frontmatter(read_text(prompt) or "")[0])
        if tags:
            return tags
    yaml = case_dir / "case.yaml"
    if yaml.is_file():
        return parse_tags((read_text(yaml) or "").splitlines())
    return []


def case_declared_name(case_dir: Path) -> Optional[str]:
    """`name:` from the case's prompt.md frontmatter, which overrides the dir name."""
    prompt = case_dir / "prompt.md"
    if not prompt.is_file():
        return None
    return frontmatter_value(split_frontmatter(read_text(prompt) or "")[0], "name") or None


def resolve_case(name: str, cases: Dict[str, Path]) -> Optional[str]:
    declared = {k: case_declared_name(v) for k, v in cases.items()}
    explicit = [k for k, n in declared.items() if n == name]
    if len(explicit) == 1:
        return explicit[0]
    plain = [k for k in cases if declared[k] is None]
    if name in plain:
        return name
    matches = [k for k in plain if k.split("/")[-1] == name]
    return matches[0] if len(matches) == 1 else None


def skill_name_of(skill_dir: Path, fallback: str) -> str:
    text = read_text(skill_dir / "SKILL.md") or ""
    name = frontmatter_value(split_frontmatter(text)[0], "name")
    return name or fallback


def build_wrapper(dest: Path, skill_src: Path, evals_src: Path, name: str) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    (dest / ".claude-plugin").mkdir(parents=True)
    manifest = {"name": name, "version": "0.0.0", "description": "evolving-skills gate wrapper"}
    (dest / ".claude-plugin" / "plugin.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    def skill_ignore(d, names):
        drop = [n for n in names if n in IGNORED_DIR_NAMES]
        if Path(d) == skill_src and "evals" in names:
            drop.append("evals")
        return drop

    def evals_ignore(d, names):
        drop = [n for n in names if n in IGNORED_DIR_NAMES]
        if Path(d) == evals_src:
            drop += [n for n in names if n in EVAL_IGNORED_DIRS]
        return drop

    shutil.copytree(skill_src, dest / "skills" / name, ignore=skill_ignore)
    shutil.copytree(evals_src, dest / "evals", ignore=evals_ignore)


def parse_eval_result(path: Path) -> Tuple[Optional[Dict[str, List[float]]], str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return None, f"result unreadable: {e}"
    if not isinstance(data, dict):
        return None, "result is not an object"
    if data.get("partial"):
        return None, "partial result"
    out: Dict[str, List[float]] = {}
    for case in data.get("cases") or []:
        name = case.get("name")
        runs = ((case.get("arms") or {}).get("with")) or []
        scores = [float(r["score"]) for r in runs if isinstance(r, dict) and isinstance(r.get("score"), (int, float))]
        if not scores:
            agg = (case.get("aggregates") or {}).get("score")
            if not isinstance(agg, (int, float)):
                return None, f"case {name!r} has no score"
            scores = [float(agg)]
        out[str(name)] = scores
    return out, ""


def run_arm(cfg: dict, wrapper: Path, out: Path, case: Optional[str] = None) -> Tuple[Optional[Dict[str, List[float]]], str]:
    argv = [
        cfg["claude_bin"], "plugin", "eval", str(wrapper),
        "--ablation", "none", "--no-publish", "--trust-plugin", "--threshold", "0",
        "--runs", str(cfg["runs"]), "--max-cost-usd", str(cfg["max_cost_usd"]),
        "--json", str(out),
    ]
    if case is not None:
        argv += ["--case", case]
    elif not cfg["final"]:
        argv += ["--tag"] + list(cfg["tags"])
    if out.exists():
        out.unlink()
    try:
        proc = run_cmd(argv, timeout=cfg["timeout"])
    except subprocess.TimeoutExpired:
        return None, "eval timed out"
    except OSError as e:
        return None, f"eval could not start: {e}"
    if proc.returncode != 0:
        return None, f"eval exited {proc.returncode}: {(proc.stderr or '').strip()[:500]}"
    return parse_eval_result(out)


def mean(xs: List[float]) -> float:
    return sum(xs) / len(xs)


def apply_rules(base: Dict[str, List[float]], head: Dict[str, List[float]], meta: Dict[str, dict], final: bool) -> dict:
    """Evaluate R1-R4 for a skill with a base copy."""
    existing = [c for c in head if not meta[c]["new"]]
    # A new case tagged only holdout is left to R4 at --final.
    new = [c for c in head if meta[c]["new"] and GATE_TAG in meta[c]["tags"]]
    failed: List[str] = []
    details: Dict[str, str] = {}
    if existing:
        b = mean([mean(base[c]) for c in existing])
        h = mean([mean(head[c]) for c in existing])
        if h < b:
            failed.append(RULE_R1)
            details[RULE_R1] = f"existing mean {h:.3f} < base {b:.3f}"
        drops = [c for c in existing if mean(base[c]) - mean(head[c]) > R2_MAX_DROP]
        if drops:
            failed.append(RULE_R2)
            details[RULE_R2] = "dropped more than %.2f: %s" % (R2_MAX_DROP, ", ".join(drops))
    r3_reasons = []
    for c in new:
        hb, hh = mean(base[c]), mean(head[c])
        if hb >= PASS_SCORE:
            r3_reasons.append(f"{c}: baseline-already-passes")
        elif not (hh > hb and hh >= PASS_SCORE):
            r3_reasons.append(f"{c}: head {hh:.3f} vs base {hb:.3f}")
    if r3_reasons:
        failed.append(RULE_R3)
        details[RULE_R3] = "; ".join(r3_reasons)
        if any(r.endswith("baseline-already-passes") for r in r3_reasons):
            details["reason"] = "baseline-already-passes"
    if final:
        hold = [c for c in head if HOLDOUT_TAG in meta[c]["tags"]]
        if hold:
            b = mean([mean(base[c]) for c in hold])
            h = mean([mean(head[c]) for c in hold])
            if h < b:
                failed.append(RULE_R4)
                details[RULE_R4] = f"holdout mean {h:.3f} < base {b:.3f}"
    return {"failed": failed, "details": details}


def eval_skill(cfg: dict, run: Path, rel: str) -> dict:
    head_dir = run / "head" / rel
    base_dir = run / "base" / rel
    has_base = (base_dir / "SKILL.md").is_file()
    head_cases = find_cases(head_dir / "evals")
    if not head_cases:
        return {"status": "unmeasured", "reason": "no eval cases"}
    base_cases = find_cases(base_dir / "evals") if has_base else {}
    if has_base:
        untagged = [
            k for k in head_cases
            if k not in base_cases and not ({GATE_TAG, HOLDOUT_TAG} & set(case_tags(head_cases[k])))
        ]
        if untagged:
            return {
                "status": "fail",
                "failed_rules": [],
                "details": {"reason": RULE_NEW_CASE_UNTAGGED, "cases": untagged},
            }
    name = skill_name_of(head_dir, Path(rel).name if rel != "." else Path(cfg["root"]).name)
    arms = ["base", "head"] if has_base else ["head"]
    wrappers = {}
    for arm in arms:
        wrappers[arm] = run / "wrap" / arm / name
        build_wrapper(wrappers[arm], base_dir if arm == "base" else head_dir, head_dir / "evals", name)

    scores: Dict[str, Dict[str, List[float]]] = {}
    for arm in arms:
        res, err = run_arm(cfg, wrappers[arm], run / f"eval-{arm}-{name}.json")
        if res is None:
            return {"status": "inconclusive", "reason": f"{arm}: {err}"}
        scores[arm] = res
    if not scores["head"]:
        return {"status": "unmeasured", "reason": "no case matched"}

    meta: Dict[str, dict] = {}
    for c in scores["head"]:
        key = resolve_case(c, head_cases)
        tags = case_tags(head_cases[key]) if key else []
        # A result name that maps to no head case directory is treated as existing.
        is_new = key is not None and key not in base_cases
        meta[c] = {"new": bool(has_base and is_new), "tags": tags}

    def table() -> Dict[str, dict]:
        rows = {}
        for c in scores["head"]:
            row = {"head": round(mean(scores["head"][c]), 4), "new": meta[c]["new"], "tags": meta[c]["tags"]}
            if has_base and c in scores["base"]:
                row["base"] = round(mean(scores["base"][c]), 4)
            rows[c] = row
        return rows

    if not has_base:
        low = [c for c in scores["head"] if mean(scores["head"][c]) < PASS_SCORE]
        out = {"status": "fail" if low else "pass", "cases": table(), "new_skill": True}
        if low:
            out["failed_rules"] = [RULE_NEW_SKILL]
            out["details"] = {RULE_NEW_SKILL: "below %.2f: %s" % (PASS_SCORE, ", ".join(low))}
        return out

    missing = [c for c in scores["head"] if c not in scores["base"]]
    if missing:
        return {"status": "inconclusive", "reason": "cases missing on base arm: " + ", ".join(missing)}

    verdict = apply_rules(scores["base"], scores["head"], meta, cfg["final"])
    retakes = 0
    retaken: List[str] = []
    if (
        retakes < MAX_RETAKES
        and (RULE_R1 in verdict["failed"] or RULE_R2 in verdict["failed"])
        and RULE_R3 not in verdict["failed"]
    ):
        retakes += 1
        retaken = [
            c for c in scores["head"]
            if not meta[c]["new"] and mean(scores["head"][c]) < mean(scores["base"][c])
        ]
        for c in retaken:
            safe = re.sub(r"[^A-Za-z0-9._-]+", "_", c)
            for arm in arms:
                res, err = run_arm(cfg, wrappers[arm], run / f"eval-{arm}-{name}-retake-{safe}.json", case=c)
                if res is None:
                    return {"status": "inconclusive", "reason": f"retake {arm}/{c}: {err}", "cases": table()}
                scores[arm][c] = scores[arm][c] + res.get(c, [])
        verdict = apply_rules(scores["base"], scores["head"], meta, cfg["final"])

    out = {"status": "fail" if verdict["failed"] else "pass", "cases": table(), "retaken": retaken}
    if verdict["failed"]:
        out["failed_rules"] = verdict["failed"]
        out["details"] = verdict["details"]
    return out


def step_eval(cfg: dict, run: Path, meta: dict) -> dict:
    skills = staged_skill_dirs(run, all_paths(meta))
    per = {rel: eval_skill(cfg, run, rel) for rel in skills}
    statuses = [r["status"] for r in per.values()]
    if "fail" in statuses:
        status = "fail"
    elif "inconclusive" in statuses:
        status = "inconclusive"
    elif "pass" not in statuses:
        status = "unmeasured"
    else:
        status = "pass"
    return {"status": status, "skills": per}


# ---------------------------------------------------------------- check


def cmd_check(args) -> int:
    run, meta = load_run(args.run)
    tampered = base_mismatches(run, meta)
    if tampered:
        return refuse("base-tampered: " + ", ".join(tampered))
    steps: Dict[str, dict] = {}
    reasons: List[str] = []
    order = ["diff", "guard", "validators", "eval"]
    verdict = "pass"

    diff = compute_diff(run)
    if not (diff["added"] or diff["removed"] or diff["modified"]):
        steps["diff"] = dict(diff, status="fail", reason="empty-diff")
        verdict, reasons = "fail", ["empty-diff"]
    else:
        steps["diff"] = dict(diff, status="pass")

    if verdict == "pass":
        violations = guard(run, diff, args.protect or [], args.leak_chars, all_paths(meta))
        steps["guard"] = {"status": "blocked" if violations else "pass", "violations": violations}
        if violations:
            verdict = "blocked"
            reasons = [f"{v['kind']}: {v['file']}" + (f" ({v['detail']})" if "detail" in v else "") for v in violations]

    if verdict == "pass":
        vdir = Path(args.validators_dir).expanduser() if args.validators_dir else (
            Path(__file__).resolve().parents[2] / "creating-agent-skills" / "scripts"
        )
        if not vdir.is_dir():
            steps["validators"] = {"status": "unavailable", "missing": [str(vdir)]}
        else:
            steps["validators"] = step_validators(run, meta, diff, vdir, args.timeout_seconds)
        st = steps["validators"]["status"]
        if st == "fail":
            verdict = "fail"
            reasons = list(steps["validators"].get("reasons", ["validator-regression"]))
        elif st == "unavailable":
            verdict = "inconclusive"
            reasons = ["validators-unavailable"]

    if verdict == "pass":
        if args.skip_eval:
            steps["eval"] = {"status": "unmeasured", "reason": "--skip-eval"}
        else:
            cfg = {
                "claude_bin": args.claude_bin,
                "runs": args.runs,
                "max_cost_usd": args.max_cost_usd,
                "final": args.final,
                "tags": args.tags or ["gate"],
                "timeout": args.timeout_seconds,
                "root": meta["root"],
            }
            steps["eval"] = step_eval(cfg, run, meta)
        st = steps["eval"]["status"]
        if st != "pass":
            verdict = st
            reasons = [f"eval-{st}"]
            for rel, r in steps["eval"].get("skills", {}).items():
                if r.get("status") == "fail":
                    reasons += [f"{rel}: {rule}" for rule in r.get("failed_rules", [])]
                    if r.get("details", {}).get("reason"):
                        reasons.append(f"{rel}: {r['details']['reason']}")
                elif r.get("reason"):
                    reasons.append(f"{rel}: {r['reason']}")

    for name in order:
        steps.setdefault(name, {"status": "skipped"})
    out = {
        "verdict": verdict,
        "reasons": reasons,
        "steps": steps,
        "final": bool(args.final),
        "head_digest": head_digest(run / "head"),
        "root": meta["root"],
        "paths": meta["paths"],
        "new_paths": meta["new_paths"],
        "base_commit": meta["base_commit"],
        "created": now_iso(),
    }
    (run / "verdict.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    emit(out)
    return VERDICT_EXIT[verdict]


# ---------------------------------------------------------------- land


RUN_KEYS = ("root", "paths", "new_paths", "base_commit")


def refuse(msg: str) -> int:
    sys.stderr.write(f"refusing: {msg}\n")
    return EXIT_USAGE


def cmd_land(args) -> int:
    run, meta = load_run(args.run)
    tampered = base_mismatches(run, meta)
    if tampered:
        return refuse("base-tampered: " + ", ".join(tampered))
    root = Path(meta["root"])
    paths = all_paths(meta)
    vpath = run / "verdict.json"
    if not vpath.is_file():
        return refuse("no verdict.json; run `check` first")
    verdict = json.loads(vpath.read_text(encoding="utf-8"))
    changed_keys = [k for k in RUN_KEYS if verdict.get(k) != meta.get(k)]
    if changed_keys:
        return refuse("base-tampered: run.json " + ", ".join(changed_keys) + " changed since check")
    v = verdict.get("verdict")
    if not (v == "pass" or (v == "unmeasured" and args.allow_unmeasured)):
        return refuse(f"verdict is {v!r}")
    if head_digest(run / "head") != verdict.get("head_digest"):
        return refuse("head/ changed since check")
    if git_ok(["status", "--porcelain", "--"] + paths, root).strip():
        return refuse("the staged paths have uncommitted changes in the repository")
    proc = git(["diff", "--quiet", meta["base_commit"], "HEAD", "--"] + paths, root)
    if proc.returncode == 1:
        return refuse("the staged paths changed in the repository since stage")
    if proc.returncode != 0:
        return refuse(f"git diff failed: {proc.stderr.strip()}")
    for np in meta["new_paths"]:
        if os.path.lexists(root / np):
            return refuse(f"new path now exists in the repository: {np}")
    msg = Path(args.message_file).expanduser().resolve()
    if not msg.is_file() or not msg.read_text(encoding="utf-8").strip():
        return refuse("message file is missing or empty")

    diff = compute_diff(run)
    applied: List[str] = []
    for rel in diff["added"] + diff["modified"]:
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(run / "head" / rel, dst)
        applied.append(rel)

    def git_fail(proc: subprocess.CompletedProcess) -> int:
        sys.stderr.write("git failed after applying: " + json.dumps(applied) + "\n" + (proc.stderr or ""))
        return EXIT_GIT

    for rel in diff["removed"]:
        p = git(["rm", "-q", "--", rel], root)
        if p.returncode != 0:
            return git_fail(p)
        applied.append(rel)
    if diff["added"] + diff["modified"]:
        p = git(["add", "--"] + diff["added"] + diff["modified"], root)
        if p.returncode != 0:
            return git_fail(p)
    files = sorted(diff["added"] + diff["modified"] + diff["removed"])
    p = git(["commit", "-F", str(msg), "--"] + files, root)
    if p.returncode != 0:
        return git_fail(p)
    sha = git_ok(["rev-parse", "HEAD"], root).strip()
    out = {"commit": sha, "files": files}
    (run / "landed.json").write_text(json.dumps(dict(out, landed=now_iso()), indent=2) + "\n", encoding="utf-8")
    emit(out)
    return EXIT_PASS


# ---------------------------------------------------------------- revert


def cmd_revert(args) -> int:
    root = Path(args.root).expanduser().resolve()
    files = [f for f in git_ok(["show", "--name-only", "--format=", args.commit], root).splitlines() if f]
    if files and git_ok(["status", "--porcelain", "--"] + files, root).strip():
        return refuse("files touched by the commit have uncommitted changes")
    p = git(["revert", "--no-edit", args.commit], root)
    if p.returncode != 0:
        sys.stderr.write(p.stderr or "git revert failed\n")
        return EXIT_GIT
    emit({"reverted": args.commit, "commit": git_ok(["rev-parse", "HEAD"], root).strip()})
    return EXIT_PASS


# ---------------------------------------------------------------- main


def build_parser() -> argparse.ArgumentParser:
    p = GateArgumentParser(prog="gate.py", description="Gate automatic skill edits.")
    sub = p.add_subparsers(dest="cmd", parser_class=GateArgumentParser)
    sub.required = True

    s = sub.add_parser("stage")
    s.add_argument("--root", required=True)
    s.add_argument("--path", action="append")
    s.add_argument("--new-path", action="append")
    s.add_argument("--state-dir")

    c = sub.add_parser("check")
    c.add_argument("--run", required=True)
    c.add_argument("--tags", nargs="+", action="extend")
    c.add_argument("--final", action="store_true")
    c.add_argument("--runs", type=int, default=3)
    c.add_argument("--max-cost-usd", type=float, default=5)
    c.add_argument("--skip-eval", action="store_true")
    c.add_argument("--validators-dir")
    c.add_argument("--claude-bin", default="claude")
    c.add_argument("--protect", nargs="+", action="extend")
    c.add_argument("--leak-chars", type=int, default=32)
    c.add_argument("--timeout-seconds", type=int, default=1800)

    l = sub.add_parser("land")
    l.add_argument("--run", required=True)
    l.add_argument("--message-file", required=True)
    l.add_argument("--allow-unmeasured", action="store_true")

    r = sub.add_parser("revert")
    r.add_argument("--root", required=True)
    r.add_argument("--commit", required=True)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    try:
        args = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
        handler = {"stage": cmd_stage, "check": cmd_check, "land": cmd_land, "revert": cmd_revert}[args.cmd]
        return handler(args)
    except UsageError as e:
        sys.stderr.write(f"error: {e}\n")
        return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
