# Scripts in Claude Code Skills - Complete Guide

This guide covers everything you need to know about using scripts in Claude Code skills, including when to use them, how to write them, and best practices.

## Table of Contents

- [Why Use Scripts in Skills](#why-use-scripts-in-skills)
- [When to Use Scripts](#when-to-use-scripts)
- [Shell Scripts vs Python Scripts](#shell-scripts-vs-python-scripts)
- [Creating Scripts](#creating-scripts)
- [Script Examples](#script-examples)
- [Best Practices](#best-practices)
- [Cross-Platform Considerations](#cross-platform-considerations)
- [Testing Scripts](#testing-scripts)
- [Troubleshooting](#troubleshooting)

## Why Use Scripts in Skills

Scripts provide several advantages in Claude Code skills:

### 1. Deterministic Execution
- Scripts run the same way every time
- No need for Claude to regenerate code
- Reliable, tested functionality

### 2. Token Efficiency
- Pre-written scripts save context tokens
- Claude doesn't need to generate code
- Faster skill activation and execution

### 3. Consistency
- Standardized operations across users
- No variation in generated code quality
- Team-wide consistency

### 4. Complexity Handling
- Handle complex logic that's hard for Claude to generate reliably
- Include error handling, edge cases, validation
- Use specialized libraries or APIs

### 5. Performance
- Optimized, tested code
- No generation overhead
- Direct execution

## When to Use Scripts

### ✅ Use Scripts For:

**1. Validation and Checking**
```python
# validate.py - Check project structure
- File existence checks
- JSON/YAML syntax validation
- Configuration verification
- Dependency validation
```

**2. Setup and Initialization**
```bash
# setup.sh - Initialize project
- Create directory structure
- Copy templates
- Initialize git
- Install dependencies
```

**3. Data Transformation**
```python
# transform.py - Process data
- Parse and transform files
- Generate reports
- Convert formats (CSV → JSON, etc.)
- Aggregate data
```

**4. File Operations**
```bash
# organize.sh - Organize files
- Move/copy files systematically
- Batch rename operations
- Archive/cleanup operations
```

**5. Integration with External Tools**
```python
# deploy.py - Deploy application
- API calls
- Cloud service interactions
- CI/CD operations
- Third-party integrations
```

### ❌ Don't Use Scripts For:

**1. User-Specific Logic**
- Code that needs to adapt to project structure
- Business logic that varies by user
- Customized implementations

**2. File Content Modifications**
- Editing source code files
- Refactoring code
- Adding features

**3. Analysis and Decision-Making**
- Code review
- Architecture decisions
- Pattern detection

**4. Simple One-Liners**
- Operations that don't benefit from scripting
- Commands Claude can easily generate
- One-off operations

## Shell Scripts vs Python Scripts

### Shell Scripts (.sh)

**Best For:**
- Simple command chaining
- File system operations
- Git operations
- Quick setup tasks
- < 50 lines of logic

**Pros:**
- Fast for simple tasks
- Native command integration
- Familiar to developers
- Good for CLI tool orchestration

**Cons:**
- Platform-dependent (harder on Windows)
- Limited data structures
- Harder to test
- Poor error handling for complex logic

**Example Use Cases:**
```bash
# Good uses for shell scripts:
- Initialize git repository
- Create directory structure
- Run npm/pip commands
- Simple file operations
- Environment setup
```

### Python Scripts (.py)

**Best For:**
- Complex logic
- Data processing
- Cross-platform compatibility
- JSON/YAML parsing
- Error handling
- > 50 lines of logic

**Pros:**
- Cross-platform (works everywhere)
- Rich standard library
- Great error handling
- Easy to test
- Complex data structures
- Readable and maintainable

**Cons:**
- Requires Python installation
- Slightly slower startup than shell
- More verbose for simple tasks

**Example Use Cases:**
```python
# Good uses for Python scripts:
- Validate complex configurations
- Parse and transform data
- API integrations
- File format conversions
- Project analysis
```

### Decision Matrix

| Task | Shell Script | Python Script |
|------|-------------|---------------|
| Simple file operations | ✅ | ❌ |
| Git commands | ✅ | ❌ |
| npm/yarn commands | ✅ | ❌ |
| JSON parsing | ❌ | ✅ |
| Complex validation | ❌ | ✅ |
| Data transformation | ❌ | ✅ |
| Cross-platform | ❌ | ✅ |
| API calls | ❌ | ✅ |
| Error handling | ❌ | ✅ |
| Quick setup | ✅ | ❌ |

## Creating Scripts

### Shell Script Template

```bash
#!/usr/bin/env bash

# Script Name - Brief description
# Usage: bash script-name.sh [args]

set -e  # Exit on error
set -u  # Exit on undefined variable
set -o pipefail  # Exit on pipe failure

# Colors for output
readonly GREEN='\033[0;32m'
readonly RED='\033[0;31m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m'  # No Color

# Helper functions
log_info() {
    echo -e "${GREEN}✓${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1" >&2
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Main function
main() {
    log_info "Starting process..."

    # Your logic here

    log_info "Process complete!"
}

# Run main function
main "$@"
```

### Python Script Template

```python
#!/usr/bin/env python3
"""
Script Name - Brief description

Usage:
    python script_name.py [args]

Example:
    python script_name.py --input file.json
"""

import sys
import argparse
from pathlib import Path


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'


def log_info(message: str) -> None:
    """Print info message with green checkmark"""
    print(f"{Colors.GREEN}✓{Colors.END} {message}")


def log_error(message: str) -> None:
    """Print error message with red X"""
    print(f"{Colors.RED}✗{Colors.END} {message}", file=sys.stderr)


def log_warning(message: str) -> None:
    """Print warning message with yellow triangle"""
    print(f"{Colors.YELLOW}⚠{Colors.END} {message}")


def main() -> int:
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Script description"
    )
    parser.add_argument(
        '--input',
        type=Path,
        help='Input file path'
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Output file path'
    )

    args = parser.parse_args()

    try:
        log_info("Starting process...")

        # Your logic here

        log_info("Process complete!")
        return 0

    except Exception as e:
        log_error(f"Error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
```

## Script Examples

### Example 1: Project Validator (Python)

See [examples/3-skill-with-scripts/scripts/validate.py](examples/3-skill-with-scripts/scripts/validate.py) for a complete example.

**Features:**
- Checks file existence
- Validates JSON syntax
- Verifies git repository
- Checks dependencies
- Colored output
- Exit codes for automation

### Example 2: Project Setup (Shell)

See [examples/3-skill-with-scripts/scripts/setup.sh](examples/3-skill-with-scripts/scripts/setup.sh) for a complete example.

**Features:**
- Initializes git
- Creates .gitignore
- Creates README template
- Sets up environment files
- Installs dependencies

### Example 3: Data Transformer (Python)

```python
#!/usr/bin/env python3
"""
Transform CSV data to JSON format
Usage: python transform.py input.csv output.json
"""

import csv
import json
import sys
from pathlib import Path


def csv_to_json(csv_path: Path, json_path: Path) -> None:
    """Convert CSV file to JSON"""
    data = []

    with open(csv_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            data.append(row)

    with open(json_path, 'w', encoding='utf-8') as jsonfile:
        json.dump(data, jsonfile, indent=2, ensure_ascii=False)

    print(f"✓ Converted {len(data)} rows from {csv_path} to {json_path}")


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python transform.py input.csv output.json")
        return 1

    csv_path = Path(sys.argv[1])
    json_path = Path(sys.argv[2])

    if not csv_path.exists():
        print(f"✗ Error: {csv_path} not found", file=sys.stderr)
        return 1

    try:
        csv_to_json(csv_path, json_path)
        return 0
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
```

### Example 4: File Organizer (Shell)

```bash
#!/usr/bin/env bash

# Organize files by extension
# Usage: bash organize.sh <directory>

set -e

readonly GREEN='\033[0;32m'
readonly NC='\033[0m'

if [ $# -eq 0 ]; then
    echo "Usage: bash organize.sh <directory>"
    exit 1
fi

TARGET_DIR="$1"

if [ ! -d "$TARGET_DIR" ]; then
    echo "Error: Directory $TARGET_DIR not found"
    exit 1
fi

cd "$TARGET_DIR"

# Create directories
mkdir -p images documents scripts

# Move files
mv *.jpg *.png *.gif images/ 2>/dev/null || true
mv *.pdf *.docx *.txt documents/ 2>/dev/null || true
mv *.sh *.py *.rb scripts/ 2>/dev/null || true

echo -e "${GREEN}✓${NC} Files organized successfully"
```

## Best Practices

### 1. Make Scripts Executable

```bash
# Make script executable
chmod +x scripts/setup.sh
chmod +x scripts/validate.py

# Verify
ls -l scripts/
```

### 2. Add Shebang Line

```bash
#!/usr/bin/env bash  # For shell scripts
```

```python
#!/usr/bin/env python3  # For Python scripts
```

**Why `#!/usr/bin/env`?**
- More portable across systems
- Finds python3/bash in user's PATH
- Works with virtual environments

### 3. Use Descriptive Names

✅ Good:
- `validate-project.py`
- `setup-environment.sh`
- `transform-data.py`

❌ Bad:
- `script.py`
- `util.sh`
- `test.py`

### 4. Include Usage Documentation

```python
"""
Script Name - One-line description

Detailed description of what the script does.

Usage:
    python script_name.py [options] <args>

Arguments:
    arg1    Description of arg1
    arg2    Description of arg2

Options:
    -h, --help     Show this help message
    -v, --verbose  Enable verbose output

Examples:
    python script_name.py input.txt
    python script_name.py --verbose data.json
"""
```

### 5. Handle Errors Gracefully

```python
try:
    result = risky_operation()
except FileNotFoundError as e:
    log_error(f"File not found: {e}")
    return 1
except ValueError as e:
    log_error(f"Invalid value: {e}")
    return 1
except Exception as e:
    log_error(f"Unexpected error: {e}")
    return 1
```

### 6. Use Exit Codes

```python
# Exit codes convention
SUCCESS = 0
ERROR_GENERAL = 1
ERROR_FILE_NOT_FOUND = 2
ERROR_INVALID_INPUT = 3
ERROR_PERMISSION_DENIED = 4

sys.exit(SUCCESS)  # Success
sys.exit(ERROR_FILE_NOT_FOUND)  # Specific error
```

```bash
# Shell scripts
exit 0  # Success
exit 1  # General error
exit 2  # Invalid usage
```

### 7. Add Progress Indicators

```python
# For long-running operations
from tqdm import tqdm  # If available

for item in tqdm(items, desc="Processing"):
    process(item)
```

```bash
# Simple shell progress
echo "Step 1/3: Initializing..."
initialize
echo "Step 2/3: Processing..."
process
echo "Step 3/3: Finalizing..."
finalize
```

### 8. Validate Input

```python
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('file', type=Path)
    args = parser.parse_args()

    # Validate input
    if not args.file.exists():
        log_error(f"File not found: {args.file}")
        return 1

    if not args.file.suffix == '.json':
        log_error("File must be JSON")
        return 1

    # Process...
```

### 9. Use Version Control

```python
# Include version number
__version__ = '1.0.0'

# Show in help
parser.add_argument(
    '--version',
    action='version',
    version=f'%(prog)s {__version__}'
)
```

### 10. Add Dry-Run Mode

```python
parser.add_argument(
    '--dry-run',
    action='store_true',
    help='Show what would be done without doing it'
)

if args.dry_run:
    print(f"Would process: {file}")
else:
    process(file)
```

## Cross-Platform Considerations

### Path Handling

```python
# ✅ Use Path objects (cross-platform)
from pathlib import Path

file_path = Path('scripts') / 'validate.py'
config_path = Path.home() / '.config' / 'app' / 'settings.json'

# ❌ Avoid hardcoded separators
file_path = 'scripts/validate.py'  # Unix only
file_path = 'scripts\\validate.py'  # Windows only
```

### Line Endings

```bash
# Configure git to handle line endings
# .gitattributes file:
*.sh text eol=lf
*.py text eol=lf
```

### Shell Script Compatibility

```bash
# Use POSIX-compliant commands
# ✅ Good (POSIX)
if [ -f "file.txt" ]; then
    echo "File exists"
fi

# ❌ Avoid bash-specific features if possible
if [[ -f "file.txt" ]]; then  # Bash-specific
    echo "File exists"
fi
```

### Testing on Multiple Platforms

```bash
# Test matrix
- Ubuntu/Linux
- macOS
- Windows (Git Bash / WSL)
```

## Testing Scripts

### Manual Testing

```bash
# Test happy path
bash setup.sh

# Test with invalid input
bash setup.sh /nonexistent/path

# Test error handling
python validate.py --input broken.json
```

### Automated Testing

```python
# test_script.py
import subprocess
import pytest

def test_validate_success():
    result = subprocess.run(
        ['python', 'validate.py'],
        capture_output=True
    )
    assert result.returncode == 0

def test_validate_missing_file():
    result = subprocess.run(
        ['python', 'validate.py', '--input', 'nonexistent.json'],
        capture_output=True
    )
    assert result.returncode == 2  # File not found
```

## Troubleshooting

### Issue: Script Not Executable

**Symptoms:**
```bash
$ ./setup.sh
bash: ./setup.sh: Permission denied
```

**Fix:**
```bash
chmod +x setup.sh
```

### Issue: Python Script Not Found

**Symptoms:**
```bash
$ python validate.py
python: command not found
```

**Fix:**
```bash
# Use python3 instead
python3 validate.py

# Or update shebang
#!/usr/bin/env python3
```

### Issue: Shell Script Fails on Windows

**Symptoms:**
- "command not found" errors
- Path issues

**Solutions:**
1. Use Git Bash or WSL
2. Convert to Python for cross-platform
3. Use POSIX-compliant commands only

### Issue: Import Errors in Python

**Symptoms:**
```python
ModuleNotFoundError: No module named 'requests'
```

**Fix:**
```bash
# Install dependencies
pip install requests

# Or use only standard library
import urllib.request  # Instead of requests
```

## Summary

### Quick Reference

**When to Use Scripts:**
- ✅ Deterministic operations
- ✅ Complex logic
- ✅ Performance-critical tasks
- ✅ Cross-platform compatibility needed (Python)
- ✅ Token efficiency important

**When NOT to Use Scripts:**
- ❌ User-specific customization
- ❌ Content-based file editing
- ❌ Analysis and decision-making
- ❌ Simple one-off operations

**Choose Shell When:**
- Simple file operations
- Git/npm commands
- Quick setup tasks
- < 50 lines

**Choose Python When:**
- Complex logic
- Data processing
- Cross-platform needed
- > 50 lines

### Next Steps

1. Review the [example skills with scripts](examples/3-skill-with-scripts/)
2. Use the [script templates](#creating-scripts) as starting points
3. Test scripts on multiple platforms
4. Document usage in SKILL.md
5. Add error handling and validation
