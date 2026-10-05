#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = []
# ///
"""Gather the repo and handoff state the handoff skill needs, in one call.

Usage:  handoff_state.py write | list | resume [--file NAME]
Prints one JSON object (ASCII). Read-only: never writes, renames, or deletes,
and never runs the handoff's verification command. Outside git every git field
is null and the script still succeeds.
"""
# Startup cost matters here (the script runs on every handoff): stdlib modules
# that subprocess does not already load (pathlib, datetime, secrets) are avoided.
import json, os, re, subprocess, sys, time

PLAN_FILES = ("PLAN.md", "TASK_LIST.md", "TODO.md")
LEGACY = "HANDOFF.md"
# never let git refresh the index: keeps the script read-only and safe to run
# beside other git processes
GIT_ENV = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}


def spawn(*args, cwd, quiet=False):
    """Start git without waiting, so independent calls overlap. None if git is absent."""
    try:
        return subprocess.Popen(["git", *args], cwd=cwd, env=GIT_ENV,
                                stdout=subprocess.DEVNULL if quiet else subprocess.PIPE,
                                stderr=subprocess.DEVNULL,
                                encoding="utf-8", errors="replace")
    except OSError:
        return None


def result(proc):
    """Stripped stdout of a spawned git, or None when it failed or never started."""
    if proc is None:
        return None
    out, _ = proc.communicate()
    return out.strip() if proc.returncode == 0 else None


def lines(text):
    return [l for l in text.splitlines() if l] if text else []


def session():
    full = os.environ.get("CLAUDE_CODE_SESSION_ID") or None
    if full:
        return {"full": full, "short": full[:8], "fallback": False}
    return {"full": None, "short": os.urandom(4).hex(), "fallback": True}


def after(line, label):
    return line.split(label, 1)[1].strip() if label in line else ""


BACKTICKED = re.compile(r"`([^`]*)`")
SENTENCE_END = re.compile(r"(?<=[.!?])\s")
WHEN = re.compile(r"(\d{4}-\d{2}-\d{2}) (\d{2}):(\d{2})")


def backticked(text):
    m = BACKTICKED.search(text or "")
    return m.group(1) if m else None


def parse_header(path):
    """Header fields plus a one-line summary (Goal's first sentence, else first Remaining)."""
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    h: dict = {"when": None, "session": None, "branch": None, "last_commit": None,
               "format": None, "goal": None}
    for line in text.splitlines():
        if "**" not in line:
            continue
        if "**When:**" in line:
            h["when"] = after(line, "**When:**").split("|")[0].strip()
        if "**Format:**" in line:
            h["format"] = (after(line, "**Format:**").split() or [None])[0]
        if "**Session:**" in line:
            h["session"] = (after(line, "**Session:**").split() or [None])[0]
        if "**Branch:**" in line:
            h["branch"] = backticked(after(line, "**Branch:**").split("|")[0])
        if "**Last commit:**" in line:
            commit = backticked(after(line, "**Last commit:**"))
            h["last_commit"] = commit.split()[0] if commit else None
    h["goal"] = summary(text)
    return h


def section_lines(text, heading):
    body = text.split(f"\n{heading}\n", 1)
    if len(body) < 2:
        return []
    out = []
    for line in body[1].splitlines():
        if line.startswith("## "):
            break
        line = line.strip()
        if line and not line.startswith("<!--"):
            out.append(line)
    return out


def summary(text):
    goal = section_lines(text, "## Goal")
    if goal:
        return SENTENCE_END.split(goal[0], maxsplit=1)[0]
    for line in section_lines(text, "## Remaining"):
        if line.startswith("- [ ]"):
            return line[len("- [ ]"):].strip()
    return None


def sort_key(entry):
    """Dated names sort as-is; a legacy file sorts by its When: (seconds 00)."""
    if not entry["legacy"]:
        return entry["name"]
    m = WHEN.match(entry["when"] or "")
    return f"{m.group(1)}-{m.group(2)}{m.group(3)}00" if m else ""


def handoffs(base, own):
    """Every *-HANDOFF.md plus a legacy bare HANDOFF.md, parsed, newest first.

    normcase gives the platform's case rules (folded on Windows, exact elsewhere),
    matching what glob("*-HANDOFF.md") did.
    """
    legacy, suffix = os.path.normcase(LEGACY), os.path.normcase("-HANDOFF.md")
    out = []
    with os.scandir(base) as entries:
        for e in entries:
            name = os.path.normcase(e.name)
            is_legacy = name == legacy
            if not (is_legacy or name.endswith(suffix)) or not e.is_file():
                continue
            h = parse_header(e.path)
            out.append({"name": e.name, "legacy": is_legacy,
                        "own": not own["fallback"] and h["session"] == own["short"], **h})
    return sorted(out, key=sort_key, reverse=True)


def start_staleness(commit, cwd):
    """Start the ancestor check and drift count side by side; None if nothing to check."""
    if not commit:
        return None
    return (commit,
            spawn("merge-base", "--is-ancestor", commit, "HEAD", cwd=cwd, quiet=True),
            spawn("rev-list", "--count", f"{commit}..HEAD", cwd=cwd))


def staleness(started, latest):
    """Collect start_staleness(); drift only counts when the commit is an ancestor."""
    if started is None:
        return None
    commit, anc, count = started
    drift = result(count)
    if anc is None:
        return None
    anc.wait()
    ancestor = anc.returncode == 0
    return {"recorded_commit": commit, "is_ancestor": ancestor,
            "drift": int(drift) if ancestor and drift else None,
            "latest_commit_date": latest}


def main(argv):
    if not argv or argv[0] not in ("write", "list", "resume"):
        print(__doc__, file=sys.stderr)
        return 2
    mode, cwd = argv[0], os.getcwd()
    # Start every git call before waiting on any. All run from the cwd, which git
    # resolves to the same repo as the root; status is told to print root-relative
    # paths. Outside git they all fail fast and are discarded below.
    procs = {"top": spawn("rev-parse", "--show-toplevel", cwd=cwd)}
    if mode == "write":
        procs.update(
            branch=spawn("branch", "--show-current", cwd=cwd),
            log=spawn("log", "--oneline", "-20", cwd=cwd),
            status=spawn("-c", "status.relativePaths=false", "status", "--short", cwd=cwd),
            diff_stat=spawn("diff", "--stat", cwd=cwd),
            stash=spawn("stash", "list", cwd=cwd),
            user_name=spawn("config", "user.name", cwd=cwd),
            remote=spawn("remote", "get-url", "origin", cwd=cwd))
    elif mode == "resume":
        procs.update(
            current_branch=spawn("branch", "--show-current", cwd=cwd),
            status=spawn("-c", "status.relativePaths=false", "status", "--short", cwd=cwd),
            latest=spawn("log", "-1", "--format=%ci", cwd=cwd))
    # Only the root is needed to read the handoffs: do that (and, for resume, start
    # the staleness calls) while the rest of the first wave is still running.
    top = result(procs.pop("top"))
    in_git = top is not None
    base = os.path.normpath(top) if in_git else cwd
    sess = session()
    found = handoffs(base, sess)
    target = None
    if mode == "resume":
        name = argv[2] if len(argv) > 2 and argv[1] == "--file" else None
        if name:
            target = next((h for h in found if h["name"] == name), None)
        else:
            target = found[0] if found else None
    started = start_staleness(target["last_commit"], base) if in_git and target else None
    got = {k: result(p) for k, p in procs.items()}
    if not in_git:  # user.name may come from global config; the rest is repo-only
        got = {k: (v if k == "user_name" else None) for k, v in got.items()}
    out = {"base_dir": base, "in_git": in_git, "session": sess}

    if mode == "write":
        now = time.localtime()
        out.update({
            "branch": got["branch"],
            "log": lines(got["log"]) if in_git else None,
            "status": got["status"],
            "diff_stat": got["diff_stat"],
            "stash": lines(got["stash"]) if in_git else None,
            "user_name": got["user_name"],
            "remote": got["remote"],
            "timestamp": time.strftime("%Y-%m-%d-%H%M%S", now),
            "when": time.strftime("%Y-%m-%d %H:%M", now),
            "plan_files": [n for n in PLAN_FILES if os.path.isfile(os.path.join(base, n))],
            "handoffs": found,
        })
    elif mode == "list":
        out["handoffs"] = found
    else:
        if len(argv) > 2 and argv[1] == "--file":
            out["missing_file"] = None if target else argv[2]
        out.update({
            "current_branch": got["current_branch"],
            "status": got["status"],
            "legacy": any(h["legacy"] for h in found),
            "handoffs": found,
            "target": target,
            "staleness": staleness(started, got["latest"]),
        })
    print(json.dumps(out, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
