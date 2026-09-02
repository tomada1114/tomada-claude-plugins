#!/usr/bin/env python3
"""Tests for worktree_setup.sh. Stdlib-only (unittest).

Run: python3 -m unittest discover -s scripts/tests -p 'test_*.py'
     (from the shipping-issues skill directory)

worktree_setup.sh never calls `gh` (it only touches git and the local
filesystem), so these tests don't use FakeGh — they drive real, disposable
git repos under tempfile.TemporaryDirectory() instead.
"""
from __future__ import annotations

import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


SCRIPT = Path(__file__).resolve().parent.parent / "worktree_setup.sh"


def git(repo, *args):
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        text=True,
        capture_output=True,
    )


def make_repo(path):
    git(path, "init", "-q")
    git(path, "config", "user.email", "tests@example.invalid")
    git(path, "config", "user.name", "shipping-issues tests")
    (path / "README.md").write_text("fixture\n", encoding="utf-8")
    git(path, "add", "README.md")
    git(path, "commit", "-qm", "fixture")
    git(path, "branch", "-M", "main")


def write_stub(bin_dir: Path, name: str, record_path: Path, *, exit_code: int = 0) -> None:
    """Install a fake executable on `bin_dir` that records its argv and cwd
    (one per line) to `record_path`, then exits with `exit_code`."""
    stub = bin_dir / name
    stub.write_text(
        "#!/usr/bin/env bash\n"
        f'printf \'%s\\n\' "$*" > "{record_path}"\n'
        f'pwd >> "{record_path}"\n'
        f"exit {exit_code}\n",
        encoding="utf-8",
    )
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def run_script(args, cwd, *, extra_path: str | None = None):
    env = dict(os.environ)
    if extra_path:
        env["PATH"] = f"{extra_path}{os.pathsep}{env.get('PATH', '')}"
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
    )


class WorktreeSetupTest(unittest.TestCase):
    def test_creates_worktree_on_requested_branch_from_base(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            repo = td / "repo"
            repo.mkdir()
            make_repo(repo)
            root = td / "worktrees"

            proc = run_script(
                ["--issue", "42", "--branch", "feat/42", "--base", "main", "--root", str(root)],
                repo,
            )

            wt = root / "42"
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(wt.is_dir())
            branch = git(wt, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
            wt_head = git(wt, "rev-parse", "HEAD").stdout.strip()
            main_head = git(repo, "rev-parse", "main").stdout.strip()

        self.assertEqual(branch, "feat/42")
        self.assertEqual(wt_head, main_head)
        self.assertIn(f"worktree: {wt}\n", proc.stdout)
        self.assertIn("result: CREATED\n", proc.stdout)
        self.assertIn("verdict: READY\n", proc.stdout)

    def test_main_checkout_stays_clean(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            repo = td / "repo"
            repo.mkdir()
            make_repo(repo)
            root = td / "worktrees"

            before = git(repo, "status", "--porcelain").stdout
            proc = run_script(
                ["--issue", "1", "--branch", "feat/1", "--base", "main", "--root", str(root)],
                repo,
            )
            after = git(repo, "status", "--porcelain").stdout

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(before, "")
        self.assertEqual(after, "", "worktree_setup.sh must never dirty the main checkout")

    def test_copies_untracked_local_config_only(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            repo = td / "repo"
            repo.mkdir()
            make_repo(repo)
            (repo / ".env").write_text("A=1\n", encoding="utf-8")
            (repo / ".env.local").write_text("B=2\n", encoding="utf-8")
            (repo / ".env.example").write_text("C=3\n", encoding="utf-8")
            (repo / ".claude").mkdir()
            (repo / ".claude" / "settings.local.json").write_text("{}\n", encoding="utf-8")
            # .envrc matches a copy pattern but is tracked, so it must be
            # left to the normal `git worktree add` checkout, not re-copied.
            (repo / ".envrc").write_text("export D=4\n", encoding="utf-8")
            git(repo, "add", ".envrc")
            git(repo, "commit", "-qm", "track envrc")
            root = td / "worktrees"

            proc = run_script(
                ["--issue", "9", "--branch", "feat/9", "--base", "main", "--root", str(root)],
                repo,
            )
            wt = root / "9"
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual((wt / ".env").read_text(encoding="utf-8"), "A=1\n")
            self.assertEqual((wt / ".env.local").read_text(encoding="utf-8"), "B=2\n")
            self.assertEqual(
                (wt / ".claude" / "settings.local.json").read_text(encoding="utf-8"), "{}\n"
            )
            self.assertFalse((wt / ".env.example").exists())

        self.assertIn("copied: .env\n", proc.stdout)
        self.assertIn("copied: .env.local\n", proc.stdout)
        self.assertIn("copied: .claude/settings.local.json\n", proc.stdout)
        self.assertNotIn("copied: .env.example\n", proc.stdout)
        self.assertNotIn("copied: .envrc\n", proc.stdout)

    def test_reentry_against_existing_worktree_is_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            repo = td / "repo"
            repo.mkdir()
            make_repo(repo)
            root = td / "worktrees"
            args = ["--issue", "5", "--branch", "feat/5", "--base", "main", "--root", str(root)]

            first = run_script(args, repo)
            second = run_script(args, repo)

        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn("result: EXISTS\n", second.stdout)
        self.assertIn("verdict: READY\n", second.stdout)

    def test_path_exists_but_is_not_a_registered_worktree_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            repo = td / "repo"
            repo.mkdir()
            make_repo(repo)
            root = td / "worktrees"
            (root / "6").mkdir(parents=True)

            proc = run_script(
                ["--issue", "6", "--branch", "feat/6", "--base", "main", "--root", str(root)],
                repo,
            )

        self.assertEqual(proc.returncode, 1)
        self.assertIn("verdict: BLOCKED\n", proc.stdout)

    def test_dependency_install_runs_detected_command_in_worktree(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            repo = td / "repo"
            repo.mkdir()
            make_repo(repo)
            (repo / "pnpm-lock.yaml").write_text("lockfileVersion: '6.0'\n", encoding="utf-8")
            git(repo, "add", "pnpm-lock.yaml")
            git(repo, "commit", "-qm", "add pnpm lockfile")
            root = td / "worktrees"
            bin_dir = td / "bin"
            bin_dir.mkdir()
            record = td / "pnpm-call.txt"
            write_stub(bin_dir, "pnpm", record, exit_code=0)

            proc = run_script(
                ["--issue", "3", "--branch", "feat/3", "--base", "main", "--root", str(root)],
                repo,
                extra_path=str(bin_dir),
            )
            wt = root / "3"
            recorded = record.read_text(encoding="utf-8").splitlines()

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(recorded[0], "install --frozen-lockfile")
        self.assertEqual(recorded[1], str(wt))
        self.assertIn("deps: pnpm install --frozen-lockfile\n", proc.stdout)

    def test_install_command_failure_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            repo = td / "repo"
            repo.mkdir()
            make_repo(repo)
            (repo / "pnpm-lock.yaml").write_text("lockfileVersion: '6.0'\n", encoding="utf-8")
            git(repo, "add", "pnpm-lock.yaml")
            git(repo, "commit", "-qm", "add pnpm lockfile")
            root = td / "worktrees"
            bin_dir = td / "bin"
            bin_dir.mkdir()
            record = td / "pnpm-call.txt"
            write_stub(bin_dir, "pnpm", record, exit_code=7)

            proc = run_script(
                ["--issue", "4", "--branch", "feat/4", "--base", "main", "--root", str(root)],
                repo,
                extra_path=str(bin_dir),
            )

        self.assertEqual(proc.returncode, 1)
        self.assertIn("verdict: BLOCKED\n", proc.stdout)
        self.assertIn("exit=7", proc.stdout)

    def test_verify_failure_is_a_warning_not_a_blocker(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            repo = td / "repo"
            repo.mkdir()
            make_repo(repo)
            root = td / "worktrees"
            log = td / "verify-logs" / "10.log"

            proc = run_script(
                [
                    "--issue", "10", "--branch", "feat/10", "--base", "main",
                    "--root", str(root),
                    "--verify", "echo failing-output && exit 1",
                    "--log", str(log),
                ],
                repo,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(log.exists())
            self.assertIn("failing-output", log.read_text(encoding="utf-8"))

        self.assertIn("baseline: FAIL(exit=1)\n", proc.stdout)
        self.assertIn(f"baseline_log: {log}\n", proc.stdout)
        self.assertIn("verdict: READY_WITH_WARNINGS\n", proc.stdout)
        self.assertNotIn(str(repo), str(log))

    def test_dry_run_creates_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            repo = td / "repo"
            repo.mkdir()
            make_repo(repo)
            root = td / "worktrees"

            proc = run_script(
                [
                    "--issue", "11", "--branch", "feat/11", "--base", "main",
                    "--root", str(root), "--dry-run",
                ],
                repo,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertFalse((root / "11").exists())
            worktree_list = git(repo, "worktree", "list").stdout.strip().splitlines()
            self.assertEqual(len(worktree_list), 1)

        self.assertTrue(
            any(line.startswith("DRY:") for line in proc.stdout.splitlines()),
            proc.stdout,
        )

    def test_resolves_main_checkout_from_inside_another_worktree(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            repo = td / "repo"
            repo.mkdir()
            make_repo(repo)
            other = td / "other-worktree"
            git(repo, "worktree", "add", str(other), "-b", "other-branch", "main")
            root = td / "worktrees"

            proc = run_script(
                ["--issue", "12", "--branch", "feat/12", "--base", "main", "--root", str(root)],
                other,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue((root / "12").is_dir())
            # git canonicalizes --git-common-dir (e.g. resolving macOS's
            # /var -> /private/var symlink), so compare against the
            # resolved repo path rather than the literal one this test
            # constructed it from.
            resolved_repo = repo.resolve()

        self.assertIn(f"repo_root: {resolved_repo}\n", proc.stdout)


if __name__ == "__main__":
    unittest.main()
