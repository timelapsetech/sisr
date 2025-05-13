#!/usr/bin/env python3
"""
Simple Image Sequence Renderer (SISR) core functionality.

This module provides the core functionality for rendering image sequences
into videos with various options for cropping, overlays, and output formats.
It supports:
- Multiple output formats (MP4, MOV, GIF)
- Various crop options (Instagram, HD, UHD)
- Date and frame number overlays
- Progress tracking
- Temporary file handling
"""

import os
import sys
import subprocess
import tempfile
import shutil
import glob
from datetime import datetime
from typing import List, Tuple, Optional, Union, Dict, Any
from PIL import Image, ImageFont, ImageDraw
import piexif
import platform
from tqdm import tqdm
import atexit
from .utils import get_ffmpeg_path

def inspect_exif(image_path: str) -> None:
    """Inspect and print all EXIF data from an image.
    
    Args:
        image_path: Path to the image file
    """
    print(f"\nInspecting EXIF data for: {image_path}")
    try:
        # Try PIL first
        with Image.open(image_path) as img:
            print("\nPIL EXIF data:")
            exif_data = img._getexif() if hasattr(img, '_getexif') else None
            if exif_data:
                for tag_id, value in exif_data.items():
                    print(f"Tag {tag_id}: {value}")
            else:
                print("No EXIF data found in PIL")
            
            # Try piexif
            try:
                print("\nPiexif data:")
                exif_dict = piexif.load(img.info.get('exif', b''))
                for ifd in ("0th", "Exif", "GPS", "1st"):
                    if ifd in exif_dict:
                        print(f"\n{ifd} IFD:")
                        for tag_id, value in exif_dict[ifd].items():
                            print(f"Tag {tag_id}: {value}")
            except Exception as e:
                print(f"Piexif error: {e}")
    except Exception as e:
        print(f"Error inspecting image: {e}")

def extract_date_time(image_path: str) -> str:
    """Extract date and time from image metadata.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Date and time in format 'YYYY:MM:DD HH:MM:SS'
        
    The function tries multiple methods to extract the date:
    1. EXIF data using PIL
    2. EXIF data using piexif
    3. File modification time as fallback
    """
    try:
        # Try PIL first
        with Image.open(image_path) as img:
            exif_data = img._getexif() if hasattr(img, '_getexif') else None
            
            if exif_data:
                # Try DateTimeOriginal (36867) first
                if 36867 in exif_data:
                    date_str = exif_data[36867]
                    if date_str and isinstance(date_str, str):
                        formatted_date = format_datetime(date_str)
                        if formatted_date and validate_date(formatted_date):
                            return formatted_date
                # Then try DateTime (306)
                elif 306 in exif_data:
                    date_str = exif_data[306]
                    if date_str and isinstance(date_str, str):
                        formatted_date = format_datetime(date_str)
                        if formatted_date and validate_date(formatted_date):
                            return formatted_date
            
            # Try piexif if PIL didn't find it
            try:
                exif_bytes = img.info.get('exif', b'')
                if exif_bytes:
                    exif_dict = piexif.load(exif_bytes)
                    
                    # Check ExifIFD.DateTimeOriginal (36867)
                    if "Exif" in exif_dict and piexif.ExifIFD.DateTimeOriginal in exif_dict["Exif"]:
                        date_str = exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal].decode('utf-8')
                        if date_str and isinstance(date_str, str):
                            formatted_date = format_datetime(date_str)
                            if formatted_date and validate_date(formatted_date):
                                return formatted_date
                    # Check 0th.DateTime (306)
                    elif "0th" in exif_dict and 306 in exif_dict["0th"]:
                        date_str = exif_dict["0th"][306].decode('utf-8')
                        if date_str and isinstance(date_str, str):
                            formatted_date = format_datetime(date_str)
                            if formatted_date and validate_date(formatted_date):
                                return formatted_date
                    # Check for Pentax-specific date fields
                    elif "0th" in exif_dict:
                        # Try to combine Date and Time fields if they exist
                        date = exif_dict["0th"].get(306, b'').decode('utf-8')  # Date field
                        time = exif_dict["0th"].get(307, b'').decode('utf-8')  # Time field
                        if date and time:
                            date_str = f"{date} {time}"
                            if date_str and isinstance(date_str, str):
                                formatted_date = format_datetime(date_str)
                                if formatted_date and validate_date(formatted_date):
                                    return formatted_date
            except Exception:
                pass
        
        # If no EXIF data found, use file modification time
        mod_time = os.path.getmtime(image_path)
        date = datetime.fromtimestamp(mod_time).strftime('%Y:%m:%d %H:%M:%S')
        return date
    except Exception:
        # Return current time as fallback
        date = datetime.now().strftime('%Y:%m:%d %H:%M:%S')
        return date

def format_datetime(datetime_str: str) -> str:
    """Format a date/time string for display.
    
    Args:
        datetime_str: Date/time string in format 'YYYY:MM:DD HH:MM:SS'
        
    Returns:
        Formatted date/time string like 'Monday, January 1, 2024 12:00PM'
        
    If the input string cannot be parsed, returns it unchanged.
    """
    try:
        # Try parsing with the standard format
        dt = datetime.strptime(datetime_str, '%Y:%m:%d %H:%M:%S')
        formatted = dt.strftime('%A, %B %d, %Y %I:%M%p')
        return formatted
    except ValueError:
        try:
            # Try parsing with just the date part
            dt = datetime.strptime(datetime_str, '%Y:%m:%d')
            formatted = dt.strftime('%A, %B %d, %Y')
            return formatted
        except ValueError:
            return datetime_str

def validate_date(date_str: str) -> bool:
    """Validate if a string is a properly formatted date.
    
    Args:
        date_str: Date string to validate
        
    Returns:
        True if valid date, False otherwise
    """
    try:
        datetime.strptime(date_str, '%A, %B %d, %Y %I:%M%p')
        return True
    except ValueError:
        try:
            datetime.strptime(date_str, '%A, %B %d, %Y')
            return True
        except ValueError:
            return False

def create_date_files(image_dir: str, output_dir: str) -> List[Tuple[str, str]]:
    """Create a list of image files with their dates.
    
    Args:
        image_dir: Directory containing source images
        output_dir: Directory for output files
        
    Returns:
        List of tuples (image_path, date_string)
        
    The function:
    1. Creates output directory if it doesn't exist
    2. Finds all image files in input directory
    3. Extracts date/time from each image
    4. Returns sorted list of (image_path, date) tuples
    """
    os.makedirs(output_dir, exist_ok=True)
    image_files = []
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.tiff', '*.bmp']:
        found = glob.glob(os.path.join(image_dir, ext))
        found.extend(glob.glob(os.path.join(image_dir, ext.upper())))
        image_files.extend(found)
    
    image_files.sort()
    
    date_files = []
    for img_path in image_files:
        date_time = extract_date_time(img_path)
        
        # Ensure we have a valid date string
        if not date_time:
            date_time = datetime.now().strftime('%Y:%m:%d %H:%M:%S')
        
        formatted_date = format_datetime(date_time)
        
        # Ensure we have a valid formatted date
        if not formatted_date:
            formatted_date = datetime.now().strftime('%A, %B %d, %Y %I:%M%p')
        
        date_files.append((img_path, formatted_date))
    
    return date_files

def get_system_font() -> str:
    """Get the appropriate system font for the current platform.
    
    Returns:
        Path to system font file or font name
        
    The function checks different font paths based on the operating system:
    - Windows: Returns 'Courier New'
    - macOS: Checks several system font paths
    - Linux: Checks several common font paths
    
    Falls back to 'Courier' if no system font is found.
    """
    system = platform.system()
    if system == 'Windows':
        return 'Courier New'
    elif system == 'Darwin':
        # Try different possible font paths on macOS
        font_paths = [
            '/System/Library/Fonts/Courier.ttc',
            '/System/Library/Fonts/Courier New.ttf',
            '/Library/Fonts/Courier New.ttf',
            '/System/Library/Fonts/Monaco.ttf'
        ]
        for font_path in font_paths:
            if os.path.exists(font_path):
                return font_path
        print("Warning: No monospace font found on macOS, falling back to Courier")
        return 'Courier'
    else:
        font_paths = [
            '/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf',
            '/usr/share/fonts/TTF/Courier.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',
            '/usr/share/fonts/dejavu/DejaVuSansMono.ttf'
        ]
        for font_path in font_paths:
            if os.path.exists(font_path):
                return font_path
        print("Warning: No monospace font found, falling back to Courier")
        return 'Courier'

def parse_resolution(resolution_str: Optional[str]) -> Tuple[Optional[int], Optional[int]]:
    """Parse a resolution string into width and height.
    
    Args:
        resolution_str: Resolution string in format 'WxH' or 'W:H'
        
    Returns:
        Tuple of (width, height) as integers, or (None, None) if invalid
        
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
    image_date_files: List[Tuple[str, str]],
    output_file: str,
    fps: Union[int, float] = 30,
    crop_type: Optional[str] = None,
    overlay_type: Optional[str] = None,
    quality: str = "default"
) -> str:
    """Create a video from image sequence with optional overlay and cropping."""
    if not isinstance(fps, (int, float)) or fps <= 0:
        raise ValueError(f"FPS must be a positive number, but got {fps}")

    if not image_date_files:
        raise ValueError("Image sequence list (image_date_files) cannot be empty.")

    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Get the first image to determine dimensions
    first_img_path = image_date_files[0][0]
    with Image.open(first_img_path) as first_img:
        width, height = first_img.size
        
    # Initialize crop coordinates
    x = y = 0
        
    # Apply cropping if specified
    if crop_type:
        if crop_type == "instagram":
            # Instagram crop (1080x1920 - 9:16 aspect ratio)
            target_width, target_height = 1080, 1920
            if width / height > target_width / target_height:
                # Image is wider than 9:16
                new_width = int(height * target_width / target_height)
                # Ensure width is even
                new_width = new_width - (new_width % 2)
                x = (width - new_width) // 2
                if crop_type == "instagram_keep_top":
                    y = 0
                elif crop_type == "instagram_keep_bottom":
                    y = height - target_height
                else:  # center
                    y = (height - target_height) // 2
                width = new_width
            else:
                # Image is taller than 9:16
                new_height = int(width * target_height / target_width)
                # Ensure height is even
                new_height = new_height - (new_height % 2)
                y = (height - new_height) // 2
                if crop_type == "instagram_keep_top":
                    y = 0
                elif crop_type == "instagram_keep_bottom":
                    y = height - new_height
                else:  # center
                    y = (height - new_height) // 2
                height = new_height
        elif crop_type.startswith("hd_"):
            # HD crop (1920x1080)
            target_width, target_height = 1920, 1080
            if width / height > target_width / target_height:
                # Image is wider than 16:9
                new_width = int(height * target_width / target_height)
                # Ensure width is even
                new_width = new_width - (new_width % 2)
                x = (width - new_width) // 2
                if crop_type == "hd_keep_top":
                    y = 0
                elif crop_type == "hd_keep_bottom":
                    y = height - target_height
                else:  # center
                    y = (height - target_height) // 2
                width = new_width
            else:
                # Image is taller than 16:9
                new_height = int(width * target_height / target_width)
                # Ensure height is even
                new_height = new_height - (new_height % 2)
                y = (height - new_height) // 2
                if crop_type == "hd_keep_top":
                    y = 0
                elif crop_type == "hd_keep_bottom":
                    y = height - new_height
                else:  # center
                    y = (height - new_height) // 2
                height = new_height
        elif crop_type.startswith("uhd_"):
            # UHD crop (3840x2160)
            target_width, target_height = 3840, 2160
            if width / height > target_width / target_height:
                # Image is wider than 16:9
                new_width = int(height * target_width / target_height)
                # Ensure width is even
                new_width = new_width - (new_width % 2)
                x = (width - new_width) // 2
                if crop_type == "uhd_keep_top":
                    y = 0
                elif crop_type == "hd_keep_bottom":
                    y = height - target_height
                else:  # center
                    y = (height - target_height) // 2
                width = new_width
            else:
                # Image is taller than 16:9
                new_height = int(width * target_height / target_width)
                # Ensure height is even
                new_height = new_height - (new_height % 2)
                y = (height - new_height) // 2
                if crop_type == "uhd_keep_top":
                    y = 0
                elif crop_type == "hd_keep_bottom":
                    y = height - new_height
                else:  # center
                    y = (height - new_height) // 2
                height = new_height

    # Build output filename with options
    base_name = os.path.splitext(output_file)[0]
    ext = os.path.splitext(output_file)[1]
    
    # Add quality suffix
    if quality == "gif":
        ext = ".gif"
    elif quality in ["prores", "proreshq"]:
        ext = ".mov"
    
    # Build options string
    options = []
    if crop_type:
        options.append(crop_type)
    if overlay_type:
        options.append(overlay_type)
    if quality != "default":
        options.append(quality)
    
    # Create final output filename
    if options:
        output_file = f"{base_name}_{'_'.join(options)}{ext}"

    # Build base FFmpeg command
    base_cmd = [get_ffmpeg_path(), '-y', '-framerate', str(fps)]
    
    # Add input pattern for image sequence
    input_dir = os.path.dirname(image_date_files[0][0])
    first_filename = os.path.basename(image_date_files[0][0])
    base_name = first_filename.split('_')[0]
    ext = os.path.splitext(first_filename)[1]
    seq_part = first_filename.split('_')[1].split('.')[0]
    num_digits = len(seq_part)
    pattern = f"{base_name}_%0{num_digits}d{ext}"
    input_path = os.path.join(input_dir, pattern)
    base_cmd.extend(['-i', input_path])
    
    # Build filter chain
    filter_chain = []
    
    # Add text overlay if specified
    if overlay_type:
        # Get font path
        font_path = get_system_font()
        
        # Calculate font size based on image dimensions
        font_size = int(min(width, height) * 0.05)
        
        # Calculate box padding (15% of font size)
        box_padding = int(font_size * 0.25)
        
        ffmpeg_font_path = font_path.replace("\\", "/")

        if overlay_type == "date":
            temp_dir = tempfile.mkdtemp()
            
            num_frames = len(image_date_files)
            num_digits_for_frame_files = len(str(num_frames - 1)) if num_frames > 0 else 1

            # Generate one text file per frame and store their paths
            frame_date_file_paths = []
            for i, (_, date_str) in enumerate(image_date_files):
                frame_date_filename = f"date_{i:0{num_digits_for_frame_files}d}.txt"
                full_frame_date_path = os.path.join(temp_dir, frame_date_filename)
                content = date_str if date_str else "No date available"
                with open(full_frame_date_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                frame_date_file_paths.append(full_frame_date_path.replace("\\", "/"))

            filter_parts = []
            current_input_stream = "[0:v]"
            if crop_type:
                filter_parts.append(f"[0:v]crop={width}:{height}:{x}:{y}[v_cropped]")
                current_input_stream = "[v_cropped]"
            
            # Chain drawtext filters, one for each frame
            for i in range(num_frames):
                textfile_for_this_frame = frame_date_file_paths[i]
                output_stream_label = f"[v{i}]" if i < num_frames - 1 else "[v_out]"
                
                drawtext_filter = (
                    f"{current_input_stream}"
                    f"drawtext=textfile='{textfile_for_this_frame}'"
                    f":fontfile='{ffmpeg_font_path}'"
                    f":fontsize={font_size}"
                    f":fontcolor=white"
                    f":box=1"
                    f":boxcolor=black@0.5"
                    f":boxborderw={box_padding}"
                    f":x=(w-text_w-{int(width*0.05)})"
                    f":y=(h-text_h-{int(height*0.05)})"
                    f":enable='eq(n,{i})'"
                    f"{output_stream_label}"
                )
                filter_parts.append(drawtext_filter)
                current_input_stream = output_stream_label
            
            if not filter_parts:
                if current_input_stream == "[0:v]":
                    base_cmd.extend(['-map', '0:v'])
                else:
                    base_cmd.extend(['-filter_complex', f"{current_input_stream}[v_out]"])
                    base_cmd.extend(['-map', '[v_out]'])
            elif num_frames == 0:
                 base_cmd.extend(['-map', current_input_stream.replace("[","[").replace("]","") if crop_type else '0:v'])
            else:
                filter_complex = ';'.join(filter_parts)
                base_cmd.extend(['-filter_complex', filter_complex])
                base_cmd.extend(['-map', '[v_out]'])
            
            def cleanup():
                try:
                    shutil.rmtree(temp_dir)
                except Exception:
                    pass
            atexit.register(cleanup)

        elif overlay_type == "frame":
            temp_dir = tempfile.mkdtemp()
            num_frames = len(image_date_files)

            # Generate one text file per frame for frame numbers
            frame_num_file_paths = []
            for i in range(num_frames):
                frame_num_text = f"FRAME: {i}"
                frame_num_filename = f"framenum_{i}.txt"
                full_frame_num_path = os.path.join(temp_dir, frame_num_filename)
                with open(full_frame_num_path, 'w', encoding='utf-8') as f:
                    f.write(frame_num_text)
                frame_num_file_paths.append(full_frame_num_path.replace("\\", "/"))

            filter_parts = []
            current_input_stream = "[0:v]"
            if crop_type:
                filter_parts.append(f"[0:v]crop={width}:{height}:{x}:{y}[v_cropped]")
                current_input_stream = "[v_cropped]"

            # Chain drawtext filters for frame numbers
            for i in range(num_frames):
                textfile_for_this_frame = frame_num_file_paths[i]
                output_stream_label = f"[v{i}_frame]" if i < num_frames - 1 else "[v_out]"
                
                drawtext_filter = (
                    f"{current_input_stream}"
                    f"drawtext=textfile='{textfile_for_this_frame}'"
                    f":fontfile='{ffmpeg_font_path}'"
                    f":fontsize={font_size}"
                    f":fontcolor=white"
                    f":box=1:boxcolor=black@0.5:boxborderw={box_padding}"
                    f":x=(w-text_w)/2"
                    f":y={int(height*0.05)}"
                    f":enable='eq(n,{i})'"
                    f":fix_bounds=true"
                    f"{output_stream_label}"
                )
                filter_parts.append(drawtext_filter)
                current_input_stream = output_stream_label

            if not filter_parts and num_frames > 0:
                if current_input_stream == "[0:v]":
                    base_cmd.extend(['-map', '0:v'])
                else:
                    filter_complex = f"{current_input_stream}[v_out]"
                    base_cmd.extend(['-filter_complex', filter_complex])
                    base_cmd.extend(['-map', '[v_out]'])
            elif num_frames == 0:
                if current_input_stream == "[0:v]":
                     base_cmd.extend(['-map', '0:v']) 
                else:
                     base_cmd.extend(['-filter_complex', f"{current_input_stream}[v_out]"])
                     base_cmd.extend(['-map', '[v_out]'])
            else:
                filter_complex = ';'.join(filter_parts)
                base_cmd.extend(['-filter_complex', filter_complex])
                base_cmd.extend(['-map', '[v_out]'])

            def cleanup_frame_num_tempdir():
                try:
                    shutil.rmtree(temp_dir)
                except Exception:
                    pass
            atexit.register(cleanup_frame_num_tempdir)

    # If no overlay_type was specified, but cropping was, we need to handle that.
    elif not overlay_type and crop_type:
        filter_complex = f"[0:v]crop={width}:{height}:{x}:{y}[v_out]"
        base_cmd.extend(['-filter_complex', filter_complex])
        base_cmd.extend(['-map', '[v_out]'])
    
    # Add quality-specific settings
    if quality in ["prores", "proreshq"]:
        # For ProRes, use specific codec settings
        profile = "3" if quality == "proreshq" else "2"
        base_cmd.extend([
            '-c:v', 'prores_ks',
            '-profile:v', profile,
            '-vendor', 'apl0',
            '-pix_fmt', 'yuv422p10le'
        ])
    elif quality != "gif":
        # Default MP4 with good quality
        base_cmd.extend([
            '-c:v', 'libx264',
            '-preset', 'slow',
            '-crf', '18',
            '-pix_fmt', 'yuv420p'
        ])
    
    # Add output file
    base_cmd.append(output_file)
    
    # Run ffmpeg command
    try:
        # Calculate total frames for progress bar
        total_frames = len(image_date_files)
        duration = total_frames / fps
        
        # Create progress bar
        with tqdm(total=total_frames, desc="Rendering", unit="frames") as pbar:
            # Run ffmpeg with progress monitoring
            process = subprocess.Popen(
                base_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Monitor FFmpeg output for progress
            while True:
                output = process.stderr.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    # Look for frame number in FFmpeg output
                    if "frame=" in output:
                        try:
                            frame = int(output.split("frame=")[1].split()[0])
                            pbar.n = frame
                            pbar.refresh()
                        except (IndexError, ValueError):
                            pass
            
            # Get the return code
            return_code = process.wait()
            
            if return_code != 0:
                error_output = process.stderr.read()
                print("FFmpeg error output:", error_output)
                print("FFmpeg return code:", return_code)
                print("FFmpeg command:", ' '.join(base_cmd))
                raise subprocess.CalledProcessError(return_code, base_cmd, error_output)
            
    except subprocess.CalledProcessError as e:
        print("FFmpeg error output:", e.stderr)
        print("FFmpeg return code:", e.returncode)
        print("FFmpeg command:", ' '.join(base_cmd))
        raise
    
    return output_file

def find_image_directories(root_dir: str) -> List[str]:
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