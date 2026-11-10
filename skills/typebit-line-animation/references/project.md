# Project and revision contract

The project is the editable source of truth. The HTML is a distributable rendering of it. Use `prepare` to create the initial project, then modify that generated structure instead of inventing a parallel format. Run the CLI with `--help` for the current argument contract.

## Project fields

`project.json` uses `schema_version: 1` and contains:

| Field | Meaning |
| --- | --- |
| `name`, `duration`, `brand_color` | Artwork name, total duration in seconds (1–300), and six-digit hex accent color. |
| `fill_start`, `doodle` | Start of the final color reveal (default 85% of duration), and whether the blue decoration appears. |
| `source` | Original source path, SHA-256, and the selected image kind. |
| `scene`, optional `contours` | Project-relative paths to the final SVG scene and a separate raster-contour SVG. |
| `layers` | Stable layer IDs, human-readable labels, phase, start time, and duration. |
| `processing` | Actual processing method, whether it is approximate, warnings, and unresolved `needs`. |
| `visual_review` | Agent/user review status, current HTML hash, and notes; independent of automated browser checks. |
| Optional `font` | Copied font asset path and the family name applied to all live SVG text. |
| `revision`, `render` | Render revision and current HTML path/hash, maintained by the helper. |

Layer phases are `main`, `secondary`, and `details`; the player subsequently reveals final color. Every drawable geometry element outside definitions needs exactly one layer entry whose ID matches the element. Layer timings must end at or before `fill_start`. Phase names communicate intent; explicit `start` and `duration` values determine playback. Changing only a phase label does not reschedule a layer.

`prepare` creates `scene.svg`, original/derived assets, and `project.json`. A raster source also needs `contours.svg`. Preparation can return `needs_input` while preserving a useful partial project. Resolve each actual `processing.needs` issue before removing its entry; deleting warnings or needs without producing the required artwork does not complete the work.

Treat the generated file as authoritative for supported optional fields. Keep file references within the project so the package can move to another machine. Do not introduce external scripts, stylesheets, fonts, images, or network URLs into the scene.

After inspecting the final HTML's actual screenshots against the source, update only `visual_review` in `project.json`:

```json
{
  "status": "reviewed",
  "html_sha256": "COPY_THE_CURRENT_render.html_sha256_VALUE",
  "notes": ["Record the actual comparison, approximations, and remaining limitations."]
}
```

Use the actual `render.html_sha256`, not the example string above. `package` binds the review to that HTML and propagates it into the current verification report. Do not edit automated check results to mark visual review. A later render resets the review; inspect that new version before setting it again. If no visual inspection occurred, keep the status `unverified`.

## Natural-language revision

1. Inspect the latest project, existing rendered preview, and the user's change request.
2. Preserve the source files before edits. After a successful render, the helper retains a snapshot in `.last-render.zip`; the next render archives that snapshot in `revisions/rNNNN.zip`. This protects the preceding rendered project, not unrendered intermediate changes.
3. Map the request to the smallest relevant change: timing, layer order, contour geometry, mask, or accent color. Preserve all unrelated artwork.
4. Reset visual-review status when a relevant visual change invalidates the previous review; retain useful notes as history, not as proof that the new version was checked.
5. Render again, run verification against the new `animation.html`, inspect the resulting previews, and update visual-review notes accurately. Each render resets visual review and archives the previous verification directory.
6. Package only after the final render and validation so the sources, HTML, and reports refer to the same revision. Default verification lives in `verification/report.json` and `report.md`; the default ZIP is the project directory's sibling `<project-name>-project.zip`. The ZIP contains the current project, not the hidden snapshot or `revisions` history; keep that history separately when needed.

Examples:

- “Draw the lettering last”: identify the lettering layers, move them into the details phase, and adjust timings without changing their geometry.
- “Keep these white highlights”: correct the alpha mask from original pixels, rather than painting guessed white patches over the result. Update the derived `assets/subject.png` and its embedded image data in `scene.svg` together; changing the PNG alone does not update the embedded final scene.
- “Fewer lines on the right”: remove or simplify the relevant contours, while retaining original pixels in the final reveal.
- “Make it 12 seconds”: adjust `duration`, `fill_start`, and layer timings coherently, then verify pause/resume and completion at the new duration.

Do not introduce an interactive editing application. The chat is the editing interface; the project is the durable, portable representation.
