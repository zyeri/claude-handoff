---
name: handoff
description: Write, resume, or show a self-contained handoff doc (HANDOFF.md).
argument-hint: "[quick | resume [<file>] | show]"
---

Use the **handoff** skill, routing by the argument below (natural-language requests
like "resume the handoff" or "show me the handoff" reach the same skill directly):

- empty          -> **Write** a new handoff (Full mode)
- `quick`        -> **Write** in Quick mode (header + Remaining + Verification)
- `resume`       -> **Resume**: read `HANDOFF.md`, check the format stamp and staleness,
                    restore the branch, run the verification, and restate what's left.
                    An optional file or date ref (`resume 2026-08-29`, `resume yesterday's`)
                    selects a specific `*-HANDOFF.md` archive.
- `show`         -> **Show**: just render `HANDOFF.md` — no git, no checkout, no verify run.

Argument: $ARGUMENTS
