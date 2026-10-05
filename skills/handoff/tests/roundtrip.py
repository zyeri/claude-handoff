#!/usr/bin/env python3
"""Round-trip fixture for the handoff skill (write, resume, show, list).

Cross-platform: runs on Windows, macOS, and Linux (pure Python + git).
Run after editing SKILL.md, write.md, resume.md, or scripts/handoff_state.py:
  python skills/handoff/tests/roundtrip.py
Prints per-check status; exits 0 with "ALL PASS", non-zero on first failure.

The Write half is write.md and the Resume half is resume.md; SKILL.md is the router.

Layers:
  A. Mechanics - the git and filename behaviors the skill relies on actually hold.
  B. Skill text - the skill files still contain the instructions those mechanics
     enforce, so deleting a step from the doc fails the test (guards the skill, not
     just git); the router points at the direction files without carrying them.
  C. The Write and Resume halves agree on section and header names.
  D. A handoff built from the template is resumable (base dir, branch, session, verify).
  E. Quick mode's definition in SKILL.md keeps header, Remaining, Verification.
  F. Critical trigger phrases appear in both the description and the routing body.
  G. Date-relative resume refs resolve against real files.
  H. Resume staleness, including rewritten history, end to end.
  I. Each phrasing routes to the correct direction.
  J. The slash command routes every mode; command file and README use current naming.
  K. Half-scoped rules: each needle is checked in the half (Write/Resume) it governs.
  L. The state script reports correct JSON against temp repos, writes nothing, and
     every direction is told to call it.
"""
import json, os, re, subprocess, sys, tempfile, shutil, time
from pathlib import Path
from typing import NoReturn

# "HANDOFF.md" not preceded by a filename char, i.e. the pre-0.2.0 bare name
BARE_NAME = re.compile(r"(?<![\w*-])HANDOFF\.md")

SKILL = Path(__file__).resolve().parent.parent / "SKILL.md"
WRITE = SKILL.parent / "write.md"     # Write direction, read on demand
RESUME = SKILL.parent / "resume.md"   # Resume direction, read on demand
VERBOSE = "-v" in sys.argv or "--verbose" in sys.argv
SLOW_BUDGET_S = 5.0   # soft warn past this; not a failure (layer L starts ~9 Pythons)
DESC_BUDGET = 450     # chars, the always-loaded frontmatter description line
passed = 0

def ok(msg):
    global passed; passed += 1
    if VERBOSE:
        print(f"  ok: {msg}")

def fail(msg) -> NoReturn:
    print(f"FAIL: {msg}", file=sys.stderr); sys.exit(1)

def _all_text():
    """Router plus both direction files: whole-skill checks search all three."""
    _halves()
    return "\n".join(f.read_text(encoding="utf-8") for f in (SKILL, WRITE, RESUME))

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
    text = _all_text()
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
    # the router loads on every call: it must point at the direction files and
    # must not carry their bodies, or the split saves nothing
    router = SKILL.read_text(encoding="utf-8")
    for name in ("write.md", "resume.md"):
        if name not in router:
            fail(f"router SKILL.md never tells the agent to read {name}")
        ok(f"router points at {name}")
    for heading in ("# Writing a handoff", "# Resuming from a handoff"):
        if f"\n{heading}\n" in router:
            fail(f"router SKILL.md still carries the {heading!r} body")
        ok(f"router does not carry {heading!r}")

# ----- Layer K: half-scoped rules (a needle in the wrong half proves nothing) -----
def _halves():
    """The Write half is write.md, the Resume half is resume.md (split in 0.2.1)."""
    for f in (WRITE, RESUME):
        if not f.exists():
            fail(f"direction file missing: {f.name}")
    return WRITE.read_text(encoding="utf-8"), RESUME.read_text(encoding="utf-8")

def test_half_scoped_rules():
    write_half, _ = _halves()
    # cleanup never deletes: another session's in-flight handoff must survive
    if "keep only the 3 most recent" in write_half:
        fail("Write half still deletes old handoffs (cross-session prune)")
    if "never delete" not in write_half or "suggest" not in write_half:
        fail("Write half must list old handoffs and suggest removal, never delete")
    ok("write: old handoffs are listed for removal, never deleted")
    text = _all_text()
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
    # verify runs once: the self-audit reruns it only when the handoff file can
    # change the result (the self-referential trap), else reuses step 4
    audit = write_half.split("**Self-audit", 1)[1].split("\n7.", 1)[0]
    for needle, label in [("reuse the step 4 result", "self-audit reuses step 4 verify"),
                          ("working-tree", "self-audit names the rerun condition")]:
        if needle not in audit:
            fail(f"self-audit missing {label} ({needle!r})")
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
    write_half, resume_half = _halves()
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
    text = _all_text()
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
    # the description sits in context every session, invoked or not: keep it lean
    if len(desc) > DESC_BUDGET:
        fail(f"description is {len(desc)} chars (> {DESC_BUDGET} budget)")
    ok(f"description within budget ({len(desc)} <= {DESC_BUDGET} chars)")

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

# ----- Layer L: the state script gathers in one call what the skill needs -----
# Run as a subprocess, never imported (an import would write __pycache__).
SCRIPT = SKILL.parent / "scripts" / "handoff_state.py"
SID = "ca154123-b6ff-45f6-8e61-0f3d22874fff"

def state(mode, *args, cwd, sid: str | None = SID):
    env = {k: v for k, v in os.environ.items()
           if k != "CLAUDE_CODE_SESSION_ID"}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if sid is not None:
        env["CLAUDE_CODE_SESSION_ID"] = sid
    r = subprocess.run([sys.executable, str(SCRIPT), mode, *args], cwd=cwd, env=env,
                       capture_output=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        fail(f"handoff_state.py {mode} exited {r.returncode}: {r.stderr.strip()}")
    if not r.stdout.isascii():
        fail(f"handoff_state.py {mode} printed non-ASCII output")
    try:
        return json.loads(r.stdout)
    except ValueError:
        fail(f"handoff_state.py {mode} printed non-JSON: {r.stdout[:200]!r}")

def _doc(when, session, commit, goal=None, remaining="(clear) next - do it"):
    head = (f"# Handoff - t\n\n- **When:** {when} | **Author:** t | **Format:** handoff/2\n"
            f"- **Session:** {session} (full: {session}-x)\n"
            f"- **Branch:** `main` | **Last commit:** `{commit} seed`\n\n")
    body = f"## Goal\n{goal}\n\n" if goal else ""
    return head + body + f"## Remaining\n- [ ] {remaining}\n"

def test_state_script():
    if not SCRIPT.exists():
        fail(f"state script missing: {SCRIPT.name}")
    # each direction gathers through the script, and keeps the raw commands as
    # the fallback for hosts with no Python
    router = SKILL.read_text(encoding="utf-8")
    write_half, resume_half = _halves()
    listing = router.split("# Listing handoffs", 1)[-1]
    for hay, needle, label in [
            (router, "uv run --no-project --script", "router: uv invocation"),
            (router, "scripts/handoff_state.py", "router: script path"),
            (router, "python3", "router: no-uv fallback"),
            (write_half, "handoff_state.py write", "write: gathers via the script"),
            (write_half, "git log --oneline -20", "write: raw-command fallback kept"),
            (resume_half, "handoff_state.py resume", "resume: gathers via the script"),
            (listing, "handoff_state.py list", "list: rows via the script")]:
        if needle not in hay:
            fail(f"skill text missing {label} ({needle!r})")
        ok(label)
    work = Path(tempfile.mkdtemp())
    try:
        git("init", "-q", "-b", "main", cwd=work)
        git("config", "user.email", "t@t", cwd=work)
        git("config", "user.name", "t", cwd=work)
        (work / "calc.py").write_text("x = 1\n")
        git("add", "-A", cwd=work); git("commit", "-qm", "seed", cwd=work)
        head = git("rev-parse", "--short", "HEAD", cwd=work).stdout.strip()
        (work / "calc.py").write_text("x = 2\n")              # dirty
        (work / "TODO.md").write_text("- a\n")
        sub = work / "pkg"; sub.mkdir()
        (sub / "new.py").write_text("y = 1\n")                # untracked, below the root

        before = sorted(p.name for p in work.rglob("*") if ".git" not in p.parts)
        w = state("write", cwd=sub)
        after = sorted(p.name for p in work.rglob("*") if ".git" not in p.parts)
        if before != after:
            fail(f"state script wrote files: {set(after) - set(before)}")
        ok("state: read-only (no files created)")

        if not w["in_git"] or Path(w["base_dir"]).resolve() != work.resolve():
            fail(f"state write: base dir {w['base_dir']!r}, in_git {w['in_git']!r}")
        ok("state write: base dir is the repo root from a subdirectory")
        if w["branch"] != "main" or w["user_name"] != "t" or w["remote"] is not None:
            fail(f"state write: branch/user/remote wrong: {w['branch']!r} {w['user_name']!r} {w['remote']!r}")
        ok("state write: branch, user.name, no remote")
        if not any("seed" in l for l in w["log"]) or "calc.py" not in w["status"]:
            fail(f"state write: log/status wrong: {w['log']!r} {w['status']!r}")
        if "calc.py" not in w["diff_stat"] or w["stash"] != []:
            fail(f"state write: diff_stat/stash wrong: {w['diff_stat']!r} {w['stash']!r}")
        ok("state write: log, status, diff stat, stash")
        if "?? pkg/" not in w["status"]:            # from pkg/ git would say "?? ./"
            fail(f"state write: status paths not repo-root-relative: {w['status']!r}")
        ok("state write: status paths are relative to the repo root, not the cwd")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}-\d{6}", w["timestamp"]):
            fail(f"state write: timestamp format {w['timestamp']!r}")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", w["when"]):
            fail(f"state write: when format {w['when']!r}")
        if w["timestamp"][:10] != w["when"][:10]:
            fail("state write: timestamp and when disagree")
        ok("state write: timestamp and When from one clock reading")
        s = w["session"]
        if s != {"full": SID, "short": SID[:8], "fallback": False}:
            fail(f"state write: session {s!r}")
        ok("state write: short id is the first 8 chars of CLAUDE_CODE_SESSION_ID")
        if w["plan_files"] != ["TODO.md"]:
            fail(f"state write: plan_files {w['plan_files']!r}")
        ok("state write: plan/TODO files found at the base dir")

        fb = state("write", cwd=work, sid=None)["session"]
        if not (fb["fallback"] and fb["full"] is None and re.fullmatch(r"[0-9a-f]{8}", fb["short"])):
            fail(f"state write: fallback session {fb!r}")
        ok("state write: random 8-hex fallback id when the env var is unset")

        # handoff files: date-first sort, legacy placed by When:, header parsing
        (work / "2026-08-30-090000-7f2e9a41-HANDOFF.md").write_text(
            _doc("2026-08-30 09:00", "7f2e9a41", head, goal="Ship calc. Then more."))
        (work / "2026-08-30-143000-ca154123-HANDOFF.md").write_text(
            _doc("2026-08-30 14:30", "ca154123", head))           # Quick: no Goal
        (work / "HANDOFF.md").write_text(_doc("2026-08-30 12:00", "-", head, goal="Old."))
        lst = state("list", cwd=work)["handoffs"]
        names = [h["name"] for h in lst]
        if names != ["2026-08-30-143000-ca154123-HANDOFF.md", "HANDOFF.md",
                     "2026-08-30-090000-7f2e9a41-HANDOFF.md"]:
            fail(f"state list: order {names!r}")
        ok("state list: newest first, legacy placed by its When:")
        newest, legacy, oldest = lst
        if not legacy["legacy"] or newest["legacy"]:
            fail("state list: legacy flag wrong")
        if not newest["own"] or oldest["own"]:
            fail("state list: own-session flag wrong")
        ok("state list: legacy and own-session flags")
        if oldest["goal"] != "Ship calc." or newest["goal"] != "(clear) next - do it":
            fail(f"state list: goal {oldest['goal']!r} / {newest['goal']!r}")
        if (oldest["session"], oldest["branch"], oldest["format"], oldest["when"]) != \
                ("7f2e9a41", "main", "handoff/2", "2026-08-30 09:00"):
            fail(f"state list: header parse {oldest!r}")
        if oldest["last_commit"] != head:
            fail(f"state list: last_commit {oldest['last_commit']!r}")
        ok("state list: header fields, Goal sentence, Remaining fallback")

        # resume: target, staleness (current, drift, rewritten), --file
        r = state("resume", cwd=work)
        if r["target"]["name"] != newest["name"] or r["current_branch"] != "main":
            fail(f"state resume: target {r['target']!r}")
        st = r["staleness"]
        if (st["recorded_commit"], st["is_ancestor"], st["drift"]) != (head, True, 0) \
                or not st["latest_commit_date"]:
            fail(f"state resume: fresh staleness {st!r}")
        ok("state resume: newest target, current handoff shows 0 drift")
        git("add", "calc.py", cwd=work); git("commit", "-qm", "caf\u00e9 \u00fc", cwd=work)
        st = state("resume", cwd=work)["staleness"]
        if (st["is_ancestor"], st["drift"]) != (True, 1):
            fail(f"state resume: drift {st!r}")
        ok("state resume: drift counted, non-ASCII subject survives")
        git("checkout", "-q", "--orphan", "other", cwd=work)
        git("commit", "-qm", "rewritten", cwd=work)
        st = state("resume", "--file", oldest["name"], cwd=work)
        if st["target"]["name"] != oldest["name"]:
            fail("state resume: --file not honoured")
        if (st["staleness"]["is_ancestor"], st["staleness"]["drift"]) != (False, None):
            fail(f"state resume: rewritten history {st['staleness']!r}")
        ok("state resume: --file, rewritten history gives no drift count")
    finally:
        shutil.rmtree(work, ignore_errors=True)

    outside = Path(tempfile.mkdtemp())
    try:
        w = state("write", cwd=outside)
        if w["in_git"] or w["branch"] is not None or w["log"] is not None:
            fail(f"state write outside git: {w!r}")
        if Path(w["base_dir"]).resolve() != outside.resolve():
            fail(f"state write outside git: base dir {w['base_dir']!r}")
        r = state("resume", cwd=outside)
        if r["target"] is not None or r["staleness"] is not None:
            fail(f"state resume with no handoffs: {r!r}")
        ok("state: non-git dir and no handoffs handled without errors")
    finally:
        shutil.rmtree(outside, ignore_errors=True)

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
    test_state_script()
    elapsed = time.perf_counter() - t0
    print(f"ALL PASS ({passed} checks, {elapsed:.2f}s)"
          + ("   [run with -v for per-check output]" if not VERBOSE else ""))
    if elapsed > SLOW_BUDGET_S:
        print(f"WARN: fixture took {elapsed:.2f}s (> {SLOW_BUDGET_S:.0f}s budget) "
              "- consider trimming subprocess-heavy layers", file=sys.stderr)
