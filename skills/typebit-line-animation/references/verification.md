# Verification and handoff

Verify the exported HTML itself, not only an editor preview or a locally served development page. Run the bundled `verify` command after the final render and inspect its output. Report the browser, environment, result, and any skipped checks exactly as recorded.

## Playback and offline behavior

- The initial page waits without autoplay.
- Right Arrow starts; repeated presses during playback do not restart it. After completion it restarts from the beginning.
- Space pauses/resumes and R restarts. Screen playback controls work without a keyboard.
- The final frame remains visible after the timeline finishes.
- The file opens through `file://` with networking disabled; no external resource is required or requested.
- The exported file works independently of the source/project directory. Images, SVG, script, and required fonts are embedded.

Missing Chromium, browser launch failures, and skipped steps are verification limitations. Do not convert them to passing results. If using a host browser manually instead, record the actual checks performed separately and retain the automated report's original outcome.

## Visual review

Inspect real rendered captures at the opening, a middle drawing state, and the final frame. Review light, dark, and checkerboard compositing. These backgrounds are test surfaces; they must not become part of the exported artwork.

Check:

- Main shape, scale, placement, original lettering, and final source colors.
- Meaningful contour order, limited photo texture noise, and readable text.
- Exterior transparency, alpha-edge halos, interior white lettering, highlights, and genuine holes.
- Brand doodles behind the artwork and away from readable text.

Screenshots on a checkerboard alone do not prove an alpha channel. Review the file structure and alpha results together with the visual captures. Automated checks can verify timing, controls, requests, and known transparency behavior; they cannot establish artistic fidelity or decide whether a white region belongs to the subject.

After this inspection, record `visual_review.status: reviewed`, the current HTML SHA-256, and specific notes in `project.json`, following [the project contract](project.md). Then run `package` to bind and propagate the review. Leave automated results unchanged. The verifier starts with visual review marked unverified because browser automation alone cannot perform that judgment.

## Delivery

Return the HTML, editable project package, visible preview, and verification report as real file links. State the technique: original SVG paths, approximate contours, masked original-image reveal, or their combination. Include unresolved font, mask, and verification issues when they exist.

Use wording such as “Chromium offline playback checks passed; the attached preview was visually reviewed” only when both claims are supported. Do not describe a CI configuration, a prior sample run, or an unexecuted test as verification of the user's current artwork.
