# Writing a handoff

## Modes

- **Full** (default) - the complete template below. End-of-session, real handoff, anything non-trivial.
- **Quick** (`/handoff quick`, or a short pause) - only the header block, `Remaining`, and `Verification`.

## Audience

Tune detail to who reads it (ask if unclear):

- **For a fresh agent** (default) - exact commands and `file:line` refs; assume no memory.
- **For a teammate** - include the *why* and tradeoffs; they fill gaps a machine can't.

## Steps

1. **Gather state from the repo, not memory.** Run `handoff_state.py write` (see "Gather state in one call" in `SKILL.md`): one call returns `in_git`, branch, log, status, diff stat, stash, `user_name`, `remote`, `plan_files`, the step 3 `timestamp`/`when` and `session`, and the existing `handoffs`. Draft from that output. Only if the script can't run, gather by hand: first check `git rev-parse --is-inside-work-tree`.
   - **In a git repo** - run these and draft from the real output:
     - `git branch --show-current`
     - `git log --oneline -20`
     - `git status --short`
     - `git diff --stat`
     - `git stash list` and untracked files - see the next step.
   - **Not a git repo** - skip the git commands (don't let them error). Draft from the filesystem: recently modified files; omit the `Branch:`/`Last commit:` header lines. Say in the doc that it's not version-controlled.
   - Either way, read any plan/TODO/spec file present (e.g. `PLAN.md`, `TASK_LIST.md`, `TODO.md`).
2. **Handle uncommitted work explicitly.** A dirty tree loses context on resume. If `git status` shows changes, tell the reader what to do: commit them, stash them (and note the stash), or list exactly which files are mid-edit and why. Never leave "you have local changes" unexplained.
3. **Name the file - never overwrite in place.** Every write creates a new file; nothing is ever clobbered, which is what makes concurrent agents safe. Format: `<YYYY-MM-DD-HHMMSS>-<short-session-id>-HANDOFF.md` - date-first so alphabetical sort is chronological, seconds plus the session id so two agents writing in the same second never collide. Get both parts from command output, never from your own sense of the time - the filename is the sort key, so an invented timestamp makes the wrong file "the newest". The step 1 script output already carries both (`timestamp` and `when` from one clock reading, `session.short` with `fallback: true` when it had to generate one); the commands below are the by-hand equivalent:
   - Timestamp: `date +%Y-%m-%d-%H%M%S` (bash/zsh) or `Get-Date -Format yyyy-MM-dd-HHmmss` (PowerShell; `MM` is month, `mm` is minutes). Use the same run for the header's `When:` line.
   - `<short-session-id>`: the first 8 characters of the `CLAUDE_CODE_SESSION_ID` environment variable. If that variable is unset (no session id exposed in this harness), generate one - `od -An -N4 -tx1 /dev/urandom | tr -d ' \n'` (bash/zsh) or `[guid]::NewGuid().ToString('N').Substring(0,8)` (PowerShell) - and note the fallback in `Watch out`.

   Example: `2026-09-03-153042-ca154123-HANDOFF.md`. After writing, if more than 3 `*-HANDOFF.md` files exist, list the ones older than the newest 3 and suggest the user remove them - never delete them yourself. An older file may be another session's in-flight handoff, and deleting it is exactly the clobbering this naming scheme prevents.
4. **Prove the verification command works.** Actually run the command you plan to record. Only record it if it passes now - a verify command that doesn't work defeats the section. If nothing passes yet, say so ("tests red - expected until X").
5. **Write the file in the base dir** (repo root - see Base dir in `SKILL.md`; name from step 3) using the template below.
6. **Self-audit before finishing** - run the same checks a resume would, against what you wrote:
   - Does the `Verification` command still pass now that the handoff file exists? Rerun it only if it can see the new file: it inspects working-tree state (git status, git diff, a clean-tree check) or globs `*-HANDOFF.md`. A git-status/clean-tree check will now see the untracked handoff file; exclude it or expect it as the sole untracked entry (see the Verification rule below). Otherwise reuse the step 4 result - no need to run a test suite twice - provided nothing but the handoff file changed since step 4; if anything else changed, rerun.
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
