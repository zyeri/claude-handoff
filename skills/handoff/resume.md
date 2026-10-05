# Resuming from a handoff

## Steps

0. **Gather state in one call.** Run `handoff_state.py resume` (add `--file <name>` once a specific ref has resolved to a file; see "Gather state in one call" in `SKILL.md`). Its JSON answers the mechanical parts of steps 1-5: `target` (the handoff, legacy file placed by its `When:`) and `handoffs` (all candidates, each with parsed header) for step 1, `session` for step 2, `target.format` for step 3, `staleness` (`is_ancestor`, `drift`, `latest_commit_date` - the results of the commands in step 4) for step 4, `current_branch` and `status` for step 5. Then Read the `target` file itself for the sections. Run the commands below by hand only if the script can't run.
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
