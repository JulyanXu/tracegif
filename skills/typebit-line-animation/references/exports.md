# Playback speed and export formats

Keep one editable project and derive its deliverables from a current render. Prepare artwork once; changing speed, duration, size, or format should not cause a new interpretation of the source image.

## Speed and duration

The timeline is measured in source animation seconds. Playback speed determines how fast those seconds pass. A 10-second timeline at 2× plays in 5 seconds; its drawing order and layer geometry are unchanged.

```text
python <skill-directory>/scripts/typebit.py configure <project-directory> --duration 12 --speed 1.5
python <skill-directory>/scripts/typebit.py render <project-directory>
python <skill-directory>/scripts/typebit.py verify <project-directory>/animation.html
```

`--duration` proportionally rescales the layer schedule and final reveal. `--speed` saves the default rate, between 0.25 and 4. The HTML toolbar can change rate during playback without jumping to another frame, and the progress slider pauses at a selected timeline position. To keep a toolbar choice for future Agent edits, also save it through `configure`.

## Formats

| Format | Default output | Behavior |
| --- | --- | --- |
| `html` | `exports/animation.html` | Self-contained interactive animation, initially waiting. Keeps the project's default playback rate. |
| `png` | `exports/animation.png` | Final frame by default, with full alpha transparency and no controls. |
| `gif` | `exports/animation.gif` | Looping animated browser captures, solid white matte by default, and a short final-frame hold. |

All default paths are relative to the project directory. `--output PATH` selects another output file of the corresponding extension. A target inside the project must be under `exports/`; an external target is also allowed. Existing files are replaced only when their matching export sidecar and checksum identify them as a previous generated export. Otherwise choose a new filename. Never overwrite the original source, project metadata, or canonical `animation.html` with a derived export.

```text
python <skill-directory>/scripts/typebit.py export <project-directory> --format html
python <skill-directory>/scripts/typebit.py export <project-directory> --format png --width 1080
python <skill-directory>/scripts/typebit.py export <project-directory> --format png --time 5 --output drawing.png
python <skill-directory>/scripts/typebit.py export <project-directory> --format gif --width 640 --fps 15 --background "#F7F5EF"
python <skill-directory>/scripts/typebit.py package <project-directory>
```

For PNG, `--time` is a timeline position, not elapsed wall-clock time. A 5-second frame is the same drawing state at either 0.5× or 2×, so PNG rejects `--speed`. Its default background is transparent; use a solid `--background "#RRGGBB"` if requested. The toolbar's PNG button saves the currently displayed frame instead of automatically seeking to the end.

For GIF, the animation portion lasts `duration / speed`, followed by a 0.8-second final hold before looping. `--speed` can override the project rate for that export without modifying the project. GIF exports the whole animation and rejects `--time`. GIF uses a palette and cannot preserve smooth alpha edges, so transparent GIF output is not supported. Use HTML for a transparent animation or PNG for a transparent still.

An HTML export can also use `--speed` to set that copy's initial rate. It does not accept image dimensions, a matte, or a selected frame. The HTML toolbar's download similarly saves the chosen rate while resetting the saved copy to idle. These copies are new files with their own checksums; the original HTML's playback report does not silently become a report for a different file.

The standalone HTML toolbar offers HTML, PNG and GIF downloads with no server or runtime network dependency. **Save GIF** uses the selected speed for the full timeline, a white matte, a maximum width of 480 pixels, 10 fps and an 800 ms final hold. It shows progress and a Cancel GIF button. The prior position, rate and playback state are restored on success, cancellation or error. Browser export rejects more than 600 frames, 100 million aggregate frame pixels or a height above 4096 pixels; use a faster speed or ask the Agent for a smaller CLI export. The bundled gifenc encoder and its MIT notice are embedded into each HTML. Browser GIF and CLI GIF may differ in palette quantization, while using the same artwork and timeline.

## Size and resource limits

For CLI exports, PNG and GIF preserve the source aspect ratio. The default width is the source width capped at 720 pixels. Explicit widths must be 32–2048 pixels; height is limited to 4096 pixels and the total canvas to 8 million pixels. GIF frame rates are 1–30 fps, default 15 fps. GIF generation is limited to 900 captured frames and 160 million aggregate frame pixels. If a large or slow animation exceeds those bounds, reduce width or fps, or choose a faster rate. The helper returns a clear error rather than silently changing the requested settings.

## Evidence and packaging

Each export creates a sidecar named `<output-filename>.export.json`. It binds the source HTML hash to the output hash and records format settings such as dimensions, rate, fps, selected frame, and matte as applicable. Inspect the output yourself; a sidecar proves provenance, not artistic quality.

Exports require a current render. If saved settings or source assets changed, render and verify again before exporting. Generated `exports/` and `preview/` directories are excluded from editable-source snapshots, so refreshing a preview does not make the source stale. Rendering a new revision archives the previous previews and exports with its history; generate new ones for the new HTML. Current exports are included in the project package; export before running `package` if those files should travel with the editable project.

The capture and encoding foundations are documented in [Playwright screenshots](https://playwright.dev/python/docs/screenshots), [Playwright offline contexts](https://playwright.dev/python/docs/api/class-browsercontext#browser-context-set-offline), and [Pillow GIF support](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#gif). These references describe the libraries; the TypeBit command limits above describe this implementation.
