"""Capture the real player at regular timeline positions for a README GIF."""
from __future__ import annotations

import argparse
import io
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright


def make_preview(html: Path, output: Path, frames: int = 40) -> None:
    if not 4 <= frames <= 200:
        raise ValueError("Choose between 4 and 200 frames.")
    output.parent.mkdir(parents=True, exist_ok=True)
    images = []
    panels = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            context = browser.new_context(offline=True, viewport={"width": 800, "height": 540}, device_scale_factor=1)
            page = context.new_page()
            page.goto(html.resolve().as_uri(), wait_until="load")
            page.wait_for_function("Boolean(window.typebit)")
            page.evaluate("window.typebit.setControlsVisible(false); document.body.style.background='#f7f8fa'; document.documentElement.style.background='#f7f8fa'")
            duration = float(page.evaluate("window.typebit.getState().duration"))
            playback_rate = float(page.evaluate("window.typebit.getState().playbackRate || 1"))
            for index in range(frames + 1):
                page.evaluate("time => window.typebit.seek(time)", duration * index / frames)
                page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
                png = page.locator("#typebit-stage").screenshot(animations="disabled")
                with Image.open(io.BytesIO(png)) as frame:
                    images.append(frame.convert("RGB").quantize(colors=128))
            # Source is the original artwork layer, without our tracing or decoration.
            page.evaluate("window.typebit.seek(window.typebit.getState().duration); document.getElementById('typebit-art').style.opacity='1'; document.getElementById('typebit-traces').style.opacity='0'; document.getElementById('typebit-doodle').style.opacity='0'")
            panels.append(("SOURCE", page.locator("#typebit-stage").screenshot(animations="disabled")))
            for label, time in [("DRAWING", duration / 2), ("FINISH", duration)]:
                page.evaluate("time => window.typebit.seek(time)", time)
                page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
                panels.append((label, page.locator("#typebit-stage").screenshot(animations="disabled")))
        finally:
            browser.close()
    frame_duration = max(20, round(duration / playback_rate * 1000 / frames))
    durations = [frame_duration] * len(images)
    durations[0] = 500
    durations[-1] = 1500
    images[0].save(output, save_all=True, append_images=images[1:], duration=durations, loop=0, optimize=True, disposal=2)
    # Only compose captured frames: no replacement artwork or simulated animation.
    panel_width, label_height, gutter = 480, 48, 16
    converted = []
    for label, png in panels:
        with Image.open(io.BytesIO(png)) as frame:
            panel_height = round(frame.height * panel_width / frame.width)
            converted.append((label, frame.convert("RGB").resize((panel_width, panel_height), Image.Resampling.LANCZOS)))
    sheet = Image.new("RGB", (panel_width * 3 + gutter * 4, panel_height + label_height + gutter * 2), "#f7f8fa")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=17)
    for index, (label, frame) in enumerate(converted):
        left = gutter + index * (panel_width + gutter)
        draw.text((left + 20, gutter + 12), label, fill="#34435a", font=font)
        sheet.paste(frame, (left, gutter + label_height))
    sheet.save(output.with_name("preview.png"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html", type=Path)
    parser.add_argument("--output", type=Path, default=Path("docs/media/demo.gif"))
    parser.add_argument("--frames", type=int, default=40)
    args = parser.parse_args()
    make_preview(args.html, args.output, args.frames)
    print(json.dumps({"status": "created", "file": str(args.output.resolve()), "poster": str(args.output.with_name("preview.png").resolve())}))


if __name__ == "__main__":
    main()
