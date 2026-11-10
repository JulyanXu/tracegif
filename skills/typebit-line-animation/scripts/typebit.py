#!/usr/bin/env python3
"""Run TypeBit from any working directory; no package installation required."""

import argparse
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Agent-assisted offline SVG animation")
    parser.add_argument("--version", action="version", version="TypeBit 0.1.0")
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
    verify = sub.add_parser("verify", help="Exercise the exported file in offline Chromium")
    verify.add_argument("html", type=Path)
    verify.add_argument("--output", type=Path)
    package = sub.add_parser("package", help="Bundle the editable project with its verification")
    package.add_argument("project", type=Path)
    package.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        from typebitlib.core import TypeBitError, doctor, prepare_project, render_project, package_project
        if args.command == "doctor":
            result = doctor()
        elif args.command == "prepare":
            result = prepare_project(args.input, args.project, kind=args.kind, mask=args.mask,
                                     contours=args.contours, remove_white=args.remove_white_background,
                                     duration=args.duration, font=args.font, font_family=args.font_family)
        elif args.command == "render":
            result = render_project(args.project)
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
