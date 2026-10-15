import contextlib
import io
import json
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_allowlist as ca  # noqa: E402

DOCS = """\
# Configure cloud environments

## Network access

* not-a-default.example.com

## Default allowed domains

With **Trusted** network access, sessions can reach the following domains.

<AccordionGroup>
  <Accordion title="Version control">
    * github.com
    * [www.github.com](http://www.github.com)
    * raw\\.githubusercontent.com
  </Accordion>
  <Accordion title="Container registries">
    * \\*.gcr.io
    * Registry-1.Docker.io
  </Accordion>
  <Accordion title="Development tools">
    * nodejs.org (Node.js)
    * github.com
  </Accordion>
</AccordionGroup>

## Security proxy

* after-the-section.example.com
"""


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = ca.main(argv)
    return code, out.getvalue(), err.getvalue()


class ParseAllowlistTest(unittest.TestCase):
    def test_parse_allowlist_docs_formats_returns_bare_rules_in_section_only(self):
        self.assertEqual(
            ca.parse_allowlist(DOCS),
            [
                "github.com",
                "www.github.com",
                "raw.githubusercontent.com",
                "*.gcr.io",
                "registry-1.docker.io",
                "nodejs.org",
            ],
        )

    def test_parse_allowlist_missing_heading_raises(self):
        with self.assertRaisesRegex(ValueError, "not found"):
            ca.parse_allowlist("# Nothing here\n* github.com\n")

    def test_parse_allowlist_empty_section_raises(self):
        with self.assertRaisesRegex(ValueError, "no domain entries"):
            ca.parse_allowlist("## Default allowed domains\n\nprose only\n## Next\n")


class NormalizeTest(unittest.TestCase):
    def test_normalize_host_url_returns_hostname(self):
        self.assertEqual(ca.normalize_host("https://CDN.Example.com:443/path?q=1"), "cdn.example.com")

    def test_normalize_host_bare_host_with_port_and_path(self):
        self.assertEqual(ca.normalize_host("example.com:8080/x"), "example.com")

    def test_normalize_rule_blank_returns_empty(self):
        self.assertEqual(ca.normalize_rule("   "), "")


class RuleMatchesTest(unittest.TestCase):
    def test_wildcard_matches_subdomain(self):
        self.assertTrue(ca.rule_matches("eu.gcr.io", "*.gcr.io"))

    def test_wildcard_does_not_match_apex(self):
        self.assertFalse(ca.rule_matches("gcr.io", "*.gcr.io"))

    def test_exact_rule_does_not_match_subdomain(self):
        self.assertFalse(ca.rule_matches("download.microsoft.com", "microsoft.com"))


class CheckTest(unittest.TestCase):
    def test_check_prefers_extra_over_default_and_reports_missing(self):
        results = ca.check(
            ["nodejs.org", "cdn.playwright.dev", "eu.gcr.io", "nope.example"],
            ["nodejs.org", "*.gcr.io"],
            ["cdn.playwright.dev", "nodejs.org"],
        )
        self.assertEqual(
            [(r.host, r.covered, r.matched_by, r.source) for r in results],
            [
                ("nodejs.org", True, "nodejs.org", "extra"),
                ("cdn.playwright.dev", True, "cdn.playwright.dev", "extra"),
                ("eu.gcr.io", True, "*.gcr.io", "default"),
                ("nope.example", False, None, None),
            ],
        )


class MainTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.docs = Path(self.tmp.name) / "docs.md"
        self.docs.write_text(DOCS, encoding="utf-8")

    def test_main_all_covered_exits_zero_with_text(self):
        code, out, _ = run(["github.com", "https://eu.gcr.io/v2", "--docs-file", str(self.docs)])
        self.assertEqual(code, 0)
        self.assertIn("OK       eu.gcr.io  (by *.gcr.io, default)", out)
        self.assertIn("2/2 covered", out)
        self.assertIn("subdomains only", out)

    def test_main_missing_host_exits_one(self):
        code, out, _ = run(["cdn.playwright.dev", "--docs-file", str(self.docs)])
        self.assertEqual(code, 1)
        self.assertIn("MISSING  cdn.playwright.dev", out)

    def test_main_exact_match_only_omits_wildcard_note(self):
        code, out, _ = run(["github.com", "--docs-file", str(self.docs)])
        self.assertEqual(code, 0)
        self.assertNotIn("note:", out)

    def test_main_json_with_extra_and_hosts_file(self):
        hosts = Path(self.tmp.name) / "hosts.txt"
        hosts.write_text("# comment\n\ncdn.playwright.dev\nnodejs.org\n", encoding="utf-8")
        code, out, _ = run(
            [
                "--hosts-file",
                str(hosts),
                "--extra",
                "cdn.playwright.dev",
                "--docs-file",
                str(self.docs),
                "--json",
            ]
        )
        payload = json.loads(out)
        self.assertEqual(code, 0)
        self.assertTrue(payload["defaults_included"])
        self.assertEqual(payload["default_entries"], 6)
        self.assertEqual(
            [(r["host"], r["source"]) for r in payload["results"]],
            [("cdn.playwright.dev", "extra"), ("nodejs.org", "default")],
        )

    def test_main_no_defaults_skips_docs(self):
        code, out, _ = run(["nodejs.org", "--no-defaults", "--extra", "cdn.playwright.dev"])
        self.assertEqual(code, 1)
        self.assertIn("MISSING  nodejs.org", out)

    def test_main_no_hosts_exits_two(self):
        code, _, err = run(["--docs-file", str(self.docs)])
        self.assertEqual(code, 2)
        self.assertIn("ERR_NO_HOSTS", err)

    def test_main_unreadable_hosts_file_exits_two(self):
        code, _, err = run(["--hosts-file", str(Path(self.tmp.name) / "missing.txt")])
        self.assertEqual(code, 2)
        self.assertIn("ERR_HOSTS_FILE", err)

    def test_main_docs_without_section_exits_two_naming_retry(self):
        bad = Path(self.tmp.name) / "bad.md"
        bad.write_text("# nothing\n", encoding="utf-8")
        code, _, err = run(["github.com", "--docs-file", str(bad)])
        self.assertEqual(code, 2)
        self.assertIn("ERR_ALLOWLIST", err)
        self.assertIn("--docs-file", err)

    def test_main_fetches_live_docs_when_no_docs_file(self):
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = DOCS.encode("utf-8")
        with mock.patch.object(ca.urllib.request, "urlopen", return_value=response) as urlopen:
            code, _, _ = run(["github.com"])
        self.assertEqual(code, 0)
        self.assertEqual(urlopen.call_args.args[0].full_url, ca.DOCS_URL)

    def test_main_fetch_failure_exits_two(self):
        with mock.patch.object(
            ca.urllib.request, "urlopen", side_effect=urllib.error.URLError("offline")
        ):
            code, _, err = run(["github.com"])
        self.assertEqual(code, 2)
        self.assertIn("offline", err)


if __name__ == "__main__":
    unittest.main()
