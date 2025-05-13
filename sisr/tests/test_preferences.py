import os
import tempfile
import json
from sisr import preferences

def test_save_and_load_prefs(tmp_path, monkeypatch):
    # Use a temp file for preferences
    test_prefs_path = tmp_path / "prefs.json"
    monkeypatch.setattr(preferences, "PREFS_PATH", str(test_prefs_path))

    # Save preferences
    prefs = {"input_dir": "/tmp/input", "output_dir": "/tmp/output"}
    preferences.save_prefs(prefs)
    assert os.path.exists(test_prefs_path)

    # Load preferences
    loaded = preferences.load_prefs()
    assert loaded == prefs

    # Overwrite and reload
    prefs2 = {"input_dir": "/foo", "output_dir": "/bar"}
    preferences.save_prefs(prefs2)
    loaded2 = preferences.load_prefs()
    assert loaded2 == prefs2 