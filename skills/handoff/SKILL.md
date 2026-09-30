---
name: handoff
description: Write, resume, show, or list self-contained, session-stamped handoff docs (a dated `*-HANDOFF.md` file, safe for multiple concurrent agents in the same directory). Triggers on writing intents - "create/write/make a handoff", wrap up, pause, hand off - on resuming intents - "read the handoff", resume, pick up, continue, "where were we" - on show intents - "show me/print/display the handoff" - and on list intents - "list the handoffs", "which handoffs are there". Writing summarizes done/remaining/key-files/how-to-resume; resuming reads the newest matching handoff file, restores context, runs the verification, and restates what's left; showing just renders it; listing prints one row per handoff to pick from.
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

**Every handoff is a dated, session-stamped file - this skill never writes a bare `HANDOFF.md`.** Filenames are `<YYYY-MM-DD-HHMMSS>-<short-session-id>-HANDOFF.md` (e.g. `2026-09-03-153042-ca154123-HANDOFF.md`); see step 3 under Writing. "The handoff" (unqualified) means the newest file matching `*-HANDOFF.md` in the base dir.

**Base dir.** Handoff files live in, and are looked up from, the base dir: the repo root when inside git (`git rev-parse --show-toplevel`), else the current directory. A session started in a subdirectory still reads and writes the root's handoffs, so the next session finds them.

**Default when nothing disambiguates** (bare request, no verb, no clear phrasing):
- No file matches `*-HANDOFF.md` and there is no legacy bare `HANDOFF.md` -> **write, Full**.
- Only a legacy bare `HANDOFF.md` exists (left by a pre-0.2.0 version) -> treat it as a match; Resume step 1 flags it and offers the rename.
- A match exists + **clean** working tree -> **resume** the newest match (nothing local to lose; continuing is the obvious intent).
- A match exists + **dirty** working tree -> **ask**: "Resume the existing handoff, or write a new one covering your current changes?" Never guess here - the dirty tree could be work the old handoff documents, or new work that wants its own handoff.
- If the newest match's session id (parsed from its `**Session:**` header line) differs from this session's own `CLAUDE_CODE_SESSION_ID`, say so before resuming/showing it - see Resume step 2 for the wording and for docs with no `Session:` line.

### For specific/date-relative resume (`/handoff resume <ref>`)
`<ref>` may be a filename or a relative phrase. Resolve against `*-HANDOFF.md` files (names are date-first, so they sort chronologically):
- exact filename -> that file
- "yesterday's" / "last / previous" -> the newest file strictly before today (or the 2nd-newest if the newest is from today)
- a date like "2026-08-29" -> the file(s) whose prefix matches; if more than one session wrote that day, list them and ask which
- a session id or its prefix like "ca154123" / "ca15" -> the file whose session id (the segment between the timestamp and `-HANDOFF.md`) starts with it - never a match inside the timestamp digits. If more than one file matches, list them and ask.
If nothing matches, list the files and ask.

---

# Writing a handoff

## Modes

- **Full** (default) - the complete template below. End-of-session, real handoff, anything non-trivial.
- **Quick** (`/handoff quick`, or a short pause) - only the header block, `Remaining`, and `Verification`.

## Audience

Tune detail to who reads it (ask if unclear):

- **For a fresh agent** (default) - exact commands and `file:line` refs; assume no memory.
- **For a teammate** - include the *why* and tradeoffs; they fill gaps a machine can't.

## Steps

1. **Gather state from the repo, not memory.** First check `git rev-parse --is-inside-work-tree`.
   - **In a git repo** - run these and draft from the real output:
     - `git branch --show-current`
     - `git log --oneline -20`
     - `git status --short`
     - `git diff --stat`
     - `git stash list` and untracked files - see the next step.
   - **Not a git repo** - skip the git commands (don't let them error). Draft from the filesystem: recently modified files; omit the `Branch:`/`Last commit:` header lines. Say in the doc that it's not version-controlled.
   - Either way, read any plan/TODO/spec file present (e.g. `PLAN.md`, `TASK_LIST.md`, `TODO.md`).
2. **Handle uncommitted work explicitly.** A dirty tree loses context on resume. If `git status` shows changes, tell the reader what to do: commit them, stash them (and note the stash), or list exactly which files are mid-edit and why. Never leave "you have local changes" unexplained.
3. **Name the file - never overwrite in place.** Every write creates a new file; nothing is ever clobbered, which is what makes concurrent agents safe. Format: `<YYYY-MM-DD-HHMMSS>-<short-session-id>-HANDOFF.md` - date-first so alphabetical sort is chronological, seconds plus the session id so two agents writing in the same second never collide. Get both parts from command output, never from your own sense of the time - the filename is the sort key, so an invented timestamp makes the wrong file "the newest":
   - Timestamp: `date +%Y-%m-%d-%H%M%S` (bash/zsh) or `Get-Date -Format yyyy-MM-dd-HHmmss` (PowerShell; `MM` is month, `mm` is minutes). Use the same run for the header's `When:` line.
   - `<short-session-id>`: the first 8 characters of the `CLAUDE_CODE_SESSION_ID` environment variable. If that variable is unset (no session id exposed in this harness), generate one - `od -An -N4 -tx1 /dev/urandom | tr -d ' \n'` (bash/zsh) or `[guid]::NewGuid().ToString('N').Substring(0,8)` (PowerShell) - and note the fallback in `Watch out`.

   Example: `2026-09-03-153042-ca154123-HANDOFF.md`. After writing, if more than 3 `*-HANDOFF.md` files exist, list the ones older than the newest 3 and suggest the user remove them - never delete them yourself. An older file may be another session's in-flight handoff, and deleting it is exactly the clobbering this naming scheme prevents.
4. **Prove the verification command works.** Actually run the command you plan to record. Only record it if it passes now - a verify command that doesn't work defeats the section. If nothing passes yet, say so ("tests red - expected until X").
5. **Write the file in the base dir** (repo root - see Base dir above; name from step 3) using the template below.
6. **Self-audit before finishing** - run the same checks a resume would, against what you wrote:
   - Does the `Verification` command actually pass right now (the exact command recorded) - including now that the handoff file exists? A git-status/clean-tree check will now see the untracked handoff file; exclude it or expect it as the sole untracked entry (see the Verification rule below).
   - Is every path relative to the stated base dir, and does each one exist? Is there no absolute path from this machine anywhere in the doc (header, `How to resume`, `Watch out`)?
   - Does `Branch:`/`Last commit:` match `git` right now?
   - Does the `Session:` line's id match `CLAUDE_CODE_SESSION_ID` right now (or the fallback, if noted)?
   - Did the filename timestamp and `When:` come from a command run in this turn (step 3), not from memory?
   Fix anything that fails before saving - don't ship a handoff that wouldn't survive its own resume.
7. **Confirm** the path written and name any open decisions the reader must make.

## Template

```markdown
# Handoff - <project/task name>

<!-- Reader starts here: where am I, what do I run -->
- **When:** <YYYY-MM-DD HH:MM> | **Author:** <git config user.name> via <model name> | **Format:** handoff/2
- **Session:** <short-session-id> (full: <full-session-id>)<| session name, if the harness exposes one>
- **Branch:** `<branch>` | **Last commit:** `<hash> <subject>`
- **Run everything from:** `<repo-name>` repo root (your clone of <output of git remote get-url origin, or "no remote">) - every command and path below is relative to here.
- **Resume with:** `<the one command to get going>`

## Goal
One or two sentences: what this work is trying to achieve.

## Completed
- [x] <task> - <what changed, where>

## Remaining
<!-- For 2+ parallel threads, group under ### <workstream> headings -->
<!-- Tag each with confidence: (clear) known path | (fuzzy) needs investigation | (blocked) waiting on X -->
- [ ] (clear) <task> - <first concrete action>
- [ ] (fuzzy) <task> - <what's unknown, where to start digging>

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
- Concrete over vague: real paths, real commands, real line numbers - not "the auth file."
- **One base dir.** State the repo root once in the header; make every command and path relative to it - never the author's cwd. A handoff travels (gist, another machine, another OS); `cd rttest` works from one place, `src/calc.py` works from the root anywhere. Name the root by identity - the repo name plus `git remote get-url origin` - not by this machine's absolute path: `C:\Users\me\projects\app` is dead on the reader's Mac. `How to resume` step 1 is "from your clone of the repo", never a `cd` to a local path.
- Every remaining task starts with one doable action.
- `Verification` is required and gets its own section - the highest-value line in the doc. Never record a verify command you haven't run.
- **Guard the self-referential trap.** If the verify command inspects working-tree cleanliness (e.g. `git status --short` expecting empty output), it must account for the handoff file itself: once written it appears as an untracked `?? <name>-HANDOFF.md` (unless git-ignored) and a naive clean-tree check flips to dirty on resume. Either exclude it (`git status --short -- . ':!*-HANDOFF.md'`), or record the expected result as "the only working-tree entry is this handoff file, untracked - no other changes." This bites doc-only / pre-code repos, where a git-status check is the natural verification.
- Pad every table so the pipes align in the raw source (table alignment, not just column alignment) - the `Key files` table above shows the target.
- **Never write secret-shaped strings** into the doc - API keys, tokens, passwords, `.env` values, connection strings. Reference them by name ("`POSTMARK_TOKEN` - ask team lead"). Handoffs get shared, committed, and gisted.
- **Format stamp.** The header carries `Format: handoff/2`. This integer versions the *document layout*, not the plugin release. Stamp the current value verbatim. Bump it (and record the change in `CHANGELOG.md`) ONLY when you change the handoff doc's structure - rename/add/remove a section or header field. The number lives here, next to the template it stamps, so the two cannot drift.
- **Author names the human.** Fill it from `git config user.name` plus the model, e.g. "Alex Schmidt via Claude Opus". `Session:` already identifies the agent; `Author:` tells a teammate whom to ask. Outside git or with no user.name set, use just the model name.
- **Session line exists for disambiguation, not just identity.** When multiple agents work the same directory, the `Session:` line plus the filename's timestamp+id are what let a reader (or a resuming agent) tell handoffs apart and avoid mixing up whose work is whose. Always populate it from the real environment value - never invent an id.

---

# Resuming from a handoff

## Steps

1. **Find and read the handoff.** Glob `*-HANDOFF.md` in the base dir; the newest by filename (date-first, so alphabetical sort is chronological) is "the handoff" unless a specific ref was given. If nothing matches, list any candidates and ask which to use.
   - **Legacy bare `HANDOFF.md`.** The glob never matches a bare `HANDOFF.md` left by a pre-0.2.0 version, so check for one separately. If it exists, place it among the candidates by its `When:` line - it may be newer than every dated file. Say it is a legacy `handoff/1` doc, and offer to rename it to `<YYYY-MM-DD-HHMMSS>-legacy-HANDOFF.md` (timestamp from its `When:`, seconds `00`) so future globs find it. Rename only if the user approves.
2. **Check whose session it is.** Parse the header's `Session:` line and compare its short id to this session's own `CLAUDE_CODE_SESSION_ID`.
   - **They match:** say nothing and continue.
   - **They differ:** say so as information, not alarm - "this handoff was written by a different session (<id>); if that session is still running, coordinate before touching the same files." Resuming your own earlier work from a fresh session is the normal case, so don't treat a mismatch as an error.
   - **The doc has no `Session:` line** (a `handoff/1` doc): skip the comparison and say the doc predates session stamps.
   - **`CLAUDE_CODE_SESSION_ID` is unset** in this harness: skip the comparison and say you can't tell whose session wrote it.
3. **Check the format stamp.** Read the header's `Format: handoff/N`. This skill writes `handoff/2`. If the line is **absent**, treat the doc as `handoff/1` (pre-versioning) and proceed. If `N` is **higher** than what this skill writes, warn that the doc was written by a newer handoff format and some fields may have moved - parse defensively rather than trusting positions. If `N` is **lower**, the doc uses an older layout - read it against that older format's structure (fields may be named or positioned differently from the current template) rather than assuming the current one. Either way, the CHANGELOG's "Document format" notes record each version's layout - consult them when `N` differs from what this skill writes.
   If the doc has **no `Branch:` / `Last commit:` lines** (written outside git), skip steps 4 and 5 and say so. If the base dir is a git repo now, note that the handoff predates version control and check files by existence instead.
4. **Check staleness.** First run `git merge-base --is-ancestor <Last commit hash> HEAD`.
   - **Exit 0** (the recorded commit is in this branch's history): count the commits since it with `git log --oneline <hash>..HEAD`. If any landed after the handoff was written, warn loudly - the doc describes a *past* state and its Completed/Remaining lists may be wrong. Report how many commits diverged before doing anything else.
   - **Any other exit** (1 = history was rebased, squashed, or amended; 128 = the object is gone, e.g. a fresh clone): say "the recorded commit is not in this branch's history (rebased/squashed/rewritten)" and do not report a drift count - `<hash>..HEAD` would count the whole rewritten history. Instead compare the handoff's `When:` against `git log -1 --format=%ci`; if the latest commit is newer, treat the handoff as stale.
5. **Restore the branch.** From the header's `Branch:` line: if already on it, skip. Otherwise check `git status --short` first - a dirty tree makes `git checkout` fail or silently no-op. If dirty, stop and tell the reader to commit/stash before switching; don't assume the switch happened. Report if the branch is missing or diverged from the `Last commit` hash.
6. **Run the verification command.** Execute the `Verification` section's command from the stated base dir. Report pass/fail against its expected result - the fastest proof the work is in the state the handoff claims.
7. **Restate status.** Summarize back to the reader:
   - What's done (from `Completed`).
   - The remaining tasks, with the **first one's first concrete action** called out as the next move; lead with `(clear)` items, flag `(blocked)` ones.
   - Anything from `Watch out` that affects the next step.
8. **Flag drift.** If repo reality contradicts the handoff (branch gone, recorded commit gone from history, verification fails, files named don't exist), say so plainly instead of proceeding - a stale handoff is worse than none.

## Rules

- Verify against the repo; don't just parrot the handoff back. The doc reflects when it was written, not necessarily now.
- End with exactly one next action the reader can take immediately.
- Don't start the remaining work unless the reader asks - resume means restore context, then hand back control.

---

# Showing a handoff

Just render the doc - the reader wants to *look*, not act. No git, no checkout, no verify run.

1. Read the file named/implied, or the newest `*-HANDOFF.md` in the base dir if unspecified. Include a legacy bare `HANDOFF.md` as a candidate the same way Resume step 1 does, without renaming it. If none match, list any candidates.
2. Print it as-is. Optionally add a one-line staleness note if the `When:` date is clearly old, or a one-line note if its `Session:` id differs from this session's own - but take no action.
3. If the reader then wants to act, they'll say "resume" / "pick up" - hand off to the Resume direction.

---

# Listing handoffs

For `/handoff list` or "which handoffs are there": a table of every handoff in the base dir, so the reader can pick one without opening each file. No git, no checkout, no verify run.

1. Glob `*-HANDOFF.md` in the base dir, plus a legacy bare `HANDOFF.md` if present. Sort newest first.
2. Read only each file's header and `## Goal`. Print one row per file: filename, `When`, `Session` (short id, or "none" for pre-session docs), `Branch`, and the first sentence of `Goal` (Quick docs have no `Goal`; use the first `Remaining` item instead). Mark this session's own files and the legacy file.
3. End with how to pick one: `/handoff resume <filename>` or `/handoff resume <session-id>`.
