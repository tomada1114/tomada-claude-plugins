---
name: project-validator
description: Validate project structure, dependencies, and configuration files. Use when setting up projects, checking project health, or troubleshooting configuration issues.
---

# Project Validator

This skill validates common project configurations and structure. It demonstrates how to use scripts for deterministic validation tasks.

## When to Use This Skill

Use this skill when:
- Setting up a new project
- Troubleshooting configuration issues
- Ensuring project follows best practices
- Onboarding new team members
- Pre-deployment checks

## Validation Checks

This skill performs the following validations:

1. **File Structure**: Checks for required files and directories
2. **Dependencies**: Validates package.json and lock files
3. **Configuration**: Checks for proper config files
4. **Git Setup**: Ensures git is configured properly
5. **Environment**: Validates .env files and required variables

## Instructions

### Quick Validation

Run the validation script to check your project:

```bash
python scripts/validate.py
```

This will check:
- ✓ package.json exists and is valid JSON
- ✓ README.md exists
- ✓ .gitignore is present
- ✓ Git repository is initialized
- ✓ Node modules are installed
- ✓ Required environment variables are set

### Setup Script

For new projects, run the setup script:

```bash
bash scripts/setup.sh
```

This will:
1. Initialize git if not already initialized
2. Create .gitignore if missing
3. Create basic README.md template
4. Set up pre-commit hooks
5. Install dependencies

## Examples

### Example 1: Validate Existing Project

```bash
$ python scripts/validate.py

=== Project Validation Report ===

✓ package.json found and valid
✓ README.md exists
✓ .gitignore present
✓ Git repository initialized
✗ node_modules not found - run 'npm install'
✓ TypeScript configured (tsconfig.json found)

Issues found: 1
Run suggested commands to fix issues.
```

### Example 2: Setup New Project

```bash
$ bash scripts/setup.sh

=== Project Setup ===

✓ Git initialized
✓ Created .gitignore with Node.js defaults
✓ Created README.md template
✓ Installing dependencies...
✓ Setup complete!

Next steps:
1. Review and customize README.md
2. Add your project description to package.json
3. Configure environment variables in .env
```

## Script Details

### validate.py

Python script that checks:
- File existence and validity
- JSON syntax in config files
- Git repository status
- Dependency installation
- Environment configuration

**Why Python?**
- Cross-platform compatibility (works on Windows, Mac, Linux)
- Rich standard library for file operations
- Easy to extend with additional checks
- Better error handling than shell scripts

### setup.sh

Shell script that:
- Initializes project structure
- Creates boilerplate files
- Runs initialization commands

**Why Shell?**
- Simple command chaining
- Native git/npm integration
- Fast for straightforward tasks
- Familiar to most developers

## Customization

You can customize the validation by editing the scripts:

**Add custom checks to validate.py:**
```python
def check_custom_requirement():
    """Add your custom validation logic"""
    if not os.path.exists('custom-file.json'):
        return False, "custom-file.json is missing"
    return True, "Custom check passed"
```

**Add setup steps to setup.sh:**
```bash
# Add custom initialization
echo "Running custom setup..."
mkdir -p custom-directory
cp template.txt custom-directory/
```

## Best Practices

- Run validation before commits
- Include validation in CI/CD pipeline
- Keep scripts up-to-date with project requirements
- Document any custom checks
- Use exit codes for automation

## AI Assistant Instructions

When this skill is activated:

1. **Assess the situation**: Determine if this is a new project or existing one
2. **Recommend appropriate script**:
   - New project → suggest `setup.sh`
   - Existing project → suggest `validate.py`
3. **Run the script**: Execute the appropriate script
4. **Review output**: Analyze validation results
5. **Provide fixes**: If issues found, suggest specific commands to fix them

Always:
- Run the scripts from the project root directory
- Explain what each script does before running
- Show the full output to the user
- Provide actionable next steps based on results

Never:
- Run scripts without explaining what they do
- Modify scripts without user permission
- Skip validation steps
- Assume project structure without checking
