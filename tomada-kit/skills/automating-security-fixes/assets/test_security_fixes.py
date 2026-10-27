"""Tests for scripts/security_fixes.py.

No test reaches GitHub, a registry, uv, or pnpm: `call` and `fetch_json` are
replaced on the loaded module, and the fake lockers rewrite the lockfiles the
way the real ones would for the versions a test names.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from types import ModuleType

    type MakeFake = Callable[..., Fake]

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "security_fixes", REPO_ROOT / "scripts" / "security_fixes.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolve their module through sys.modules while the class body runs.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


security_fixes = _load_module()

NOW = "2026-10-25T12:00:00Z"
REPO = "owner/app"

PYPROJECT = """\
[tool.uv]
exclude-newer = "7 days"

# One-package exceptions.
[tool.uv.exclude-newer-package]

[tool.uv.workspace]
members = ["backend"]
"""

WORKSPACE = """\
packages:
  - "frontend"

minimumReleaseAge: 10080
# One-version exceptions.
minimumReleaseAgeExclude: []

trustLockfile: false
"""


def _uv_lock(versions: dict[str, str]) -> str:
    return "version = 1\n" + "".join(
        f'\n[[package]]\nname = "{name}"\nversion = "{version}"\n'
        for name, version in sorted(versions.items())
    )


def _pnpm_lock(versions: dict[str, str]) -> str:
    keys = "".join(
        f"\n  '{name}@{version}':\n    resolution: {{integrity: x}}\n"
        if name.startswith("@")
        else f"\n  {name}@{version}:\n    resolution: {{integrity: x}}\n"
        for name, version in sorted(versions.items())
    )
    return f"---\nlockfileVersion: '9.0'\n\nimporters:\n\n  .: {{}}\n\npackages:\n{keys}\nsnapshots: {{}}\n"


def _alert(  # noqa: PLR0913 -- one keyword per field a test varies
    package: str,
    vulnerable: str,
    patched: str | None,
    *,
    ghsa: str = "GHSA-aaaa-bbbb-cccc",
    ecosystem: str = "pip",
    manifest: str = "uv.lock",
) -> dict[str, Any]:
    return {
        "html_url": f"https://github.com/{REPO}/security/dependabot/1",
        "dependency": {
            "package": {"ecosystem": ecosystem, "name": package},
            "manifest_path": manifest,
        },
        "security_advisory": {
            "ghsa_id": ghsa,
            "severity": "high",
            "withdrawn_at": None,
        },
        "security_vulnerability": {
            "vulnerable_version_range": vulnerable,
            "first_patched_version": {"identifier": patched} if patched else None,
        },
    }


def _advisory(
    package: str,
    vulnerable: str,
    patched: str | None,
    *,
    ghsa: str = "GHSA-dddd-eeee-ffff",
) -> dict[str, Any]:
    return {
        "ghsa_id": ghsa,
        "severity": "high",
        "html_url": f"https://github.com/advisories/{ghsa}",
        "withdrawn_at": None,
        "vulnerabilities": [
            {
                "package": {"ecosystem": "pip", "name": package},
                "vulnerable_version_range": vulnerable,
                "first_patched_version": patched,
            }
        ],
    }


@dataclass
class Fake:
    """Stands in for gh, uv, pnpm, and the registries."""

    root: Path
    alerts: list[dict[str, Any]] = field(default_factory=list)
    pulls: list[dict[str, str]] = field(default_factory=list)
    uv_result: dict[str, str] = field(default_factory=dict)
    pnpm_result: dict[str, str] = field(default_factory=dict)
    # Per-call lock results, consumed before the fixed result above applies.
    uv_rounds: list[dict[str, str]] = field(default_factory=list)
    pnpm_rounds: list[dict[str, str]] = field(default_factory=list)
    # GitHub Advisory Database entries; the script filters them by version.
    advisories: list[dict[str, Any]] = field(default_factory=list)
    published: dict[str, str] = field(default_factory=dict)
    gh_fails: bool = False
    pnpm_install_fails: bool = False
    calls: list[list[str]] = field(default_factory=list)

    def call(self, argv: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        argv = list(argv)
        self.calls.append(argv)
        out = ""
        code = 0
        if argv[:2] == ["gh", "api"]:
            if self.gh_fails:
                return subprocess.CompletedProcess(argv, 1, "", "HTTP 403")
            if "dependabot/alerts" in argv[3]:
                rows = self.alerts
            elif argv[3].startswith("advisories?"):
                rows = self.advisories
            else:
                rows = self.pulls
            out = "".join(json.dumps(row) + "\n" for row in rows)
        elif argv[:2] == ["uv", "lock"]:
            lock = security_fixes.uv_locked((cwd / "uv.lock").read_text("utf-8"))
            versions = {name: max(found) for name, found in lock.items()}
            versions.update(self.uv_rounds.pop(0) if self.uv_rounds else self.uv_result)
            (cwd / "uv.lock").write_text(_uv_lock(versions), "utf-8")
        elif argv[:2] == ["pnpm", "update"]:
            lock = security_fixes.pnpm_locked(
                (cwd / "pnpm-lock.yaml").read_text("utf-8")
            )
            versions = {name: max(found) for name, found in lock.items()}
            versions.update(
                self.pnpm_rounds.pop(0) if self.pnpm_rounds else self.pnpm_result
            )
            (cwd / "pnpm-lock.yaml").write_text(_pnpm_lock(versions), "utf-8")
        elif argv[:2] == ["pnpm", "install"] and self.pnpm_install_fails:
            code = 1
        return subprocess.CompletedProcess(
            argv, code, out, "policy violation" if code else ""
        )

    def fetch_json(self, url: str) -> Any:
        if url.startswith("https://pypi.org/pypi/"):
            name, version = url.removeprefix("https://pypi.org/pypi/").split("/")[:2]
            stamp = self.published[f"{name}=={version}"]
            return {"urls": [{"upload_time_iso_8601": stamp}]}
        name = url.removeprefix("https://registry.npmjs.org/").replace("%2F", "/")
        return {
            "time": {
                key.split("@")[-1]: value
                for key, value in self.published.items()
                if key.rsplit("@", 1)[0] == name
            }
        }


@pytest.fixture
def make_fake(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> MakeFake:
    def make(
        uv: dict[str, str] | None = None,
        pnpm: dict[str, str] | None = None,
        pyproject: str = PYPROJECT,
        workspace: str = WORKSPACE,
    ) -> Fake:
        (tmp_path / "pyproject.toml").write_text(pyproject, "utf-8")
        (tmp_path / "uv.lock").write_text(_uv_lock(uv or {}), "utf-8")
        (tmp_path / "pnpm-workspace.yaml").write_text(workspace, "utf-8")
        (tmp_path / "pnpm-lock.yaml").write_text(_pnpm_lock(pnpm or {}), "utf-8")
        fake = Fake(tmp_path)
        monkeypatch.setattr(security_fixes, "call", fake.call)
        monkeypatch.setattr(security_fixes, "fetch_json", fake.fetch_json)
        return fake

    return make


def _main(fake: Fake, *extra: str) -> int:
    out = fake.root / "out"
    return int(
        security_fixes.main(
            ["--out", str(out), "--repo", REPO, "--now", NOW, *extra], root=fake.root
        )
    )


# --------------------------------------------------------------------------- #
#  The committed files
# --------------------------------------------------------------------------- #


def test_committed_exception_lists_parse_under_a_seven_day_window() -> None:
    # A Security Fixes pull request adds entries to these files, so the test
    # holds for any entries the script can read, not only for empty lists.
    pyproject = (REPO_ROOT / "pyproject.toml").read_text("utf-8")
    workspace = (REPO_ROOT / "pnpm-workspace.yaml").read_text("utf-8")

    assert isinstance(security_fixes.uv_exceptions(pyproject), dict)
    assert isinstance(security_fixes.pnpm_exceptions(workspace), list)
    assert security_fixes.uv_window(pyproject) == timedelta(days=7)
    assert security_fixes.pnpm_window(workspace) == timedelta(days=7)


def test_committed_lockfiles_parse() -> None:
    uv = security_fixes.uv_locked((REPO_ROOT / "uv.lock").read_text("utf-8"))
    pnpm = security_fixes.pnpm_locked((REPO_ROOT / "pnpm-lock.yaml").read_text("utf-8"))

    assert "pytest" in uv
    assert "react" in pnpm
    assert any(name.startswith("@") for name in pnpm)


# --------------------------------------------------------------------------- #
#  Versions
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("version", "vulnerable", "expected"),
    [
        ("21.14.8", "< 21.14.9", True),
        ("21.14.9", "< 21.14.9", False),
        ("21.14.1", ">= 20.26.6, <= 21.14.1", True),
        ("20.26.5", ">= 20.26.6, <= 21.14.1", False),
        ("2026.6.17", ">= 2019.03.09, < 2026.10.19", True),
        ("1.0", "= 1.0.0", True),
        ("v2.1", "> 2.0.9", True),
    ],
    ids=[
        "below",
        "at-fix",
        "inside-pair",
        "below-pair",
        "date-versions",
        "padded",
        "v-prefix",
    ],
)
def test_in_range_reads_github_ranges(
    version: str, vulnerable: str, expected: bool
) -> None:
    assert security_fixes.in_range(version, vulnerable) is expected


def test_in_range_rejects_a_pre_release_instead_of_guessing() -> None:
    with pytest.raises(
        security_fixes.SecurityFixError, match="cannot compare version"
    ) as info:
        security_fixes.in_range("1.0.0-beta.1", "< 1.0.0")

    assert info.value.code == "ERR_FIXES_VERSION"


def test_plan_fixes_targets_the_highest_patch_among_live_alerts() -> None:
    alert = security_fixes.Alert
    notes: list[str] = []
    alerts = [
        alert("uv", "virtualenv", "GHSA-1", "high", "<= 21.14.1", "21.14.2", ""),
        alert("uv", "virtualenv", "GHSA-2", "medium", "< 21.14.9", "21.14.9", ""),
        alert("uv", "virtualenv", "GHSA-3", "low", "< 1.0", "1.0", ""),
        alert("uv", "certifi", "GHSA-4", "high", "< 2026.10.19", "2026.10.19", ""),
        alert("uv", "idna", "GHSA-5", "high", "< 9", None, ""),
    ]
    locked = {"virtualenv": {"21.9.0"}, "certifi": {"2026.10.19"}, "idna": {"3.10"}}

    fixes = security_fixes.plan_fixes(alerts, locked, notes)

    assert [(fix.package, fix.target) for fix in fixes] == [("virtualenv", "21.14.9")]
    assert {a.ghsa for a in fixes[0].alerts} == {"GHSA-1", "GHSA-2"}
    assert any(note.startswith("certifi: no locked version") for note in notes)
    assert any(note == "idna: no patched version yet for GHSA-5" for note in notes)


# --------------------------------------------------------------------------- #
#  Editing the exception lists
# --------------------------------------------------------------------------- #


def test_uv_add_then_drop_round_trips_with_its_comment() -> None:
    added = security_fixes.uv_add(
        PYPROJECT, "certifi", "2026-10-20T02:24:17Z", ["why", "when"]
    )
    replaced = security_fixes.uv_add(
        added, "certifi", "2026-10-21T00:00:00Z", ["newer"]
    )

    assert '# why\n# when\ncertifi = "2026-10-20T02:24:17Z"\n' in added
    assert tomllib.loads(replaced)["tool"]["uv"]["exclude-newer-package"] == {
        "certifi": "2026-10-21T00:00:00Z"
    }
    assert "# why" not in replaced
    assert security_fixes.uv_drop(replaced, "certifi") == PYPROJECT


def test_uv_exceptions_rejects_an_entry_it_cannot_read() -> None:
    text = PYPROJECT.replace(
        "[tool.uv.exclude-newer-package]\n",
        "[tool.uv.exclude-newer-package]\ncertifi = { cutoff = 1 }\n",
    )

    with pytest.raises(security_fixes.SecurityFixError, match="cannot read") as info:
        security_fixes.uv_exceptions(text)

    assert info.value.code == "ERR_FIXES_FILE"


def test_pnpm_add_then_drop_round_trips_to_an_empty_list() -> None:
    added = security_fixes.pnpm_add(WORKSPACE, "@scope/pkg@1.2.3", ["why"])
    twice = security_fixes.pnpm_add(added, "@scope/pkg@1.2.3", ["again"])

    assert (
        'minimumReleaseAgeExclude:\n  # why\n  - "@scope/pkg@1.2.3"\n\ntrust' in added
    )
    assert twice == added
    assert security_fixes.pnpm_exceptions(added) == ["@scope/pkg@1.2.3"]
    assert security_fixes.pnpm_drop(added, "@scope/pkg@1.2.3") == WORKSPACE


def test_pnpm_exceptions_rejects_a_flow_list() -> None:
    text = WORKSPACE.replace(
        "minimumReleaseAgeExclude: []", "minimumReleaseAgeExclude: [a]"
    )

    with pytest.raises(security_fixes.SecurityFixError, match="flow value") as info:
        security_fixes.pnpm_exceptions(text)

    assert info.value.code == "ERR_FIXES_FILE"


def test_title_shortens_a_long_package_list() -> None:
    plan = security_fixes.Plan(
        fixes=[
            security_fixes.Fix("uv", f"package-number-{i}", "1.0", []) for i in range(6)
        ]
    )

    result = security_fixes.title(plan)

    assert len(result) <= security_fixes.TITLE_LIMIT
    assert result.startswith("deps: fix security alerts in package-number-0")
    assert result.endswith("more")


# --------------------------------------------------------------------------- #
#  Runs
# --------------------------------------------------------------------------- #


def test_main_does_nothing_while_an_earlier_pull_request_is_open(
    make_fake: MakeFake,
) -> None:
    fake = make_fake(uv={"certifi": "2026.6.17"})
    fake.pulls = [{"ref": "automation/security-fixes/1", "url": "https://x/pull/1"}]
    fake.alerts = [_alert("certifi", "< 2026.10.19", "2026.10.19")]

    assert _main(fake) == 0
    assert not (fake.root / "out").exists()
    assert [argv[:2] for argv in fake.calls] == [["gh", "api"]]


def test_main_adds_a_cutoff_just_after_a_fix_inside_the_window(
    make_fake: MakeFake,
) -> None:
    fake = make_fake(uv={"certifi": "2026.6.17"})
    fake.alerts = [_alert("certifi", ">= 2019.03.09, < 2026.10.19", "2026.10.19")]
    fake.published = {"certifi==2026.10.19": "2026-10-20T02:24:16.604828Z"}
    fake.uv_result = {"certifi": "2026.10.19"}

    assert _main(fake) == 0

    pyproject = (fake.root / "pyproject.toml").read_text("utf-8")
    assert tomllib.loads(pyproject)["tool"]["uv"]["exclude-newer-package"] == {
        "certifi": "2026-10-20T02:24:17Z"
    }
    assert (
        "# GHSA-aaaa-bbbb-cccc: version 2026.10.19, published 2026-10-20T02:24:16Z."
        in (pyproject)
    )
    assert ["uv", "lock", "--upgrade-package=certifi"] in fake.calls
    assert (fake.root / "out" / "title.txt").read_text("utf-8") == (
        "deps: fix security alerts in certifi\n"
    )
    body = (fake.root / "out" / "body.md").read_text("utf-8")
    assert "exception until 2026-10-27" in body
    assert "`certifi`: 2026.6.17 → 2026.10.19" in body


def test_main_upgrades_a_fix_already_outside_the_window_without_an_exception(
    make_fake: MakeFake,
) -> None:
    fake = make_fake(uv={"virtualenv": "21.9.0"})
    fake.alerts = [_alert("virtualenv", "< 21.14.9", "21.14.9")]
    fake.published = {"virtualenv==21.14.9": "2026-10-17T16:09:42Z"}
    fake.uv_result = {"virtualenv": "21.14.11"}

    assert _main(fake) == 0

    pyproject = (fake.root / "pyproject.toml").read_text("utf-8")
    assert security_fixes.uv_exceptions(pyproject) == {}
    assert "already outside the window" in (fake.root / "out" / "body.md").read_text(
        "utf-8"
    )


def test_main_fails_when_the_lock_still_holds_a_vulnerable_version(
    make_fake: MakeFake, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = make_fake(uv={"virtualenv": "21.9.0"})
    fake.alerts = [_alert("virtualenv", "< 21.14.9", "21.14.9")]
    fake.published = {"virtualenv==21.14.9": "2026-10-17T16:09:42Z"}
    fake.uv_result = {"virtualenv": "21.14.8"}

    assert _main(fake) == 1

    err = capsys.readouterr().err
    assert err.startswith("ERR_FIXES_UNRESOLVED: virtualenv is still locked at 21.14.8")
    assert "\nExpected: " in err
    assert "\nNext: " in err
    assert not (fake.root / "out").exists()
    assert security_fixes.uv_locked((fake.root / "uv.lock").read_text("utf-8")) == {
        "virtualenv": {"21.9.0"}
    }


def test_main_still_plans_one_lockfile_when_the_other_fails(
    make_fake: MakeFake, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = make_fake(uv={"certifi": "2026.6.17"}, pnpm={"postcss": "8.5.30"})
    fake.alerts = [
        _alert("certifi", "< 2026.10.19", "2026.10.19"),
        _alert(
            "postcss", "< 8.5.31", "8.5.31", ecosystem="npm", manifest="pnpm-lock.yaml"
        ),
    ]
    fake.published = {
        "certifi==2026.10.19": "2026-10-10T00:00:00Z",
        "postcss@8.5.31": "2026-10-24T00:00:00Z",
    }
    fake.uv_result = {"certifi": "2026.10.19"}
    fake.pnpm_result = {"postcss": "8.5.30"}

    assert _main(fake) == 1

    assert capsys.readouterr().err.startswith("ERR_FIXES_UNRESOLVED: postcss")
    assert (fake.root / "pnpm-workspace.yaml").read_text("utf-8") == WORKSPACE
    assert (fake.root / "out" / "title.txt").read_text("utf-8") == (
        "deps: fix security alerts in certifi\n"
    )
    body = (fake.root / "out" / "body.md").read_text("utf-8")
    assert "### Failed in this run" in body
    assert "- `ERR_FIXES_UNRESOLVED`: postcss is still locked at 8.5.30" in body
    assert "postcss" not in body.split("### Failed in this run")[0]


def test_main_drops_an_expired_uv_exception_that_keeps_the_lock(
    make_fake: MakeFake,
) -> None:
    pyproject = security_fixes.uv_add(
        PYPROJECT, "certifi", "2026-10-17T00:00:00Z", ["old"]
    )
    fake = make_fake(uv={"certifi": "2026.10.19"}, pyproject=pyproject)

    assert _main(fake) == 0

    assert (fake.root / "pyproject.toml").read_text("utf-8") == PYPROJECT
    assert ["uv", "lock"] in fake.calls
    assert (fake.root / "out" / "title.txt").read_text("utf-8") == (
        "deps: drop expired release-window exceptions\n"
    )


def test_main_keeps_an_expired_uv_exception_whose_removal_moves_the_lock(
    make_fake: MakeFake, capsys: pytest.CaptureFixture[str]
) -> None:
    pyproject = security_fixes.uv_add(
        PYPROJECT, "certifi", "2026-10-17T00:00:00Z", ["old"]
    )
    fake = make_fake(uv={"certifi": "2026.10.19"}, pyproject=pyproject)
    fake.uv_result = {"certifi": "2026.10.18"}

    assert _main(fake) == 1

    assert capsys.readouterr().err.startswith("ERR_FIXES_EXPIRY: dropping ['certifi']")
    assert (fake.root / "pyproject.toml").read_text("utf-8") == pyproject
    assert security_fixes.uv_locked((fake.root / "uv.lock").read_text("utf-8")) == {
        "certifi": {"2026.10.19"}
    }


def test_main_keeps_an_unexpired_uv_exception(make_fake: MakeFake) -> None:
    pyproject = security_fixes.uv_add(
        PYPROJECT, "certifi", "2026-10-20T02:24:17Z", ["new"]
    )
    fake = make_fake(uv={"certifi": "2026.10.19"}, pyproject=pyproject)

    assert _main(fake) == 0

    assert (fake.root / "pyproject.toml").read_text("utf-8") == pyproject
    assert not (fake.root / "out").exists()


def test_main_excludes_one_pnpm_version_inside_the_window(make_fake: MakeFake) -> None:
    fake = make_fake(pnpm={"@scope/pkg": "1.2.2", "postcss": "8.5.30"})
    fake.alerts = [
        _alert(
            "@scope/pkg", "< 1.2.3", "1.2.3", ecosystem="npm", manifest="pnpm-lock.yaml"
        )
    ]
    fake.published = {"@scope/pkg@1.2.3": "2026-10-24T00:00:00Z"}
    fake.pnpm_result = {"@scope/pkg": "1.2.3"}

    assert _main(fake) == 0

    workspace = (fake.root / "pnpm-workspace.yaml").read_text("utf-8")
    assert security_fixes.pnpm_exceptions(workspace) == ["@scope/pkg@1.2.3"]
    assert [
        "pnpm",
        "update",
        "--recursive",
        "--lockfile-only",
        "--no-save",
        "@scope/pkg",
    ] in fake.calls


def test_main_drops_an_expired_pnpm_exception_when_installs_still_pass(
    make_fake: MakeFake,
) -> None:
    workspace = security_fixes.pnpm_add(WORKSPACE, "postcss@8.5.31", ["old"])
    fake = make_fake(pnpm={"postcss": "8.5.31"}, workspace=workspace)
    fake.published = {"postcss@8.5.31": "2026-10-18T00:00:00Z"}

    assert _main(fake) == 0

    assert (fake.root / "pnpm-workspace.yaml").read_text("utf-8") == WORKSPACE
    assert ["pnpm", "install", "--frozen-lockfile", "--lockfile-only"] in fake.calls


def test_main_restores_a_pnpm_exception_whose_removal_fails_the_install(
    make_fake: MakeFake, capsys: pytest.CaptureFixture[str]
) -> None:
    workspace = security_fixes.pnpm_add(WORKSPACE, "postcss@8.5.31", ["old"])
    fake = make_fake(pnpm={"postcss": "8.5.31"}, workspace=workspace)
    fake.published = {"postcss@8.5.31": "2026-10-18T00:00:00Z"}
    fake.pnpm_install_fails = True

    assert _main(fake) == 1

    assert capsys.readouterr().err.startswith("ERR_FIXES_EXPIRY: the lock fails")
    assert (fake.root / "pnpm-workspace.yaml").read_text("utf-8") == workspace


def test_main_notes_alerts_on_files_it_does_not_handle(
    make_fake: MakeFake, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = make_fake()
    fake.alerts = [
        _alert("lodash", "< 4.17.21", "4.17.21", ecosystem="npm", manifest="x/y")
    ]

    assert _main(fake) == 0

    assert "not a lockfile this workflow handles" in capsys.readouterr().out


def test_main_reports_a_gh_failure(
    make_fake: MakeFake, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = make_fake()
    fake.gh_fails = True

    assert _main(fake) == 1

    assert capsys.readouterr().err.startswith(
        "ERR_FIXES_GH: gh api repos/owner/app/pulls"
    )


def test_main_rejects_a_repo_that_is_not_owner_name(make_fake: MakeFake) -> None:
    fake = make_fake()

    with pytest.raises(SystemExit) as info:
        security_fixes.main(["--out", "x", "--repo", "nope"], root=fake.root)

    assert info.value.code == 2


def test_main_raises_a_target_when_the_relocked_version_has_an_advisory(
    make_fake: MakeFake,
) -> None:
    fake = make_fake(uv={"virtualenv": "21.9.0"})
    fake.alerts = [_alert("virtualenv", "< 21.14.9", "21.14.9")]
    fake.advisories = [
        _advisory("virtualenv", ">= 21.14.9, < 21.14.13", "21.14.13", ghsa="GHSA-cx6f")
    ]
    fake.published = {
        "virtualenv==21.14.9": "2026-10-17T16:09:42Z",
        "virtualenv==21.14.13": "2026-10-22T20:10:16.95Z",
    }
    fake.uv_rounds = [{"virtualenv": "21.14.11"}, {"virtualenv": "21.14.13"}]

    assert _main(fake) == 0

    pyproject = (fake.root / "pyproject.toml").read_text("utf-8")
    assert security_fixes.uv_exceptions(pyproject) == {
        "virtualenv": "2026-10-22T20:10:17Z"
    }
    assert [argv for argv in fake.calls if argv[:2] == ["uv", "lock"]] == [
        ["uv", "lock", "--upgrade-package=virtualenv"],
        ["uv", "lock", "--upgrade-package=virtualenv"],
    ]
    body = (fake.root / "out" / "body.md").read_text("utf-8")
    assert "| `virtualenv` | uv.lock | 21.14.13 |" in body
    assert "[GHSA-cx6f](https://github.com/advisories/GHSA-cx6f) (high)" in body
    assert "exception until 2026-10-29" in body


def test_main_adds_a_package_whose_moved_version_has_an_advisory(
    make_fake: MakeFake,
) -> None:
    fake = make_fake(uv={"certifi": "2026.6.17", "idna": "3.9"})
    fake.alerts = [_alert("certifi", "< 2026.10.19", "2026.10.19")]
    fake.advisories = [_advisory("idna", "= 3.10", "3.11")]
    fake.published = {
        "certifi==2026.10.19": "2026-10-10T00:00:00Z",
        "idna==3.11": "2026-10-01T00:00:00Z",
    }
    fake.uv_rounds = [{"certifi": "2026.10.19", "idna": "3.10"}, {"idna": "3.11"}]

    assert _main(fake) == 0

    assert ["uv", "lock", "--upgrade-package=certifi", "--upgrade-package=idna"] in (
        fake.calls
    )
    assert (fake.root / "out" / "title.txt").read_text("utf-8") == (
        "deps: fix security alerts in certifi, idna\n"
    )


def test_main_fails_when_a_relocked_version_has_an_unpatched_advisory(
    make_fake: MakeFake, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = make_fake(uv={"virtualenv": "21.9.0"})
    fake.alerts = [_alert("virtualenv", "< 21.14.9", "21.14.9")]
    fake.advisories = [_advisory("virtualenv", ">= 21.14.9", None)]
    fake.published = {"virtualenv==21.14.9": "2026-10-17T16:09:42Z"}
    fake.uv_result = {"virtualenv": "21.14.11"}

    assert _main(fake) == 1

    err = capsys.readouterr().err
    assert err.startswith(
        "ERR_FIXES_UNRESOLVED: virtualenv is still locked at 21.14.11"
    )
    assert "has no patched version" in err
    assert security_fixes.uv_locked((fake.root / "uv.lock").read_text("utf-8")) == {
        "virtualenv": {"21.9.0"}
    }


def test_main_gives_up_after_the_advisory_rounds(
    make_fake: MakeFake, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = make_fake(uv={"virtualenv": "1.0"})
    fake.alerts = [_alert("virtualenv", "< 1.1", "1.1")]
    fake.advisories = [
        _advisory("virtualenv", f"= 1.{n}", f"1.{n + 1}", ghsa=f"GHSA-{n}")
        for n in range(1, 9)
    ]
    fake.published = {f"virtualenv==1.{n}": "2026-01-01T00:00:00Z" for n in range(1, 9)}
    fake.uv_rounds = [{"virtualenv": f"1.{n}"} for n in range(1, 9)]

    assert _main(fake) == 1

    assert capsys.readouterr().err.startswith("ERR_FIXES_UNRESOLVED: virtualenv")
    assert len([a for a in fake.calls if a[:2] == ["uv", "lock"]]) == (
        security_fixes.ADVISORY_ROUNDS
    )


def test_main_replaces_a_pnpm_exception_when_the_target_rises(
    make_fake: MakeFake,
) -> None:
    fake = make_fake(pnpm={"postcss": "8.5.30"})
    fake.alerts = [
        _alert(
            "postcss", "< 8.5.31", "8.5.31", ecosystem="npm", manifest="pnpm-lock.yaml"
        )
    ]
    advisory = _advisory("postcss", "= 8.5.31", "8.5.32")
    advisory["vulnerabilities"][0]["package"]["ecosystem"] = "npm"
    fake.advisories = [advisory]
    fake.published = {
        "postcss@8.5.31": "2026-10-24T00:00:00Z",
        "postcss@8.5.32": "2026-10-24T12:00:00Z",
    }
    fake.pnpm_rounds = [{"postcss": "8.5.31"}, {"postcss": "8.5.32"}]

    assert _main(fake) == 0

    workspace = (fake.root / "pnpm-workspace.yaml").read_text("utf-8")
    assert security_fixes.pnpm_exceptions(workspace) == ["postcss@8.5.32"]
