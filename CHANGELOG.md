# Changelog

All notable changes to this project are documented here. Releases follow
[Semantic Versioning](https://semver.org/). The generated `HANDOFF.md` **document
format** is versioned separately as a plain integer (`Format: handoff/N`), bumped only
when the doc's structure changes — see the "Document format" notes below.

## [0.1.0] - 2026-08-30

Initial release.

### Added
- `handoff` skill with three directions: **Write**, **Resume**, **Show** — routed by
  slash arg (`/handoff`, `/handoff resume`, `/handoff show`) or natural-language phrasing.
- Writing: reads repo state (no-git fallback), proves the verification command before
  recording it, date-first archives (keep last 3), secrets guard, self-audit before save.
- Resuming: format-stamp check, staleness guard, dirty-tree-safe branch restore,
  runs the recorded verification, restates remaining work.
- Cross-platform test fixture (`skills/handoff/tests/roundtrip.py`) — git mechanics plus
  skill-text assertions; quiet by default, `-v` for detail.
- Plugin packaging (`.claude-plugin/plugin.json` + `marketplace.json`), MIT license.
  (CI on a Linux/macOS/Windows matrix is prepared but deferred until the publishing
  token carries the `workflow` scope; run the fixture manually meanwhile.)

### Document format
- **handoff/1** — initial layout: header (When/Author/Format, Branch/Last commit,
  Run-everything-from, Resume-with), Goal, Completed, Remaining (confidence-tagged),
  Key files, How to resume, Verification, Watch out.
