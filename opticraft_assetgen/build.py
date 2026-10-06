"""Assembling assets.pak.tns from the player's jar and the files this tool ships."""
import os

from . import jarsource, mcpk

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# The tutorial world, which the game opens read-only in place from the pak.
TUTORIAL = "assets/legacy/tutorial/"


def bundled_files(tutorial=True):
    """OptiCraft's own files shipped in data/: {path below assets/: bytes}.
    That is its Legacy UI art, the cursor and the tutorial world."""
    files = {}
    for directory, _, names in os.walk(DATA_DIR):
        for name in names:
            full = os.path.join(directory, name)
            rel = os.path.relpath(full, DATA_DIR).replace(os.sep, "/")
            if not tutorial and ("assets/" + rel).startswith(TUTORIAL):
                continue
            with open(full, "rb") as f:
                files[rel] = f.read()
    return files


def _write_verified(output, files, report):
    report.size = mcpk.write_pak(output, files)
    report.count = len(files)
    # Read it back: every entry must come out exactly as it went in.
    if mcpk.read_pak(output) != files:
        raise RuntimeError(f"{output}: verification failed")
    return report


class Report:
    def __init__(self):
        self.from_jar = 0
        self.from_bundle = 0
        self.warnings = []
        self.size = 0
        self.count = 0


def build(jar_path, output, tutorial=True):
    """Write the pak; return a Report. Raises jarsource.JarError for an unusable jar."""
    report = Report()
    resources, report.warnings = jarsource.read_resources(jar_path)

    # The game's own resources, unchanged, under assets/ where OptiCraft looks.
    files = {"assets/" + name: data for name, data in resources.items()}
    report.from_jar = len(files)

    # OptiCraft's Legacy UI art, cursor and tutorial world. A jar never has
    # these paths; if a modified jar does, its file wins.
    for rel, data in bundled_files(tutorial).items():
        key = "assets/" + rel
        if key not in files:
            files[key] = data
            report.from_bundle += 1

    return _write_verified(output, files, report)
