# Changelog

## 0.2.0 — 2026-11-10

- Add speed selection from 0.25× to 4×, timeline scrubbing, elapsed time, and HTML/current-frame PNG downloads to the offline player.
- Add `configure` to persist playback speed, proportionally retime a project, and toggle requested decoration without regenerating artwork.
- Add `export` for standalone HTML, transparent PNG frames, and GIF animations captured from the offline browser, with source/output checksums and export settings.
- Separate generated previews and exports from editable-source snapshots so revising and re-exporting keeps the project workflow consistent.
- Disable added blue doodle strokes by default so new animations preserve the source without extra decoration. Missing `doodle` settings also default to off; the boolean `true` remains available when explicitly requested.
- Reject non-boolean `doodle` values instead of treating strings such as `"false"` as enabled. Existing projects that store `doodle: true` keep that setting; set it to `false`, render, and verify to remove unwanted decoration.
- Align Skill instructions and bilingual documentation with the optional-decoration behavior. The `v0.1.0` release assets are unchanged.

## 0.1.0 — 2026-11-10

Initial release of TypeBit as a portable Agent Skill.

- Native SVG line-animation player with a default ten-second sequence, manual start, pause/resume, and replay.
- SVG, PNG, and JPEG project preparation, with optional host-produced masks and contour paths.
- Editable project files and natural-language revision through the host Agent.
- Self-contained HTML export and project packaging.
- Local Chromium verification with offline playback checks and transparency preview captures.
- English documentation, Chinese documentation, and installation guidance for Codex, Claude Code, and other capable Agent hosts.

Photo interpretation and semantic layering use the host Agent's existing tools. TypeBit does not install AI models or configure an inference API. Browser verification applies only to the specific artifact and environment recorded in its report.
