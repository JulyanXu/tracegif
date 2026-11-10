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


def build_release(project: Path, output: Path, version: str) -> dict:
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
    with zipfile.ZipFile(project_zip) as archive:
        candidates = [item for item in archive.namelist() if Path(item).name == "animation.html"]
        if not candidates:
            raise ValueError("Editable project package is missing animation.html.")
        primary = min(candidates, key=lambda name: (name.count("/"), len(name)))
        if hashlib.sha256(archive.read(primary)).hexdigest() != report["html_sha256"]:
            raise ValueError("Editable project package is stale. Re-run package.")
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
    for extension in ("png", "gif"):
        exported = project / "exports" / f"animation.{extension}"
        sidecar = exported.with_name(exported.name + ".export.json")
        if not exported.is_file() or not sidecar.is_file():
            raise ValueError(f"Export the example as {extension.upper()} before building release attachments.")
        export_report = json.loads(sidecar.read_text(encoding="utf-8"))
        if export_report.get("source_html_sha256") != report["html_sha256"] or export_report.get("output_sha256") != sha256(exported):
            raise ValueError(f"The {extension.upper()} example export is stale. Re-run export and package.")
        name = f"typebit-example.{extension}"
        shutil.copyfile(exported, output / name)
        names.append(name)
        shutil.copyfile(sidecar, output / (name + ".export.json"))
        names.append(name + ".export.json")
    evidence_files = [(p, p.relative_to(evidence).as_posix()) for p in evidence.rglob("*") if p.is_file()]
    name = "typebit-example-verification.zip"
    zip_files(output / name, evidence_files)
    names.append(name)
    preview = evidence / "light-final.png"
    if preview.is_file():
        shutil.copyfile(preview, output / "typebit-example-preview.png")
        names.append("typebit-example-preview.png")
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
    parser.add_argument("--version", default="0.2.0")
    args = parser.parse_args()
    try:
        print(json.dumps(build_release(args.project, args.output, args.version), indent=2))
        return 0
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
