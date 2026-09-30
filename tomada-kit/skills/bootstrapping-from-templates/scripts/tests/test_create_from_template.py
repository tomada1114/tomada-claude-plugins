import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import create_from_template as cft  # noqa: E402
from create_from_template import Proc  # noqa: E402


class FakeRunner:
    """Answers commands by the first matching prefix; records every call."""

    def __init__(self, rules):
        self.rules = rules
        self.calls = []

    def __call__(self, cmd):
        cmd = list(cmd)
        self.calls.append(cmd)
        for prefix, answer in self.rules:
            if cmd[: len(prefix)] == prefix:
                return answer(cmd) if callable(answer) else answer
        return Proc(1, "", "unexpected: " + " ".join(cmd))


def ok(out=""):
    return Proc(0, out, "")


def fail(err="boom"):
    return Proc(1, "", err)


TEMPLATE_OK = (["gh", "repo", "view", "me/tpl", "--json", "isTemplate"], ok('{"isTemplate": true}'))
NEW_MISSING = (["gh", "repo", "view", "me/app", "--json", "name"], fail("not found"))
NEW_EXISTS = (["gh", "repo", "view", "me/app", "--json", "name"], ok('{"name":"app"}'))
CREATE_OK = (["gh", "repo", "create"], ok())
COMMITS_OK = (["gh", "api"], ok("1\n"))


def clone_ok(cmd):
    Path(cmd[-1]).mkdir(parents=True)
    return ok()


class ParseRemoteTest(unittest.TestCase):
    def test_https_and_ssh(self):
        self.assertEqual(cft.parse_remote("https://github.com/me/tpl.git\n"), "me/tpl")
        self.assertEqual(cft.parse_remote("git@github.com:me/tpl.git"), "me/tpl")
        self.assertEqual(cft.parse_remote("https://github.com/me/tpl"), "me/tpl")
        self.assertIsNone(cft.parse_remote("https://gitlab.com/me/tpl"))


class MainTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dest = Path(self.tmp.name) / "gh" / "me" / "app"

    def tearDown(self):
        self.tmp.cleanup()

    def run_main(self, argv, runner, sleep=lambda s: None):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cft.main(argv, run=runner, sleep=sleep)
        return code, out.getvalue(), err.getvalue()

    def base(self, *extra):
        return ["--template", "me/tpl", "--repo", "me/app", "--dest", str(self.dest), *extra]

    def test_creates_waits_and_clones(self):
        polls = iter([ok("0"), ok("1")])
        runner = FakeRunner([TEMPLATE_OK, NEW_MISSING, CREATE_OK,
                             (["gh", "api"], lambda c: next(polls)),
                             (["git", "clone"], clone_ok)])
        code, out, _ = self.run_main(self.base("--json"), runner)
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertTrue(data["created"] and data["cloned"])
        self.assertIn(["gh", "repo", "create", "me/app", "--template", "me/tpl", "--public"], runner.calls)

    def test_private_visibility_and_text_output(self):
        runner = FakeRunner([TEMPLATE_OK, NEW_MISSING, CREATE_OK, COMMITS_OK, (["git", "clone"], clone_ok)])
        code, out, _ = self.run_main(self.base("--visibility", "private"), runner)
        self.assertEqual(code, 0)
        self.assertIn("created", out)
        self.assertIn("--private", runner.calls[2])

    def test_rerun_reuses_repo_and_clone(self):
        self.dest.mkdir(parents=True)
        runner = FakeRunner([TEMPLATE_OK, NEW_EXISTS, COMMITS_OK,
                             (["git", "-C"], ok("https://github.com/me/app.git"))])
        code, out, _ = self.run_main(self.base(), runner)
        self.assertEqual(code, 0)
        self.assertIn("exists", out)
        self.assertFalse(any(c[:3] == ["gh", "repo", "create"] for c in runner.calls))

    def test_dest_belongs_to_other_repo(self):
        self.dest.mkdir(parents=True)
        runner = FakeRunner([TEMPLATE_OK, NEW_MISSING, (["git", "-C"], ok("https://github.com/x/y.git"))])
        code, _, err = self.run_main(self.base(), runner)
        self.assertEqual(code, 1)
        self.assertIn("not a clone", err)

    def test_dry_run_plans_without_writing(self):
        runner = FakeRunner([TEMPLATE_OK, NEW_MISSING])
        code, out, _ = self.run_main(self.base("--dry-run"), runner)
        self.assertEqual(code, 0)
        self.assertIn("gh repo create me/app", out)
        self.assertIn("git clone", out)
        code, out, _ = self.run_main(self.base("--dry-run", "--json"), runner)
        self.assertTrue(json.loads(out)["dry_run"])

    def test_dry_run_nothing_to_do(self):
        self.dest.mkdir(parents=True)
        runner = FakeRunner([TEMPLATE_OK, NEW_EXISTS, (["git", "-C"], ok("git@github.com:me/app.git"))])
        code, out, _ = self.run_main(self.base("--dry-run"), runner)
        self.assertEqual((code, out.strip()), (0, "nothing to do"))

    def test_not_a_template(self):
        runner = FakeRunner([(["gh", "repo", "view", "me/tpl"], ok('{"isTemplate": false}'))])
        code, _, err = self.run_main(self.base(), runner)
        self.assertEqual(code, 1)
        self.assertIn("--template", err)

    def test_template_unreadable(self):
        runner = FakeRunner([(["gh", "repo", "view", "me/tpl"], fail("auth"))])
        code, _, err = self.run_main(self.base(), runner)
        self.assertEqual(code, 1)
        self.assertIn("gh auth status", err)

    def test_create_fails(self):
        runner = FakeRunner([TEMPLATE_OK, NEW_MISSING, (["gh", "repo", "create"], fail("name taken"))])
        code, _, err = self.run_main(self.base(), runner)
        self.assertEqual(code, 1)
        self.assertIn("name taken", err)

    def test_clone_fails(self):
        runner = FakeRunner([TEMPLATE_OK, NEW_EXISTS, COMMITS_OK, (["git", "clone"], fail("denied"))])
        code, _, err = self.run_main(self.base(), runner)
        self.assertEqual(code, 1)
        self.assertIn("git clone failed", err)

    def test_wait_times_out(self):
        runner = FakeRunner([TEMPLATE_OK, NEW_EXISTS, (["gh", "api"], ok("0"))])
        code, _, err = self.run_main(self.base("--timeout", "0"), runner)
        self.assertEqual(code, 1)
        self.assertIn("Re-run", err)

    def test_wait_polls_until_commit(self):
        answers = iter([fail(), ok("1")])
        runner = FakeRunner([(["gh", "api"], lambda c: next(answers))])
        slept = []
        ticks = iter([0.0, 1.0, 2.0])
        cft.wait_for_commit("me/app", runner, 10, 3, sleep=slept.append, clock=lambda: next(ticks))
        self.assertEqual(slept, [3])

    def test_bad_repo_argument(self):
        code, _, err = self.run_main(["--template", "me/tpl", "--repo", "bad"], FakeRunner([]))
        self.assertEqual(code, 2)
        self.assertIn("OWNER/NAME", err)

    def test_bad_template_argument(self):
        code, _, err = self.run_main(["--template", "nope", "--repo", "me/app", "--dest", str(self.dest)],
                                     FakeRunner([]))
        self.assertEqual(code, 1)

    def test_template_path_with_warnings(self):
        runner = FakeRunner([
            (["git", "-C", "/tpl", "remote"], ok("git@github.com:me/tpl.git\n")),
            (["git", "-C", "/tpl", "rev-list"], ok("2\n")),
            (["git", "-C", "/tpl", "status"], ok(" M README.md\n")),
            TEMPLATE_OK, NEW_MISSING,
        ])
        code, out, _ = self.run_main(["--template-path", "/tpl", "--repo", "me/app",
                                      "--dest", str(self.dest), "--dry-run"], runner)
        self.assertEqual(code, 0)
        self.assertIn("ahead", out)
        self.assertIn("uncommitted", out)

    def test_template_path_without_origin(self):
        runner = FakeRunner([(["git", "-C", "/tpl", "remote"], fail())])
        code, _, err = self.run_main(["--template-path", "/tpl", "--repo", "me/app"], runner)
        self.assertEqual(code, 1)
        self.assertIn("no 'origin'", err)

    def test_template_path_non_github(self):
        runner = FakeRunner([(["git", "-C", "/tpl", "remote"], ok("https://gitlab.com/a/b.git"))])
        code, _, err = self.run_main(["--template-path", "/tpl", "--repo", "me/app"], runner)
        self.assertEqual(code, 1)
        self.assertIn("not a GitHub URL", err)

    def test_default_dest_uses_ghq_root(self):
        runner = FakeRunner([(["ghq", "root"], ok("/src\n"))])
        self.assertEqual(cft.default_dest("me/app", runner), Path("/src/github.com/me/app"))
        runner = FakeRunner([(["ghq", "root"], fail())])
        self.assertEqual(cft.default_dest("me/app", runner), Path.home() / "ghq/github.com/me/app")

    def test_run_cmd_executes(self):
        p = cft.run_cmd([sys.executable, "-c", "print('hi')"])
        self.assertEqual((p.returncode, p.stdout.strip()), (0, "hi"))


if __name__ == "__main__":
    unittest.main()
