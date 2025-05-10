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
    """Main GUI class for the Simple Image Sequence Renderer."""
    
    def __init__(self, root: tk.Tk) -> None:
        """Initialize the GUI."""
        self.root = root
        self.root.title("SISR")
        self.root.geometry("600x550")  # Increased height for title
        
        # Set theme colors
        self.bg_color = "#1a1a1a"  # Dark background
        self.accent_color = "#2563eb"  # Blue accent
        self.text_color = "#ffffff"  # White text
        
        # Configure root window
        self.root.configure(bg=self.bg_color)
        
        # Create main frame with padding
        self.main_frame = ttk.Frame(self.root, padding="30")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Create title
        self.create_title()
        
        # Create sections
        self.create_directory_section()
        self.create_options_section()
        self.create_progress_section()
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(0, weight=1)
        
        # Initialize variables
        self.input_dir: Optional[str] = None
        self.output_dir: Optional[str] = None
        self.crop_type: Optional[str] = None
        self.overlay_type: Optional[str] = None
        self.quality: str = "default"
        
    def create_title(self) -> None:
        """Create the title section."""
        title_frame = ttk.Frame(self.main_frame)
        title_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        # Main title
        title_label = ttk.Label(
            title_frame,
            text="Simple Image Sequence Renderer",
            font=("Helvetica", 20, "bold"),
            foreground=self.text_color
        )
        title_label.pack()
        
        # Subtitle
        subtitle_label = ttk.Label(
            title_frame,
            text="SISR",
            font=("Helvetica", 14),
            foreground=self.accent_color
        )
        subtitle_label.pack(pady=(5, 0))
        
    def create_directory_section(self) -> None:
        """Create the directory selection section."""
        # Input directory
        ttk.Label(
            self.main_frame,
            text="Input Directory",
            font=("Helvetica", 11),
            foreground=self.text_color
        ).grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        
        input_frame = ttk.Frame(self.main_frame)
        input_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        input_frame.columnconfigure(0, weight=1)
        
        self.input_dir_var = tk.StringVar()
        input_entry = ttk.Entry(
            input_frame,
            textvariable=self.input_dir_var,
            font=("Helvetica", 11)
        )
        input_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        ttk.Button(
            input_frame,
            text="Browse",
            command=self.select_input_dir,
            style="Accent.TButton"
        ).grid(row=0, column=1)
        
        # Output directory
        ttk.Label(
            self.main_frame,
            text="Output Directory",
            font=("Helvetica", 11),
            foreground=self.text_color
        ).grid(row=3, column=0, sticky=tk.W, pady=(0, 5))
        
        output_frame = ttk.Frame(self.main_frame)
        output_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        output_frame.columnconfigure(0, weight=1)
        
        self.output_dir_var = tk.StringVar()
        output_entry = ttk.Entry(
            output_frame,
            textvariable=self.output_dir_var,
            font=("Helvetica", 11)
        )
        output_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        ttk.Button(
            output_frame,
            text="Browse",
            command=self.select_output_dir,
            style="Accent.TButton"
        ).grid(row=0, column=1)
        
    def create_options_section(self) -> None:
        """Create the options section."""
        options_frame = ttk.Frame(self.main_frame)
        options_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        # Create three columns
        for col in range(3):
            options_frame.columnconfigure(col, weight=1)
        
        # Crop options
        ttk.Label(
            options_frame,
            text="Crop",
            font=("Helvetica", 11),
            foreground=self.text_color
        ).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        self.crop_type_var = tk.StringVar()
        self.crop_combo = ttk.Combobox(
            options_frame,
            textvariable=self.crop_type_var,
            state="readonly",
            values=('None', 'Instagram', 'HD', 'UHD'),
            font=("Helvetica", 11)
        )
        self.crop_combo.grid(row=1, column=0, sticky=(tk.W, tk.E))
        self.crop_combo.bind('<<ComboboxSelected>>', self.on_crop_type_change)
        
        ttk.Label(
            options_frame,
            text="Position",
            font=("Helvetica", 11),
            foreground=self.text_color
        ).grid(row=2, column=0, sticky=tk.W, pady=(5, 5))
        
        self.crop_position_var = tk.StringVar()
        self.crop_position_combo = ttk.Combobox(
            options_frame,
            textvariable=self.crop_position_var,
            state="readonly",
            values=('center', 'keep_top', 'keep_bottom'),
            font=("Helvetica", 11)
        )
        self.crop_position_combo.grid(row=3, column=0, sticky=(tk.W, tk.E))
        self.crop_position_combo.set('center')
        
        # Overlay options
        ttk.Label(
            options_frame,
            text="Overlay",
            font=("Helvetica", 11),
            foreground=self.text_color
        ).grid(row=0, column=1, sticky=tk.W, pady=(0, 5))
        
        self.overlay_type_var = tk.StringVar()
        self.overlay_combo = ttk.Combobox(
            options_frame,
            textvariable=self.overlay_type_var,
            state="readonly",
            values=('None', 'Date', 'Frame'),
            font=("Helvetica", 11)
        )
        self.overlay_combo.grid(row=1, column=1, sticky=(tk.W, tk.E))
        self.overlay_combo.set('None')
        
        # Quality options
        ttk.Label(
            options_frame,
            text="Quality",
            font=("Helvetica", 11),
            foreground=self.text_color
        ).grid(row=0, column=2, sticky=tk.W, pady=(0, 5))
        
        self.quality_var = tk.StringVar()
        self.quality_combo = ttk.Combobox(
            options_frame,
            textvariable=self.quality_var,
            state="readonly",
            values=('Default', 'ProRes', 'ProRes HQ', 'GIF'),
            font=("Helvetica", 11)
        )
        self.quality_combo.grid(row=1, column=2, sticky=(tk.W, tk.E))
        self.quality_combo.set('Default')
        
        # Start button
        self.start_button = ttk.Button(
            self.main_frame,
            text="Start Rendering",
            command=self.start_render,
            style="Accent.TButton"
        )
        self.start_button.grid(row=6, column=0, pady=(0, 20))
        
    def create_progress_section(self) -> None:
        """Create the progress tracking section."""
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self.main_frame,
            mode='determinate',
            variable=self.progress_var,
            style="Accent.Horizontal.TProgressbar"
        )
        self.progress_bar.grid(row=7, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Status label
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        ttk.Label(
            self.main_frame,
            textvariable=self.status_var,
            font=("Helvetica", 11),
            foreground=self.text_color
        ).grid(row=8, column=0, sticky=tk.W)
        
    def configure_styles(self) -> None:
        """Configure custom styles for the GUI."""
        style = ttk.Style()
        
        # Configure colors
        style.configure("TFrame", background=self.bg_color)
        style.configure("TLabel", background=self.bg_color, foreground=self.text_color)
        
        # Configure buttons
        style.configure("TButton", 
                       background=self.bg_color,
                       foreground=self.text_color,
                       font=("Helvetica", 11))
        style.configure("Accent.TButton",
                       background=self.accent_color,
                       foreground=self.text_color,
                       font=("Helvetica", 11))
        
        # Configure progress bar
        style.configure("Accent.Horizontal.TProgressbar",
                       troughcolor="#2d2d2d",
                       background=self.accent_color)
        
        # Configure comboboxes
        style.configure("TCombobox",
                       fieldbackground=self.bg_color,
                       background=self.bg_color,
                       foreground=self.text_color,
                       arrowcolor=self.text_color,
                       font=("Helvetica", 11))
        
        # Configure entry fields
        style.configure("TEntry",
                       fieldbackground=self.bg_color,
                       foreground=self.text_color,
                       font=("Helvetica", 11))
        
    def select_input_dir(self) -> None:
        """Handle input directory selection."""
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.input_dir_var.set(dir_path)
            self.input_dir = dir_path
            if not find_image_directories(dir_path):
                messagebox.showwarning("Warning", "No image files found in selected directory")
                
    def select_output_dir(self) -> None:
        """Handle output directory selection."""
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.output_dir_var.set(dir_path)
            self.output_dir = dir_path
            os.makedirs(dir_path, exist_ok=True)
            
    def on_crop_type_change(self, event: Any) -> None:
        """Handle crop type selection change."""
        crop_type = self.crop_type_var.get()
        if crop_type == 'None':
            self.crop_position_combo.set('center')
            self.crop_position_combo.state(['disabled'])
        else:
            self.crop_position_combo.state(['!disabled'])
            
    def get_crop_type(self) -> Optional[str]:
        """Get the selected crop type."""
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
        """Get the selected overlay type."""
        overlay_type = self.overlay_type_var.get()
        if overlay_type == 'None':
            return None
        return overlay_type.lower()
        
    def get_quality(self) -> str:
        """Get the selected quality setting."""
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
            messagebox.showerror("Error", "Please select both input and output directories")
            return
            
        # Disable start button
        self.start_button.state(['disabled'])
        
        try:
            # Get options
            crop_type = self.get_crop_type()
            overlay_type = self.get_overlay_type()
            quality = self.get_quality()
            
            # Find image directories
            image_dirs = find_image_directories(self.input_dir)
            if not image_dirs:
                messagebox.showerror("Error", "No image directories found")
                return
                
            # Process each directory
            for dir_path in image_dirs:
                # Create output filename
                dir_name = os.path.basename(dir_path)
                output_file = os.path.join(self.output_dir, f"{dir_name}.mp4")
                
                # Get image files with dates if using date overlay
                if overlay_type == "date":
                    image_date_files = create_date_files(dir_path, self.output_dir)
                else:
                    # For non-date overlays, just get the image paths
                    image_files = [f for f in sorted(os.listdir(dir_path)) 
                                 if f.lower().endswith(('.jpg', '.jpeg', '.png', '.tiff', '.bmp'))]
                    image_date_files = [(os.path.join(dir_path, f), None) for f in image_files]
                
                if not image_date_files:
                    continue
                    
                # Update status
                self.status_var.set(f"Processing {dir_name}...")
                self.root.update()
                
                # Create video
                create_video_with_overlay(
                    image_date_files=image_date_files,
                    output_file=output_file,
                    fps=30,
                    crop_type=crop_type,
                    overlay_type=overlay_type,
                    quality=quality
                )
                
            self.status_var.set("Rendering completed successfully")
            messagebox.showinfo("Success", "Video rendering completed successfully")
            
        except Exception as e:
            self.status_var.set("Error during rendering")
            messagebox.showerror("Error", str(e))
            
        finally:
            # Re-enable start button
            self.start_button.state(['!disabled'])

def main() -> None:
    """Main entry point for the GUI application."""
    root = tk.Tk()
    app = SISRGUI(root)
    app.configure_styles()
    root.mainloop()
    
if __name__ == "__main__":
    main() 