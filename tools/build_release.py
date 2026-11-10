"""Build portable release attachments from an already verified example."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "typebit-line-animation"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def zip_files(output: Path, files: list[tuple[Path, str]]) -> None:
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source, name in sorted(files, key=lambda item: item[1]):
            info = zipfile.ZipInfo(name.replace("\\", "/"), date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, source.read_bytes())


def build_case_bundle(root: Path, output: Path) -> None:
    """Ship public examples only when their package and export evidence agree."""
    root = root.resolve()
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cases = manifest.get("cases", [])
    if not cases:
        raise ValueError("Build the public cases before creating release attachments.")
    # The build manifest describes the media directory. The release uses a
    # different layout, so every shipped path must be recorded independently.
    release_manifest = {**manifest, "artifact_type": "public-case-release", "cases": []}
    seen = set()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr("README.txt", "TypeBit public cases\nOpen each animation.html offline. GIFs have a solid background; PNGs preserve transparency.\nThe project ZIPs contain original MIT artwork, editable layers, and browser reports.\nAll paths in manifest.json are relative to this archive's root.\n")
        for case in cases:
            slug = case["slug"]
            if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug) or slug in seen:
                raise ValueError("Invalid or duplicate case slug.")
            seen.add(slug)
            package = (root / case["project_zip"]).resolve()
            if not package.is_relative_to(root) or not package.is_file() or package.suffix != ".zip":
                raise ValueError("A case package must be a ZIP inside the case build directory.")
            if case.get("automated_status") != "passed" or sha256(package) != case.get("project_zip_sha256"):
                raise ValueError(f"Case {slug} is unverified or its package is stale.")
            release_case = {**case, "project_zip": f"{slug}/{slug}-project.zip", "assets": {}}

            def add_asset(name: str, payload: bytes) -> None:
                destination = f"{slug}/{name}"
                bundle.writestr(destination, payload)
                release_case["assets"][name] = {
                    "file": destination, "sha256": hashlib.sha256(payload).hexdigest()}

            with zipfile.ZipFile(package) as editable:
                html_bytes = editable.read("animation.html")
                report_bytes = editable.read("verification/report.json")
                report = json.loads(report_bytes)
                identity = hashlib.sha256(html_bytes).hexdigest()
                if identity != case["html_sha256"] or report.get("html_sha256") != identity or report.get("automated_status") != "passed":
                    raise ValueError(f"Case {slug} has mismatched HTML and verification.")
                add_asset("animation.html", html_bytes)
                add_asset("report.json", report_bytes)
                for extension in ("gif", "png"):
                    payload = editable.read(f"exports/animation.{extension}")
                    export_report_bytes = editable.read(f"exports/animation.{extension}.export.json")
                    export_report = json.loads(export_report_bytes)
                    if export_report.get("source_html_sha256") != identity or export_report.get("output_sha256") != hashlib.sha256(payload).hexdigest():
                        raise ValueError(f"Case {slug} has a stale {extension.upper()} export.")
                    add_asset(f"animation.{extension}", payload)
                    add_asset(f"animation.{extension}.export.json", export_report_bytes)
            bundle.write(package, release_case["project_zip"])
            release_manifest["cases"].append(release_case)
        bundle.writestr("manifest.json", json.dumps(release_manifest, ensure_ascii=False, indent=2) + "\n")


def build_release(project: Path, output: Path, version: str, cases_root: Path | None = None) -> dict:
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?", version):
        raise ValueError("Use a semantic version such as 0.1.0 (without the v prefix).")
    version_source = (SKILL / "scripts" / "typebitlib" / "__init__.py").read_text(encoding="utf-8")
    declared = re.search(r'__version__\s*=\s*[\"\']([^\"\']+)', version_source)
    if not declared or declared[1] != version:
        raise ValueError("Release tag version must match the bundled TypeBit version.")
    project, output = project.resolve(), output.resolve()
    html = project / "animation.html"
    evidence = project / "verification"
    report = json.loads((evidence / "report.json").read_text(encoding="utf-8"))
    if report.get("automated_status") != "passed":
        raise ValueError("Release example must pass actual offline browser verification.")
    if report.get("html_sha256") != sha256(html):
        raise ValueError("Verification belongs to a different HTML revision. Re-run verify.")
    project_zip = project.parent / (project.name + "-project.zip")
    if not project_zip.is_file():
        raise ValueError("Run package for the example project before building release attachments.")
    export_files = []
    for extension in ("png", "gif"):
        exported = project / "exports" / f"animation.{extension}"
        sidecar = exported.with_name(exported.name + ".export.json")
        if not exported.is_file() or not sidecar.is_file():
            raise ValueError(f"Export the example as {extension.upper()} before building release attachments.")
        export_report = json.loads(sidecar.read_text(encoding="utf-8"))
        if export_report.get("source_html_sha256") != report["html_sha256"] or export_report.get("output_sha256") != sha256(exported):
            raise ValueError(f"The {extension.upper()} example export is stale. Re-run export and package.")
        export_files.extend([(exported, f"typebit-example.{extension}"),
                             (sidecar, f"typebit-example.{extension}.export.json")])
    with zipfile.ZipFile(project_zip) as archive:
        # Require canonical package members, not another revision's same-named
        # file. Re-exporting or reviewing without repackaging must fail before
        # writing attachments, even when animation.html has not changed.
        current_files = [html, evidence / "report.json", *(source for source, _ in export_files)]
        for source in current_files:
            relative = source.relative_to(project).as_posix()
            try:
                packaged = archive.read(relative)
            except KeyError as exc:
                raise ValueError(f"Editable project package is missing {relative}. Re-run package.") from exc
            if packaged != source.read_bytes():
                raise ValueError(f"Editable project package is stale: {relative}. Re-run package.")
    output.mkdir(parents=True, exist_ok=True)
    skill_files = [(p, f"typebit-line-animation/{p.relative_to(SKILL).as_posix()}")
                   for p in SKILL.rglob("*") if p.is_file()
                   and not {"__pycache__", ".venv", ".git"}.intersection(p.parts)
                   and p.suffix not in {".pyc", ".pyo"}]
    if not (SKILL / "LICENSE").is_file():
        skill_files.append((ROOT / "LICENSE", "typebit-line-animation/LICENSE"))
    names = []
    name = f"typebit-line-animation-{version}.zip"
    zip_files(output / name, skill_files)
    names.append(name)
    for source, name in [(html, "typebit-example.html"), (project_zip, "typebit-example-project.zip")]:
        shutil.copyfile(source, output / name)
        names.append(name)
    for source, name in export_files:
        shutil.copyfile(source, output / name)
        names.append(name)
    evidence_files = [(p, p.relative_to(evidence).as_posix()) for p in evidence.rglob("*") if p.is_file()]
    name = "typebit-example-verification.zip"
    zip_files(output / name, evidence_files)
    names.append(name)
    preview = evidence / "light-final.png"
    if preview.is_file():
        shutil.copyfile(preview, output / "typebit-example-preview.png")
        names.append("typebit-example-preview.png")
    name = f"typebit-cases-{version}.zip"
    build_case_bundle(cases_root or project.parent / "cases", output / name)
    names.append(name)
    manifest = {"version": version, "skill": "typebit-line-animation", "html_sha256": sha256(html),
                "automated_status": report["automated_status"], "visual_review": report.get("visual_review", {}),
                "files": [{"name": name, "sha256": sha256(output / name)} for name in sorted(names)]}
    (output / "release-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    names.append("release-manifest.json")
    (output / "SHA256SUMS").write_text("".join(f"{sha256(output / name)}  {name}\n" for name in sorted(names)), encoding="utf-8")
    return {"status": "built", "output": str(output), "files": sorted(names + ["SHA256SUMS"])}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=ROOT / "build" / "example")
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--version", default="0.3.0")
    parser.add_argument("--cases-root", type=Path, help="Public case build directory containing manifest.json")
    args = parser.parse_args()
    try:
        print(json.dumps(build_release(args.project, args.output, args.version, args.cases_root), indent=2))
        return 0
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
