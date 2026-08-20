<!-- platform-annex -->
# Scripts in Skills

## Table of Contents

- [Script or prose?](#script-or-prose)
- [Conventions](#conventions)
- [Invoking a bundled script](#invoking-a-bundled-script)
- [Shell vs Python](#shell-vs-python)
- [Writing scripts an agent can rely on](#writing-scripts-an-agent-can-rely-on)
- [Patterns](#patterns)
- [Review checklist](#review-checklist)

---

## Script or prose?

The dividing line: a step whose result is identical on every run — enumerating, counting, validating structure, converting formats, applying a rule table or dictionary, running tests, collecting a diff — is a script. Prose keeps the judgment: what the numbers mean, what to do on failure, which route to take.

**Use scripts for:**
- Validation and checking (file structure, JSON/YAML syntax, dependencies)
- Setup and initialization (directory structure, git init, install deps)
- Data transformation (format conversion, aggregation, reporting)
- Integration with external tools (API calls, CI/CD, cloud services)
- Operations that are repeatedly rewritten by the model

**Do not use scripts for:**
- User-specific logic that varies by project
- File content modifications (use the editing tool)
- Analysis and decision-making (use the model's reasoning)
- Simple one-liners the model can generate easily

If a procedure in SKILL.md would be followed identically by the model every time, it is a script that hasn't been written yet.

---

## Conventions

The authoritative list. Deviating from any of these is what the *scripts* review lens checks for.

### Placement and naming

Scripts live at `scripts/<verb>_<object>.py` or `.sh`, snake_case, named for what they do (`validate_skill.py`, not `script.py`). Tests live at `scripts/tests/test_<name>.py`, sharing the script's basename.

In a project (repo-local) skill collection, put shared logic that two or more sibling skills would otherwise duplicate (frontmatter parsing, JSONL I/O, a time helper) at `.claude/skills/_shared/` — not itself a skill (no `SKILL.md`), just library code plus its own tests (`_shared/tests/`). Consumers reach it with a `sys.path` bootstrap resolved from the consuming script's own location, never a hardcoded absolute path:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared"))
from medialib import mdtext
```

Two rules keep this from rotting: changing `_shared/` means running every consumer's tests, not just the one you were editing; and a new or changed script needs a new or updated `test_*.py` actually wired into the project's test discovery — confirm a typo'd filename didn't silently drop out.

### CLI contract

- `argparse`-based, with working `--help`.
- `--json` on anything an agent parses: stable keys, `ensure_ascii=False`. Human-readable text is the default output; `--json` is opt-in.
- Exit codes: `0` = OK, `1` = findings/errors, `2` = bad invocation.
- Errors go to stderr and name the fix — `Field 'signature_date' not found. Available fields: customer_name, order_total, signature_date_signed` costs one turn to fix; `KeyError: signature_date` costs three.
- Input and output paths are **arguments**, never assumed. A script invoked through `${CLAUDE_SKILL_DIR}` (or a full absolute path when called from outside a skill) takes the workspace path as an argument — the parent skill already knows where the workspace lives; the script should accept that path, not invent its own.
- `--dry-run` on anything that mutates: perform the analysis, make no changes, let the agent preview before re-running for real.

### Shape

- One script, one responsibility — a check script does not also fix; a fixer takes a plan file.
- Logic in pure functions that take data and return data; a thin `main(argv) -> int` that only parses args, calls the functions, and prints.
- A dataclass for findings/results, so `--json` output is `asdict()`.
- Reuse a sibling script's types by importing it from the same directory rather than duplicating them.

### Dependencies

- Standard library first.
- Anything else declared in SKILL.md.
- When a dependency is optional, degrade with an info-level message naming the install command rather than crashing.

### Tests and coverage

- stdlib `unittest`, discovered with `python3 -m unittest discover -s scripts/tests -p 'test_*.py'` run from the skill directory — the suite runs identically on both hosts without pytest.
- Fixtures built in `tempfile.TemporaryDirectory()`.
- Coverage **≥ 90%**, measured with:
  ```bash
  python3 -m coverage run --source=scripts --omit='scripts/tests/*' -m unittest discover -s scripts/tests -p 'test_*.py'
  python3 -m coverage report -m
  ```
  `coverage` is the one permitted non-stdlib dependency, and only for tests.
- `check_scripts.py` in the creating-agent-skills skill runs both and reports `S001`–`S007`; every new or changed script ships with its test in the same change.
- Shell scripts: a subprocess smoke test from Python is enough — coverage is not measured for them.

### Generated files

`__pycache__/`, `.pytest_cache/`, `.coverage`, `.coverage.*`, `htmlcov/` must be ignored by the enclosing repository's `.gitignore`; `check_scripts.py`'s `S007` verifies it.

---

## Invoking a bundled script

Reference bundled scripts through `${CLAUDE_SKILL_DIR}`, never a hardcoded `~/.claude/skills/<name>/…` path:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/validate.py <target> --json
bash ${CLAUDE_SKILL_DIR}/scripts/setup.sh 4 ~/work/run-2026-04-07
```

`${CLAUDE_SKILL_DIR}` resolves to the directory holding this `SKILL.md` — the skill's own subdirectory even when installed as a plugin. A hardcoded personal path breaks on plugin install and project checkout, and silently runs the *wrong copy* when both exist.

The same variable expands inside `allowed-tools`, so pre-approving the skill's own scripts costs one line and removes the permission prompt. This is one of the two reasons `allowed-tools` is worth writing at all (see `yaml-spec.md`'s `allowed-tools` section, load via SKILL.md); otherwise the field defaults to omitted:

```yaml
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/validate.py:*)
```

**Say whether Claude should run the script or read it.** Both are legitimate, and the wrong guess wastes a turn or a context window:

- "Run `scripts/analyze_form.py` to extract the fields" — execution, the common case. Source never enters context.
- "See `scripts/analyze_form.py` for the extraction algorithm" — reading, for logic the model must extend or mirror.

---

## Shell vs Python

| Criteria | Shell (.sh) | Python (.py) |
|----------|-------------|--------------|
| Complexity | < 50 lines | > 50 lines |
| Use case | File ops, git, npm, quick setup | Data processing, validation, API calls |
| Error handling | Basic | Comprehensive |
| Cross-platform | Unix-only | Cross-platform |
| Data structures | Limited | Rich |

**Rule of thumb:** If you need JSON parsing, complex error handling, or cross-platform support, use Python.

---

## Writing scripts an agent can rely on

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

---

## Patterns

### Pattern: deterministic phase, then judgment

When a script has both a deterministic component and a judgment component, split them.

- **Phase 1: deterministic.** Apply a dictionary, regex, or rule table. Fast, free, repeatable — handles the bulk of cases.
- **Phase 2: judgment.** Hand the remaining ambiguous cases to the model, either as `--json` output for the parent to interpret or via a direct call.

Example: a de-ai-article skill splits this across a script and the model. `scan_artifacts.py` does the deterministic Phase 1 (symbol artifacts via `--mode scan`; vocabulary density, structure and rhythm metrics via `--mode density`); the skill then hands the judgment calls — which findings to apply, how to reflow — to detection lenses in Phase 2. Categorizing the rule table lets it grow without any single section becoming unwieldy, and per-category stats in the report make it easy to see where the table is paying off.

### Pattern: snapshot-and-restore wrappers

For scripts that mutate user state (settings, configs, branches), wrap the destructive part in snapshot and restore steps. See `workspace-conventions.md` (load via SKILL.md) for the workspace structure. The script should:

1. Take a `--snapshot-dir` argument (default: `<workspace>/.snapshot/`).
2. Copy each file it's about to mutate into the snapshot dir.
3. Perform the mutation.
4. On either success or failure (use `trap` in bash, `try/finally` in Python), restore from the snapshot.
5. Verify the restore succeeded before reporting the final status.

### Pattern: categorized diff collection

For analysis scripts that summarize a git diff, categorize by directory or file type rather than dumping a flat list — the model consumes categorized output far more efficiently, and the same idea carries to any per-area breakdown (frontend pages/hooks/api/components, backend controllers/use-cases/models).

See `../examples/project-validator/scripts/validate.py` for a complete worked example.

---

## Review checklist

Used by the Improving playbook's *scripts* lens. `check_scripts.py` (`S001–S007`) and `W050` cover the mechanical part.

### SC1: Deterministic work is not written as prose
Any numbered procedure the model would execute identically every run (enumeration, counting, validation, conversion, rule tables) is a FAIL until it is a script.

### SC2: Placement and naming follow Conventions
`scripts/`, `scripts/tests/test_<name>.py`, snake_case verb_object filenames.

### SC3: CLI contract is followed
`--help`, `--json` where an agent parses the output, exit codes 0/1/2, stderr errors that name the fix, paths as arguments, `--dry-run` on mutators.

### SC4: One responsibility per script
Pure functions plus a thin `main`; results returned as dataclasses.

### SC5: Dependencies are declared
Standard library first, others declared in SKILL.md, optional ones degrade with an install hint rather than crashing.

### SC6: Tests present and passing, coverage ≥ 90%
Read `check_scripts.py`'s output and say what the uncovered lines are (error paths? CLI glue?) rather than repeating the number.

### SC7: Generated files are ignored
`.gitignore` covers `__pycache__/`, `.pytest_cache/`, `.coverage`, `.coverage.*`, `htmlcov/`.

### SC8: Invocation is explicit
Scripts are invoked through `${CLAUDE_SKILL_DIR}`; SKILL.md says whether to run or read each one.

### SC9: Workspace-aware, not self-locating
Scripts that participate in a phase take the workspace path as an argument and write nothing to a location of their own choosing.
