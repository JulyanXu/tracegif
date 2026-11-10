"""Reproduce this example's APPROXIMATE circular mask; not a segmenter.

The center and radius were selected after visually inspecting blue-marble.jpg.
Only the separate grayscale mask is written. The NASA photograph is untouched.
"""

from math import hypot
from pathlib import Path

from PIL import Image

SIZE = (1041, 1041)
CENTER = (520, 520)
RADIUS = 491


def create_mask(output: Path) -> None:
    width, height = SIZE
    # One-pixel coverage transition gives a soft edge without changing RGB.
    alpha = bytes(
        round(255 * min(1.0, max(0.0, RADIUS - hypot(x - CENTER[0], y - CENTER[1]) + 0.5)))
        for y in range(height)
        for x in range(width)
    )
    Image.frombytes("L", SIZE, alpha).save(output)


if __name__ == "__main__":
    directory = Path(__file__).resolve().parent
    with Image.open(directory / "blue-marble.jpg") as source:
        if source.size != SIZE:
            raise ValueError("This demo mask is only aligned to the bundled 1041 x 1041 photograph.")
    destination = directory / "blue-marble-mask.png"
    create_mask(destination)
    print(f"Wrote the example-specific approximate mask: {destination}")
