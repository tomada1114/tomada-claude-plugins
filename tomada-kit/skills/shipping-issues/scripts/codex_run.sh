#!/usr/bin/env bash
# codex_run.sh — Run one Codex turn for this skill's implement / review /
# CI-repair steps, through whichever entry point this machine actually has.
#
# MODEL AND EFFORT ARE DELIBERATELY NOT PASSED.
# An unset model and effort make Codex fall back to `~/.codex/config.toml`
# (`model` / `model_reasoning_effort`), so that file is the single place to edit
# when a newer model ships. Pinning them here would also break the strongest
# setting available: the companion entry point rejects effort `max` outright,
# while config.toml accepts it.
# For a one-off override, export CODEX_RUN_MODEL / CODEX_RUN_EFFORT; `max` is
# dropped with a warning on the companion path because it cannot accept it.
#
# Usage:
#   codex_run.sh check
#   codex_run.sh task   --cwd DIR --prompt-file FILE [--write] [--resume]
#   codex_run.sh review --cwd DIR [--base REF] [--focus-file FILE]
#
# Prints (all subcommands):
#   codex_mode: companion | exec | NONE
# check adds:
#   codex_cli: <version>       or `unknown`
#   codex_companion: <path>    or a note that the plugin is absent
#   codex_auth: ok | NOT_AUTHENTICATED | unknown
#   codex_ready: yes | no      the caller falls back on anything but `yes`
# task adds:
#   codex_status: <n>          0 = the turn completed
#   codex_thread: <id>         companion mode only
#   codex_touched: <files>     patch-based edits only; `git status` is the authority
#   ---- codex output ----     followed by the run's final message, verbatim
# review adds:
#   review_verdict: approve | needs-attention | UNPARSED | UNSTRUCTURED
#   review_summary: <one line>
#   FINDINGS:                  one `- [sev] file:l1-l2 (conf) — what — fix` per line
#
# Exit codes:
#   0 = the turn completed (review: verdict approve)
#   1 = Codex ran but the turn failed (review: verdict needs-attention)
#   3 = no Codex entry point on this machine, or (check) Codex is present but
#       not ready/authenticated — the caller falls back
#   4 = usage error

set -uo pipefail

MODEL="${CODEX_RUN_MODEL:-}"
EFFORT="${CODEX_RUN_EFFORT:-}"

emit() { printf '%s: %s\n' "$1" "$2"; }
die() { printf '%s\n' "$1" >&2; exit 4; }

trap 'rm -f "${ERRF:-}" "${LAST:-}"' EXIT INT TERM

# --- entry point discovery -------------------------------------------------
# The plugin installs under a version-numbered directory, so the path cannot be
# hardcoded; take the highest version present.
find_companion() {
  ls -d "$HOME"/.claude/plugins/cache/openai-codex/codex/*/scripts/codex-companion.mjs \
    2>/dev/null | sort -V | tail -1
}

COMPANION=""
MODE="NONE"
if command -v codex >/dev/null 2>&1; then
  MODE="exec"
  if command -v node >/dev/null 2>&1; then
    COMPANION="$(find_companion)"
    [[ -n "$COMPANION" ]] && MODE="companion"
  fi
fi

# --- argument parsing ------------------------------------------------------
CMD="${1:-}"
shift || true
DIR=""
PROMPT_FILE=""
FOCUS_FILE=""
BASE=""
WRITE=0
RESUME=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --cwd) [[ $# -ge 2 ]] || die "--cwd needs a value"; DIR="$2"; shift 2 ;;
    --prompt-file) [[ $# -ge 2 ]] || die "--prompt-file needs a value"; PROMPT_FILE="$2"; shift 2 ;;
    --focus-file) [[ $# -ge 2 ]] || die "--focus-file needs a value"; FOCUS_FILE="$2"; shift 2 ;;
    --base) [[ $# -ge 2 ]] || die "--base needs a value"; BASE="$2"; shift 2 ;;
    --write) WRITE=1; shift ;;
    --resume) RESUME=1; shift ;;
    *) die "Unknown argument: $1" ;;
  esac
done

if [[ "$CMD" == "--help" || "$CMD" == "-h" ]]; then
  # Print the header comment block as help: every comment line after the
  # shebang, up to the first line that is not a comment. Self-adjusting, so
  # editing the header cannot silently truncate --help.
  awk 'NR==1 {next} /^#/ {sub(/^# ?/, ""); print; next} {exit}' "$0"
  exit 0
fi

emit codex_mode "$MODE"
[[ "$MODE" == "NONE" ]] && {
  emit codex_detail "codex CLI not on PATH (install: npm install -g @openai/codex)"
  exit 3
}

# `max` is the whole reason model/effort stay unset; refuse to smuggle it in.
COMPANION_EFFORT="$EFFORT"
if [[ "$MODE" == "companion" && "$EFFORT" == "max" ]]; then
  echo "codex_run.sh: dropping CODEX_RUN_EFFORT=max (companion rejects it); config.toml still applies" >&2
  COMPANION_EFFORT=""
fi

resolve_dir() {
  [[ -n "$DIR" ]] || die "$CMD needs --cwd DIR"
  [[ -d "$DIR" ]] || die "No such directory: $DIR"
  DIR="$(cd "$DIR" && pwd)"
}

# --- check -----------------------------------------------------------------
if [[ "$CMD" == "check" ]]; then
  emit codex_cli "$(codex --version 2>/dev/null || echo unknown)"
  ready="no"
  if [[ "$MODE" == "companion" ]]; then
    emit codex_companion "$COMPANION"
    ERRF="$(mktemp)"
    setup_json="$(node "$COMPANION" setup --json 2>"$ERRF")"
    node_status=$?
    [[ $node_status -ne 0 ]] && sed -n '1,20p' "$ERRF" >&2
    rm -f "$ERRF"
    check_out="$(printf '%s' "$setup_json" | python3 -c '
import json, sys
raw = sys.stdin.read()
try:
    d = json.loads(raw)
except Exception:
    print("codex_auth: unknown")
    print("codex_ready: no")
    sys.exit(0)
print("codex_auth: " + ("ok" if d.get("auth", {}).get("loggedIn") else "NOT_AUTHENTICATED"))
print("codex_ready: " + ("yes" if d.get("ready") else "no"))
')"
    printf '%s\n' "$check_out"
    ready="$(printf '%s\n' "$check_out" | sed -n 's/^codex_ready: //p')"
  else
    emit codex_companion 'none (plugin not installed; using bare codex exec)'
    emit codex_auth "unknown"
  fi
  [[ "$ready" == "yes" ]] && exit 0
  exit 3
fi

# --- task ------------------------------------------------------------------
if [[ "$CMD" == "task" ]]; then
  resolve_dir
  [[ -n "$PROMPT_FILE" || "$RESUME" -eq 1 ]] || die "task needs --prompt-file FILE (or --resume)"
  if [[ -n "$PROMPT_FILE" ]]; then
    [[ -f "$PROMPT_FILE" ]] || die "No such prompt file: $PROMPT_FILE"
    PROMPT_FILE="$(cd "$(dirname "$PROMPT_FILE")" && pwd)/$(basename "$PROMPT_FILE")"
  fi
  SANDBOX="read-only"; [[ "$WRITE" -eq 1 ]] && SANDBOX="workspace-write"

  if [[ "$MODE" == "companion" ]]; then
    set -- task --cwd "$DIR" --json
    [[ "$WRITE" -eq 1 ]] && set -- "$@" --write
    [[ "$RESUME" -eq 1 ]] && set -- "$@" --resume-last
    [[ -n "$PROMPT_FILE" ]] && set -- "$@" --prompt-file "$PROMPT_FILE"
    [[ -n "$MODEL" ]] && set -- "$@" --model "$MODEL"
    [[ -n "$COMPANION_EFFORT" ]] && set -- "$@" --effort "$COMPANION_EFFORT"
    ERRF="$(mktemp)"
    out="$(node "$COMPANION" "$@" 2>"$ERRF")"
    printf '%s' "$out" | python3 -c '
import json, sys
raw = sys.stdin.read()
try:
    d = json.loads(raw)
except Exception:
    print("codex_status: 1"); print("---- codex output ----"); print(raw); sys.exit(1)
status = d.get("status", 1)
print("codex_status: %s" % status)
if d.get("threadId"):
    print("codex_thread: %s" % d["threadId"])
touched = d.get("touchedFiles") or []
if touched:
    print("codex_touched: %s" % ", ".join(touched))
print("---- codex output ----")
print((d.get("rawOutput") or "").rstrip())
sys.exit(0 if status == 0 else 1)
'
    rc=$?
    [[ $rc -ne 0 ]] && sed -n '1,20p' "$ERRF" >&2
    rm -f "$ERRF"
    exit $rc
  fi

  # exec fallback: no job tracking, no resume-by-cwd — one turn, last message out.
  [[ "$RESUME" -eq 1 ]] && die "--resume needs the companion entry point (plugin not installed)"
  LAST="$(mktemp)"
  set -- exec -C "$DIR" -s "$SANDBOX" -o "$LAST" --skip-git-repo-check
  [[ -n "$MODEL" ]] && set -- "$@" -m "$MODEL"
  [[ -n "$EFFORT" ]] && set -- "$@" -c "model_reasoning_effort=$EFFORT"
  ERRF="$(mktemp)"
  codex "$@" - < "$PROMPT_FILE" >/dev/null 2>"$ERRF"
  status=$?
  [[ $status -ne 0 ]] && sed -n '1,20p' "$ERRF" >&2
  rm -f "$ERRF"
  emit codex_status "$status"
  echo "---- codex output ----"
  cat "$LAST"
  rm -f "$LAST"
  exit $(( status == 0 ? 0 : 1 ))
fi

# --- review ----------------------------------------------------------------
if [[ "$CMD" == "review" ]]; then
  resolve_dir
  FOCUS=""
  if [[ -n "$FOCUS_FILE" ]]; then
    [[ -f "$FOCUS_FILE" ]] || die "No such focus file: $FOCUS_FILE"
    FOCUS="$(cat "$FOCUS_FILE")"
  fi

  if [[ "$MODE" == "companion" ]]; then
    set -- adversarial-review --cwd "$DIR" --json
    [[ -n "$BASE" ]] && set -- "$@" --base "$BASE" --scope branch
    [[ -n "$MODEL" ]] && set -- "$@" --model "$MODEL"
    ERRF="$(mktemp)"
    out="$(node "$COMPANION" "$@" -- "$FOCUS" 2>"$ERRF")"
    printf '%s' "$out" | python3 -c '
import json, sys
raw = sys.stdin.read()
try:
    d = json.loads(raw)
except Exception:
    print("review_verdict: UNPARSED"); print(raw[:2000]); sys.exit(1)
r = d.get("result") or {}
if not r:
    print("review_verdict: UNPARSED")
    print("review_detail: %s" % (d.get("parseError") or "no structured result"))
    print((d.get("rawOutput") or "")[:2000])
    sys.exit(1)
verdict = r.get("verdict", "UNPARSED")
print("review_verdict: %s" % verdict)
print("review_summary: %s" % " ".join((r.get("summary") or "").split()))
print("FINDINGS:")
for f in r.get("findings") or []:
    print("  - [%s] %s:%s-%s (%.2f) — %s — %s" % (
        f.get("severity", "?"), f.get("file", "?"),
        f.get("line_start", "?"), f.get("line_end", "?"),
        float(f.get("confidence") or 0),
        " ".join((f.get("title") or "").split()),
        " ".join((f.get("recommendation") or "").split())))
else_steps = r.get("next_steps") or []
if else_steps:
    print("NEXT-STEPS:")
    for s in else_steps:
        print("  - %s" % " ".join(s.split()))
sys.exit(0 if verdict == "approve" else 1)
'
    rc=$?
    [[ $rc -ne 0 ]] && sed -n '1,20p' "$ERRF" >&2
    rm -f "$ERRF"
    exit $rc
  fi

  # exec fallback: no built-in adversarial reviewer — run the focus prompt
  # read-only and return its text as-is for the caller to read.
  [[ -n "$FOCUS" ]] || die "review needs --focus-file FILE without the companion entry point"
  LAST="$(mktemp)"
  set -- exec -C "$DIR" -s read-only -o "$LAST" --skip-git-repo-check
  [[ -n "$MODEL" ]] && set -- "$@" -m "$MODEL"
  [[ -n "$EFFORT" ]] && set -- "$@" -c "model_reasoning_effort=$EFFORT"
  ERRF="$(mktemp)"
  codex "$@" - < "$FOCUS_FILE" >/dev/null 2>"$ERRF"
  status=$?
  [[ $status -ne 0 ]] && sed -n '1,20p' "$ERRF" >&2
  rm -f "$ERRF"
  emit review_verdict "UNSTRUCTURED"
  echo "---- codex output ----"
  cat "$LAST"
  rm -f "$LAST"
  # unstructured, unjudged fallback — never read this as an approval
  exit 1
fi

die "Usage: codex_run.sh {check|task|review} [...]"
