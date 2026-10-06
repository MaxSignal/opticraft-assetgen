# opticraft-assetgen

Builds `assets.pak.tns`, the asset pack of OptiCraft for TI-Nspire, from your
own copy of **Minecraft 1.2.5**.

OptiCraft draws Minecraft's textures, fonts and texts, which cannot be
redistributed. This tool takes them from the Minecraft 1.2.5 client jar that
the Minecraft launcher installs on your computer, adds OptiCraft's own Legacy
UI art (shipped in `opticraft_assetgen/data/`), and writes the pack the
calculator program reads. Nothing is downloaded.

## Requirements

- Python 3.8 or later (standard library only)
- Minecraft Java Edition, with version 1.2.5 installed

## Getting the Minecraft 1.2.5 jar

In the Minecraft launcher: **Installations → New installation**, choose the
version **release 1.2.5**, create it and press **Play** once. The launcher
then keeps the jar at

| System | Path |
| --- | --- |
| Windows | `%APPDATA%\.minecraft\versions\1.2.5\1.2.5.jar` |
| macOS | `~/Library/Application Support/minecraft/versions/1.2.5/1.2.5.jar` |
| Linux | `~/.minecraft/versions/1.2.5/1.2.5.jar` |

The tool also looks in Prism Launcher's and MultiMC's `libraries` folders
and in the old launcher's `.minecraft/bin/minecraft.jar`.

## Usage

From the top of this repository:

```sh
python3 -m opticraft_assetgen
```

This finds the jar, writes `assets.pak.tns` in the current folder and checks
it. Copy that file to the calculator next to `opticraft.tns`, keeping the
name `assets.pak.tns`.

Options:

| Option | |
| --- | --- |
| `--jar PATH` | use this jar (or an unpacked copy of it) instead of searching |
| `--minecraft-dir DIR` | search this game folder instead of the default one |
| `-o`, `--output PATH` | where to write the pack (default `assets.pak.tns`) |
| `--opticraft-pak PATH` | also take the files of an OptiCraft release `assets.pak` that neither the jar nor this tool provide, such as the tutorial world |
| `--no-tutorial` | with `--opticraft-pak`, leave the tutorial world out (about 12 MB) |

Or install it as a command:

```sh
pip install .
opticraft-assetgen --help
```

## What goes into the pack

| Source | Files |
| --- | --- |
| Your Minecraft 1.2.5 jar | every resource in it (textures, fonts, languages, texts), unchanged, under `assets/`; the compiled classes and `META-INF` are left out |
| This tool (`opticraft_assetgen/data/`) | OptiCraft's Legacy UI art (`legacy/`: title logo, menu panorama, startup logos, checkbox and tip sprites) and `cursor.png` |
| `--opticraft-pak` (optional) | the rest of an OptiCraft release pack: the tutorial world, OptiFine's connected-glass texture `ctm.png`, ... |

Without `--opticraft-pak` the game runs normally; only the tutorial world is
missing and glass does not connect. The calculator build has no sound, so
sounds are never included.

The jar is checked before anything is written: a jar from Minecraft 1.5 or
later, or one without the core 1.2 textures, is refused; missing optional
files are listed as warnings.

## Pack format

MCPK, as read by OptiCraft's `PakArchive` (see `opticraft_assetgen/mcpk.py`
and the upstream `scripts/make_pak.py`): a 32-byte header, a table of
FNV-1a-hashed entries sorted by hash, the NUL-terminated paths, and each file
at a 64-byte boundary, uncompressed.

## Tests

```sh
python3 -m unittest discover -s tests
```

## Related

The calculator program itself is the TI-Nspire port of OptiCraft Heritage
Edition (`nspire-port`: patches, build scripts and tools; the patched source
tree is `opticraft`, branch `nspire-port`).

## Layout

```text
opticraft_assetgen/
  cli.py        command line
  locate.py     finding the 1.2.5 jar in launcher folders
  jarsource.py  reading and checking the jar
  build.py      assembling the pack
  mcpk.py       writing and reading MCPK
  data/         OptiCraft's own UI art
tests/
```
