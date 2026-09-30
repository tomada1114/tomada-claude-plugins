#!/usr/bin/env python3
"""Detect a repository's development toolchain and propose Claude Code permission rules.

Reads marker files only (no network, no builds). The proposal is deliberately loose:
one wildcard allow rule per detected tool, ask rules for publish-style subcommands and
for task-runner recipes whose names suggest they act on the machine or on GitHub. The
calling agent reviews the proposal against the repository's own policy before merging.

Exit codes: 0 detected, 1 nothing recognized, 2 bad invocation.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Sequence

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
    r"bootstrap|clean.*|reset.*|nuke|logs-follow|notari[sz]e.*|sign.*|upload.*|tag.*)$"
)

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
    allow: list[str] = field(default_factory=list)
    ask: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    existing: dict[str, list[str]] = field(default_factory=dict)


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


def detect(root: Path, run: Callable[[Sequence[str]], str | None] = default_run) -> Detection:
    det = Detection(root=str(root))
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
    runner = "just" if "just" in det.tools else "make" if "make" in det.tools else None
    allow, ask, domains = list(BASELINE_ALLOW), list(BASELINE_ASK), list(BASELINE_DOMAINS)
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
    det.allow = list(dict.fromkeys(allow))
    det.ask = list(dict.fromkeys(ask))
    det.domains = list(dict.fromkeys(domains))
    det.allow += [f"WebFetch(domain:{d})" for d in det.domains]

    settings = root / ".claude" / "settings.json"
    if settings.exists():
        try:
            perms = json.loads(_read(settings)).get("permissions", {})
            det.existing = {k: list(perms.get(k, [])) for k in ("allow", "ask", "deny")}
        except (json.JSONDecodeError, AttributeError):
            det.existing = {}
    return det


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root", help="repository root")
    ap.add_argument("--json", action="store_true", help="print the detection as JSON")
    args = ap.parse_args(argv)
    root = Path(args.root)
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2
    det = detect(root)
    if args.json:
        print(json.dumps(asdict(det), ensure_ascii=False, indent=2))
    else:
        for tool in det.tools:
            print(f"{tool:12} {det.evidence[tool]}")
        if det.human_candidates:
            print("human-only candidates:", ", ".join(det.human_candidates))
        print(f"proposed: {len(det.allow)} allow, {len(det.ask)} ask")
    return 0 if det.tools else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
