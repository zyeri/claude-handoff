---
name: handoff
description: Write, resume, or show a self-contained handoff doc (HANDOFF.md). Triggers on writing intents — "create/write/make a handoff", wrap up, pause, hand off — on resuming intents — "read the handoff", resume, pick up, continue, "where were we" — and on show intents — "show me/print/display the handoff". Writing summarizes done/remaining/key-files/how-to-resume; resuming reads HANDOFF.md, restores context, runs the verification, and restates what's left; showing just renders it.
---

# Handoff

One skill, two directions. Route by intent — from the slash arg if given, else the natural-language phrasing:

| Direction | Slash arg | Phrasings that mean this |
|-----------|-----------|--------------------------|
| **Write** (Full) | `/handoff` | "create/write/make a handoff", "wrap up", "hand this off", "pause here" |
| **Write** (Quick) | `/handoff quick` | "quick handoff", "jot a handoff" |
| **Resume** | `/handoff resume` | "read the handoff", "resume", "pick up where we left off", "continue", "where were we" |
| **Resume** (specific) | `/handoff resume <file>` | "resume yesterday's", "read the handoff from <date/file>" |
| **Show** | `/handoff show` | "show me the handoff", "print/display the handoff", "just show the handoff" |

**Show** vs **Resume:** Show only renders `HANDOFF.md` — no git, no checkout, no verify run — for when the user wants to *see* the doc. Resume does the heavyweight restore (checkout, verify, restate). The split hinges on the verb: **"read the handoff" means Resume** (act on it — reading a handoff is *for* resuming); **"show/display/print the handoff" means Show** (just look). When unsure which, prefer Resume and say you're doing the full restore, so the user can stop you if they only wanted to look.

**Default when nothing disambiguates** (bare request, no verb, no clear phrasing):
- No `HANDOFF.md` present → **write, Full**.
- `HANDOFF.md` present + **clean** working tree → **resume** (nothing local to lose; continuing is the obvious intent).
- `HANDOFF.md` present + **dirty** working tree → **ask**: "Resume the existing handoff, or write a new one covering your current changes?" Never guess here — the dirty tree could be work the old handoff documents, or new work that wants its own handoff.

### For specific/date-relative resume (`/handoff resume <ref>`)
`<ref>` may be a filename or a relative phrase. Resolve against `*-HANDOFF.md` archives (names are date-first, so they sort chronologically):
- exact filename → that file
- "yesterday's" / "last / previous" → the newest archive strictly before today (or the 2nd-newest if `HANDOFF.md` is today's)
- a date like "2026-08-29" → the archive whose prefix matches
If nothing matches, list the archives and ask.

---

# Writing a handoff

## Modes

- **Full** (default) — the complete template below. End-of-session, real handoff, anything non-trivial.
- **Quick** (`/handoff quick`, or a short pause) — only the header block, `Remaining`, and `Verification`.

## Audience

Tune detail to who reads it (ask if unclear):

- **For a fresh agent** (default) — exact commands and `file:line` refs; assume no memory.
- **For a teammate** — include the *why* and tradeoffs; they fill gaps a machine can't.

## Steps

1. **Gather state from the repo, not memory.** First check `git rev-parse --is-inside-work-tree`.
   - **In a git repo** — run these and draft from the real output:
     - `git branch --show-current`
     - `git log --oneline -20`
     - `git status --short`
     - `git diff --stat`
     - `git stash list` and untracked files — see the next step.
   - **Not a git repo** — skip the git commands (don't let them error). Draft from the filesystem: recently modified files; omit the `Branch:`/`Last commit:` header lines. Say in the doc that it's not version-controlled.
   - Either way, read any plan/TODO/spec file present (e.g. `PLAN.md`, `TASK_LIST.md`, `TODO.md`).
2. **Handle uncommitted work explicitly.** A dirty tree loses context on resume. If `git status` shows changes, tell the reader what to do: commit them, stash them (and note the stash), or list exactly which files are mid-edit and why. Never leave "you have local changes" unexplained.
3. **Don't clobber an existing handoff.** If `HANDOFF.md` already exists, archive it first, then write anew. Name the archive **date-first** so alphabetical sort is chronological: `<YYYY-MM-DD-HHMM>-HANDOFF.md` (e.g. `2026-08-30-1430-HANDOFF.md`). Then prune: keep only the 3 most recent `*-HANDOFF.md` archives.
4. **Prove the verification command works.** Actually run the command you plan to record. Only record it if it passes now — a verify command that doesn't work defeats the section. If nothing passes yet, say so ("tests red — expected until X").
5. **Write `HANDOFF.md`** using the template below.
6. **Self-audit before finishing** — run the same checks a resume would, against what you wrote:
   - Does the `Verification` command actually pass right now (the exact command recorded)?
   - Is every path relative to the stated base dir, and does each one exist?
   - Does `Branch:`/`Last commit:` match `git` right now?
   Fix anything that fails before saving — don't ship a handoff that wouldn't survive its own resume.
7. **Confirm** the path written and name any open decisions the reader must make.

## Template

```markdown
# Handoff — <project/task name>

<!-- Reader starts here: where am I, what do I run -->
- **When:** <YYYY-MM-DD HH:MM> · **Author:** <name/agent> · **Format:** handoff/1
- **Branch:** `<branch>` · **Last commit:** `<hash> <subject>`
- **Run everything from:** `<repo root, e.g. the dir containing .git>` — every command and path below is relative to here.
- **Resume with:** `<the one command to get going>`

## Goal
One or two sentences: what this work is trying to achieve.

## Completed
- [x] <task> — <what changed, where>

## Remaining
<!-- For 2+ parallel threads, group under ### <workstream> headings -->
<!-- Tag each with confidence: (clear) known path · (fuzzy) needs investigation · (blocked) waiting on X -->
- [ ] (clear) <task> — <first concrete action>
- [ ] (fuzzy) <task> — <what's unknown, where to start digging>

## Key files
| Path             | Role                            |
|------------------|---------------------------------|
| `path/to/file`   | what it does / why it matters   |

## How to resume
1. <first command or action to run>
2. <next step>

## Verification
The one command that proves nothing is broken, and its expected result:
```
<command>          # expected: <what a passing run looks like>
```

## Watch out
- <non-obvious traps, env setup, credentials, quirks>
- <decisions the next person must make before proceeding>
```

## Rules

- Self-contained: no reference to this conversation or context the reader can't see.
- Concrete over vague: real paths, real commands, real line numbers — not "the auth file."
- **One base dir.** State the repo root once in the header; make every command and path relative to it — never the author's cwd. A handoff travels (gist, another machine); `cd rttest` works from one place, `src/calc.py` works from the root anywhere.
- Every remaining task starts with one doable action.
- `Verification` is required and gets its own section — the highest-value line in the doc. Never record a verify command you haven't run.
- Pad every table so the pipes align in the raw source (table alignment, not just column alignment) — the `Key files` table above shows the target.
- **Never write secret-shaped strings** into the doc — API keys, tokens, passwords, `.env` values, connection strings. Reference them by name ("`POSTMARK_TOKEN` — ask team lead"). Handoffs get shared, committed, and gisted.
- **Format stamp.** The header carries `Format: handoff/1`. This integer versions the *document layout*, not the plugin release. Stamp the current value verbatim. Bump it (and record the change in `CHANGELOG.md`) ONLY when you change the HANDOFF.md structure — rename/add/remove a section or header field. The number lives here, next to the template it stamps, so the two cannot drift.

---

# Resuming from a handoff

## Steps

1. **Find and read the handoff.** Read `HANDOFF.md` in the working directory. If it's missing, list any `*-HANDOFF.md` archives (date-first, so the last one alphabetically is newest) and ask which to use.
2. **Check the format stamp.** Read the header's `Format: handoff/N`. This skill writes `handoff/1`. If the line is **absent**, treat the doc as `handoff/1` (pre-versioning) and proceed. If `N` is **higher** than 1, warn that the doc was written by a newer handoff format and some fields may have moved — parse defensively rather than trusting positions.
3. **Check staleness.** Compare the handoff's `When:` timestamp and `Last commit` hash against `git log --oneline -5`. If commits landed after the handoff was written, warn loudly — the doc describes a *past* state and its Completed/Remaining lists may be wrong. Report how many commits diverged before doing anything else.
4. **Restore the branch.** From the header's `Branch:` line: if already on it, skip. Otherwise check `git status --short` first — a dirty tree makes `git checkout` fail or silently no-op. If dirty, stop and tell the reader to commit/stash before switching; don't assume the switch happened. Report if the branch is missing or diverged from the `Last commit` hash.
5. **Run the verification command.** Execute the `Verification` section's command from the stated base dir. Report pass/fail against its expected result — the fastest proof the work is in the state the handoff claims.
6. **Restate status.** Summarize back to the reader:
   - What's done (from `Completed`).
   - The remaining tasks, with the **first one's first concrete action** called out as the next move; lead with `(clear)` items, flag `(blocked)` ones.
   - Anything from `Watch out` that affects the next step.
7. **Flag drift.** If repo reality contradicts the handoff (branch gone, verification fails, files named don't exist), say so plainly instead of proceeding — a stale handoff is worse than none.

## Rules

- Verify against the repo; don't just parrot the handoff back. The doc reflects when it was written, not necessarily now.
- End with exactly one next action the reader can take immediately.
- Don't start the remaining work unless the reader asks — resume means restore context, then hand back control.

---

# Showing a handoff

Just render the doc — the reader wants to *look*, not act. No git, no checkout, no verify run.

1. Read `HANDOFF.md` (or the archive named/implied). If missing, list `*-HANDOFF.md` archives.
2. Print it as-is. Optionally add a one-line staleness note if the `When:` date is clearly old — but take no action.
3. If the reader then wants to act, they'll say "resume" / "pick up" — hand off to the Resume direction.
