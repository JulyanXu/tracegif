"""Validate the self-contained release skill without third-party validators."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "typebit-line-animation"


def main():
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not match:
        raise ValueError("SKILL.md needs YAML frontmatter.")
    name = re.search(r"^name:\s*[\"']?([a-z0-9-]+)", match[1], re.M)
    if not name or name[1] != SKILL.name:
        raise ValueError("Skill name must match its folder.")
    if not re.search(r"^description:\s*\S", match[1], re.M):
        raise ValueError("A nonempty discovery description is required.")
    for relative in ["scripts/typebit.py", "requirements.txt", "assets/player.js", "assets/player.css"]:
        if not (SKILL / relative).is_file():
            raise ValueError(f"Missing bundled resource: {relative}")
    for destination in re.findall(r"\]\(([^)]+)\)", text):
        if "://" in destination or destination.startswith("#"):
            continue
        target = (SKILL / destination.split("#")[0]).resolve()
        if not target.is_relative_to(SKILL.resolve()) or not target.exists():
            raise ValueError(f"Skill reference is missing or escapes its bundle: {destination}")
    print("Skill format and bundled references validated.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
