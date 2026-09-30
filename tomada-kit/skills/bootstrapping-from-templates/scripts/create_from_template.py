#!/usr/bin/env python3
"""Create a GitHub repository from a template repository and clone it locally.

GitHub fills a repository created from a template asynchronously, so cloning right after
`gh repo create --template` can fetch an empty repository. This script waits until the
default branch has a commit before cloning. Re-running is safe: an existing repository
is not re-created and an existing clone of it is reused.

Exit codes: 0 created or reused, 1 a step failed, 2 bad invocation.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Sequence

REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
REMOTE_RE = re.compile(r"github\.com[:/]([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?$")


@dataclass
class Proc:
    returncode: int
    stdout: str = ""
    stderr: str = ""


Runner = Callable[[Sequence[str]], Proc]


def run_cmd(cmd: Sequence[str]) -> Proc:
    p = subprocess.run(list(cmd), capture_output=True, text=True)
    return Proc(p.returncode, p.stdout, p.stderr)


@dataclass
class Result:
    repo: str
    template: str
    path: str
    url: str = ""
    visibility: str = "public"
    created: bool = False
    cloned: bool = False
    dry_run: bool = False
    warnings: list[str] = field(default_factory=list)
    planned: list[str] = field(default_factory=list)


class StepError(Exception):
    """A step failed; the message names the fix."""


def parse_remote(url: str) -> str | None:
    m = REMOTE_RE.search(url.strip())
    return m.group(1) if m else None


def template_from_path(path: Path, run: Runner) -> tuple[str, list[str]]:
    """Resolve owner/name from a local template checkout and collect warnings about it."""
    remote = run(["git", "-C", str(path), "remote", "get-url", "origin"])
    if remote.returncode != 0:
        raise StepError(f"{path} has no 'origin' remote; pass --template OWNER/NAME instead.")
    name = parse_remote(remote.stdout)
    if not name:
        raise StepError(f"origin of {path} is not a GitHub URL: {remote.stdout.strip()}")
    warnings: list[str] = []
    ahead = run(["git", "-C", str(path), "rev-list", "--count", "@{u}..HEAD"])
    if ahead.returncode == 0 and ahead.stdout.strip() not in ("", "0"):
        warnings.append(
            f"local template is {ahead.stdout.strip()} commit(s) ahead of its upstream; "
            "the new repository is cut from GitHub's copy, so push first if those commits belong in it"
        )
    dirty = run(["git", "-C", str(path), "status", "--porcelain"])
    if dirty.returncode == 0 and dirty.stdout.strip():
        warnings.append("local template has uncommitted changes; they will not be in the new repository")
    return name, warnings


def check_template(template: str, run: Runner) -> None:
    p = run(["gh", "repo", "view", template, "--json", "isTemplate"])
    if p.returncode != 0:
        raise StepError(f"cannot read {template}: {p.stderr.strip()} (is `gh auth status` logged in?)")
    if not json.loads(p.stdout or "{}").get("isTemplate"):
        raise StepError(
            f"{template} is not marked as a template repository; enable it with "
            f"`gh repo edit {template} --template` or pick another template."
        )


def repo_exists(repo: str, run: Runner) -> bool:
    return run(["gh", "repo", "view", repo, "--json", "name"]).returncode == 0


def wait_for_commit(repo: str, run: Runner, timeout: float, interval: float,
                    sleep: Callable[[float], None] = time.sleep,
                    clock: Callable[[], float] = time.monotonic) -> None:
    deadline = clock() + timeout
    while True:
        p = run(["gh", "api", f"repos/{repo}/commits?per_page=1", "--jq", "length"])
        if p.returncode == 0 and p.stdout.strip() not in ("", "0"):
            return
        if clock() >= deadline:
            raise StepError(
                f"{repo} still has no commits after {timeout:.0f}s; GitHub may still be copying "
                "the template. Re-run this script with the same arguments to resume."
            )
        sleep(interval)


def default_dest(repo: str, run: Runner) -> Path:
    p = run(["ghq", "root"])
    root = Path(p.stdout.strip()) if p.returncode == 0 and p.stdout.strip() else Path.home() / "ghq"
    return root / "github.com" / repo


def origin_matches(dest: Path, repo: str, run: Runner) -> bool:
    p = run(["git", "-C", str(dest), "remote", "get-url", "origin"])
    return p.returncode == 0 and parse_remote(p.stdout) == repo


def create(args: argparse.Namespace, run: Runner = run_cmd,
           sleep: Callable[[float], None] = time.sleep) -> Result:
    warnings: list[str] = []
    template = args.template
    if args.template_path:
        template, warnings = template_from_path(Path(args.template_path), run)
    if not template or not REPO_RE.match(template):
        raise StepError("give the template as --template OWNER/NAME or --template-path DIR")
    dest = Path(args.dest) if args.dest else default_dest(args.repo, run)
    result = Result(repo=args.repo, template=template, path=str(dest),
                    url=f"https://github.com/{args.repo}", visibility=args.visibility,
                    dry_run=args.dry_run, warnings=warnings)

    check_template(template, run)
    exists = repo_exists(args.repo, run)
    create_cmd = ["gh", "repo", "create", args.repo, "--template", template, f"--{args.visibility}"]
    clone_cmd = ["git", "clone", f"https://github.com/{args.repo}.git", str(dest)]
    if dest.exists() and not origin_matches(dest, args.repo, run):
        raise StepError(f"{dest} exists and is not a clone of {args.repo}; pass --dest elsewhere.")
    need_clone = not dest.exists()

    if args.dry_run:
        result.planned = ([" ".join(create_cmd)] if not exists else []) + \
                         ([" ".join(clone_cmd)] if need_clone else [])
        return result

    if not exists:
        p = run(create_cmd)
        if p.returncode != 0:
            raise StepError(f"gh repo create failed: {p.stderr.strip()}")
        result.created = True
    wait_for_commit(args.repo, run, args.timeout, args.interval, sleep=sleep)
    if need_clone:
        dest.parent.mkdir(parents=True, exist_ok=True)
        p = run(clone_cmd)
        if p.returncode != 0:
            raise StepError(f"git clone failed: {p.stderr.strip()}")
        result.cloned = True
    return result


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--template", help="template repository as OWNER/NAME")
    src.add_argument("--template-path", help="local checkout of the template; owner/name read from origin")
    ap.add_argument("--repo", required=True, help="new repository as OWNER/NAME")
    ap.add_argument("--visibility", choices=["public", "private", "internal"], default="public")
    ap.add_argument("--dest", help="clone destination (default: $(ghq root)/github.com/OWNER/NAME)")
    ap.add_argument("--timeout", type=float, default=120.0, help="seconds to wait for the template copy")
    ap.add_argument("--interval", type=float, default=3.0, help="seconds between polls")
    ap.add_argument("--dry-run", action="store_true", help="check and print the plan without writing")
    ap.add_argument("--json", action="store_true", help="print the result as JSON")
    return ap


def main(argv: Sequence[str] | None = None, run: Runner = run_cmd,
         sleep: Callable[[float], None] = time.sleep) -> int:
    args = build_parser().parse_args(argv)
    if not REPO_RE.match(args.repo):
        print(f"error: --repo must be OWNER/NAME, got {args.repo!r}", file=sys.stderr)
        return 2
    try:
        result = create(args, run=run, sleep=sleep)
    except StepError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    else:
        for w in result.warnings:
            print(f"warning: {w}")
        if result.dry_run:
            print("\n".join(result.planned) or "nothing to do")
        else:
            state = "created" if result.created else "exists"
            print(f"{result.repo}: {state}; clone at {result.path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
