#!/usr/bin/env python3
"""
Simple Image Sequence Renderer (SISR)

A Python package for rendering image sequences into videos with various options
for cropping, overlays, and output formats.

Author: Dave Klee <dave@timelapsetech.com>
Version: 0.1.0
"""

import os
import sys
import argparse
import subprocess
import tempfile
import shutil
import glob
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import piexif
import platform
from tqdm import tqdm

from .core import (
    create_video_with_overlay,
    create_date_files,
    find_image_directories,
    extract_date_time,
    format_datetime,
    get_system_font,
    parse_resolution,
)

__version__ = "0.1.0"
__author__ = "Dave Klee"
__email__ = "dave@timelapsetech.com"

__all__ = [
    "create_video_with_overlay",
    "create_date_files",
    "find_image_directories",
    "extract_date_time",
    "format_datetime",
    "get_system_font",
    "parse_resolution",
]

def create_date_files(image_dir, output_dir):
    """Create a list of image files with their dates.
    
    Args:
        image_dir (str): Directory containing source images
        output_dir (str): Directory for output files
        
    Returns:
        list: List of tuples (image_path, date_string)
        
    The function:
    1. Creates output directory if it doesn't exist
    2. Finds all image files in input directory
    3. Extracts date/time from each image
    4. Returns sorted list of (image_path, date) tuples
    """
    os.makedirs(output_dir, exist_ok=True)
    image_files = []
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.tiff', '*.bmp']:
        image_files.extend(glob.glob(os.path.join(image_dir, ext)))
        image_files.extend(glob.glob(os.path.join(image_dir, ext.upper())))
    image_files.sort()
    date_files = []
    for img_path in image_files:
        date_time = extract_date_time(img_path)
        formatted_date = format_datetime(date_time)
        date_files.append((img_path, formatted_date))
    return date_files

def get_system_font():
    """Get the appropriate system font for the current platform.
    
    Returns:
        str: Path to system font file or font name
        
    The function checks different font paths based on the operating system:
    - Windows: Returns 'Arial'
    - macOS: Checks several system font paths
    - Linux: Checks several common font paths
    
    Falls back to 'Arial' if no system font is found.
    """
    system = platform.system()
    if system == 'Windows':
        return 'Arial'
    elif system == 'Darwin':
        # Try different possible font paths on macOS
        font_paths = [
            '/System/Library/Fonts/Helvetica.ttc',
            '/System/Library/Fonts/HelveticaNeue.ttc',
            '/System/Library/Fonts/Arial.ttf',
            '/Library/Fonts/Arial.ttf'
        ]
        for font_path in font_paths:
            if os.path.exists(font_path):
                return font_path
        print("Warning: No system font found on macOS, falling back to Arial")
        return 'Arial'
    else:
        font_paths = [
            '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
            '/usr/share/fonts/TTF/Arial.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/dejavu/DejaVuSans.ttf'
        ]
        for font_path in font_paths:
            if os.path.exists(font_path):
                return font_path
        print("Warning: No system font found, falling back to Arial")
        return 'Arial'

def parse_resolution(resolution_str):
    """Parse a resolution string into width and height.
    
    Args:
        resolution_str (str): Resolution string in format 'WxH' or 'W:H'
        
    Returns:
        tuple: (width, height) as integers, or (None, None) if invalid
        
    Examples:
        >>> parse_resolution('1920x1080')
        (1920, 1080)
        >>> parse_resolution('3840:2160')
        (3840, 2160)
        >>> parse_resolution('invalid')
        (None, None)
    """
    if not resolution_str:
        return None, None
    parts = resolution_str.split('x') if 'x' in resolution_str else resolution_str.split(':')
    if len(parts) != 2:
        return None, None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None, None

def create_video_with_overlay(
    image_date_files,
    output_file,
    fps=30,
    crop_type=None,
    overlay_type=None,
    quality="default"
):
    """Create a video from image sequence with optional overlay and cropping.
    
    Args:
        image_date_files (list): List of (image_path, date_string) tuples
        output_file (str): Path for output video file
        fps (int, optional): Frames per second. Defaults to 30.
        crop_type (str, optional): Type of crop to apply. Defaults to None.
            Valid options:
            - None: No cropping
            - "instagram": Square 1080x1080
            - "hd_center", "hd_keep_top", "hd_keep_bottom": 1920x1080
            - "uhd_center", "uhd_keep_top", "uhd_keep_bottom": 3840x2160
        overlay_type (str, optional): Type of overlay to add. Defaults to None.
            Valid options:
            - None: No overlay
            - "date": Show date/time from image metadata
            - "frame": Show frame number
        quality (str, optional): Output quality setting. Defaults to "default".
            Valid options:
            - "default": H.264 high quality
            - "prores": Apple ProRes 422
            - "proreshq": Apple ProRes 422 HQ
            - "gif": Animated GIF
            
    Returns:
        str: Path to the output video file
        
    Raises:
        ValueError: If invalid crop_type, overlay_type, quality, or fps is provided
        RuntimeError: If ffmpeg command fails
        
    The function:
    1. Validates input parameters
    2. Creates temporary directory if needed
    3. Builds ffmpeg filter chain for crop and overlay
    4. Executes ffmpeg command with progress tracking
    5. Cleans up temporary files
    """
    # Validate fps
    if not isinstance(fps, (int, float)) or fps <= 0:
        raise ValueError("FPS must be a positive number")

    # Validate crop_type
    valid_crop_types = [
        None, "instagram",
        "hd_center", "hd_keep_top", "hd_keep_bottom",
        "uhd_center", "uhd_keep_top", "uhd_keep_bottom"
    ]
    if crop_type not in valid_crop_types:
        raise ValueError(f"Invalid crop_type. Must be one of: {valid_crop_types}")

    # Validate overlay_type
    valid_overlay_types = [None, "date", "frame"]
    if overlay_type not in valid_overlay_types:
        raise ValueError(f"Invalid overlay_type. Must be one of: {valid_overlay_types}")

    # Validate quality
    valid_qualities = ["default", "prores", "proreshq", "gif"]
    if quality.lower() not in valid_qualities:
        raise ValueError(f"Invalid quality. Must be one of: {valid_qualities}")

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # Create a temporary directory for intermediate files if none specified
    temp_dir = tempfile.mkdtemp(dir=os.path.dirname(output_file))
    
    try:
        # Create a temporary file for the image list
        image_list_path = os.path.join(temp_dir, "image_list.txt")
        with open(image_list_path, 'w') as f:
            for img_path, date_str in image_date_files:
                f.write(f"file '{img_path}'\n")
                f.write(f"duration {1/fps}\n")
                if overlay_type == "date" and date_str:
                    # Escape special characters in the date string
                    escaped_date = date_str.replace("'", "\\'").replace(":", "\\:").replace(" ", "\\ ")
                    f.write(f"file_packet_metadata date={escaped_date}\n")

        # Get the first image to determine original dimensions
        with Image.open(image_date_files[0][0]) as first_img:
            orig_width, orig_height = first_img.size
            orig_ratio = orig_width / orig_height

        # Build the video filter chain
        filter_chain = []
        
        # Add scaling and cropping based on crop type
        if crop_type:
            if crop_type == "instagram":
                # Instagram: 1080x1080 square
                target_width = 1080
                target_height = 1080
                # Scale down to fit within 1080x1080, maintaining aspect ratio
                filter_chain.append("scale=w=1080:h=1080:force_original_aspect_ratio=decrease")
                # Pad to 1080x1080, centering the image
                filter_chain.append("pad=w=1080:h=1080:x=(ow-iw)/2:y=(oh-ih)/2:color=black")
            elif crop_type.startswith("hd"):
                # HD: 1920x1080 (16:9)
                target_width = 1920
                target_height = 1080
                target_ratio = target_width / target_height
                
                if orig_ratio > target_ratio:
                    # Image is wider than target, scale to height
                    resize_height = target_height
                    resize_width = int(orig_ratio * resize_height)
                else:
                    # Image is taller than target, scale to width
                    resize_width = target_width
                    resize_height = int(resize_width / orig_ratio)
                
                # Calculate crop parameters based on crop type
                if crop_type == "hd_keep_top":
                    crop_y_offset = 0
                elif crop_type == "hd_keep_bottom":
                    crop_y_offset = resize_height - target_height
                else:  # center
                    crop_y_offset = int((resize_height - target_height) / 2)
                
                filter_chain.append(f"scale={resize_width}:{resize_height}")
                filter_chain.append(f"crop={target_width}:{target_height}:0:{crop_y_offset}")
                
            elif crop_type.startswith("uhd"):
                # UHD: 3840x2160 (16:9)
                target_width = 3840
                target_height = 2160
                target_ratio = target_width / target_height
                
                if orig_ratio > target_ratio:
                    # Image is wider than target, scale to height
                    resize_height = target_height
                    resize_width = int(orig_ratio * resize_height)
                else:
                    # Image is taller than target, scale to width
                    resize_width = target_width
                    resize_height = int(resize_width / orig_ratio)
                
                # Calculate crop parameters based on crop type
                if crop_type == "uhd_keep_top":
                    crop_y_offset = 0
                elif crop_type == "uhd_keep_bottom":
                    crop_y_offset = resize_height - target_height
                else:  # center
                    crop_y_offset = int((resize_height - target_height) / 2)
                
                filter_chain.append(f"scale={resize_width}:{resize_height}")
                filter_chain.append(f"crop={target_width}:{target_height}:0:{crop_y_offset}")
        
        # For GIF output, reduce resolution by half
        if quality == "gif":
            filter_chain.append("scale=iw/2:ih/2")
        
        # Add overlay if needed
        if overlay_type == "date":
            # Adjust font size based on resolution
            fontsize = 48
            if crop_type and crop_type.startswith("uhd"):
                fontsize = 96  # Double font size for UHD
            if quality == "gif":
                fontsize = fontsize // 2  # Halve font size for GIF
            
            # Use the drawtext filter with metadata
            filter_chain.append(f"drawtext=text='%{{metadata\\:date}}':fontcolor=white@0.8:fontsize={fontsize}:box=1:boxcolor=black@0.5:boxborderw=10:x=(w*0.9)-tw:y=(h*0.9)-th:fontfile=/System/Library/Fonts/Courier.dfont")
        elif overlay_type == "frame":
            filter_chain.append("drawtext=text='FRAME\\: %{frame_num}':fontcolor=white@0.8:fontsize=96:box=1:boxcolor=black@0.5:boxborderw=5:x=(w*0.05)+(w*0.9-tw)/2:y=(h*0.05)+th")
        
        # Build the ffmpeg command
        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', image_list_path,
        ]
        
        # Add filter chain if needed
        if quality == "gif":
            # For GIF output, we need to:
            # 1. Use palettegen to generate an optimal color palette
            # 2. Use paletteuse to apply the palette
            # 3. Set appropriate GIF parameters
            palette_path = os.path.join(temp_dir, "palette.png")
            cmd.extend([
                '-vf', f"{','.join(filter_chain)},split[s0][s1];[s0]palettegen=max_colors=256:stats_mode=full[p];[s1][p]paletteuse=dither=sierra2_4a:diff_mode=rectangle",
                '-loop', '1',  # Loop forever
                '-f', 'gif'
            ])
        else:
            # For non-GIF output, use the regular filter chain
            if filter_chain:
                cmd.extend(['-vf', ','.join(filter_chain)])
            
            # Add codec settings based on quality
            if quality == "prores":
                cmd.extend([
                    '-c:v', 'prores_ks',
                    '-pix_fmt', 'yuv422p10le',
                    '-profile:v', '2',  # ProRes 422
                    '-vendor', 'apl0',
                    '-movflags', '+faststart',
                    '-qscale:v', '9'  # Quality setting for standard ProRes
                ])
            elif quality == "proreshq":
                cmd.extend([
                    '-c:v', 'prores_ks',
                    '-pix_fmt', 'yuv422p10le',
                    '-profile:v', '3',  # ProRes HQ
                    '-vendor', 'apl0',
                    '-movflags', '+faststart',
                    '-qscale:v', '5'  # Higher quality setting for ProRes HQ
                ])
            else:
                # Default to high quality H.264
                cmd.extend([
                    '-c:v', 'libx264',
                    '-pix_fmt', 'yuv420p',
                    '-profile:v', 'high',
                    '-crf', '18'  # High quality, visually lossless
                ])
            
            # Add framerate
            cmd.extend(['-r', str(fps)])
        
        # Add output file
        cmd.append(output_file)
        
        # Run ffmpeg command
        print("Running ffmpeg command:", ' '.join(cmd))
        with tqdm(total=len(image_date_files), desc="Rendering video") as pbar:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            while True:
                output = process.stderr.readline()
                if output == b'' and process.poll() is not None:
                    break
                if output:
                    # Update progress bar based on frame count
                    if b'frame=' in output:
                        try:
                            frame = int(output.split(b'frame=')[1].split(b' ')[0])
                            pbar.update(frame - pbar.n)
                        except:
                            pass
            
            if process.returncode != 0:
                raise RuntimeError("ffmpeg command failed")
        
        return output_file
    finally:
        # Clean up temporary files if we created them
        shutil.rmtree(temp_dir)

def find_image_directories(root_dir):
    """Find all directories containing image files.
    
    Args:
        root_dir (str): Root directory to search in
        
    Returns:
        list: List of directory paths containing images
        
    The function:
    1. Walks through directory tree
    2. Checks for common image file extensions
    3. Returns list of directories containing images
    4. Skips hidden directories and files
    """
    image_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.bmp'}
    dirs_with_images = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if not d.startswith('.')]
        has_images = any(
            any(f.lower().endswith(ext) for ext in image_extensions)
            for f in filenames if not f.startswith('.')
        )
        if has_images:
            dirs_with_images.append(dirpath)
    return dirs_with_images

def main():
    """Command-line interface for the SISR package.
    
    Parses command-line arguments and executes video rendering with
    specified options. Supports:
    - Input/output directory selection
    - FPS setting
    - Resolution specification
    - Temporary directory
    - Crop options (Instagram, HD, UHD)
    - Overlay options (date, frame)
    - Quality settings
    """
    parser = argparse.ArgumentParser(description='Create a video from images with optional date overlay and cropping')
    
    # New format: --input INPUT --output-dir OUTPUT_DIR [options]
    parser.add_argument('--input', required=True, help='Input directory containing images')
    parser.add_argument('--output-dir', required=True, help='Output directory for rendered video')
    parser.add_argument('--fps', type=int, default=30, help='Frames per second (default: 30)')
    parser.add_argument('--resolution', help='Target resolution (e.g., 1920x1080)')
    parser.add_argument('--temp_dir', help='Directory to store temporary files (default: system temp directory)')
    parser.add_argument('--instagram-crop', action='store_true', help='Crop to Instagram story format (1080x1920)')
    parser.add_argument('--hd-crop', choices=['center', 'keep-top', 'keep-bottom'], help='Crop to HD format (1920x1080)')
    parser.add_argument('--uhd-crop', choices=['center', 'keep-top', 'keep-bottom'], help='Crop to UHD format (3840x2160)')
    parser.add_argument('--overlay-date', action='store_true', help='Add date overlay to each frame')
    parser.add_argument('--overlay-frame', action='store_true', help='Add frame number overlay to each frame')
    parser.add_argument('--quality', choices=['default', 'prores', 'proreshq', 'gif'], default='default',
                      help='Video quality setting (default: default)')
    
    args = parser.parse_args()
    
    # Convert paths to absolute paths
    args.input = os.path.abspath(args.input)
    args.output_dir = os.path.abspath(args.output_dir)
    
    if args.overlay_date and args.overlay_frame:
        print("Error: Cannot use both date and frame overlays simultaneously")
        sys.exit(1)
    
    overlay = None
    if args.overlay_date:
        overlay = 'date'
    elif args.overlay_frame:
        overlay = 'frame'
    
    crop_type = None
    if args.instagram_crop:
        crop_type = 'instagram'
    elif args.hd_crop:
        crop_type = f'hd_{args.hd_crop}'
    elif args.uhd_crop:
        crop_type = f'uhd_{args.uhd_crop}'
    
    if args.hd_crop and args.uhd_crop:
        print("Error: Cannot use both HD and UHD crops simultaneously")
        sys.exit(1)
    
    if args.instagram_crop and (args.hd_crop or args.uhd_crop):
        print("Error: Cannot use Instagram crop with HD or UHD crops")
        sys.exit(1)
    
    # Get the input directory name for the base filename
    input_dir_name = os.path.basename(os.path.normpath(args.input))
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Build the output filename with all relevant options
    base = input_dir_name
    
    # Add quality suffix
    if args.quality == "prores":
        base = f"{base}_prores"
    elif args.quality == "proreshq":
        base = f"{base}_proreshq"
    elif args.quality == "gif":
        base = f"{base}_gif"
    
    # Add crop type if specified
    if crop_type:
        base = f"{base}_{crop_type}"
    
    # Add overlay type if specified
    if overlay:
        base = f"{base}_{overlay}"
    
    # Set the correct extension based on quality
    if args.quality in ["prores", "proreshq"]:
        output_file = os.path.join(args.output_dir, f"{base}.mov")
    elif args.quality == "gif":
        output_file = os.path.join(args.output_dir, f"{base}.gif")
    else:
        output_file = os.path.join(args.output_dir, f"{base}.mp4")
    
    # Set up temp directory
    if args.temp_dir:
        temp_dir = os.path.abspath(args.temp_dir)
        os.makedirs(temp_dir, exist_ok=True)
    else:
        temp_dir = None  # Let create_video_with_overlay handle temp directory creation
    
    # Only create date files if we're using a date overlay
    if overlay == "date":
        date_files_dir = os.path.join(temp_dir or args.output_dir, 'date_files')
        image_date_files = create_date_files(args.input, date_files_dir)
    else:
        # For non-date overlays, just get the image paths
        image_files = []
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.tiff', '*.bmp']:
            image_files.extend(glob.glob(os.path.join(args.input, ext)))
            image_files.extend(glob.glob(os.path.join(args.input, ext.upper())))
        image_files.sort()
        image_date_files = [(img, None) for img in image_files]
    
    if not image_date_files:
        print("No images found to process")
        sys.exit(0)
        
    create_video_with_overlay(
        image_date_files=image_date_files,
        output_file=output_file,
        fps=args.fps,
        crop_type=crop_type,
        overlay_type=overlay,
        quality=args.quality
    )

if __name__ == "__main__":
    main()