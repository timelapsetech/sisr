import os
import shutil
import sys

import pytest

from ..core import (
    UnprocessableImageSequenceError,
    create_video_with_overlay,
    format_batch_render_summary,
    resolve_ffmpeg_image_sequence,
)
from ..__main__ import main


def _files(dir_path, names):
    return [(os.path.join(dir_path, name), None) for name in names]


def test_resolve_underscore_sequence(temp_dir):
    names = ["test_000.jpg", "test_001.jpg", "test_002.jpg"]
    spec = resolve_ffmpeg_image_sequence(_files(temp_dir, names))
    assert spec.number_width == 3
    assert spec.input_path == os.path.join(temp_dir, "test_%03d.jpg")
    assert [os.path.basename(path) for path, _ in spec.files] == names


def test_resolve_sequence_starting_at_one(temp_dir):
    names = ["img_0001.png", "img_0002.png", "img_0003.png"]
    spec = resolve_ffmpeg_image_sequence(_files(temp_dir, names))
    assert spec.start_number == 1
    assert spec.input_path == os.path.join(temp_dir, "img_%04d.png")


def test_resolve_numbered_files_without_underscore(temp_dir):
    names = ["DSCF0001.JPG", "DSCF0002.JPG"]
    spec = resolve_ffmpeg_image_sequence(_files(temp_dir, names))
    assert spec.start_number == 1
    assert spec.input_path == os.path.join(temp_dir, "DSCF%04d.JPG")


def test_resolve_rejects_unnumbered_images(temp_dir):
    with pytest.raises(
        UnprocessableImageSequenceError, match="processable image sequence"
    ):
        resolve_ffmpeg_image_sequence(
            _files(temp_dir, ["photo.jpg", "screenshot.png"])
        )


def test_resolve_rejects_single_image(temp_dir):
    with pytest.raises(UnprocessableImageSequenceError, match="at least 2"):
        resolve_ffmpeg_image_sequence(_files(temp_dir, ["img_0001.jpg"]))


def test_resolve_rejects_single_numbered_file_among_stills(temp_dir):
    with pytest.raises(UnprocessableImageSequenceError, match="at least 2"):
        resolve_ffmpeg_image_sequence(
            _files(temp_dir, ["preview.jpg", "shot.png", "img_0001.jpg"])
        )


def test_resolve_rejects_gappy_sequence(temp_dir):
    with pytest.raises(UnprocessableImageSequenceError, match="not consecutive"):
        resolve_ffmpeg_image_sequence(
            _files(temp_dir, ["img_001.jpg", "img_003.jpg"])
        )


def test_create_video_raises_descriptive_error_not_index_error(temp_dir):
    image_date_files = _files(temp_dir, ["holiday.jpg", "vacation.jpg"])
    with pytest.raises(UnprocessableImageSequenceError, match="holiday.jpg"):
        create_video_with_overlay(
            image_date_files=image_date_files,
            output_file=os.path.join(temp_dir, "out.mp4"),
            fps=30,
        )


def test_format_batch_render_summary():
    text = format_batch_render_summary(
        2, [("stills", "no numbers"), ("gappy", "missing frames")]
    )
    assert "Rendered 2 folders successfully." in text
    assert "Skipped 2 folders" in text
    assert "- stills" in text
    assert "- gappy" in text
    assert "no numbers" not in text
    assert "missing frames" not in text


def test_batch_cli_skips_unprocessable_folder(temp_dir, image_sequence):
    root = os.path.join(temp_dir, "batch")
    good = os.path.join(root, "good")
    bad = os.path.join(root, "bad")
    os.makedirs(good)
    os.makedirs(bad)
    for src in image_sequence:
        shutil.copy(src, good)
    shutil.copy(image_sequence[0], os.path.join(bad, "loose_photo.jpg"))
    shutil.copy(image_sequence[0], os.path.join(bad, "another_photo.jpg"))

    output_dir = os.path.join(temp_dir, "output")
    os.makedirs(output_dir)
    sys.argv = [
        "sisr",
        "--input",
        root,
        "--output-dir",
        output_dir,
        "--fps",
        "30",
    ]
    main()

    output_files = os.listdir(output_dir)
    assert any(name.endswith(".mp4") and name.startswith("good") for name in output_files)
    assert not any("bad" in name for name in output_files)


def test_batch_cli_exits_when_all_folders_unprocessable(temp_dir, image_sequence):
    root = os.path.join(temp_dir, "batch")
    bad = os.path.join(root, "bad")
    os.makedirs(bad)
    shutil.copy(image_sequence[0], os.path.join(bad, "loose_photo.jpg"))
    output_dir = os.path.join(temp_dir, "output")
    os.makedirs(output_dir)
    sys.argv = [
        "sisr",
        "--input",
        root,
        "--output-dir",
        output_dir,
        "--fps",
        "30",
    ]
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1
    assert os.listdir(output_dir) == []


def test_batch_cli_skips_single_image_folder(temp_dir, image_sequence, capsys):
    root = os.path.join(temp_dir, "batch")
    good = os.path.join(root, "good")
    still = os.path.join(root, "still")
    os.makedirs(good)
    os.makedirs(still)
    for src in image_sequence:
        shutil.copy(src, good)
    shutil.copy(image_sequence[0], os.path.join(still, "only_frame_001.jpg"))

    output_dir = os.path.join(temp_dir, "output")
    os.makedirs(output_dir)
    sys.argv = [
        "sisr",
        "--input",
        root,
        "--output-dir",
        output_dir,
        "--fps",
        "30",
    ]
    main()

    output_files = os.listdir(output_dir)
    assert any(name.endswith(".mp4") and name.startswith("good") for name in output_files)
    assert not any("still" in name for name in output_files)
    captured = capsys.readouterr()
    assert "Skipped 1 folder" in captured.out
    assert "still" in captured.out
