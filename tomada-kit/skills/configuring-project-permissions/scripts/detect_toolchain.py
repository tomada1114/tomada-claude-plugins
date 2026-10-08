#!/usr/bin/env python3
"""Detect a repository's development toolchain and propose Claude Code permission rules.

Reads marker files only (no network, no builds). The proposal is deliberately loose:
one wildcard allow rule per detected tool, ask rules for publish-style subcommands and
for task-runner recipes whose names suggest they act on the machine or on GitHub. The
calling agent reviews the proposal against the repository's own policy before merging.

The proposal is split by destination. Generic rules (git, gh, coreutils, GitHub docs) are
`global_candidates` for the user-level ~/.claude/settings.json and are never proposed for
the project. Project rules go to the gitignored .claude/settings.local.json; any a
user-level rule already covers is dropped (`covered_by_global`), and a project allow a
user-level ask/deny would stop anyway is dropped too (`blocked_by_global`), because
Claude Code evaluates deny, then ask, then allow across every settings file.

Exit codes: 0 detected, 1 nothing recognized, 2 bad invocation or unreadable global
settings.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Sequence

from rule_match import first_cover, load_permissions

# tool -> (allow rules, ask rules, docs domains)
TOOL_RULES: dict[str, tuple[list[str], list[str], list[str]]] = {
    "just": (["Bash(just *)"], [], []),
    "make": (["Bash(make *)"], [], []),
    "mise": (["Bash(mise install *)", "Bash(mise trust *)", "Bash(mise ls *)", "Bash(mise run *)",
              "Bash(mise which *)", "Bash(mise current *)"], [], ["mise.jdx.dev"]),
    "pnpm": (["Bash(pnpm *)", "Bash(node *)"], ["Bash(pnpm publish *)"],
             ["nodejs.org", "www.npmjs.com", "registry.npmjs.org"]),
    "npm": (["Bash(npm *)", "Bash(npx *)", "Bash(node *)"], ["Bash(npm publish *)"],
            ["nodejs.org", "www.npmjs.com", "registry.npmjs.org"]),
    "yarn": (["Bash(yarn *)", "Bash(node *)"], ["Bash(yarn publish *)", "Bash(yarn npm publish *)"],
             ["nodejs.org", "www.npmjs.com", "yarnpkg.com"]),
    "bun": (["Bash(bun *)", "Bash(bunx *)"], ["Bash(bun publish *)"], ["bun.sh"]),
    "cargo": (["Bash(cargo *)", "Bash(rustup *)", "Bash(rustc *)"], ["Bash(cargo publish *)"],
              ["docs.rs", "crates.io", "doc.rust-lang.org"]),
    "uv": (["Bash(uv *)", "Bash(uvx *)", "Bash(python *)", "Bash(python3 *)"], ["Bash(uv publish *)"],
           ["docs.python.org", "pypi.org", "docs.astral.sh"]),
    "python": (["Bash(python *)", "Bash(python3 *)", "Bash(pip *)", "Bash(pytest *)"], [],
               ["docs.python.org", "pypi.org"]),
    "go": (["Bash(go *)", "Bash(gofmt *)"], [], ["pkg.go.dev", "go.dev"]),
    "swift": (["Bash(swift *)", "Bash(xcodebuild *)", "Bash(xcrun *)"],
              ["Bash(xcrun notarytool *)", "Bash(xcrun altool *)"],
              ["developer.apple.com", "swift.org", "swiftpackageindex.com"]),
    "xcodegen": (["Bash(xcodegen *)"], [], []),
    "tauri": ([], [], ["v2.tauri.app", "tauri.app"]),
    "next": ([], [], ["nextjs.org", "react.dev", "vercel.com"]),
    "tailwind": ([], [], ["tailwindcss.com"]),
    "shadcn": ([], [], ["ui.shadcn.com"]),
    "vite": ([], [], ["vite.dev", "vitest.dev"]),
    "docker": (["Bash(docker compose *)", "Bash(docker ps *)", "Bash(docker logs *)",
                "Bash(docker images *)"], [], ["docs.docker.com"]),
    "lefthook": (["Bash(lefthook run *)", "Bash(lefthook install *)", "Bash(lefthook version *)"], [], []),
    "typos": (["Bash(typos *)"], [], []),
    "gitleaks": (["Bash(gitleaks *)"], [], []),
    "osv-scanner": (["Bash(osv-scanner *)"], [], []),
    "zizmor": (["Bash(zizmor *)"], [], []),
    "actionlint": (["Bash(actionlint *)"], [], []),
    "shellcheck": (["Bash(shellcheck *)"], [], []),
    "swiftlint": (["Bash(swiftlint *)"], [], []),
    "swiftformat": (["Bash(swiftformat *)"], [], []),
    "prettier": ([], [], ["prettier.io"]),
    "eslint": ([], [], ["eslint.org"]),
}

BASELINE_ALLOW = [
    "Bash(git *)", "Bash(gh issue *)", "Bash(gh pr *)", "Bash(gh run *)", "Bash(gh workflow view *)",
    "Bash(gh workflow list *)", "Bash(gh label list *)", "Bash(gh repo view *)", "Bash(gh search *)",
    "Bash(rg *)", "Bash(fd *)", "Bash(jq *)", "Bash(yq *)", "Bash(tree *)", "Bash(diff *)",
    "Bash(chmod +x *)", "WebSearch",
]
BASELINE_ASK = ["Bash(gh issue delete *)", "Bash(gh repo delete *)", "Bash(gh release create *)",
                "Bash(gh repo edit *)"]
BASELINE_DOMAINS = ["github.com", "raw.githubusercontent.com", "docs.github.com", "code.claude.com"]

# Recipe/script names that usually act on the developer's machine, on GitHub, or on a release.
HUMAN_RECIPE_RE = re.compile(
    r"^(run|dev|start|serve|open|install-app|uninstall|release.*|publish.*|deploy.*|labels?|ruleset|"
    r"bootstrap|reset.*|logs-follow|notari[sz]e.*|sign.*|upload.*|tag.*)$"
)

CLEANUP_RECIPE_RE = re.compile(r"^(clean.*|prune.*|nuke)$")

JUST_RECIPE_RE = re.compile(r"^(?:@)?([A-Za-z_][\w-]*)(?:\s+[^:=]*)?:(?!=)", re.MULTILINE)
MAKE_TARGET_RE = re.compile(r"^([A-Za-z_][\w.-]*)\s*:(?!=)", re.MULTILINE)


@dataclass
class Detection:
    root: str
    tools: list[str] = field(default_factory=list)
    evidence: dict[str, str] = field(default_factory=dict)
    recipes: list[str] = field(default_factory=list)
    package_scripts: list[str] = field(default_factory=list)
    human_candidates: list[str] = field(default_factory=list)
    cleanup_recipes: list[str] = field(default_factory=list)
    allow: list[str] = field(default_factory=list)
    ask: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    global_candidates: dict[str, list[str]] = field(default_factory=dict)
    covered_by_global: list[dict[str, str]] = field(default_factory=list)
    blocked_by_global: list[dict[str, str]] = field(default_factory=list)
    existing: dict[str, dict[str, list[str]]] = field(default_factory=dict)
    committed_hooks: bool = False
    ignored: dict[str, bool | None] = field(default_factory=dict)
    codex: dict[str, object] = field(default_factory=dict)


def _add(det: Detection, tool: str, why: str) -> None:
    if tool not in det.tools:
        det.tools.append(tool)
        det.evidence[tool] = why


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def just_recipes(root: Path, run: Callable[[Sequence[str]], str | None]) -> list[str]:
    out = run(["just", "--justfile", str(root / "justfile"), "--summary"]) if shutil.which("just") else None
    if out:
        return out.split()
    text = _read(root / "justfile") or _read(root / "Justfile")
    names = [m.group(1) for m in JUST_RECIPE_RE.finditer(text)]
    return [n for n in dict.fromkeys(names) if n not in ("set", "export", "import", "mod", "alias")]


def default_run(cmd: Sequence[str]) -> str | None:
    try:
        p = subprocess.run(list(cmd), capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return p.stdout if p.returncode == 0 else None


def default_check(cmd: Sequence[str]) -> int | None:
    """Return code of `cmd`, or None when it cannot run."""
    try:
        return subprocess.run(list(cmd), capture_output=True, text=True, timeout=20).returncode
    except (OSError, subprocess.TimeoutExpired):
        return None


def is_ignored(root: Path, rel: str, check: Callable[[Sequence[str]], int | None]) -> bool | None:
    code = check(["git", "-C", str(root), "check-ignore", "-q", rel])
    return {0: True, 1: False}.get(code) if code is not None else None


def codex_state(root: Path, codex_home: Path | None) -> dict[str, object]:
    config = (codex_home / "config.toml") if codex_home else None
    trusted: bool | None = None
    if config and config.is_file():
        try:
            data = tomllib.loads(config.read_text(encoding="utf-8"))
            entry = (data.get("projects") or {}).get(str(root.resolve())) or {}
            trusted = isinstance(entry, dict) and entry.get("trust_level") == "trusted"
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError, AttributeError):
            trusted = None
    return {"trusted": trusted, "local_rules": (root / ".codex/rules/local.rules").is_file(),
            "config": str(config) if config else ""}


def _settings(path: Path) -> tuple[dict[str, list[str]], bool]:
    try:
        perms = load_permissions(path)
    except ValueError:
        return {}, False
    try:
        data = json.loads(_read(path) or "{}")
    except json.JSONDecodeError:
        data = {}
    return perms, bool(isinstance(data, dict) and data.get("hooks"))


def detect(root: Path, run: Callable[[Sequence[str]], str | None] = default_run,
           global_path: Path | None = None, codex_home: Path | None = None,
           check: Callable[[Sequence[str]], int | None] = default_check) -> Detection:
    """Detect `root`'s toolchain. `global_path` None means no user-level settings."""
    det = Detection(root=str(root))
    glob_perms = load_permissions(global_path) if global_path else {k: [] for k in ("allow", "ask", "deny")}
    exists = lambda *names: next((n for n in names if (root / n).exists()), None)  # noqa: E731

    if f := exists("justfile", "Justfile"):
        _add(det, "just", f)
        det.recipes = just_recipes(root, run)
    if f := exists("Makefile"):
        _add(det, "make", f)
        det.recipes += [t for t in dict.fromkeys(MAKE_TARGET_RE.findall(_read(root / f)))
                        if not t.startswith(".") and t not in det.recipes]
    if f := exists("mise.toml", ".mise.toml", ".tool-versions"):
        _add(det, "mise", f)

    pkg_text = _read(root / "package.json")
    if pkg_text:
        try:
            pkg = json.loads(pkg_text)
        except json.JSONDecodeError:
            pkg = {}
        manager = str(pkg.get("packageManager", "")).split("@")[0]
        lock = exists("pnpm-lock.yaml", "bun.lockb", "bun.lock", "yarn.lock", "package-lock.json")
        by_lock = {"pnpm-lock.yaml": "pnpm", "bun.lockb": "bun", "bun.lock": "bun",
                   "yarn.lock": "yarn", "package-lock.json": "npm"}
        tool = manager if manager in ("pnpm", "npm", "yarn", "bun") else by_lock.get(lock or "", "npm")
        _add(det, tool, f"package.json ({'packageManager' if manager else lock or 'default'})")
        det.package_scripts = list((pkg.get("scripts") or {}).keys())
        deps = {**(pkg.get("dependencies") or {}), **(pkg.get("devDependencies") or {})}
        for dep, t in (("next", "next"), ("@tauri-apps/api", "tauri"), ("@tauri-apps/cli", "tauri"),
                       ("tailwindcss", "tailwind"), ("vite", "vite"), ("vitest", "vite"),
                       ("prettier", "prettier"), ("eslint", "eslint"), ("lefthook", "lefthook")):
            if dep in deps:
                _add(det, t, f"package.json dependency {dep}")
    if f := exists("components.json"):
        _add(det, "shadcn", f)
    if f := exists("Cargo.toml", "src-tauri/Cargo.toml"):
        _add(det, "cargo", f)
    if f := exists("src-tauri/tauri.conf.json"):
        _add(det, "tauri", f)
    if f := exists("uv.lock"):
        _add(det, "uv", f)
    elif f := exists("pyproject.toml", "requirements.txt", "setup.py"):
        _add(det, "uv" if "[tool.uv]" in _read(root / f) else "python", f)
    if f := exists("go.mod"):
        _add(det, "go", f)
    xcode = next(iter(sorted(root.glob("*.xcodeproj"))), None)
    if f := exists("Package.swift") or (xcode.name if xcode else None):
        _add(det, "swift", f)
    if f := exists("project.yml"):
        if "targets:" in _read(root / f):
            _add(det, "xcodegen", f)
    if f := exists("compose.yaml", "compose.yml", "docker-compose.yml", "docker-compose.yaml"):
        _add(det, "docker", f)
    for marker, tool in (("lefthook.yml", "lefthook"), ("typos.toml", "typos"), (".gitleaksignore", "gitleaks"),
                         (".gitleaks.toml", "gitleaks"), ("osv-scanner.toml", "osv-scanner"),
                         (".github/zizmor.yml", "zizmor"), (".swiftlint.yml", "swiftlint"),
                         (".swiftformat", "swiftformat")):
        if (root / marker).exists():
            _add(det, tool, marker)
    if (root / ".github/workflows").is_dir():
        _add(det, "actionlint", ".github/workflows/")
    if list(root.glob("scripts/*.sh")):
        _add(det, "shellcheck", "scripts/*.sh")

    det.human_candidates = [r for r in dict.fromkeys(det.recipes + det.package_scripts) if HUMAN_RECIPE_RE.match(r)]
    det.cleanup_recipes = [r for r in dict.fromkeys(det.recipes + det.package_scripts)
                           if CLEANUP_RECIPE_RE.match(r)]
    runner = "just" if "just" in det.tools else "make" if "make" in det.tools else None
    allow: list[str] = []
    ask: list[str] = []
    domains: list[str] = []
    for tool in det.tools:
        a, k, d = TOOL_RULES.get(tool, ([], [], []))
        allow += a
        ask += k
        domains += d
    for name in det.human_candidates:
        if name in det.recipes and runner:
            ask.append(f"Bash({runner} {name}*)")
        pm = next((t for t in ("pnpm", "npm", "yarn", "bun") if t in det.tools), None)
        if name in det.package_scripts and pm:
            ask += [f"Bash({pm} {name}*)", f"Bash({pm} run {name}*)"]
    if "mise" in det.tools:
        allow += [f"Bash(mise exec -- {t} *)" for t in det.tools if TOOL_RULES.get(t, ([],))[0] and t != "mise"]
    det.domains = list(dict.fromkeys(domains))
    allow += [f"WebFetch(domain:{d})" for d in det.domains]
    scripts = root / "scripts"
    if scripts.is_dir() and any(p.is_file() and (p.suffix == ".sh" or os.access(p, os.X_OK))
                                for p in scripts.iterdir()):
        allow.append("Bash(scripts/*)")
    if any(p.is_dir() for p in root.glob(".agents/skills/*/scripts")):
        allow += ["Bash(.agents/skills/*/scripts/*)", "Bash(bash .agents/skills/*/scripts/*)"]

    g_allow, g_stop = glob_perms["allow"], glob_perms["deny"] + glob_perms["ask"]
    for rule in dict.fromkeys(allow):
        if by := first_cover(rule, glob_perms["deny"]) or first_cover(rule, glob_perms["ask"]):
            kind = "deny" if by in glob_perms["deny"] else "ask"
            det.blocked_by_global.append({"rule": rule, "by": by, "kind": kind})
        elif by := first_cover(rule, g_allow):
            det.covered_by_global.append({"rule": rule, "by": by})
        else:
            det.allow.append(rule)
    for rule in dict.fromkeys(ask):
        if by := first_cover(rule, g_stop):
            det.covered_by_global.append({"rule": rule, "by": by})
        else:
            det.ask.append(rule)

    base_allow = BASELINE_ALLOW + [f"WebFetch(domain:{d})" for d in BASELINE_DOMAINS]
    det.global_candidates = {
        "allow": [r for r in base_allow if not first_cover(r, g_allow)],
        "ask": [r for r in BASELINE_ASK if not first_cover(r, g_stop)],
        "domains": [d for d in BASELINE_DOMAINS if not first_cover(f"WebFetch(domain:{d})", g_allow)],
    }

    local, _ = _settings(root / ".claude" / "settings.local.json")
    committed, det.committed_hooks = _settings(root / ".claude" / "settings.json")
    det.existing = {"local": local, "committed": committed}
    det.ignored = {rel: is_ignored(root, rel, check)
                   for rel in (".claude/settings.local.json", ".codex/rules/local.rules")}
    det.codex = codex_state(root, codex_home)
    return det


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root", help="repository root")
    ap.add_argument("--json", action="store_true", help="print the detection as JSON")
    ap.add_argument("--global", dest="global_path", default="~/.claude/settings.json",
                    help="user-level Claude Code settings (default: ~/.claude/settings.json)")
    ap.add_argument("--no-global", action="store_true", help="ignore user-level settings")
    ap.add_argument("--codex-home", default=os.environ.get("CODEX_HOME") or "~/.codex",
                    help="Codex CLI home (default: $CODEX_HOME or ~/.codex)")
    args = ap.parse_args(argv)
    root = Path(args.root)
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2
    global_path = None if args.no_global else Path(args.global_path).expanduser()
    try:
        det = detect(root, global_path=global_path, codex_home=Path(args.codex_home).expanduser())
    except ValueError as e:
        print(f"error: cannot read global settings: {e}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(asdict(det), ensure_ascii=False, indent=2))
    else:
        for tool in det.tools:
            print(f"{tool:12} {det.evidence[tool]}")
        if det.human_candidates:
            print("human-only candidates:", ", ".join(det.human_candidates))
        if det.cleanup_recipes:
            print("cleanup recipes:", ", ".join(det.cleanup_recipes))
        print(f"proposed: {len(det.allow)} allow, {len(det.ask)} ask")
        gc = det.global_candidates
        print(f"global candidates: {len(gc['allow'])} allow, {len(gc['ask'])} ask")
        print(f"covered by global: {len(det.covered_by_global)}, blocked by global: {len(det.blocked_by_global)}")
        for b in det.blocked_by_global:
            print(f"  blocked: {b['rule']} by {b['kind']} {b['by']}")
        print("ignored: " + ", ".join(f"{k}={v}" for k, v in det.ignored.items()))
        print(f"codex: trusted={det.codex['trusted']}, local_rules={det.codex['local_rules']}, "
              f"config={det.codex['config']}")
    return 0 if det.tools else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
