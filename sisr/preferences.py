import os
import json

PREFS_PATH = os.path.expanduser("~/.sisr_prefs.json")


def load_prefs():
    if os.path.exists(PREFS_PATH):
        with open(PREFS_PATH, "r") as f:
            return json.load(f)
    return {}


def save_prefs(prefs):
    with open(PREFS_PATH, "w") as f:
        json.dump(prefs, f)
