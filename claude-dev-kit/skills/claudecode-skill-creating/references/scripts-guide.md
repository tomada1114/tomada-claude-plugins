# Scripts in Skills

## Table of Contents

- [When to Use Scripts](#when-to-use-scripts)
- [Shell vs Python](#shell-vs-python)
- [Script Templates](#script-templates)
- [Examples](#examples)
- [Best Practices](#best-practices)

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

See [examples/3-skill-with-scripts/scripts/validate.py](../examples/3-skill-with-scripts/scripts/validate.py) for a complete implementation.

Features: file existence checks, JSON syntax validation, git repo verification, dependency checking, colored output with exit codes.

### Project Setup (Shell)

See [examples/3-skill-with-scripts/scripts/setup.sh](../examples/3-skill-with-scripts/scripts/setup.sh) for a complete implementation.

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

## Real-World Patterns

These patterns are extracted from production skills (`~/draever/.claude/skills/*`, `~/.claude/skills/*`) and are worth copying when you build new scripts.

### Pattern 1: Absolute-path invocation, no fixed output dir

Production scripts are invoked with their **full absolute path** and take input/output paths as **arguments**, never assuming a fixed location.

```bash
# Good — explicit, portable, parent skill chooses the workspace
bash ~/.claude/skills/tmux-orchestrating/scripts/setup.sh 4 ~/work/run-2026-04-07
python3 ~/.claude/skills/fixing-transcriptions/scripts/fix_transcription.py \
    ~/notes/voice-memo.md --json
bash ~/draever/.claude/skills/e2e-testing/scripts/collect-changes.sh main

# Bad — script writes to a hardcoded path inside its own dir
python3 ~/.claude/skills/foo/scripts/run.py    # writes to ./output.json (where?)
```

Why this matters: when SKILL.md invokes a script as part of a phase, the parent skill already knows where the workspace lives. The script should accept that path, not invent its own.

### Pattern 2: Mode flags for LLM coordination (`--dry-run`, `--json`)

Scripts that participate in a workflow with the main LLM agent benefit from two flags:

- `--dry-run` — perform all the analysis but make no changes. The LLM uses this to preview what the script *would* do, decide whether to proceed, and only then re-run without `--dry-run`.
- `--json` — emit machine-parseable output instead of human-friendly text. The LLM uses this to ingest results into its own reasoning.

Example: `~/.claude/skills/fixing-transcriptions/scripts/fix_transcription.py` exposes both. The skill's SKILL.md has the LLM run `--dry-run --json` first, present the proposed changes to the user, and only then execute the destructive run.

### Pattern 3: Two-phase scripts (Dictionary → LLM)

When a script has both a deterministic component and a judgment component, split them.

- **Phase 1: Deterministic.** Apply a dictionary, regex, or rule table. Fast, free, repeatable. Handles 80% of cases.
- **Phase 2: LLM judgment.** Hand the remaining ambiguous cases off to the LLM (either by emitting them as `--json` for the parent to interpret, or by calling Claude directly via headless mode).

Example: `~/.claude/skills/fixing-transcriptions/scripts/fix_transcription.py` reads `~/.claude/skills/fixing-transcriptions/dictionaries/misconversion-dict.json` for Phase 1 (exact-match and regex categories), then surfaces the `context_dependent` candidates to the LLM in Phase 2.

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

For scripts that mutate user state (settings, configs, branches), wrap the destructive part in snapshot and restore steps. See `workspace-conventions.md` for the workspace structure. The script should:

1. Take a `--snapshot-dir` argument (default: `<workspace>/.snapshot/`).
2. Copy each file it's about to mutate into the snapshot dir.
3. Perform the mutation.
4. On either success or failure (use `trap` in bash, `try/finally` in Python), restore from the snapshot.
5. Verify the restore succeeded before reporting the final status.

Example to study: `~/.claude/skills/cc-cli-verify/scripts/`.

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

Source: `~/draever/.claude/skills/e2e-testing/scripts/collect-changes.sh`. The same idea works for FE: pages / hooks / api / components.
