import sys
import os


def get_ffmpeg_path():
    """Return the path to the ffmpeg binary, using the bundled version if available."""
    if getattr(sys, "frozen", False):
        # PyInstaller bundle
        base_path = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        ffmpeg = os.path.join(base_path, "ffmpeg")
        if os.path.exists(ffmpeg):
            return ffmpeg
        # Try next to the executable (for .app bundles)
        ffmpeg = os.path.join(os.path.dirname(sys.executable), "ffmpeg")
        if os.path.exists(ffmpeg):
            return ffmpeg
    # Fallback to system ffmpeg
    return "ffmpeg"
