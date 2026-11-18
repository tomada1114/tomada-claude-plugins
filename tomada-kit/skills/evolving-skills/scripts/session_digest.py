#!/usr/bin/env python3
"""session_digest.py - Turn a Claude Code transcript into a small JSON digest.

The digest lets a cheap model look at a session without reading the full
transcript: which skills were used, what the person said after the first
skill use, and how many tool errors and interruptions happened.

Usage:
    session_digest.py --transcript T [--skills-root DIR ...]
                      [--max-chars 400] [--max-messages 40] [--out F]

Options:
    --transcript T     Transcript file (.jsonl, one event per line).
    --skills-root DIR  Repeatable. Keep only skills for which
                       <DIR>/<name>/SKILL.md exists, and record that root.
                       Without it every Skill call and slash command counts.
    --max-chars N      Truncate each follow-up message to N characters.
    --max-messages N   Keep at most N follow-ups (the earliest ones).
    --out F            Write the JSON to F instead of stdout.

Output keys:
    session_id, transcript, turns, skills_used [{name, via, root,
    event_index}], followups [{event_index, text, kind}], tool_errors,
    interruptions. event_index is the 0-based line number in the transcript.
    A followup's kind is "message" (typed by the person) or "answer" (the
    person's answers to an AskUserQuestion call, from its tool result).
    Answers count toward --max-messages but not toward turns.

Exit codes:
    0  digest written
    2  bad invocation (argparse)
    3  transcript missing or unreadable
"""

import argparse
import json
import re
import sys
from pathlib import Path

DEFAULT_MAX_CHARS = 400
DEFAULT_MAX_MESSAGES = 40

# Wrapper tags whose content is injected by the harness, not typed by the person.
WRAPPER_TAG_RE = re.compile(
    r"<(system-reminder|local-command-stdout|local-command-stderr"
    r"|local-command-stdout-error|local-command-caveat|task-notification"
    r"|command-message|command-args|command-name|bash-stdout|bash-stderr"
    r"|user-prompt-submit-hook)>.*?</\1>",
    re.S,
)
COMMAND_NAME_RE = re.compile(r"<command-name>\s*(.*?)\s*</command-name>", re.S)
INTERRUPT_PREFIX = "[Request interrupted by user"
# The person's answers to AskUserQuestion arrive as a tool result of this form:
# 'The user answered: "<q>"="<a>", ... Read the answers carefully — ...'
ASK_TOOL = "AskUserQuestion"
ANSWER_PREFIX = "The user answered: "
ANSWER_SUFFIX = " Read the answers carefully"
# Plain-text messages the harness writes into user turns.
HARNESS_PREFIXES = (
    "Stop hook feedback:",
    "SubagentStop hook feedback:",
    "PreToolUse hook",
    "PostToolUse hook",
    "UserPromptSubmit hook",
    "Caveat: The messages below were generated",
    "This session is being continued from a previous conversation",
)


def normalize_skill_name(raw):
    """Strip a leading slash and a `plugin:` prefix; None when nothing is left."""
    if not isinstance(raw, str):
        return None
    name = raw.strip().lstrip("/").strip()
    if ":" in name:
        name = name.rsplit(":", 1)[1].strip()
    return name or None


def resolve_root(name, roots):
    """Return the first root holding <name>/SKILL.md, or None."""
    for root in roots:
        if (Path(root) / name / "SKILL.md").is_file():
            return str(root)
    return None


def content_text(content):
    """Join the text of a message content (string or list of blocks)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [
            b.get("text", "")
            for b in content
            if isinstance(b, dict) and b.get("type") == "text" and isinstance(b.get("text"), str)
        ]
        return "\n".join(parts)
    return ""


def answer_text(content):
    """Extract the person's answers from an AskUserQuestion tool result."""
    text = content_text(content).strip()
    if text.startswith(ANSWER_PREFIX):
        text = text[len(ANSWER_PREFIX):]
        cut = text.find(ANSWER_SUFFIX)
        if cut >= 0:
            text = text[:cut]
    return text.strip()


def is_tool_result_only(content):
    if not isinstance(content, list):
        return False
    blocks = [b for b in content if isinstance(b, dict)]
    return bool(blocks) and all(b.get("type") == "tool_result" for b in blocks)


def truncate(text, max_chars):
    text = " ".join(text.split())
    return text[:max_chars] if max_chars >= 0 else text


def read_events(path):
    """Return [(line_index, event_dict)], skipping blank and malformed lines.

    Raises OSError when the file cannot be read.
    """
    events = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for index, line in enumerate(fh):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            if isinstance(obj, dict):
                events.append((index, obj))
    return events


def build_digest(transcript, skills_roots=None, max_chars=DEFAULT_MAX_CHARS,
                 max_messages=DEFAULT_MAX_MESSAGES):
    """Build the digest dict. Raises OSError when the transcript is unreadable."""
    path = Path(transcript)
    if not path.is_file():
        raise FileNotFoundError(str(path))
    roots = [Path(r) for r in (skills_roots or [])]
    events = read_events(path)

    session_id = None
    turns = 0
    skills_used = []
    person_messages = []  # (event_index, text, kind) in event order
    ask_ids = set()
    tool_errors = 0
    interruptions = 0

    def add_skill(raw, via, index):
        name = normalize_skill_name(raw)
        if not name:
            return
        root = None
        if roots:
            root = resolve_root(name, roots)
            if root is None:
                return
        skills_used.append({"name": name, "via": via, "root": root, "event_index": index})

    for index, obj in events:
        if session_id is None and isinstance(obj.get("sessionId"), str):
            session_id = obj["sessionId"]
        etype = obj.get("type")
        message = obj.get("message")
        content = message.get("content") if isinstance(message, dict) else None

        if etype == "assistant":
            if obj.get("isSidechain") or not isinstance(content, list):
                continue
            for block in content:
                if not (isinstance(block, dict) and block.get("type") == "tool_use"):
                    continue
                if block.get("name") == "Skill":
                    tin = block.get("input") if isinstance(block.get("input"), dict) else {}
                    add_skill(tin.get("skill"), "tool", index)
                elif block.get("name") == ASK_TOOL and isinstance(block.get("id"), str):
                    ask_ids.add(block["id"])
            continue

        if etype != "user" or obj.get("isSidechain"):
            continue

        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_result" and block.get("is_error"):
                    tool_errors += 1
                if block.get("type") == "tool_result" and block.get("tool_use_id") in ask_ids:
                    answer = answer_text(block.get("content"))
                    if answer:
                        person_messages.append((index, answer, "answer"))
                elif (block.get("type") == "text" and isinstance(block.get("text"), str)
                      and block["text"].strip().startswith(INTERRUPT_PREFIX)):
                    interruptions += 1
        elif isinstance(content, str) and content.strip().startswith(INTERRUPT_PREFIX):
            interruptions += 1

        if obj.get("isMeta") or is_tool_result_only(content):
            continue
        text = content_text(content).strip()
        if not text or text.startswith(INTERRUPT_PREFIX):
            continue

        command = COMMAND_NAME_RE.search(text)
        if command:
            turns += 1
            add_skill(command.group(1), "command", index)
            continue

        remainder = WRAPPER_TAG_RE.sub("", text).strip()
        if not remainder or remainder.startswith(HARNESS_PREFIXES):
            continue
        turns += 1
        person_messages.append((index, remainder, "message"))

    followups = []
    if skills_used:
        first_use = min(s["event_index"] for s in skills_used)
        for index, text, kind in person_messages:
            if index <= first_use:
                continue
            if len(followups) >= max_messages:
                break
            followups.append({"event_index": index, "text": truncate(text, max_chars), "kind": kind})

    return {
        "session_id": session_id or path.stem,
        "transcript": str(path),
        "turns": turns,
        "skills_used": skills_used,
        "followups": followups,
        "tool_errors": tool_errors,
        "interruptions": interruptions,
    }


def build_parser():
    parser = argparse.ArgumentParser(
        prog="session_digest.py",
        description="Turn a Claude Code transcript into a small JSON digest.",
    )
    parser.add_argument("--transcript", required=True)
    parser.add_argument("--skills-root", action="append", default=[])
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    parser.add_argument("--max-messages", type=int, default=DEFAULT_MAX_MESSAGES)
    parser.add_argument("--out")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        digest = build_digest(args.transcript, args.skills_root, args.max_chars, args.max_messages)
    except OSError as exc:
        print("error: cannot read transcript: %s" % exc, file=sys.stderr)
        return 3
    text = json.dumps(digest, ensure_ascii=False, indent=2)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
