"""Assembling assets.pak.tns from the player's jar and the files this tool ships."""
import os
import struct

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


class OptiCraftPakError(Exception):
    pass


def read_opticraft_assets(source):
    """The files of an OptiCraft release: its assets.pak (MCPK) or an unpacked
    data folder (the Wii release's apps/OptiCraft/data). Keys are pak paths."""
    if os.path.isdir(source):
        files = {}
        for directory, _, names in os.walk(source):
            for name in names:
                full = os.path.join(directory, name)
                with open(full, "rb") as f:
                    files[os.path.relpath(full, source).replace(os.sep, "/")] = f.read()
        return files
    try:
        return mcpk.read_pak(source)
    except (OSError, ValueError, struct.error) as e:
        raise OptiCraftPakError(f"{source}: not an OptiCraft assets.pak ({e})")


def _opticraft_game_files(files, tutorial):
    """What the calculator uses from an OptiCraft release: assets/ only (the
    calculator build has no sound, so resources/ is left out), without the
    files a read-only open of the tutorial never needs."""
    for key, data in files.items():
        lowered = key.lower()
        if not lowered.startswith("assets/") or lowered.startswith(TUTORIAL_EXCLUDED):
            continue
        if not tutorial and lowered.startswith(TUTORIAL):
            continue
        yield key, data


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

    # Anything else from an OptiCraft release (the tutorial world, OptiFine
    # extras): only files the jar and the bundle did not provide.
    if opticraft_pak:
        for key, data in _opticraft_game_files(read_opticraft_assets(opticraft_pak), tutorial):
            if key not in files:
                files[key] = data
                report.from_opticraft_pak += 1

    return _write_verified(output, files, report)


def build_from_opticraft(source, output, tutorial=True):
    """The pack straight from an OptiCraft release, without Minecraft: its
    assets/ files, with the bundled UI art filling anything it lacks."""
    report = Report()
    files = dict(_opticraft_game_files(read_opticraft_assets(source), tutorial))
    if "assets/terrain.png" not in files:
        raise OptiCraftPakError(f"{source}: no assets/terrain.png; not an OptiCraft asset pack")
    report.from_opticraft_pak = len(files)
    for rel, data in bundled_files().items():
        key = "assets/" + rel
        if key not in files:
            files[key] = data
            report.from_bundle += 1
    return _write_verified(output, files, report)
