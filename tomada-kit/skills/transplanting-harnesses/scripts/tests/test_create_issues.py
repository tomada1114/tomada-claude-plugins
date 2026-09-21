#!/usr/bin/env python3
"""Tests for create_issues.py. Stdlib-only (unittest).

Run: python3 -m unittest discover -s scripts/tests -p 'test_*.py'
     (from the transplanting-harnesses skill directory)
"""
from __future__ import annotations

import io
import json
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _fakegh import FakeGh  # noqa: E402
import create_issues as ci  # noqa: E402


# --- fixtures ----------------------------------------------------------


def base_plan(repo: str = "acme/widgets") -> dict:
    return {
        "repo": repo,
        "reference": {"source": "https://example.com/ref", "commit": "abc123",
                      "license": "MIT", "snapshot_dir": "docs/harness-reference"},
        "labels": [{"name": "chore", "color": "ffffff", "description": "chore work"}],
        "tracking": {"title": "Transplant harness", "body_file": "bodies/tracking.md",
                     "labels": ["chore"]},
        "issues": [
            {"key": "agents-md", "title": "Add AGENTS.md", "body_file": "bodies/agents-md.md",
             "priority": "P0", "labels": ["chore"], "depends_on": [], "area": "policy-docs",
             "touches": ["AGENTS.md"], "design": "settled"},
            {"key": "ci-setup", "title": "Set up CI", "body_file": "bodies/ci-setup.md",
             "priority": "P1", "labels": [], "depends_on": ["agents-md"], "area": "ci",
             "touches": [], "design": "settled"},
        ],
    }


def base_bodies() -> dict:
    return {
        "tracking.md": "Tracking body referencing {{#agents-md}} and {{#ci-setup}}.\n",
        "agents-md.md": "Add AGENTS.md content.\n",
        "ci-setup.md": "Set up CI after {{#agents-md}}.\n",
    }


def write_plan(tmpdir: Path, plan: dict, bodies: dict) -> Path:
    bodies_dir = tmpdir / "bodies"
    bodies_dir.mkdir(exist_ok=True, parents=True)
    for name, content in bodies.items():
        (bodies_dir / name).write_text(content, encoding="utf-8")
    plan_path = tmpdir / "plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    return plan_path


def make_issue(key: str, priority: str = "P1", depends_on: list | None = None, **kw) -> ci.PlanIssue:
    fields = dict(title=key, body_file=f"{key}.md", body="body", priority=priority,
                  labels=[], depends_on=depends_on or [], area="a", touches=[], design="settled")
    fields.update(kw)
    return ci.PlanIssue(key=key, **fields)


def create_response(number: int, id_: int, url: str) -> str:
    return json.dumps({"number": number, "id": id_, "html_url": url})


# --- mirrors of shipping-issues/scripts/issue_digest.py's regex shapes ---
# Copied, not imported (skills do not share code across scripts/ trees) —
# see references/ship-contract.md. Used only to prove this script's output
# is readable by the consumer that actually parses it.
_SHIP_CONTRACT_RE = re.compile(r"<!--\s*ship\s*:(.*?)-->", re.DOTALL | re.IGNORECASE)
_CONTRACT_FIELD_RE = re.compile(r"([A-Za-z][\w-]*)\s*=\s*(\S+)")
_CONTRACT_REQUIRED_FIELDS = ("tier", "blocked-by", "touches")
_DEP_PATTERNS = [
    (re.compile(r"(?:depends?\s+on|blocked\s+by|after|requires?)\s*:?\s*#(\d+)", re.IGNORECASE), "depends_on"),
    (re.compile(r"(?:blocks|blocking)\s*:?\s*#(\d+)", re.IGNORECASE), "blocks"),
]


def parse_contract(body: str) -> dict | None:
    blocks = _SHIP_CONTRACT_RE.findall(body)
    if not blocks:
        return None
    raw: dict[str, str] = {}
    for block in blocks:
        for k, v in _CONTRACT_FIELD_RE.findall(block):
            raw[k.strip().lower()] = v.strip()
    return raw


def extract_deps(body: str, kind: str) -> list[int]:
    nums: list[int] = []
    for pat, k in _DEP_PATTERNS:
        if k == kind:
            nums += [int(n) for n in pat.findall(body)]
    return sorted(nums)


# --- validate_plan ----------------------------------------------------------


class ValidatePlanTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _write(self, plan=None, bodies=None) -> Path:
        return write_plan(self.tmpdir, plan if plan is not None else base_plan(),
                           bodies if bodies is not None else base_bodies())

    def _errors(self, plan=None, bodies=None, **kw):
        path = self._write(plan, bodies)
        _, errors = ci.validate_plan(json.loads(path.read_text(encoding="utf-8")), path, **kw)
        return errors

    def test_valid_plan_returns_plan_and_no_errors(self):
        path = self._write()
        plan, errors = ci.validate_plan(json.loads(path.read_text(encoding="utf-8")), path)
        self.assertEqual(errors, [])
        self.assertIsNotNone(plan)
        self.assertEqual(plan.repo, "acme/widgets")
        self.assertEqual([i.key for i in plan.issues], ["agents-md", "ci-setup"])
        self.assertEqual(plan.tracking.title, "Transplant harness")

    def test_non_dict_plan(self):
        errors = ci.validate_plan([], self.tmpdir / "plan.json")[1]
        self.assertTrue(any(e.code == "ERR_PLAN_MISSING_FIELD" for e in errors))

    def test_missing_repo(self):
        plan = base_plan(); del plan["repo"]
        errors = self._errors(plan)
        self.assertTrue(any(e.code == "ERR_PLAN_MISSING_FIELD" and "repo" in e.message for e in errors))

    def test_repo_bad_shape(self):
        plan = base_plan(); plan["repo"] = "not-a-slug"
        errors = self._errors(plan)
        self.assertTrue(any(e.code == "ERR_PLAN_MISSING_FIELD" and "owner/name" in e.message for e in errors))

    def test_repo_mismatch_is_an_error(self):
        errors = self._errors(local_repo="other/repo")
        self.assertTrue(any(e.code == "ERR_PLAN_REPO_MISMATCH" for e in errors))

    def test_repo_match_is_case_insensitive_and_clean(self):
        errors = self._errors(local_repo="ACME/Widgets")
        self.assertEqual(errors, [])

    def test_labels_top_level_not_a_list(self):
        plan = base_plan(); plan["labels"] = "nope"
        errors = self._errors(plan)
        self.assertTrue(any(e.code == "ERR_PLAN_MISSING_FIELD" and "'labels'" in e.message for e in errors))

    def test_label_entry_missing_name(self):
        plan = base_plan(); plan["labels"] = [{"color": "fff"}]
        errors = self._errors(plan)
        self.assertTrue(any("labels[0]" in e.message for e in errors))

    def test_label_defaults_applied(self):
        plan = base_plan(); plan["labels"] = [{"name": "only-name"}]
        path = self._write(plan)
        result, errors = ci.validate_plan(json.loads(path.read_text(encoding="utf-8")), path)
        self.assertEqual(errors, [])
        self.assertEqual(result.labels[0], {"name": "only-name", "color": "ededed", "description": ""})

    def test_tracking_not_an_object(self):
        plan = base_plan(); plan["tracking"] = "nope"
        errors = self._errors(plan)
        self.assertTrue(any(e.code == "ERR_PLAN_MISSING_FIELD" and "'tracking'" in e.message for e in errors))

    def test_tracking_missing_title(self):
        plan = base_plan(); del plan["tracking"]["title"]
        errors = self._errors(plan)
        self.assertTrue(any("tracking.title is required" in e.message for e in errors))

    def test_tracking_missing_body_file_field(self):
        plan = base_plan(); del plan["tracking"]["body_file"]
        errors = self._errors(plan)
        self.assertTrue(any("tracking.body_file is required" in e.message for e in errors))

    def test_tracking_labels_wrong_type(self):
        plan = base_plan(); plan["tracking"]["labels"] = "nope"
        errors = self._errors(plan)
        self.assertTrue(any("tracking.labels must be a list" in e.message for e in errors))

    def test_tracking_body_file_missing_on_disk(self):
        plan = base_plan(); plan["tracking"]["body_file"] = "bodies/nope.md"
        errors = self._errors(plan)
        self.assertTrue(any(e.code == "ERR_PLAN_BODY_MISSING" and "tracking.body_file" in e.message
                             for e in errors))

    def test_tracking_body_reserved_marker(self):
        bodies = base_bodies()
        bodies["tracking.md"] = "Body\n\n<!-- harness-transplant: key=tracking -->\n"
        errors = self._errors(bodies=bodies)
        self.assertTrue(any(e.code == "ERR_PLAN_RESERVED_CONTENT" for e in errors))

    def test_issues_not_a_nonempty_list(self):
        plan = base_plan(); plan["issues"] = []
        errors = self._errors(plan)
        self.assertTrue(any(e.code == "ERR_PLAN_MISSING_FIELD" and "'issues'" in e.message for e in errors))

    def test_issue_entry_not_an_object(self):
        plan = base_plan(); plan["issues"].append("nope")
        errors = self._errors(plan)
        self.assertTrue(any("issues[2] must be an object" in e.message for e in errors))

    def test_issue_missing_key(self):
        plan = base_plan(); del plan["issues"][0]["key"]
        errors = self._errors(plan)
        self.assertTrue(any("key is required" in e.message for e in errors))

    def test_invalid_key_format(self):
        plan = base_plan(); plan["issues"][0]["key"] = "Bad_Key"
        errors = self._errors(plan)
        self.assertTrue(any(e.code == "ERR_PLAN_INVALID_KEY" for e in errors))

    def test_reserved_key_tracking(self):
        plan = base_plan(); plan["issues"][0]["key"] = "tracking"
        errors = self._errors(plan)
        self.assertTrue(any(e.code == "ERR_PLAN_INVALID_KEY" and "reserved" in e.message for e in errors))

    def test_duplicate_key(self):
        plan = base_plan(); plan["issues"][1]["key"] = "agents-md"
        errors = self._errors(plan)
        self.assertTrue(any(e.code == "ERR_PLAN_DUPLICATE_KEY" for e in errors))

    def test_issue_missing_title(self):
        plan = base_plan(); del plan["issues"][0]["title"]
        errors = self._errors(plan)
        self.assertTrue(any("title is required" in e.message for e in errors))

    def test_issue_missing_body_file_field(self):
        plan = base_plan(); del plan["issues"][0]["body_file"]
        errors = self._errors(plan)
        self.assertTrue(any("body_file is required" in e.message for e in errors))

    def test_missing_body_file_on_disk(self):
        plan = base_plan(); plan["issues"][0]["body_file"] = "bodies/missing.md"
        errors = self._errors(plan)
        self.assertTrue(any(e.code == "ERR_PLAN_BODY_MISSING" for e in errors))

    def test_empty_body_file(self):
        bodies = base_bodies(); bodies["agents-md.md"] = "   \n"
        errors = self._errors(bodies=bodies)
        self.assertTrue(any(e.code == "ERR_PLAN_BODY_EMPTY" for e in errors))

    def test_unknown_dependency(self):
        plan = base_plan(); plan["issues"][1]["depends_on"] = ["nope"]
        errors = self._errors(plan)
        self.assertTrue(any(e.code == "ERR_PLAN_UNKNOWN_DEPENDENCY" for e in errors))

    def test_unknown_dependency_not_double_reported_for_broken_target(self):
        # ci-setup depends on "agents-md", and that key is spelled correctly,
        # but it is excluded from by_key because it is a duplicate — that
        # already produces ERR_PLAN_DUPLICATE_KEY, so it should not also cause
        # an UNKNOWN_DEPENDENCY finding for ci-setup.
        plan = base_plan()
        plan["issues"].append(dict(plan["issues"][0]))  # duplicate "agents-md" key
        errors = self._errors(plan)
        self.assertTrue(any(e.code == "ERR_PLAN_DUPLICATE_KEY" for e in errors))
        self.assertFalse(any(e.code == "ERR_PLAN_UNKNOWN_DEPENDENCY" for e in errors))

    def test_self_dependency(self):
        plan = base_plan(); plan["issues"][0]["depends_on"] = ["agents-md"]
        errors = self._errors(plan)
        self.assertTrue(any(e.code == "ERR_PLAN_SELF_DEPENDENCY" for e in errors))

    def test_cycle_detected_and_named(self):
        plan = base_plan()
        plan["issues"][0]["depends_on"] = ["ci-setup"]
        errors = self._errors(plan)
        cycles = [e for e in errors if e.code == "ERR_PLAN_CYCLE"]
        self.assertEqual(len(cycles), 1)
        self.assertIn("agents-md", cycles[0].message)
        self.assertIn("ci-setup", cycles[0].message)
        self.assertIn("->", cycles[0].message)

    def test_invalid_priority(self):
        plan = base_plan(); plan["issues"][0]["priority"] = "P9"
        errors = self._errors(plan)
        self.assertTrue(any(e.code == "ERR_PLAN_INVALID_PRIORITY" for e in errors))

    def test_priority_inversion(self):
        plan = base_plan()
        plan["issues"][0]["priority"] = "P3"  # blocker
        plan["issues"][1]["priority"] = "P0"  # depends on the P3 blocker
        errors = self._errors(plan)
        self.assertTrue(any(e.code == "ERR_PLAN_PRIORITY_INVERSION" for e in errors))

    def test_no_inversion_when_blocker_is_equal_or_higher_priority(self):
        errors = self._errors()  # base_plan: agents-md P0 blocks ci-setup P1
        self.assertFalse(any(e.code == "ERR_PLAN_PRIORITY_INVERSION" for e in errors))

    def test_invalid_design(self):
        plan = base_plan(); plan["issues"][0]["design"] = "maybe"
        errors = self._errors(plan)
        self.assertTrue(any(e.code == "ERR_PLAN_INVALID_DESIGN" for e in errors))

    def test_wrong_type_fields_on_issue(self):
        plan = base_plan()
        plan["issues"][0]["labels"] = "nope"
        plan["issues"][0]["depends_on"] = "nope"
        plan["issues"][0]["touches"] = "nope"
        errors = self._errors(plan)
        msgs = [e.message for e in errors]
        self.assertTrue(any("labels must be a list" in m for m in msgs))
        self.assertTrue(any("depends_on must be a list" in m for m in msgs))
        self.assertTrue(any("touches must be a list" in m for m in msgs))

    def test_area_required(self):
        plan = base_plan(); del plan["issues"][0]["area"]
        errors = self._errors(plan)
        self.assertTrue(any(e.code == "ERR_PLAN_MISSING_FIELD" and "area" in e.message for e in errors))

    def test_defaults_for_optional_fields(self):
        plan = base_plan()
        for issue in plan["issues"]:
            issue.pop("labels", None)
            issue.pop("touches", None)
            issue.pop("design", None)
        path = self._write(plan)
        result, errors = ci.validate_plan(json.loads(path.read_text(encoding="utf-8")), path)
        self.assertEqual(errors, [])
        first = result.issues[0]
        self.assertEqual(first.labels, [])
        self.assertEqual(first.touches, [])
        self.assertEqual(first.design, "settled")

    def test_unknown_placeholder_in_issue_body(self):
        bodies = base_bodies(); bodies["agents-md.md"] = "See {{#nope}}.\n"
        errors = self._errors(bodies=bodies)
        self.assertTrue(any(e.code == "ERR_PLAN_UNKNOWN_PLACEHOLDER" for e in errors))

    def test_unknown_placeholder_in_tracking_body(self):
        bodies = base_bodies(); bodies["tracking.md"] = "See {{#nope}}.\n"
        errors = self._errors(bodies=bodies)
        self.assertTrue(any(e.code == "ERR_PLAN_UNKNOWN_PLACEHOLDER" for e in errors))

    def test_tracking_placeholder_reference_is_allowed(self):
        bodies = base_bodies(); bodies["agents-md.md"] = "See {{#tracking}} for context.\n"
        errors = self._errors(bodies=bodies)
        self.assertEqual(errors, [])

    def test_reserved_dependencies_heading(self):
        bodies = base_bodies(); bodies["agents-md.md"] = "Body\n\n## Dependencies\n\nNone\n"
        errors = self._errors(bodies=bodies)
        self.assertTrue(any(e.code == "ERR_PLAN_RESERVED_CONTENT" and "Dependencies" in e.message
                             for e in errors))

    def test_reserved_ship_contract(self):
        bodies = base_bodies(); bodies["agents-md.md"] = "Body\n\n<!-- ship: tier=P0 -->\n"
        errors = self._errors(bodies=bodies)
        self.assertTrue(any(e.code == "ERR_PLAN_RESERVED_CONTENT" and "contract" in e.message
                             for e in errors))

    def test_reserved_marker(self):
        bodies = base_bodies()
        bodies["agents-md.md"] = "Body\n\n<!-- harness-transplant: key=agents-md -->\n"
        errors = self._errors(bodies=bodies)
        self.assertTrue(any(e.code == "ERR_PLAN_RESERVED_CONTENT" and "marker" in e.message
                             for e in errors))

    def test_out_of_repo_reference_rejected(self):
        for text in ("see plan.json for order", "copy /Users/someone/ref/AGENTS.md",
                     "read /home/ci/ref/x", "in ~/.local/state/run"):
            bodies = base_bodies(); bodies["agents-md.md"] = f"Body\n\n{text}\n"
            errors = self._errors(bodies=bodies)
            self.assertTrue(any(e.code == "ERR_PLAN_OUT_OF_REPO_REF" for e in errors), text)

    def test_in_repo_paths_are_not_out_of_repo(self):
        bodies = base_bodies()
        bodies["agents-md.md"] = "Body\n\nSee `docs/harness-reference/AGENTS.md` and docs/home/x.\n"
        self.assertEqual(self._errors(bodies=bodies), [])

    def test_stray_dependency_phrase_rejected(self):
        errs = ci.stray_dependency_errors("a", "do this after\n   {{#b}} lands", [], [])
        self.assertEqual([e.code for e in errs], ["ERR_PLAN_STRAY_DEPENDENCY_PHRASE"])
        self.assertIn("after {{#b}}", errs[0].message)
        errs = ci.stray_dependency_errors("a", "this blocks {{#c}}", [], [])
        self.assertEqual(len(errs), 1)
        errs = ci.stray_dependency_errors("a", "{{#b}} の後にやる", [], [])
        self.assertEqual(len(errs), 1)

    def test_declared_or_neutral_phrases_pass(self):
        self.assertEqual(ci.stray_dependency_errors("a", "after {{#b}}", ["b"], []), [])
        self.assertEqual(ci.stray_dependency_errors("a", "blocks {{#c}}", [], ["c"]), [])
        self.assertEqual(ci.stray_dependency_errors("a", "once {{#b}} lands; see {{#c}}", [], []), [])
        self.assertEqual(ci.stray_dependency_errors("a", "after {{#a}}", [], []), [])

    def test_multiple_errors_collected_together(self):
        plan = base_plan()
        plan["issues"][0]["priority"] = "P9"
        plan["issues"][1]["key"] = "Bad Key"
        errors = self._errors(plan)
        codes = {e.code for e in errors}
        self.assertIn("ERR_PLAN_INVALID_PRIORITY", codes)
        self.assertIn("ERR_PLAN_INVALID_KEY", codes)
        self.assertGreaterEqual(len(errors), 2)


# --- find_cycle / topo_order -------------------------------------------


class FindCycleTest(unittest.TestCase):
    def test_acyclic_returns_none(self):
        self.assertIsNone(ci.find_cycle({"a": ["b"], "b": []}))

    def test_two_node_cycle(self):
        cycle = ci.find_cycle({"a": ["b"], "b": ["a"]})
        self.assertIsNotNone(cycle)
        self.assertEqual(cycle[0], cycle[-1])
        self.assertEqual(set(cycle), {"a", "b"})

    def test_three_node_cycle(self):
        cycle = ci.find_cycle({"a": ["b"], "b": ["c"], "c": ["a"]})
        self.assertIsNotNone(cycle)
        self.assertEqual(cycle[0], cycle[-1])
        self.assertEqual(set(cycle), {"a", "b", "c"})

    def test_disjoint_components_one_cyclic(self):
        cycle = ci.find_cycle({"a": [], "b": ["c"], "c": ["b"]})
        self.assertIsNotNone(cycle)
        self.assertEqual(cycle[0], cycle[-1])
        self.assertEqual(set(cycle), {"b", "c"})
        self.assertNotIn("a", cycle)


class TopoOrderTest(unittest.TestCase):
    def test_simple_chain(self):
        issues = [make_issue("b", priority="P1", depends_on=["a"]), make_issue("a", priority="P0")]
        order = ci.topo_order(issues)
        self.assertEqual([i.key for i in order], ["a", "b"])

    def test_ties_broken_by_priority_first(self):
        issues = [make_issue("low", priority="P2"), make_issue("high", priority="P0")]
        order = ci.topo_order(issues)
        self.assertEqual([i.key for i in order], ["high", "low"])

    def test_ties_broken_by_plan_order_when_priority_equal(self):
        issues = [make_issue("second", priority="P1"), make_issue("first", priority="P1")]
        order = ci.topo_order(issues)
        self.assertEqual([i.key for i in order], ["second", "first"])

    def test_diamond_dependency(self):
        issues = [
            make_issue("root", priority="P0"),
            make_issue("left", priority="P1", depends_on=["root"]),
            make_issue("right", priority="P2", depends_on=["root"]),
            make_issue("tip", priority="P0", depends_on=["left", "right"]),
        ]
        order = [i.key for i in ci.topo_order(issues)]
        self.assertEqual(order[0], "root")
        self.assertEqual(order[-1], "tip")
        self.assertLess(order.index("left"), order.index("tip"))
        self.assertLess(order.index("right"), order.index("tip"))


# --- body assembly (pure functions) -------------------------------------


class BodyAssemblyTest(unittest.TestCase):
    def test_dependencies_section_lists_both_kinds(self):
        section = ci.dependencies_section([11], [13])
        self.assertEqual(section, "## Dependencies\n\n- Depends on #11\n- Blocks #13")

    def test_dependencies_section_none_when_both_empty(self):
        self.assertEqual(ci.dependencies_section([], []), "## Dependencies\n\nNone")

    def test_contract_line_all_fields(self):
        line = ci.contract_line("P1", "ci", [11], [13], ["ci/", "Makefile"], "settled")
        self.assertEqual(
            line,
            "<!-- ship: tier=P1 area=ci blocked-by=#11 blocks=#13 "
            "touches=ci/,Makefile design=settled -->",
        )

    def test_contract_line_empty_becomes_none_and_star(self):
        line = ci.contract_line("P0", "policy-docs", [], [], [], "open")
        self.assertIn("blocked-by=none", line)
        self.assertIn("blocks=none", line)
        self.assertIn("touches=*", line)
        self.assertIn("design=open", line)

    def test_contract_parses_with_shipping_issues_regex_shape(self):
        line = ci.contract_line("P1", "ci", [11], [13], ["ci/"], "settled")
        parsed = parse_contract(line)
        self.assertIsNotNone(parsed)
        for field in _CONTRACT_REQUIRED_FIELDS:
            self.assertIn(field, parsed)
        self.assertEqual(parsed["tier"], "P1")
        self.assertEqual(parsed["area"], "ci")
        self.assertEqual(parsed["blocked-by"], "#11")
        self.assertEqual(parsed["blocks"], "#13")
        self.assertEqual(parsed["touches"], "ci/")
        self.assertEqual(parsed["design"], "settled")

    def test_dependencies_lines_match_shipping_issues_dep_patterns(self):
        section = ci.dependencies_section([11], [13])
        self.assertEqual(extract_deps(section, "depends_on"), [11])
        self.assertEqual(extract_deps(section, "blocks"), [13])

    def test_pass1_body_unresolved_placeholder_plus_marker(self):
        issue = make_issue("ci-setup", body="See {{#agents-md}}.")
        body = ci.pass1_body(issue.body, issue.key)
        self.assertIn("{{#agents-md}}", body)
        self.assertTrue(body.rstrip().endswith(ci.marker("ci-setup")))

    def test_pass2_issue_body_full_shape(self):
        issue = make_issue("ci-setup", priority="P1", depends_on=["agents-md"],
                            area="ci", touches=["ci/"], body="See {{#agents-md}}.")
        numbers = {"agents-md": 11, "ci-setup": 12}
        body = ci.pass2_issue_body(issue, numbers, [15])
        self.assertNotIn("{{#agents-md}}", body)
        self.assertIn("#11", body)
        self.assertIn("## Dependencies", body)
        self.assertIn("- Depends on #11", body)
        self.assertIn("- Blocks #15", body)
        self.assertIn(ci.marker("ci-setup"), body)
        parsed = parse_contract(body)
        self.assertIsNotNone(parsed)
        for field in _CONTRACT_REQUIRED_FIELDS:
            self.assertIn(field, parsed)
        self.assertEqual(extract_deps(body, "depends_on"), [11])
        self.assertEqual(extract_deps(body, "blocks"), [15])

    def test_pass2_issue_body_none_dependencies(self):
        issue = make_issue("standalone", priority="P2", depends_on=[])
        body = ci.pass2_issue_body(issue, {"standalone": 20}, [])
        self.assertIn("## Dependencies\n\nNone", body)

    def test_pass2_tracking_body_has_sub_issues_and_marker(self):
        tracking = ci.TrackingInfo(title="T", body_file="t.md", body="See {{#agents-md}}.", labels=[])
        body = ci.pass2_tracking_body(
            tracking, {"agents-md": 11}, [(11, "Add AGENTS.md"), (12, "Set up CI")],
        )
        self.assertIn("#11", body)
        self.assertIn("## Sub-issues", body)
        self.assertIn("- [ ] #11 Add AGENTS.md", body)
        self.assertIn("- [ ] #12 Set up CI", body)
        self.assertIn(ci.marker("tracking"), body)
        self.assertIn("<!-- ship: tier=P3 area=tracking blocked-by=#11,#12 blocks=none "
                      "touches=* design=settled -->", body)


# --- plumbing: parse_concatenated_json / created.json -------------------


class ParseConcatenatedJsonTest(unittest.TestCase):
    def test_single_array(self):
        self.assertEqual(ci.parse_concatenated_json('[{"a": 1}]'), [{"a": 1}])

    def test_multiple_arrays_concatenated(self):
        self.assertEqual(
            ci.parse_concatenated_json('[{"a": 1}][{"b": 2}]'), [{"a": 1}, {"b": 2}],
        )

    def test_whitespace_between_documents(self):
        self.assertEqual(
            ci.parse_concatenated_json('[{"a": 1}]\n[{"b": 2}]\n'), [{"a": 1}, {"b": 2}],
        )

    def test_empty_string(self):
        self.assertEqual(ci.parse_concatenated_json(""), [])

    def test_single_object_not_wrapped_in_array(self):
        self.assertEqual(ci.parse_concatenated_json('{"a": 1}'), [{"a": 1}])


class CreatedJsonTest(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "created.json"
            data = {"tracking": ci.CreatedEntry(1, 2, "u")}
            ci.save_created(path, data)
            loaded = ci.load_created(path)
            self.assertEqual(loaded["tracking"].number, 1)
            self.assertEqual(loaded["tracking"].id, 2)
            self.assertEqual(loaded["tracking"].url, "u")

    def test_missing_file_returns_empty(self):
        self.assertEqual(ci.load_created(Path("/nonexistent-dir/created.json")), {})

    def test_corrupt_json_returns_empty(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "created.json"
            path.write_text("not json", encoding="utf-8")
            self.assertEqual(ci.load_created(path), {})

    def test_non_dict_json_returns_empty(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "created.json"
            path.write_text("[]", encoding="utf-8")
            self.assertEqual(ci.load_created(path), {})

    def test_malformed_entries_are_skipped(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "created.json"
            path.write_text(json.dumps({"a": {"number": 1}, "b": "not-a-dict"}), encoding="utf-8")
            self.assertEqual(ci.load_created(path), {})


# --- resolve_local_repo ---------------------------------------------------


class ResolveLocalRepoTest(unittest.TestCase):
    def test_not_a_git_repo_returns_none(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertIsNone(ci.resolve_local_repo(Path(td)))

    def test_parses_https_url(self):
        with patch("create_issues.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="https://github.com/acme/widgets.git\n", stderr="",
            )
            self.assertEqual(ci.resolve_local_repo(Path(".")), "acme/widgets")

    def test_parses_ssh_url(self):
        with patch("create_issues.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="git@github.com:acme/widgets.git\n", stderr="",
            )
            self.assertEqual(ci.resolve_local_repo(Path(".")), "acme/widgets")

    def test_nonzero_returncode_is_none(self):
        with patch("create_issues.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="x")
            self.assertIsNone(ci.resolve_local_repo(Path(".")))

    def test_oserror_is_none(self):
        with patch("create_issues.subprocess.run", side_effect=OSError("boom")):
            self.assertIsNone(ci.resolve_local_repo(Path(".")))


# --- run_gh ------------------------------------------------------------


class RunGhTest(unittest.TestCase):
    def test_gh_not_found_raises_gherror(self):
        with patch("create_issues.subprocess.run", side_effect=FileNotFoundError()):
            with self.assertRaises(ci.GhError) as cm:
                ci.run_gh(["issue", "list"])
        self.assertEqual(cm.exception.code, "ERR_GH_NOT_FOUND")

    def test_timeout_raises_gherror(self):
        with patch("create_issues.subprocess.run",
                   side_effect=subprocess.TimeoutExpired(cmd="gh", timeout=1)):
            with self.assertRaises(ci.GhError) as cm:
                ci.run_gh(["issue", "list"])
        self.assertEqual(cm.exception.code, "ERR_GH_TIMEOUT")


# --- gh-backed unit helpers (via FakeGh) --------------------------------


class UpsertLabelTest(unittest.TestCase):
    def test_success(self):
        with FakeGh({("label", "create"): ""}) as fake:
            with patch.dict("os.environ", fake.env, clear=False):
                ci.upsert_label("acme/widgets", "chore", "ffffff", "d")

    def test_failure_raises(self):
        prefix = ("label", "create")
        with FakeGh({prefix: ""}, exits={prefix: 1}, stderrs={prefix: "HTTP 403"}) as fake:
            with patch.dict("os.environ", fake.env, clear=False):
                with self.assertRaises(ci.GhError) as cm:
                    ci.upsert_label("acme/widgets", "chore", "ffffff", "d")
        self.assertEqual(cm.exception.code, "ERR_GH_LABEL_FAILED")


class FetchAllIssuesTest(unittest.TestCase):
    def test_filters_pull_requests(self):
        existing = [
            {"number": 1, "id": 11, "html_url": "u1", "body": "x"},
            {"number": 2, "id": 12, "html_url": "u2", "body": "y", "pull_request": {}},
        ]
        prefix = ("api", "repos/acme/widgets/issues", "--method", "GET")
        with FakeGh({prefix: json.dumps(existing)}) as fake:
            with patch.dict("os.environ", fake.env, clear=False):
                result = ci.fetch_all_issues("acme/widgets")
        self.assertEqual([it["number"] for it in result], [1])

    def test_failure_raises(self):
        prefix = ("api", "repos/acme/widgets/issues", "--method", "GET")
        with FakeGh({prefix: ""}, exits={prefix: 1}, stderrs={prefix: "boom"}) as fake:
            with patch.dict("os.environ", fake.env, clear=False):
                with self.assertRaises(ci.GhError) as cm:
                    ci.fetch_all_issues("acme/widgets")
        self.assertEqual(cm.exception.code, "ERR_GH_LIST_FAILED")


class ScanExistingByKeyTest(unittest.TestCase):
    def test_finds_markers_and_ignores_unmarked(self):
        existing = [
            {"number": 1, "id": 11, "html_url": "u1",
             "body": "x <!-- harness-transplant: key=agents-md -->"},
            {"number": 2, "id": 12, "html_url": "u2", "body": "no marker here"},
            {"number": 3, "id": 13, "html_url": "u3",
             "body": "<!-- harness-transplant: key=tracking -->"},
        ]
        prefix = ("api", "repos/acme/widgets/issues", "--method", "GET")
        with FakeGh({prefix: json.dumps(existing)}) as fake:
            with patch.dict("os.environ", fake.env, clear=False):
                found = ci.scan_existing_by_key("acme/widgets")
        self.assertEqual(set(found), {"agents-md", "tracking"})
        self.assertEqual(found["agents-md"].number, 1)
        self.assertEqual(found["tracking"].id, 13)


class CreateIssueTest(unittest.TestCase):
    def test_success(self):
        prefix = ("api", "repos/acme/widgets/issues", "--method", "POST")
        with FakeGh({prefix: create_response(5, 55, "u")}) as fake:
            with patch.dict("os.environ", fake.env, clear=False):
                entry = ci.create_issue("acme/widgets", "T", "B", ["chore"])
        self.assertEqual(entry, ci.CreatedEntry(5, 55, "u"))

    def test_failure_raises(self):
        prefix = ("api", "repos/acme/widgets/issues", "--method", "POST")
        with FakeGh({prefix: ""}, exits={prefix: 1}, stderrs={prefix: "boom"}) as fake:
            with patch.dict("os.environ", fake.env, clear=False):
                with self.assertRaises(ci.GhError) as cm:
                    ci.create_issue("acme/widgets", "T", "B", [])
        self.assertEqual(cm.exception.code, "ERR_GH_CREATE_FAILED")

    def test_bad_json_response_raises(self):
        prefix = ("api", "repos/acme/widgets/issues", "--method", "POST")
        with FakeGh({prefix: "not json"}) as fake:
            with patch.dict("os.environ", fake.env, clear=False):
                with self.assertRaises(ci.GhError) as cm:
                    ci.create_issue("acme/widgets", "T", "B", [])
        self.assertEqual(cm.exception.code, "ERR_GH_CREATE_FAILED")


class PatchIssueBodyTest(unittest.TestCase):
    def test_success(self):
        prefix = ("api", "repos/acme/widgets/issues/5", "--method", "PATCH")
        with FakeGh({prefix: ""}) as fake:
            with patch.dict("os.environ", fake.env, clear=False):
                ci.patch_issue_body("acme/widgets", 5, "body")

    def test_failure_raises(self):
        prefix = ("api", "repos/acme/widgets/issues/5", "--method", "PATCH")
        with FakeGh({prefix: ""}, exits={prefix: 1}, stderrs={prefix: "boom"}) as fake:
            with patch.dict("os.environ", fake.env, clear=False):
                with self.assertRaises(ci.GhError) as cm:
                    ci.patch_issue_body("acme/widgets", 5, "body")
        self.assertEqual(cm.exception.code, "ERR_GH_PATCH_FAILED")


class LinkHelpersTest(unittest.TestCase):
    def test_link_sub_issue_success(self):
        prefix = ("api", "repos/acme/widgets/issues/1/sub_issues", "--method", "POST")
        with FakeGh({prefix: ""}) as fake:
            with patch.dict("os.environ", fake.env, clear=False):
                ok, warning = ci.link_sub_issue("acme/widgets", 1, 99)
        self.assertTrue(ok)
        self.assertEqual(warning, "")

    def test_link_sub_issue_422_counts_as_success(self):
        prefix = ("api", "repos/acme/widgets/issues/1/sub_issues", "--method", "POST")
        with FakeGh({prefix: ""}, exits={prefix: 1},
                   stderrs={prefix: "HTTP 422: already a sub-issue"}) as fake:
            with patch.dict("os.environ", fake.env, clear=False):
                ok, warning = ci.link_sub_issue("acme/widgets", 1, 99)
        self.assertTrue(ok)
        self.assertEqual(warning, "")

    def test_link_sub_issue_other_failure_is_warning(self):
        prefix = ("api", "repos/acme/widgets/issues/1/sub_issues", "--method", "POST")
        with FakeGh({prefix: ""}, exits={prefix: 1}, stderrs={prefix: "HTTP 500: boom"}) as fake:
            with patch.dict("os.environ", fake.env, clear=False):
                ok, warning = ci.link_sub_issue("acme/widgets", 1, 99)
        self.assertFalse(ok)
        self.assertIn("500", warning)

    def test_link_blocked_by_success(self):
        prefix = ("api", "repos/acme/widgets/issues/2/dependencies/blocked_by", "--method", "POST")
        with FakeGh({prefix: ""}) as fake:
            with patch.dict("os.environ", fake.env, clear=False):
                ok, warning = ci.link_blocked_by("acme/widgets", 2, 55)
        self.assertTrue(ok)
        self.assertEqual(warning, "")

    def test_link_blocked_by_failure_is_warning(self):
        prefix = ("api", "repos/acme/widgets/issues/2/dependencies/blocked_by", "--method", "POST")
        with FakeGh({prefix: ""}, exits={prefix: 1}, stderrs={prefix: "HTTP 500: boom"}) as fake:
            with patch.dict("os.environ", fake.env, clear=False):
                ok, warning = ci.link_blocked_by("acme/widgets", 2, 55)
        self.assertFalse(ok)
        self.assertIn("500", warning)

    def test_link_blocked_by_422_counts_as_success(self):
        prefix = ("api", "repos/acme/widgets/issues/2/dependencies/blocked_by", "--method", "POST")
        with FakeGh({prefix: ""}, exits={prefix: 1},
                   stderrs={prefix: "HTTP 422: already blocked by that issue"}) as fake:
            with patch.dict("os.environ", fake.env, clear=False):
                ok, warning = ci.link_blocked_by("acme/widgets", 2, 55)
        self.assertTrue(ok)
        self.assertEqual(warning, "")


# --- CLI: dry run --------------------------------------------------------


class DryRunTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _write(self, plan=None, bodies=None) -> Path:
        return write_plan(self.tmpdir, plan if plan is not None else base_plan(),
                           bodies if bodies is not None else base_bodies())

    def test_prints_order_table_and_exits_0(self):
        path = self._write()
        out, err = io.StringIO(), io.StringIO()
        with patch.object(ci, "resolve_local_repo", return_value=None), \
                redirect_stdout(out), redirect_stderr(err):
            rc = ci.main([str(path)])
        self.assertEqual(rc, 0, err.getvalue())
        text = out.getvalue()
        self.assertIn("agents-md", text)
        self.assertIn("ci-setup", text)
        self.assertIn("Dry run: no GitHub writes were made", text)
        self.assertLess(text.index("agents-md"), text.index("ci-setup"))

    def test_json_output(self):
        path = self._write()
        out = io.StringIO()
        with patch.object(ci, "resolve_local_repo", return_value=None), redirect_stdout(out):
            rc = ci.main([str(path), "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(out.getvalue())
        self.assertTrue(payload["dry_run"])
        self.assertEqual(payload["repo"], "acme/widgets")
        self.assertEqual([r["key"] for r in payload["order"]], ["agents-md", "ci-setup"])
        self.assertEqual(payload["order"][1]["depends_on"], ["agents-md"])

    def test_makes_no_gh_calls(self):
        path = self._write()
        out = io.StringIO()
        with patch.object(ci, "resolve_local_repo", return_value=None), \
                patch.object(ci, "run_gh",
                             side_effect=AssertionError("gh must not be called in a dry run")), \
                redirect_stdout(out):
            rc = ci.main([str(path)])
        self.assertEqual(rc, 0)

    def test_validation_errors_exit_2_with_codes_on_stderr(self):
        plan = base_plan(); plan["issues"][0]["priority"] = "P9"
        path = self._write(plan)
        out, err = io.StringIO(), io.StringIO()
        with patch.object(ci, "resolve_local_repo", return_value=None), \
                redirect_stdout(out), redirect_stderr(err):
            rc = ci.main([str(path)])
        self.assertEqual(rc, 2)
        self.assertIn("ERR_PLAN_INVALID_PRIORITY", err.getvalue())
        self.assertEqual(out.getvalue(), "")

    def test_missing_plan_file_exits_2(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = ci.main([str(self.tmpdir / "nope.json")])
        self.assertEqual(rc, 2)
        self.assertIn("ERR_PLAN_NOT_FOUND", err.getvalue())

    def test_invalid_json_exits_2(self):
        bad = self.tmpdir / "plan.json"
        bad.write_text("{not json", encoding="utf-8")
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = ci.main([str(bad)])
        self.assertEqual(rc, 2)
        self.assertIn("ERR_PLAN_INVALID_JSON", err.getvalue())

    def test_help_exits_0(self):
        with self.assertRaises(SystemExit) as cm:
            ci.main(["--help"])
        self.assertEqual(cm.exception.code, 0)


# --- CLI: apply ----------------------------------------------------------


class ApplyTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _write(self, plan=None, bodies=None) -> Path:
        return write_plan(self.tmpdir, plan if plan is not None else base_plan(),
                           bodies if bodies is not None else base_bodies())

    def _run(self, path, extra_args, responses, exits=None, stderrs=None, local_repo="acme/widgets"):
        with FakeGh(responses, exits=exits, stderrs=stderrs) as fake:
            out, err = io.StringIO(), io.StringIO()
            with patch.dict("os.environ", fake.env, clear=False), \
                    patch.object(ci, "resolve_local_repo", return_value=local_repo), \
                    redirect_stdout(out), redirect_stderr(err):
                rc = ci.main([str(path), "--apply", *extra_args])
            calls = fake.calls
        return rc, out.getvalue(), err.getvalue(), calls

    def test_happy_path_creates_labels_tracking_issues_and_links(self):
        path = self._write()
        responses = {
            ("api", "repos/acme/widgets/issues", "--method", "GET"): "[]",
            ("api", "repos/acme/widgets/issues", "--method", "POST"): [
                create_response(100, 9100, "https://github.com/acme/widgets/issues/100"),
                create_response(101, 9101, "https://github.com/acme/widgets/issues/101"),
                create_response(102, 9102, "https://github.com/acme/widgets/issues/102"),
            ],
        }
        rc, out, err, calls = self._run(path, ["--json"], responses)
        self.assertEqual(rc, 0, err)
        payload = json.loads(out)
        self.assertEqual(payload["tracking"], {
            "number": 100, "url": "https://github.com/acme/widgets/issues/100", "status": "created",
        })
        self.assertEqual(payload["counts"], {"created": 3, "reused": 0, "link_warnings": 0})
        self.assertEqual({row["key"]: row["number"] for row in payload["issues"]},
                          {"agents-md": 101, "ci-setup": 102})

        label_calls = [c for c in calls if c[:2] == ["label", "create"]]
        self.assertEqual({c[2] for c in label_calls}, {"chore", "priority: P0", "priority: P1"})

        create_calls = [c for c in calls
                        if c[:4] == ["api", "repos/acme/widgets/issues", "--method", "POST"]]
        self.assertEqual(len(create_calls), 3)

        patch_calls = [c for c in calls if len(c) >= 4 and c[0] == "api" and c[2:4] == ["--method", "PATCH"]]
        self.assertEqual({c[1] for c in patch_calls}, {
            "repos/acme/widgets/issues/100",
            "repos/acme/widgets/issues/101",
            "repos/acme/widgets/issues/102",
        })

        sub_issue_calls = [c for c in calls if c[1] == "repos/acme/widgets/issues/100/sub_issues"]
        self.assertEqual(len(sub_issue_calls), 2)

        blocked_by_calls = [c for c in calls if "dependencies/blocked_by" in c[1]]
        self.assertEqual(len(blocked_by_calls), 1)
        self.assertEqual(blocked_by_calls[0][1],
                         "repos/acme/widgets/issues/102/dependencies/blocked_by")
        self.assertIn("issue_id=9101", blocked_by_calls[0])

        created = json.loads((self.tmpdir / "created.json").read_text(encoding="utf-8"))
        self.assertEqual(set(created), {"tracking", "agents-md", "ci-setup"})
        self.assertEqual(created["agents-md"]["number"], 101)

    def test_human_readable_summary(self):
        path = self._write()
        responses = {
            ("api", "repos/acme/widgets/issues", "--method", "GET"): "[]",
            ("api", "repos/acme/widgets/issues", "--method", "POST"): [
                create_response(100, 9100, "u100"),
                create_response(101, 9101, "u101"),
                create_response(102, 9102, "u102"),
            ],
        }
        rc, out, err, _ = self._run(path, [], responses)
        self.assertEqual(rc, 0, err)
        self.assertIn("Tracking: u100", out)
        self.assertIn("created: 3, reused: 0, link warnings: 0", out)

    def test_idempotent_rerun_reuses_marked_issues(self):
        path = self._write()
        existing = [
            {"number": 55, "id": 8055, "html_url": "u55",
             "body": "...\n\n<!-- harness-transplant: key=tracking -->\n"},
            {"number": 56, "id": 8056, "html_url": "u56",
             "body": "...\n\n<!-- harness-transplant: key=agents-md -->\n"},
        ]
        responses = {
            ("api", "repos/acme/widgets/issues", "--method", "GET"): json.dumps(existing),
            ("api", "repos/acme/widgets/issues", "--method", "POST"): [
                create_response(102, 9102, "u102"),
            ],
        }
        rc, out, err, calls = self._run(path, ["--json"], responses)
        self.assertEqual(rc, 0, err)
        payload = json.loads(out)
        self.assertEqual(payload["counts"], {"created": 1, "reused": 2, "link_warnings": 0})
        self.assertEqual(payload["tracking"]["number"], 55)
        create_calls = [c for c in calls
                        if c[:4] == ["api", "repos/acme/widgets/issues", "--method", "POST"]]
        self.assertEqual(len(create_calls), 1)

    def test_resumes_from_created_json(self):
        path = self._write()
        (self.tmpdir / "created.json").write_text(json.dumps({
            "tracking": {"number": 55, "id": 8055, "url": "u55"},
            "agents-md": {"number": 56, "id": 8056, "url": "u56"},
        }), encoding="utf-8")
        responses = {
            ("api", "repos/acme/widgets/issues", "--method", "GET"): "[]",
            ("api", "repos/acme/widgets/issues", "--method", "POST"): [
                create_response(102, 9102, "u102"),
            ],
        }
        rc, out, err, calls = self._run(path, ["--json"], responses)
        self.assertEqual(rc, 0, err)
        payload = json.loads(out)
        self.assertEqual(payload["counts"], {"created": 1, "reused": 2, "link_warnings": 0})
        create_calls = [c for c in calls
                        if c[:4] == ["api", "repos/acme/widgets/issues", "--method", "POST"]]
        self.assertEqual(len(create_calls), 1)

    def test_link_failure_is_a_warning_not_fatal(self):
        path = self._write()
        responses = {
            ("api", "repos/acme/widgets/issues", "--method", "GET"): "[]",
            ("api", "repos/acme/widgets/issues", "--method", "POST"): [
                create_response(100, 9100, "u100"),
                create_response(101, 9101, "u101"),
                create_response(102, 9102, "u102"),
            ],
        }
        prefix = ("api", "repos/acme/widgets/issues/100/sub_issues", "--method", "POST")
        responses[prefix] = ""
        exits = {prefix: 1}
        stderrs = {prefix: "HTTP 500: boom"}
        rc, out, err, _ = self._run(path, ["--json"], responses, exits=exits, stderrs=stderrs)
        self.assertEqual(rc, 0, err)
        payload = json.loads(out)
        self.assertEqual(payload["counts"]["link_warnings"], 2)
        self.assertEqual(len(payload["link_warnings"]), 2)
        self.assertIn("warning:", err)

    def test_link_422_counts_as_success(self):
        path = self._write()
        responses = {
            ("api", "repos/acme/widgets/issues", "--method", "GET"): "[]",
            ("api", "repos/acme/widgets/issues", "--method", "POST"): [
                create_response(100, 9100, "u100"),
                create_response(101, 9101, "u101"),
                create_response(102, 9102, "u102"),
            ],
        }
        prefix = ("api", "repos/acme/widgets/issues/100/sub_issues", "--method", "POST")
        responses[prefix] = ""
        exits = {prefix: 1}
        stderrs = {prefix: "HTTP 422: already a sub-issue"}
        rc, out, err, _ = self._run(path, ["--json"], responses, exits=exits, stderrs=stderrs)
        self.assertEqual(rc, 0, err)
        payload = json.loads(out)
        self.assertEqual(payload["counts"]["link_warnings"], 0)
        self.assertEqual(payload["counts"]["created"], 3)

    def test_blocked_by_link_failure_is_a_warning_too(self):
        path = self._write()
        responses = {
            ("api", "repos/acme/widgets/issues", "--method", "GET"): "[]",
            ("api", "repos/acme/widgets/issues", "--method", "POST"): [
                create_response(100, 9100, "u100"),
                create_response(101, 9101, "u101"),
                create_response(102, 9102, "u102"),
            ],
        }
        prefix = ("api", "repos/acme/widgets/issues/102/dependencies/blocked_by", "--method", "POST")
        rc, out, err, _ = self._run(path, ["--json"], responses,
                                    exits={prefix: 1}, stderrs={prefix: "HTTP 500: boom"})
        self.assertEqual(rc, 0, err)
        payload = json.loads(out)
        self.assertEqual(payload["counts"]["link_warnings"], 1)
        self.assertIn("blocked-by link", payload["link_warnings"][0])

    def test_human_readable_summary_prints_link_warnings(self):
        path = self._write()
        responses = {
            ("api", "repos/acme/widgets/issues", "--method", "GET"): "[]",
            ("api", "repos/acme/widgets/issues", "--method", "POST"): [
                create_response(100, 9100, "u100"),
                create_response(101, 9101, "u101"),
                create_response(102, 9102, "u102"),
            ],
        }
        prefix = ("api", "repos/acme/widgets/issues/100/sub_issues", "--method", "POST")
        rc, out, err, _ = self._run(path, [], responses,
                                    exits={prefix: 1}, stderrs={prefix: "HTTP 500: boom"})
        self.assertEqual(rc, 0, err)
        self.assertIn("Link warnings:", out)
        self.assertIn("sub-issue link", out)

    def test_design_open_issue_gets_blocked_design_label(self):
        plan = base_plan()
        plan["issues"][1]["design"] = "open"
        path = self._write(plan)
        responses = {
            ("api", "repos/acme/widgets/issues", "--method", "GET"): "[]",
            ("api", "repos/acme/widgets/issues", "--method", "POST"): [
                create_response(100, 9100, "u100"),
                create_response(101, 9101, "u101"),
                create_response(102, 9102, "u102"),
            ],
        }
        rc, out, err, calls = self._run(path, [], responses)
        self.assertEqual(rc, 0, err)
        label_calls = [c for c in calls if c[:2] == ["label", "create"]]
        self.assertEqual({c[2] for c in label_calls}, {"chore", "priority: P0", "priority: P1",
                                                        "blocked: design"})

    def test_gh_missing_exits_1(self):
        path = self._write()
        out, err = io.StringIO(), io.StringIO()
        with patch.object(ci, "resolve_local_repo", return_value="acme/widgets"), \
                patch.object(ci.shutil, "which", return_value=None), \
                redirect_stdout(out), redirect_stderr(err):
            rc = ci.main([str(path), "--apply"])
        self.assertEqual(rc, 1)
        self.assertIn("ERR_GH_NOT_FOUND", err.getvalue())

    def test_label_failure_exits_1(self):
        path = self._write()
        prefix = ("label", "create")
        rc, out, err, _ = self._run(path, [], {}, exits={prefix: 1}, stderrs={prefix: "HTTP 403"})
        self.assertEqual(rc, 1)
        self.assertIn("ERR_GH_LABEL_FAILED", err)

    def test_list_issues_failure_exits_1(self):
        path = self._write()
        prefix = ("api", "repos/acme/widgets/issues", "--method", "GET")
        rc, out, err, _ = self._run(path, [], {}, exits={prefix: 1}, stderrs={prefix: "HTTP 500"})
        self.assertEqual(rc, 1)
        self.assertIn("ERR_GH_LIST_FAILED", err)

    def test_create_failure_exits_1_and_preserves_partial_created_json(self):
        path = self._write()
        responses = {
            ("api", "repos/acme/widgets/issues", "--method", "GET"): "[]",
            ("api", "repos/acme/widgets/issues", "--method", "POST"): [
                create_response(100, 9100, "u100"), "",
            ],
        }
        prefix = ("api", "repos/acme/widgets/issues", "--method", "POST")
        exits = {prefix: [0, 1]}
        stderrs = {prefix: ["", "HTTP 500: boom"]}
        rc, out, err, _ = self._run(path, [], responses, exits=exits, stderrs=stderrs)
        self.assertEqual(rc, 1)
        self.assertIn("ERR_GH_CREATE_FAILED", err)
        created = json.loads((self.tmpdir / "created.json").read_text(encoding="utf-8"))
        self.assertEqual(set(created), {"tracking"})

    def test_patch_failure_exits_1(self):
        path = self._write()
        responses = {
            ("api", "repos/acme/widgets/issues", "--method", "GET"): "[]",
            ("api", "repos/acme/widgets/issues", "--method", "POST"): [
                create_response(100, 9100, "u100"),
                create_response(101, 9101, "u101"),
                create_response(102, 9102, "u102"),
            ],
        }
        prefix = ("api", "repos/acme/widgets/issues/101", "--method", "PATCH")
        responses[prefix] = ""
        rc, out, err, _ = self._run(path, [], responses, exits={prefix: 1},
                                    stderrs={prefix: "HTTP 500"})
        self.assertEqual(rc, 1)
        self.assertIn("ERR_GH_PATCH_FAILED", err)


if __name__ == "__main__":
    unittest.main()
