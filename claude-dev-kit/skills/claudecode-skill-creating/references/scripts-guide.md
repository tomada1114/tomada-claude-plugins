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
