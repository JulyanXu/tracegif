#!/usr/bin/env python3
"""Run TypeBit from any working directory; no package installation required."""

import argparse
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Agent-assisted offline SVG animation")
    from typebitlib import __version__
    parser.add_argument("--version", action="version", version=f"TypeBit {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Check local dependencies; host model capabilities are separate")
    prepare = sub.add_parser("prepare", help="Create an editable project without changing the input")
    prepare.add_argument("input", type=Path)
    prepare.add_argument("--project", type=Path, required=True)
    prepare.add_argument("--kind", choices=["auto", "svg", "logo", "lineart", "photo"], default="auto")
    prepare.add_argument("--mask", type=Path)
    prepare.add_argument("--contours", type=Path)
    prepare.add_argument("--remove-white-background", action="store_true")
    prepare.add_argument("--duration", type=float, default=10.0)
    prepare.add_argument("--font", type=Path)
    prepare.add_argument("--font-family", default="TypeBitEmbedded")
    render = sub.add_parser("render", help="Render the project; archive the preceding render")
    render.add_argument("project", type=Path)
    configure = sub.add_parser("configure", help="Adjust timing and preferences without rebuilding source artwork")
    configure.add_argument("project", type=Path)
    configure.add_argument("--duration", type=float, help="Timeline seconds; scales all layer timings proportionally")
    configure.add_argument("--speed", type=float, help="Default playback multiplier, 0.25–4")
    configure.add_argument("--doodle", choices=["on", "off"], help="Optional decorative strokes (off by default)")
    export = sub.add_parser("export", help="Export the current rendered project as HTML, PNG, or GIF")
    export.add_argument("project", type=Path)
    export.add_argument("--format", choices=["html", "png", "gif"], required=True)
    export.add_argument("--output", type=Path)
    export.add_argument("--width", type=int, help="Pixel width; preserves aspect ratio")
    export.add_argument("--fps", type=int, default=15, help="GIF frames per second")
    export.add_argument("--background", help="#RRGGBB matte; PNG defaults transparent, GIF defaults white")
    export.add_argument("--time", type=float, help="PNG timeline position in seconds (default final frame)")
    export.add_argument("--speed", type=float, help="Export-only playback multiplier, 0.25–4")
    verify = sub.add_parser("verify", help="Exercise the exported file in offline Chromium")
    verify.add_argument("html", type=Path)
    verify.add_argument("--output", type=Path)
    package = sub.add_parser("package", help="Bundle the editable project with its verification")
    package.add_argument("project", type=Path)
    package.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        from typebitlib.core import doctor, prepare_project, render_project, package_project, configure_project
        if args.command == "doctor":
            result = doctor()
        elif args.command == "prepare":
            result = prepare_project(args.input, args.project, kind=args.kind, mask=args.mask,
                                     contours=args.contours, remove_white=args.remove_white_background,
                                     duration=args.duration, font=args.font, font_family=args.font_family)
        elif args.command == "render":
            result = render_project(args.project)
        elif args.command == "configure":
            result = configure_project(args.project, duration=args.duration, playback_rate=args.speed,
                                       doodle=None if args.doodle is None else args.doodle == "on")
        elif args.command == "export":
            from typebitlib.export import export_project
            result = export_project(args.project, format=args.format, output=args.output, width=args.width,
                                    fps=args.fps, background=args.background, time=args.time, speed=args.speed)
        elif args.command == "verify":
            from typebitlib.verify import verify_html
            result = verify_html(args.html.resolve(), args.output.resolve() if args.output else None)
        else:
            result = package_project(args.project, args.output)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        status = result.get("automated_status", result.get("status"))
        return 1 if status in {"failed", "error"} else 2 if status == "unverified" else 0
    except Exception as exc:
        print(json.dumps({"status": "error", "error": type(exc).__name__, "message": str(exc)}, ensure_ascii=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
