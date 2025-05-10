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
    print(f"\n{'='*50}")
    print(f"Extracting date from: {image_path}")
    print(f"{'='*50}")
    
    def validate_date(date_str: str) -> bool:
        """Validate that a date string is in the correct format."""
        try:
            datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
            return True
        except ValueError:
            print(f"Invalid date format: {date_str}")
            return False
    
    def format_date(date_str: str) -> str:
        """Format a date string to the required format."""
        try:
            print(f"Formatting date: {date_str}")
            # Try parsing with various formats
            formats = [
                '%Y:%m:%d %H:%M:%S',
                '%Y-%m-%d %H:%M:%S',
                '%Y:%m:%d',
                '%Y-%m-%d',
                '%Y:%m:%d %H:%M:%S%z',  # With timezone
                '%Y-%m-%d %H:%M:%S%z'   # With timezone
            ]
            
            # First try to parse with timezone
            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    formatted = dt.strftime('%Y:%m:%d %H:%M:%S')
                    print(f"Successfully formatted date using format {fmt}: {formatted}")
                    return formatted
                except ValueError:
                    continue
            
            # If that fails, try removing timezone info and parse again
            if '+' in date_str or '-' in date_str:
                date_str = date_str.split('+')[0].split('-')[0].strip()
                print(f"Trying without timezone: {date_str}")
                for fmt in formats[:4]:  # Only use formats without timezone
                    try:
                        dt = datetime.strptime(date_str, fmt)
                        formatted = dt.strftime('%Y:%m:%d %H:%M:%S')
                        print(f"Successfully formatted date using format {fmt}: {formatted}")
                        return formatted
                    except ValueError:
                        continue
            
            print(f"Failed to format date: {date_str}")
            return None
        except Exception as e:
            print(f"Error formatting date {date_str}: {e}")
            return None
    
    try:
        # Try PIL first
        print("\nOpening image with PIL...")
        with Image.open(image_path) as img:
            print(f"Image format: {img.format}")
            print(f"Image mode: {img.mode}")
            print(f"Image size: {img.size}")
            print(f"Image info keys: {list(img.info.keys())}")
            
            # Print all info values
            print("\nImage info values:")
            for key, value in img.info.items():
                if isinstance(value, bytes):
                    print(f"{key}: {len(value)} bytes")
                else:
                    print(f"{key}: {value}")
            
            print("\nTrying PIL extraction...")
            exif_data = img._getexif() if hasattr(img, '_getexif') else None
            
            if exif_data:
                print("Found EXIF data in PIL")
                print("EXIF data keys:", exif_data.keys())
                # Try DateTimeOriginal (36867) first
                if 36867 in exif_data:
                    date_str = exif_data[36867]
                    print(f"Found DateTimeOriginal in PIL: {date_str}")
                    if date_str and isinstance(date_str, str):
                        formatted_date = format_date(date_str)
                        if formatted_date and validate_date(formatted_date):
                            return formatted_date
                # Then try DateTime (306)
                elif 306 in exif_data:
                    date_str = exif_data[306]
                    print(f"Found DateTime in PIL: {date_str}")
                    if date_str and isinstance(date_str, str):
                        formatted_date = format_date(date_str)
                        if formatted_date and validate_date(formatted_date):
                            return formatted_date
            else:
                print("No EXIF data found in PIL")
            
            # Try piexif if PIL didn't find it
            try:
                print("\nTrying piexif extraction...")
                exif_bytes = img.info.get('exif', b'')
                print(f"EXIF bytes length: {len(exif_bytes)}")
                if exif_bytes:
                    print("First 100 bytes of EXIF data:", exif_bytes[:100])
                    exif_dict = piexif.load(exif_bytes)
                    print("\nPiexif data structure:")
                    for ifd in exif_dict:
                        print(f"\n{ifd} IFD:")
                        for tag_id, value in exif_dict[ifd].items():
                            if isinstance(value, bytes):
                                try:
                                    value_str = value.decode('utf-8')
                                    print(f"Tag {tag_id}: {value_str}")
                                except UnicodeDecodeError:
                                    print(f"Tag {tag_id}: {len(value)} bytes (binary)")
                            else:
                                print(f"Tag {tag_id}: {value}")
                    
                    # Check ExifIFD.DateTimeOriginal (36867)
                    if "Exif" in exif_dict and piexif.ExifIFD.DateTimeOriginal in exif_dict["Exif"]:
                        date_str = exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal].decode('utf-8')
                        print(f"Found DateTimeOriginal in piexif: {date_str}")
                        if date_str and isinstance(date_str, str):
                            formatted_date = format_date(date_str)
                            if formatted_date and validate_date(formatted_date):
                                return formatted_date
                    # Check 0th.DateTime (306)
                    elif "0th" in exif_dict and 306 in exif_dict["0th"]:
                        date_str = exif_dict["0th"][306].decode('utf-8')
                        print(f"Found DateTime in piexif: {date_str}")
                        if date_str and isinstance(date_str, str):
                            formatted_date = format_date(date_str)
                            if formatted_date and validate_date(formatted_date):
                                return formatted_date
                    # Check for Pentax-specific date fields
                    elif "0th" in exif_dict:
                        # Try to combine Date and Time fields if they exist
                        date = exif_dict["0th"].get(306, b'').decode('utf-8')  # Date field
                        time = exif_dict["0th"].get(307, b'').decode('utf-8')  # Time field
                        if date and time:
                            date_str = f"{date} {time}"
                            print(f"Found Pentax Date/Time: {date_str}")
                            if date_str and isinstance(date_str, str):
                                formatted_date = format_date(date_str)
                                if formatted_date and validate_date(formatted_date):
                                    return formatted_date
                else:
                    print("No EXIF bytes found in image info")
            except Exception as e:
                print(f"Piexif error: {e}")
                print("Full piexif error:", str(e))
        
        # If no EXIF data found, use file modification time
        print("\nNo EXIF data found, using file modification time")
        mod_time = os.path.getmtime(image_path)
        date = datetime.fromtimestamp(mod_time).strftime('%Y:%m:%d %H:%M:%S')
        print(f"Using modification time: {date}")
        return date
    except Exception as e:
        print(f"Error extracting date: {e}")
        print("Full error:", str(e))
        # Return current time as fallback
        date = datetime.now().strftime('%Y:%m:%d %H:%M:%S')
        print(f"Using current time as fallback: {date}")
        return date

def format_datetime(datetime_str: str) -> str:
    """Format a date/time string for display.
    
    Args:
        datetime_str: Date/time string in format 'YYYY:MM:DD HH:MM:SS'
        
    Returns:
        Formatted date/time string like 'Monday, January 1, 2024 12:00PM'
        
    If the input string cannot be parsed, returns it unchanged.
    """
    print(f"\nFormatting datetime: {datetime_str}")
    try:
        # Try parsing with the standard format
        dt = datetime.strptime(datetime_str, '%Y:%m:%d %H:%M:%S')
        formatted = dt.strftime('%A, %B %d, %Y %I:%M%p')
        print(f"Formatted result: {formatted}")
        return formatted
    except ValueError:
        try:
            # Try parsing with just the date part
            dt = datetime.strptime(datetime_str, '%Y:%m:%d')
            formatted = dt.strftime('%A, %B %d, %Y')
            print(f"Formatted result (date only): {formatted}")
            return formatted
        except ValueError as e:
            print(f"Error formatting date {datetime_str}: {e}")
            return datetime_str

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
    print(f"\n{'='*50}")
    print(f"Creating date files from directory: {image_dir}")
    print(f"{'='*50}")
    
    os.makedirs(output_dir, exist_ok=True)
    image_files = []
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.tiff', '*.bmp']:
        found = glob.glob(os.path.join(image_dir, ext))
        found.extend(glob.glob(os.path.join(image_dir, ext.upper())))
        if found:
            print(f"Found {len(found)} files with extension {ext}")
            print("Files found:", found)
        image_files.extend(found)
    
    print(f"\nTotal image files found: {len(image_files)}")
    image_files.sort()
    
    date_files = []
    for img_path in image_files:
        print(f"\nProcessing: {img_path}")
        print(f"File exists: {os.path.exists(img_path)}")
        print(f"File size: {os.path.getsize(img_path)} bytes")
        
        date_time = extract_date_time(img_path)
        print(f"Extracted date_time: {date_time}")
        
        # Ensure we have a valid date string
        if not date_time:
            print("Warning: Empty date string, using current time")
            date_time = datetime.now().strftime('%Y:%m:%d %H:%M:%S')
        
        formatted_date = format_datetime(date_time)
        print(f"Formatted date: {formatted_date}")
        
        # Ensure we have a valid formatted date
        if not formatted_date:
            print("Warning: Empty formatted date, using current time")
            formatted_date = datetime.now().strftime('%A, %B %d, %Y %I:%M%p')
        
        date_files.append((img_path, formatted_date))
    
    print(f"\nFinal date_files list length: {len(date_files)}")
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
        # Or handle as an error, depending on desired behavior for empty input
        print("Warning: No image files provided for video creation.")
        # Depending on desired behavior, could return an empty string, raise error, or try to create an empty video if FFmpeg supports it.
        # For now, let's prevent FFmpeg call with no input images if it would error.
        # This specific error ("Error opening input file") is usually due to FPS=0 or pattern mismatch.
        # If image_date_files is empty, other parts of the code will fail first (e.g., getting first_img_path).
        # It might be better to raise ValueError here too.
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
            # Square crop for Instagram
            size = min(width, height)
            x = (width - size) // 2
            y = (height - size) // 2
            width = height = size
        elif crop_type.startswith("hd_"):
            # HD crop (1920x1080)
            target_width, target_height = 1920, 1080
            if width / height > target_width / target_height:
                # Image is wider than 16:9
                new_width = int(height * target_width / target_height)
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
    base_cmd = ['ffmpeg', '-y', '-framerate', str(fps)]
    
    # Add input pattern for image sequence
    input_dir = os.path.dirname(image_date_files[0][0])
    # Use the actual filename pattern from the first image
    first_filename = os.path.basename(image_date_files[0][0])
    # Extract the pattern by finding the number of digits in the sequence number
    base_name = first_filename.split('_')[0]
    ext = os.path.splitext(first_filename)[1]
    # Find the sequence number part and count its digits
    seq_part = first_filename.split('_')[1].split('.')[0]
    num_digits = len(seq_part)
    pattern = f"{base_name}_%0{num_digits}d{ext}"
    input_path = os.path.join(input_dir, pattern)
    base_cmd.extend(['-i', input_path])
    
    # Build filter chain
    filter_chain = []
    
    # Debug the input data
    print("\nDebug: Checking image_date_files input")
    print(f"Number of files: {len(image_date_files)}")
    for i, (img_path, date_str) in enumerate(image_date_files):
        print(f"File {i}:")
        print(f"  Path: {img_path}")
        print(f"  Date: {date_str}")
        print(f"  Date type: {type(date_str)}")
    
    # Add text overlay if specified
    if overlay_type:
        # Get font path
        font_path = get_system_font()
        
        # Calculate font size based on image dimensions
        # Use 5% of the smaller dimension for font size
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
                frame_date_file_paths.append(full_frame_date_path.replace("\\", "/")) # Use normalized path

            filter_parts = []
            current_input_stream = "[0:v]"
            if crop_type:
                filter_parts.append(f"[0:v]crop={width}:{height}:{x}:{y}[v_cropped]")
                current_input_stream = "[v_cropped]"
            
            # Chain drawtext filters, one for each frame
            for i in range(num_frames):
                textfile_for_this_frame = frame_date_file_paths[i]
                output_stream_label = f"[v{i}]" if i < num_frames - 1 else "[v_out]" # Final output is [v_out]
                
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
                    f":enable='eq(n,{i})'" # Enable only for frame 'i'
                    f"{output_stream_label}"
                )
                filter_parts.append(drawtext_filter)
                current_input_stream = output_stream_label # Output of this becomes input for next
            
            if not filter_parts: # Handle case with no frames/no overlay needed
                if current_input_stream == "[0:v]": # No crop, no overlay
                    base_cmd.extend(['-map', '0:v']) # Map input directly
                else: # Cropped, but no overlay to apply (should not happen if num_frames > 0)
                    base_cmd.extend(['-filter_complex', f"{current_input_stream}[v_out]"])
                    base_cmd.extend(['-map', '[v_out]'])
            elif num_frames == 0: # No images, but overlay was requested
                 base_cmd.extend(['-map', current_input_stream.replace("[","[").replace("]","") if crop_type else '0:v']) # Map input directly
            else: # num_frames > 0, overlay filters were added
                filter_complex = ';'.join(filter_parts)
                print(f"Filter complex: {filter_complex}")
                base_cmd.extend(['-filter_complex', filter_complex])
                base_cmd.extend(['-map', '[v_out]']) # Map the final output of the chain
            
            def cleanup():
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    print(f"Warning: Failed to clean up temporary directory: {e}")
            atexit.register(cleanup)

        elif overlay_type == "frame":
            temp_dir = tempfile.mkdtemp()
            num_frames = len(image_date_files)

            # Generate one text file per frame for frame numbers
            frame_num_file_paths = []
            for i in range(num_frames):
                # Non-zero-padded frame number as requested
                frame_num_text = f"FRAME: {i}"
                frame_num_filename = f"framenum_{i}.txt" # Simpler filenames
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
                    f":x=(w-text_w)/2"  # Center horizontally
                    f":y={int(height*0.05)}" # Top margin (5% of height)
                    f":enable='eq(n,{i})'"
                    f":fix_bounds=true" # Keep fix_bounds from previous attempt
                    # text_shaping was removed as it didn't help the parsing issue
                    f"{output_stream_label}"
                )
                filter_parts.append(drawtext_filter)
                current_input_stream = output_stream_label

            if not filter_parts and num_frames > 0 : # Should not happen if num_frames > 0
                 #This condition means overlay was requested, files exist, but no filters generated.
                 #Default to mapping current_input_stream (which could be [0:v] or [v_cropped])
                if current_input_stream == "[0:v]":
                    base_cmd.extend(['-map', '0:v'])
                else:
                    # If only crop was applied, current_input_stream is [v_cropped]. Map it.
                    filter_complex = f"{current_input_stream}[v_out]"
                    base_cmd.extend(['-filter_complex', filter_complex])
                    base_cmd.extend(['-map', '[v_out]'])
            elif num_frames == 0 : # No images to process
                if current_input_stream == "[0:v]":
                     base_cmd.extend(['-map', '0:v']) 
                else: # Cropping was defined but no images
                     base_cmd.extend(['-filter_complex', f"{current_input_stream}[v_out]"])
                     base_cmd.extend(['-map', '[v_out]'])
            else: # Filters were generated
                filter_complex = ';'.join(filter_parts)
                print(f"Filter complex: {filter_complex}")
                base_cmd.extend(['-filter_complex', filter_complex])
                base_cmd.extend(['-map', '[v_out]'])

            def cleanup_frame_num_tempdir():
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    print(f"Warning: Failed to clean up frame num temporary directory: {e}")
            atexit.register(cleanup_frame_num_tempdir)

    # If no overlay_type was specified, but cropping was, we need to handle that.
    elif not overlay_type and crop_type: # elif to the main overlay_type if/elif
        filter_complex = f"[0:v]crop={width}:{height}:{x}:{y}[v_out]"
        print(f"Filter complex (crop only): {filter_complex}")
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
    elif quality != "gif":  # Skip for GIFs as we already handled it in the filter chain
        # Default MP4 with good quality
        base_cmd.extend([
            '-c:v', 'libx264',
            '-preset', 'slow',
            '-crf', '18',
            '-pix_fmt', 'yuv420p'
        ])
    
    # Add output file
    base_cmd.append(output_file)
    
    # Print command for debugging
    print("\nFFmpeg command:", ' '.join(base_cmd))
    print("Input pattern:", input_path)
    print("Number of frames:", len(image_date_files))
    print("Number of digits in sequence:", num_digits)
    
    # Run ffmpeg command
    try:
        result = subprocess.run(base_cmd, check=True, capture_output=True, text=True)
        if result.stderr:
            print("FFmpeg output:", result.stderr)
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