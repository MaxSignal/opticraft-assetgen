"""Finding a Minecraft 1.2.5 client jar that the player already has installed.

Nothing is downloaded: the assets come from the player's own copy of the game,
as installed by the official launcher (or a third-party launcher that uses
Mojang's files).
"""
import os
import sys

VERSION = "1.2.5"


def _minecraft_dirs():
    """The game directories the official launcher uses on each system."""
    home = os.path.expanduser("~")
    dirs = []
    if sys.platform.startswith("win"):
        appdata = os.environ.get("APPDATA")
        if appdata:
            dirs.append(os.path.join(appdata, ".minecraft"))
    elif sys.platform == "darwin":
        dirs.append(os.path.join(home, "Library", "Application Support", "minecraft"))
    dirs.append(os.path.join(home, ".minecraft"))
    # Flatpak build of the official launcher.
    dirs.append(os.path.join(home, ".var", "app", "com.mojang.Minecraft", ".minecraft"))
    return dirs


def _launcher_library_dirs():
    """Prism Launcher / MultiMC keep the client jar under libraries/."""
    home = os.path.expanduser("~")
    roots = []
    if sys.platform.startswith("win"):
        appdata = os.environ.get("APPDATA")
        if appdata:
            roots += [os.path.join(appdata, "PrismLauncher"), os.path.join(appdata, "MultiMC")]
    elif sys.platform == "darwin":
        roots.append(os.path.join(home, "Library", "Application Support", "PrismLauncher"))
    roots += [
        os.path.join(home, ".local", "share", "PrismLauncher"),
        os.path.join(home, ".var", "app", "org.prismlauncher.PrismLauncher", "data", "PrismLauncher"),
        os.path.join(home, ".local", "share", "multimc"),
    ]
    return [os.path.join(root, "libraries") for root in roots]


def candidate_jars(minecraft_dir=None):
    """Possible jar paths, most likely first (they need not exist)."""
    dirs = [minecraft_dir] if minecraft_dir else _minecraft_dirs()
    candidates = []
    for directory in dirs:
        candidates.append(os.path.join(directory, "versions", VERSION, VERSION + ".jar"))
        # The pre-2013 launcher kept a single minecraft.jar for whichever
        # version was installed last.
        candidates.append(os.path.join(directory, "bin", "minecraft.jar"))
    if not minecraft_dir:
        for libraries in _launcher_library_dirs():
            candidates.append(os.path.join(libraries, "com", "mojang", "minecraft", VERSION,
                                           f"minecraft-{VERSION}-client.jar"))
    return candidates


def find_jar(minecraft_dir=None):
    """The first existing candidate, or None."""
    for path in candidate_jars(minecraft_dir):
        if os.path.isfile(path):
            return path
    return None
