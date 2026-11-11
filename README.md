# TraceGIF

**Draw the lines. Make the GIF. Keep the source.**

TraceGIF turns images into line-drawing animations, animated GIFs and offline HTML. Your Agent interprets the artwork and makes revisions from conversation; the Skill preserves editable layers, renders native SVG and checks the exported file in a real browser.

Previously **TypeBit**. The project is now TraceGIF to make its two main uses clear: traced line animation and GIF creation. Existing projects remain editable; see the [migration notes](docs/migration.md).

[中文文档](README.zh-CN.md) · [Install the skill](#install-the-skill) · [Releases](https://github.com/JulyanXu/tracegif/releases) · [Report a problem](https://github.com/JulyanXu/tracegif/issues)

![TraceGIF line-animation demo](docs/media/demo.gif)

*Recorded example playback. Exported HTML waits for you to press Play; speed and progress are adjustable.*

## From an image to a portable animation

1. Give your Agent an image and ask for a line animation.
2. Preview the result, adjust playback speed, or scrub to a particular frame. Describe artwork changes in conversation.
3. Choose a standalone HTML, animated GIF, or PNG frame. Keep the editable project and verification report for later revisions.

The default sequence draws the main structure, secondary contours, and lettering/details before revealing color. It lasts about 10 seconds and holds the final frame. The subject's exterior stays transparent. Extra decoration is off by default; blue doodles can be added behind the subject when requested.

**No account, separate model installation, or inference API configuration.** TraceGIF uses the vision and image tools already available in your Agent host. It does not include a website, visual editor, or cloud processing service. The player uses native SVG and JavaScript rather than GSAP.

![Source, drawing, and final-frame preview](docs/media/preview.png)

## Seven scenarios, one editable workflow

| Botanical identity | Product storytelling | White-letter preservation |
| --- | --- | --- |
| [![Leaf Studio animation](docs/cases/leaf-studio/animation.gif)](docs/cases/README.md) | [![Coffee Story animation](docs/cases/coffee-story/animation.gif)](docs/cases/README.md) | [![White Letter Badge animation](docs/cases/white-letter-badge/animation.gif)](docs/cases/README.md) |
| Introduce a botanical mark, branch by branch. | Draw a cup, then its steam and details. | Keep white letterforms inside a transparent PNG badge. |

| Architecture | Travel itinerary | Education | Event invitation |
| --- | --- | --- | --- |
| [![Courtyard House](docs/cases/courtyard-house/animation.gif)](docs/cases/README.md) | [![City Route](docs/cases/city-route/animation.gif)](docs/cases/README.md) | [![Orbit Lesson](docs/cases/orbit-lesson/animation.gif)](docs/cases/README.md) | [![Celebration Card](docs/cases/celebration-card/animation.gif)](docs/cases/README.md) |
| Present a facade, from structure to small details. | Introduce route stops and a journey. | Draw an illustrative orbital diagram step by step. | Build a portrait invitation from its frame to its message. |

These are original, editable demonstration artworks. Each GIF comes from the actual exported player. [Explore the source → drawing → final gallery](docs/cases/README.md), or [download all seven HTML/GIF/PNG examples and editable projects](https://github.com/JulyanXu/tracegif/releases/download/v0.4.0/tracegif-cases-0.4.0.zip). The gallery includes reusable prompts, processing notes, and verification reports.

## What it handles

| Input | How it is treated |
| --- | --- |
| SVG | Reuse supported original geometry and assign drawing order. Text must be outlined or use an explicitly supplied embeddable font. |
| PNG / JPEG logo or line art | Use host-assisted contour paths, preserve original color pixels, and correct transparency as needed. |
| Photo | Use the host's visual/image tools to create simplified contours and a subject mask, then reveal the masked original image. |

Photo results are **approximate contours with an original-image reveal**, not a promise of perfect automatic vectorization. Seeing a photo is not the same as having a segmentation tool. If the host cannot produce a useful mask, TraceGIF preserves the work and reports that subject isolation is incomplete. Raster input without contour paths cannot be rendered as a finished line animation.

## Install the skill

Download a release or clone this repository. Copy the **entire** `skills/tracegif` folder into your host's skill directory:

Use **v0.4.0 or later** for the TraceGIF name, configurable browser GIF exports and seven public cases. Install the complete `tracegif` folder from the release ZIP. Earlier releases retain their original names and behavior. To remove decoration from an older project, run `configure PROJECT --doodle off`, then render and verify again.

| Host | Personal skill location | Invocation |
| --- | --- | --- |
| Codex | `~/.agents/skills/tracegif/` | `$tracegif` |
| Claude Code | `~/.claude/skills/tracegif/` | `/tracegif` |
| Other hosts | Their supported skill location, or ask the Agent to read the copied `SKILL.md` | Host-specific |

Project-local alternatives are `.agents/skills/` for Codex and `.claude/skills/` for Claude Code. These instructions follow the hosts' [Codex](https://learn.chatgpt.com/docs/build-skills) and [Claude Code](https://code.claude.com/docs/en/skills) documentation. Available image, file, and browser tools depend on the host; installation alone does not grant those capabilities.

Use **Python 3.12** for the reference environment. From the repository root, in your chosen Python environment:

```text
python -m pip install -r skills/tracegif/requirements.txt
python -m playwright install chromium
python skills/tracegif/scripts/tracegif.py doctor
```

For a copied skill, run the same commands from its folder using `requirements.txt` and `scripts/tracegif.py`. If your interpreter is named `python3`, use that consistently. A virtual environment is recommended. See the [environment guide](skills/tracegif/references/environment.md) for host setup and missing capabilities.

Installation downloads Python packages and Chromium. **The finished HTML plays offline** without Python, TraceGIF, or the original project folder. The preparation scripts need Pillow and defusedxml; browser verification also needs Playwright and its installed Chromium. Linux may require additional [Playwright system dependencies](https://playwright.dev/python/docs/intro).

## Ask your Agent

```text
Use $tracegif on the attached image. Preserve its shape,
lettering, and colors. Make a transparent 10-second line animation,
show me a real preview, verify offline playback, and deliver the HTML
with the editable project and verification report.
```

In Claude Code, use `/tracegif`. In another host, name the skill or provide the path to its `SKILL.md`.

Then revise in plain language:

> Draw the lettering last, simplify the lines on the right, and keep the white highlights.

> Make it 12 seconds, start at 1.5× speed, and give me a GIF with a white background plus the transparent final PNG.

If an earlier project includes unwanted decoration, say “remove the blue decoration.” The Agent disables it without changing the source artwork.

The Agent updates the existing project and checks the new export. Changing timing or format reuses its artwork; it does not require tracing the image again. The HTML toolbar provides playback and downloads; artwork revisions stay in the conversation.

## Try the included SVG

After installing dependencies, run from the repository root:

```text
python skills/tracegif/scripts/tracegif.py prepare examples/source/typebit-mark.svg --project build/example --kind svg
python skills/tracegif/scripts/tracegif.py configure build/example --duration 12 --speed 1.5
python skills/tracegif/scripts/tracegif.py render build/example
python skills/tracegif/scripts/tracegif.py verify build/example/animation.html
python skills/tracegif/scripts/tracegif.py export build/example --format gif --width 640 --fps 15
python skills/tracegif/scripts/tracegif.py export build/example --format png
python skills/tracegif/scripts/tracegif.py package build/example
```

Open `build/example/animation.html`. This example has a 12-second timeline and plays it in 8 seconds at 1.5×. Format exports appear in `build/example/exports/`; the project package is `build/example-project.zip`. Browser results are in `build/example/verification/report.json` and `report.md` alongside screenshots. For a new image, use the Agent to interpret and review the artwork. The `configure` and extra-format `export` steps are optional.

| Control | Behavior |
| --- | --- |
| Play button / Right Arrow | Start playback; Right Arrow does not restart an animation already playing. After completion it replays. |
| Space | Pause or resume. |
| R | Replay from the beginning. |
| Speed selector | Change playback from 0.25× to 4× without jumping to another frame. |
| Progress slider | Move to a frame and pause there. |
| HTML download | Save a standalone copy that starts at the selected speed and waits for Play. |
| PNG download | Save the currently displayed frame with transparency and no toolbar. |
| GIF settings / download | Choose width, frame rate and background, then save the complete animation at the selected speed; progress and cancellation are available. |

The displayed time is the animation's timeline position. Playback duration is timeline duration divided by speed. To save a different project default, ask the Agent or use `configure PROJECT --speed 0.5`; to stretch the drawing schedule itself, use `configure PROJECT --duration 20`. Render and verify after either saved change.

## Choose an output format

![Offline player with speed, progress and download controls](docs/media/player-controls.png)

| Format | Best for | Transparency and playback |
| --- | --- | --- |
| HTML | Offline interactive presentation | Transparent artwork, adjustable speed, keyboard and screen controls. |
| PNG | A still frame or final image | Full alpha transparency by default; CLI exports the final frame unless `--time` is supplied. |
| GIF | A preview in documents or GitHub | Animated browser captures, with a solid white background by default. Use `--background "#RRGGBB"` for another color. |
| Project ZIP | Editing again with an Agent | Source, layers, timings, reports, and generated exports. |

Open **GIF settings** to select width (Auto, 240, 480, 720 or 960 px), frame rate (5, 10, 15 or 20 fps) and background color. Defaults remain Auto up to 480 px, 10 fps and white. **Save GIF** exports the full timeline at the selected playback speed with a 0.8-second final hold, progress and cancellation. Saving HTML also keeps those GIF preferences. Larger exports are limited to protect browser memory; the settings show actionable feedback. GIF is a palette format; use HTML or PNG when smooth transparency matters. See [speed and export options](skills/tracegif/references/exports.md).

For host-prepared raster artwork, `prepare` accepts `--mask PATH`, `--contours SVG`, `--kind logo|lineart|photo`, and `--duration SECONDS`. `--remove-white-background` removes border-connected near-white pixels as a candidate mask; it still needs visual review. It does not remove every white region.

For live SVG text, supply `--font PATH --font-family NAME` with the correct redistributable font. The supplied font is applied to all text, which appears during the final reveal. Outline lettering to animate its strokes or preserve multiple fonts. Unsupported external resources are rejected rather than fetched at playback time. See the [project guide](skills/tracegif/references/project.md).

## Try a real photograph

The included Apollo 17 **Blue Marble** photograph is credited to **NASA / Apollo 17 crew**. Its three illustrative contours were authored after viewing the source; the circular mask is specific to this photograph. This is an approximate example, not automatic general-purpose segmentation. See the [source and use notes](examples/source/ATTRIBUTION.md); NASA does not endorse TraceGIF.

| Approximate contours | Original-photo reveal |
| --- | --- |
| ![Host-authored globe and land contours](docs/media/photo-contours.png) | ![Original Blue Marble photo over a checkerboard](docs/media/photo-preview.png) |

```text
python skills/tracegif/scripts/tracegif.py prepare examples/source/blue-marble.jpg --project build/photo-example --kind photo --mask examples/source/blue-marble-mask.png --contours examples/source/blue-marble-contours.svg
python -c "from shutil import copyfile; copyfile('examples/source/ATTRIBUTION.md', 'build/photo-example/ATTRIBUTION.md')"
python skills/tracegif/scripts/tracegif.py render build/photo-example
python skills/tracegif/scripts/tracegif.py verify build/photo-example/animation.html
python skills/tracegif/scripts/tracegif.py package build/photo-example
```

The photo test compares every decoded RGB pixel with the source and checks the supplied alpha mask. The circular edge can trim the atmosphere slightly; cloud and terrain detail appears in the final photo reveal rather than being reconstructed as paths.

## Files you keep

- **`animation.html`** — embedded SVG, images, playback code, and required fonts; no runtime network dependency.
- **Project directory and ZIP** — original source, editable scene, timing/layer metadata, masks and fonts used by the project.
- **Verification report and screenshots** — evidence for the particular exported file and browser run.
- **`exports/`** — requested GIFs, PNG frames, or HTML copies, with export settings and source/output checksums.
- **Revision history** — earlier rendered project snapshots retained locally when rendering again. The delivery ZIP contains the current project; keep `revisions/` separately if needed.

## What “verified” means

See the [dated validation record](docs/validation.md) for real browser results and the independent Agent revision test.

The verifier opens the exported file through `file://`, disables networking, checks playback controls, and captures opening, middle, and final states over light, dark, and checkerboard backgrounds. The Agent separately reviews fidelity, lettering, contour quality, and white/transparent regions.

A passing browser test does **not** establish artistic fidelity. Missing browser support, incomplete masks, and unperformed checks must be disclosed. A CI workflow or another example's report is not verification of your artwork. Refer to each artifact's report for actual results; host-specific integration and CI support are not implied by installation instructions.

## Development and releases

TraceGIF keeps its runtime, Skill instructions, and references together under `skills/tracegif/`. The GitHub repository is its documentation and distribution home. Release assets contain the installable skill and examples; user artwork is not automatically uploaded or published.

Changes should preserve source pixels, deterministic offline output, playback behavior, and honest verification. See [CHANGELOG.md](CHANGELOG.md), the [Skill workflow](skills/tracegif/SKILL.md), and the [verification guide](skills/tracegif/references/verification.md). To report a problem, include the TraceGIF version, `doctor` output, and report; attach artwork only if you intend to share it publicly.

Maintainers can run `python tools/validate_skill.py` and `python -m unittest discover -s tests -v`, followed by the sample workflow above. [Checks](.github/workflows/checks.yml) defines Python 3.12 jobs on Ubuntu, Windows, and macOS and retains browser evidence. A configured job is not a passing run: inspect [Actions](https://github.com/JulyanXu/tracegif/actions) for actual results.

For a release, update the runtime version and changelog, then push a matching `vX.Y.Z` tag. The [release workflow](.github/workflows/release.yml) runs checks and publishes the tested Linux example, skill ZIP, verification evidence, and checksums. CI records visual review as unverified because no Agent inspects those screenshots. Record any local Agent review against its own HTML hash; it does not transfer automatically to a separately built artifact.

[MIT License](LICENSE) · Copyright © 2026 Julyan Xu. Dependencies and user assets retain their own licenses; see [third-party notices](THIRD_PARTY_NOTICES.md).
