"""Assembling assets.pak.tns from the player's jar and the files this tool ships."""
import os

from . import jarsource, mcpk

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# Never needed by a read-only open of the tutorial world (as in the upstream
# scripts/make_pak.py).
TUTORIAL = "assets/legacy/tutorial/"
TUTORIAL_EXCLUDED = (
    TUTORIAL + "session.lock",
    TUTORIAL + "level.dat_old",
    TUTORIAL + "level.dat_mcr",
)


def bundled_files():
    """OptiCraft's own files shipped in data/: {path below assets/: bytes}."""
    files = {}
    for directory, _, names in os.walk(DATA_DIR):
        for name in names:
            full = os.path.join(directory, name)
            rel = os.path.relpath(full, DATA_DIR).replace(os.sep, "/")
            with open(full, "rb") as f:
                files[rel] = f.read()
    return files


class Report:
    def __init__(self):
        self.from_jar = 0
        self.from_bundle = 0
        self.from_opticraft_pak = 0
        self.warnings = []
        self.size = 0
        self.count = 0


def build(jar_path, output, opticraft_pak=None, tutorial=True):
    """Write the pak; return a Report. Raises jarsource.JarError for an unusable jar."""
    report = Report()
    resources, report.warnings = jarsource.read_resources(jar_path)

    # The game's own resources, unchanged, under assets/ where OptiCraft looks.
    files = {"assets/" + name: data for name, data in resources.items()}
    report.from_jar = len(files)

    # OptiCraft's Legacy UI art and cursor. A jar never has these paths; if a
    # modified jar does, its file wins.
    for rel, data in bundled_files().items():
        key = "assets/" + rel
        if key not in files:
            files[key] = data
            report.from_bundle += 1

    # Anything else from an official OptiCraft pak (the tutorial world, OptiFine
    # extras). Only files the jar and the bundle did not provide, and only
    # assets/: the calculator build has no sound, so resources/ is left out.
    if opticraft_pak:
        for key, data in mcpk.read_pak(opticraft_pak).items():
            lowered = key.lower()
            if not lowered.startswith("assets/") or key in files:
                continue
            if lowered.startswith(TUTORIAL_EXCLUDED):
                continue
            if not tutorial and lowered.startswith(TUTORIAL):
                continue
            files[key] = data
            report.from_opticraft_pak += 1

    report.size = mcpk.write_pak(output, files)
    report.count = len(files)

    # Read it back: every entry must come out exactly as it went in.
    written = mcpk.read_pak(output)
    if written != files:
        raise RuntimeError(f"{output}: verification failed")
    return report
