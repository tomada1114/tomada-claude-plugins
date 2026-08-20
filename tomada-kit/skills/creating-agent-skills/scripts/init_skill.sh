#!/usr/bin/env bash
# init_skill.sh — Scaffold a new Claude Code skill directory.
#
# Usage:
#   init_skill.sh <skill-name> [basic|advanced] [--scope user|project]
#
# Defaults:
#   template = basic
#   scope    = user  (~/.claude/skills/<name>)   # scripts-ignore: S006
#
# Exit codes:
#   0 = created
#   1 = bad arguments
#   2 = target already exists
#   3 = template not found

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(dirname "$SCRIPT_DIR")"
ASSETS_DIR="$SKILL_ROOT/assets"

NAME=""
TEMPLATE="basic"
SCOPE="user"

usage() {
  sed -n '2,12p' "$0" >&2
  exit 1
}

# Parse arguments
if [[ $# -lt 1 ]]; then usage; fi
NAME="$1"; shift
while [[ $# -gt 0 ]]; do
  case "$1" in
    basic|advanced) TEMPLATE="$1"; shift ;;
    --scope) SCOPE="${2:-}"; shift 2 ;;
    -h|--help) usage ;;
    *) echo "Unknown argument: $1" >&2; usage ;;
  esac
done

# Validate name (must match official skill name regex)
if [[ ! "$NAME" =~ ^[a-z0-9][a-z0-9-]*[a-z0-9]$ ]]; then
  echo "Error: skill name must match ^[a-z0-9][a-z0-9-]*[a-z0-9]$ (kebab-case, 2+ chars)" >&2
  exit 1
fi
if [[ ${#NAME} -gt 64 ]]; then
  echo "Error: skill name max 64 chars" >&2
  exit 1
fi

# Resolve target directory
case "$SCOPE" in
  user)    BASE="$HOME/.claude/skills" ;;   # scripts-ignore: S006
  project) BASE="$(pwd)/.claude/skills" ;;
  *) echo "Error: --scope must be 'user' or 'project'" >&2; exit 1 ;;
esac
TARGET="$BASE/$NAME"

if [[ -e "$TARGET" ]]; then
  echo "Error: $TARGET already exists" >&2
  exit 2
fi

TEMPLATE_FILE="$ASSETS_DIR/${TEMPLATE}-skill-template.md"
if [[ ! -f "$TEMPLATE_FILE" ]]; then
  echo "Error: template not found: $TEMPLATE_FILE" >&2
  exit 3
fi

# Create directory layout
mkdir -p "$TARGET"
if [[ "$TEMPLATE" == "advanced" ]]; then
  mkdir -p "$TARGET/references" "$TARGET/assets" "$TARGET/scripts"
fi

# Copy template and substitute name placeholder in frontmatter
SKILL_MD="$TARGET/SKILL.md"
sed -e "s/^name: your-skill-name/name: $NAME/" \
    -e "s/^name: advanced-skill-name/name: $NAME/" \
    "$TEMPLATE_FILE" > "$SKILL_MD"

echo "Created skill scaffold:"
echo "  $TARGET"
echo ""
echo "Next steps:"
echo "  1. Edit $SKILL_MD"
echo "  2. Replace the placeholder description (key use case first, English only)"
echo "  3. Run: python3 $SCRIPT_DIR/validate_skill.py $TARGET"
