"""Finding the Minecraft 1.2.5 client jar inside the folder the player names.

Where Minecraft is installed differs between systems and launchers, so the
player always says where to look; nothing is searched on its own. The tool
accepts the game folder itself, a folder below it, or the jar.
"""
import os

VERSION = "1.2.5"

# Relative to the folder the player gives, most likely first.
_JAR_PATHS = (
    # Official launcher: the game folder (.minecraft / minecraft).
    ("versions", VERSION, VERSION + ".jar"),
    # The versions/1.2.5 folder itself.
    (VERSION + ".jar",),
    # The pre-2013 launcher kept one minecraft.jar for the installed version.
    ("bin", "minecraft.jar"),
    ("minecraft.jar",),
    # Prism Launcher / MultiMC data folder.
    ("libraries", "com", "mojang", "minecraft", VERSION, f"minecraft-{VERSION}-client.jar"),
    (f"minecraft-{VERSION}-client.jar",),
)

# Shown when no folder is given or nothing is found in it.
TYPICAL_LOCATIONS = (
    ("Windows", r"%APPDATA%\.minecraft"),
    ("macOS", "~/Library/Application Support/minecraft"),
    ("Linux", "~/.minecraft"),
    ("Prism Launcher", "its data folder (Settings > Launcher > Folders)"),
)


class NotFound(Exception):
    def __init__(self, path, tried):
        super().__init__(path)
        self.path = path
        self.tried = tried


def resolve(path):
    """The jar (or unpacked jar folder) to read for `path`; raises NotFound."""
    path = os.path.expanduser(path)
    if os.path.isfile(path):
        return path
    if not os.path.isdir(path):
        raise NotFound(path, [])
    tried = []
    for parts in _JAR_PATHS:
        candidate = os.path.join(path, *parts)
        tried.append(candidate)
        if os.path.isfile(candidate):
            return candidate
    # An unpacked jar: the resources sit at the top of the folder.
    if os.path.isfile(os.path.join(path, "terrain.png")):
        return path
    raise NotFound(path, tried)
