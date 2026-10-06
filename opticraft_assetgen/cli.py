"""Command line: python -m opticraft_assetgen [options]"""
import argparse
import os
import sys

from . import __version__, build, jarsource, locate

DESCRIPTION = """\
Build assets.pak.tns, the asset pack of OptiCraft for TI-Nspire, from your own
copy of Minecraft 1.2.5.

The textures, fonts and texts come from the Minecraft 1.2.5 client jar that
the Minecraft launcher installs. OptiCraft's own Legacy UI art (title logo,
menu panorama, ...) ships with this tool. Nothing is downloaded.

Without --jar, the jar is looked for where the official launcher, Prism
Launcher and MultiMC keep it. If none is found, install Minecraft 1.2.5 in the
launcher (Installations > New installation > version "release 1.2.5"),
start it once, and run this again.
"""


def parse_args(argv):
    parser = argparse.ArgumentParser(prog="opticraft-assetgen", description=DESCRIPTION,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--jar", help="Minecraft 1.2.5 client jar (or an unpacked copy of it)")
    parser.add_argument("--minecraft-dir", help="game directory to search instead of the default "
                        "(.minecraft or Application Support/minecraft)")
    parser.add_argument("-o", "--output", default="assets.pak.tns",
                        help="pak to write (default: assets.pak.tns)")
    parser.add_argument("--opticraft-pak", help="an assets.pak from an OptiCraft release: adds its "
                        "files that are neither in the jar nor in this tool, such as the "
                        "tutorial world")
    parser.add_argument("--no-tutorial", action="store_true",
                        help="with --opticraft-pak, leave the tutorial world out (about 12 MB)")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)

    jar = args.jar
    if jar is None:
        jar = locate.find_jar(args.minecraft_dir)
        if jar is None:
            print("Could not find a Minecraft 1.2.5 jar. Looked in:", file=sys.stderr)
            for path in locate.candidate_jars(args.minecraft_dir):
                print("  " + path, file=sys.stderr)
            print("Install Minecraft 1.2.5 in the launcher and start it once, or pass --jar.",
                  file=sys.stderr)
            return 2
    elif not os.path.exists(jar):
        print(f"{jar}: not found", file=sys.stderr)
        return 2
    print(f"Minecraft jar: {jar}")
    if os.path.isfile(jar):
        if jarsource.sha1_of(jar) == jarsource.CLIENT_SHA1:
            print("  matches the official Minecraft 1.2.5 client")
        else:
            print("  not the official 1.2.5 client file; checking its contents instead")

    try:
        report = build.build(jar, args.output, args.opticraft_pak, tutorial=not args.no_tutorial)
    except jarsource.JarError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    for warning in report.warnings:
        print(f"  warning: {warning}")
    print(f"From the jar:            {report.from_jar} files")
    print(f"OptiCraft UI (bundled):  {report.from_bundle} files")
    if args.opticraft_pak:
        print(f"From the OptiCraft pak:  {report.from_opticraft_pak} files")
    print(f"Wrote {args.output}: {report.count} files, {report.size / 1e6:.1f} MB (verified)")
    print("Copy it next to opticraft.tns on the calculator, keeping the name assets.pak.tns.")
    return 0
