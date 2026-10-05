# Changelog

All notable changes to this project are documented here. Releases follow
[Semantic Versioning](https://semver.org/). The generated handoff file's **document
format** is versioned separately as a plain integer (`Format: handoff/N`), bumped only
when the doc's structure changes - see the "Document format" notes below.

## [0.2.1] - 2026-10-04

Document format unchanged: **handoff/2**.

### Changed
- **Faster to load.** `SKILL.md` is now a router (routing, naming, base dir, Show,
  List); the Write and Resume instructions moved to `write.md` and `resume.md`,
  which the agent reads only for that direction, and their steps now gather state
  through the script below. Per invocation the
  agent now loads about 16 KB for Write, 12 KB for Resume, and 7 KB for Show or
  List, down from 19 KB for every direction.
- **Faster to run.** New read-only `scripts/handoff_state.py` (stdlib only, PEP 723)
  prints one JSON object with everything Write, Resume, and List used to gather
  with separate commands: base dir, branch, log, status, diff stat, stash,
  user.name, remote, timestamp, session id, every handoff with its parsed header,
  and Resume's staleness results. The by-hand commands stay as the fallback when
  no Python is available. The script starts its git calls in parallel, imports
  only what `subprocess` does not already load, runs git with
  `GIT_OPTIONAL_LOCKS=0` so it never rewrites the index, and prints compact JSON.
  Measured on Windows against a 60-commit repo with 13 handoffs: write 98 ms,
  resume 87 ms, list 62 ms per run, against 208, 169, and 76 ms for the first
  draft that ran its git calls one at a time.
- **Verify runs once per write.** The self-audit reruns the verification command
  only when it can see the new handoff file (working-tree or git-status checks, or
  a `*-HANDOFF.md` glob), or when other files changed after step 4.
- The always-loaded skill `description` is shorter (400 characters, from 727),
  keeping every trigger phrase.
- `roundtrip.py` reads the split files, checks the description length budget, and
  adds a layer for the state script.

## [0.2.0] - 2026-09-30

Document format bumped: **handoff/2** - see notes below.

### Changed
- **Breaking: no more bare `HANDOFF.md`.** Every write now creates a new file named
  `<YYYY-MM-DD-HHMMSS>-<short-session-id>-HANDOFF.md` and never overwrites in place -
  this is what makes concurrent agents in the same directory safe. "The handoff"
  (unqualified) now means the newest file matching `*-HANDOFF.md`.
- **No more automatic pruning.** Past 3 handoff files, the writer lists the older ones
  and suggests removing them, but never deletes: an older file may be another
  session's in-flight handoff.
- Header gains a `**Session:**` line (short id, full id, and session name if the
  harness exposes one), populated from `CLAUDE_CODE_SESSION_ID`. Resume and Show now
  compare this against the acting session's own id and warn when a handoff belongs to
  a different session, so an agent doesn't silently act on another agent's in-flight
  work. (`skills/handoff/SKILL.md`, `skills/handoff/tests/roundtrip.py`)
- The filename timestamp, `When:`, and the fallback session id now come from command
  output (`date` / `Get-Date`, `/dev/urandom` / `NewGuid()`), never from the model's
  own sense of time - a guessed timestamp made the wrong file sort as newest.
- `Run everything from:` names the repo by identity (repo name + `git remote get-url
  origin`) instead of the author's absolute path, so a handoff works on another
  machine or OS. Self-audit now checks for leftover local absolute paths.
- Resume checks `git merge-base --is-ancestor` before counting drift. When the
  recorded commit was rebased, squashed, amended, or is missing, it says so and falls
  back to comparing `When:` with the latest commit date, instead of reporting the
  whole rewritten history as drift.
- `commands/handoff.md`, `README.md`, and the marketplace description now describe
  the `*-HANDOFF.md` naming; the fixture fails if a bare `HANDOFF.md` reappears there.
- Handoff files live at the repo root (`git rev-parse --show-toplevel`), not the
  directory the session started in, so a session begun in a subdirectory still finds
  them.
- Resume and Show handle docs missing fields instead of erroring: no `Session:` line
  (`handoff/1`), an unset `CLAUDE_CODE_SESSION_ID`, or no `Branch:` / `Last commit:`
  (written outside git). A session mismatch is reported as information, since
  resuming your own work from a fresh session is the normal case.
- A leftover bare `HANDOFF.md` from before 0.2.0 is found, placed by its `When:`
  line, flagged as legacy, and renamed to `<timestamp>-legacy-HANDOFF.md` only if the
  user approves.
- `Author:` is now `git config user.name` plus the model ("Alex Schmidt via Claude
  Opus") instead of a bare agent name. Not a structural change; still `handoff/2`.

### Added
- **List direction** (`/handoff list`, "list the handoffs"): one row per handoff with
  file, `When`, `Session`, `Branch`, and the goal. Resume refs also accept a session id
  or its prefix (`/handoff resume ca154123`).

- All tracked files are now ASCII-only. The handoff header's field separator is `|`
  instead of a middle dot; the fields themselves are unchanged, so still `handoff/2`,
  and older docs using the middle dot parse the same way.
- README: new "Upgrading from 0.1.x" section and design notes for session stamps,
  repo-root lookup, clock-sourced timestamps, and rewritten-history detection. Plugin
  and marketplace descriptions mention the List direction.

### Tests
- `test_quick_mode` now asserts on SKILL.md's Quick definition instead of a string
  the test built itself, and the dirty-tree guard is checked in the Resume half only;
  both could previously pass with the instruction deleted.

## [0.1.2] - 2026-08-31

### Changed
- Resume format-stamp handling now covers all three mismatch cases: absent (treat as
  `handoff/1`), higher (newer format - parse defensively), and lower (older layout -
  read against that version's structure). Both mismatch clauses point to the CHANGELOG's
  "Document format" notes as the layout record. (`skills/handoff/SKILL.md`)

Document format unchanged (`handoff/1`).

## [0.1.1] - 2026-08-30

### Fixed
- Guard the self-referential verification trap: a recorded verify that checks
  working-tree cleanliness (`git status --short` expecting empty) breaks on resume
  because the freshly written `HANDOFF.md` is untracked. SKILL.md now instructs such
  a verify to exclude `HANDOFF.md` or expect it as the sole untracked entry, and the
  self-audit re-checks the verify after the doc exists. (Reported by a peer session.)

Document format unchanged (`handoff/1`).

## [0.1.0] - 2026-08-30

Initial release.

### Added
- `handoff` skill with three directions: **Write**, **Resume**, **Show** - routed by
  slash arg (`/handoff`, `/handoff resume`, `/handoff show`) or natural-language phrasing.
- Writing: reads repo state (no-git fallback), proves the verification command before
  recording it, date-first archives (keep last 3), secrets guard, self-audit before save.
- Resuming: format-stamp check, staleness guard, dirty-tree-safe branch restore,
  runs the recorded verification, restates remaining work.
- Cross-platform test fixture (`skills/handoff/tests/roundtrip.py`) - git mechanics plus
  skill-text assertions; quiet by default, `-v` for detail.
- Plugin packaging (`.claude-plugin/plugin.json` + `marketplace.json`), MIT license.
  (CI on a Linux/macOS/Windows matrix is prepared but deferred until the publishing
  token carries the `workflow` scope; run the fixture manually meanwhile.)

### Document format
- **handoff/1** - initial layout: header (When/Author/Format, Branch/Last commit,
  Run-everything-from, Resume-with), Goal, Completed, Remaining (confidence-tagged),
  Key files, How to resume, Verification, Watch out.
- **handoff/2** (0.2.0) - adds a `**Session:**` header line (short id, full id,
  session name if available) directly after `When/Author/Format`. All other sections
  unchanged from handoff/1.
