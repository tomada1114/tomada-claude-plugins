#!/usr/bin/env bash
# bridge_symlink.sh — Make a real Claude skill folder visible to Codex via a symlink.
#
# Topology A: the REAL skill lives at .claude/skills/<name>/ (Claude reads it natively);
# Codex reaches the SAME folder through a symlink it officially follows.
#
# Usage:
#   bridge_symlink.sh <real-skill-path> [--scope user|repo] [--codex-dir <dir>]
#                     [--relative] [--dry-run]
#
# Scope resolution (when --codex-dir not given):
#   user  -> $CODEX_HOME/skills (default ~/.codex/skills)
#   repo  -> <repo-root>/.agents/skills   (repo-root = git toplevel of the real skill)
#   auto  -> if real skill is under $HOME/.claude/skills      => user
#            if real skill is under <repo>/.claude/skills     => repo
#
# Safety:
#   - Refuses if <real-skill-path> is itself a symlink or lacks SKILL.md.
#   - Refuses to clobber a target that is a REAL directory/file (only repoints symlinks).
#   - Idempotent: re-running when the link already points correctly reports OK.
#
# Cleanup (always on, not a flag):
#   - Before creating/repointing the requested symlink, sweeps CODEX_DIR for
#     dangling symlinks (source .claude/skills/<name> no longer exists) and
#     unlinks them (also dropping their .gitignore entry if tracked there).
#   - Only ever touches BROKEN symlinks. Real Codex-only directories and any
#     symlink that still resolves are never removed. Independent of git (works
#     even when CODEX_DIR is not inside a git work tree, e.g. ~/.codex/skills).
#
# Exit codes: 0 = ok/idempotent, 1 = bad args, 2 = unsafe target, 3 = source invalid
set -euo pipefail

REAL=""
SCOPE="auto"
CODEX_DIR=""
RELATIVE=0
DRY_RUN=0

die() { echo "Error: $*" >&2; exit "${2:-1}"; }

[[ $# -ge 1 ]] || die "missing <real-skill-path>. See header for usage." 1
REAL="$1"; shift
while [[ $# -gt 0 ]]; do
  case "$1" in
    --scope) SCOPE="${2:-}"; shift 2 ;;
    --codex-dir) CODEX_DIR="${2:-}"; shift 2 ;;
    --relative) RELATIVE=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) sed -n '2,30p' "$0"; exit 0 ;;
    *) die "unknown argument: $1" 1 ;;
  esac
done

# --- Validate source ---------------------------------------------------------
[[ -e "$REAL" ]] || die "real skill path does not exist: $REAL" 3
[[ -L "$REAL" ]] && die "real skill path is itself a symlink (must be the real folder): $REAL" 3
[[ -d "$REAL" ]] || die "real skill path is not a directory: $REAL" 3
REAL="$(cd "$REAL" && pwd -P)"                 # canonical absolute path
[[ -f "$REAL/SKILL.md" ]] || die "no SKILL.md under $REAL" 3
NAME="$(basename "$REAL")"

# --- Resolve Codex skills dir ------------------------------------------------
codex_home() { echo "${CODEX_HOME:-$HOME/.codex}"; }

repo_root_of() {
  git -C "$1" rev-parse --show-toplevel 2>/dev/null || true
}

if [[ -z "$CODEX_DIR" ]]; then
  if [[ "$SCOPE" == "auto" ]]; then
    case "$REAL" in
      "$HOME/.claude/skills/"*) SCOPE="user" ;;
      *"/.claude/skills/"*)     SCOPE="repo" ;;
      *) SCOPE="user" ;;
    esac
  fi
  case "$SCOPE" in
    user) CODEX_DIR="$(codex_home)/skills" ;;
    repo)
      RR="$(repo_root_of "$REAL")"
      [[ -n "$RR" ]] || die "repo scope but no git repo found for $REAL" 1
      CODEX_DIR="$RR/.agents/skills" ;;
    *) die "--scope must be user|repo|auto" 1 ;;
  esac
fi

# --- Sweep dangling symlinks (always; not gated by a flag, not gated by git) -
# Any symlink directly under CODEX_DIR that no longer resolves means its real
# .claude/skills/<name> source was deleted; unlink it. Only ever touches
# BROKEN symlinks — real directories and symlinks that still resolve are left
# alone, so hand-placed Codex-only skills are never at risk.
sweep_dangling_symlinks() {
  local dir="$1" gi="$1/.gitignore" p name
  [[ -d "$dir" ]] || return 0
  for p in "$dir"/*; do
    [[ -L "$p" && ! -e "$p" ]] || continue
    name="$(basename "$p")"
    if [[ "$DRY_RUN" -eq 1 ]]; then
      echo "[dry-run] would unlink dangling symlink (source removed): $p"
      continue
    fi
    rm -f "$p"
    echo "unlinked dangling symlink (source removed): $p"
    if [[ -f "$gi" ]] && grep -qxF "$name" "$gi" 2>/dev/null; then
      grep -vxF "$name" "$gi" > "$gi.tmp" && mv "$gi.tmp" "$gi"
    fi
  done
}

sweep_dangling_symlinks "$CODEX_DIR"

TARGET="$CODEX_DIR/$NAME"

# --- Compute link source (absolute or relative) ------------------------------
LINK_SRC="$REAL"
if [[ "$RELATIVE" -eq 1 ]]; then
  # relative path from TARGET's parent (CODEX_DIR) to REAL
  if command -v python3 >/dev/null 2>&1; then
    LINK_SRC="$(python3 -c 'import os,sys;print(os.path.relpath(sys.argv[1],sys.argv[2]))' "$REAL" "$CODEX_DIR")"
  fi
fi

echo "skill:      $NAME"
echo "real:       $REAL"
echo "codex dir:  $CODEX_DIR  (scope=$SCOPE)"
echo "target:     $TARGET"
echo "link src:   $LINK_SRC"

# --- Register generated symlink in <codex-dir>/.gitignore (git work tree only)
# Ignore ONLY generated bridge symlinks so real Codex-only content stays committable.
register_gitignore() {
  [[ "$DRY_RUN" -eq 1 ]] && return 0
  git -C "$CODEX_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1 || return 0
  local GI="$CODEX_DIR/.gitignore"
  if ! { [[ -f "$GI" ]] && grep -qxF "$NAME" "$GI"; }; then
    [[ -f "$GI" ]] || printf '# Generated Codex bridge symlinks (managed by bridge_symlink.sh).\n# Real Codex-only skills are NOT listed here and remain committable.\n' > "$GI"
    printf '%s\n' "$NAME" >> "$GI"
    echo "registered '$NAME' in $GI"
  fi
}

# --- Idempotency / safety on existing target ---------------------------------
if [[ -L "$TARGET" ]]; then
  CUR="$(readlink "$TARGET")"
  CUR_RESOLVED="$(cd "$(dirname "$TARGET")" && cd "$(dirname "$CUR")" 2>/dev/null && pwd -P)/$(basename "$CUR")" || CUR_RESOLVED="$CUR"
  if [[ "$(cd "$TARGET" 2>/dev/null && pwd -P || echo)" == "$REAL" ]]; then
    register_gitignore
    echo "OK: symlink already points to the real skill (idempotent no-op)."
    exit 0
  fi
  echo "Note: existing symlink points elsewhere ($CUR); will repoint."
elif [[ -e "$TARGET" ]]; then
  die "target exists and is a REAL file/dir (refusing to clobber): $TARGET" 2
fi

# --- Apply -------------------------------------------------------------------
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[dry-run] mkdir -p $CODEX_DIR && ln -sfn $LINK_SRC $TARGET"
  exit 0
fi

mkdir -p "$CODEX_DIR"
ln -sfn "$LINK_SRC" "$TARGET"

register_gitignore

# --- Verify ------------------------------------------------------------------
if [[ "$(cd "$TARGET" && pwd -P)" == "$REAL" && -f "$TARGET/SKILL.md" ]]; then
  echo "OK: $TARGET -> $REAL (Codex will discover '$NAME')."
  exit 0
fi
die "symlink created but does not resolve to the real skill" 2
