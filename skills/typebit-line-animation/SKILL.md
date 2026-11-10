---
name: typebit-line-animation
description: Create and revise offline SVG line-animation HTML from images, logos, line art, or photos, using the host Agent's visual tools and real-browser verification. Use for image-to-line animations and natural-language revisions of TypeBit projects.
---

# TypeBit line animation

Turn a supplied image into an offline HTML animation, with editable source and an honest verification report. Use the host Agent's existing vision and image tools for interpretation and image editing. The bundled Python helpers perform deterministic preparation, packaging, and browser checks. There is no separate model, API account, web editor, or hosted service to set up.

## Start with the available evidence

1. Locate this skill directory and the source image. Resolve script paths relative to this `SKILL.md`, not the user's current directory.
2. Run `python <skill-directory>/scripts/typebit.py doctor`. Read [environment.md](references/environment.md) if dependencies or browser support are missing.
3. View the actual source. Decide whether it is SVG, a raster logo, line art, or a photo; file extensions alone do not identify the subject. Confirm which host tools can inspect images, create/edit masks or paths, write files, and operate a browser. Seeing an image does not imply access to subject segmentation.
4. Preserve the original. Work in a new project directory and keep source geometry, proportions, placement, colors, and letterforms. Use reasonable defaults unless the user specifies otherwise: a 10-second timeline, 1× playback, no added decoration, and standalone HTML plus the editable project and preview. Ask about format only when the requested use cannot be inferred.

## Build the artwork

Read [artwork.md](references/artwork.md) when preparing a raster image, photo, or image with white regions. Read [project.md](references/project.md) before editing a project or authoring contour layers.

- For SVG, retain supported original geometry. Expand every visible `<use>` instance into ordinary geometry before preparation, including instances mixed with other shapes. Resolve external resources before export; do not silently substitute fonts or redraw lettering.
- For raster logos and line art, use the host's visual reasoning and available image tools to create meaningful contours. Supply them with `--contours`; the helpers do not trace or infer semantic paths. A project missing contours or a usable alpha mask remains incomplete and cannot render.
- For photos, simplify major contours and use a subject mask to reveal the original image at the end. Take color pixels from the source, not a generated replacement. Record approximate tracing and masked raster reveal in `processing` and the handoff.
- Protect internal white lettering, highlights, and negative space. Removing every white pixel is not background removal. Use the optional connected-border white removal only when appropriate, then inspect the result.
- Use the default order: main structure, secondary contours, lettering/details, then color. Default duration is 10 seconds, followed by a held final frame. Preserve the source without adding decorative strokes by default. Only when the user requests blue doodles, set `doodle: true` in `project.json` and keep them restrained, behind the subject, and clear of text.

Use the CLI as a repeatable helper:

```text
python <skill-directory>/scripts/typebit.py prepare <input> --project <project-directory> --kind <svg|logo|lineart|photo>
python <skill-directory>/scripts/typebit.py configure <project-directory> --duration 12 --speed 1.5
python <skill-directory>/scripts/typebit.py render <project-directory>
python <skill-directory>/scripts/typebit.py verify <exported-html> --output <verification-directory>
python <skill-directory>/scripts/typebit.py export <project-directory> --format <html|png|gif>
python <skill-directory>/scripts/typebit.py package <project-directory>
```

`prepare` also accepts `--mask`, `--contours`, `--remove-white-background`, and `--duration`. Live SVG text requires `--font PATH --font-family NAME`; that single font applies to all live text, which appears in the final reveal. Outline lettering to animate its strokes or preserve mixed fonts. Use absolute paths and quote paths with spaces. Inspect command output for the actual created paths. Preparation alone is not a completed, visually reviewed animation.

`configure` and additional-format `export` are optional. Use `configure --duration` to rescale the existing drawing schedule, `--speed` to set its initial playback rate, and `--doodle off` to remove added decoration. Duration and speed are different: a 12-second timeline at 1.5× takes 8 seconds to play. Timing changes reuse the existing geometry and mask; do not reinterpret or regenerate the whole image.

## Preview and revise in conversation

Show previews rendered from the actual HTML. When the user asks for changes, update the existing project rather than creating a new interpretation of the whole image. Preserve a copy of source files before editing them; rendering archives the previous successfully rendered project, not every intermediate edit. Change only the relevant contours, semantic layers, timing, mask, or color, then render and verify again.

Examples: “Draw the lettering last,” “Keep the white highlights,” “Use fewer lines on the right,” and “Remove the blue decoration.” Set `doodle: false` to remove decoration from an existing project; do not remove blue pixels or paths that belong to the source artwork. There is no visual editing page: the user gives feedback in chat, and the Agent edits the project.

The delivered HTML has a speed selector, progress slider, and replay control. Speed changes keep the current frame position; scrubbing pauses at the chosen frame. The toolbar can save a standalone HTML copy using the selected speed or a transparent PNG of the current frame. To persist a preference in the editable project, run `configure`, render, and verify. A downloaded HTML copy does not modify the project's source settings.

Read [exports.md](references/exports.md) when choosing a delivery format. Use HTML for offline controls, PNG for a transparent still, and GIF for an animated preview with a solid background. GIF generation runs through the helper and uses the actual browser renderer; do not claim transparent GIF edges or provide a renamed HTML file as another format. Inspect the exported asset and its sidecar report before delivery.

## Verify and deliver

Read [verification.md](references/verification.md). Check opening, middle, and final frames on light, dark, and checkerboard backgrounds. Inspect shape fidelity, original lettering, alpha edges, and retained white regions yourself; a passing playback test does not prove visual quality.

The exported player must wait on open. Right Arrow starts playback, does not reset a playing animation, and replays after completion. Space pauses/resumes; R replays. Include accessible playback, speed, and progress controls. Keep the final frame visible. Confirm speed changes do not jump or restart playback and input controls retain their own keyboard behavior.

Use real-browser offline verification on the exported file and report its actual outcome. If a required host tool or browser is unavailable, state what could not be completed and preserve useful work. Do not mark unperformed checks as passed or present a rectangular opaque photo as a successfully isolated subject.

Deliver links to the single HTML, requested additional formats, editable project package, preview, and verification report. State the timeline duration and default speed, processing method, approximations, and any remaining verification limitations. For GIF, state its solid background. All images, player code, SVG, and required redistributable fonts must be embedded in the HTML; playback must not depend on this skill, its source directory, or the network.
