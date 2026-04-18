import os
import sys
from typing import Optional


def _imageio_ffmpeg_exe() -> Optional[str]:
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def get_ffmpeg_path():
    """Return the path to the bundled ffmpeg binary.

    Uses the static build shipped with ``imageio-ffmpeg`` (includes ``drawtext``
    and a consistent codec set). PyInstaller builds place that binary beside the
    executable or under ``_MEIPASS``.

    Override with ``SISR_FFMPEG`` or ``FFMPEG_BINARY`` for debugging only.
    """
    override = os.environ.get("SISR_FFMPEG") or os.environ.get("FFMPEG_BINARY")
    if override:
        return override
    if getattr(sys, "frozen", False):
        base_path = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        for candidate in (
            os.path.join(base_path, "ffmpeg"),
            os.path.join(os.path.dirname(sys.executable), "ffmpeg"),
        ):
            if os.path.exists(candidate):
                return candidate
    bundled = _imageio_ffmpeg_exe()
    if bundled:
        return bundled
    return "ffmpeg"
