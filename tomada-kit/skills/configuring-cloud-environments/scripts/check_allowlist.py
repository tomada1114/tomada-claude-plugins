#!/usr/bin/env python3
"""Check which hosts a Claude Code cloud environment's network access lets through.

Reads the Trusted default allowlist from the live "Configure cloud environments"
page (or a saved copy), adds any Custom allowed domains, and reports for each
host whether an entry covers it and which one.

Usage:
  check_allowlist.py HOST [HOST ...] [--extra DOMAIN ...] [--no-defaults]
                     [--hosts-file PATH] [--docs-file PATH] [--json]

Exit codes: 0 every host covered, 1 at least one host not covered,
2 bad invocation or the allowlist could not be read.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from urllib.parse import urlsplit

DOCS_URL = "https://code.claude.com/docs/en/cloud-environments.md"
SECTION_HEADING = "## Default allowed domains"
_BULLET = re.compile(r"^\s*\*\s+(.+?)\s*$")
_LINK = re.compile(r"^\[([^\]]+)\]\([^)]*\)")


@dataclass
class Result:
    host: str
    covered: bool
    matched_by: str | None
    source: str | None  # "default", "extra", or None


def parse_allowlist(markdown: str) -> list[str]:
    """Return the domain entries under the "Default allowed domains" heading."""
    lines = markdown.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == SECTION_HEADING)
    except StopIteration:
        raise ValueError(f"heading {SECTION_HEADING!r} not found") from None
    entries: list[str] = []
    for line in lines[start + 1 :]:
        if line.startswith("## "):
            break
        match = _BULLET.match(line)
        if not match:
            continue
        entry = normalize_rule(match.group(1))
        if entry and entry not in entries:
            entries.append(entry)
    if not entries:
        raise ValueError(f"no domain entries under {SECTION_HEADING!r}")
    return entries


def normalize_rule(text: str) -> str:
    """Turn one docs bullet or Custom-list line into a bare domain rule."""
    text = text.strip()
    link = _LINK.match(text)
    if link:
        text = link.group(1)
    text = text.replace("\\", "")
    token = text.split()[0] if text.split() else ""
    return token.lower().rstrip(".")


def normalize_host(text: str) -> str:
    """Accept a bare host or a URL and return the lower-case hostname."""
    text = text.strip()
    if "://" in text:
        return (urlsplit(text).hostname or "").lower()
    return text.split("/")[0].split(":")[0].lower().rstrip(".")


def rule_matches(host: str, rule: str) -> bool:
    """`*.example.com` matches subdomains only; other rules match exactly."""
    if rule.startswith("*."):
        return host.endswith("." + rule[2:])
    return host == rule


def check(hosts: list[str], defaults: list[str], extra: list[str]) -> list[Result]:
    results = []
    for host in hosts:
        found = None
        for source, rules in (("extra", extra), ("default", defaults)):
            rule = next((r for r in rules if rule_matches(host, r)), None)
            if rule:
                found = (rule, source)
                break
        if found:
            results.append(Result(host, True, found[0], found[1]))
        else:
            results.append(Result(host, False, None, None))
    return results


def load_docs(docs_file: str | None) -> str:
    if docs_file:
        with open(docs_file, encoding="utf-8") as handle:
            return handle.read()
    # The docs host answers 403 to urllib's default User-Agent; name this script instead.
    request = urllib.request.Request(
        DOCS_URL, headers={"User-Agent": "check_allowlist (claude-code skill)"}
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8")


def read_lines(path: str) -> list[str]:
    with open(path, encoding="utf-8") as handle:
        return [line.strip() for line in handle if line.strip() and not line.lstrip().startswith("#")]


def render_text(results: list[Result]) -> str:
    rows = []
    for r in results:
        if r.covered:
            rows.append(f"OK       {r.host}  (by {r.matched_by}, {r.source})")
        else:
            rows.append(f"MISSING  {r.host}")
    missing = sum(not r.covered for r in results)
    rows.append(f"{len(results) - missing}/{len(results)} covered")
    if any(r.matched_by and r.matched_by.startswith("*.") for r in results) or missing:
        rows.append("note: a *.domain rule is treated as subdomains only, never the bare domain")
    return "\n".join(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("hosts", nargs="*", help="hosts or URLs to check")
    parser.add_argument("--hosts-file", help="file with one host or URL per line")
    parser.add_argument(
        "--extra", action="append", default=[], help="a Custom allowed domain (repeatable)"
    )
    parser.add_argument(
        "--no-defaults",
        action="store_true",
        help="Custom access with 'Also include default list' unchecked",
    )
    parser.add_argument("--docs-file", help="a saved copy of the docs page instead of fetching it")
    parser.add_argument("--json", action="store_true", help="print results as JSON")
    args = parser.parse_args(argv)

    raw_hosts = list(args.hosts)
    if args.hosts_file:
        try:
            raw_hosts += read_lines(args.hosts_file)
        except OSError as exc:
            print(f"ERR_HOSTS_FILE: {exc}", file=sys.stderr)
            return 2
    hosts = [h for h in (normalize_host(x) for x in raw_hosts) if h]
    if not hosts:
        print("ERR_NO_HOSTS: pass at least one host or --hosts-file", file=sys.stderr)
        return 2

    defaults: list[str] = []
    if not args.no_defaults:
        try:
            defaults = parse_allowlist(load_docs(args.docs_file))
        except (OSError, urllib.error.URLError, ValueError) as exc:
            print(
                f"ERR_ALLOWLIST: {exc}\n"
                f"Next: save {DOCS_URL} to a file and rerun with --docs-file <path>",
                file=sys.stderr,
            )
            return 2
    extra = [r for r in (normalize_rule(x) for x in args.extra) if r]

    results = check(hosts, defaults, extra)
    if args.json:
        payload = {
            "defaults_included": not args.no_defaults,
            "default_entries": len(defaults),
            "results": [asdict(r) for r in results],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_text(results))
    return 0 if all(r.covered for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
