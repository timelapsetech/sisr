#!/usr/bin/env python3
"""
Simple Image Sequence Renderer (SISR) command-line interface.

This module provides the command-line interface for the SISR application,
allowing users to:
- Select input/output directories
- Set FPS and resolution
- Choose crop options (Instagram, HD, UHD)
- Add overlays (date, frame)
- Set quality options
"""

import os
import sys
import argparse
import re
from typing import Optional, List, Tuple
from sisr.core import (
    create_video_with_overlay,
    find_image_directories,
    create_date_files,
)
from sisr.gui import main as gui_main
from sisr.utils import get_ffmpeg_path


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        Parsed command line arguments

    The function defines and parses the following arguments:
    - input: Input directory containing images
    - output-dir: Output directory for rendered video
    - fps: Frames per second (default: 30)
    - resolution: Custom resolution (WxH)
    - instagram-crop: Enable Instagram square crop
    - hd-crop: HD crop type (center, keep_top, keep_bottom)
    - uhd-crop: UHD crop type (center, keep_top, keep_bottom)
    - overlay-date: Add date overlay
    - overlay-frame: Add frame number overlay
    - quality: Output quality (default, prores, proreshq, gif)
    """
    parser = argparse.ArgumentParser(description="Simple Image Sequence Renderer")

    # Required arguments
    parser.add_argument(
        "--input", required=True, help="Input directory containing images"
    )
    parser.add_argument(
        "--output-dir", required=True, help="Output directory for rendered video"
    )

    # Optional arguments
    parser.add_argument(
        "--fps", type=float, default=30, help="Frames per second (default: 30)"
    )

    # Resolution options
    parser.add_argument("--resolution", help="Custom resolution (WxH)")

    # Crop options
    crop_group = parser.add_mutually_exclusive_group()
    crop_group.add_argument(
        "--instagram-crop", action="store_true", help="Enable Instagram square crop"
    )
    crop_group.add_argument(
        "--hd-crop", choices=["center", "keep_top", "keep_bottom"], help="HD crop type"
    )
    crop_group.add_argument(
        "--uhd-crop",
        choices=["center", "keep_top", "keep_bottom"],
        help="UHD crop type",
    )

    # Overlay options
    overlay_group = parser.add_mutually_exclusive_group()
    overlay_group.add_argument(
        "--overlay-date", action="store_true", help="Add date overlay"
    )
    overlay_group.add_argument(
        "--overlay-frame", action="store_true", help="Add frame number overlay"
    )

    # Quality options
    parser.add_argument(
        "--quality",
        choices=["default", "prores", "proreshq", "gif"],
        default="default",
        help="Output quality",
    )

    # Max width/height options (only valid if no crop is selected)
    parser.add_argument(
        "--max-width", type=int, help="Maximum output width (only if no crop mode)"
    )
    parser.add_argument(
        "--max-height", type=int, help="Maximum output height (only if no crop mode)"
    )

    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    """Validate command line arguments.

    Args:
        args: Parsed command line arguments

    Raises:
        ValueError: If any argument is invalid
    """
    # Check input directory
    if not os.path.isdir(args.input):
        raise ValueError(f"Input directory does not exist: {args.input}")

    # Check output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Check FPS
    if args.fps <= 0:
        raise ValueError("FPS must be positive")

    # Check resolution format
    if args.resolution:
        try:
            width, height = map(int, args.resolution.split("x"))
            if width <= 0 or height <= 0:
                raise ValueError
        except ValueError:
            raise ValueError("Resolution must be in format WxH with positive integers")

    # Max width/height only allowed if no crop
    if (args.max_width or args.max_height) and (
        args.instagram_crop or args.hd_crop or args.uhd_crop
    ):
        raise ValueError("--max-width and --max-height can only be used if no crop mode is selected.")
    if args.max_width is not None and args.max_width <= 0:
        raise ValueError("--max-width must be a positive integer")
    if args.max_height is not None and args.max_height <= 0:
        raise ValueError("--max-height must be a positive integer")


def get_crop_type(args: argparse.Namespace) -> Optional[str]:
    """Get the crop type from command line arguments.

    Args:
        args: Parsed command line arguments

    Returns:
        Crop type string or None if no crop is selected
    """
    if args.instagram_crop:
        return "instagram"
    elif args.hd_crop:
        return f"hd_{args.hd_crop}"
    elif args.uhd_crop:
        return f"uhd_{args.uhd_crop}"
    return None


def get_overlay_type(args: argparse.Namespace) -> Optional[str]:
    """Get the overlay type from command line arguments.

    Args:
        args: Parsed command line arguments

    Returns:
        Overlay type string or None if no overlay is selected
    """
    if args.overlay_date:
        return "date"
    elif args.overlay_frame:
        return "frame"
    return None


def main() -> None:
    """Main entry point for the CLI application.

    The function:
    1. If no arguments are provided, launches the GUI
    2. Otherwise, parses command line arguments and runs in CLI mode
    3. Validates input/output directories
    4. Processes each image directory
    5. Creates videos with specified options
    """
    # If no arguments are provided, launch the GUI
    if len(sys.argv) == 1:
        gui_main()
        return

    args = parse_args()
    try:
        validate_args(args)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Validate input directory
    if not os.path.isdir(args.input):
        print(f"Error: Input directory '{args.input}' does not exist")
        sys.exit(1)

    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)

    # Find all image directories
    image_dirs = find_image_directories(args.input)
    if not image_dirs:
        print(f"No image directories found in '{args.input}'")
        sys.exit(1)

    # Process each directory
    for dir_path in image_dirs:
        # Create output filename
        dir_name = os.path.basename(dir_path)
        # Set extension based on quality
        if args.quality == "gif":
            ext = ".gif"
        elif args.quality in ["prores", "proreshq"]:
            ext = ".mov"
        else:
            ext = ".mp4"

        # Add overlay type to filename if specified
        if args.overlay_date:
            dir_name += "_date"
        elif args.overlay_frame:
            dir_name += "_frame"

        output_file = os.path.join(args.output_dir, f"{dir_name}{ext}")

        print(f"Processing directory: {dir_path}")
        print(f"Output file: {output_file}")

        # Get image files with dates if using date overlay
        if args.overlay_date:
            print("Creating date files...")
            image_date_files = create_date_files(dir_path, args.output_dir)
        else:
            # For non-date overlays, just get the image paths
            image_files = [
                f
                for f in sorted(os.listdir(dir_path))
                if f.lower().endswith((".jpg", ".jpeg", ".png", ".tiff", ".bmp"))
            ]
            image_date_files = [(os.path.join(dir_path, f), None) for f in image_files]
        if not image_date_files:
            print(f"No images found in {dir_path}")
            continue
        # Check for sequentially named images
        numbers = []
        pattern = re.compile(r"(\d+)")
        for img_path, _ in image_date_files:
            match = pattern.search(os.path.basename(img_path))
            if match:
                numbers.append(int(match.group(1)))
        numbers.sort()
        if not numbers or numbers != list(range(numbers[0], numbers[0] + len(numbers))):
            print(f"Error: The directory '{dir_name}' does not contain a sequentially named image sequence. Please ensure your images are named in order (e.g., img_0001.jpg, img_0002.jpg, ...). Skipping.")
            continue

        print(f"Found {len(image_date_files)} images")

        create_video_with_overlay(
            image_date_files=image_date_files,
            output_file=output_file,
            fps=args.fps,
            crop_type=get_crop_type(args),
            overlay_type=get_overlay_type(args),
            quality=args.quality,
            max_width=args.max_width,
            max_height=args.max_height,
        )

    print("Rendering completed successfully")


if __name__ == "__main__":
    main()
