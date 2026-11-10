# Verification and handoff

Verify the exported HTML itself, not only an editor preview or a locally served development page. Run the bundled `verify` command after the final render and inspect its output. Report the browser, environment, result, and any skipped checks exactly as recorded.

## Playback and offline behavior

- The initial page waits without autoplay.
- Right Arrow starts; repeated presses during playback do not restart it. After completion it restarts from the beginning.
- Space pauses/resumes and R restarts. Screen playback controls work without a keyboard.
- Speed controls cover 0.25× to 4×. Changing speed preserves the current timeline position in both playing and paused states; the displayed timeline duration does not change.
- Scrubbing pauses at the selected frame. Keyboard events in the speed selector or progress slider must not trigger global playback shortcuts.
- The final frame remains visible after the timeline finishes.
- The file opens through `file://` with networking disabled; no external resource is required or requested.
- The exported file works independently of the source/project directory. Images, SVG, script, and required fonts are embedded.

Missing Chromium, browser launch failures, and skipped steps are verification limitations. Do not convert them to passing results. If using a host browser manually instead, record the actual checks performed separately and retain the automated report's original outcome.

## Format exports

Run exports only against the current rendered project. A stale HTML is not a valid basis for a new delivery. The export sidecar records the source HTML SHA-256, output SHA-256, format, dimensions, and applicable timing/background settings; this is export provenance, not a substitute for the playback or visual review report.

- HTML: reopen the downloaded copy offline, confirm it starts idle with the selected speed, and check its own hash if it is delivered as a separately verified artifact.
- PNG: inspect the intended frame, alpha channel, aspect ratio, and absence of toolbar controls. The browser button saves the current frame; the CLI defaults to the final frame.
- GIF: exercise the toolbar download offline, decode the downloaded GIF and check that cancellation restores the original playback state. Inspect the beginning, drawing stage, and final frame; check playback speed and the chosen solid background. Palette quantization and frame timing are GIF limitations. Do not label a white GIF background transparent.

Changing only export width, matte, or format does not require redrawing source contours. A new rendered HTML, changed timing, or altered artwork requires new verification. Check [exports.md](exports.md) for the supported format settings.

## Visual review

Inspect real rendered captures at the opening, a middle drawing state, and the final frame. Review light, dark, and checkerboard compositing. These backgrounds are test surfaces; they must not become part of the exported artwork.

Check:

- Main shape, scale, placement, original lettering, and final source colors.
- Meaningful contour order, limited photo texture noise, and readable text.
- Exterior transparency, alpha-edge halos, interior white lettering, highlights, and genuine holes.
- No decorative strokes absent from the source unless requested. If blue doodles were requested, check that they sit behind the artwork and away from readable text.

Screenshots on a checkerboard alone do not prove an alpha channel. Review the file structure and alpha results together with the visual captures. Automated checks can verify timing, controls, requests, and known transparency behavior; they cannot establish artistic fidelity or decide whether a white region belongs to the subject.

After this inspection, record `visual_review.status: reviewed`, the current HTML SHA-256, and specific notes in `project.json`, following [the project contract](project.md). Then run `package` to bind and propagate the review. Leave automated results unchanged. The verifier starts with visual review marked unverified because browser automation alone cannot perform that judgment.

## Delivery

Return the HTML, requested additional formats, editable project package, visible preview, and verification report as real file links. State the timeline duration, default speed, and technique: original SVG paths, approximate contours, masked original-image reveal, or their combination. Include unresolved font, mask, and verification issues when they exist.

Use wording such as “Chromium offline playback checks passed; the attached preview was visually reviewed” only when both claims are supported. Do not describe a CI configuration, a prior sample run, or an unexecuted test as verification of the user's current artwork.
