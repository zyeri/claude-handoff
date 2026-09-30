#!/usr/bin/env python3
"""Round-trip fixture for the handoff skill (write, resume, show, list).

Cross-platform: runs on Windows, macOS, and Linux (pure Python + git).
Run after editing SKILL.md:  python skills/handoff/tests/roundtrip.py
Prints per-check status; exits 0 with "ALL PASS", non-zero on first failure.

Layers:
  A. Mechanics - the git and filename behaviors the skill relies on actually hold.
  B. Skill text - SKILL.md still contains the instructions those mechanics enforce,
     so deleting a step from the doc fails the test (guards the skill, not just git).
  C. The Write and Resume halves agree on section and header names.
  D. A handoff built from the template is resumable (base dir, branch, session, verify).
  E. Quick mode's definition in SKILL.md keeps header, Remaining, Verification.
  F. Critical trigger phrases appear in both the description and the routing body.
  G. Date-relative resume refs resolve against real files.
  H. Resume staleness, including rewritten history, end to end.
  I. Each phrasing routes to the correct direction.
  J. The slash command routes every mode; command file and README use current naming.
  K. Half-scoped rules: each needle is checked in the half (Write/Resume) it governs.
"""
import re, subprocess, sys, tempfile, shutil, time
from pathlib import Path
from typing import NoReturn

# "HANDOFF.md" not preceded by a filename char, i.e. the pre-0.2.0 bare name
BARE_NAME = re.compile(r"(?<![\w*-])HANDOFF\.md")

SKILL = Path(__file__).resolve().parent.parent / "SKILL.md"
VERBOSE = "-v" in sys.argv or "--verbose" in sys.argv
SLOW_BUDGET_S = 3.0   # soft warn past this; not a failure (slow machines vary)
passed = 0

def ok(msg):
    global passed; passed += 1
    if VERBOSE:
        print(f"  ok: {msg}")

def fail(msg) -> NoReturn:
    print(f"FAIL: {msg}", file=sys.stderr); sys.exit(1)

def git(*args, cwd, check=True):
    return subprocess.run(["git", *args], cwd=cwd, check=check,
                          capture_output=True, text=True)

# ----- Layer A: mechanics -----
def test_mechanics():
    work = Path(tempfile.mkdtemp())
    try:
        git("init", "-q", cwd=work)
        git("config", "user.email", "t@t", cwd=work)
        git("config", "user.name", "t", cwd=work)
        (work / "calc.py").write_text("def add(a,b): return a+b\n")
        git("add", "-A", cwd=work); git("commit", "-qm", "add calc.add", cwd=work)
        base = git("rev-parse", "--short", "HEAD", cwd=work).stdout.strip()
        # dirty tree
        with (work / "calc.py").open("a") as f:
            f.write("def sub(a,b): return a-b  # WIP, no test\n")

        if git("rev-parse", "--is-inside-work-tree", cwd=work).stdout.strip() != "true":
            fail("in-repo detection")
        ok("in-repo detection")

        if not git("status", "--short", cwd=work).stdout.strip():
            fail("dirty tree not detected")
        ok("dirty tree detected (uncommitted-work path)")

        r = subprocess.run([sys.executable, "-c",
                            "import calc; assert calc.add(1,2)==3"], cwd=work)
        if r.returncode != 0:
            fail("verify command")
        ok("verify command passes before being recorded")

        if len([x for x in git("log","--oneline",f"{base}..HEAD",cwd=work).stdout.splitlines() if x]) != 0:
            fail("should be current while fresh")
        ok("staleness: current when fresh")
        git("add", "-A", cwd=work); git("commit", "-qm", "add sub()", cwd=work)
        drift = [x for x in git("log","--oneline",f"{base}..HEAD",cwd=work).stdout.splitlines() if x]
        if len(drift) < 1:
            fail("staleness drift not detected")
        ok("staleness: drift detected after new commit")

        (work / "2026-08-30-143000-ca154123-HANDOFF.md").write_text("")
        (work / "2026-08-30-090000-7f2e9a41-HANDOFF.md").write_text("")
        newest = sorted(p.name for p in work.glob("*-HANDOFF.md"))[-1]
        if newest != "2026-08-30-143000-ca154123-HANDOFF.md":
            fail(f"date-first sort (got {newest})")
        ok("date-first archive sorts chronologically")

        # same-second collision resolved by session id, not overwritten
        (work / "2026-08-30-143000-aaaaaaaa-HANDOFF.md").write_text("")
        (work / "2026-08-30-143000-bbbbbbbb-HANDOFF.md").write_text("")
        same_second = sorted(p.name for p in work.glob("2026-08-30-143000-*-HANDOFF.md"))
        if len(same_second) != 3:
            fail(f"same-second files collided (got {same_second})")
        ok("session-id suffix prevents same-second filename collisions")

        # a renamed legacy file joins the glob and sorts by its When: time
        (work / "2026-08-30-120000-legacy-HANDOFF.md").write_text("")
        names = sorted(p.name for p in work.glob("*-HANDOFF.md"))
        if names.index("2026-08-30-120000-legacy-HANDOFF.md") != 1:
            fail(f"renamed legacy handoff mis-sorted: {names}")
        ok("legacy rename target joins the glob in date order")
        # a bare HANDOFF.md never matches the glob, so resume must look for it
        (work / "HANDOFF.md").write_text("")
        if "HANDOFF.md" in [p.name for p in work.glob("*-HANDOFF.md")]:
            fail("bare HANDOFF.md unexpectedly matched *-HANDOFF.md")
        ok("bare HANDOFF.md is invisible to the glob (needs its own check)")

        # repo root resolves the same from a subdirectory
        nested = work / "pkg" / "deep"; nested.mkdir(parents=True)
        top = git("rev-parse", "--show-toplevel", cwd=nested).stdout.strip()
        if Path(top).resolve() != work.resolve():
            fail(f"show-toplevel from subdir gave {top!r}")
        ok("base dir: show-toplevel finds the repo root from a subdirectory")
    finally:
        shutil.rmtree(work, ignore_errors=True)

    # no-git fallback: detection is non-true outside any repo
    outside = Path(tempfile.mkdtemp())
    try:
        res = git("rev-parse", "--is-inside-work-tree", cwd=outside, check=False)
        if res.returncode == 0 and res.stdout.strip() == "true":
            fail("no-git fallback should not report a repo")
        ok("no-git fallback detected")
    finally:
        shutil.rmtree(outside, ignore_errors=True)

# ----- Layer B: skill text still enforces the mechanics -----
def test_skill_text():
    text = SKILL.read_text(encoding="utf-8")
    required = {
        "no-git detection":     "is-inside-work-tree",
        "date-first archive":   "date-first",
        "staleness check":      "Check staleness",
        "verify is run":        "Prove the verification",
        "self-audit step":      "Self-audit",
        "secrets guard":        "secret-shaped",
        "base dir rule":        "Run everything from",
        "both directions":      "Resuming from a handoff",
        "resume slash verb":    "/handoff resume",
        "quick slash verb":     "/handoff quick",
        "show slash verb":      "/handoff show",
        "write NL phrasing":    "create/write/make a handoff",
        "show direction":       "Showing a handoff",
        "read-means-resume":    "\"read the handoff\" means Resume",
        "routing default":      "Default when nothing disambiguates",
        "clean-tree resumes":   "**clean** working tree",
        "dirty-tree asks":      "write a new one covering your current changes",
        "date-relative resume": "yesterday's",
        "format stamp template":"**Format:** handoff/2",
        "format check in resume":"Check the format stamp",
        "format bump rule":     "record the change in `CHANGELOG.md`",
        "self-ref verify trap": "self-referential trap",
        "session id in name":   "short-session-id",
        "session env var":      "CLAUDE_CODE_SESSION_ID",
        "session header line":  "**Session:**",
        "no bare HANDOFF.md":   "never writes a bare `HANDOFF.md`",
        "cross-session check":  "written by a different session",
    }
    for label, needle in required.items():
        if needle not in text:
            fail(f"SKILL.md missing instruction for: {label} ({needle!r})")
        ok(f"skill text present: {label}")

# ----- Layer K: half-scoped rules (a needle in the wrong half proves nothing) -----
def _halves():
    text = SKILL.read_text(encoding="utf-8")
    write_half, _, resume_half = text.partition("# Resuming from a handoff")
    if not resume_half:
        fail("could not split SKILL.md into Write / Resume halves")
    return write_half, resume_half

def test_half_scoped_rules():
    write_half, _ = _halves()
    # cleanup never deletes: another session's in-flight handoff must survive
    if "keep only the 3 most recent" in write_half:
        fail("Write half still deletes old handoffs (cross-session prune)")
    if "never delete" not in write_half or "suggest" not in write_half:
        fail("Write half must list old handoffs and suggest removal, never delete")
    ok("write: old handoffs are listed for removal, never deleted")
    text = SKILL.read_text(encoding="utf-8")
    _, resume_half = _halves()
    checks = [
        # 11: Author carries a human name, not always "Claude"
        (write_half, "git config user.name", "write: Author from git user.name"),
        # 8: files live at the repo root, whatever dir the session started in
        (text, "git rev-parse --show-toplevel", "base dir: repo root via show-toplevel"),
        (write_half, "Write the file in the base dir", "write: file goes in the base dir"),
        # 9: the dirty-tree guard must be in the Resume half (it was also in Write)
        (resume_half, "git status --short", "resume: dirty-tree guard before checkout"),
        # 6: missing header fields are handled, not errored on
        (resume_half, "no `Session:` line", "resume: absent Session line"),
        (resume_half, "`CLAUDE_CODE_SESSION_ID` is unset", "resume: own session id unset"),
        (resume_half, "no `Branch:`", "resume: absent Branch/Last commit (no-git doc)"),
        (resume_half, "if that session is still running", "resume: mismatch framed as info"),
        # 10: a leftover bare HANDOFF.md is found, flagged, renamed only on approval
        (resume_half, "legacy", "resume: legacy bare HANDOFF.md considered"),
        (resume_half, "-legacy-HANDOFF.md", "resume: legacy rename target"),
        (resume_half, "only if the user approves", "resume: legacy rename needs approval"),
        # 7: a list direction
        (text, "# Listing handoffs", "list direction section"),
        (text, "/handoff list", "list slash verb"),
    ]
    for hay, needle, label in checks:
        if needle not in hay:
            fail(f"SKILL.md missing {label} ({needle!r})")
        ok(label)
    # 10: routing default must see a legacy bare HANDOFF.md, or an upgrading
    # user with only a bare file gets a fresh write and never reaches Resume
    default = text.split("**Default when nothing disambiguates**", 1)[1].split("###", 1)[0]
    if "legacy bare `HANDOFF.md` exists" not in default or "treat it as a match" not in default:
        fail("routing default ignores a legacy bare HANDOFF.md")
    ok("routing default counts a legacy bare HANDOFF.md")
    # 7: session-id refs match the id segment only (hex ids can start with digits)
    for needle, label in [("the segment between the timestamp and `-HANDOFF.md`", "session ref matches id segment only"),
                          ("more than one file matches, list them and ask", "ambiguous session ref asks"),
                          ("first `Remaining` item", "list falls back when Goal is absent (Quick docs)")]:
        if needle not in text:
            fail(f"SKILL.md missing {label} ({needle!r})")
        ok(label)
    # 8: no instruction still anchors handoff files to the cwd
    if "in the working directory" in text:
        fail("SKILL.md still anchors handoff files to the working directory")
    ok("base dir: no cwd-anchored lookup left")
    # timestamp + fallback id come from command output, never the model's head
    for needle, label in [("date +%Y-%m-%d-%H%M%S", "POSIX timestamp command"),
                          ("Get-Date -Format yyyy-MM-dd-HHmmss", "PowerShell timestamp command"),
                          ("/dev/urandom", "POSIX random-id command"),
                          ("NewGuid()", "PowerShell random-id command"),
                          ("from a command run in this turn", "self-audit: timestamp provenance")]:
        if needle not in write_half:
            fail(f"Write half missing {label} ({needle!r})")
        ok(f"write: {label}")
    # portable base dir: name the repo by identity, not the author's local path
    for needle, label in [("git remote get-url origin", "base dir from repo identity"),
                          ("no absolute path from this machine", "self-audit: no local absolute paths")]:
        if needle not in write_half:
            fail(f"Write half missing {label} ({needle!r})")
        ok(f"write: {label}")

# ----- Layer C: the two halves stay in sync -----
# A section written by the Write half is read by name in the Resume half.
# Rename one without the other and the doc silently breaks - assert both agree.
def test_halves_in_sync():
    text = SKILL.read_text(encoding="utf-8")
    write_half, _, resume_half = text.partition("# Resuming from a handoff")
    if not resume_half:
        fail("could not split SKILL.md into Write / Resume halves")
    # (label, token the WRITE template emits, token the RESUME half reads it by)
    shared = [
        ("Verification section", "## Verification", "Verification"),
        ("Branch header line",   "**Branch:**",     "Branch"),
        ("Session header line",  "**Session:**",    "Session"),
        ("base dir header",      "Run everything from", "base dir"),
        ("Completed section",    "## Completed",    "Completed"),
        ("Remaining section",    "## Remaining",    "Remaining"),
        ("Watch out section",    "## Watch out",    "Watch out"),
    ]
    for label, write_tok, read_tok in shared:
        if write_tok not in write_half:
            fail(f"Write half no longer emits: {label} ({write_tok!r})")
        if read_tok not in resume_half:
            fail(f"Resume half no longer reads: {label} ({read_tok!r})")
        ok(f"halves in sync: {label}")

# ----- Layer D: a written handoff is actually resumable -----
# Build a doc from the template's real shape, then confirm a resumer can extract
# the three things it must: base dir, branch, and a runnable verify command.
SAMPLE = """# Handoff - sample

- **When:** 2026-08-30 14:30 | **Author:** test | **Format:** handoff/2
- **Session:** ca154123 (full: ca154123-b6ff-45f6-8e61-0f3d22874fff)
- **Branch:** `main` | **Last commit:** `abc1234 seed`
- **Run everything from:** `sample` repo root (your clone of https://example.com/sample.git) - every command and path below is relative to here.
- **Resume with:** `python -c "import calc"`

## Completed
- [x] add() - calc.py

## Remaining
- [ ] (clear) add sub test - write test_sub

## Verification
```
python -c "print('PASS')"          # expected: prints PASS
```

## Watch out
- nothing
"""

def _extract(doc, label):
    for line in doc.splitlines():
        if label in line and "`" in line:
            return line.split("`")[1]
    return None

def test_resumable_contract():
    base = _extract(SAMPLE, "Run everything from")
    branch = _extract(SAMPLE, "**Branch:**")
    if base != "sample":
        fail(f"resumer can't extract base dir (got {base!r})")
    ok("resumable: base dir extractable")
    # portable: the base dir names the repo, never this machine's absolute path
    if base.startswith(("/", "\\", "~")) or (len(base) > 1 and base[1] == ":"):
        fail(f"base dir is a machine-specific absolute path: {base!r}")
    ok("resumable: base dir is portable (not an absolute local path)")
    if branch != "main":
        fail(f"resumer can't extract branch (got {branch!r})")
    ok("resumable: branch extractable")
    # format stamp: resumer parses 'Format: handoff/N' from the header
    fmt = None
    for line in SAMPLE.splitlines():
        if "Format:" in line:
            fmt = line.split("Format:**")[1].strip().split()[0]
            break
    if fmt != "handoff/2":
        fail(f"resumer can't extract format stamp (got {fmt!r})")
    ok("resumable: format stamp extractable (handoff/2)")
    # session line: resumer parses the short session id for disambiguation
    session_line = next(l for l in SAMPLE.splitlines() if "**Session:**" in l)
    session = session_line.split("**Session:**")[1].strip().split()[0]
    if session != "ca154123":
        fail(f"resumer can't extract session id (got {session!r})")
    ok("resumable: session id extractable")
    # verify command lives in the fenced block after '## Verification'
    after = SAMPLE.split("## Verification", 1)[1]
    cmd = after.split("```", 2)[1].strip().splitlines()[0].split("#")[0].strip()
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.returncode != 0 or "PASS" not in r.stdout:
        fail(f"resumer's extracted verify command didn't pass: {cmd!r}")
    ok("resumable: verify command runs and passes end-to-end")

# ----- Layer E: Quick mode still carries the must-haves -----
def test_quick_mode():
    text = SKILL.read_text(encoding="utf-8")
    quick = next((l for l in text.splitlines() if l.startswith("- **Quick**")), None)
    if quick is None:
        fail("SKILL.md no longer defines Quick mode")
    for needle, label in [("header", "header"),
                          ("`Remaining`", "Remaining"),
                          ("`Verification`", "Verification")]:
        if needle not in quick:
            fail(f"Quick mode definition dropped required section: {label}")
        ok(f"quick mode keeps: {label}")

# ----- Layer F: critical trigger phrases live in BOTH description and routing table -----
# If a phrase is only in the table, the skill never fires on it (description gates loading).
# If only in the description, the body can't route it. Both, or neither.
def test_description_table_sync():
    text = SKILL.read_text(encoding="utf-8")
    fm = text.split("---", 2)[1]  # frontmatter block
    desc = next(l for l in fm.splitlines() if l.startswith("description:"))
    body = text.split("---", 2)[2]
    critical = ["create", "resume", "pick up", "continue",
                "wrap up", "show", "read the handoff", "list the handoffs"]
    for phrase in critical:
        if phrase not in desc:
            fail(f"trigger phrase missing from description: {phrase!r}")
        if phrase not in body:
            fail(f"trigger phrase missing from routing body: {phrase!r}")
        ok(f"trigger in both description + body: {phrase!r}")

# ----- Layer I: phrasings route to the CORRECT direction (not just present) -----
# Presence != routing. Find each phrase's row in the routing table and assert the
# row's bolded Direction is the expected one.
def _direction_of_row(text, phrase):
    for line in text.splitlines():
        if line.startswith("| **") and phrase in line:
            # first bold token is the Direction cell
            return line.split("**")[1].strip()
    return None

def test_routing_correctness():
    text = SKILL.read_text(encoding="utf-8")
    cases = [
        ("create/write/make a handoff", "Write"),
        ("wrap up",                     "Write"),
        ("quick handoff",               "Write"),
        ("read the handoff",            "Resume"),
        ("pick up where we left off",   "Resume"),
        ("where were we",               "Resume"),
        ("show me the handoff",         "Show"),
        ("print/display the handoff",   "Show"),
        ("list the handoffs",           "List"),
    ]
    for phrase, want in cases:
        got = _direction_of_row(text, phrase)
        if got != want:
            fail(f"routing: {phrase!r} -> {got!r}, expected {want!r}")
        ok(f"routes correctly: {phrase!r} -> {want}")

# ----- Layer J: plugin slash-command dispatches to the skill (when present) -----
# Only meaningful in the full plugin checkout (repo-root/commands/handoff.md).
# On a skill-only install that path won't exist, so skip rather than fail.
def test_command_file():
    cmd = SKILL.parents[2] / "commands" / "handoff.md"
    if not cmd.exists():
        ok("command file check skipped (skill-only checkout)")
        return
    text = cmd.read_text(encoding="utf-8")
    fm = text.split("---", 2)
    if "name:" not in fm[1] or "description:" not in fm[1]:
        fail("commands/handoff.md frontmatter incomplete")
    for mode in ("quick", "resume", "show", "list"):
        if mode not in text:
            fail(f"commands/handoff.md doesn't route mode: {mode}")
    if "$ARGUMENTS" not in text:
        fail("commands/handoff.md never consumes $ARGUMENTS")
    if "handoff" not in fm[1]:
        fail("commands/handoff.md doesn't reference the handoff skill")
    ok("command file dispatches all modes to the skill via $ARGUMENTS")
    # user-facing docs describe the current naming: no bare HANDOFF.md, no old name
    for doc in (cmd, cmd.parents[1] / "README.md"):
        if not doc.exists():
            continue
        body = doc.read_text(encoding="utf-8")
        # lines about upgrading from the legacy name may (must) mention it
        current = "\n".join(l for l in body.splitlines()
                            if "legacy" not in l and "0.1.x" not in l)
        if BARE_NAME.search(current) or "HHMM-HANDOFF" in current:
            fail(f"{doc.name} still describes a bare or old-style HANDOFF.md name")
        if "*-HANDOFF.md" not in body:
            fail(f"{doc.name} never names the *-HANDOFF.md files")
        ok(f"{doc.name} describes the current *-HANDOFF.md naming")
    # guard the real bug: an unanchored .gitignore rule (HANDOFF.md) plus
    # case-insensitive git silently excludes commands/handoff.md from the publish.
    root = cmd.parents[1]
    if (root / ".git").exists():
        ig = git("check-ignore", str(cmd), cwd=root, check=False)
        if ig.returncode == 0:   # a match means it's ignored
            fail("commands/handoff.md is git-ignored - it would never be published")
        ok("command file is NOT git-ignored (publishable)")

# ----- Layer G: date-relative archive selection (#4) -----
# Drives off REAL files in a temp dir: create archives, glob them the way a resumer
# does, and resolve relative references. Tests the mechanism, not a hand-picked list.
def test_date_relative_pick():
    work = Path(tempfile.mkdtemp())
    try:
        for n in ("2026-08-28-090000-aaaaaaaa-HANDOFF.md",
                  "2026-08-29-140000-bbbbbbbb-HANDOFF.md",
                  "2026-08-30-103000-cccccccc-HANDOFF.md"):
            (work / n).write_text("")
        (work / "notes.md").write_text("")            # unrelated, must be ignored
        # glob exactly as the skill says: '*-HANDOFF.md', date-first sort
        archives = sorted(p.name for p in work.glob("*-HANDOFF.md"))
        if archives != ["2026-08-28-090000-aaaaaaaa-HANDOFF.md",
                        "2026-08-29-140000-bbbbbbbb-HANDOFF.md",
                        "2026-08-30-103000-cccccccc-HANDOFF.md"]:
            fail(f"archive glob picked wrong set: {archives}")
        ok("date-relative: glob selects only real *-HANDOFF.md files")
        today = "2026-08-30"
        prev = sorted(a for a in archives if not a.startswith(today))[-1]
        if prev != "2026-08-29-140000-bbbbbbbb-HANDOFF.md":
            fail(f"'previous' pick wrong (got {prev})")
        ok("date-relative: 'previous' resolves to newest before today")
        match = [a for a in archives if a.startswith("2026-08-28")]
        if match != ["2026-08-28-090000-aaaaaaaa-HANDOFF.md"]:
            fail("date-prefix match wrong")
        ok("date-relative: date prefix resolves exactly")
    finally:
        shutil.rmtree(work, ignore_errors=True)

# ----- Layer H: resume half surfaces staleness end-to-end (#5) -----
# Parse a handoff's recorded 'Last commit' hash, advance the repo, and confirm
# the comparison the resume step describes reports drift.
def test_resume_staleness_e2e():
    work = Path(tempfile.mkdtemp())
    try:
        git("init", "-q", cwd=work)
        git("config", "user.email", "t@t", cwd=work)
        git("config", "user.name", "t", cwd=work)
        (work / "f.txt").write_text("1\n")
        git("add", "-A", cwd=work); git("commit", "-qm", "seed", cwd=work)
        recorded = git("rev-parse", "--short", "HEAD", cwd=work).stdout.strip()
        doc = f"- **Branch:** `main` | **Last commit:** `{recorded} seed`\n"
        # fresh: resume should see 0 drift
        parsed = doc.split("Last commit:")[1].split("`")[1].split()[0]
        n = [x for x in git("log","--oneline",f"{parsed}..HEAD",cwd=work).stdout.splitlines() if x]
        if len(n) != 0:
            fail("resume staleness: should be current")
        ok("resume staleness e2e: current handoff shows 0 drift")
        # advance repo, resume should now flag drift
        (work / "f.txt").write_text("2\n")
        git("add", "-A", cwd=work); git("commit", "-qm", "change", cwd=work)
        n = [x for x in git("log","--oneline",f"{parsed}..HEAD",cwd=work).stdout.splitlines() if x]
        if len(n) < 1:
            fail("resume staleness: drift not surfaced")
        ok("resume staleness e2e: stale handoff surfaces drift")
        # recorded commit is an ancestor: merge-base exits 0, drift count is meaningful
        if git("merge-base", "--is-ancestor", parsed, "HEAD", cwd=work, check=False).returncode != 0:
            fail("ancestor check: reachable recorded commit not seen as ancestor")
        ok("rewritten-commit check: reachable commit is an ancestor (exit 0)")
        # history rewritten (amend/rebase/squash): the recorded commit is no longer
        # an ancestor, and 'log <hash>..HEAD' would report a misleading drift count
        rewritten = git("rev-parse", "--short", "HEAD", cwd=work).stdout.strip()
        git("commit", "--amend", "-qm", "change (amended)", cwd=work)
        rc = git("merge-base", "--is-ancestor", rewritten, "HEAD", cwd=work, check=False).returncode
        if rc != 1:
            fail(f"rewritten commit should not be an ancestor (exit 1), got exit {rc}")
        ok("rewritten-commit check: amended-away commit is not an ancestor (exit 1)")
        # object gone entirely (fresh clone, gc): merge-base errors instead
        rc = git("merge-base", "--is-ancestor", "deadbeefdeadbeef", "HEAD", cwd=work, check=False).returncode
        if rc not in (1, 128):
            fail(f"missing commit should fail the ancestor check, got exit {rc}")
        ok("rewritten-commit check: missing object fails the ancestor check")
        _, resume_half = _halves()
        for needle, label in [("git merge-base --is-ancestor", "ancestor check"),
                              ("not in this branch's history", "rewritten-history message"),
                              ("git log -1 --format=%ci", "When: fallback comparison"),
                              ("recorded commit gone", "drift flag for a gone commit")]:
            if needle not in resume_half:
                fail(f"Resume half missing {label} ({needle!r})")
            ok(f"resume: {label}")
    finally:
        shutil.rmtree(work, ignore_errors=True)

if __name__ == "__main__":
    if not shutil.which("git"):
        fail("git not on PATH")
    t0 = time.perf_counter()
    test_mechanics()
    test_skill_text()
    test_halves_in_sync()
    test_half_scoped_rules()
    test_resumable_contract()
    test_quick_mode()
    test_description_table_sync()
    test_routing_correctness()
    test_command_file()
    test_date_relative_pick()
    test_resume_staleness_e2e()
    elapsed = time.perf_counter() - t0
    print(f"ALL PASS ({passed} checks, {elapsed:.2f}s)"
          + ("   [run with -v for per-check output]" if not VERBOSE else ""))
    if elapsed > SLOW_BUDGET_S:
        print(f"WARN: fixture took {elapsed:.2f}s (> {SLOW_BUDGET_S:.0f}s budget) "
              "- consider trimming subprocess-heavy layers", file=sys.stderr)
