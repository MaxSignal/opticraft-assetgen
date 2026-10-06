"""Reading the game's resources out of a Minecraft client jar.

Minecraft 1.2.5 keeps its textures and text at the top of the jar ("terrain.png",
"gui/items.png", "lang/en_US.lang", ...), next to the compiled classes. OptiCraft
loads the same files from "assets/<path>" in its pak.
"""
import hashlib
import os
import zipfile

# SHA-1 of the 1.2.5 client jar in Mojang's version manifest. A match is
# reported; a different jar is still accepted when its layout is the 1.2 one
# (a re-downloaded or repackaged jar has a different hash, same files).
CLIENT_SHA1 = "4a2fac7504182a97dcbcd7560c6392d7c8139928"

# Without these the game cannot draw its world or its menus.
REQUIRED = (
    "terrain.png",
    "gui/gui.png",
    "gui/items.png",
    "gui/icons.png",
    "font/default.png",
    "title/mclogo.png",
    "particles.png",
)

# Expected in 1.2.5; missing ones are reported, the pak is still written.
EXPECTED = (
    "lang/en_US.lang",
    "lang/languages.txt",
    "title/splashes.txt",
    "font.txt",
    "achievement/map.txt",
    "mob/char.png",
    "misc/grasscolor.png",
    "misc/foliagecolor.png",
    "environment/clouds.png",
    "terrain/sun.png",
    "terrain/moon_phases.png",
    "title/bg/panorama0.png",
)


class JarError(Exception):
    pass


def sha1_of(path):
    digest = hashlib.sha1()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _is_resource(name):
    if name.endswith("/") or name.startswith("META-INF/"):
        return False
    return not name.endswith(".class")


def read_resources(path):
    """Return ({resource path: bytes}, warnings) from a jar or an unpacked jar folder."""
    if os.path.isdir(path):
        resources = {}
        for directory, _, names in os.walk(path):
            for name in names:
                full = os.path.join(directory, name)
                rel = os.path.relpath(full, path).replace(os.sep, "/")
                if _is_resource(rel):
                    with open(full, "rb") as f:
                        resources[rel] = f.read()
    else:
        try:
            with zipfile.ZipFile(path) as jar:
                resources = {info.filename: jar.read(info) for info in jar.infolist()
                             if _is_resource(info.filename)}
        except zipfile.BadZipFile as e:
            raise JarError(f"{path}: not a jar ({e})")
    return resources, check_layout(resources)


def check_layout(resources):
    """Raise JarError for a jar this port cannot use; return warnings otherwise."""
    if any(name.startswith("assets/minecraft/") for name in resources):
        raise JarError("this is a Minecraft 1.6 or later jar (assets/minecraft/...); "
                       "use the 1.2.5 jar")
    if any(name.startswith("textures/blocks/") for name in resources):
        raise JarError("this is a Minecraft 1.5 jar (textures/blocks/...); use the 1.2.5 jar")
    missing = [name for name in REQUIRED if name not in resources]
    if missing:
        raise JarError("not a Minecraft 1.2 client jar; missing " + ", ".join(missing))
    warnings = [f"missing {name}" for name in EXPECTED if name not in resources]
    return warnings
