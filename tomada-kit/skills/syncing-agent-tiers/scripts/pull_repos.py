#!/usr/bin/env python3
"""Fast-forward each synced repo's main checkout, only when it is safe to."""
import json
import subprocess
from pathlib import Path

cfg = json.loads((Path(__file__).parent.parent / "assets/repos.json").read_text())
root = Path.home() / "ghq/github.com" / cfg["owner"]


def git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)


for name in cfg["repos"]:
    repo = root / name
    if not repo.is_dir():
        print(f"{name}: skip (not cloned)")
        continue
    branch = git(repo, "branch", "--show-current").stdout.strip()
    if branch != "main":
        print(f"{name}: skip (on {branch or 'detached HEAD'})")
        continue
    if git(repo, "status", "--porcelain").stdout.strip():
        print(f"{name}: skip (uncommitted changes)")
        continue
    r = git(repo, "pull", "--ff-only", "--quiet")
    print(f"{name}: {'ok' if r.returncode == 0 else 'FAILED ' + r.stderr.strip()}")
