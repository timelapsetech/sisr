#!/usr/bin/env python3
"""
Simple Image Sequence Renderer (SISR) GUI.

This module provides a graphical user interface for the SISR application,
allowing users to:
- Select input and output directories
- Choose crop options (Instagram, HD, UHD)
- Add overlays (date, frame)
- Set quality options
- Monitor rendering progress
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Optional, Dict, Any, List, Tuple
from .core import create_video_with_overlay, find_image_directories, create_date_files

class SISRGUI:
    """Main GUI class for the Simple Image Sequence Renderer.
    
    This class creates and manages the main application window and all its
    components, including:
    - Directory selection
    - Crop and overlay options
    - Quality settings
    - Progress tracking
    """
    
    def __init__(self, root: tk.Tk) -> None:
        """Initialize the GUI.
        
        Args:
            root: The root Tkinter window
        """
        self.root = root
        self.root.title("Simple Image Sequence Renderer")
        self.root.geometry("800x600")
        
        # Create main frame
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Directory selection
        self.create_directory_section()
        
        # Crop options
        self.create_crop_section()
        
        # Overlay options
        self.create_overlay_section()
        
        # Quality options
        self.create_quality_section()
        
        # Progress bar
        self.create_progress_section()
        
        # Start button
        self.create_start_button()
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=1)
        
        # Initialize variables
        self.input_dir: Optional[str] = None
        self.output_dir: Optional[str] = None
        self.crop_type: Optional[str] = None
        self.overlay_type: Optional[str] = None
        self.quality: str = "default"
        
    def create_directory_section(self) -> None:
        """Create the directory selection section of the GUI.
        
        This section includes:
        - Input directory selection
        - Output directory selection
        - Directory path display
        """
        # Input directory
        ttk.Label(self.main_frame, text="Input Directory:").grid(row=0, column=0, sticky=tk.W)
        self.input_dir_var = tk.StringVar()
        ttk.Entry(self.main_frame, textvariable=self.input_dir_var, width=50).grid(row=0, column=1, sticky=(tk.W, tk.E))
        ttk.Button(self.main_frame, text="Browse", command=self.select_input_dir).grid(row=0, column=2)
        
        # Output directory
        ttk.Label(self.main_frame, text="Output Directory:").grid(row=1, column=0, sticky=tk.W)
        self.output_dir_var = tk.StringVar()
        ttk.Entry(self.main_frame, textvariable=self.output_dir_var, width=50).grid(row=1, column=1, sticky=(tk.W, tk.E))
        ttk.Button(self.main_frame, text="Browse", command=self.select_output_dir).grid(row=1, column=2)
        
    def create_crop_section(self) -> None:
        """Create the crop options section of the GUI.
        
        This section includes:
        - Crop type selection (Instagram, HD, UHD)
        - Crop position options (center, keep_top, keep_bottom)
        """
        # Crop type
        ttk.Label(self.main_frame, text="Crop Type:").grid(row=2, column=0, sticky=tk.W)
        self.crop_type_var = tk.StringVar()
        self.crop_combo = ttk.Combobox(self.main_frame, textvariable=self.crop_type_var, state="readonly")
        self.crop_combo['values'] = ('None', 'Instagram', 'HD', 'UHD')
        self.crop_combo.grid(row=2, column=1, sticky=(tk.W, tk.E))
        self.crop_combo.bind('<<ComboboxSelected>>', self.on_crop_type_change)
        
        # Crop position
        ttk.Label(self.main_frame, text="Crop Position:").grid(row=3, column=0, sticky=tk.W)
        self.crop_position_var = tk.StringVar()
        self.crop_position_combo = ttk.Combobox(self.main_frame, textvariable=self.crop_position_var, state="readonly")
        self.crop_position_combo['values'] = ('center', 'keep_top', 'keep_bottom')
        self.crop_position_combo.grid(row=3, column=1, sticky=(tk.W, tk.E))
        self.crop_position_combo.set('center')
        
    def create_overlay_section(self) -> None:
        """Create the overlay options section of the GUI.
        
        This section includes:
        - Overlay type selection (None, date, frame)
        """
        # Overlay type
        ttk.Label(self.main_frame, text="Overlay:").grid(row=4, column=0, sticky=tk.W)
        self.overlay_type_var = tk.StringVar()
        self.overlay_combo = ttk.Combobox(self.main_frame, textvariable=self.overlay_type_var, state="readonly")
        self.overlay_combo['values'] = ('None', 'Date', 'Frame')
        self.overlay_combo.grid(row=4, column=1, sticky=(tk.W, tk.E))
        self.overlay_combo.set('None')
        
    def create_quality_section(self) -> None:
        """Create the quality options section of the GUI.
        
        This section includes:
        - Quality selection (default, prores, proreshq, gif)
        """
        # Quality
        ttk.Label(self.main_frame, text="Quality:").grid(row=5, column=0, sticky=tk.W)
        self.quality_var = tk.StringVar()
        self.quality_combo = ttk.Combobox(self.main_frame, textvariable=self.quality_var, state="readonly")
        self.quality_combo['values'] = ('Default', 'ProRes', 'ProRes HQ', 'GIF')
        self.quality_combo.grid(row=5, column=1, sticky=(tk.W, tk.E))
        self.quality_combo.set('Default')
        
    def create_progress_section(self) -> None:
        """Create the progress tracking section of the GUI.
        
        This section includes:
        - Progress bar
        - Status label
        """
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.main_frame, length=300, mode='determinate', variable=self.progress_var)
        self.progress_bar.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        # Status label
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        ttk.Label(self.main_frame, textvariable=self.status_var).grid(row=7, column=0, columnspan=3)
        
    def create_start_button(self) -> None:
        """Create the start button section of the GUI.
        
        This section includes:
        - Start button
        - Button state management
        """
        self.start_button = ttk.Button(self.main_frame, text="Start Rendering", command=self.start_render)
        self.start_button.grid(row=8, column=0, columnspan=3, pady=10)
        
    def select_input_dir(self) -> None:
        """Handle input directory selection.
        
        Opens a directory selection dialog and updates the input directory path.
        Also validates that the selected directory contains image files.
        """
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.input_dir_var.set(dir_path)
            self.input_dir = dir_path
            if not find_image_directories(dir_path):
                messagebox.showwarning("Warning", "No image files found in selected directory")
                
    def select_output_dir(self) -> None:
        """Handle output directory selection.
        
        Opens a directory selection dialog and updates the output directory path.
        Creates the directory if it doesn't exist.
        """
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.output_dir_var.set(dir_path)
            self.output_dir = dir_path
            os.makedirs(dir_path, exist_ok=True)
            
    def on_crop_type_change(self, event: Any) -> None:
        """Handle crop type selection change.
        
        Args:
            event: The event that triggered this callback
        """
        crop_type = self.crop_type_var.get()
        if crop_type == 'None':
            self.crop_position_combo.set('center')
            self.crop_position_combo.state(['disabled'])
        else:
            self.crop_position_combo.state(['!disabled'])
            
    def get_crop_type(self) -> Optional[str]:
        """Get the selected crop type.
        
        Returns:
            The crop type string in the format expected by the core module,
            or None if no crop is selected.
        """
        crop_type = self.crop_type_var.get()
        if crop_type == 'None':
            return None
        position = self.crop_position_var.get()
        if crop_type == 'Instagram':
            return 'instagram'
        elif crop_type == 'HD':
            return f'hd_{position}'
        elif crop_type == 'UHD':
            return f'uhd_{position}'
        return None
        
    def get_overlay_type(self) -> Optional[str]:
        """Get the selected overlay type.
        
        Returns:
            The overlay type string in the format expected by the core module,
            or None if no overlay is selected.
        """
        overlay_type = self.overlay_type_var.get()
        if overlay_type == 'None':
            return None
        return overlay_type.lower()
        
    def get_quality(self) -> str:
        """Get the selected quality setting.
        
        Returns:
            The quality string in the format expected by the core module.
        """
        quality_map = {
            'Default': 'default',
            'ProRes': 'prores',
            'ProRes HQ': 'proreshq',
            'GIF': 'gif'
        }
        return quality_map.get(self.quality_var.get(), 'default')
        
    def start_render(self) -> None:
        """Start the rendering process."""
        if not self.input_dir or not self.output_dir:
            messagebox.showerror("Error", "Please select input and output directories")
            return
            
        # Get options
        crop_type = self.get_crop_type()
        overlay_type = self.get_overlay_type()
        quality = self.get_quality()
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        print(f"Output directory: {self.output_dir}")
        
        # Disable start button
        self.start_button.state(['disabled'])
        self.status_var.set("Rendering...")
        
        try:
            # Find image directories
            image_dirs = find_image_directories(self.input_dir)
            if not image_dirs:
                raise ValueError("No image files found in input directory")
                
            # Process each directory
            for dir_path in image_dirs:
                # Create output filename for this directory
                dir_name = os.path.basename(dir_path)
                base_name = dir_name
                
                # Add overlay type to filename if specified
                if overlay_type == "date":
                    base_name += "_date"
                elif overlay_type == "frame":
                    base_name += "_frame"
                    
                # Set extension based on quality
                if quality == "gif":
                    ext = ".gif"
                elif quality in ["prores", "proreshq"]:
                    ext = ".mov"
                else:
                    ext = ".mp4"
                    
                dir_output = os.path.join(self.output_dir, f"{base_name}{ext}")
                print(f"Processing directory: {dir_path}")
                print(f"Output file will be: {dir_output}")
                
                # Get list of image files with dates
                if overlay_type == "date":
                    image_date_files = create_date_files(dir_path, self.output_dir)
                else:
                    # For non-date overlays, just get the image files
                    image_files = [os.path.join(dir_path, f) for f in sorted(os.listdir(dir_path)) 
                                 if f.lower().endswith(('.jpg', '.jpeg', '.png', '.tiff', '.bmp'))]
                    image_date_files = [(f, "") for f in image_files]
                
                if not image_date_files:
                    print(f"No image files found in {dir_path}")
                    continue
                    
                print(f"Found {len(image_date_files)} images")
                
                # Create video
                create_video_with_overlay(
                    image_date_files=image_date_files,
                    output_file=dir_output,
                    fps=30,
                    crop_type=crop_type,
                    overlay_type=overlay_type,
                    quality=quality
                )
                
                print(f"Completed processing {dir_name}")
                
            # Show completion message
            messagebox.showinfo("Success", f"Rendering completed successfully\nOutput saved to: {self.output_dir}")
            self.status_var.set("Ready")
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            print(error_msg)
            messagebox.showerror("Error", error_msg)
            self.status_var.set("Error occurred")
            
        finally:
            # Re-enable start button
            self.start_button.state(['!disabled'])
            
def main() -> None:
    """Main entry point for the GUI application."""
    root = tk.Tk()
    app = SISRGUI(root)
    root.mainloop()
    
if __name__ == "__main__":
    main() 