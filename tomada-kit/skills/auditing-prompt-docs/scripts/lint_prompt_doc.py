#!/usr/bin/env python3
"""Flag prompt-wording anti-patterns in instruction documents.

Checks Markdown documents that act as prompts (SKILL.md, CLAUDE.md, AGENTS.md,
agent and command definitions) against Anthropic's published prompting guidance
for current Claude models. Detection only -- this script never edits a file.

See references/rules.md for the full rationale and rewrite examples behind each
rule id.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

SEVERITIES = ("info", "warn", "error")

# Filenames treated as prompt documents when a directory is scanned.
SKILL_FILES = {"SKILL.md"}
MEMORY_FILES = {"CLAUDE.md", "AGENTS.md"}
# Directory names whose *.md files are agent or command definitions.
AGENT_DIRS = {"agents", "subagents"}
COMMAND_DIRS = {"commands"}
# Reference files bundled with a skill are loaded into context on demand, so they
# carry the same wording rules as the body that points at them.
REFERENCE_DIRS = {"references"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}

IGNORE_FILE_RE = re.compile(r"prompt-lint-ignore-file:\s*([A-Za-z0-9,\s]+)")
IGNORE_LINE_RE = re.compile(r"prompt-lint-ignore:\s*([A-Za-z0-9,\s]+)")


def classify(path: Path) -> str:
    """Return the document kind, which selects size budgets and the file filter."""
    name = path.name
    if name in SKILL_FILES:
        return "skill"
    if name in MEMORY_FILES:
        return "memory"
    parents = {p.name for p in path.parents}
    if parents & AGENT_DIRS:
        return "agent"
    if parents & COMMAND_DIRS:
        return "command"
    if parents & REFERENCE_DIRS:
        return "reference"
    return "other"


@dataclass
class Finding:
    rule: str
    name: str
    severity: str
    file: str
    line: int
    match: str
    why: str
    fix: str


@dataclass
class LineRule:
    """A rule that fires on a single line matching any of its patterns."""

    id: str
    name: str
    severity: str
    why: str
    fix: str
    patterns: list[str]
    regexes: list[re.Pattern[str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.regexes = [re.compile(p, re.IGNORECASE) for p in self.patterns]

    def scan(self, line: str) -> str | None:
        for rx in self.regexes:
            m = rx.search(line)
            if m:
                return m.group(0).strip()
        return None


LINE_RULES: list[LineRule] = [
    LineRule(
        id="P001",
        name="forced-verification",
        severity="warn",
        why="Current models self-verify; an added re-check causes over-verification, not accuracy.",
        fix="Delete it. If you need evidence, ask for the commands run and their output.",
        patterns=[
            r"\b(double[-\s]?check|re-?verify|re-?check)\b",
            r"\bverify\s+(your|its|the)\s+(own\s+)?(answer|work|output|response|result)\b",
            r"\bfinal\s+verification\s+(step|pass|phase)\b",
            r"\bbefore\s+(responding|answering|finishing)[^.\n]{0,40}\b(verify|confirm|validate)\b",
        ],
    ),
    LineRule(
        id="P002",
        name="severity-self-filtering",
        severity="error",
        why="Models follow this literally: they investigate fully, then suppress findings. Recall collapses.",
        fix="Ask for coverage with a confidence and severity on each finding; filter in a later phase.",
        patterns=[
            r"\bonly\s+report\b[^.\n]{0,60}\b(high|critical|severe|important|major|significant)\b",
            r"\bbe\s+conservative\b",
            r"\b(do\s+not|don'?t)\s+nitpick\b",
            r"\bavoid\s+nitpick",
            r"\b(skip|ignore|omit)\s+(minor|low[-\s]severity|trivial|small)\s+(issues|findings|bugs)\b",
            r"\bhigh[-\s]severity\s+(issues\s+)?only\b",
        ],
    ),
    LineRule(
        id="P003",
        name="reasoning-echo",
        severity="error",
        why="Asking the model to reproduce its own reasoning can trigger a refusal category and a model fallback.",
        fix="Ask for evidence instead: file:line citations, command output, or the artifact itself.",
        patterns=[
            r"\bshow\s+(your|the)\s+(reasoning|thought\s+process|thinking|work)\b",
            r"\bexplain\s+how\s+you\s+(arrived|got|reached)\b",
            r"\bwrite\s+out\s+your\s+(thinking|thought\s+process|reasoning)\b",
            r"\bnarrate\s+your\s+(reasoning|thinking|thought)\b",
            r"\bthink\s+out\s+loud\b",
            r"\boutput\s+your\s+(chain[-\s]of[-\s]thought|internal\s+reasoning)\b",
        ],
    ),
    LineRule(
        id="P004",
        name="emphasis-shouting",
        severity="warn",
        why="Current models respond to plain phrasing; shouted emphasis overtriggers the behavior it guards.",
        fix="Drop the emphasis and state the condition: 'Use this tool when ...'.",
        patterns=[
            r"(?:^|[^\w])(CRITICAL|IMPORTANT|MANDATORY|ATTENTION|URGENT|WARNING)\s*[:：]",
            r"\bYou\s+MUST\b",
            r"\bMUST\s+ALWAYS\b",
            r"\bNEVER\s+EVER\b",
            r"\bABSOLUTELY\s+(MUST|NEVER)\b",
        ],
    ),
    LineRule(
        id="P005",
        name="tool-overtrigger",
        severity="warn",
        why="Tools that undertriggered on older models now trigger appropriately; blanket defaults overtrigger them.",
        fix="Name the condition: 'Use [tool] when it would improve your understanding of the problem.'",
        patterns=[
            r"\b(if|when)\s+in\s+doubt,?\s*(use|call|invoke|run|reach\s+for)\b",
            r"\bdefault\s+to\s+(using|calling|invoking)\b",
            r"\balways\s+use\s+the\b[^.\n]{0,30}\btool\b",
            r"\byou\s+must\s+(use|call|invoke)\b[^.\n]{0,30}\b(tool|skill)\b",
        ],
    ),
    LineRule(
        id="P006",
        name="fixed-progress-scaffolding",
        severity="warn",
        why="Progress updates are already well calibrated; fixed cadence scaffolding fights that and adds noise.",
        fix="Delete it. If the shape of the updates is wrong, show one example of the update you want.",
        patterns=[
            r"\bafter\s+every\s+\d+\s+(tool\s+calls|steps|actions)\b",
            r"\bevery\s+\d+\s+(tool\s+calls|steps)\b[^.\n]{0,40}\b(summar|report|update)",
            r"\b(provide|give|post)\s+a\s+(status|progress)\s+update\s+every\b",
        ],
    ),
    LineRule(
        id="P008",
        name="blanket-thoroughness",
        severity="info",
        why="A standing thoroughness order invites scope expansion, which current models already do unprompted.",
        fix="Say what 'done' is. Ask for maximal coverage only on the one task that needs it.",
        patterns=[
            r"\bgo\s+above\s+and\s+beyond\b",
            r"\bbe\s+(extremely\s+|very\s+|as\s+)?thorough\b",
            r"\bleave\s+no\s+stone\s+unturned\b",
            r"\bexhaustively\s+(search|explore|analy[sz]e|review)\b",
        ],
    ),
    LineRule(
        id="P009",
        name="open-ended-delegation",
        severity="warn",
        why="Current models delegate readily; an open-ended nudge spawns sub-agents for work one search would finish.",
        fix="State when delegation is and is not warranted, and cap the spawn count.",
        patterns=[
            r"\buse\s+sub-?agents?\s+(whenever|liberally|freely|as\s+much|aggressively)\b",
            r"\bdelegate\s+(whenever|liberally|freely|aggressively)\b",
            r"\bspawn\s+(as\s+many|multiple)\s+(sub-?agents?|agents)\b",
        ],
    ),
    LineRule(
        id="P010",
        name="legacy-api",
        severity="error",
        why="Manual thinking budgets and assistant prefills return 400 on current models.",
        fix="Use adaptive thinking with the effort parameter; replace prefills with structured outputs or a direct instruction.",
        patterns=[
            r"\bbudget_tokens\b",
            r"\bthinking\s*[:=]\s*\{?\s*[\"']?type[\"']?\s*[:=]\s*[\"']enabled[\"']",
            r"\bprefill(ed)?\s+(assistant\s+)?(response|message|turn)\b",
            r"\bassistant\s+prefill\b",
        ],
    ),
    LineRule(
        id="P011",
        name="sampling-params",
        severity="warn",
        why="Sonnet 5 returns 400 for a non-default temperature, top_p, or top_k.",
        fix="Remove the parameter and steer tone or variety from the prompt instead.",
        patterns=[r"\b(temperature|top_p|top_k)\s*[:=]\s*[0-9]"],
    ),
    LineRule(
        id="P012",
        name="negative-formatting-rule",
        severity="warn",
        why="Prohibitions steer formatting weakly, and on models that already format sparsely they suppress needed structure.",
        fix="Describe the output you want ('flowing prose paragraphs'), or say when each element is appropriate.",
        patterns=[
            r"\b(do\s+not|don'?t|never)\s+use\s+(markdown|bullets?|bullet\s+points|lists?|headers?|emoji)\b",
            r"\bno\s+(bullet\s+points|markdown|lists|headers)\b",
            r"\bavoid\s+(using\s+)?(markdown|bullet\s+points|lists)\b",
        ],
    ),
    LineRule(
        id="P013",
        name="narration-suppression",
        severity="warn",
        why="Written for models that over-narrated; on current models it produces silent runs users cannot follow.",
        fix="Remove it, then state when you want user-facing text and what each update should contain.",
        patterns=[
            r"\bhold\s+(all\s+)?(findings|updates|comments)\b[^.\n]{0,40}\bfinal\b",
            r"\b(do\s+not|don'?t|never)\s+(narrate|provide\s+(progress\s+)?updates|comment\s+on\s+your)\b",
            r"\bno\s+(running\s+)?commentary\b",
            r"\bwithout\s+(any\s+)?commentary\b",
        ],
    ),
]

# P007 fires only on a sustained pattern, not a single clause: a document needs
# both an absolute count and a share of its lines before prohibition-by-listing
# is the document's actual style.
NEGATIVE_CLAUSE_RE = re.compile(
    r"\b(do\s+not|don'?t|never|must\s+not|avoid|refrain\s+from)\b", re.IGNORECASE
)
NEGATIVE_MIN_COUNT = 12
NEGATIVE_MIN_RATIO = 0.15

# Body-line budgets by document kind: (warn, error). A memory file is re-read
# into every session, so its budget is tighter than a reference document's.
SIZE_BUDGETS = {
    "skill": (200, 500),
    "memory": (200, 400),
    "agent": (200, 400),
    "command": (150, 300),
    "reference": (400, 800),
    "other": (400, 800),
}

# Below this length a repeated line is boilerplate (a heading, "See above"),
# not a duplicated directive.
DUPLICATE_MIN_CHARS = 40


def parse_ignores(text: str, regex: re.Pattern[str]) -> set[str]:
    out: set[str] = set()
    for m in regex.finditer(text):
        for token in m.group(1).replace(",", " ").split():
            out.add(token.upper())
    return out


def strip_frontmatter(lines: list[str]) -> tuple[list[str], int]:
    """Return (body lines, 1-based line number of the first body line)."""
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return lines[i + 1 :], i + 2
    return lines, 1


def normalize(line: str) -> str:
    s = line.strip().lower()
    s = re.sub(r"^[-*+>]\s+|^\d+[.)]\s+", "", s)
    s = re.sub(r"[`*_#\[\]()]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip(" .,:;")


def lint_text(text: str, path_label: str, kind: str) -> list[Finding]:
    """Return every finding for one document. Pure: takes text, returns data."""
    file_ignores = parse_ignores(text, IGNORE_FILE_RE)
    lines = text.splitlines()
    findings: list[Finding] = []

    def suppressed(rule_id: str, idx: int) -> bool:
        if "ALL" in file_ignores or rule_id in file_ignores:
            return True
        for probe in (idx, idx - 1):
            if 0 <= probe < len(lines):
                if rule_id in parse_ignores(lines[probe], IGNORE_LINE_RE):
                    return True
        return False

    for idx, line in enumerate(lines):
        if IGNORE_LINE_RE.search(line) or IGNORE_FILE_RE.search(line):
            continue
        for rule in LINE_RULES:
            if suppressed(rule.id, idx):
                continue
            hit = rule.scan(line)
            if hit:
                findings.append(
                    Finding(
                        rule=rule.id,
                        name=rule.name,
                        severity=rule.severity,
                        file=path_label,
                        line=idx + 1,
                        match=hit[:120],
                        why=rule.why,
                        fix=rule.fix,
                    )
                )

    body, offset = strip_frontmatter(lines)
    content = [ln for ln in body if ln.strip()]

    if not suppressed("P007", 0):
        negatives = sum(1 for ln in content if NEGATIVE_CLAUSE_RE.search(ln))
        if content and negatives >= NEGATIVE_MIN_COUNT:
            ratio = negatives / len(content)
            if ratio >= NEGATIVE_MIN_RATIO:
                findings.append(
                    Finding(
                        rule="P007",
                        name="negative-enumeration-density",
                        severity="info",
                        file=path_label,
                        line=offset,
                        match=f"{negatives} prohibition clauses across {len(content)} lines",
                        why="A long list of prohibitions steers more weakly than one positive example, and every clause costs context.",
                        fix="Replace the longest runs with one or two examples of the output you do want.",
                    )
                )

    if not suppressed("D001", 0):
        warn_at, error_at = SIZE_BUDGETS.get(kind, SIZE_BUDGETS["other"])
        n = len(body)
        if n > warn_at:
            findings.append(
                Finding(
                    rule="D001",
                    name="doc-size-budget",
                    severity="error" if n > error_at else "warn",
                    file=path_label,
                    line=offset,
                    match=f"{n} body lines (budget {warn_at} for a {kind} document)",
                    why="This text is re-read into context on every run, so length is a recurring cost.",
                    fix="Keep the decisions and the hard rules; move rationale, examples, and single-branch detail into a reference file.",
                )
            )

    if not suppressed("D002", 0):
        seen: dict[str, int] = {}
        for i, raw in enumerate(body):
            if raw.lstrip().startswith("#"):
                continue
            norm = normalize(raw)
            if len(norm) < DUPLICATE_MIN_CHARS:
                continue
            if norm in seen:
                findings.append(
                    Finding(
                        rule="D002",
                        name="duplicate-directive",
                        severity="info",
                        file=path_label,
                        line=offset + i,
                        match=f"repeats line {seen[norm]}: {norm[:80]}",
                        why="A directive stated twice reads as two rules and costs context twice.",
                        fix="Keep the statement where it is acted on and delete the other.",
                    )
                )
            else:
                seen[norm] = offset + i

    findings.sort(key=lambda f: (f.line, f.rule))
    return findings


def discover(paths: list[Path]) -> list[Path]:
    out: list[Path] = []
    for p in paths:
        if p.is_file():
            out.append(p)
            continue
        for child in sorted(p.rglob("*.md")):
            if SKIP_DIRS & {part for part in child.parts}:
                continue
            if child.name in SKILL_FILES or child.name in MEMORY_FILES:
                out.append(child)
            elif classify(child) in ("agent", "command", "reference"):
                out.append(child)
    return out


def render(findings: list[Finding], scanned: list[Path]) -> str:
    if not findings:
        return f"No findings in {len(scanned)} document(s)."
    out: list[str] = []
    by_file: dict[str, list[Finding]] = {}
    for f in findings:
        by_file.setdefault(f.file, []).append(f)
    for fname, items in by_file.items():
        out.append(fname)
        for f in items:
            out.append(f"  {f.line}:  {f.severity:<5} {f.rule}  {f.name}  -- {f.match}")
            out.append(f"         fix: {f.fix}")
        out.append("")
    counts = {s: sum(1 for f in findings if f.severity == s) for s in SEVERITIES}
    out.append(
        f"{len(findings)} finding(s) in {len(scanned)} document(s): "
        f"{counts['error']} error, {counts['warn']} warn, {counts['info']} info."
    )
    out.append("Rationale and rewrites: references/rules.md")
    return "\n".join(out)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="lint_prompt_doc.py",
        description="Flag prompt-wording anti-patterns in instruction documents.",
    )
    p.add_argument("paths", nargs="+", help="Files or directories to scan.")
    p.add_argument("--json", action="store_true", help="Emit machine-readable findings.")
    p.add_argument(
        "--ignore",
        default="",
        help="Comma-separated rule ids to skip (e.g. P004,D002).",
    )
    p.add_argument(
        "--min-severity",
        choices=SEVERITIES,
        default="info",
        help="Report findings at this severity or above (default: info).",
    )
    p.add_argument("--list-rules", action="store_true", help="Print the rule catalog and exit.")
    return p


def rule_catalog() -> list[dict[str, str]]:
    rows = [
        {"rule": r.id, "name": r.name, "severity": r.severity, "why": r.why, "fix": r.fix}
        for r in LINE_RULES
    ]
    rows.extend(
        [
            {
                "rule": "P007",
                "name": "negative-enumeration-density",
                "severity": "info",
                "why": "Prohibition lists steer weakly and cost context.",
                "fix": "Replace the longest runs with positive examples.",
            },
            {
                "rule": "D001",
                "name": "doc-size-budget",
                "severity": "warn",
                "why": "Body length is a recurring context cost.",
                "fix": "Move rationale and single-branch detail into a reference file.",
            },
            {
                "rule": "D002",
                "name": "duplicate-directive",
                "severity": "info",
                "why": "A repeated directive reads as two rules.",
                "fix": "Keep one statement, at the point where it is acted on.",
            },
        ]
    )
    return sorted(rows, key=lambda r: r["rule"])


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.list_rules:
        rows = rule_catalog()
        if args.json:
            print(json.dumps({"rules": rows}, indent=2, ensure_ascii=False))
        else:
            for r in rows:
                print(f"{r['rule']}  {r['severity']:<5} {r['name']}\n      {r['why']}")
        return 0

    targets = [Path(p) for p in args.paths]
    missing = [str(p) for p in targets if not p.exists()]
    if missing:
        print(f"Path not found: {', '.join(missing)}", file=sys.stderr)
        return 2

    scanned = discover(targets)
    if not scanned:
        print(
            "No prompt documents found. Expected SKILL.md, CLAUDE.md, AGENTS.md, "
            "or *.md under an agents/ or commands/ directory; pass a file path "
            "directly to lint any other document.",
            file=sys.stderr,
        )
        return 2

    ignored = {t.strip().upper() for t in args.ignore.split(",") if t.strip()}
    floor = SEVERITIES.index(args.min_severity)

    findings: list[Finding] = []
    for path in scanned:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            print(f"Skipping {path}: not UTF-8 text.", file=sys.stderr)
            continue
        for f in lint_text(text, str(path), classify(path)):
            if f.rule in ignored or SEVERITIES.index(f.severity) < floor:
                continue
            findings.append(f)

    if args.json:
        counts = {s: sum(1 for f in findings if f.severity == s) for s in SEVERITIES}
        print(
            json.dumps(
                {
                    "findings": [asdict(f) for f in findings],
                    "summary": {"documents": len(scanned), **counts},
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        print(render(findings, scanned))

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
