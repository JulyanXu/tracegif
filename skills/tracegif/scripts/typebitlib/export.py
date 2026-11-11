"""Export the current portable player without reinterpreting its artwork."""

from __future__ import annotations

import hashlib
import io
import json
import math
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from .core import TypeBitError, sha256
from .verify import external_resources

FORMATS = {"html", "png", "gif"}
MAX_GIF_FRAMES = 900
MAX_GIF_PIXELS = 160_000_000
FINAL_HOLD_MS = 800


def _number(value, name, minimum, maximum):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise TypeBitError(f"{name} must be a finite number.")
    if not minimum <= value <= maximum:
        raise TypeBitError(f"{name} must be between {minimum} and {maximum}.")
    return float(value)


def _integer(value, name, minimum, maximum):
    result = _number(value, name, minimum, maximum)
    if not result.is_integer():
        raise TypeBitError(f"{name} must be an integer.")
    return int(result)


def _matte(background, format):
    if background is None:
        return "#FFFFFF" if format == "gif" else "transparent"
    if not isinstance(background, str):
        raise TypeBitError("background must be transparent or a six-digit hex color.")
    if background.lower() == "transparent":
        if format == "gif":
            raise TypeBitError("GIF requires a solid background; use PNG or HTML for true transparency.")
        return "transparent"
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", background):
        raise TypeBitError("background must be transparent or a six-digit hex color, such as #FFFFFF.")
    return background.upper()


def _destination(project, format, output):
    raw = Path(output) if output is not None else project / "exports" / f"animation.{format}"
    absolute = raw.absolute()
    target = raw.resolve()
    exports_path = project / "exports"
    exports = exports_path.resolve()
    if exports_path.is_symlink() or exports_path.is_junction() or not exports.is_relative_to(project):
        raise TypeBitError("The project's exports directory must stay inside the project and cannot be a link.")
    if absolute.is_relative_to(project) and not target.is_relative_to(project):
        raise TypeBitError("Export output escapes the project through a link or parent traversal.")
    if target.is_relative_to(project) and not target.is_relative_to(exports):
        raise TypeBitError("Write project exports inside its exports directory, not over source files or animation.html.")
    if target.suffix.lower() != f".{format}":
        raise TypeBitError(f"Output filename must end in .{format}.")
    report = target.with_name(target.name + ".export.json")
    if target.is_dir() or report.is_dir() or raw.is_symlink() or report.is_symlink():
        raise TypeBitError("Export output and report must be regular files, not directories or links.")
    # A chosen path can replace a previously exported file, never an unrelated file.
    if target.exists() or report.exists():
        try:
            previous = json.loads(report.read_text(encoding="utf-8"))
            known_export = (target.is_file() and previous.get("format") == format
                            and previous.get("output_file") == target.name
                            and previous.get("output_sha256") == sha256(target))
        except (OSError, ValueError):
            known_export = False
        if not known_export:
            raise TypeBitError("The output path already contains an unrelated or modified file. Choose a new filename.")
    return target, report


def _atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".typebit-export-", dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _html_with_speed(markup, rate):
    pattern = r'(<script type="application/json" id="typebit-config">)(.*?)(</script>)'
    match = re.search(pattern, markup, flags=re.S)
    if not match:
        raise TypeBitError("The current HTML is missing its player configuration. Render the project again.")
    config = json.loads(match.group(2))
    config["playback_rate"] = rate
    encoded = json.dumps(config, ensure_ascii=True).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return markup[:match.start(2)] + encoded + markup[match.end(2):]


def _capture(html, width, height, times, background):
    """Yield only real offline Chromium screenshots; never simulate vector playback."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise TypeBitError("Browser export needs the locked Playwright dependency and Chromium. Run doctor.") from exc
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=True)
        except Exception as exc:
            raise TypeBitError("Chromium could not start for export. Run doctor and install Playwright Chromium.") from exc
        try:
            context = browser.new_context(offline=True, service_workers="block", device_scale_factor=1,
                                          viewport={"width": width, "height": height})
            requests = []
            errors = []

            def route_request(route):
                if urlsplit(route.request.url).scheme in {"http", "https", "ws", "wss"}:
                    requests.append(route.request.url)
                    route.abort()
                else:
                    route.continue_()

            context.route("**/*", route_request)
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
            page.on("websocket", lambda socket: requests.append(socket.url))
            page.goto(html.as_uri(), wait_until="load", timeout=15000)
            page.wait_for_function("window.typebit && typeof window.typebit.seek === 'function'", timeout=5000)
            page.evaluate("async () => { await document.fonts.ready; window.typebit.setControlsVisible(false); }")
            page.evaluate("color => { document.body.style.background = color; document.documentElement.style.background = color; }", background)
            for time in times:
                page.evaluate("time => window.typebit.seek(time)", time)
                page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
                png = page.screenshot(omit_background=background == "transparent", animations="disabled")
                if requests or errors:
                    raise TypeBitError("Browser export failed: " + "; ".join(requests + errors)[:1000])
                yield png, browser.version
        finally:
            browser.close()


def export_project(project_path, *, format, output=None, width=None, fps=15, background=None, time=None, speed=None):
    """Export a fresh project's HTML, selected PNG frame, or matte-composited GIF.

    PNG time is expressed in original timeline seconds. HTML and GIF can override
    playback speed without changing the editable project. GIF has an 800 ms final
    hold and uses an opaque matte because it cannot retain smooth alpha edges.
    """
    from .core import require_current_render

    project = Path(project_path).resolve()
    manifest = require_current_render(project)
    if format not in FORMATS:
        raise TypeBitError("Export format must be html, png, or gif.")
    target, report_path = _destination(project, format, output)
    duration = _number(manifest["duration"], "duration", 1, 300)
    rate = _number(manifest.get("playback_rate", 1) if speed is None else speed, "speed", .25, 4)
    fps = _integer(fps, "fps", 1, 30)
    source_html = project / "animation.html"
    source_bytes = source_html.read_bytes()
    markup = source_bytes.decode("utf-8")
    external = external_resources(markup)
    if external:
        raise TypeBitError("Current HTML has non-embedded resources; render a self-contained file before export.")
    result = {"status": "exported", "format": format, "output_file": target.name,
              "source_html_sha256": sha256(source_html), "playback_rate": rate,
              "timeline_duration": duration, "effective_duration": duration / rate,
              "created_at": datetime.now(timezone.utc).isoformat(),
              "validation": {"embedded_resources": "passed"}}
    if format == "html":
        if width is not None or background is not None or time is not None or fps != 15:
            raise TypeBitError("HTML keeps its responsive transparent player; width, background, time, and fps are image-export options.")
        payload = source_bytes if speed is None else _html_with_speed(markup, rate).encode("utf-8")
        result["validation"]["browser_capture"] = "not_required"
    else:
        from PIL import Image

        view_box = manifest["view_box"]
        source_width = _number(view_box[2], "source width", 1, 1_000_000)
        source_height = _number(view_box[3], "source height", 1, 1_000_000)
        width = _integer(min(720, max(32, round(source_width))) if width is None else width, "width", 32, 2048)
        height = max(1, round(width * source_height / source_width))
        if height > 4096 or width * height > 8_000_000:
            raise TypeBitError("Export canvas is too large. Reduce width; height must be at most 4096 and canvas at most 8 megapixels.")
        matte = _matte(background, format)
        result.update({"width": width, "height": height, "background": matte,
                       "validation": {"embedded_resources": "passed", "browser_capture": "passed", "offline": True}})
        if format == "png":
            if speed is not None:
                raise TypeBitError("PNG is a still image; select --time in timeline seconds instead of --speed.")
            if fps != 15:
                raise TypeBitError("PNG is a still image; --fps only applies to GIF animation.")
            frame_time = duration if time is None else _number(time, "time", 0, duration)
            frames = list(_capture(source_html, width, height, [frame_time], matte))
            payload, browser_version = frames[0]
            result.update({"time": frame_time, "frame_count": 1, "browser": browser_version})
        else:
            if time is not None:
                raise TypeBitError("--time selects a PNG frame; GIF exports the complete animation.")
            steps = max(1, math.ceil(duration / rate * fps))
            if steps + 1 > MAX_GIF_FRAMES or (steps + 1) * width * height > MAX_GIF_PIXELS:
                raise TypeBitError("GIF exceeds 900 frames or 160 million frame pixels. Reduce width/fps or increase speed.")
            times = [duration * index / steps for index in range(steps + 1)]
            images = []
            browser_version = None
            for png, browser_version in _capture(source_html, width, height, times, matte):
                with Image.open(io.BytesIO(png)) as image:
                    images.append(image.convert("RGB").quantize(colors=256))
            # GIF stores 10 ms ticks. Round cumulative times to avoid per-frame drift.
            boundaries = [round(index * duration / rate / steps * 100) * 10 for index in range(steps + 1)]
            durations = [boundaries[index + 1] - boundaries[index] for index in range(steps)] + [FINAL_HOLD_MS]
            stream = io.BytesIO()
            images[0].save(stream, format="GIF", save_all=True, append_images=images[1:], duration=durations,
                           loop=0, optimize=False, disposal=2)
            payload = stream.getvalue()
            with Image.open(io.BytesIO(payload)) as encoded:
                encoded_frame_count = encoded.n_frames
            result.update({"fps": fps, "captured_frame_count": len(images), "frame_count": encoded_frame_count,
                           "duration_ms": sum(durations), "final_hold_ms": FINAL_HOLD_MS, "loop": True,
                           "browser": browser_version, "transparency": "opaque_matte"})
    result["output_sha256"] = hashlib.sha256(payload).hexdigest()
    result["bytes"] = len(payload)
    _atomic_write(target, payload)
    _atomic_write(report_path, (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return {**result, "output": str(target), "report": str(report_path)}
