---
name: handoff
description: Write, resume, show, or list self-contained, session-stamped handoff docs (dated `*-HANDOFF.md` files, safe for concurrent agents). Use for writing - "create/write/make a handoff", wrap up, pause, hand off; resuming - "read the handoff", resume, pick up, continue, "where were we"; showing - "show me/print/display the handoff"; listing - "list the handoffs", "which handoffs are there".
---

# Handoff

One skill, four directions. Route by intent - from the slash arg if given, else the natural-language phrasing:

| Direction | Slash arg | Phrasings that mean this |
|-----------|-----------|--------------------------|
| **Write** (Full) | `/handoff` | "create/write/make a handoff", "wrap up", "hand this off", "pause here" |
| **Write** (Quick) | `/handoff quick` | "quick handoff", "jot a handoff" |
| **Resume** | `/handoff resume` | "read the handoff", "resume", "pick up where we left off", "continue", "where were we" |
| **Resume** (specific) | `/handoff resume <file>` | "resume yesterday's", "read the handoff from <date/file>" |
| **Show** | `/handoff show` | "show me the handoff", "print/display the handoff", "just show the handoff" |
| **List** | `/handoff list` | "list the handoffs", "which handoffs are there" |

**Show** vs **Resume:** Show only renders the handoff file - no git, no checkout, no verify run - for when the user wants to *see* the doc. Resume does the heavyweight restore (checkout, verify, restate). The split hinges on the verb: **"read the handoff" means Resume** (act on it - reading a handoff is *for* resuming); **"show/display/print the handoff" means Show** (just look). When unsure which, prefer Resume and say you're doing the full restore, so the user can stop you if they only wanted to look.

**Every handoff is a dated, session-stamped file - this skill never writes a bare `HANDOFF.md`.** Filenames are `<YYYY-MM-DD-HHMMSS>-<short-session-id>-HANDOFF.md` (e.g. `2026-09-03-153042-ca154123-HANDOFF.md`); see step 3 in `write.md`. "The handoff" (unqualified) means the newest file matching `*-HANDOFF.md` in the base dir.

**Base dir.** Handoff files live in, and are looked up from, the base dir: the repo root when inside git (`git rev-parse --show-toplevel`), else the current directory. A session started in a subdirectory still reads and writes the root's handoffs, so the next session finds them.

**Default when nothing disambiguates** (bare request, no verb, no clear phrasing):
- No file matches `*-HANDOFF.md` and there is no legacy bare `HANDOFF.md` -> **write, Full**.
- Only a legacy bare `HANDOFF.md` exists (left by a pre-0.2.0 version) -> treat it as a match; Resume step 1 (`resume.md`) flags it and offers the rename.
- A match exists + **clean** working tree -> **resume** the newest match (nothing local to lose; continuing is the obvious intent).
- A match exists + **dirty** working tree -> **ask**: "Resume the existing handoff, or write a new one covering your current changes?" Never guess here - the dirty tree could be work the old handoff documents, or new work that wants its own handoff.
- If the newest match's session id (parsed from its `**Session:**` header line) differs from this session's own `CLAUDE_CODE_SESSION_ID`, say so before resuming/showing it - see Resume step 2 (`resume.md`) for the wording and for docs with no `Session:` line.

### For specific/date-relative resume (`/handoff resume <ref>`)
`<ref>` may be a filename or a relative phrase. Resolve against `*-HANDOFF.md` files (names are date-first, so they sort chronologically):
- exact filename -> that file
- "yesterday's" / "last / previous" -> the newest file strictly before today (or the 2nd-newest if the newest is from today)
- a date like "2026-08-29" -> the file(s) whose prefix matches; if more than one session wrote that day, list them and ask which
- a session id or its prefix like "ca154123" / "ca15" -> the file whose session id (the segment between the timestamp and `-HANDOFF.md`) starts with it - never a match inside the timestamp digits. If more than one file matches, list them and ask.
If nothing matches, list the files and ask.

## Load your direction

Write and Resume keep their instructions in their own files, next to this one in the skill's base directory (shown when the skill loads). Read the one you need before acting:

- **Write** -> `write.md`
- **Resume** -> `resume.md`
- **Show** and **List** -> below, no extra file.

**Gather state in one call.** `scripts/handoff_state.py` (in the skill's base directory) prints, as one JSON object, everything a direction would otherwise collect with separate commands: base dir, git state, session id, timestamp, and every handoff file with its parsed header. It is read-only and never runs a verification. Run it from the base dir (or any directory inside the repo) with `uv run --no-project --script "<skill dir>/scripts/handoff_state.py" <write|resume|list>`, where `<skill dir>` is the "Base directory for this skill" printed when the skill loaded - keep the quotes, since on Windows it is a backslash path; without uv, use `python3` (or `python`) in place of `uv run --no-project --script`. If no Python works, fall back to the individual commands each direction file lists.

---

# Showing a handoff

Just render the doc - the reader wants to *look*, not act. No git, no checkout, no verify run.

1. Read the file named/implied, or the newest `*-HANDOFF.md` in the base dir if unspecified (the first entry of `handoff_state.py list` output, which also carries its `own` flag for step 2). Include a legacy bare `HANDOFF.md` as a candidate the same way Resume step 1 (`resume.md`) does, without renaming it. If none match, list any candidates.
2. Print it as-is. Optionally add a one-line staleness note if the `When:` date is clearly old, or a one-line note if its `Session:` id differs from this session's own - but take no action.
3. If the reader then wants to act, they'll say "resume" / "pick up" - hand off to the Resume direction.

---

# Listing handoffs

For `/handoff list` or "which handoffs are there": a table of every handoff in the base dir, so the reader can pick one without opening each file. No git, no checkout, no verify run.

1. Run `handoff_state.py list`: `handoffs` arrives sorted newest first (legacy file included, placed by its `When:`), with each header parsed, `goal` already reduced to the row summary, and `own` marking this session's files - no need to open any file. Without the script: glob `*-HANDOFF.md` in the base dir, plus a legacy bare `HANDOFF.md` if present, and sort newest first.
2. Without the script, read only each file's header and `## Goal`. Print one row per file: filename, `When`, `Session` (short id, or "none" for pre-session docs), `Branch`, and the first sentence of `Goal` (Quick docs have no `Goal`; use the first `Remaining` item instead). Mark this session's own files and the legacy file.
3. End with how to pick one: `/handoff resume <filename>` or `/handoff resume <session-id>`.
