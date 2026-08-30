# claude-handoff

A Claude Code skill for writing, resuming, and showing self-contained **handoff docs** — so any session (yours later, a teammate, or a fresh agent) can pick up work with zero prior context.

## What it does

One skill, three directions:

| Direction | Invoke | What happens |
|-----------|--------|--------------|
| **Write**  | `/handoff` · `/handoff quick` | Reads repo state (branch, log, status, dirty tree) and writes `HANDOFF.md`: goal, done, remaining, key files, how to resume, and a **proven** verification command. |
| **Resume** | `/handoff resume` · "read the handoff" | Reads `HANDOFF.md`, checks staleness against git, restores the branch, runs the verification, and restates what's left. |
| **Show**   | `/handoff show` · "show me the handoff" | Just renders the doc — no git, no checkout, no verify run. |

Natural-language phrasing routes the same way; see the routing table in `skills/handoff/SKILL.md`.

## Install

Symlink (or copy) the skill into your Claude Code skills directory:

```
# copy
cp -r skills/handoff ~/.claude/skills/handoff

# or symlink so edits here stay live (Windows: needs Developer Mode / admin)
ln -s "$PWD/skills/handoff" ~/.claude/skills/handoff
```

## Test

The behaviors the skill depends on are covered by a cross-platform fixture (pure Python + git — runs on Windows, macOS, Linux):

```
python skills/handoff/tests/roundtrip.py
```

It checks two things: (A) the git **mechanics** both directions rely on, and (B) that `SKILL.md` still **contains the instructions** those mechanics enforce — so deleting a step from the doc fails the test. Prints `ALL PASS (<n> checks)` on success.

## Design notes

- **Verification is proven, not promised** — the writer runs the verify command before recording it.
- **Archives are date-first** (`YYYY-MM-DD-HHMM-HANDOFF.md`) so alphabetical sort is chronological; only the last 3 are kept.
- **Secrets never land in the doc** — referenced by name, since handoffs get shared and committed.
- **Ambiguity is asked, not guessed** — a dirty tree with an existing handoff prompts "resume or write new?" rather than silently picking.
