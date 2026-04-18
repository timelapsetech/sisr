#!/usr/bin/env python3
"""Generate PNGs under ``resources/icons/`` and ``resources/icon.icns`` (macOS only)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from typing import List, Tuple

from PIL import Image, ImageDraw

# Repo root (parent of ``resources/``)
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ICONS_DIR = os.path.join(REPO_ROOT, "resources", "icons")
ICNS_OUT = os.path.join(REPO_ROOT, "resources", "icon.icns")


def create_icon(size: int) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    padding = size // 8
    film_width = size - (2 * padding)
    film_height = size - (2 * padding)

    draw.rectangle(
        [(padding, padding), (size - padding, size - padding)],
        fill="black",
        outline="white",
        width=max(2, size // 64),
    )

    handle_width = size // 3
    handle_height = size // 4
    handle_x = (size - handle_width) // 2
    handle_y = (size - handle_height) // 2

    handle_radius = size // 8
    left_handle_x = handle_x + handle_radius
    right_handle_x = handle_x + handle_width - handle_radius
    handle_y_pos = size // 2

    draw.ellipse(
        [
            (left_handle_x - handle_radius, handle_y_pos - handle_radius),
            (left_handle_x + handle_radius, handle_y_pos + handle_radius),
        ],
        fill="white",
        outline="white",
        width=max(2, size // 64),
    )

    draw.ellipse(
        [
            (right_handle_x - handle_radius, handle_y_pos - handle_radius),
            (right_handle_x + handle_radius, handle_y_pos + handle_radius),
        ],
        fill="white",
        outline="white",
        width=max(2, size // 64),
    )

    blade_length = size // 3
    blade_width = size // 16
    blade_x = handle_x + handle_width // 2
    blade_y = handle_y_pos

    draw.rectangle(
        [
            (blade_x - blade_length, blade_y - blade_width),
            (blade_x, blade_y + blade_width),
        ],
        fill="white",
        outline="white",
        width=max(2, size // 64),
    )

    draw.rectangle(
        [
            (blade_x, blade_y - blade_width),
            (blade_x + blade_length, blade_y + blade_width),
        ],
        fill="white",
        outline="white",
        width=max(2, size // 64),
    )

    return image


# PNG sizes used for GUI + iconset source files (named icon_{w}x{h}.png in ``icons/``).
PNG_SIZES = [16, 32, 64, 128, 256, 512, 1024]

# Maps Apple .iconset filename -> square size we generated (see PNG_SIZES).
ICONSET_MEMBERS: List[Tuple[str, int]] = [
    ("icon_16x16.png", 16),
    ("icon_16x16@2x.png", 32),
    ("icon_32x32.png", 32),
    ("icon_32x32@2x.png", 64),
    ("icon_128x128.png", 128),
    ("icon_128x128@2x.png", 256),
    ("icon_256x256.png", 256),
    ("icon_256x256@2x.png", 512),
    ("icon_512x512.png", 512),
    ("icon_512x512@2x.png", 1024),
]


def main() -> None:
    os.makedirs(ICONS_DIR, exist_ok=True)

    for size in PNG_SIZES:
        icon = create_icon(size)
        out = os.path.join(ICONS_DIR, f"icon_{size}x{size}.png")
        icon.save(out)
        print(f"Wrote {out}")

    if sys.platform != "darwin":
        print(
            "Skipping .icns (iconutil is macOS-only). On macOS run this script again."
        )
        return

    iconset = os.path.join(REPO_ROOT, "resources", "SISR.iconset")
    shutil.rmtree(iconset, ignore_errors=True)
    os.makedirs(iconset, exist_ok=True)

    for name, size in ICONSET_MEMBERS:
        src = os.path.join(ICONS_DIR, f"icon_{size}x{size}.png")
        if not os.path.isfile(src):
            raise SystemExit(f"Missing generated icon for size {size}: {src}")
        shutil.copy2(src, os.path.join(iconset, name))

    try:
        subprocess.run(
            ["iconutil", "-c", "icns", iconset, "-o", ICNS_OUT],
            check=True,
        )
    except FileNotFoundError:
        raise SystemExit(
            "iconutil not found; install Xcode command-line tools."
        ) from None

    print(f"Wrote {ICNS_OUT}")
    shutil.rmtree(iconset, ignore_errors=True)


if __name__ == "__main__":
    main()
