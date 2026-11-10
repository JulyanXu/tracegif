"""Portable, offline-oriented project preparation and export.

Semantic interpretation belongs to the host agent. No image model is downloaded.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import html
import importlib.metadata
import importlib.util
import json
import math
import re
import shutil
import sys
import zipfile
from collections import deque
from pathlib import Path
from xml.etree import ElementTree as ET

from . import __version__

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
GEOMETRY = {"path", "rect", "circle", "ellipse", "line", "polyline", "polygon"}
ALLOWED = GEOMETRY | {"svg", "g", "defs", "clipPath", "mask", "linearGradient", "radialGradient",
                      "stop", "pattern", "title", "desc", "text", "tspan", "use", "image", "style", "symbol"}
DEFINITION = {"defs", "clipPath", "mask", "pattern", "symbol"}
ASSETS = Path(__file__).resolve().parents[2] / "assets"


class TypeBitError(ValueError):
    """A user-actionable project error."""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, data: dict):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def local_name(name: str) -> str:
    return name.rsplit("}", 1)[-1]


def safe_path(project: Path, name: str) -> Path:
    if not isinstance(name, str) or not name:
        raise TypeBitError("An asset path must be a nonempty project-relative path.")
    result = (project / name).resolve()
    if not result.is_relative_to(project.resolve()):
        raise TypeBitError(f"Asset path escapes the project: {name}")
    return result


def _finite_number(value, label, minimum=0, maximum=3600):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        raise TypeBitError(f"{label} must be a finite number.")
    if not minimum <= value <= maximum:
        raise TypeBitError(f"{label} must be between {minimum} and {maximum}.")
    return float(value)


def _safe_css(value: str):
    if re.search(r"@|\\|expression\s*\(|behavior\s*:|-moz-binding", value, re.I):
        raise TypeBitError("SVG CSS contains an unsupported import, escape, or active expression. Flatten styles first.")
    for match in re.finditer(r"url\s*\((.*?)\)", value, re.I | re.S):
        ref = match.group(1).strip(" \t\r\n\"'")
        if not re.fullmatch(r"#[A-Za-z_][\w.:-]*", ref):
            raise TypeBitError("SVG CSS references an external resource. Embed or outline it first.")


def _stylesheet_rules(value):
    value = re.sub(r"/\*.*?\*/", "", value, flags=re.S).strip()
    matches = list(re.finditer(r"([^{}]+)\{([^{}]*)\}", value))
    remainder = re.sub(r"([^{}]+)\{([^{}]*)\}", "", value).strip()
    if remainder:
        raise TypeBitError("Nested or malformed SVG CSS is unsupported. Flatten it into presentation attributes first.")
    return [(match[1].strip(), match[2]) for match in matches]


def sanitize_svg(source: str, *, allow_text=False):
    from defusedxml import ElementTree as SafeET
    try:
        root = SafeET.fromstring(source)
    except Exception as exc:
        raise TypeBitError(f"Invalid or unsafe SVG: {exc}") from exc
    if local_name(root.tag) != "svg":
        raise TypeBitError("Expected an SVG root element.")
    warnings = []
    def clean(parent, in_definition=False):
        in_definition = in_definition or local_name(parent.tag) in DEFINITION
        if local_name(parent.tag) == "use" and not in_definition:
            raise TypeBitError("Expand visible SVG <use> instances into ordinary geometry before preparation; symbol references cannot be progressively drawn.")
        if parent.tag.startswith("{") and not parent.tag.startswith("{" + SVG_NS + "}"):
            raise TypeBitError("Only the SVG namespace is supported for artwork elements.")
        for child in list(parent):
            if local_name(child.tag) not in ALLOWED:
                warnings.append(f"Removed unsupported SVG element: {local_name(child.tag)}")
                parent.remove(child)
            else:
                clean(child, in_definition)
        for attr in list(parent.attrib):
            key = local_name(attr)
            key_lower = key.lower()
            value = parent.attrib[attr]
            if key_lower.startswith("on") or key_lower in {"base", "tabindex"}:
                del parent.attrib[attr]
                warnings.append(f"Removed active SVG attribute: {key}")
            elif key_lower == "href":
                is_image = local_name(parent.tag) == "image"
                if value.startswith("#"):
                    continue
                if is_image and re.fullmatch(r"data:image/(?:png|jpeg|webp);base64,[A-Za-z0-9+/=\s]+", value):
                    continue
                raise TypeBitError("SVG references an external or unsupported resource. Embed PNG/JPEG/WebP data or use a local #id.")
            elif key_lower in {"style", "fill", "stroke", "filter", "clip-path", "mask", "cursor", "color", "font-family", "marker", "marker-start", "marker-mid", "marker-end"} or "url(" in value.lower():
                _safe_css(value)
        if local_name(parent.tag) == "style":
            _safe_css(parent.text or "")
            _stylesheet_rules(parent.text or "")
        if local_name(parent.tag) in {"text", "tspan"} and not allow_text:
            raise TypeBitError("SVG contains text without an embedded font. Convert lettering to paths, or prepare with --font PATH --font-family NAME.")
    clean(root)
    ids = set()
    for node in root.iter():
        if "id" in node.attrib:
            identity = node.get("id")
            if not re.fullmatch(r"[A-Za-z_][\w.:-]*", identity or "") or identity in ids:
                raise TypeBitError(f"SVG IDs must be unique and valid: {identity!r}")
            ids.add(identity)
    serial = 0
    def number(node, in_definition=False):
        nonlocal serial
        in_definition = in_definition or local_name(node.tag) in DEFINITION
        if local_name(node.tag) in GEOMETRY and not in_definition and not node.get("id"):
            serial += 1
            identity = f"shape-{serial:04d}"
            while identity in ids:
                serial += 1
                identity = f"shape-{serial:04d}"
            node.set("id", identity)
            ids.add(identity)
        for child in node:
            number(child, in_definition)
    number(root)
    if root.get("viewBox"):
        try:
            view_box = [float(x) for x in re.split(r"[ ,]+", root.get("viewBox").strip())]
        except ValueError as exc:
            raise TypeBitError("SVG viewBox must contain four finite numbers.") from exc
    else:
        try:
            width = float(re.sub(r"px$", "", root.get("width", "")))
            height = float(re.sub(r"px$", "", root.get("height", "")))
            view_box = [0.0, 0.0, width, height]
        except ValueError as exc:
            raise TypeBitError("SVG needs a viewBox or numeric width and height.") from exc
    if len(view_box) != 4 or not all(math.isfinite(x) for x in view_box) or min(view_box[2:]) <= 0:
        raise TypeBitError("SVG viewBox must have finite coordinates and positive dimensions.")
    root.set("viewBox", " ".join(f"{x:g}" for x in view_box))
    return root, view_box, warnings


def drawable_nodes(root):
    def visit(node, hidden=False):
        hidden = hidden or local_name(node.tag) in DEFINITION
        if local_name(node.tag) in GEOMETRY and not hidden:
            yield node
        for child in node:
            yield from visit(child, hidden)
    return list(visit(root))


def default_layers(root, duration):
    nodes = drawable_nodes(root)
    phases = {"main": [], "secondary": [], "details": []}
    for index, node in enumerate(nodes):
        phase = node.get("data-phase", "main" if index == 0 else "secondary")
        if phase not in phases:
            phase = "details"
        phases[phase].append(node)
    windows = {"main": (0, .4), "secondary": (.4, .65), "details": (.65, .85)}
    layers = []
    for phase, items in phases.items():
        lo, hi = windows[phase]
        span = (hi - lo) * duration / max(len(items), 1)
        for index, node in enumerate(items):
            layers.append({"id": node.get("id"), "label": node.get("id"), "phase": phase,
                           "start": round(lo * duration + index * span, 4), "duration": round(span, 4)})
    return layers


def border_white_candidate(image, threshold=245):
    """Remove only near-white pixels connected to the outer border."""
    from PIL import Image
    import PIL.ImageChops
    rgb = image.convert("RGB")
    channels = rgb.split()
    mask = PIL.ImageChops.darker(PIL.ImageChops.darker(channels[0], channels[1]), channels[2])
    mask = mask.point(lambda v: 255 if v >= threshold else 0).tobytes()
    width, height = image.size
    visited = bytearray(width * height)
    queue = deque()
    def add(index):
        if not visited[index] and mask[index]:
            visited[index] = 1
            queue.append(index)
    for x in range(width):
        add(x)
        add((height - 1) * width + x)
    for y in range(height):
        add(y * width)
        add(y * width + width - 1)
    while queue:
        index = queue.popleft()
        x, y = index % width, index // width
        if x: add(index - 1)
        if x + 1 < width: add(index + 1)
        if y: add(index - width)
        if y + 1 < height: add(index + width)
    alpha = bytearray(image.getchannel("A").tobytes())
    for index, removed in enumerate(visited):
        if removed:
            alpha[index] = 0
    result = image.copy()
    result.putalpha(Image.frombytes("L", image.size, bytes(alpha)))
    return result


def _data_uri(path, mime):
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def prepare_project(input_path: Path, project_path: Path, *, kind="auto", mask=None, contours=None,
                    remove_white=False, duration=10, font=None, font_family="TypeBitEmbedded"):
    from PIL import Image, ImageChops, ImageOps
    source = input_path.resolve()
    project = project_path.resolve()
    _finite_number(duration, "duration", 1, 300)
    if not source.is_file():
        raise TypeBitError(f"Input does not exist: {source}")
    if source.stat().st_size > 40 * 1024 * 1024:
        raise TypeBitError("Input exceeds the 40 MiB limit. Simplify or resize the source.")
    if project.exists() and any(project.iterdir()):
        raise TypeBitError("Project directory is not empty. Edit its project.json/scene.svg or choose a new directory.")
    if not re.fullmatch(r"[\w -]{1,80}", font_family):
        raise TypeBitError("Font family must be a simple name containing letters, numbers, spaces or hyphens.")
    warnings, needs = [], []
    extension = source.suffix.lower()
    is_svg = extension == ".svg"
    if kind == "svg" and not is_svg:
        raise TypeBitError("--kind svg requires an SVG input.")
    font_info = None
    if font:
        font = font.resolve()
        if not font.is_file() or font.suffix.lower() not in {".woff", ".woff2", ".ttf", ".otf"}:
            raise TypeBitError("Font must be a local WOFF, WOFF2, TTF or OTF file you can redistribute.")
        font_info = {"path": "assets/font" + font.suffix.lower(), "family": font_family}
    if is_svg:
        root, view_box, messages = sanitize_svg(source.read_text(encoding="utf-8-sig"), allow_text=bool(font))
        warnings.extend(messages)
        actual_kind = "svg" if kind == "auto" else kind
        method = "native-svg"
        approximate = False
        if mask or contours or remove_white:
            raise TypeBitError("Raster mask/contour/background options do not apply to SVG. Edit its background shapes directly.")
        trace_root = root
    else:
        if extension not in {".png", ".jpg", ".jpeg", ".webp"}:
            raise TypeBitError("Supported inputs are SVG, PNG, JPEG and WebP.")
        with Image.open(source) as opened:
            if opened.width * opened.height > 20_000_000:
                raise TypeBitError("Raster exceeds 20 megapixels. Resize it before preparation.")
            image = ImageOps.exif_transpose(opened).convert("RGBA")
        actual_kind = ("logo" if image.convert("RGB").getcolors(256) is not None else "photo") if kind == "auto" else kind
        if kind == "auto":
            warnings.append("Raster kind is only a palette heuristic; the host agent must inspect and confirm it.")
        view_box = [0, 0, image.width, image.height]
        if mask:
            mask = mask.resolve()
            with Image.open(mask) as opened:
                if opened.size != image.size:
                    raise TypeBitError("Mask dimensions must match the orientation-corrected original image exactly.")
                matte = opened.getchannel("A") if "A" in opened.getbands() and opened.getchannel("A").getextrema()[0] < 255 else opened.convert("L")
                image.putalpha(ImageChops.multiply(image.getchannel("A"), matte))
        elif remove_white:
            image = border_white_candidate(image)
            warnings.append("Border-connected white removal is a candidate mask; inspect white subject edges and anti-aliasing.")
        elif image.getchannel("A").getextrema()[0] == 255:
            needs.append("Provide a foreground --mask from the host image tools, or a transparent source; an opaque rectangle is not transparent artwork.")
        trace_root = None
        if contours:
            contours = contours.resolve()
            trace_root, contour_box, messages = sanitize_svg(contours.read_text(encoding="utf-8-sig"))
            warnings.extend(messages)
            if any(abs(a-b) > .001 for a, b in zip(view_box, contour_box)):
                raise TypeBitError("Contours must use viewBox='0 0 original_width original_height' to preserve alignment.")
        else:
            needs.append("Provide --contours SVG from the host agent or its image/vector tools; TypeBit does not infer semantic paths.")
        root = ET.Element(f"{{{SVG_NS}}}svg", {"viewBox": " ".join(map(str, view_box))})
        method = "approximate-contours-original-pixels"
        approximate = True
    if trace_root is not None and not drawable_nodes(trace_root):
        needs.append("No drawable paths found. Expand SVG <use> instances or convert the artwork to paths.")
    project.mkdir(parents=True, exist_ok=True)
    (project / "assets").mkdir(exist_ok=True)
    source_rel = "assets/source" + extension
    shutil.copyfile(source, project / source_rel)
    if font_info:
        shutil.copyfile(font, project / font_info["path"])
    if not is_svg:
        image.save(project / "assets/subject.png")
        if mask:
            shutil.copyfile(mask, project / ("assets/mask" + mask.suffix.lower()))
        ET.SubElement(root, f"{{{SVG_NS}}}image", {"id": "source-image", "width": str(image.width), "height": str(image.height),
                      "href": _data_uri(project / "assets/subject.png", "image/png")})
        if trace_root is not None:
            (project / "contours.svg").write_text(ET.tostring(trace_root, encoding="unicode"), encoding="utf-8")
    (project / "scene.svg").write_text(ET.tostring(root, encoding="unicode"), encoding="utf-8")
    manifest = {"schema_version": 1, "typebit_version": __version__, "revision": 0, "name": source.stem,
                "duration": duration, "fill_start": duration * .85, "playback_rate": 1.0,
                "brand_color": "#2563EB", "doodle": False,
                "source": {"path": source_rel, "sha256": sha256(source), "kind": actual_kind},
                "scene": "scene.svg", "view_box": view_box,
                "layers": default_layers(trace_root, duration) if trace_root is not None else [],
                "processing": {"method": method, "approximation": approximate, "warnings": warnings, "needs": needs},
                "visual_review": {"status": "unverified", "notes": []}}
    if not is_svg and trace_root is not None:
        manifest["contours"] = "contours.svg"
    if font_info:
        manifest["font"] = font_info
    write_json(project / "project.json", manifest)
    return {"status": "needs_input" if needs else "prepared", "project": str(project), "kind": actual_kind,
            "method": method, "layer_count": len(manifest["layers"]), "warnings": warnings, "needs": needs}


def configure_project(project_path, *, duration=None, playback_rate=None, doodle=None):
    """Change timing/preferences without reinterpreting or replacing source artwork."""
    project = Path(project_path).resolve()
    path = project / "project.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        raise TypeBitError("Unsupported project schema.")
    if all(value is None for value in (duration, playback_rate, doodle)):
        raise TypeBitError("Choose --duration, --speed, or --doodle to configure the project.")
    updated = copy.deepcopy(manifest)
    if duration is not None:
        previous = _finite_number(manifest.get("duration"), "duration", 1, 300)
        target = _finite_number(duration, "duration", 1, 300)
        ratio = target / previous
        updated["duration"] = target
        updated["fill_start"] = _finite_number(manifest.get("fill_start", previous * .85), "fill_start", 0, previous - .001) * ratio
        for layer in updated.get("layers", []):
            layer["start"] = _finite_number(layer.get("start"), "layer.start", 0, previous) * ratio
            layer["duration"] = _finite_number(layer.get("duration"), "layer.duration", .001, previous) * ratio
            if layer["duration"] < .001:
                raise TypeBitError("Requested duration makes a layer shorter than 0.001 seconds.")
    if playback_rate is not None:
        updated["playback_rate"] = _finite_number(playback_rate, "playback_rate", .25, 4)
    if doodle is not None:
        if not isinstance(doodle, bool):
            raise TypeBitError("doodle must be a boolean.")
        updated["doodle"] = doodle
    # Validate the complete result before persisting any setting, even when an
    # unrelated existing field is invalid or proportional retiming hits a limit.
    final_duration = _finite_number(updated.get("duration"), "duration", 1, 300)
    final_fill = _finite_number(updated.get("fill_start", final_duration * .85), "fill_start", 0, final_duration - .001)
    final_rate = _finite_number(updated.get("playback_rate", 1), "playback_rate", .25, 4)
    if not isinstance(updated.get("doodle", False), bool):
        raise TypeBitError("doodle must be a boolean.")
    for layer in updated.get("layers", []):
        start = _finite_number(layer.get("start"), "layer.start", 0, final_fill)
        span = _finite_number(layer.get("duration"), "layer.duration", .001, final_duration)
        if start + span > final_fill + .001:
            raise TypeBitError("A layer ends after fill_start. Correct its timing before configuring.")
    effective_duration = final_duration / final_rate
    changed = updated != manifest
    if changed:
        updated["visual_review"] = {"status": "unverified", "notes": []}
        write_json(path, updated)
    return {"status": "configured", "project": str(project), "changed": changed,
            "duration": updated["duration"], "playback_rate": updated.get("playback_rate", 1),
            "effective_duration": effective_duration,
            "next": "render, verify, export chosen formats, then package"}


def _prefix_ids(root, prefix, scope):
    ids = {node.get("id"): prefix + node.get("id") for node in root.iter() if node.get("id")}
    for node in root.iter():
        for key, value in list(node.attrib.items()):
            if key == "id":
                node.set(key, ids[value])
            elif local_name(key).lower() == "href" and value.startswith("#"):
                node.set(key, "#" + ids.get(value[1:], value[1:]))
            else:
                node.set(key, re.sub(r"url\(\s*['\"]?#([\w.:-]+)['\"]?\s*\)", lambda m: f"url(#{ids.get(m[1], m[1])})", value, flags=re.I))
        if local_name(node.tag) == "style":
            rules = []
            for selectors, declarations in _stylesheet_rules(node.text or ""):
                selectors = re.sub(r"#([A-Za-z_][\w-]*)", lambda m: "#" + ids.get(m[1], m[1]), selectors)
                selectors = ",".join(f"#{scope} {s.strip()}" for s in selectors.split(","))
                declarations = re.sub(r"url\(\s*['\"]?#([\w.:-]+)['\"]?\s*\)",
                                      lambda m: f"url(#{ids.get(m[1], m[1])})", declarations, flags=re.I)
                rules.append(selectors + "{" + declarations + "}")
            node.text = "\n".join(rules)
    return root


def _project_zip(project, output, *, include_verification=True):
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(project.rglob("*")):
            if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(project.resolve()) or path.resolve() == output.resolve():
                continue
            relative = path.relative_to(project)
            if any(part.startswith(".") or part in {"revisions", "__pycache__"} for part in relative.parts):
                continue
            if not include_verification and relative.parts[0] in {"verification", "preview", "exports"}:
                continue
            archive.write(path, relative.as_posix())


def render_project(project_path):
    project = Path(project_path).resolve()
    manifest_path = project / "project.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        raise TypeBitError("Unsupported project schema. This release reads schema_version 1.")
    duration = _finite_number(manifest.get("duration"), "duration", 1, 300)
    playback_rate = _finite_number(manifest.get("playback_rate", 1), "playback_rate", .25, 4)
    fill_start = _finite_number(manifest.get("fill_start", duration * .85), "fill_start", 0, duration - .001)
    color = manifest.get("brand_color", "#2563EB")
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
        raise TypeBitError("brand_color must be a six-digit hex color.")
    doodle = manifest.get("doodle", False)
    if not isinstance(doodle, bool):
        raise TypeBitError("doodle must be a boolean; set true only when decorative strokes are requested.")
    source_info = manifest.get("source", {})
    source = safe_path(project, source_info.get("path"))
    if sha256(source) != source_info.get("sha256"):
        raise TypeBitError("Original source changed. Preserve the source and prepare a new project instead.")
    font_info = manifest.get("font")
    root, view_box, warnings = sanitize_svg(safe_path(project, manifest["scene"]).read_text(encoding="utf-8"), allow_text=bool(font_info))
    trace_root = root
    if manifest.get("contours"):
        trace_root, contour_box, more = sanitize_svg(safe_path(project, manifest["contours"]).read_text(encoding="utf-8"))
        if view_box != contour_box:
            raise TypeBitError("Scene and contour viewBoxes no longer match.")
        warnings += more
    elif source.suffix.lower() != ".svg":
        raise TypeBitError("Raster project needs a contours SVG before rendering. Add aligned contours and update project.json.")
    needs = manifest.get("processing", {}).get("needs", [])
    if needs:
        raise TypeBitError("Resolve project.processing.needs before rendering: " + " ".join(needs))
    drawable_ids = {node.get("id") for node in drawable_nodes(trace_root)}
    layers = manifest.get("layers", [])
    if not layers or not drawable_ids:
        raise TypeBitError("No drawable contour layers. Add paths and their animation timings.")
    seen = set()
    for layer in layers:
        identity = layer.get("id")
        if identity not in drawable_ids or identity in seen:
            raise TypeBitError(f"Layer ID is missing, non-geometric, or duplicated: {identity}")
        seen.add(identity)
        start = _finite_number(layer.get("start"), f"{identity}.start", 0, fill_start)
        length = _finite_number(layer.get("duration"), f"{identity}.duration", .001, duration)
        if start + length > fill_start + .001:
            raise TypeBitError(f"Layer {identity} ends after fill_start. Adjust its start/duration.")
    if seen != drawable_ids:
        raise TypeBitError("Every drawable contour needs a stable layer entry. Add missing layers or remove unwanted contour shapes.")
    css = (ASSETS / "player.css").read_text(encoding="utf-8")
    js = (ASSETS / "player.js").read_text(encoding="utf-8")
    gif_encoder = (ASSETS / "vendor/gifenc.js").read_text(encoding="utf-8")
    if font_info:
        font_path = safe_path(project, font_info["path"])
        family = font_info.get("family", "TypeBitEmbedded")
        if not re.fullmatch(r"[\w -]{1,80}", family):
            raise TypeBitError("Invalid embedded font family name.")
        mime = {".woff": "font/woff", ".woff2": "font/woff2", ".ttf": "font/ttf", ".otf": "font/otf"}.get(font_path.suffix.lower())
        if not mime:
            raise TypeBitError("Unsupported font format.")
        css += f"\n@font-face{{font-family:'{family}';src:url('{_data_uri(font_path, mime)}')}}\n#typebit-scene text,#typebit-scene tspan{{font-family:'{family}'!important}}"
    art = _prefix_ids(copy.deepcopy(root), "art-", "typebit-art")
    trace = _prefix_ids(copy.deepcopy(trace_root), "trace-", "typebit-traces")
    for svg in (art, trace):
        for attr, value in zip(("x", "y", "width", "height"), view_box):
            svg.set(attr, f"{value:g}")
    outer = ET.Element(f"{{{SVG_NS}}}svg", {"id": "typebit-scene", "viewBox": " ".join(f"{x:g}" for x in view_box),
                         "role": "img", "aria-label": str(manifest.get("name", "TypeBit animation"))})
    ET.SubElement(outer, f"{{{SVG_NS}}}g", {"id": "typebit-doodle"})
    ET.SubElement(outer, f"{{{SVG_NS}}}g", {"id": "typebit-art"}).append(art)
    ET.SubElement(outer, f"{{{SVG_NS}}}g", {"id": "typebit-traces"}).append(trace)
    config = {"duration": duration, "fill_start": fill_start, "brand_color": color,
              "layers": layers, "doodle": doodle, "playback_rate": playback_rate}
    config_json = json.dumps(config, ensure_ascii=True).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    name = html.escape(str(manifest.get("name", "TypeBit animation")))
    markup = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="generator" content="TypeBit {__version__}"><title>{name}</title><style>{css}</style></head>
<body><main id="typebit-stage">{ET.tostring(outer, encoding="unicode")}</main>
<div id="typebit-controls" role="group" aria-label="Animation controls">
<button id="typebit-control" type="button" aria-label="Play animation">Play</button>
<button id="typebit-replay" type="button" aria-label="Replay animation">Replay</button>
<label for="typebit-speed">Speed <select id="typebit-speed" aria-label="Playback speed">
<option value="0.25">0.25×</option><option value="0.5">0.5×</option><option value="0.75">0.75×</option>
<option value="1" selected>1×</option><option value="1.5">1.5×</option><option value="2">2×</option>
<option value="3">3×</option><option value="4">4×</option></select></label>
<input id="typebit-progress" type="range" min="0" max="{duration:g}" step="0.01" value="0" aria-label="Animation progress">
<output id="typebit-time" aria-live="off">0:00</output>
<button id="typebit-download-html" type="button" title="Save offline HTML with the selected speed">Save HTML</button>
<button id="typebit-download-png" type="button" title="Save the current frame with transparency">Save PNG</button>
<button id="typebit-download-gif" type="button" title="Save the full animation as a white-background GIF at the selected speed">Save GIF</button>
<button id="typebit-cancel-export" type="button" hidden>Cancel GIF</button>
<output id="typebit-export-status" aria-live="polite"></output>
</div>
<script type="application/json" id="typebit-config">{config_json}</script><script>{gif_encoder}</script><script>{js}</script></body></html>'''
    previous = project / ".last-render.zip"
    old_revision = int(manifest.get("revision", 0))
    revisions = project / "revisions"
    if revisions.is_symlink() or revisions.is_junction() or not revisions.resolve().is_relative_to(project):
        raise TypeBitError("The revisions folder must stay inside the project and cannot be a link.")
    if previous.exists():
        destination = safe_path(project, f"revisions/r{old_revision:04d}.zip")
        if destination.exists():
            raise TypeBitError("Revision archive already exists. Restore the correct project revision before rendering.")
    derived_archives = []
    for folder in ("verification", "preview", "exports"):
        current = project / folder
        if current.exists():
            if current.is_symlink() or current.is_junction() or not current.resolve().is_relative_to(project):
                raise TypeBitError(f"The {folder} folder must stay inside the project and cannot be a link.")
            destination = safe_path(project, f"revisions/r{old_revision:04d}-{folder}")
            if destination.exists():
                raise TypeBitError(f"Previous {folder} archive already exists.")
            derived_archives.append((current, destination))
    if previous.exists():
        revisions.mkdir(exist_ok=True)
        shutil.copyfile(previous, revisions / f"r{old_revision:04d}.zip")
    for current, destination in derived_archives:
        revisions.mkdir(exist_ok=True)
        # Both paths are fixed descendants of the verified project directory.
        current.rename(destination)
    output = project / "animation.html"
    output.write_text(markup, encoding="utf-8")
    manifest["revision"] = old_revision + 1
    manifest["typebit_version"] = __version__
    manifest["view_box"] = view_box
    manifest["visual_review"] = {"status": "unverified", "notes": []}
    manifest["render"] = {"html": "animation.html", "html_sha256": sha256(output),
                          "input_sha256": _render_input_hash(project, manifest)}
    write_json(manifest_path, manifest)
    _project_zip(project, previous, include_verification=False)
    return {"status": "rendered", "html": str(output), "html_sha256": sha256(output), "revision": manifest["revision"],
            "warnings": warnings, "visual_review": "unverified"}


def _render_input_hash(project, manifest):
    inputs = copy.deepcopy(manifest)
    for key in ("render", "visual_review", "revision"):
        inputs.pop(key, None)
    paths = [manifest["scene"], manifest["source"]["path"]]
    if manifest.get("contours"):
        paths.append(manifest["contours"])
    if manifest.get("font"):
        paths.append(manifest["font"]["path"])
    payload = {"settings": inputs, "files": {name: sha256(safe_path(project, name)) for name in paths}}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=True).encode("utf-8")).hexdigest()


def require_current_render(project_path):
    """Validate the source/HTML binding before either exporting or packaging."""
    project = Path(project_path).resolve()
    manifest = json.loads((project / "project.json").read_text(encoding="utf-8"))
    if manifest.get("typebit_version") != __version__:
        raise TypeBitError("Render this project with the current TypeBit version before exporting or packaging.")
    html_path = project / "animation.html"
    if not html_path.exists() or manifest.get("render", {}).get("html_sha256") != sha256(html_path):
        raise TypeBitError("Render this project before exporting or packaging; the HTML is missing or changed.")
    if manifest.get("render", {}).get("input_sha256") != _render_input_hash(project, manifest):
        raise TypeBitError("Project settings changed or assets changed since the last render. Render and verify again before packaging.")
    # Detect editable-source changes even when the previous HTML is still present.
    snapshot = project / ".last-render.zip"
    if snapshot.exists():
        with zipfile.ZipFile(snapshot) as archive:
            for member in archive.namelist():
                if member in {"project.json", "animation.html"} or Path(member).parts[0] in {"verification", "preview", "exports"}:
                    continue
                path = safe_path(project, member)
                if not path.is_file() or hashlib.sha256(path.read_bytes()).digest() != hashlib.sha256(archive.read(member)).digest():
                    raise TypeBitError("Project assets changed since the last render. Render and verify again before packaging.")
            old = json.loads(archive.read("project.json"))
            current = copy.deepcopy(manifest)
            old.pop("visual_review", None)
            current.pop("visual_review", None)
            if old != current:
                raise TypeBitError("Project settings changed since the last render. Render and verify again before packaging.")
    return manifest


def package_project(project_path, output_path=None):
    project = Path(project_path).resolve()
    manifest = require_current_render(project)
    html_path = project / "animation.html"
    report_path = project / "verification/report.json"
    verification_status = "unverified"
    review = manifest.get("visual_review", {})
    if review.get("status") == "reviewed":
        if review.get("html_sha256") != sha256(html_path) or not review.get("notes"):
            raise TypeBitError("Visual review needs notes and the exact current html_sha256.")
    if report_path.exists():
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if report.get("html_sha256") != sha256(html_path):
            raise TypeBitError("Verification report belongs to a different HTML. Verify the current render first.")
        verification_status = report.get("automated_status", "unverified")
        if review.get("status") == "reviewed":
            report["visual_review"] = review
            write_json(report_path, report)
            report_md = project / "verification/report.md"
            if report_md.exists():
                content = report_md.read_text(encoding="utf-8")
                content = re.sub(r"Visual review:.*?(?=\n\n)",
                                 "Visual review: **reviewed** for the HTML hash above.\n\n" + "\n".join("- " + str(n) for n in review["notes"]),
                                 content, count=1, flags=re.S)
                report_md.write_text(content, encoding="utf-8")
    output = Path(output_path).resolve() if output_path else project.parent / (project.name + "-project.zip")
    if output == html_path or output.suffix.lower() != ".zip":
        raise TypeBitError("Package output must be a separate .zip file.")
    _project_zip(project, output)
    return {"status": "packaged", "zip": str(output), "sha256": sha256(output), "verification": verification_status,
            "visual_review": manifest.get("visual_review", {}).get("status", "unverified")}


def doctor():
    requirements = {"Pillow": "PIL", "defusedxml": "defusedxml", "playwright": "playwright"}
    dependencies = {}
    for distribution, module in requirements.items():
        try:
            dependencies[distribution] = {"installed": importlib.util.find_spec(module) is not None,
                                          "version": importlib.metadata.version(distribution)}
        except importlib.metadata.PackageNotFoundError:
            dependencies[distribution] = {"installed": False}
    browser = {"available": False, "reason": "Playwright is not installed"}
    if dependencies["playwright"]["installed"]:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as runtime:
                with runtime.chromium.launch(headless=True) as chromium:
                    browser = {"available": True, "version": chromium.version}
        except Exception as exc:
            browser = {"available": False, "reason": str(exc).splitlines()[0], "fix": "python -m playwright install chromium"}
    ready = sys.version_info >= (3, 12) and all(v["installed"] for v in dependencies.values()) and browser["available"]
    return {"status": "ready" if ready else "unverified", "typebit_version": __version__, "python": sys.version.split()[0],
            "dependencies": dependencies, "browser": browser,
            "host_capabilities": {"vision": "agent_must_check", "image_editing": "agent_must_check", "semantic_segmentation": "agent_must_check"},
            "note": "No model, API credentials, or GPU required by TypeBit. Host-agent connectivity is separate."}
