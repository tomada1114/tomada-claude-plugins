#!/usr/bin/env python3
"""
Project Validator Script

This script validates common project structure and configuration.
It checks for required files, valid JSON, git setup, and dependencies.
"""

import os
import json
import sys
from pathlib import Path


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'


def check_mark(passed):
    """Return check mark or X based on passed status"""
    if passed:
        return f"{Colors.GREEN}✓{Colors.END}"
    return f"{Colors.RED}✗{Colors.END}"


def validate_file_exists(filepath, description):
    """Check if a file exists"""
    exists = os.path.exists(filepath)
    status = check_mark(exists)
    print(f"{status} {description}")
    return exists


def validate_json_file(filepath, description):
    """Check if file exists and contains valid JSON"""
    if not os.path.exists(filepath):
        print(f"{check_mark(False)} {description} - file not found")
        return False

    try:
        with open(filepath, 'r') as f:
            json.load(f)
        print(f"{check_mark(True)} {description}")
        return True
    except json.JSONDecodeError as e:
        print(f"{check_mark(False)} {description} - invalid JSON: {e}")
        return False


def validate_git_repo():
    """Check if directory is a git repository"""
    is_git = os.path.exists('.git')
    status = check_mark(is_git)
    print(f"{status} Git repository initialized")
    return is_git


def validate_node_modules():
    """Check if node_modules exists"""
    exists = os.path.exists('node_modules')
    status = check_mark(exists)
    message = "node_modules installed"
    if not exists:
        message += f" - {Colors.YELLOW}run 'npm install'{Colors.END}"
    print(f"{status} {message}")
    return exists


def validate_typescript():
    """Check if TypeScript is configured"""
    has_tsconfig = os.path.exists('tsconfig.json')
    if has_tsconfig:
        print(f"{check_mark(True)} TypeScript configured (tsconfig.json found)")
        return True
    print(f"{Colors.BLUE}ℹ{Colors.END} TypeScript not configured (optional)")
    return True  # Not an error, just optional


def validate_env_file():
    """Check for environment configuration"""
    has_env = os.path.exists('.env')
    has_example = os.path.exists('.env.example')

    if has_env:
        print(f"{check_mark(True)} Environment file (.env) present")
        return True
    elif has_example:
        print(f"{check_mark(False)} .env file missing - {Colors.YELLOW}copy from .env.example{Colors.END}")
        return False
    else:
        print(f"{Colors.BLUE}ℹ{Colors.END} No environment files (may not be required)")
        return True


def main():
    """Run all validation checks"""
    print(f"\n{Colors.BOLD}=== Project Validation Report ==={Colors.END}\n")

    checks = []

    # Required files
    checks.append(validate_json_file('package.json', 'package.json found and valid'))
    checks.append(validate_file_exists('README.md', 'README.md exists'))
    checks.append(validate_file_exists('.gitignore', '.gitignore present'))

    # Git setup
    checks.append(validate_git_repo())

    # Dependencies
    checks.append(validate_node_modules())

    # Optional configurations
    validate_typescript()  # Don't count as failure
    validate_env_file()    # May or may not be required

    # Summary
    print(f"\n{Colors.BOLD}Summary:{Colors.END}")
    passed = sum(checks)
    total = len(checks)
    failed = total - passed

    if failed == 0:
        print(f"{Colors.GREEN}✓ All checks passed! Project is properly configured.{Colors.END}")
        sys.exit(0)
    else:
        print(f"{Colors.RED}✗ {failed} issue(s) found.{Colors.END}")
        print(f"\nRun suggested commands to fix issues.")
        sys.exit(1)


if __name__ == '__main__':
    main()
