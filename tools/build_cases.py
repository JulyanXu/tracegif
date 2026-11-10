"""Rebuild original TypeBit case studies from sources and actual offline captures.

This helper never claims to perform a visual review. An Agent or human reviews
the resulting frames and may then bind review notes through the normal project
contract before refreshing the delivery files.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import re
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/typebit-line-animation/scripts"))
from typebitlib import __version__
from typebitlib.core import configure_project, package_project, prepare_project, render_project, sha256
from typebitlib.export import export_project
from typebitlib.verify import verify_html


def case_directory(root: Path, slug: str) -> Path:
    if not re.fullmatch(r"[a-z0-9-]+", slug):
        raise ValueError("Case slugs must contain only lower-case letters, numbers and hyphens.")
    directory = root / slug
    if not directory.resolve().is_relative_to(root.resolve()) or directory.is_symlink() or directory.is_junction():
        raise ValueError("Case output must stay within its root and cannot be a directory link.")
    return directory


def make_raster_source(browser, svg: Path, output: Path) -> None:
    """Render authored native artwork to PNG, not a generated replacement image."""
    context = browser.new_context(offline=True, viewport={"width": 640, "height": 480}, device_scale_factor=1)
    try:
        page = context.new_page()
        page.goto(svg.resolve().as_uri())
        page.screenshot(path=str(output), omit_background=True)
        provenance = {"schema_version": 1, "method": "Chromium SVG render",
                      "browser": browser.version,
                      "source_svg": {"file": svg.name, "sha256": sha256(svg)},
                      "output_png": {"file": output.name, "sha256": sha256(output)}}
        output.with_suffix(output.suffix + ".source.json").write_text(
            json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    finally:
        context.close()


def raster_provenance(source: Path, svg: Path) -> dict:
    """Validate the recorded render relationship without cross-platform re-rasterization."""
    path = source.with_suffix(source.suffix + ".source.json")
    if path.is_file():
        record = json.loads(path.read_text(encoding="utf-8"))
        if (record.get("schema_version") == 1
                and record.get("source_svg") == {"file": svg.name, "sha256": sha256(svg)}
                and record.get("output_png") == {"file": source.name, "sha256": sha256(source)}):
            return record
    raise ValueError(f"{source.name} has missing or stale SVG render provenance; run --refresh-raster "
                     "with a new --build-root to regenerate the PNG from its current authored SVG.")


def case_input_hashes(case: dict, examples_root: Path) -> dict:
    return {role: {"file": case[role], "sha256": sha256(examples_root / case[role])}
            for role in ("source", "contours", "source_svg") if case.get(role)}


def prepared_input_hashes(project: Path) -> dict:
    settings = json.loads((project / "project.json").read_text(encoding="utf-8"))
    paths = {"source": settings["source"]["path"], "scene": settings["scene"]}
    if settings.get("contours"):
        paths["contours"] = settings["contours"]
    return {role: {"file": relative, "sha256": sha256(project / relative)}
            for role, relative in paths.items()}


def validate_case_reuse(project: Path, case: dict, inputs: dict) -> None:
    """Refuse to silently retain contours or pixels from another authored revision."""
    record_path = project / "case-inputs.json"
    guidance = f"{case['slug']} inputs changed or lack provenance; choose a new --build-root"
    if case.get("source_svg"):
        guidance += " and use --refresh-raster if the authored SVG or PNG changed"
    guidance += " to preserve the previous project."
    if not record_path.is_file():
        raise ValueError(guidance)
    record = json.loads(record_path.read_text(encoding="utf-8"))
    if (record.get("schema_version") != 1 or record.get("authored_inputs") != inputs
            or record.get("prepared_inputs") != prepared_input_hashes(project)):
        raise ValueError(guidance)


def record_case_inputs(project: Path, inputs: dict, raster: dict | None) -> None:
    record = {"schema_version": 1, "authored_inputs": inputs,
              "prepared_inputs": prepared_input_hashes(project)}
    if raster:
        record["raster_provenance"] = raster
    (project / "case-inputs.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8")


def capture_preview(browser, source: Path, project: Path, media: Path, case: dict) -> None:
    context = browser.new_context(offline=True, viewport={"width": 480, "height": 360}, device_scale_factor=1)
    try:
        page = context.new_page()
        mime = "image/svg+xml" if source.suffix.lower() == ".svg" else "image/png"
        uri = "data:" + mime + ";base64," + base64.b64encode(source.read_bytes()).decode("ascii")
        source_preview = project / ".source-preview.html"
        source_preview.write_text(
            '<!doctype html><meta charset="utf-8"><style>html,body{margin:0;width:100%;height:100%;'
            f'background:{case["matte"]};display:grid;place-items:center}}img{{width:100%;height:100%;object-fit:contain}}</style>'
            f'<img alt="Original source artwork" src="{uri}">', encoding="utf-8")
        page.goto(source_preview.as_uri())
        original_png = page.screenshot()
        panels = [("SOURCE", original_png)]
        page.goto((project / "animation.html").as_uri())
        page.evaluate("color => {typebit.setControlsVisible(false);document.body.style.background=color;document.documentElement.style.background=color}", case["matte"])
        for label, at in [("DRAWING", case["duration"] * .68), ("FINISH", case["duration"])]:
            page.evaluate("time => typebit.seek(time)", at)
            page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
            panels.append((label, page.screenshot()))
        sheet = Image.new("RGB", (1488, 426), case["matte"])
        draw = ImageDraw.Draw(sheet)
        font = ImageFont.load_default(size=18)
        for index, (label, png) in enumerate(panels):
            left = 12 + index * 492
            draw.text((left + 14, 19), label, fill="#34433e", font=font)
            with Image.open(io.BytesIO(png)) as frame:
                sheet.paste(frame.convert("RGB"), (left, 54))
        sheet.save(media / "preview.png")
    finally:
        context.close()


def refresh_delivery(project: Path, media: Path, case: dict, build_root: Path) -> dict:
    """Refresh checksummed public records after packaging (including manual review)."""
    package = package_project(project)
    manifest = json.loads((project / "project.json").read_text(encoding="utf-8"))
    report = json.loads((project / "verification/report.json").read_text(encoding="utf-8"))
    for name, origin in {"animation.html": project / "animation.html",
                         "animation.gif": project / "exports/animation.gif",
                         "final.png": project / "exports/animation.png"}.items():
        shutil.copyfile(origin, media / name)
    for extension in ("gif", "png"):
        shutil.copyfile(project / f"exports/animation.{extension}.export.json", media / f"animation.{extension}.export.json")
    (media / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    entry = {key: case[key] for key in ("slug", "title", "title_zh", "kind", "method", "limitations", "duration", "playback_rate", "matte")}
    entry.update({"html_sha256": manifest["render"]["html_sha256"],
                  "project_zip": Path(package["zip"]).relative_to(build_root).as_posix(),
                  "project_zip_sha256": package["sha256"],
                  "automated_status": report["automated_status"],
                  "checks_passed": sum(check["status"] == "passed" for check in report["checks"]),
                  "visual_review": manifest["visual_review"],
                  "assets": {name: {"file": name, "sha256": sha256(media / name)}
                             for name in ("animation.html", "animation.gif", "final.png", "preview.png", "report.json")}})
    input_record = project / "case-inputs.json"
    if input_record.is_file():
        entry["input_provenance"] = json.loads(input_record.read_text(encoding="utf-8"))
    source_rgba = Image.open(project / manifest["source"]["path"]).convert("RGBA") if case["kind"] != "svg" else None
    if source_rgba is not None:
        with Image.open(project / "assets/subject.png") as subject:
            entry["raster_checks"] = {
                "original_rgba_preserved": source_rgba.tobytes() == subject.convert("RGBA").tobytes(),
                "transparent_corner_alpha": source_rgba.getpixel((0, 0))[3],
                "white_letter_rgba": list(source_rgba.getpixel((267, 245))),
                "no_background_removal": True,
            }
        if not entry["raster_checks"]["original_rgba_preserved"] or entry["raster_checks"]["white_letter_rgba"] != [255, 255, 255, 255]:
            raise ValueError("Controlled raster case failed original-pixel or white-letter preservation.")
    (media / "case.json").write_text(json.dumps(entry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return entry


def build_cases(build_root: Path, media_root: Path, refresh_raster: bool = False) -> dict:
    build_root, media_root = build_root.resolve(), media_root.resolve()
    build_root.mkdir(parents=True, exist_ok=True)
    media_root.mkdir(parents=True, exist_ok=True)
    cases = json.loads((ROOT / "examples/cases.json").read_text(encoding="utf-8"))["cases"]
    entries = []
    for case in cases:
        slug = case["slug"]
        project = case_directory(build_root, slug)
        media = case_directory(media_root, slug)
        source = ROOT / "examples" / case["source"]
        # Check before refresh or configure can mutate any input or existing project.
        if project.exists():
            validate_case_reuse(project, case, case_input_hashes(case, ROOT / "examples"))
        if case.get("source_svg") and (refresh_raster or not source.is_file()):
            with sync_playwright() as runtime:
                browser = runtime.chromium.launch(headless=True)
                try:
                    make_raster_source(browser, ROOT / "examples" / case["source_svg"], source)
                finally:
                    browser.close()
        raster = raster_provenance(source, ROOT / "examples" / case["source_svg"]) if case.get("source_svg") else None
        inputs = case_input_hashes(case, ROOT / "examples")
        if project.exists():
            validate_case_reuse(project, case, inputs)
        else:
            prepared = prepare_project(source, project, kind=case["kind"], duration=case["duration"],
                                       contours=ROOT / "examples" / case["contours"] if case.get("contours") else None)
            if prepared["status"] != "prepared":
                raise ValueError(f"Case preparation incomplete: {prepared}")
            record_case_inputs(project, inputs, raster)
        configure_project(project, duration=case["duration"], playback_rate=case["playback_rate"], doodle=False)
        settings_path = project / "project.json"
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        settings["name"] = case["title"]
        settings["processing"]["method"] = case["method"]
        settings["processing"]["approximation"] = False
        settings["processing"]["warnings"] = [case["limitations"]]
        settings_path.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        shutil.copyfile(ROOT / "LICENSE", project / "LICENSE")
        (project / "CASE.md").write_text(
            f'# {case["title"]}\n\n{case["use_case"]}.\n\n{case["method"]}\n\n'
            f'{case["limitations"]}\n\nOriginal artwork created for TypeBit, MIT licensed. No third-party brand, font or user-uploaded image.\n\n'
            f'Timeline: {case["duration"]} seconds; default speed: {case["playback_rate"]}x. GIF matte: {case["matte"]}.\n\n'
            f'Request: {case["prompt"]}\n\nRevision example: {case["revision_prompt"]}\n', encoding="utf-8")
        render_project(project)
        report = verify_html(project / "animation.html")
        if report["automated_status"] != "passed":
            raise ValueError(f'{slug} failed browser verification: {report["report_path"]}')
        export_project(project, format="png", width=640)
        export_project(project, format="gif", width=480, fps=10, background=case["matte"])
        media.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, media / ("source" + source.suffix.lower()))
        if case.get("source_svg"):
            shutil.copyfile(ROOT / "examples" / case["source_svg"], media / "source.svg")
        with sync_playwright() as runtime:
            browser = runtime.chromium.launch(headless=True)
            try:
                capture_preview(browser, source, project, media, case)
            finally:
                browser.close()
        entry = refresh_delivery(project, media, case, build_root)
        entries.append(entry)
        print(json.dumps({"case": slug, "status": "built", "automated_status": entry["automated_status"],
                          "visual_review": entry["visual_review"]["status"]}), flush=True)
    manifest = {"schema_version": 1, "typebit_version": __version__, "license": "MIT", "cases": entries}
    (build_root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (media_root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": "built", "case_count": len(entries), "manifest": str(build_root / "manifest.json")}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-root", type=Path, default=ROOT / "build/cases")
    parser.add_argument("--media-root", type=Path, default=ROOT / "docs/cases")
    parser.add_argument("--refresh-raster", action="store_true", help="Re-render the authored badge SVG to its source PNG")
    args = parser.parse_args()
    try:
        print(json.dumps(build_cases(args.build_root, args.media_root, args.refresh_raster), indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
