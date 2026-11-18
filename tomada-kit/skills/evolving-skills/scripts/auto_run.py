#!/usr/bin/env python3
"""auto_run.py - Session-end trigger and background worker for evolving-skills.

A SessionEnd command hook runs `auto_run.py hook`. It decides cheaply, with no
model call, whether the session is worth a look; if so it starts a detached
`auto_run.py run` worker that runs headless `claude -p` passes (harvest, then
improve when the evidence ledger has something that recurred). Every launch is
capped per day and by budget, and one file switches it all off.

Usage:
    auto_run.py hook [--claude-bin BIN]         (reads hook JSON on stdin)
    auto_run.py run --cwd DIR [--digest PATH] [--claude-bin BIN]
    auto_run.py status
    auto_run.py disable
    auto_run.py enable
    auto_run.py settings-snippet

Subcommands:
    hook              Decide and maybe launch the worker. Prints nothing,
                      always exits 0, logs one line to <state>/auto/hook.log.
    run               The detached worker: takes the lock, runs harvest (when
                      --digest is given) and improve, each under its daily cap.
    status            Print JSON: enabled, counts and caps, lock, hook.log tail,
                      config in effect.
    disable           Create <state>/auto/disabled.
    enable            Rename <state>/auto/disabled to disabled.off-<ts>.
    settings-snippet  Print the `hooks` JSON to merge into settings.json.
                      This script never edits settings.

State lives under $AGENT_SKILL_STATE_DIR (default ~/.local/state/agent-skills)
/evolving-skills/auto/. Config: assets/auto-config.json (missing keys fall back
to built-in defaults). `project_roots` (default false) lets `hook` also count
skills under <cwd>/.claude/skills; improve.max_groups and
improve.eval_max_cost_usd bound the work of one improve launch.
Env EVOLVING_SKILLS_AUTO=0 disables; the headless runs get
EVOLVING_SKILLS_CHILD=1 so they never start more runs.

Exit codes:
    hook  always 0
    other 0 ok, 3 bad invocation
"""

import argparse
import copy
import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# The hook imports session_digest on every session end; keep the skill dir free
# of __pycache__.
sys.dont_write_bytecode = True

SCRIPT_PATH = Path(__file__).resolve()
SCRIPTS_DIR = SCRIPT_PATH.parent
SKILL_DIR = SCRIPT_PATH.parents[1]
SKILLS_ROOT = SCRIPT_PATH.parents[2]
CONFIG_PATH = SKILL_DIR / "assets" / "auto-config.json"

DEFAULT_CONFIG = {
    "min_followups": 2,
    "lock_stale_minutes": 120,
    "project_roots": False,
    "harvest": {"agent": "scout", "max_budget_usd": 0.5, "daily_cap": 6,
                "tools": ["Read", "Glob", "Grep", "Skill"]},
    "improve": {"agent": "executor", "max_budget_usd": 5, "daily_cap": 2,
                "tools": ["Read", "Glob", "Grep", "Skill", "Edit", "Write"],
                "max_groups": 2, "eval_max_cost_usd": 1},
}

HARVEST_TIMEOUT = 20 * 60
IMPROVE_TIMEOUT = 60 * 60
SIGNALS_TIMEOUT = 8
GIT_TIMEOUT = 10
EXIT_BAD_INVOCATION = 3


class UsageError(Exception):
    pass


# --------------------------------------------------------------------------
# Paths, time, config
# --------------------------------------------------------------------------

def state_dir():
    base = os.environ.get("AGENT_SKILL_STATE_DIR", "~/.local/state/agent-skills")
    return Path(base).expanduser() / "evolving-skills"


def auto_dir():
    return state_dir() / "auto"


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


def iso(ts):
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


def stamp(ts):
    return ts.strftime("%Y%m%dT%H%M%SZ")


def load_config():
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return cfg
    if not isinstance(data, dict):
        return cfg
    for key, value in data.items():
        if isinstance(cfg.get(key), dict) and isinstance(value, dict):
            cfg[key].update(value)
        elif key in cfg:
            cfg[key] = value
    return cfg


def child_env():
    env = dict(os.environ)
    env["EVOLVING_SKILLS_CHILD"] = "1"
    return env


# --------------------------------------------------------------------------
# Process launches (patched in tests)
# --------------------------------------------------------------------------

def spawn_detached(argv, cwd, env, log_path):
    """Start argv in its own session, stdin closed, output appended to log_path."""
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "ab") as log:
        proc = subprocess.Popen(
            argv, cwd=str(cwd), env=env, stdin=subprocess.DEVNULL,
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
            close_fds=True,
        )
    return proc.pid


def run_cmd(argv, cwd=None, timeout=None, *, env=None, log_path=None):
    """Run argv and wait. Returns (returncode, stdout_text).

    With log_path, stdout and stderr are appended to that file and stdout_text
    is empty. A timeout or a missing binary returns a non-zero code.
    """
    try:
        if log_path is not None:
            log_path = Path(log_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "ab") as log:
                proc = subprocess.run(
                    argv, cwd=None if cwd is None else str(cwd), env=env,
                    stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                    timeout=timeout,
                )
            return proc.returncode, ""
        proc = subprocess.run(
            argv, cwd=None if cwd is None else str(cwd), env=env,
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout,
        )
        return proc.returncode, proc.stdout or ""
    except subprocess.TimeoutExpired:
        return 124, ""
    except OSError:
        return 127, ""


# --------------------------------------------------------------------------
# Shared helpers
# --------------------------------------------------------------------------

def disabled_reasons():
    reasons = []
    if (auto_dir() / "disabled").exists():
        reasons.append("file:%s" % (auto_dir() / "disabled"))
    if os.environ.get("EVOLVING_SKILLS_AUTO") == "0":
        reasons.append("env:EVOLVING_SKILLS_AUTO=0")
    return reasons


def promotable():
    """True when signals.py reports a non-empty list of promotable groups."""
    code, out = run_cmd(
        [sys.executable, str(SCRIPTS_DIR / "signals.py"), "promotable", "--json"],
        cwd=str(SKILLS_ROOT), timeout=SIGNALS_TIMEOUT,
    )
    if code != 0:
        return False
    try:
        data = json.loads(out)
    except ValueError:
        return False
    return isinstance(data, list) and len(data) > 0


def counts_path(now=None):
    return auto_dir() / ("counts-%s.json" % (now or utcnow()).strftime("%Y-%m-%d"))


def read_counts(now=None):
    counts = {"harvest": 0, "improve": 0}
    try:
        data = json.loads(counts_path(now).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return counts
    if isinstance(data, dict):
        for key in counts:
            if isinstance(data.get(key), int):
                counts[key] = data[key]
    return counts


def bump_count(kind):
    counts = read_counts()
    counts[kind] += 1
    path = counts_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(counts) + "\n", encoding="utf-8")
    return counts


def lock_path():
    return auto_dir() / "lock"


def lock_info(cfg):
    """Return (exists, stale, data) for the current lock."""
    path = lock_path()
    if not path.exists():
        return False, False, None
    data = None
    started = None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        started = datetime.datetime.strptime(data["time"], "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=datetime.timezone.utc)
    except (OSError, ValueError, KeyError, TypeError):
        try:
            started = datetime.datetime.fromtimestamp(path.stat().st_mtime, datetime.timezone.utc)
        except OSError:
            return False, False, None
    age_minutes = (utcnow() - started).total_seconds() / 60.0
    return True, age_minutes > float(cfg["lock_stale_minutes"]), data


def acquire_lock(cfg):
    """Create the lock exclusively, replacing a stale one. True on success."""
    path = lock_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(2):
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            exists, stale, _data = lock_info(cfg)
            if exists and not stale:
                return False
            if exists:
                try:
                    os.replace(str(path), str(path.with_name("lock.stale-%s" % stamp(utcnow()))))
                except OSError:
                    return False
            continue
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"pid": os.getpid(), "time": iso(utcnow())}, fh)
        return True
    return False


def release_lock():
    path = lock_path()
    if path.exists():
        os.replace(str(path), str(path.with_name("lock.done")))


def git_toplevel(root):
    code, out = run_cmd(["git", "rev-parse", "--show-toplevel"], cwd=str(root), timeout=GIT_TIMEOUT)
    top = out.strip()
    if code == 0 and top:
        return Path(top)
    return Path(root)


def improve_prompt(section):
    """The improve prompt, bounding how many groups (and paid eval runs) one launch handles."""
    return "/evolving-skills improve --max-groups %s --eval-max-cost-usd %s" % (
        section["max_groups"], section["eval_max_cost_usd"])


def claude_argv(claude_bin, prompt, section):
    return ([claude_bin, "-p", prompt, "--agent", str(section["agent"]),
             "--max-budget-usd", str(section["max_budget_usd"]), "--allowedTools"]
            + [str(t) for t in section["tools"]]
            + ["Bash(python3 %s/*)" % SCRIPTS_DIR])


# --------------------------------------------------------------------------
# hook
# --------------------------------------------------------------------------

def hook_log(session, decision, detail=""):
    try:
        path = auto_dir() / "hook.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        detail = " ".join(str(detail).split())
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("%s %s %s %s\n" % (iso(utcnow()), session or "-", decision, detail))
    except Exception:  # noqa: BLE001 - a hook must never fail
        pass


def safe_name(text):
    return re.sub(r"[^A-Za-z0-9._-]", "_", text) or "session"


def hook_decide(payload, claude_bin):
    """Make the hook decision; returns (decision, detail)."""
    if os.environ.get("EVOLVING_SKILLS_CHILD") == "1":
        return "skip-child", ""
    reasons = disabled_reasons()
    if reasons:
        return "skip-disabled", ",".join(reasons)
    transcript = payload.get("transcript_path")
    if not isinstance(transcript, str) or not transcript or not Path(transcript).is_file():
        return "skip-no-transcript", str(transcript or "")

    cfg = load_config()
    cwd = payload.get("cwd") if isinstance(payload.get("cwd"), str) and payload.get("cwd") else os.getcwd()
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    import session_digest  # noqa: E402 - sibling module

    roots = [SKILLS_ROOT]
    project_skills = Path(cwd) / ".claude" / "skills"
    if cfg.get("project_roots") is True and project_skills.is_dir() and project_skills.resolve() != Path(SKILLS_ROOT).resolve():
        roots.append(project_skills)
    digest = session_digest.build_digest(transcript, roots)
    harvest = bool(digest["skills_used"]) and len(digest["followups"]) >= int(cfg["min_followups"])
    improve = promotable()
    summary = "skills=%d followups=%d harvest=%s improve=%s" % (
        len(digest["skills_used"]), len(digest["followups"]), harvest, improve)
    if not harvest and not improve:
        return "skip-nothing-to-do", summary
    exists, stale, _data = lock_info(cfg)
    if exists and not stale:
        return "skip-locked", summary

    argv = [sys.executable, str(SCRIPT_PATH), "run", "--cwd", str(cwd)]
    if harvest:
        session = payload.get("session_id") if isinstance(payload.get("session_id"), str) else ""
        digest_path = auto_dir() / "digests" / ("%s.json" % safe_name(session or digest["session_id"]))
        digest_path.parent.mkdir(parents=True, exist_ok=True)
        digest_path.write_text(json.dumps(digest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        argv += ["--digest", str(digest_path)]
    if claude_bin != "claude":
        argv += ["--claude-bin", claude_bin]
    log_path = auto_dir() / "logs" / ("%s-worker.log" % stamp(utcnow()))
    pid = spawn_detached(argv, str(cwd), child_env(), str(log_path))
    return "launch", "%s pid=%s" % (summary, pid)


def cmd_hook(argv):
    session = ""
    try:
        parser = argparse.ArgumentParser(prog="auto_run.py hook", add_help=False)
        parser.add_argument("--claude-bin", default="claude")
        args, _unknown = parser.parse_known_args(argv)
        claude_bin = args.claude_bin
    except BaseException:  # noqa: BLE001 - argparse exits on bad input
        claude_bin = "claude"
    try:
        try:
            payload = json.loads(sys.stdin.read() or "{}")
        except ValueError:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        session = payload.get("session_id") if isinstance(payload.get("session_id"), str) else ""
        decision, detail = hook_decide(payload, claude_bin)
        hook_log(session, decision, detail)
    except BaseException as exc:  # noqa: BLE001 - a hook must never fail
        hook_log(session, "error", repr(exc))
    return 0


# --------------------------------------------------------------------------
# run
# --------------------------------------------------------------------------

def cmd_run(args):
    cfg = load_config()
    if not acquire_lock(cfg):
        print(json.dumps({"ran": [], "skipped": "locked"}))
        return 0
    ran = []
    try:
        if args.digest:
            if read_counts()["harvest"] < int(cfg["harvest"]["daily_cap"]):
                bump_count("harvest")
                log_path = auto_dir() / "logs" / ("%s-harvest.log" % stamp(utcnow()))
                code, _ = run_cmd(
                    claude_argv(args.claude_bin, "/evolving-skills harvest %s" % args.digest, cfg["harvest"]),
                    cwd=args.cwd, timeout=HARVEST_TIMEOUT, env=child_env(), log_path=log_path)
                ran.append({"pass": "harvest", "code": code, "log": str(log_path)})
            else:
                ran.append({"pass": "harvest", "skipped": "daily_cap"})
        if promotable():
            if read_counts()["improve"] < int(cfg["improve"]["daily_cap"]):
                bump_count("improve")
                log_path = auto_dir() / "logs" / ("%s-improve.log" % stamp(utcnow()))
                code, _ = run_cmd(
                    claude_argv(args.claude_bin, improve_prompt(cfg["improve"]), cfg["improve"]),
                    cwd=str(git_toplevel(SKILLS_ROOT)), timeout=IMPROVE_TIMEOUT,
                    env=child_env(), log_path=log_path)
                ran.append({"pass": "improve", "code": code, "log": str(log_path)})
            else:
                ran.append({"pass": "improve", "skipped": "daily_cap"})
    finally:
        release_lock()
    print(json.dumps({"ran": ran}))
    return 0


# --------------------------------------------------------------------------
# status / disable / enable / settings-snippet
# --------------------------------------------------------------------------

def cmd_status(_args):
    cfg = load_config()
    reasons = disabled_reasons()
    exists, stale, data = lock_info(cfg)
    try:
        lines = (auto_dir() / "hook.log").read_text(encoding="utf-8").splitlines()[-10:]
    except OSError:
        lines = []
    counts = read_counts()
    print(json.dumps({
        "enabled": not reasons,
        "disabled_reasons": reasons,
        "state_dir": str(auto_dir()),
        "today": utcnow().strftime("%Y-%m-%d"),
        "counts": counts,
        "caps": {"harvest": cfg["harvest"]["daily_cap"], "improve": cfg["improve"]["daily_cap"]},
        "lock": {"held": exists and not stale, "exists": exists, "stale": stale, "info": data},
        "hook_log_tail": lines,
        "config": cfg,
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_disable(_args):
    path = auto_dir() / "disabled"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(iso(utcnow()) + "\n", encoding="utf-8")
    print("disabled: %s" % path)
    return 0


def cmd_enable(_args):
    path = auto_dir() / "disabled"
    if path.exists():
        target = path.with_name("disabled.off-%s" % stamp(utcnow()))
        os.replace(str(path), str(target))
        print("enabled (moved %s to %s)" % (path, target))
    else:
        print("already enabled")
    if os.environ.get("EVOLVING_SKILLS_AUTO") == "0":
        print("note: EVOLVING_SKILLS_AUTO=0 is still set in this environment", file=sys.stderr)
    return 0


def settings_snippet():
    return {"SessionEnd": [{"hooks": [{
        "type": "command",
        "command": 'python3 "%s" hook' % SCRIPT_PATH,
        "timeout": 15,
    }]}]}


def cmd_settings_snippet(_args):
    print(json.dumps(settings_snippet(), indent=2))
    return 0


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(prog="auto_run.py",
                                     description="Session-end trigger and worker for evolving-skills.")

    def error(message):
        raise UsageError(message)

    parser.error = error
    sub = parser.add_subparsers(dest="command")
    run = sub.add_parser("run")
    run.add_argument("--cwd", required=True)
    run.add_argument("--digest")
    run.add_argument("--claude-bin", default="claude")
    for name in ("status", "disable", "enable", "settings-snippet"):
        sub.add_parser(name)
    for p in sub.choices.values():
        p.error = error
    return parser


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "hook":
        return cmd_hook(argv[1:])
    try:
        args = build_parser().parse_args(argv)
    except UsageError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return EXIT_BAD_INVOCATION
    handlers = {
        "run": cmd_run,
        "status": cmd_status,
        "disable": cmd_disable,
        "enable": cmd_enable,
        "settings-snippet": cmd_settings_snippet,
    }
    if args.command not in handlers:
        print("error: a subcommand is required (hook, run, status, disable, enable, settings-snippet)",
              file=sys.stderr)
        return EXIT_BAD_INVOCATION
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
