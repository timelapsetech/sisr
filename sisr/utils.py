import os
import sys
from typing import Optional


def _imageio_ffmpeg_exe() -> tuple[Optional[str], Optional[BaseException]]:
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe(), None
    except BaseException as exc:  # noqa: BLE001 — report any import/runtime failure
        return None, exc


def get_ffmpeg_path() -> str:
    """Return the path to the bundled ffmpeg binary.

    Uses the static build shipped with ``imageio-ffmpeg`` (includes ``drawtext``
    and a consistent codec set). PyInstaller builds place that binary beside the
    executable or under ``_MEIPASS``.

    Override with ``SISR_FFMPEG`` or ``FFMPEG_BINARY`` for debugging only.

    Raises:
        RuntimeError: If no bundled binary is available (e.g. ``imageio-ffmpeg``
            is not installed). Falling back to ``ffmpeg`` on ``PATH`` is unsafe:
            Homebrew builds often omit the ``drawtext`` filter.
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
    bundled, load_err = _imageio_ffmpeg_exe()
    if bundled:
        return bundled
    detail = f"\nUnderlying error: {load_err!r}" if load_err else ""
    raise RuntimeError(
        "Could not locate the bundled FFmpeg from imageio-ffmpeg. "
        "It includes filters such as drawtext that SISR needs for overlays.\n\n"
        "Install the declared dependency, for example:\n"
        "  pip install imageio-ffmpeg\n"
        "or reinstall this package from its requirements."
        f"{detail}"
    )
