"""Exercise the delivered file, with network disabled, and retain evidence.

Automation proves player behavior and self-containment, not subject fidelity.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit


class _ResourceParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.references: list[str] = []
        self.styles: list[str] = []
        self.in_style = False

    def handle_starttag(self, tag, attrs):
        self.in_style = tag.lower() == "style" or self.in_style
        for key, value in attrs:
            if value is None:
                continue
            if key.lower() in {"src", "href", "xlink:href", "poster", "data"}:
                self.references.append(value)
            elif key.lower() == "srcset":
                # A data URL has commas; srcset is unnecessary in a portable export.
                self.references.append("unsupported-srcset:" + value)
            elif key.lower() == "style":
                self.styles.append(value)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag.lower() == "style":
            self.in_style = False

    def handle_data(self, data):
        if self.in_style:
            self.styles.append(data)


def external_resources(html: str) -> list[str]:
    """Find non-embedded HTML/SVG/CSS references, including relative files."""
    parser = _ResourceParser()
    parser.feed(html)
    for css in parser.styles:
        parser.references.extend(
            match[1].strip() for match in
            re.findall(r"url\(\s*(['\"]?)(.*?)\1\s*\)", css, flags=re.I | re.S)
        )
        parser.references.extend(re.findall(r"@import\s+['\"]([^'\"]+)['\"]", css, flags=re.I))
    return sorted({ref.strip() for ref in parser.references
                   if ref.strip() and not ref.strip().startswith(("#", "data:"))})


def _save_report(report: dict, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    report["report_path"] = "report.json"
    (output / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    rows = ["# TypeBit verification", "", f"Automated checks: **{report['automated_status']}**",
            "", f"HTML SHA-256: `{report.get('html_sha256', 'unavailable')}`", "",
            "Visual review: **unverified**. An agent or human must compare the original and screenshots.", "",
            "| Check | Result | Detail |", "|---|---|---|"]
    for item in report["checks"]:
        detail = str(item.get("detail", "")).replace("|", "\\|").replace("\n", " ")
        rows.append(f"| {item['name']} | {item['status']} | {detail} |")
    rows.extend(["", "## Screenshots", ""])
    rows.extend(f"- [{item['file']}]({item['file']}): {item['background']}, {item['time']:.2f}s"
                for item in report["screenshots"])
    rows.extend(["", "The transparent-corner observation does not validate the subject mask or interior white details.", ""])
    (output / "report.md").write_text("\n".join(rows), encoding="utf-8")
    return report


def verify_html(html_path: Path, output_dir: Path | None = None) -> dict:
    html_path = Path(html_path).resolve()
    output = Path(output_dir).resolve() if output_dir else html_path.parent / "verification"
    report = {
        "schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
        "html_file": html_path.name, "automated_status": "unverified",
        "visual_review": {"status": "unverified", "required": [
            "Compare subject shape, scale and position with the source",
            "Inspect lettering, internal white areas, edges and contour density",
            "Review disclosed approximation and mask technique"]},
        "checks": [], "screenshots": [], "network_requests": [], "console_errors": [],
    }

    def record(name, passed, detail=""):
        report["checks"].append({"name": name, "status": "passed" if passed else "failed", "detail": detail})

    if not html_path.is_file():
        record("html_exists", False, "The HTML file does not exist.")
        report["automated_status"] = "failed"
        return _save_report(report, output)
    data = html_path.read_bytes()
    report["html_sha256"] = hashlib.sha256(data).hexdigest()
    try:
        external = external_resources(data.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        record("html_parse", False, str(exc))
        report["automated_status"] = "failed"
        return _save_report(report, output)
    record("embedded_resources", not external, external)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        report["checks"].append({"name": "browser_available", "status": "unverified", "detail": "Install the locked requirements and run python -m playwright install chromium."})
        report["automated_status"] = "failed" if external else "unverified"
        return _save_report(report, output)

    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=True)
        except Exception as exc:
            report["checks"].append({"name": "browser_available", "status": "unverified", "detail": str(exc)[:1500]})
            report["automated_status"] = "failed" if external else "unverified"
            return _save_report(report, output)
        try:
            context = browser.new_context(viewport={"width": 960, "height": 720}, device_scale_factor=1,
                                          offline=True, service_workers="block")
            page = context.new_page()

            def route_request(route):
                url = route.request.url
                if urlsplit(url).scheme in {"http", "https", "ws", "wss"}:
                    report["network_requests"].append(url)
                    route.abort()
                else:
                    route.continue_()

            context.route("**/*", route_request)
            page.on("pageerror", lambda error: report["console_errors"].append(str(error)))
            page.on("console", lambda message: report["console_errors"].append(message.text) if message.type == "error" else None)
            page.on("websocket", lambda socket: report["network_requests"].append(socket.url))
            page.goto(html_path.as_uri(), wait_until="load", timeout=15000)
            page.wait_for_function("window.typebit && typeof window.typebit.getState === 'function'", timeout=5000)
            state = lambda: page.evaluate("window.typebit.getState()")
            duration = float(state()["duration"])
            initial_rate = float(state().get("playbackRate", 1))
            if not 0.1 <= duration <= 300:
                raise ValueError("Duration must be between 0.1 and 300 seconds for validation.")
            report["browser"] = {"name": "chromium", "version": browser.version, "offline": True, "url_scheme": "file"}

            def check(name, action):
                try:
                    result, detail = action()
                    record(name, bool(result), detail)
                except Exception as exc:
                    record(name, False, str(exc)[:1500])

            def initial_wait():
                before = state()
                page.wait_for_timeout(180)
                after = state()
                return before["status"] == after["status"] == "idle" and abs(after["time"]) < 0.01, after
            check("initial_wait", initial_wait)

            if page.evaluate("typeof window.typebit.setPlaybackRate === 'function'"):
                def speed_continuity():
                    page.evaluate("typebit.seek(typebit.getState().duration / 4); typebit.play()")
                    before = state()
                    page.locator("#typebit-speed").select_option("2")
                    after = state()
                    page.evaluate("typebit.pause()")
                    paused = state()
                    page.locator("#typebit-speed").select_option("0.5")
                    stopped = state()
                    result = (after["playbackRate"] == 2 and after["status"] == "playing"
                              and before["time"] <= after["time"] < before["time"] + .5
                              and stopped["status"] == "paused" and stopped["time"] == paused["time"])
                    page.evaluate("typebit.setPlaybackRate(1); typebit.seek(0)")
                    return result, {"playing": after, "paused": stopped}
                check("speed_changes_without_reset", speed_continuity)

                def scrubber():
                    page.locator("#typebit-progress").evaluate("(element, value) => {element.value=value; element.dispatchEvent(new Event('input',{bubbles:true})); element.focus();}", duration / 2)
                    middle = state()
                    page.keyboard.press("ArrowRight")
                    after = state()
                    page.locator("#typebit-progress").evaluate("e => e.blur()")
                    page.evaluate("typebit.seek(0)")
                    return (middle["status"] == "paused" and abs(middle["time"] - duration / 2) < .02
                            and after["status"] == "paused"), after
                check("scrubber_seeks_without_global_shortcuts", scrubber)

            def right_no_reset():
                page.keyboard.press("ArrowRight")
                page.wait_for_timeout(180)
                before = state()
                page.keyboard.press("ArrowRight")
                after = state()
                return before["status"] == after["status"] == "playing" and after["time"] >= before["time"] - 0.03, after
            check("right_starts_without_reset", right_no_reset)

            def pause_resume():
                page.keyboard.press("Space")
                before = state()
                page.wait_for_timeout(180)
                paused = state()
                page.keyboard.press("Space")
                page.wait_for_timeout(120)
                resumed = state()
                return (before["status"] == paused["status"] == "paused"
                        and abs(before["time"] - paused["time"]) < 0.03
                        and resumed["status"] == "playing" and resumed["time"] > paused["time"]), resumed
            check("space_pauses_and_resumes", pause_resume)

            def right_resume():
                page.evaluate("window.typebit.pause()")
                before = state()
                page.keyboard.press("ArrowRight")
                page.wait_for_timeout(80)
                after = state()
                return after["status"] == "playing" and after["time"] >= before["time"], after
            check("right_resumes_pause", right_resume)

            def restart():
                page.evaluate("window.typebit.seek(Math.min(2, window.typebit.getState().duration / 2))")
                page.keyboard.press("r")
                after = state()
                return after["status"] == "playing" and after["time"] < 0.25, after
            check("r_restarts", restart)

            def repeated_event():
                page.evaluate("window.typebit.pause()")
                before = state()
                page.evaluate("document.dispatchEvent(new KeyboardEvent('keydown', {key:'r', code:'KeyR', repeat:true, bubbles:true}))")
                after = state()
                return before == after, after
            check("held_key_ignored", repeated_event)

            def editable_ignored():
                page.evaluate("window.typebit.pause(); const i=document.createElement('input'); i.id='typebit-verification-input'; document.body.append(i); i.focus();")
                before = state()
                page.keyboard.press("r")
                page.keyboard.press("ArrowRight")
                page.keyboard.press("Space")
                after = state()
                page.evaluate("document.getElementById('typebit-verification-input').remove()")
                return before == after, after
            check("editable_shortcuts_ignored", editable_ignored)

            def button_toggle():
                page.evaluate("window.typebit.pause(); window.typebit.setControlsVisible(true)")
                page.locator("#typebit-control").click()
                first = state()
                page.locator("#typebit-control").click()
                second = state()
                page.locator("#typebit-control").click()
                third = state()
                return first["status"] == third["status"] == "playing" and second["status"] == "paused", third
            check("screen_button_toggle", button_toggle)

            def actual_completion():
                if page.evaluate("typeof window.typebit.setPlaybackRate === 'function'"):
                    page.evaluate("rate => typebit.setPlaybackRate(rate)", initial_rate)
                page.evaluate("window.typebit.restart()")
                page.wait_for_function("window.typebit.getState().status === 'completed'", timeout=int(duration / initial_rate * 1000) + 7000)
                end = state()
                page.wait_for_timeout(180)
                held = state()
                return abs(end["time"] - duration) < 0.05 and held == end, held
            check("real_time_completion_and_hold", actual_completion)

            def completed_replay():
                page.keyboard.press("ArrowRight")
                after = state()
                return after["status"] == "playing" and after["time"] < 0.3, after
            check("right_replays_completed", completed_replay)

            page.evaluate("window.typebit.pause(); window.typebit.setControlsVisible(false)")
            backgrounds = {
                "light": "#f7f8fa", "dark": "#101827",
                "checker": "repeating-conic-gradient(#e1e5eb 0% 25%, #fff 0% 50%) 0 0 / 24px 24px",
            }
            for label, css in backgrounds.items():
                page.evaluate("value => {document.documentElement.style.background=value; document.body.style.background=value;}", css)
                for phase, seconds in [("start", 0), ("middle", duration / 2), ("final", duration)]:
                    page.evaluate("t => window.typebit.seek(t)", seconds)
                    page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
                    filename = f"{label}-{phase}.png"
                    page.locator("#typebit-stage").screenshot(path=str(output / filename), animations="disabled")
                    report["screenshots"].append({"file": filename, "background": label, "time": seconds})
            page.evaluate("document.documentElement.style.background='transparent'; document.body.style.background='transparent'")
            page.evaluate("window.typebit.seek(window.typebit.getState().duration)")
            transparent_file = output / "transparent-final.png"
            page.locator("#typebit-stage").screenshot(path=str(transparent_file), omit_background=True, animations="disabled")
            report["screenshots"].append({"file": transparent_file.name, "background": "transparent", "time": duration})
            try:
                from PIL import Image
                with Image.open(transparent_file).convert("RGBA") as rgba:
                    points = [(0, 0), (rgba.width-1, 0), (0, rgba.height-1), (rgba.width-1, rgba.height-1)]
                    alphas = [rgba.getpixel(point)[3] for point in points]
                report["transparency_observation"] = {"status": "passed" if all(a == 0 for a in alphas) else "unverified",
                                                      "corner_alpha": alphas, "scope": "Margins only; requires visual mask review."}
            except Exception as exc:
                report["transparency_observation"] = {"status": "unverified", "detail": str(exc)}
            record("no_network_requests", not report["network_requests"], report["network_requests"])
            record("no_browser_errors", not report["console_errors"], report["console_errors"])
        except Exception as exc:
            record("browser_execution", False, str(exc)[:1500])
        finally:
            browser.close()
    report["automated_status"] = "failed" if any(c["status"] == "failed" for c in report["checks"]) else "passed"
    return _save_report(report, output)
