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
# warning, never a script failure — see "This script REPORTS" below.
#
# Usage: worktree_setup.sh --issue <n> --branch <branch> --base <base-ref>
#                          --root <worktrees-root>
#                          [--verify "<command>"] [--log <path>] [--dry-run]
#
#    or: worktree_setup.sh --spec <issue>:<branch> [--spec <issue>:<branch> ...]
#                          --base <base-ref> --root <worktrees-root>
#                          [--verify "<command>"] [--log-dir <dir>]
#                          [--verify-timeout <seconds>] [--dry-run]
#
# --spec provisions several worktrees in ONE invocation, SEQUENTIALLY — never
# in parallel. Two reasons: the dependency installs all contend for the same
# package-manager cache (pnpm store, pip/uv cache, ...), so running them
# concurrently just serializes on filesystem locks anyway but with none of the
# clarity; and a verify command that binds a fixed port or writes to one local
# dev database fails in ways that look like the issue's fault when it's really
# two worktrees racing each other, which is worse than a slower, honest run.
#
# This script REPORTS; it does not decide. A red baseline in a fresh worktree
# usually means the repo is not worktree-viable right now — a fresh worktree
# holds tracked files and nothing else: no .env beyond what got copied, no
# pre-warmed cache, no locally-running service it depends on — but "usually" is
# not "always", and telling the two apart needs the diff, the log, and the
# repo's own conventions in view. So the baseline is a warning here and the
# caller decides what it means, including whether to tear the worktree down.
# Provision the batch in small groups if that judgement matters: reading
# worktree #1's block before asking for #2 and #3 costs one extra call and
# keeps the decision where it can actually be made.
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
#     dirty main checkout as a hard stop condition. This guard is enforced
#     per-spec in batch mode, not just for the first one.
#
# Exit codes:
#   0 = READY or READY_WITH_WARNINGS (batch: every spec READY/READY_WITH_WARNINGS)
#   1 = BLOCKED (see the `verdict:` line for which check failed; batch: any
#       spec BLOCKED)
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

# Run a verify command with a hard wall-clock bound. Exits 124 on timeout, the
# same code timeout(1) uses, so callers can tell "never finished" apart from
# "finished red". stdout/stderr go straight through to the caller's redirect.
run_verify_bounded() {
  python3 - "$1" "$2" "$3" <<'PYTIMEOUT'
import os
import signal
import subprocess
import sys

workdir, command, timeout = sys.argv[1], sys.argv[2], float(sys.argv[3])
proc = subprocess.Popen(["bash", "-c", command], cwd=workdir,
                        start_new_session=True)
try:
    sys.exit(proc.wait(timeout=timeout))
except subprocess.TimeoutExpired:
    # The whole process group, not just the shell: a runner that forked workers
    # would otherwise outlive the kill still holding whatever it bound.
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(os.getpgid(proc.pid), sig)
        except (ProcessLookupError, PermissionError):
            break
        try:
            proc.wait(timeout=5)
            break
        except subprocess.TimeoutExpired:
            continue
    sys.exit(124)
PYTIMEOUT
}

usage() {
  echo "Usage: worktree_setup.sh --issue <n> --branch <branch> --base <base-ref> --root <worktrees-root> [--verify \"<command>\"] [--log <path>] [--dry-run]" >&2
  echo "   or: worktree_setup.sh --spec <issue>:<branch> [--spec ...] --base <base-ref> --root <worktrees-root> [--verify \"<command>\"] [--log-dir <dir>] [--verify-timeout <seconds>] [--dry-run]" >&2
}

# print_help — the script's own usage, derived straight from this header
# comment so the text lives in exactly one place (kept separate from usage()
# above, which is the short one-liner already used on stderr for arg errors).
print_help() {
  awk 'NR==1{next} /^#/{sub(/^# ?/,""); print; next} {exit}' "${BASH_SOURCE[0]}"
}

# --- args --------------------------------------------------------------
ISSUE="" BRANCH="" BASE="" ROOT="" VERIFY="" LOG="" DRY=0
LOG_DIR="" VERIFY_TIMEOUT="900"
SPECS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) print_help; exit 0 ;;
    --issue)  [[ $# -ge 2 ]] || { echo "--issue needs a value" >&2; exit 2; }; ISSUE="$2"; shift 2 ;;
    --branch) [[ $# -ge 2 ]] || { echo "--branch needs a value" >&2; exit 2; }; BRANCH="$2"; shift 2 ;;
    --base)   [[ $# -ge 2 ]] || { echo "--base needs a value" >&2; exit 2; }; BASE="$2"; shift 2 ;;
    --root)   [[ $# -ge 2 ]] || { echo "--root needs a value" >&2; exit 2; }; ROOT="$2"; shift 2 ;;
    --verify) [[ $# -ge 2 ]] || { echo "--verify needs a value" >&2; exit 2; }; VERIFY="$2"; shift 2 ;;
    --log)    [[ $# -ge 2 ]] || { echo "--log needs a value" >&2; exit 2; }; LOG="$2"; shift 2 ;;
    --log-dir) [[ $# -ge 2 ]] || { echo "--log-dir needs a value" >&2; exit 2; }; LOG_DIR="$2"; shift 2 ;;
    --verify-timeout) [[ $# -ge 2 ]] || { echo "--verify-timeout needs a value" >&2; exit 2; }; VERIFY_TIMEOUT="$2"; shift 2 ;;
    --spec)   [[ $# -ge 2 ]] || { echo "--spec needs a value" >&2; exit 2; }; SPECS+=("$2"); shift 2 ;;
    --dry-run) DRY=1; shift ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 2 ;;
  esac
done

# --- validation ----------------------------------------------------------
if [[ ${#SPECS[@]} -gt 0 && -n "$ISSUE" ]]; then
  echo "--spec and --issue are mutually exclusive" >&2
  exit 2
fi
if [[ ! "$VERIFY_TIMEOUT" =~ ^[0-9]+$ || "$VERIFY_TIMEOUT" -eq 0 ]]; then
  echo "--verify-timeout requires a positive integer (seconds)" >&2
  exit 2
fi
if [[ ${#SPECS[@]} -gt 0 && -n "$LOG" ]]; then
  echo "--log is single-issue only; use --log-dir with --spec" >&2
  exit 2
fi

if [[ ${#SPECS[@]} -eq 0 ]]; then
  if [[ -z "$ISSUE" || -z "$BRANCH" || -z "$BASE" || -z "$ROOT" ]]; then
    usage
    exit 2
  fi
else
  if [[ -z "$BASE" || -z "$ROOT" ]]; then
    usage
    exit 2
  fi
  for spec in "${SPECS[@]}"; do
    case "$spec" in
      *:*) ;;
      *) echo "Invalid --spec (expected <issue>:<branch>): $spec" >&2; exit 2 ;;
    esac
    spec_issue="${spec%%:*}"
    if [[ ! "$spec_issue" =~ ^[0-9]+$ ]]; then
      echo "Invalid --spec issue number (must be digits): $spec" >&2
      exit 2
    fi
  done
fi

# --path-format=absolute --git-common-dir always points at the main .git,
# regardless of which worktree this script is invoked from (see
# cleanup_run.sh for the same idiom and why --show-toplevel is wrong here).
# This is the same for every spec in a batch, so it's computed once.
repo_root=$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")

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

# --- dependency-manager detection ---------------------------------------
# This is purely a function of repo_root's file listing, so (unlike the
# per-worktree steps below) it's computed once, not once per spec. Kept in
# sync by hand with preflight.sh's pkg_manager/lockfile precedence — see the
# comment there.
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
# not found", which exits 127) this reports the failure and returns 1 — it
# never calls exit itself, so a batch run can move on to the next spec.
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
    return 1
  fi
  rm -f "$logf"
  return 0
}

do_install() {
  if [[ $DRY -eq 1 ]]; then
    echo "DRY: (cd $worktree_path && $*)"
    return 0
  fi
  run_install_cmd "$@" || return 1
  emit deps "$*"
}

do_install_js() {
  if [[ $DRY -eq 1 ]]; then
    clone_node_modules
    echo "DRY: (cd $worktree_path && $*)"
    return 0
  fi
  clone_node_modules
  run_install_cmd "$@" || return 1
  emit deps "$*${node_modules_note}"
}

do_install_yarn() {
  if [[ $DRY -eq 1 ]]; then
    clone_node_modules
    echo "DRY: (cd $worktree_path && yarn install --immutable, falling back to --frozen-lockfile)"
    return 0
  fi
  clone_node_modules
  local logf rc
  logf="$(mktemp)"
  ( cd "$worktree_path" && yarn install --immutable ) >"$logf" 2>&1
  rc=$?
  rm -f "$logf"
  if [[ $rc -eq 0 ]]; then
    emit deps "yarn install --immutable${node_modules_note}"
    return 0
  fi
  run_install_cmd yarn install --frozen-lockfile || return 1
  emit deps "yarn install --frozen-lockfile (fallback from --immutable)${node_modules_note}"
}

# --- provision_one: everything that used to be this whole script's tail,
# now per-spec. Never calls `exit` — every failure path `return`s 1 so a
# batch run can continue with the remaining specs; the single-issue driver
# below turns that return code straight into the process exit code, which
# preserves the original (pre-batch) single-issue behavior exactly.
#
# Sets globals PROVISION_VERDICT (READY|READY_WITH_WARNINGS|BLOCKED) and
# PROVISION_BASELINE (PASS|FAIL|NONE) for the caller to read.
provision_one() {
  local p_issue="$1" p_branch="$2" p_base="$3" p_root="$4" p_verify="$5" p_log="$6"
  local warn=0
  worktree_path="$p_root/$p_issue"
  node_modules_note=""
  PROVISION_VERDICT=""
  PROVISION_BASELINE="NONE"

  emit repo_root "$repo_root"
  emit worktree "$worktree_path"

  # --- 2. idempotent re-entry ---------------------------------------------
  if [[ -e "$worktree_path" ]]; then
    if is_registered_worktree "$worktree_path"; then
      emit result "EXISTS"
      emit path "$worktree_path"
      PROVISION_VERDICT="READY"
      echo "verdict: READY"
      return 0
    else
      emit result "BLOCKED"
      emit path "$worktree_path"
      PROVISION_VERDICT="BLOCKED"
      echo "verdict: BLOCKED"
      return 1
    fi
  fi

  # --- 3. create the worktree ---------------------------------------------
  if [[ $DRY -eq 1 ]]; then
    echo "DRY: mkdir -p $p_root"
    if branch_exists "$p_branch"; then
      echo "DRY: git -C $repo_root worktree add $worktree_path $p_branch"
    else
      echo "DRY: git -C $repo_root worktree add $worktree_path -b $p_branch $p_base"
    fi
  else
    mkdir -p "$p_root"
    local wt_log wt_rc
    wt_log="$(mktemp)"
    if branch_exists "$p_branch"; then
      git -C "$repo_root" worktree add "$worktree_path" "$p_branch" >"$wt_log" 2>&1
    else
      git -C "$repo_root" worktree add "$worktree_path" -b "$p_branch" "$p_base" >"$wt_log" 2>&1
    fi
    wt_rc=$?
    if [[ $wt_rc -ne 0 ]]; then
      emit result "BLOCKED"
      sed 's/^/  /' "$wt_log"
      rm -f "$wt_log"
      PROVISION_VERDICT="BLOCKED"
      echo "verdict: BLOCKED"
      return 1
    fi
    rm -f "$wt_log"
    emit result "CREATED"
  fi

  # --- 4. copy the untracked local config the worktree is missing --------
  local config_patterns=(".env" ".env.*" "*.local" ".envrc" ".dev.vars" ".claude/settings.local.json" "local.settings.json")
  local copied_any=0 pat candidate rel dest
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
  local deps_failed=0
  case "$deps_kind" in
    pnpm|bun|npm) do_install_js "${deps_cmd[@]}" || deps_failed=1 ;;
    yarn)         do_install_yarn || deps_failed=1 ;;
    uv|poetry|pipenv|bundle|go) do_install "${deps_cmd[@]}" || deps_failed=1 ;;
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
  if [[ $deps_failed -eq 1 ]]; then
    PROVISION_VERDICT="BLOCKED"
    echo "verdict: BLOCKED"
    return 1
  fi

  # --- 6. verification baseline (only with --verify) ----------------------
  if [[ -n "$p_verify" ]]; then
    local log_path="$p_log" log_dir resolved_log resolved_repo_root resolved_worktree verify_rc
    log_dir="$(dirname "$log_path")"

    resolved_log="$(resolve_path "$log_path")"
    resolved_repo_root="$(resolve_path "$repo_root")"
    resolved_worktree="$(resolve_path "$worktree_path")"

    case "$resolved_log" in
      "$resolved_repo_root"/*|"$resolved_worktree"/*)
        emit baseline_log "$log_path"
        PROVISION_VERDICT="BLOCKED"
        echo "verdict: BLOCKED"
        return 1
        ;;
    esac

    if [[ $DRY -eq 1 ]]; then
      echo "DRY: mkdir -p $log_dir"
      echo "DRY: (cd $worktree_path && $p_verify) > $log_path 2>&1"
    else
      mkdir -p "$log_dir"
      # Bounded, always. The verify command is whatever the caller passed, and
      # a repo whose "check" script starts a watcher or a dev server would
      # otherwise hang this script forever — with no output, since everything is
      # redirected to the log. A timeout is not a judgement call about the
      # command, so it belongs here rather than with the caller; `timeout` is
      # missing on a stock macOS, hence the fallback.
      # Run through python3 rather than timeout(1): timeout is not on a stock
      # macOS, and the two fallbacks that leaves (skip the bound, or kill only
      # the shell and leave its children running) are both worse than using the
      # interpreter this skill already requires. start_new_session puts the
      # command in its own process group so the whole tree dies, not just the
      # `bash -c` wrapper — a test runner that forked workers would otherwise
      # survive the kill and keep holding the port it bound.
      run_verify_bounded "$worktree_path" "$p_verify" "$VERIFY_TIMEOUT" >"$log_path" 2>&1
      verify_rc=$?
      if [[ $verify_rc -eq 0 ]]; then
        emit baseline "PASS"
        PROVISION_BASELINE="PASS"
      elif [[ $verify_rc -eq 124 ]]; then
        # 124 is `timeout`'s own exit code. Called out separately because it
        # means something different from a red baseline: the command never
        # finished, so nothing was proved either way.
        emit baseline "TIMEOUT(${VERIFY_TIMEOUT}s)"
        PROVISION_BASELINE="TIMEOUT"
        warn=1
      else
        emit baseline "FAIL(exit=$verify_rc)"
        PROVISION_BASELINE="FAIL"
        warn=1
      fi
      emit baseline_log "$log_path"
      [[ $verify_rc -ne 0 ]] && tail -15 "$log_path" | sed 's/^/  /'
    fi
  fi

  # --- 7. verdict -----------------------------------------------------------
  if [[ $warn -eq 1 ]]; then
    PROVISION_VERDICT="READY_WITH_WARNINGS"
    echo "verdict: READY_WITH_WARNINGS"
  else
    PROVISION_VERDICT="READY"
    echo "verdict: READY"
  fi
  return 0
}

default_log_path() { # $1=issue -> the same default single-issue mode always used
  printf '%s/../verify/%s-baseline.log\n' "$ROOT" "$1"
}

# --- driver: single-issue (unchanged behavior) or batch ---------------------
if [[ ${#SPECS[@]} -eq 0 ]]; then
  log_path=""
  if [[ -n "$VERIFY" ]]; then
    if [[ -n "$LOG" ]]; then
      log_path="$LOG"
    else
      log_path="$(default_log_path "$ISSUE")"
    fi
  fi
  provision_one "$ISSUE" "$BRANCH" "$BASE" "$ROOT" "$VERIFY" "$log_path"
  exit $?
fi

# --- batch mode -----------------------------------------------------------
total=0
ready=0
blocked_issues=()
batch_blocked=0
batch_warn=0
idx=0

for spec in "${SPECS[@]}"; do
  idx=$((idx + 1))
  spec_issue="${spec%%:*}"
  spec_branch="${spec#*:}"

  total=$((total + 1))

  echo "=== issue $spec_issue ==="
  spec_log=""
  if [[ -n "$VERIFY" ]]; then
    if [[ -n "$LOG_DIR" ]]; then
      spec_log="$LOG_DIR/${spec_issue}-baseline.log"
    else
      spec_log="$(default_log_path "$spec_issue")"
    fi
  fi

  provision_one "$spec_issue" "$spec_branch" "$BASE" "$ROOT" "$VERIFY" "$spec_log"

  case "$PROVISION_VERDICT" in
    BLOCKED)              blocked_issues+=("$spec_issue"); batch_blocked=1 ;;
    READY_WITH_WARNINGS)  ready=$((ready + 1)); batch_warn=1 ;;
    READY)                ready=$((ready + 1)) ;;
  esac

done

summary_verdict="READY"
[[ $batch_warn -eq 1 ]] && summary_verdict="READY_WITH_WARNINGS"
[[ $batch_blocked -eq 1 ]] && summary_verdict="BLOCKED"

echo "batch: $ready/$total ready"
if [[ ${#blocked_issues[@]} -gt 0 ]]; then
  echo "blocked: $(IFS=,; echo "${blocked_issues[*]}")"
fi
echo "verdict: $summary_verdict"
[[ "$summary_verdict" == "BLOCKED" ]] && exit 1
exit 0
