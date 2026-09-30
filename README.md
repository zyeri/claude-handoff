# claude-handoff

A Claude Code skill for writing, resuming, showing, and listing self-contained **handoff docs** - so any session (yours later, a teammate, or a fresh agent) can pick up work with zero prior context.

## What it does

One skill, four directions:

| Direction | Invoke | What happens |
|-----------|--------|--------------|
| **Write**  | `/handoff` or `/handoff quick` | Reads repo state (branch, log, status, dirty tree) and writes a new `*-HANDOFF.md` file: goal, done, remaining, key files, how to resume, and a **proven** verification command. |
| **Resume** | `/handoff resume` or "read the handoff" | Reads the newest `*-HANDOFF.md`, checks staleness against git, restores the branch, runs the verification, and restates what's left. |
| **Show**   | `/handoff show` or "show me the handoff" | Just renders the doc - no git, no checkout, no verify run. |
| **List**   | `/handoff list` or "list the handoffs" | One row per handoff (file, When, Session, Branch, Goal) so you can pick which to resume. |

Natural-language phrasing routes the same way; see the routing table in `skills/handoff/SKILL.md`.

## Install

This repo is a Claude Code **plugin** (manifest at `.claude-plugin/plugin.json`); the skill is auto-discovered from `skills/handoff/`.

**As a plugin** - add this repo as a plugin marketplace, then install `claude-handoff`:

```
/plugin marketplace add zyeri/claude-handoff
/plugin install claude-handoff@claude-handoff
```

**Or just the skill** - copy (or symlink) the skill directory into your skills path:

```
# copy
cp -r skills/handoff ~/.claude/skills/handoff

# or symlink so edits here stay live (Windows: needs Developer Mode / admin)
ln -s "$PWD/skills/handoff" ~/.claude/skills/handoff
```

## Test

The behaviors the skill depends on are covered by a cross-platform fixture (pure Python + git - runs on Windows, macOS, Linux):

```
python skills/handoff/tests/roundtrip.py
```

It checks three things: (A) the git **mechanics** the skill relies on (date-first sorting, same-second collisions, repo-root lookup from a subdirectory, rewritten-commit detection); (B) that `SKILL.md` still **contains the instructions** those mechanics enforce, each checked in the half (Write or Resume) it governs - so deleting a step from the doc fails the test; and (C) that the routing table, slash command, and this README agree with the skill. Prints `ALL PASS (<n> checks)` on success; `-v` shows each check.

## Design notes

- **Verification is proven, not promised** - the writer runs the verify command before recording it.
- **One new file per write, never overwritten** (`<YYYY-MM-DD-HHMMSS>-<short-session-id>-HANDOFF.md`) so concurrent agents in one directory can't clobber each other; date-first, so alphabetical sort is chronological. Past 3 files the skill suggests removing the oldest; it never deletes them itself.
- **Session-aware** - each handoff records the session that wrote it; resume and show say when a handoff came from another session, so two agents in one repo don't act on each other's work unnoticed.
- **Portable** - handoffs live at the repo root, and paths are relative to it, named by its remote rather than a local absolute path, so a handoff works on another machine or OS.
- **Timestamps come from the clock, not the model** - the filename and `When:` are taken from `date` / `Get-Date` output, because the filename decides which handoff is newest.
- **Rewritten history is detected** - if the recorded commit was rebased or squashed away, resume says so instead of reporting a misleading drift count.
- **Secrets never land in the doc** - referenced by name, since handoffs get shared and committed.
- **Ambiguity is asked, not guessed** - a dirty tree with an existing handoff prompts "resume or write new?" rather than silently picking.

## Upgrading from 0.1.x

0.2.0 stops writing a bare `HANDOFF.md`; every write creates a new dated file instead. A leftover `HANDOFF.md` from 0.1.x is still found by resume, show, and list, which flag it as legacy and offer to rename it to `<timestamp>-legacy-HANDOFF.md`. The rename happens only if you approve. Automatic pruning is gone: the skill suggests which old handoffs to remove and never deletes them itself. See `CHANGELOG.md` for the full list.
