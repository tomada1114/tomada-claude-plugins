#!/usr/bin/env bash
# preflight.sh — Verify the local repo is in a state where issues can be shipped,
# and report the repo's profile so the calling model doesn't have to re-derive it
# with ad-hoc probes on every run.
#
# Usage: preflight.sh [--with-github] [--profile-cache <path>]
#                      [--set-worktree-viable <yes|no>]
#
# Prints a compact key: value report and exits non-zero if a hard blocker
# is present. Soft warnings are reported but do not fail.
#
# By default this checks only the local git state plus cheap, local repo-profile
# facts (package manager, verify command, hooks). It makes no GitHub or network
# calls at all — that is a deliberate property of this script, so --with-github
# is how a caller opts into the (slower, network-dependent) GitHub checks. Later
# steps that actually need GitHub still surface a problem on their own if the
# caller skips --with-github.
#
# --profile-cache lets the caller avoid recomputing verify_command/hooks/etc on
# every invocation across a single shipping-issues run: those facts are constant
# for a repo as long as its lockfile and build-config files (package.json,
# Makefile, justfile, pyproject.toml) haven't changed, so a matching lockfile
# hash + config hash is treated as a cache hit. worktree_viable is never
# detected here (git-worktree viability requires actually running a baseline
# verify command, which is worktree_setup.sh's job, not preflight's) — it is
# only ever set via --set-worktree-viable, once the caller has paid for that
# probe, so future preflight calls can read it back for free.
#
# Exit codes:
#   0 = ready
#   1 = hard blocker (not a repo, no origin)
#   2 = usage error

set -uo pipefail

fail=0
warn=0

emit() { printf '%s: %s\n' "$1" "$2"; }

# --- hashing helper ----------------------------------------------------------
# Prefer shasum (macOS default), fall back to sha256sum (Linux default). If
# neither exists, HASHER stays empty and every hash_* call reports "" — callers
# turn that into the documented "none" value rather than failing the script.
HASHER=""
if command -v shasum >/dev/null 2>&1; then
  HASHER="shasum -a 256"
elif command -v sha256sum >/dev/null 2>&1; then
  HASHER="sha256sum"
fi

hash_file12() {
  [[ -n "$HASHER" && -f "$1" ]] || { printf '%s' ""; return; }
  $HASHER "$1" 2>/dev/null | awk '{print substr($1,1,12)}'
}

hash_str12() {
  [[ -n "$HASHER" ]] || { printf '%s' ""; return; }
  printf '%s' "$1" | $HASHER | awk '{print substr($1,1,12)}'
}

# --- args --------------------------------------------------------------------
WITH_GITHUB=0
PROFILE_CACHE=""
SET_WORKTREE_VIABLE=""

usage() {
  echo "Usage: preflight.sh [--with-github] [--profile-cache <path>] [--set-worktree-viable <yes|no>]" >&2
}

# print_help — the script's own usage, derived straight from this header
# comment so the text lives in exactly one place (kept separate from usage()
# above, which is the short one-liner already used on stderr for arg errors).
print_help() {
  awk 'NR==1{next} /^#/{sub(/^# ?/,""); print; next} {exit}' "${BASH_SOURCE[0]}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) print_help; exit 0 ;;
    --with-github) WITH_GITHUB=1; shift ;;
    --profile-cache)
      [[ $# -ge 2 ]] || { echo "--profile-cache needs a value" >&2; exit 2; }
      PROFILE_CACHE="$2"; shift 2 ;;
    --set-worktree-viable)
      [[ $# -ge 2 ]] || { echo "--set-worktree-viable needs a value" >&2; exit 2; }
      SET_WORKTREE_VIABLE="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 2 ;;
  esac
done

# --set-worktree-viable is a standalone cache-write operation: it doesn't need
# a git repo at all, so it's handled and exited before any git check runs.
if [[ -n "$SET_WORKTREE_VIABLE" ]]; then
  if [[ -z "$PROFILE_CACHE" ]]; then
    echo "--set-worktree-viable requires --profile-cache" >&2
    usage
    exit 2
  fi
  if [[ "$SET_WORKTREE_VIABLE" != "yes" && "$SET_WORKTREE_VIABLE" != "no" ]]; then
    echo "--set-worktree-viable requires yes or no" >&2
    usage
    exit 2
  fi
  mkdir -p "$(dirname "$PROFILE_CACHE")"
  python3 - "$PROFILE_CACHE" "$SET_WORKTREE_VIABLE" <<'PY'
import json
import sys

path, value = sys.argv[1], sys.argv[2]
try:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        data = {}
except Exception:
    data = {}
data["worktree_viable"] = value
with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f)
PY
  emit worktree_viable "$SET_WORKTREE_VIABLE"
  echo "verdict: READY"
  exit 0
fi

# --- git repo ------------------------------------------------------------
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  emit git_repo "NOT_A_REPO"
  echo "verdict: BLOCKED"
  exit 1
fi
emit git_repo "ok"
repo_root="$(git rev-parse --show-toplevel)"
emit repo_root "$repo_root"
git_common_dir="$(git rev-parse --path-format=absolute --git-common-dir)"
emit git_common_dir "$git_common_dir"

# --- worktree state ----------------------------------------------------------
# Neither of these is a blocker or a warning on its own — they only inform the
# caller whether parallel-worktree mode is already in play.
git_dir=$(git rev-parse --path-format=absolute --git-dir)
if [[ "$git_dir" != "$git_common_dir" ]]; then
  emit in_worktree "yes"
else
  emit in_worktree "no"
fi

worktree_list="$(git worktree list 2>/dev/null)"
worktree_count=$(printf '%s\n' "$worktree_list" | sed -n '2,$p' | grep -c . || true)
if [[ "$worktree_count" -gt 0 ]]; then
  emit existing_worktrees "$worktree_count"
  printf '%s\n' "$worktree_list" | sed -n '2,$p' | sed 's/^/  /'
fi

if ! origin_url="$(git remote get-url origin 2>/dev/null)"; then
  emit origin "MISSING"
  fail=1
  origin_url=""
else
  emit origin "$origin_url"
fi

current_branch="$(git rev-parse --abbrev-ref HEAD)"
emit current_branch "$current_branch"

dirty="$(git status --porcelain 2>/dev/null | head -20)"
if [[ -n "$dirty" ]]; then
  emit working_tree "DIRTY"
  emit dirty_files "$(git status --porcelain | wc -l | tr -d ' ')"
  printf '%s\n' "$dirty" | sed 's/^/  /'
  warn=1
else
  emit working_tree "clean"
fi

# --- repo profile: always emitted, cheap, local ------------------------------

# repo_slug — parsed from the origin URL. Handles the two common forms:
#   git@github.com:owner/repo.git
#   https://github.com/owner/repo(.git)
# and the less common ssh://git@host/owner/repo.git. Anything that doesn't
# reduce to exactly "owner/repo" is reported as UNKNOWN rather than guessed at.
repo_slug="UNKNOWN"
if [[ -n "$origin_url" ]]; then
  slug="${origin_url%.git}"
  case "$slug" in
    git@*:*) slug="${slug#*:}" ;;
    ssh://*) slug="${slug#ssh://}"; slug="${slug#*@}"; slug="${slug#*/}" ;;
    https://*|http://*) slug="${slug#*://}"; slug="${slug#*/}" ;;
  esac
  if [[ "$slug" =~ ^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$ ]]; then
    repo_slug="$slug"
  fi
fi
emit repo_slug "$repo_slug"

# default_branch — origin/HEAD is only set by `git clone`, not by `git remote
# add` + fetch, so plenty of real repos lack it (see cleanup_run.sh for the
# same gap). Fall back to origin/main, then origin/master, then whatever
# branch we're actually on — this must never fail preflight.
default_branch="$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|^origin/||')"
if [[ -z "$default_branch" ]]; then
  if git show-ref --verify --quiet refs/remotes/origin/main; then
    default_branch="main"
  elif git show-ref --verify --quiet refs/remotes/origin/master; then
    default_branch="master"
  else
    default_branch="$current_branch"
  fi
fi
emit default_branch "$default_branch"

# runstate — where a caller may persist per-repo state (e.g. the profile
# cache) across runs. Only the path is reported; the directory is deliberately
# NOT created here, since not every caller needs it.
if [[ "$repo_slug" == "UNKNOWN" ]]; then
  runstate_leaf="UNKNOWN"
else
  runstate_leaf="${repo_slug%/*}__${repo_slug#*/}"
fi
state_root="${AGENT_SKILL_STATE_DIR:-$HOME/.local/state/agent-skills}"
runstate="$state_root/shipping-issues/$runstate_leaf"
emit runstate "$runstate"

# pkg_manager / lockfile — this precedence is duplicated in worktree_setup.sh's
# "install dependencies" section. It is intentionally the SAME order in both
# places (see the comment there) — this file can't factor it into a shared
# helper without touching a third file outside this track's ownership, so if
# you change one, change the other.
pkg_manager="none"
lockfile="none"
if   [[ -f "$repo_root/pnpm-lock.yaml" ]];    then pkg_manager=pnpm;   lockfile="pnpm-lock.yaml"
elif [[ -f "$repo_root/yarn.lock" ]];         then pkg_manager=yarn;   lockfile="yarn.lock"
elif [[ -f "$repo_root/bun.lockb" ]];         then pkg_manager=bun;    lockfile="bun.lockb"
elif [[ -f "$repo_root/bun.lock" ]];          then pkg_manager=bun;    lockfile="bun.lock"
elif [[ -f "$repo_root/package-lock.json" ]]; then pkg_manager=npm;    lockfile="package-lock.json"
elif [[ -f "$repo_root/uv.lock" ]];           then pkg_manager=uv;     lockfile="uv.lock"
elif [[ -f "$repo_root/poetry.lock" ]];       then pkg_manager=poetry; lockfile="poetry.lock"
elif [[ -f "$repo_root/Pipfile.lock" ]];      then pkg_manager=pipenv; lockfile="Pipfile.lock"
elif [[ -f "$repo_root/Gemfile.lock" ]];      then pkg_manager=bundle; lockfile="Gemfile.lock"
elif [[ -f "$repo_root/go.sum" ]];            then pkg_manager=go;     lockfile="go.sum"
elif [[ -f "$repo_root/Cargo.lock" ]];        then pkg_manager=cargo;  lockfile="Cargo.lock"
elif [[ -f "$repo_root/requirements.txt" ]];  then pkg_manager=pip;    lockfile="requirements.txt"
fi
emit pkg_manager "$pkg_manager"
emit lockfile "$lockfile"

lockfile_hash="none"
if [[ "$lockfile" != "none" ]]; then
  h="$(hash_file12 "$repo_root/$lockfile")"
  [[ -n "$h" ]] && lockfile_hash="$h"
fi
emit lockfile_hash "$lockfile_hash"

# hooks — checked in this order: an explicit lefthook config always wins (even
# over a native hook that also happens to be installed), then husky, then
# pre-commit, then "some other native hook is installed", then none.
hooks="none"
if [[ -f "$repo_root/lefthook.yml" || -f "$repo_root/lefthook.yaml" || -f "$repo_root/.lefthook.yml" ]]; then
  hooks="lefthook"
elif [[ -d "$git_common_dir/hooks" ]] && grep -ril "lefthook" "$git_common_dir/hooks" 2>/dev/null | grep -v '\.sample$' | grep -q .; then
  hooks="lefthook"
elif [[ -d "$repo_root/.husky" ]]; then
  hooks="husky"
elif [[ -f "$repo_root/.pre-commit-config.yaml" ]]; then
  hooks="pre-commit"
elif [[ -d "$git_common_dir/hooks" ]] && find "$git_common_dir/hooks" -maxdepth 1 -type f ! -name '*.sample' 2>/dev/null | grep -q .; then
  hooks="native"
fi
# Not emitted here — emitted once below, after the profile-cache block has had
# a chance to override it on a cache hit.

# verify_command — first match wins, in this order: package.json scripts,
# Makefile target, justfile recipe, then a per-language default. Independent
# of pkg_manager/lockfile detection above: a repo can have a Makefile target
# that wraps a completely different toolchain than its lockfile suggests, so
# this chain is checked fresh rather than branching on pkg_manager.
VERIFY_COMMAND=""
VERIFY_SOURCE=""

if [[ -f "$repo_root/package.json" ]]; then
  # Parsed with python3 (a documented requirement of this skill) rather than
  # grep/sed, since scripts.* values are arbitrary JSON strings.
  found_script="$(python3 - "$repo_root/package.json" <<'PY'
import json
import sys

try:
    with open(sys.argv[1], encoding="utf-8") as f:
        data = json.load(f)
except Exception:
    print("")
    sys.exit(0)

scripts = data.get("scripts") if isinstance(data, dict) else None
if isinstance(scripts, dict):
    # Namespaced forms are in this list because a repo that keeps `test` as
    # "just the unit tests" and puts the real pre-PR gate behind `check:quick`
    # is common, and picking `test` there gives a baseline that passes while
    # lint and typecheck are broken — which is exactly the CI round-trip the
    # baseline exists to avoid. `check:quick` outranks `check:all` on purpose:
    # a baseline wants the cheapest command that still covers every kind of
    # failure, and the PR's own CI run covers the expensive rest.
    for key in ("verify", "check", "check:quick", "check:all", "verify:all",
                "ci", "test"):
        if scripts.get(key):
            print(key)
            sys.exit(0)
print("")
PY
)"
  if [[ -n "$found_script" ]]; then
    case "$pkg_manager" in
      pnpm) run_prefix="pnpm run" ;;
      yarn) run_prefix="yarn" ;;
      bun)  run_prefix="bun run" ;;
      *)    run_prefix="npm run" ;;
    esac
    VERIFY_COMMAND="$run_prefix $found_script"
    VERIFY_SOURCE="package.json scripts.$found_script"
  fi
fi

if [[ -z "$VERIFY_COMMAND" ]]; then
  for mkfile in "$repo_root/Makefile" "$repo_root/makefile" "$repo_root/GNUmakefile"; do
    [[ -f "$mkfile" ]] || continue
    for target in verify check test; do
      if grep -qE "^${target}:" "$mkfile"; then
        VERIFY_COMMAND="make $target"
        VERIFY_SOURCE="Makefile:$target"
        break 2
      fi
    done
  done
fi

if [[ -z "$VERIFY_COMMAND" ]]; then
  for jfile in "$repo_root/justfile" "$repo_root/.justfile"; do
    [[ -f "$jfile" ]] || continue
    for recipe in verify check test; do
      if grep -qE "^${recipe}([[:space:]].*)?:" "$jfile"; then
        VERIFY_COMMAND="just $recipe"
        VERIFY_SOURCE="justfile:$recipe"
        break 2
      fi
    done
  done
fi

if [[ -z "$VERIFY_COMMAND" ]]; then
  if [[ -f "$repo_root/uv.lock" ]]; then
    VERIFY_COMMAND="uv run pytest"; VERIFY_SOURCE="uv.lock"
  elif [[ -f "$repo_root/poetry.lock" ]]; then
    VERIFY_COMMAND="poetry run pytest"; VERIFY_SOURCE="poetry.lock"
  elif [[ -f "$repo_root/Pipfile.lock" ]]; then
    VERIFY_COMMAND="pipenv run pytest"; VERIFY_SOURCE="Pipfile.lock"
  fi
fi

if [[ -z "$VERIFY_COMMAND" ]]; then
  if [[ -f "$repo_root/Cargo.lock" ]]; then
    VERIFY_COMMAND="cargo test"; VERIFY_SOURCE="Cargo.lock"
  elif [[ -f "$repo_root/go.sum" ]]; then
    VERIFY_COMMAND="go test ./..."; VERIFY_SOURCE="go.sum"
  elif [[ -f "$repo_root/Gemfile.lock" && -f "$repo_root/Rakefile" ]]; then
    VERIFY_COMMAND="bundle exec rake"; VERIFY_SOURCE="Gemfile.lock+Rakefile"
  fi
fi

VERIFY_COMMAND="${VERIFY_COMMAND:-NONE}"
VERIFY_SOURCE="${VERIFY_SOURCE:-none}"

# --- profile cache (only touched with --profile-cache) -----------------------
# `unknown` only until an existing cache is read. worktree_viable deliberately
# SURVIVES a cache miss: it is a property of the repository and its tooling —
# whether a fresh worktree can run the gate at all — not of the lockfile or the
# package.json that invalidated the rest of the profile. Resetting it on every
# lockfile bump would throw away the one fact that cost a whole worktree install
# to learn, and the caller reads a fresh baseline before trusting a stale `yes`.
worktree_viable="unknown"
if [[ -n "$PROFILE_CACHE" ]]; then
  # meta_hash covers the small set of build-config files that can change
  # verify_command/hooks without touching the lockfile (e.g. adding a
  # `scripts.verify` to package.json doesn't bump pnpm-lock.yaml).
  meta_concat=""
  for f in package.json Makefile makefile GNUmakefile justfile .justfile pyproject.toml; do
    if [[ -f "$repo_root/$f" ]]; then
      meta_concat+="$f:$(hash_file12 "$repo_root/$f");"
    fi
  done
  meta_hash="$(hash_str12 "$meta_concat")"
  [[ -z "$meta_hash" ]] && meta_hash="none"
  # The repo's own files are only half of what the answer depends on: the
  # other half is this script's detection rules. Changing the verify_command
  # search order without bumping this leaves every existing cache serving the
  # answer the old rules gave — a stale verify_command is a weaker baseline
  # gate that nothing else in the run would notice. Bump on ANY change to how
  # verify_command, verify_source, hooks or pkg_manager are derived.
  profile_logic_version="2"

  cache_hit=0
  if [[ -f "$PROFILE_CACHE" ]]; then
    cache_read="$(python3 - "$PROFILE_CACHE" "$lockfile_hash" "$meta_hash" "$profile_logic_version" <<'PY'
import json
import sys

path, lockfile_hash, meta_hash, logic_version = sys.argv[1:5]
try:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
except Exception:
    print("MISS")
    sys.exit(0)

if not isinstance(data, dict):
    print("MISS")
    sys.exit(0)

if (data.get("lockfile_hash") != lockfile_hash
        or data.get("meta_hash") != meta_hash
        or str(data.get("logic_version")) != logic_version):
    # A miss invalidates what was *derived* from the repo's config files, not
    # what was *measured* by running a gate in a real worktree. Hand the stale
    # worktree_viable back so the caller can carry it forward; everything else
    # gets recomputed.
    print("MISS")
    print(f"worktree_viable\t{data.get('worktree_viable', '')}")
    sys.exit(0)

print("HIT")
for key in ("verify_command", "verify_source", "hooks", "pkg_manager", "worktree_viable"):
    print(f"{key}\t{data.get(key, '')}")
PY
)"
    if [[ "$(printf '%s\n' "$cache_read" | head -1)" == "HIT" ]]; then
      cache_hit=1
    fi
    if [[ -n "$cache_read" ]]; then
      while IFS=$'\t' read -r k v; do
        case "$k" in
          verify_command)  VERIFY_COMMAND="$v" ;;
          verify_source)   VERIFY_SOURCE="$v" ;;
          hooks)           hooks="$v" ;;
          pkg_manager)     pkg_manager="$v" ;;
          worktree_viable) [[ -n "$v" ]] && worktree_viable="$v" ;;
        esac
      done < <(printf '%s\n' "$cache_read" | tail -n +2)
    fi
  fi

  if [[ $cache_hit -eq 1 ]]; then
    emit profile_cache "HIT"
  else
    mkdir -p "$(dirname "$PROFILE_CACHE")"
    python3 - "$PROFILE_CACHE" "$lockfile_hash" "$meta_hash" "$VERIFY_COMMAND" "$VERIFY_SOURCE" "$hooks" "$pkg_manager" "$worktree_viable" "$profile_logic_version" <<'PY'
import json
import sys

(path, lockfile_hash, meta_hash, verify_command, verify_source,
 hooks, pkg_manager, worktree_viable, logic_version) = sys.argv[1:10]

data = {
    "lockfile_hash": lockfile_hash,
    "meta_hash": meta_hash,
    "verify_command": verify_command,
    "verify_source": verify_source,
    "hooks": hooks,
    "pkg_manager": pkg_manager,
    "worktree_viable": worktree_viable,
    "logic_version": logic_version,
}
with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f)
PY
    emit profile_cache "WRITTEN"
  fi
fi

emit verify_command "$VERIFY_COMMAND"
emit verify_source "$VERIFY_SOURCE"
emit hooks "$hooks"
[[ -n "$PROFILE_CACHE" ]] && emit worktree_viable "$worktree_viable"

# --- github (only with --with-github) -----------------------------------
if [[ $WITH_GITHUB -eq 1 ]]; then
  if ! command -v gh >/dev/null 2>&1; then
    emit gh_auth "GH_MISSING"
    emit gh_write "unknown"
  else
    if gh auth status >/dev/null 2>&1; then
      emit gh_auth "ok"
    else
      emit gh_auth "NOT_LOGGED_IN"
      warn=1
    fi
    perm="$(gh repo view --json viewerPermission -q .viewerPermission 2>/dev/null)"
    case "$perm" in
      ADMIN|MAINTAIN|WRITE) emit gh_write "yes" ;;
      READ|TRIAGE)          emit gh_write "no"; warn=1 ;;
      *)                    emit gh_write "unknown" ;;
    esac
  fi
fi

if [[ $fail -ne 0 ]]; then
  echo "verdict: BLOCKED"
  exit 1
fi
[[ $warn -ne 0 ]] && echo "verdict: READY_WITH_WARNINGS" || echo "verdict: READY"
exit 0
