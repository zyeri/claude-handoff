---
name: handoff
description: Write, resume, show, or list self-contained, session-stamped handoff docs (*-HANDOFF.md).
argument-hint: "[quick | resume [<file> | <date> | <session-id>] | show | list]"
---

Use the **handoff** skill, routing by the argument below (natural-language requests
like "resume the handoff" or "show me the handoff" reach the same skill directly):

- empty          -> **Write** a new handoff (Full mode)
- `quick`        -> **Write** in Quick mode (header + Remaining + Verification)
- `resume`       -> **Resume**: read the newest `*-HANDOFF.md`, check the format stamp and staleness,
                    restore the branch, run the verification, and restate what's left.
                    An optional file, date, or session-id ref (`resume 2026-08-29`,
                    `resume yesterday's`, `resume ca154123`)
                    selects a specific `*-HANDOFF.md` file instead.
- `show`         -> **Show**: just render the newest `*-HANDOFF.md` - no git, no checkout, no verify run.
- `list`         -> **List**: one row per handoff (file, When, Session, Branch, Goal) to pick from.

Argument: $ARGUMENTS
