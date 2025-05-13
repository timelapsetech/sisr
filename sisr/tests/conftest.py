import os
import tempfile
from pathlib import Path
import pytest
from PIL import Image
import piexif
from datetime import datetime


@pytest.fixture(scope="session")
def test_data_dir():
    """Return the path to the test data directory."""
    return Path(__file__).parent / "data"


@pytest.fixture(scope="session")
def test_images_dir(test_data_dir):
    """Return the path to the test images directory."""
    images_dir = test_data_dir / "test_images"
    images_dir.mkdir(parents=True, exist_ok=True)
    return images_dir


@pytest.fixture(scope="session")
def white_image_1920x1080(test_images_dir):
    """Create a 1920x1080 white test image with EXIF data."""
    img_path = test_images_dir / "white_1920x1080.jpg"
    if not img_path.exists():
        img = Image.new("RGB", (1920, 1080), color="white")
        # Add EXIF data with date
        exif_dict = {
            "0th": {},
            "Exif": {
                piexif.ExifIFD.DateTimeOriginal: datetime.now()
                .strftime("%Y:%m:%d %H:%M:%S")
                .encode("utf-8")
            },
        }
        exif_bytes = piexif.dump(exif_dict)
        img.save(img_path, quality=95, exif=exif_bytes)
    return str(img_path)


@pytest.fixture(scope="session")
def white_image_1080x1920(test_images_dir):
    """Create a 1080x1920 white test image with EXIF data."""
    img_path = test_images_dir / "white_1080x1920.jpg"
    if not img_path.exists():
        img = Image.new("RGB", (1080, 1920), color="white")
        # Add EXIF data with date
        exif_dict = {
            "0th": {},
            "Exif": {
                piexif.ExifIFD.DateTimeOriginal: datetime.now()
                .strftime("%Y:%m:%d %H:%M:%S")
                .encode("utf-8")
            },
        }
        exif_bytes = piexif.dump(exif_dict)
        img.save(img_path, quality=95, exif=exif_bytes)
    return str(img_path)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def image_sequence(temp_dir, white_image_1920x1080):
    """Create a sequence of 3 white test images with EXIF data."""
    sequence = []
    for i in range(3):
        img_path = os.path.join(temp_dir, f"test_{i:03d}.jpg")
        # Create a new image with EXIF data
        img = Image.new("RGB", (1920, 1080), color="white")
        # Add EXIF data with date
        exif_dict = {
            "0th": {},
            "Exif": {
                piexif.ExifIFD.DateTimeOriginal: datetime.now()
                .strftime("%Y:%m:%d %H:%M:%S")
                .encode("utf-8")
            },
        }
        exif_bytes = piexif.dump(exif_dict)
        img.save(img_path, quality=95, exif=exif_bytes)
        sequence.append(img_path)
    return sequence
