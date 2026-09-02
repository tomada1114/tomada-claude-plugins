#!/usr/bin/env bash
# worktree_setup.sh — Turn a bare `git worktree` into a working build
# environment, and report whether the project's own verification command is
# already green there — BEFORE any implementation agent is spawned.
#
# A fresh `git worktree add` gives tracked files only: no .env, no
# node_modules, no .venv, so the project's verification command fails before
# it reads a line of code. This script copies the untracked local config the
# worktree is missing, installs dependencies, and (with --verify) runs the
# project's verification command once as a baseline. A red baseline is the
# repository's problem, not the issue's — finding it here costs one command
# instead of a wasted implementation run, so a red baseline is reported as a
# warning, never a script failure.
#
# Usage: worktree_setup.sh --issue <n> --branch <branch> --base <base-ref>
#                          --root <worktrees-root>
#                          [--verify "<command>"] [--log <path>] [--dry-run]
#
# Two facts worth writing down:
#   * .venv is never copied. A virtualenv bakes absolute paths into
#     pyvenv.cfg and its bin/ shims, so a copy of one is broken the moment
#     it lives at a different path. Python deps are always re-created by
#     the matching tool (uv/poetry/pipenv), never cloned.
#   * The worktree, and every file this script writes (copied local config,
#     the baseline log), live OUTSIDE the repo's main checkout, under the
#     caller-supplied --root. This script never creates or modifies
#     anything inside the repo checkout — the skill treats an unexpectedly
#     dirty main checkout as a hard stop condition.
#
# Exit codes:
#   0 = READY or READY_WITH_WARNINGS
#   1 = BLOCKED (see the `verdict:` line for which check failed)
#   2 = usage error

set -uo pipefail
shopt -s nullglob

emit() { printf '%s: %s\n' "$1" "$2"; }

# --- resolve a path to a canonical absolute form, without requiring the
# path (or any of it) to exist yet. Walks up to the nearest existing
# ancestor, canonicalizes that with `cd && pwd -P` (which resolves symlinks
# and any `..`/`.` components in one shot), then reappends the missing tail.
resolve_path() {
  local p="$1" d b
  if [[ -d "$p" ]]; then
    (cd "$p" && pwd -P)
    return
  fi
  if [[ -e "$p" ]]; then
    printf '%s/%s\n' "$(cd "$(dirname "$p")" && pwd -P)" "$(basename "$p")"
    return
  fi
  d="$(dirname "$p")"
  b="$(basename "$p")"
  if [[ "$d" == "$p" ]]; then
    printf '%s\n' "$p"
  else
    printf '%s/%s\n' "$(resolve_path "$d")" "$b"
  fi
}

# --- args --------------------------------------------------------------
ISSUE="" BRANCH="" BASE="" ROOT="" VERIFY="" LOG="" DRY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --issue)  [[ $# -ge 2 ]] || { echo "--issue needs a value" >&2; exit 2; }; ISSUE="$2"; shift 2 ;;
    --branch) [[ $# -ge 2 ]] || { echo "--branch needs a value" >&2; exit 2; }; BRANCH="$2"; shift 2 ;;
    --base)   [[ $# -ge 2 ]] || { echo "--base needs a value" >&2; exit 2; }; BASE="$2"; shift 2 ;;
    --root)   [[ $# -ge 2 ]] || { echo "--root needs a value" >&2; exit 2; }; ROOT="$2"; shift 2 ;;
    --verify) [[ $# -ge 2 ]] || { echo "--verify needs a value" >&2; exit 2; }; VERIFY="$2"; shift 2 ;;
    --log)    [[ $# -ge 2 ]] || { echo "--log needs a value" >&2; exit 2; }; LOG="$2"; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$ISSUE" || -z "$BRANCH" || -z "$BASE" || -z "$ROOT" ]]; then
  echo "Usage: worktree_setup.sh --issue <n> --branch <branch> --base <base-ref> --root <worktrees-root> [--verify \"<command>\"] [--log <path>] [--dry-run]" >&2
  exit 2
fi

# --path-format=absolute --git-common-dir always points at the main .git,
# regardless of which worktree this script is invoked from (see
# cleanup_run.sh for the same idiom and why --show-toplevel is wrong here).
repo_root=$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")
worktree_path="$ROOT/$ISSUE"
warn=0

emit repo_root "$repo_root"
emit worktree "$worktree_path"

branch_exists() { git -C "$repo_root" show-ref --verify --quiet "refs/heads/$1"; }

is_registered_worktree() {
  local target="$1" wt
  target="$(resolve_path "$target")"
  while IFS= read -r wt; do
    wt="${wt#worktree }"
    [[ "$(resolve_path "$wt")" == "$target" ]] && return 0
  done < <(git -C "$repo_root" worktree list --porcelain | grep '^worktree ')
  return 1
}

# --- 2. idempotent re-entry ---------------------------------------------
if [[ -e "$worktree_path" ]]; then
  if is_registered_worktree "$worktree_path"; then
    emit result "EXISTS"
    emit path "$worktree_path"
    echo "verdict: READY"
    exit 0
  else
    emit result "BLOCKED"
    emit path "$worktree_path"
    echo "verdict: BLOCKED"
    exit 1
  fi
fi

# --- 3. create the worktree ---------------------------------------------
if [[ $DRY -eq 1 ]]; then
  echo "DRY: mkdir -p $ROOT"
  if branch_exists "$BRANCH"; then
    echo "DRY: git -C $repo_root worktree add $worktree_path $BRANCH"
  else
    echo "DRY: git -C $repo_root worktree add $worktree_path -b $BRANCH $BASE"
  fi
else
  mkdir -p "$ROOT"
  wt_log="$(mktemp)"
  if branch_exists "$BRANCH"; then
    git -C "$repo_root" worktree add "$worktree_path" "$BRANCH" >"$wt_log" 2>&1
  else
    git -C "$repo_root" worktree add "$worktree_path" -b "$BRANCH" "$BASE" >"$wt_log" 2>&1
  fi
  wt_rc=$?
  if [[ $wt_rc -ne 0 ]]; then
    emit result "BLOCKED"
    sed 's/^/  /' "$wt_log"
    rm -f "$wt_log"
    echo "verdict: BLOCKED"
    exit 1
  fi
  rm -f "$wt_log"
  emit result "CREATED"
fi

# --- 4. copy the untracked local config the worktree is missing --------
config_patterns=(".env" ".env.*" "*.local" ".envrc" ".dev.vars" ".claude/settings.local.json" "local.settings.json")
copied_any=0
for pat in "${config_patterns[@]}"; do
  for candidate in "$repo_root"/$pat "$repo_root"/*/$pat; do
    [[ -f "$candidate" ]] || continue
    rel="${candidate#$repo_root/}"
    git -C "$repo_root" ls-files --error-unmatch -- "$rel" >/dev/null 2>&1 && continue
    case "$rel" in
      *.example|*.sample|*.template|*.dist) continue ;;
    esac
    if [[ $DRY -eq 1 ]]; then
      echo "DRY: copied: $rel"
    else
      dest="$worktree_path/$rel"
      mkdir -p "$(dirname "$dest")"
      cp "$candidate" "$dest"
      emit copied "$rel"
    fi
    copied_any=1
  done
done
if [[ $copied_any -eq 0 ]]; then
  if [[ $DRY -eq 1 ]]; then
    echo "DRY: copied: none"
  else
    emit copied "none"
  fi
fi

# --- 5. install dependencies --------------------------------------------
deps_kind="none"
deps_is_npm_ci=0
deps_cmd=()

if   [[ -f "$repo_root/pnpm-lock.yaml" ]];    then deps_kind=pnpm;   deps_cmd=(pnpm install --frozen-lockfile)
elif [[ -f "$repo_root/yarn.lock" ]];         then deps_kind=yarn
elif [[ -f "$repo_root/bun.lockb" || -f "$repo_root/bun.lock" ]]; then deps_kind=bun; deps_cmd=(bun install --frozen-lockfile)
elif [[ -f "$repo_root/package-lock.json" ]]; then deps_kind=npm;    deps_cmd=(npm ci); deps_is_npm_ci=1
elif [[ -f "$repo_root/uv.lock" ]];           then deps_kind=uv;     deps_cmd=(uv sync)
elif [[ -f "$repo_root/poetry.lock" ]];       then deps_kind=poetry; deps_cmd=(poetry install)
elif [[ -f "$repo_root/Pipfile.lock" ]];      then deps_kind=pipenv; deps_cmd=(pipenv install --dev)
elif [[ -f "$repo_root/Gemfile.lock" ]];      then deps_kind=bundle; deps_cmd=(bundle install)
elif [[ -f "$repo_root/go.sum" ]];            then deps_kind=go;     deps_cmd=(go mod download)
elif [[ -f "$repo_root/Cargo.lock" ]];        then deps_kind=cargo
elif [[ -f "$repo_root/requirements.txt" ]];  then deps_kind=manual
fi

node_modules_note=""

clone_node_modules() {
  [[ -d "$repo_root/node_modules" && $deps_is_npm_ci -ne 1 ]] || return 0
  if [[ $DRY -eq 1 ]]; then
    echo "DRY: cp -Rc $repo_root/node_modules $worktree_path/"
    node_modules_note=" (+clonefile node_modules)"
    return 0
  fi
  if cp -Rc "$repo_root/node_modules" "$worktree_path/" 2>/dev/null; then
    node_modules_note=" (+clonefile node_modules)"
  elif cp -R "$repo_root/node_modules" "$worktree_path/" 2>/dev/null; then
    node_modules_note=" (+copy node_modules)"
  fi
  # cp failing outright is an optimization miss, not a failure: fall through
  # with no note and let the install command populate node_modules itself.
}

# Runs "$@" with cwd = the worktree. On a non-zero exit (including "command
# not found", which exits 127) this reports BLOCKED and exits the script —
# it never returns to the caller in that case.
run_install_cmd() {
  local logf rc out
  logf="$(mktemp)"
  ( cd "$worktree_path" && "$@" ) >"$logf" 2>&1
  rc=$?
  if [[ $rc -ne 0 ]]; then
    out="$(tail -20 "$logf")"
    rm -f "$logf"
    emit deps "FAILED: $* (exit=$rc)"
    printf '%s\n' "$out" | sed 's/^/  /'
    echo "verdict: BLOCKED"
    exit 1
  fi
  rm -f "$logf"
}

do_install() {
  if [[ $DRY -eq 1 ]]; then
    echo "DRY: (cd $worktree_path && $*)"
    return
  fi
  run_install_cmd "$@"
  emit deps "$*"
}

do_install_js() {
  if [[ $DRY -eq 1 ]]; then
    clone_node_modules
    echo "DRY: (cd $worktree_path && $*)"
    return
  fi
  clone_node_modules
  run_install_cmd "$@"
  emit deps "$*${node_modules_note}"
}

do_install_yarn() {
  if [[ $DRY -eq 1 ]]; then
    clone_node_modules
    echo "DRY: (cd $worktree_path && yarn install --immutable, falling back to --frozen-lockfile)"
    return
  fi
  clone_node_modules
  local logf rc
  logf="$(mktemp)"
  ( cd "$worktree_path" && yarn install --immutable ) >"$logf" 2>&1
  rc=$?
  rm -f "$logf"
  if [[ $rc -eq 0 ]]; then
    emit deps "yarn install --immutable${node_modules_note}"
    return
  fi
  run_install_cmd yarn install --frozen-lockfile
  emit deps "yarn install --frozen-lockfile (fallback from --immutable)${node_modules_note}"
}

case "$deps_kind" in
  pnpm|bun|npm) do_install_js "${deps_cmd[@]}" ;;
  yarn)         do_install_yarn ;;
  uv|poetry|pipenv|bundle|go) do_install "${deps_cmd[@]}" ;;
  cargo)
    [[ $DRY -eq 1 ]] && echo "DRY: deps: none-needed (cargo builds on demand)" || emit deps "none-needed (cargo builds on demand)"
    ;;
  manual)
    if [[ $DRY -eq 1 ]]; then
      echo "DRY: deps: MANUAL(requirements.txt)"
    else
      emit deps "MANUAL(requirements.txt)"
      warn=1
    fi
    ;;
  none)
    [[ $DRY -eq 1 ]] && echo "DRY: deps: none" || emit deps "none"
    ;;
esac

# --- 6. verification baseline (only with --verify) ----------------------
if [[ -n "$VERIFY" ]]; then
  if [[ -n "$LOG" ]]; then
    log_path="$LOG"
  else
    log_path="$ROOT/../verify/${ISSUE}-baseline.log"
  fi
  log_dir="$(dirname "$log_path")"

  resolved_log="$(resolve_path "$log_path")"
  resolved_repo_root="$(resolve_path "$repo_root")"
  resolved_worktree="$(resolve_path "$worktree_path")"

  case "$resolved_log" in
    "$resolved_repo_root"/*|"$resolved_worktree"/*)
      emit baseline_log "$log_path"
      echo "verdict: BLOCKED"
      exit 1
      ;;
  esac

  if [[ $DRY -eq 1 ]]; then
    echo "DRY: mkdir -p $log_dir"
    echo "DRY: (cd $worktree_path && $VERIFY) > $log_path 2>&1"
  else
    mkdir -p "$log_dir"
    ( cd "$worktree_path" && bash -c "$VERIFY" ) >"$log_path" 2>&1
    verify_rc=$?
    if [[ $verify_rc -eq 0 ]]; then
      emit baseline "PASS"
    else
      emit baseline "FAIL(exit=$verify_rc)"
      warn=1
    fi
    emit baseline_log "$log_path"
    [[ $verify_rc -ne 0 ]] && tail -15 "$log_path" | sed 's/^/  /'
  fi
fi

# --- 7. verdict -----------------------------------------------------------
if [[ $warn -eq 1 ]]; then
  echo "verdict: READY_WITH_WARNINGS"
else
  echo "verdict: READY"
fi
exit 0
