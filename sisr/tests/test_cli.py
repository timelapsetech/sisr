import os
import sys
import pytest
from ..__main__ import main, parse_args, validate_args
import subprocess


def get_video_dimensions(video_path):
    """Return (width, height) of the video using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=s=x:p=0",
        video_path,
    ]
    out = subprocess.check_output(cmd).decode().strip()
    w, h = map(int, out.split("x"))
    return w, h


def test_basic_video_creation(temp_dir, image_sequence):
    """Test basic video creation without any special options."""
    output_dir = os.path.join(temp_dir, "output")
    os.makedirs(output_dir)

    sys.argv = [
        "sisr",
        "--input",
        os.path.dirname(image_sequence[0]),
        "--output-dir",
        output_dir,
        "--fps",
        "30",
    ]
    main()

    output_files = os.listdir(output_dir)
    assert len(output_files) == 1
    assert output_files[0].endswith(".mp4")


@pytest.mark.parametrize(
    "crop_opt,value",
    [
        ("--instagram-crop", None),
        ("--hd-crop", "center"),
        ("--hd-crop", "keep_top"),
        ("--hd-crop", "keep_bottom"),
        ("--uhd-crop", "center"),
        ("--uhd-crop", "keep_top"),
        ("--uhd-crop", "keep_bottom"),
    ],
)
def test_crop_options(temp_dir, image_sequence, crop_opt, value):
    """Test all crop options."""
    output_dir = os.path.join(temp_dir, "output")
    os.makedirs(output_dir)

    sys.argv = [
        "sisr",
        "--input",
        os.path.dirname(image_sequence[0]),
        "--output-dir",
        output_dir,
        "--fps",
        "30",
    ]
    if crop_opt == "--instagram-crop":
        sys.argv.append(crop_opt)
    else:
        sys.argv.extend([crop_opt, value])
    main()

    output_files = os.listdir(output_dir)
    assert len(output_files) > 0
    assert any(f.endswith(".mp4") for f in output_files)


@pytest.mark.parametrize(
    "quality,ext",
    [("default", ".mp4"), ("prores", ".mov"), ("proreshq", ".mov"), ("gif", ".gif")],
)
def test_quality_options(temp_dir, image_sequence, quality, ext):
    """Test all quality options."""
    output_dir = os.path.join(temp_dir, "output")
    os.makedirs(output_dir)

    sys.argv = [
        "sisr",
        "--input",
        os.path.dirname(image_sequence[0]),
        "--output-dir",
        output_dir,
        "--fps",
        "30",
        "--quality",
        quality,
    ]
    main()

    output_files = os.listdir(output_dir)
    assert len(output_files) > 0
    assert any(f.endswith(ext) for f in output_files)


@pytest.mark.parametrize("overlay_opt", ["--overlay-date", "--overlay-frame"])
def test_overlay_options(temp_dir, image_sequence, overlay_opt):
    """Test date and frame overlay options."""
    output_dir = os.path.join(temp_dir, "output")
    os.makedirs(output_dir)

    sys.argv = [
        "sisr",
        "--input",
        os.path.dirname(image_sequence[0]),
        "--output-dir",
        output_dir,
        "--fps",
        "30",
        overlay_opt,
    ]
    main()

    output_files = os.listdir(output_dir)
    assert len(output_files) > 0
    assert any(f.endswith(".mp4") for f in output_files)


def test_custom_resolution(temp_dir, image_sequence):
    """Test custom resolution option."""
    output_dir = os.path.join(temp_dir, "output")
    os.makedirs(output_dir)

    sys.argv = [
        "sisr",
        "--input",
        os.path.dirname(image_sequence[0]),
        "--output-dir",
        output_dir,
        "--fps",
        "30",
        "--resolution",
        "1280x720",
    ]
    main()

    output_files = os.listdir(output_dir)
    assert len(output_files) == 1
    assert output_files[0].endswith(".mp4")


@pytest.mark.parametrize(
    "invalid_opts",
    [
        ["--overlay-date", "--overlay-frame"],
        ["--instagram-crop", "--hd-crop", "center"],
        ["--hd-crop", "center", "--uhd-crop", "center"],
        ["--quality", "invalid"],
        ["--fps", "0"],
    ],
)
def test_invalid_options(temp_dir, image_sequence, invalid_opts):
    """Test invalid option combinations."""
    with pytest.raises((SystemExit, ValueError)):
        sys.argv = [
            "sisr",
            "--input",
            os.path.dirname(image_sequence[0]),
            "--output-dir",
            temp_dir,
        ] + invalid_opts
        main()


def test_empty_input_directory(temp_dir):
    """Test behavior with empty input directory."""
    output_dir = os.path.join(temp_dir, "output")
    os.makedirs(output_dir)

    sys.argv = ["sisr", "--input", temp_dir, "--output-dir", output_dir, "--fps", "30"]
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1


def test_combined_options(temp_dir, image_sequence):
    """Test multiple options combined."""
    output_dir = os.path.join(temp_dir, "output")
    os.makedirs(output_dir)

    sys.argv = [
        "sisr",
        "--input",
        os.path.dirname(image_sequence[0]),
        "--output-dir",
        output_dir,
        "--fps",
        "30",
        "--hd-crop",
        "center",
        "--overlay-date",
        "--quality",
        "prores",
    ]
    main()

    output_files = os.listdir(output_dir)
    assert len(output_files) > 0
    assert any(f.endswith(".mov") for f in output_files)


def test_different_fps_values(temp_dir, image_sequence):
    """Test different FPS values."""
    fps_values = [1, 15, 30, 60, 120]

    for fps in fps_values:
        output_dir = os.path.join(temp_dir, f"output_{fps}")
        os.makedirs(output_dir)

        sys.argv = [
            "sisr",
            "--input",
            os.path.dirname(image_sequence[0]),
            "--output-dir",
            output_dir,
            "--fps",
            str(fps),
        ]
        main()

        output_files = os.listdir(output_dir)
        assert len(output_files) == 1
        assert output_files[0].endswith(".mp4")


def test_output_filename_formatting(temp_dir, image_sequence):
    """Test output filename formatting with different options."""
    output_dir = os.path.join(temp_dir, "output")
    os.makedirs(output_dir)

    # Test with date overlay
    sys.argv = [
        "sisr",
        "--input",
        os.path.dirname(image_sequence[0]),
        "--output-dir",
        output_dir,
        "--fps",
        "30",
        "--overlay-date",
    ]
    main()

    output_files = [f for f in os.listdir(output_dir) if f.endswith(".mp4")]
    assert len(output_files) == 1

    # Test with frame overlay
    sys.argv = [
        "sisr",
        "--input",
        os.path.dirname(image_sequence[0]),
        "--output-dir",
        output_dir,
        "--fps",
        "30",
        "--overlay-frame",
    ]
    main()

    output_files = [f for f in os.listdir(output_dir) if f.endswith(".mp4")]
    assert len(output_files) == 2


def test_max_width_scaling(temp_dir, image_sequence):
    output_dir = os.path.join(temp_dir, "output")
    os.makedirs(output_dir)
    sys.argv = [
        "sisr",
        "--input", os.path.dirname(image_sequence[0]),
        "--output-dir", output_dir,
        "--fps", "30",
        "--max-width", "1280",
    ]
    main()
    output_files = [f for f in os.listdir(output_dir) if f.endswith(".mp4")]
    assert len(output_files) == 1
    out_path = os.path.join(output_dir, output_files[0])
    w, h = get_video_dimensions(out_path)
    assert w == 1280
    assert h % 2 == 0


def test_max_height_scaling(temp_dir, image_sequence):
    output_dir = os.path.join(temp_dir, "output")
    os.makedirs(output_dir)
    sys.argv = [
        "sisr",
        "--input", os.path.dirname(image_sequence[0]),
        "--output-dir", output_dir,
        "--fps", "30",
        "--max-height", "720",
    ]
    main()
    output_files = [f for f in os.listdir(output_dir) if f.endswith(".mp4")]
    assert len(output_files) == 1
    out_path = os.path.join(output_dir, output_files[0])
    w, h = get_video_dimensions(out_path)
    assert h == 720
    assert w % 2 == 0


def test_max_width_and_height_scaling(temp_dir, image_sequence):
    output_dir = os.path.join(temp_dir, "output")
    os.makedirs(output_dir)
    sys.argv = [
        "sisr",
        "--input", os.path.dirname(image_sequence[0]),
        "--output-dir", output_dir,
        "--fps", "30",
        "--max-width", "1000",
        "--max-height", "500",
    ]
    main()
    output_files = [f for f in os.listdir(output_dir) if f.endswith(".mp4")]
    assert len(output_files) == 1
    out_path = os.path.join(output_dir, output_files[0])
    w, h = get_video_dimensions(out_path)
    assert w <= 1000 and h <= 500
    assert w % 2 == 0 and h % 2 == 0


def test_scaling_with_overlay(temp_dir, image_sequence):
    output_dir = os.path.join(temp_dir, "output")
    os.makedirs(output_dir)
    sys.argv = [
        "sisr",
        "--input", os.path.dirname(image_sequence[0]),
        "--output-dir", output_dir,
        "--fps", "30",
        "--max-width", "640",
        "--overlay-date",
    ]
    main()
    output_files = [f for f in os.listdir(output_dir) if f.endswith(".mp4")]
    assert len(output_files) == 1
    out_path = os.path.join(output_dir, output_files[0])
    w, h = get_video_dimensions(out_path)
    assert w == 640
    assert h % 2 == 0


def test_scaling_not_allowed_with_crop(temp_dir, image_sequence):
    output_dir = os.path.join(temp_dir, "output")
    os.makedirs(output_dir)
    sys.argv = [
        "sisr",
        "--input", os.path.dirname(image_sequence[0]),
        "--output-dir", output_dir,
        "--fps", "30",
        "--max-width", "800",
        "--hd-crop", "center",
    ]
    with pytest.raises((SystemExit, ValueError)):
        main()
