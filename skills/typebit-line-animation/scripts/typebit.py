"""Forward the old repository command to the sibling TraceGIF skill."""
from pathlib import Path
import runpy
import sys

target = Path(__file__).resolve().parents[2] / "tracegif" / "scripts" / "tracegif.py"
if not target.is_file():
    raise SystemExit("Install the complete tracegif skill beside this legacy alias.")
sys.path.insert(0, str(target.parent))
runpy.run_path(str(target), run_name="__main__")
