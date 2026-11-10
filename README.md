# TypeBit

**Give still images a drawn entrance.**

TypeBit is an Agent Skill for turning SVGs, logos, line art, and photos into standalone HTML line animations. Your Agent understands the image and makes revisions from conversation; TypeBit preserves the project, renders native SVG, and checks the exported file in a real browser.

[中文文档](README.zh-CN.md) · [Install the skill](#install-the-skill) · [Releases](https://github.com/JulyanXu/typebit/releases) · [Report a problem](https://github.com/JulyanXu/typebit/issues)

![TypeBit line-animation demo](docs/media/demo.gif)

*Recorded example playback. Exported HTML waits for you to press Play.*

## From an image to a portable animation

1. Give your Agent an image and ask for a line animation.
2. Review the actual rendered result. Say “draw the lettering last” or “keep the white highlights.”
3. Receive one offline HTML file, the editable project, and a browser-verification report.

The default sequence draws the main structure, secondary contours, and lettering/details before revealing color. It lasts about 10 seconds and holds the final frame. The subject's exterior stays transparent; restrained blue doodles sit behind it.

**No account, separate model installation, or inference API configuration.** TypeBit uses the vision and image tools already available in your Agent host. It does not include a website, visual editor, or cloud processing service. The player uses native SVG and JavaScript rather than GSAP.

![Source, drawing, and final-frame preview](docs/media/preview.png)

## What it handles

| Input | How it is treated |
| --- | --- |
| SVG | Reuse supported original geometry and assign drawing order. Text must be outlined or use an explicitly supplied embeddable font. |
| PNG / JPEG logo or line art | Use host-assisted contour paths, preserve original color pixels, and correct transparency as needed. |
| Photo | Use the host's visual/image tools to create simplified contours and a subject mask, then reveal the masked original image. |

Photo results are **approximate contours with an original-image reveal**, not a promise of perfect automatic vectorization. Seeing a photo is not the same as having a segmentation tool. If the host cannot produce a useful mask, TypeBit preserves the work and reports that subject isolation is incomplete. Raster input without contour paths cannot be rendered as a finished line animation.

## Install the skill

Download a release or clone this repository. Copy the **entire** `skills/typebit-line-animation` folder into your host's skill directory:

| Host | Personal skill location | Invocation |
| --- | --- | --- |
| Codex | `~/.agents/skills/typebit-line-animation/` | `$typebit-line-animation` |
| Claude Code | `~/.claude/skills/typebit-line-animation/` | `/typebit-line-animation` |
| Other hosts | Their supported skill location, or ask the Agent to read the copied `SKILL.md` | Host-specific |

Project-local alternatives are `.agents/skills/` for Codex and `.claude/skills/` for Claude Code. These instructions follow the hosts' [Codex](https://learn.chatgpt.com/docs/build-skills) and [Claude Code](https://code.claude.com/docs/en/skills) documentation. Available image, file, and browser tools depend on the host; installation alone does not grant those capabilities.

Use **Python 3.12** for the reference environment. From the repository root, in your chosen Python environment:

```text
python -m pip install -r skills/typebit-line-animation/requirements.txt
python -m playwright install chromium
python skills/typebit-line-animation/scripts/typebit.py doctor
```

For a copied skill, run the same commands from its folder using `requirements.txt` and `scripts/typebit.py`. If your interpreter is named `python3`, use that consistently. A virtual environment is recommended. See the [environment guide](skills/typebit-line-animation/references/environment.md) for host setup and missing capabilities.

Installation downloads Python packages and Chromium. **The finished HTML plays offline** without Python, TypeBit, or the original project folder. The preparation scripts need Pillow and defusedxml; browser verification also needs Playwright and its installed Chromium. Linux may require additional [Playwright system dependencies](https://playwright.dev/python/docs/intro).

## Ask your Agent

```text
Use $typebit-line-animation on the attached image. Preserve its shape,
lettering, and colors. Make a transparent 10-second line animation,
show me a real preview, verify offline playback, and deliver the HTML
with the editable project and verification report.
```

In Claude Code, use `/typebit-line-animation`. In another host, name the skill or provide the path to its `SKILL.md`.

Then revise in plain language:

> Draw the lettering last, simplify the lines on the right, and keep the white highlights. Make the blue strokes subtler.

The Agent updates the existing project and checks the new export. There is no separate editing page to learn.

## Try the included SVG

After installing dependencies, run from the repository root:

```text
python skills/typebit-line-animation/scripts/typebit.py prepare examples/source/typebit-mark.svg --project build/example --kind svg
python skills/typebit-line-animation/scripts/typebit.py render build/example
python skills/typebit-line-animation/scripts/typebit.py verify build/example/animation.html
python skills/typebit-line-animation/scripts/typebit.py package build/example
```

Open `build/example/animation.html`. The project package is `build/example-project.zip`; browser results are in `build/example/verification/report.json` and `report.md` alongside screenshots. This example exercises the deterministic toolchain. For a new image, use the Agent to interpret and review the artwork.

| Control | Behavior |
| --- | --- |
| Play button / Right Arrow | Start playback; Right Arrow does not restart an animation already playing. After completion it replays. |
| Space | Pause or resume. |
| R | Replay from the beginning. |

For host-prepared raster artwork, `prepare` accepts `--mask PATH`, `--contours SVG`, `--kind logo|lineart|photo`, and `--duration SECONDS`. `--remove-white-background` removes border-connected near-white pixels as a candidate mask; it still needs visual review. It does not remove every white region.

For live SVG text, supply `--font PATH --font-family NAME` with the correct redistributable font. The supplied font is applied to all text, which appears during the final reveal. Outline lettering to animate its strokes or preserve multiple fonts. Unsupported external resources are rejected rather than fetched at playback time. See the [project guide](skills/typebit-line-animation/references/project.md).

## Try a real photograph

The included Apollo 17 **Blue Marble** photograph is credited to **NASA / Apollo 17 crew**. Its three illustrative contours were authored after viewing the source; the circular mask is specific to this photograph. This is an approximate example, not automatic general-purpose segmentation. See the [source and use notes](examples/source/ATTRIBUTION.md); NASA does not endorse TypeBit.

| Approximate contours | Original-photo reveal |
| --- | --- |
| ![Host-authored globe and land contours](docs/media/photo-contours.png) | ![Original Blue Marble photo over a checkerboard](docs/media/photo-preview.png) |

```text
python skills/typebit-line-animation/scripts/typebit.py prepare examples/source/blue-marble.jpg --project build/photo-example --kind photo --mask examples/source/blue-marble-mask.png --contours examples/source/blue-marble-contours.svg
python -c "from shutil import copyfile; copyfile('examples/source/ATTRIBUTION.md', 'build/photo-example/ATTRIBUTION.md')"
python skills/typebit-line-animation/scripts/typebit.py render build/photo-example
python skills/typebit-line-animation/scripts/typebit.py verify build/photo-example/animation.html
python skills/typebit-line-animation/scripts/typebit.py package build/photo-example
```

The photo test compares every decoded RGB pixel with the source and checks the supplied alpha mask. The circular edge can trim the atmosphere slightly; cloud and terrain detail appears in the final photo reveal rather than being reconstructed as paths.

## Files you keep

- **`animation.html`** — embedded SVG, images, playback code, and required fonts; no runtime network dependency.
- **Project directory and ZIP** — original source, editable scene, timing/layer metadata, masks and fonts used by the project.
- **Verification report and screenshots** — evidence for the particular exported file and browser run.
- **Revision history** — earlier rendered project snapshots retained locally when rendering again. The delivery ZIP contains the current project; keep `revisions/` separately if needed.

## What “verified” means

See the [dated validation record](docs/validation.md) for real browser results and the independent Agent revision test.

The verifier opens the exported file through `file://`, disables networking, checks playback controls, and captures opening, middle, and final states over light, dark, and checkerboard backgrounds. The Agent separately reviews fidelity, lettering, contour quality, and white/transparent regions.

A passing browser test does **not** establish artistic fidelity. Missing browser support, incomplete masks, and unperformed checks must be disclosed. A CI workflow or another example's report is not verification of your artwork. Refer to each artifact's report for actual results; host-specific integration and CI support are not implied by installation instructions.

## Development and releases

TypeBit keeps its runtime, Skill instructions, and references together under `skills/typebit-line-animation/`. The GitHub repository is its documentation and distribution home. Release assets contain the installable skill and examples; user artwork is not automatically uploaded or published.

Changes should preserve source pixels, deterministic offline output, playback behavior, and honest verification. See [CHANGELOG.md](CHANGELOG.md), the [Skill workflow](skills/typebit-line-animation/SKILL.md), and the [verification guide](skills/typebit-line-animation/references/verification.md). To report a problem, include the TypeBit version, `doctor` output, and report; attach artwork only if you intend to share it publicly.

Maintainers can run `python tools/validate_skill.py` and `python -m unittest discover -s tests -v`, followed by the sample workflow above. [Checks](.github/workflows/checks.yml) defines Python 3.12 jobs on Ubuntu, Windows, and macOS and retains browser evidence. A configured job is not a passing run: inspect [Actions](https://github.com/JulyanXu/typebit/actions) for actual results.

For a release, update the runtime version and changelog, then push a matching `vX.Y.Z` tag. The [release workflow](.github/workflows/release.yml) runs checks and publishes the tested Linux example, skill ZIP, verification evidence, and checksums. CI records visual review as unverified because no Agent inspects those screenshots. Record any local Agent review against its own HTML hash; it does not transfer automatically to a separately built artifact.

[MIT License](LICENSE) · Copyright © 2026 Julyan Xu. Dependencies and user assets retain their own licenses; see [third-party notices](THIRD_PARTY_NOTICES.md).
