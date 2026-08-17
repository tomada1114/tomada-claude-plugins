# Scripts in Skills

## Table of Contents

- [When to Use Scripts](#when-to-use-scripts)
- [Invoking a Bundled Script](#invoking-a-bundled-script)
- [Shell vs Python](#shell-vs-python)
- [Script Templates](#script-templates)
- [Examples](#examples)
- [Best Practices](#best-practices)
- [Writing Scripts an Agent Can Rely On](#writing-scripts-an-agent-can-rely-on)
- [Real-World Patterns](#real-world-patterns)

## When to Use Scripts

Scripts provide deterministic, token-efficient execution. Script code is NOT loaded into the context window — only execution output consumes tokens.

**Use scripts for:**
- Validation and checking (file structure, JSON/YAML syntax, dependencies)
- Setup and initialization (directory structure, git init, install deps)
- Data transformation (format conversion, aggregation, reporting)
- Integration with external tools (API calls, CI/CD, cloud services)
- Operations that are repeatedly rewritten by Claude

**Do not use scripts for:**
- User-specific logic that varies by project
- File content modifications (use Claude's Edit tool)
- Analysis and decision-making (use Claude's reasoning)
- Simple one-liners that Claude can generate easily

## Invoking a Bundled Script

Reference bundled scripts through `${CLAUDE_SKILL_DIR}`, never a hardcoded `~/.claude/skills/<name>/…` path:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/validate.py <target> --json
bash ${CLAUDE_SKILL_DIR}/scripts/setup.sh 4 ~/work/run-2026-04-07
```

`${CLAUDE_SKILL_DIR}` resolves to the directory holding this `SKILL.md` — the skill's own subdirectory even when installed as a plugin. A hardcoded personal path breaks on plugin install and project checkout, and silently runs the *wrong copy* when both exist.

The same variable expands inside `allowed-tools`, so pre-approving the skill's own scripts costs one line and removes the permission prompt:

```yaml
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/validate.py:*)
```

**Say whether Claude should run the script or read it.** Both are legitimate, and the wrong guess wastes a turn or a context window:

- "Run `scripts/analyze_form.py` to extract the fields" — execution, the common case. Source never enters context.
- "See `scripts/analyze_form.py` for the extraction algorithm" — reading, for logic the model must extend or mirror.

## Shell vs Python

| Criteria | Shell (.sh) | Python (.py) |
|----------|-------------|--------------|
| Complexity | < 50 lines | > 50 lines |
| Use case | File ops, git, npm, quick setup | Data processing, validation, API calls |
| Error handling | Basic | Comprehensive |
| Cross-platform | Unix-only | Cross-platform |
| Data structures | Limited | Rich |

**Rule of thumb:** If you need JSON parsing, complex error handling, or cross-platform support, use Python.

## Script Templates

### Shell Script

```bash
#!/usr/bin/env bash
set -euo pipefail

readonly GREEN='\033[0;32m'
readonly RED='\033[0;31m'
readonly NC='\033[0m'

log_info() { echo -e "${GREEN}[OK]${NC} $1"; }
log_error() { echo -e "${RED}[ERR]${NC} $1" >&2; }

main() {
    log_info "Starting..."
    # Your logic here
    log_info "Done."
}

main "$@"
```

### Python Script

```python
#!/usr/bin/env python3
"""Brief description. Usage: python script.py [args]"""

import sys
import argparse
from pathlib import Path


def log_info(msg: str) -> None:
    print(f"\033[92m[OK]\033[0m {msg}")

def log_error(msg: str) -> None:
    print(f"\033[91m[ERR]\033[0m {msg}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="Script description")
    parser.add_argument('--input', type=Path, help='Input file path')
    args = parser.parse_args()

    try:
        log_info("Starting...")
        # Your logic here
        log_info("Done.")
        return 0
    except Exception as e:
        log_error(f"Error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
```

## Examples

### Project Validator (Python)

See [examples/project-validator/scripts/validate.py](../examples/project-validator/scripts/validate.py) for a complete implementation.

Features: file existence checks, JSON syntax validation, git repo verification, dependency checking, colored output with exit codes.

### Project Setup (Shell)

See [examples/project-validator/scripts/setup.sh](../examples/project-validator/scripts/setup.sh) for a complete implementation.

Features: git initialization, .gitignore creation, README template, environment file setup, dependency installation.

## Best Practices

1. **Make executable**: `chmod +x scripts/*.py scripts/*.sh`
2. **Add shebang**: `#!/usr/bin/env bash` or `#!/usr/bin/env python3`
3. **Use descriptive names**: `validate-project.py` not `script.py`
4. **Handle errors**: Return non-zero exit codes on failure. Catch specific exceptions.
5. **Validate input**: Check file existence and argument validity before processing.
6. **Use exit codes**: 0 = success, 1 = general error, 2 = file not found, 3 = invalid input.
7. **Add progress output**: `echo "Step 1/3: Initializing..."` for multi-step operations.
8. **Use Path objects** in Python: `Path('scripts') / 'validate.py'` for cross-platform paths.
9. **Test scripts by running them**: Added scripts must be verified to work before packaging.
10. **Return structured data** when possible: JSON output is easier for Claude to parse.
11. **Don't write logic directly in SKILL.md**: if a code block in SKILL.md exceeds ~10 lines of
    actual logic (aggregation, parsing, state updates — not a one-line CLI invocation), move it to
    `scripts/` and call it from a single line instead. SKILL.md prose should describe *when* and
    *why*, not *how* in Python/bash. `validate_skill.py` warns (W050) when a single SKILL.md code
    block exceeds 25 lines.

```python
# Structured JSON output pattern (from Anthropic's xlsx recalc.py)
import json

result = {
    "status": "errors_found",
    "total_errors": 2,
    "error_summary": {
        "#REF!": {"count": 2, "locations": ["Sheet1!B5", "Sheet1!C10"]}
    }
}
print(json.dumps(result, indent=2))
```

## Writing Scripts an Agent Can Rely On

A skill script has one consumer: an agent that cannot see its source. That changes what "good error handling" means.

### Solve, don't defer

Handle the recoverable condition in the script. Raising it to the agent turns a deterministic step into an improvisation.

```python
# Good — the script decides
def load_config(path):
    try:
        return json.loads(Path(path).read_text())
    except FileNotFoundError:
        print(f"{path} not found, using defaults", file=sys.stderr)
        return DEFAULT_CONFIG

# Bad — the agent now has to invent a recovery
def load_config(path):
    return json.loads(Path(path).read_text())
```

Unrecoverable conditions are the opposite: fail loudly with a message that names the fix. `Field 'signature_date' not found. Available fields: customer_name, order_total, signature_date_signed` lets the agent correct itself in one step; `KeyError: signature_date` costs it three.

### No voodoo constants

Every tuned number needs a reason next to it, or the agent has no basis to adjust it.

```python
# HTTP requests here complete well under 30s; the margin covers slow CI runners.
REQUEST_TIMEOUT = 30
# Most intermittent failures clear on the second attempt.
MAX_RETRIES = 3
```

If you don't know why the value is what it is, the agent reading it certainly won't.

### Plan, validate, execute

For batch or destructive operations, have the agent write a plan file, validate it with a script, and only then apply it:

```
analyze → write changes.json → validate changes.json → apply → verify
```

The plan is cheap to iterate on and machine-checkable, so mistakes surface before anything is written. Worth the extra step for bulk edits, migrations, and anything hard to reverse; overkill for single-file changes.

### Declare dependencies

State required packages in SKILL.md, and prefer the standard library where the choice is close. A script that imports `yaml` in an environment without PyYAML fails in a way the agent will try to fix by installing things.

## Real-World Patterns

Patterns from production skills, worth copying when you build new scripts.

### Pattern 1: Resolved-path invocation, no fixed output dir

Production scripts are invoked through `${CLAUDE_SKILL_DIR}` (or a full absolute path when called from outside a skill) and take input/output paths as **arguments**, never assuming a fixed location.

```bash
# Good — explicit, portable, parent skill chooses the workspace
bash ${CLAUDE_SKILL_DIR}/scripts/setup.sh 4 ~/work/run-2026-04-07
python3 ${CLAUDE_SKILL_DIR}/scripts/scan_artifacts.py \
    ~/notes/article.md --mode scan --json

# Cross-skill call to a GLOBAL skill: use the plugin-root fallback form —
# it resolves to ~/.claude locally and to the plugin dir when installed as a plugin
bash "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}"/skills/<other-skill>/scripts/collect-changes.sh main

# Cross-skill call to a PROJECT-LOCAL skill in the same repo: use a repo-root-relative
# path instead, so the call survives a checkout anywhere.
python3 .claude/skills/asking-grok/scripts/grok_search.py --help

# Bad — script writes to a hardcoded path inside its own dir
python3 ${CLAUDE_SKILL_DIR}/scripts/run.py    # writes to ./output.json (where?)
```

Why this matters: when SKILL.md invokes a script as part of a phase, the parent skill already knows where the workspace lives. The script should accept that path, not invent its own.

### Pattern 2: Mode flags for LLM coordination (`--dry-run`, `--json`)

Scripts that participate in a workflow with the main LLM agent benefit from two flags:

- `--dry-run` — perform all the analysis but make no changes. The LLM uses this to preview what the script *would* do, decide whether to proceed, and only then re-run without `--dry-run`.
- `--json` — emit machine-parseable output instead of human-friendly text. The LLM uses this to ingest results into its own reasoning.

Example: a writing-score script is read-only by default and prints a JSON report to stdout; passing `--fix` opts into applying the mechanical autofix candidates. Its SKILL.md has the LLM read the default JSON first, and re-run with `--fix` only when it wants the changes written.

### Pattern 3: Two-phase scripts (Dictionary → LLM)

When a script has both a deterministic component and a judgment component, split them.

- **Phase 1: Deterministic.** Apply a dictionary, regex, or rule table. Fast, free, repeatable. Handles 80% of cases.
- **Phase 2: LLM judgment.** Hand the remaining ambiguous cases off to the LLM (either by emitting them as `--json` for the parent to interpret, or by calling Claude directly via headless mode).

Example: de-ai-article splits this across a script and the LLM. `scan_artifacts.py` does the deterministic Phase 1 (symbol artifacts via `--mode scan`; vocabulary density, structure and rhythm metrics via `--mode density`), then the skill hands the judgment calls (which findings to apply, how to reflow) to LLM detection lenses in Phase 2.

The dictionary structure that has worked in practice:

```json
{
  "exact_match": {
    "category_a": { "wrong": "right", ... },
    "category_b": { ... }
  },
  "regex_patterns": [
    { "pattern": "...", "replacement": "..." }
  ],
  "context_dependent": [
    { "pattern": "クラウド", "candidates": ["Claude", "クラウド"], "hint": "..." }
  ]
}
```

Categorizing the dictionary lets you grow it without making any single section unwieldy. The script reports per-category stats, which makes it easy to know where the dictionary is paying off.

### Pattern 4: Snapshot-and-restore wrappers

For scripts that mutate user state (settings, configs, branches), wrap the destructive part in snapshot and restore steps. See `workspace-conventions.md` (load via SKILL.md) for the workspace structure. The script should:

1. Take a `--snapshot-dir` argument (default: `<workspace>/.snapshot/`).
2. Copy each file it's about to mutate into the snapshot dir.
3. Perform the mutation.
4. On either success or failure (use `trap` in bash, `try/finally` in Python), restore from the snapshot.
5. Verify the restore succeeded before reporting the final status.

### Pattern 5: Categorized diff collection

For analysis scripts that summarize a git diff, **categorize by directory or file type** rather than dumping a flat list. The LLM consumes the categorized output far more efficiently.

```
# from collect-changes.sh
Controllers: 3 changed
  app/Http/Controllers/Foo/BarController.php
  ...
UseCases:    2 changed
Models:      1 changed
Migrations:  1 added
```

The same idea works on the frontend side: pages / hooks / api / components.

## Shared Libraries Across Project-Local Skills

In a project (repo-local) skill collection, it's fine to put a shared Python library at
`.claude/skills/_shared/` when two or more sibling skills would otherwise duplicate the same
logic (e.g. Markdown frontmatter parsing, JSONL I/O, a JST time helper). `_shared/` is **not
itself a skill** — it holds no `SKILL.md`, only library code and its own tests
(`_shared/tests/`, or `_shared/<lib>/tests/`).

Consumers reach it with a `sys.path` bootstrap snippet resolved from the consuming script's own
location, not a hardcoded absolute path:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared"))
from medialib import mdtext
```

(`parents[2]` assumes the consumer lives at `<skill>/scripts/foo.py`, two levels under
`.claude/skills/`; adjust the index if a script lives somewhere else.)

Two rules keep this from rotting:

- **Change the shared library, run every consumer's tests.** A change to `_shared/` is a change
  to every skill that imports it. Run the project's full test target (e.g. `make test`) before
  committing a `_shared/` change, not just the tests for the skill you were editing.
- **New or changed script → new or updated `test_*.py`, wired into the test target.** If the
  project's test runner discovers tests by a glob (e.g. `find … -name 'test_*.py'`), confirm the
  new test file actually gets picked up — a typo'd filename silently drops out of the suite.
