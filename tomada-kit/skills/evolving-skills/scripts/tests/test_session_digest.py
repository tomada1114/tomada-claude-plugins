#!/usr/bin/env python3
"""Tests for session_digest.py (synthetic transcripts only)."""

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import session_digest as sd  # noqa: E402


def user(text, **extra):
    event = {"type": "user", "sessionId": "sess-1", "message": {"role": "user", "content": text}}
    event.update(extra)
    return event


def user_blocks(blocks, **extra):
    event = {"type": "user", "sessionId": "sess-1", "message": {"role": "user", "content": blocks}}
    event.update(extra)
    return event


def assistant_skill(skill, tool_id="t1", **extra):
    event = {"type": "assistant", "sessionId": "sess-1", "message": {"role": "assistant", "content": [
        {"type": "text", "text": "using a skill"},
        {"type": "tool_use", "id": tool_id, "name": "Skill", "input": {"skill": skill}},
    ]}}
    event.update(extra)
    return event


def command(name, args=""):
    return user("<command-message>%s</command-message>\n<command-name>/%s</command-name>\n"
                "<command-args>%s</command-args>" % (name.lstrip("/"), name, args))


class DigestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, events, name="t.jsonl", raw_lines=()):
        path = self.dir / name
        lines = [json.dumps(e) for e in events] + list(raw_lines)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def make_root(self, name, *skills):
        root = self.dir / name
        for skill in skills:
            (root / skill).mkdir(parents=True)
            (root / skill / "SKILL.md").write_text("---\nname: %s\n---\n" % skill)
        return root

    def test_tool_invoked_skill_and_followups(self):
        path = self.write([
            {"type": "session-owner"},
            user("please write the article"),
            assistant_skill("article-writing"),
            user_blocks([{"type": "tool_result", "tool_use_id": "t1", "content": "ok"}]),
            user("no, the title is wrong"),
            user("shorter please"),
        ])
        d = sd.build_digest(path)
        self.assertEqual(d["session_id"], "sess-1")
        self.assertEqual(d["transcript"], str(path))
        self.assertEqual(d["turns"], 3)
        self.assertEqual(d["skills_used"], [
            {"name": "article-writing", "via": "tool", "root": None, "event_index": 2}])
        self.assertEqual([f["text"] for f in d["followups"]], ["no, the title is wrong", "shorter please"])
        self.assertEqual([f["event_index"] for f in d["followups"]], [4, 5])
        self.assertEqual({f["kind"] for f in d["followups"]}, {"message"})

    def test_command_invoked_skill_and_plugin_prefix(self):
        path = self.write([
            command("myplug:deck-building", "make a deck"),
            assistant_skill("otherplug:figure-designing"),
            user("fix the colors"),
        ])
        d = sd.build_digest(path)
        self.assertEqual([(s["name"], s["via"]) for s in d["skills_used"]],
                         [("deck-building", "command"), ("figure-designing", "tool")])
        self.assertEqual(d["turns"], 2)
        self.assertEqual([f["text"] for f in d["followups"]], ["fix the colors"])

    def test_roots_filter_and_record_root(self):
        root_a = self.make_root("a", "alpha")
        root_b = self.make_root("b", "beta", "alpha")
        path = self.write([
            assistant_skill("alpha"),
            assistant_skill("beta", tool_id="t2"),
            command("clear"),
            assistant_skill("gamma", tool_id="t3"),
        ])
        d = sd.build_digest(path, [root_a, root_b])
        self.assertEqual([(s["name"], s["root"]) for s in d["skills_used"]],
                         [("alpha", str(root_a)), ("beta", str(root_b))])

    def test_followups_exclude_harness_text(self):
        path = self.write([
            assistant_skill("alpha"),
            user("<system-reminder>injected</system-reminder>"),
            user("Stop hook feedback:\nSelf-check failed"),
            user("Base directory for this skill: /x", isMeta=True),
            user("subagent prompt", isSidechain=True),
            user("<local-command-stdout>output</local-command-stdout>"),
            command("compact"),
            user_blocks([{"type": "tool_result", "tool_use_id": "t1", "content": "x"}]),
            user_blocks([{"type": "image", "source": {}}]),
            user(""),
            user("<system-reminder>r</system-reminder>real words here"),
            {"type": "attachment", "attachment": {"type": "date"}},
            {"type": "api-request-blob", "message": {"content": [{"type": "text", "text": "x"}]}},
        ])
        d = sd.build_digest(path)
        self.assertEqual([f["text"] for f in d["followups"]], ["real words here"])

    def test_followups_only_after_first_skill_and_none_without_skill(self):
        path = self.write([user("before"), assistant_skill("alpha"), user("after")])
        self.assertEqual([f["text"] for f in sd.build_digest(path)["followups"]], ["after"])
        path2 = self.write([user("hello"), user("again")], name="t2.jsonl")
        d2 = sd.build_digest(path2)
        self.assertEqual(d2["followups"], [])
        self.assertEqual(d2["skills_used"], [])
        self.assertEqual(d2["turns"], 2)

    def test_truncation_and_message_cap(self):
        events = [assistant_skill("alpha")] + [user("message %d %s" % (i, "x" * 50)) for i in range(5)]
        path = self.write(events)
        d = sd.build_digest(path, max_chars=12, max_messages=3)
        self.assertEqual(len(d["followups"]), 3)
        self.assertEqual(d["followups"][0]["text"], "message 0 xx")
        self.assertEqual([f["event_index"] for f in d["followups"]], [1, 2, 3])

    def test_errors_and_interruptions(self):
        path = self.write([
            assistant_skill("alpha"),
            user_blocks([
                {"type": "tool_result", "tool_use_id": "t1", "content": "boom", "is_error": True},
                {"type": "tool_result", "tool_use_id": "t2", "content": "fine"},
            ]),
            user_blocks([{"type": "tool_result", "tool_use_id": "t3", "is_error": True, "content": []}]),
            user_blocks([{"type": "text", "text": "[Request interrupted by user for tool use]"}]),
            user("[Request interrupted by user]"),
            user_blocks(["not a dict", {"type": "text", "text": "ok go on"}]),
            user_blocks([{"type": "tool_result", "tool_use_id": "t9", "is_error": True}],
                        isSidechain=True),
        ])
        d = sd.build_digest(path)
        self.assertEqual(d["tool_errors"], 2)
        self.assertEqual(d["interruptions"], 2)
        self.assertEqual([f["text"] for f in d["followups"]], ["ok go on"])

    def test_malformed_lines_and_unknown_events(self):
        path = self.write(
            [assistant_skill("alpha"), {"type": "mystery", "foo": 1},
             {"type": "assistant", "message": "not a dict"},
             {"type": "assistant", "isSidechain": True, "message": {"content": [
                 {"type": "tool_use", "name": "Skill", "input": {"skill": "side"}}]}},
             {"type": "assistant", "message": {"content": [
                 {"type": "tool_use", "name": "Skill", "input": "bad"},
                 {"type": "tool_use", "name": "Skill", "input": {"skill": "plug:"}}, "junk"]}},
             user("after")],
            raw_lines=["{not json", "[1, 2]", "", "   "],
        )
        d = sd.build_digest(path)
        self.assertEqual([s["name"] for s in d["skills_used"]], ["alpha"])
        self.assertEqual(d["followups"][0]["text"], "after")

    def test_ask_user_question_answers_are_followups(self):
        def ask(tool_id, **extra):
            event = {"type": "assistant", "sessionId": "sess-1", "message": {"content": [
                {"type": "tool_use", "id": tool_id, "name": "AskUserQuestion",
                 "input": {"questions": []}}]}}
            event.update(extra)
            return event

        suffix = (" Read the answers carefully — they may request clarification, changes, "
                  "or that you not proceed — and follow what they actually say.")
        path = self.write([
            ask("a0"),
            user_blocks([{"type": "tool_result", "tool_use_id": "a0",
                          "content": 'The user answered: "Q0"="before skill".' + suffix}]),
            assistant_skill("alpha"),
            ask("a1"),
            user_blocks([{"type": "tool_result", "tool_use_id": "a1",
                          "content": 'The user answered: "Title?"="Shorter",  "Tone?"="plain".'
                          + suffix}]),
            user("typed correction"),
            ask("a2"),
            user_blocks([{"type": "tool_result", "tool_use_id": "a2", "content": [
                {"type": "text", "text": "free text without the prefix"}]}]),
            ask("a3"),
            user_blocks([{"type": "tool_result", "tool_use_id": "a3", "content": ""}]),
            ask("a4", isSidechain=True),
            user_blocks([{"type": "tool_result", "tool_use_id": "a4", "content": "side"}]),
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "name": "AskUserQuestion", "input": {}}]}},
            user_blocks([{"type": "tool_result", "tool_use_id": "other", "content": "not an answer"}]),
        ])
        d = sd.build_digest(path)
        self.assertEqual([(f["kind"], f["text"]) for f in d["followups"]], [
            ("answer", '"Title?"="Shorter", "Tone?"="plain".'),
            ("message", "typed correction"),
            ("answer", "free text without the prefix"),
        ])
        self.assertEqual([f["event_index"] for f in d["followups"]], [4, 5, 7])
        self.assertEqual(d["turns"], 1)
        capped = sd.build_digest(path, max_chars=8, max_messages=2)
        self.assertEqual([f["text"] for f in capped["followups"]], ['"Title?"', "typed co"])

    def test_answer_text_helper(self):
        self.assertEqual(sd.answer_text('The user answered: "a"="b".'), '"a"="b".')
        self.assertEqual(sd.answer_text("plain"), "plain")
        self.assertEqual(sd.answer_text(None), "")

    def test_session_id_falls_back_to_stem(self):
        path = self.dir / "abc-123.jsonl"
        path.write_text(json.dumps({"type": "user", "message": {"content": "hi there"}}) + "\n")
        self.assertEqual(sd.build_digest(path)["session_id"], "abc-123")

    def test_missing_file_raises(self):
        with self.assertRaises(OSError):
            sd.build_digest(self.dir / "nope.jsonl")

    def test_helpers(self):
        self.assertIsNone(sd.normalize_skill_name(None))
        self.assertIsNone(sd.normalize_skill_name("/"))
        self.assertEqual(sd.normalize_skill_name(" /p:q:name "), "name")
        self.assertEqual(sd.content_text(None), "")
        self.assertFalse(sd.is_tool_result_only("text"))
        self.assertFalse(sd.is_tool_result_only([]))
        self.assertEqual(sd.truncate("a  b\nc", -1), "a b c")


class MainTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.path = self.dir / "s.jsonl"
        self.path.write_text("\n".join(json.dumps(e) for e in [
            assistant_skill("alpha"), user("one"), user("two")]) + "\n")

    def tearDown(self):
        self.tmp.cleanup()

    def run_main(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = sd.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_stdout(self):
        code, out, _ = self.run_main(["--transcript", str(self.path), "--max-chars", "2"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual([f["text"] for f in data["followups"]], ["on", "tw"])

    def test_out_file_and_roots(self):
        root = self.dir / "root"
        (root / "alpha").mkdir(parents=True)
        (root / "alpha" / "SKILL.md").write_text("x")
        out_path = self.dir / "sub" / "d.json"
        code, out, _ = self.run_main(["--transcript", str(self.path), "--skills-root", str(root),
                                      "--out", str(out_path)])
        self.assertEqual((code, out), (0, ""))
        data = json.loads(out_path.read_text())
        self.assertEqual(data["skills_used"][0]["root"], str(root))

    def test_missing_transcript_exit_3(self):
        code, out, err = self.run_main(["--transcript", str(self.dir / "missing.jsonl")])
        self.assertEqual((code, out), (3, ""))
        self.assertIn("cannot read", err)

    def test_unreadable_transcript_exit_3(self):
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("root can read anything")
        self.path.chmod(0)
        try:
            code, _, _ = self.run_main(["--transcript", str(self.path)])
        finally:
            self.path.chmod(0o644)
        self.assertEqual(code, 3)


if __name__ == "__main__":
    unittest.main()
