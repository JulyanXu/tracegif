# Changelog

## 0.4.0 — 2026-11-11

- Rename the project to **TraceGIF**, with a `tracegif` Skill, `tracegif.py` command, renamed release assets and migration notes. Preserve old project fields, command aliases and browser API compatibility.
- Add offline GIF settings for width, frame rate and background; retain choices in downloaded HTML and show output estimates and resource-limit feedback.
- Keep exact matte, white and black colors in resized GIF exports; make the control panel usable on short viewports and preserve native keyboard behavior for settings.
- Expand the original gallery from three to seven cases: architecture, travel, education and event invitations. Preserve native landscape/portrait proportions in actual captured comparisons.
- Audit and tighten project packaging and verification evidence so incomplete or stale deliverables are not presented as checked output.

## 0.3.0 — 2026-11-10

- Add **Save GIF** to standalone HTML: full animation at the selected speed, offline encoding, progress, cancellation and playback-state restoration.
- Embed pinned gifenc 1.0.3 with its MIT notice; no CDN, server, worker download or new installation step is needed for playback/export.
- Add three original, redistributable cases: Leaf Studio, Coffee Story and White Letter Badge, with browser-captured GIFs, source/drawing/final previews, editable projects and verification.
- Publish a bilingual case gallery and a downloadable case bundle alongside the Skill release.
- Check source provenance, export hashes and editable-package contents before rebuilding or publishing, so stale artwork and exports cannot silently enter a release.

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
