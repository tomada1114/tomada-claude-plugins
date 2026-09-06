#!/usr/bin/env python3
"""Check WCAG 2.x contrast ratios for foreground/background color pairs.

Purpose
-------
Design-concept documents produced by the ui-ux-designing skill used to carry
hand-written contrast ratios that were sometimes wrong (e.g. #71717A on
#0A0A0B was once listed as 4.6:1; the real value is 4.09:1). This script
makes the check deterministic: once a palette is chosen, run every
foreground/background pair through it and paste the result into the
document instead of computing ratios by hand.

Supported color formats
------------------------
- ``#RRGGBB`` and ``#RGB`` hex
- ``rgb(r g b)`` and ``rgb(r, g, b)`` (0-255 per channel)
- ``oklch(L C H)`` (L as 0-1 or a percentage, H in degrees), converted to
  sRGB per the CSS Color 4 spec. Channels outside [0, 1] after conversion
  are clipped and the result is flagged with ``gamut_clipped: true``.

Alpha channels are not supported and are rejected with a clear error.

Usage
-----
Check ad-hoc pairs on the command line::

    python3 check_contrast.py --pair "#71717A" "#0A0A0B" --pair "#FFFFFF" "#2563EB" --kind text

Check a batch of named pairs from a JSON file (array of objects with
``name``, ``fg``, ``bg`` and optional ``kind``)::

    python3 check_contrast.py palette.json

Both a JSON file and ``--pair`` options may be combined; at least one of
the two is required. Use ``--level AAA`` to check against the stricter
thresholds, and ``--json`` for machine-readable output.

Exit codes
----------
0 - all pairs pass at the requested level
1 - at least one pair fails
2 - bad invocation or a color value that could not be parsed
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import asdict, dataclass
from typing import List, Optional, Tuple

# ---------------------------------------------------------------------------
# WCAG thresholds
# ---------------------------------------------------------------------------

# kind -> {level: required ratio}
THRESHOLDS = {
    "text": {"AA": 4.5, "AAA": 7.0},
    "large": {"AA": 3.0, "AAA": 4.5},
    "ui": {"AA": 3.0, "AAA": 3.0},
}

VALID_KINDS = tuple(THRESHOLDS.keys())
VALID_LEVELS = ("AA", "AAA")

ACCEPTED_FORMATS_MSG = (
    "accepted color formats: #RRGGBB, #RGB, rgb(r g b) / rgb(r, g, b), "
    "oklch(L C H) (alpha is not supported)"
)


class ColorParseError(ValueError):
    """Raised when a color string cannot be parsed."""


# ---------------------------------------------------------------------------
# Color parsing
# ---------------------------------------------------------------------------

_HEX6_RE = re.compile(r"^#([0-9a-fA-F]{6})$")
_HEX3_RE = re.compile(r"^#([0-9a-fA-F]{3})$")
_RGB_RE = re.compile(
    r"^rgba?\(\s*([+-]?[0-9]*\.?[0-9]+)\s*,?\s+?"
    r"([+-]?[0-9]*\.?[0-9]+)\s*,?\s+?"
    r"([+-]?[0-9]*\.?[0-9]+)\s*"
    r"(?:[,/]\s*[+-]?[0-9]*\.?[0-9]+%?\s*)?\)$",
    re.IGNORECASE,
)
_OKLCH_RE = re.compile(
    r"^oklch\(\s*([+-]?[0-9]*\.?[0-9]+%?)\s+"
    r"([+-]?[0-9]*\.?[0-9]+)\s+"
    r"([+-]?[0-9]*\.?[0-9]+)\s*"
    r"(?:/\s*[+-]?[0-9]*\.?[0-9]+%?\s*)?\)$",
    re.IGNORECASE,
)
_ALPHA_HINT_RE = re.compile(r"^#([0-9a-fA-F]{4}|[0-9a-fA-F]{8})$")


def _clip01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


def _srgb_to_linear(c: float) -> float:
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def parse_color(value: str) -> Tuple[Tuple[float, float, float], bool]:
    """Parse a color string into an (r, g, b) tuple with channels in [0, 1].

    Returns ``(rgb, gamut_clipped)`` where ``gamut_clipped`` is True when an
    out-of-gamut OKLCH color had to be clipped into sRGB range.

    Raises ``ColorParseError`` for anything unparsable, including any color
    that carries an alpha channel.
    """
    if value is None:
        raise ColorParseError(f"color value is missing; {ACCEPTED_FORMATS_MSG}")

    s = value.strip()
    if not s:
        raise ColorParseError(f"empty color value; {ACCEPTED_FORMATS_MSG}")

    # Reject alpha-bearing forms explicitly with a clear message: 8/4-digit
    # hex, and any rgba(...) call (rgb() with a 4th channel is also written
    # as "rgba(" per the CSS Color 4 unified syntax).
    if _ALPHA_HINT_RE.match(s) or re.match(r"^rgba\(", s, re.IGNORECASE):
        raise ColorParseError(
            f"color '{value}' includes an alpha channel, which is not "
            f"supported; {ACCEPTED_FORMATS_MSG}"
        )

    m = _HEX6_RE.match(s)
    if m:
        h = m.group(1)
        r = int(h[0:2], 16) / 255.0
        g = int(h[2:4], 16) / 255.0
        b = int(h[4:6], 16) / 255.0
        return (r, g, b), False

    m = _HEX3_RE.match(s)
    if m:
        h = m.group(1)
        r = int(h[0] * 2, 16) / 255.0
        g = int(h[1] * 2, 16) / 255.0
        b = int(h[2] * 2, 16) / 255.0
        return (r, g, b), False

    m = _RGB_RE.match(s)
    if m:
        r = float(m.group(1)) / 255.0
        g = float(m.group(2)) / 255.0
        b = float(m.group(3)) / 255.0
        return (_clip01(r), _clip01(g), _clip01(b)), False

    m = _OKLCH_RE.match(s)
    if m:
        return _oklch_to_srgb(m.group(1), float(m.group(2)), float(m.group(3)))

    raise ColorParseError(f"could not parse color '{value}'; {ACCEPTED_FORMATS_MSG}")


def _oklch_to_srgb(l_raw: str, c: float, h_deg: float) -> Tuple[Tuple[float, float, float], bool]:
    """Convert OKLCH to sRGB per the CSS Color 4 spec.

    Returns ``((r, g, b), gamut_clipped)`` with channels clipped to [0, 1].
    """
    if l_raw.endswith("%"):
        L = float(l_raw[:-1]) / 100.0
    else:
        L = float(l_raw)

    h_rad = math.radians(h_deg)
    a = c * math.cos(h_rad)
    b_ = c * math.sin(h_rad)

    # OKLab -> LMS (cube-rooted intermediate)
    l_ = L + 0.3963377774 * a + 0.2158037573 * b_
    m_ = L - 0.1055613458 * a - 0.0638541728 * b_
    s_ = L - 0.0894841775 * a - 1.2914855480 * b_

    l3 = l_ ** 3
    m3 = m_ ** 3
    s3 = s_ ** 3

    # LMS -> linear sRGB
    lin_r = 4.0767416621 * l3 - 3.3077115913 * m3 + 0.2309699292 * s3
    lin_g = -1.2684380046 * l3 + 2.6097574011 * m3 - 0.3413193965 * s3
    lin_b = -0.0041960863 * l3 - 0.7034186147 * m3 + 1.7076147010 * s3

    clipped = False
    channels = []
    for lin in (lin_r, lin_g, lin_b):
        if lin < 0.0 or lin > 1.0:
            clipped = True
        lin_clipped = _clip01(lin)
        channels.append(_linear_to_srgb(lin_clipped))

    return (channels[0], channels[1], channels[2]), clipped


def _linear_to_srgb(c: float) -> float:
    c = _clip01(c)
    if c <= 0.0031308:
        v = 12.92 * c
    else:
        v = 1.055 * (c ** (1 / 2.4)) - 0.055
    return _clip01(v)


# ---------------------------------------------------------------------------
# WCAG luminance / contrast
# ---------------------------------------------------------------------------


def relative_luminance(rgb: Tuple[float, float, float]) -> float:
    """WCAG 2.x relative luminance for an (r, g, b) tuple in [0, 1]."""
    r, g, b = rgb
    r_lin = _srgb_to_linear(r)
    g_lin = _srgb_to_linear(g)
    b_lin = _srgb_to_linear(b)
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def contrast_ratio(fg_rgb: Tuple[float, float, float], bg_rgb: Tuple[float, float, float]) -> float:
    """WCAG contrast ratio between two (r, g, b) colors, rounded to 2 dp."""
    l1 = relative_luminance(fg_rgb)
    l2 = relative_luminance(bg_rgb)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    ratio = (lighter + 0.05) / (darker + 0.05)
    return round(ratio, 2)


# ---------------------------------------------------------------------------
# Pair evaluation
# ---------------------------------------------------------------------------


@dataclass
class PairResult:
    name: Optional[str]
    fg: str
    bg: str
    kind: str
    ratio: float
    required: float
    level: str
    passed: bool
    gamut_clipped: bool


@dataclass
class Pair:
    fg: str
    bg: str
    kind: str = "text"
    name: Optional[str] = None


def evaluate(pairs: List[Pair], level: str) -> List[PairResult]:
    """Evaluate a list of Pair objects at the given WCAG level.

    Raises ColorParseError for any unparsable color, and ValueError for an
    unknown kind or level.
    """
    if level not in VALID_LEVELS:
        raise ValueError(f"unknown level '{level}'; expected one of {VALID_LEVELS}")

    results: List[PairResult] = []
    for pair in pairs:
        kind = pair.kind or "text"
        if kind not in VALID_KINDS:
            raise ValueError(f"unknown kind '{kind}'; expected one of {VALID_KINDS}")

        fg_rgb, fg_clipped = parse_color(pair.fg)
        bg_rgb, bg_clipped = parse_color(pair.bg)
        ratio = contrast_ratio(fg_rgb, bg_rgb)
        required = THRESHOLDS[kind][level]
        passed = ratio >= required
        results.append(
            PairResult(
                name=pair.name,
                fg=pair.fg,
                bg=pair.bg,
                kind=kind,
                ratio=ratio,
                required=required,
                level=level,
                passed=passed,
                gamut_clipped=fg_clipped or bg_clipped,
            )
        )
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _load_pairs_from_json(path: str) -> List[Pair]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except OSError as exc:
        raise ColorParseError(f"could not read JSON file '{path}': {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ColorParseError(f"could not parse JSON file '{path}': {exc}") from exc

    if not isinstance(data, list):
        raise ColorParseError(
            f"JSON file '{path}' must contain an array of pair objects"
        )

    pairs: List[Pair] = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ColorParseError(
                f"JSON file '{path}' entry {i} must be an object with fg/bg"
            )
        if "fg" not in item or "bg" not in item:
            raise ColorParseError(
                f"JSON file '{path}' entry {i} is missing 'fg' or 'bg'"
            )
        pairs.append(
            Pair(
                fg=item["fg"],
                bg=item["bg"],
                kind=item.get("kind", "text"),
                name=item.get("name"),
            )
        )
    return pairs


def _format_table(results: List[PairResult]) -> str:
    headers = ["name", "fg", "bg", "kind", "ratio", "required", "result"]
    rows = []
    for r in results:
        rows.append(
            [
                r.name or "-",
                r.fg,
                r.bg,
                r.kind,
                f"{r.ratio:.2f}",
                f"{r.required:.2f}",
                "PASS" if r.passed else "FAIL",
            ]
        )

    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def fmt_row(cells: List[str]) -> str:
        return "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(cells))

    lines = [fmt_row(headers), fmt_row(["-" * w for w in widths])]
    for row in rows:
        lines.append(fmt_row(row))
    return "\n".join(lines)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_contrast.py",
        description=(
            "Check WCAG 2.x contrast ratios for foreground/background color "
            "pairs. Accepts #RRGGBB, #RGB, rgb(r g b), and oklch(L C H) "
            "colors (no alpha)."
        ),
    )
    parser.add_argument(
        "json_file",
        nargs="?",
        default=None,
        help=(
            "path to a JSON file: an array of objects "
            '{"name": str, "fg": str, "bg": str, "kind": '
            '"text"|"large"|"ui"} (kind optional, default text)'
        ),
    )
    parser.add_argument(
        "--pair",
        nargs=2,
        metavar=("FG", "BG"),
        action="append",
        default=None,
        help="a foreground/background color pair; repeatable",
    )
    parser.add_argument(
        "--kind",
        choices=VALID_KINDS,
        default="text",
        help="kind applied to all --pair entries (default: text)",
    )
    parser.add_argument(
        "--level",
        choices=VALID_LEVELS,
        default="AA",
        help="WCAG level to check against (default: AA)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable JSON instead of a human-readable table",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if not args.json_file and not args.pair:
        parser.print_usage(sys.stderr)
        print(
            "check_contrast.py: error: provide a JSON file, at least one "
            "--pair, or both",
            file=sys.stderr,
        )
        return 2

    pairs: List[Pair] = []
    try:
        if args.json_file:
            pairs.extend(_load_pairs_from_json(args.json_file))
        if args.pair:
            for fg, bg in args.pair:
                pairs.append(Pair(fg=fg, bg=bg, kind=args.kind, name=None))
    except ColorParseError as exc:
        print(f"check_contrast.py: error: {exc}", file=sys.stderr)
        return 2

    try:
        results = evaluate(pairs, args.level)
    except (ColorParseError, ValueError) as exc:
        print(f"check_contrast.py: error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps([asdict(r) for r in results], ensure_ascii=False, indent=2))
    else:
        print(_format_table(results))

    return 0 if all(r.passed for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
