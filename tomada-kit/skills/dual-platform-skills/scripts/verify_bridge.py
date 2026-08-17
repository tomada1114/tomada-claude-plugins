#!/usr/bin/env python3
"""verify_bridge.py — Verify a skill is correctly bridged for both Claude Code and Codex.

Usage:
    verify_bridge.py <real-skill-path> [--codex-link <path>] [--json]

Checks (Topology A):
    V1  real skill is a real directory (not a symlink) with SKILL.md      [error]
    V2  frontmatter has name + description                                [error]
    V3  Codex-incompatible frontmatter fields present (name/description    [warning]
        /metadata only is ideal for Codex)
    V4  body has NO absolute `.claude/...` paths (break under Codex —      [warning]
        use relative intra-skill paths instead)
    V5  cross-skill references to OTHER skills (won't resolve on Codex     [warning]
        unless those are bridged too / inlined)
    V6  a Codex symlink resolves to this real skill                        [warning if none found]
    V7  relative intra-skill links in SKILL.md resolve (also via symlink)  [error if broken]

Looks for Codex symlinks in: $CODEX_HOME/skills (~/.codex/skills) and, if the skill
is inside a git repo, <repo>/.agents/skills — plus any --codex-link you pass.

Exit codes: 0 = no errors (warnings ok), 1 = errors, 2 = bad invocation
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

CODEX_OK_FIELDS = {"name", "description", "metadata"}
ABS_CLAUDE_RE = re.compile(r"(?:^|[\s\(`'\"])((?:~|\$HOME|/)[^\s\)`'\"]*\.claude/[^\s\)`'\"]+)")
CROSS_SKILL_RE = re.compile(r"\.claude/skills/([a-z0-9][a-z0-9-]*)/")
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


@dataclass
class Finding:
    level: str
    code: str
    message: str


@dataclass
class Report:
    skill_path: str
    skill_name: str = ""
    codex_links: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    def add(self, level: str, code: str, msg: str) -> None:
        self.findings.append(Finding(level, code, msg))

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.level == "error"]


def fm_keys_and_required(text: str) -> tuple[list[str], dict[str, str], int]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return [], {}, 0
    keys: list[str] = []
    vals: dict[str, str] = {}
    end = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
        line = lines[i]
        if not line.startswith((" ", "\t")) and ":" in line:
            k = line.split(":", 1)[0].strip()
            if k and not k.startswith("#"):
                keys.append(k)
                vals[k] = line.split(":", 1)[1].strip().strip("\"'")
    return keys, vals, (end + 1 if end != -1 else 0)


def find_codex_links(real: Path, extra: list[str]) -> list[str]:
    """Return symlinks (as strings) that resolve to `real`."""
    candidates: list[Path] = []
    codex_home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    candidates.append(codex_home / "skills")
    try:
        rr = subprocess.run(
            ["git", "-C", str(real), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=False,
        ).stdout.strip()
        if rr:
            candidates.append(Path(rr) / ".agents" / "skills")
    except Exception:
        pass
    found: list[str] = []
    seen: set[str] = set()
    for d in candidates:
        link = d / real.name
        if link.is_symlink() and link.exists():
            try:
                if link.resolve() == real.resolve() and str(link) not in seen:
                    found.append(str(link))
                    seen.add(str(link))
            except OSError:
                pass
    for e in extra:
        p = Path(e).expanduser()
        if p.is_symlink() and p.exists() and p.resolve() == real.resolve() and str(p) not in seen:
            found.append(str(p))
            seen.add(str(p))
    return found


def verify(real: Path, extra_links: list[str]) -> Report:
    r = Report(skill_path=str(real))

    # V1
    if real.is_symlink():
        r.add("error", "V1", "real skill path is a symlink — the real folder must live under .claude/skills/")
        return r
    if not real.is_dir() or not (real / "SKILL.md").exists():
        r.add("error", "V1", "not a skill directory (missing SKILL.md)")
        return r

    text = (real / "SKILL.md").read_text(encoding="utf-8")
    keys, vals, body_start = fm_keys_and_required(text)
    r.skill_name = vals.get("name", real.name)

    # V2
    if not vals.get("name"):
        r.add("error", "V2", "frontmatter missing 'name'")
    if not vals.get("description"):
        r.add("error", "V2", "frontmatter missing 'description'")

    # V3
    extra_fields = [k for k in keys if k not in CODEX_OK_FIELDS]
    if extra_fields:
        r.add("warning", "V3",
              "Codex reads only name/description/metadata; these extra fields are ignored by Codex "
              f"(harmless but keep them Claude-only): {', '.join(extra_fields)}")

    body = "\n".join(text.splitlines()[body_start:])

    # V4 — absolute .claude paths in body
    abs_hits = sorted({m.group(1) for m in ABS_CLAUDE_RE.finditer(body)})
    if abs_hits:
        r.add("warning", "V4",
              "absolute .claude/ paths break under Codex; rewrite intra-skill refs as relative: "
              + ", ".join(abs_hits[:6]) + (" …" if len(abs_hits) > 6 else ""))

    # V5 — cross-skill refs
    cross = sorted({m.group(1) for m in CROSS_SKILL_RE.finditer(body) if m.group(1) != r.skill_name})
    if cross:
        r.add("warning", "V5",
              "references other skills (bridge or inline them for Codex): " + ", ".join(cross))

    # V7 — relative link integrity
    for m in LINK_RE.finditer(body):
        tgt = m.group(1).split("#", 1)[0]
        if not tgt or tgt.startswith(("http://", "https://", "mailto:", "/")):
            continue
        if not (real / tgt).exists():
            r.add("error", "V7", f"broken relative link: {tgt}")

    # V6 — codex symlink presence
    r.codex_links = find_codex_links(real, extra_links)
    if not r.codex_links:
        r.add("warning", "V6",
              "no Codex symlink found yet (run bridge_symlink.sh to create one)")

    return r


def render_human(r: Report) -> str:
    out = [f"Bridge check: {r.skill_name}  ({r.skill_path})"]
    out.append("  Codex links: " + (", ".join(r.codex_links) if r.codex_links else "(none)"))
    if not r.findings:
        out.append("  OK — fully bridged, no issues.")
        return "\n".join(out)
    for lvl in ("error", "warning", "info"):
        items = [f for f in r.findings if f.level == lvl]
        if items:
            out.append(f"  {lvl.upper()}S:")
            out.extend(f"    {f.code}: {f.message}" for f in items)
    return "\n".join(out)


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__, file=sys.stderr)
        return 2
    extra = [argv[i + 1] for i, a in enumerate(argv) if a == "--codex-link" and i + 1 < len(argv)]
    real = Path(argv[1]).expanduser().resolve()
    r = verify(real, extra)
    if "--json" in argv:
        print(json.dumps(asdict(r), indent=2, ensure_ascii=False))
    else:
        print(render_human(r))
    return 1 if r.errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
