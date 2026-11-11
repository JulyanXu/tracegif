"""Run the homepage's real-browser checks and save reviewable evidence."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", help="Optional deployed homepage URL; otherwise serve the local docs directory.")
    parser.add_argument("--output", type=Path, default=ROOT / "build/site-qa")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location("tracegif_site_tests", ROOT / "tests/test_site.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.LiveSiteTests.base_url = args.url
    module.LiveSiteTests.evidence_dir = output
    suite = unittest.TestLoader().loadTestsFromTestCase(module.LiveSiteTests)
    if not args.url:
        suite.addTests(unittest.TestLoader().loadTestsFromTestCase(module.PublicCaseIntegrityTests))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "url": args.url or "local docs directory served over loopback HTTP",
        "status": "passed" if result.wasSuccessful() and not result.skipped else "incomplete" if result.wasSuccessful() else "failed",
        "tests_run": result.testsRun,
        "failures": [{"test": str(test), "detail": detail} for test, detail in result.failures],
        "errors": [{"test": str(test), "detail": detail} for test, detail in result.errors],
        "skipped": [{"test": str(test), "reason": reason} for test, reason in result.skipped],
        "artifacts": [path.name for path in output.iterdir() if path.suffix in (".png", ".gif")],
        "scope": "Real homepage iframe playback, pause, speed, scrubbing, scene and language links, unobscured artwork, mobile layout, PNG/GIF downloads, downloaded HTML reopening offline, and recovery after unavailable metadata or player files. Per-case reports cover the original offline artwork.",
    }
    if not args.url:
        report["source_sha256"] = {name: hashlib.sha256((ROOT / "docs" / name).read_bytes()).hexdigest()
                                   for name in ("index.html", "site.css", "site.js", "cases/manifest.json")}
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "tests_run": result.testsRun, "report": str(output / "report.json")}))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
