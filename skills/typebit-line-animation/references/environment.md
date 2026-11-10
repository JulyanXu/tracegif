# Host and environment

## Requirements

- Python 3.12 is the supported reference environment. A default `python` pointing to Python 3.11 does not meet the `doctor` baseline; install/use 3.12 explicitly.
- Install the packages in this skill's `requirements.txt` using the same Python interpreter used for its scripts.
- Install Chromium through that interpreter's Playwright package for automated verification and CLI PNG/GIF export.
- The Agent needs source-image viewing and local file/command access. Photo isolation additionally needs a usable subject mask from the user or the host's existing image tools. Image generation is not automatically a faithful segmentation tool.

Run the following from the copied `typebit-line-animation` skill directory (or from `skills/typebit-line-animation` inside a repository checkout). These commands use the virtual environment directly, so shell activation is unnecessary.

### Windows

Install Python 3.12 with the Python launcher available, then:

```text
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m playwright install chromium
.venv\Scripts\python.exe scripts/typebit.py doctor
```

### macOS and Linux

Install Python 3.12 so `python3.12` resolves to that interpreter, then:

```text
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

On macOS:

```text
.venv/bin/python -m playwright install chromium
.venv/bin/python scripts/typebit.py doctor
```

On supported Linux systems, install Chromium and its operating-system libraries; this step can require system-administrator access:

```text
.venv/bin/python -m playwright install --with-deps chromium
.venv/bin/python scripts/typebit.py doctor
```

Use that same virtual-environment executable for later TypeBit commands. Examples that use bare `python` assume the correct environment is already selected; do not accidentally switch back to another Python installation.

Browser verification requires a Playwright-supported operating system: Windows 11 or Windows Server 2019+, macOS 14+, or a supported Linux distribution such as Ubuntu 22.04/24.04 or Debian 12/13. These are environment requirements, not a claim that every host integration was tested. See [Playwright's official installation instructions](https://playwright.dev/python/docs/intro). Installation needs network access; exported playback does not.

Do not install a local AI model, request new model API keys, or call a new external inference service as part of this skill. Use the capabilities already supplied by the host, within the user's task and the host's normal permissions.

## Skill discovery

Copy the entire `typebit-line-animation` directory, including scripts, assets, references, and requirements. Copying only `SKILL.md` is insufficient.

| Host | Personal installation | Invocation |
| --- | --- | --- |
| Codex | `~/.agents/skills/typebit-line-animation/` | `$typebit-line-animation` or a matching request |
| Claude Code | `~/.claude/skills/typebit-line-animation/` | `/typebit-line-animation` or a matching request |
| Other Agent hosts | Use the host's supported skill directory, or ask it to read this `SKILL.md` directly | Host-specific |

For project-only discovery, use `.agents/skills/typebit-line-animation/` in Codex or `.claude/skills/typebit-line-animation/` in Claude Code. These are local installation instructions, not a claim that every host/cloud session exposes the same tools. See [Codex skill locations](https://learn.chatgpt.com/docs/build-skills) and [Claude Code skill locations](https://code.claude.com/docs/en/skills).

After copying the folder, resolve its installed absolute path before running helpers. The host must use an environment in which the dependencies are installed; copying a folder does not carry an existing virtual environment with it.

## Missing capabilities

| Missing capability | Honest response |
| --- | --- |
| Vision | Explain that semantic interpretation and visual review are unavailable; do not infer a photo's contents from its filename. |
| Precise subject mask | Use an existing transparent image or user-provided mask; otherwise produce a clearly labeled approximate contour/mask if feasible. State when true subject isolation remains incomplete. |
| Image tool | Continue with supported SVG and deterministic raster operations. Do not claim a new image model was used. |
| Browser | Save the HTML and source; report browser/offline playback as unverified. A static inspection is not an equivalent substitute. |
| Local commands/files | Explain that this installation needs a host with these capabilities. Do not invent file links or verification reports. |

The standalone HTML toolbar can change speed and save HTML/PNG without Python or a network connection. CLI GIF export needs the local Python dependencies and Chromium because it captures the actual player. A missing browser must produce an actionable export error, not a simulated GIF or a passing verification claim. See [export options](exports.md).
