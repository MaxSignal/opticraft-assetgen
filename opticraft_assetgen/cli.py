"""Command line: python -m opticraft_assetgen <Minecraft folder or jar> [options]"""
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

Give the folder Minecraft is installed in (the game folder, its
versions/1.2.5 folder, or the 1.2.5 jar itself). To get version 1.2.5 there,
create an installation with version "release 1.2.5" in the launcher and start
it once.
"""


def _locations_text():
    lines = ["Usual Minecraft folders:"]
    lines += [f"  {system:15} {path}" for system, path in locate.TYPICAL_LOCATIONS]
    return "\n".join(lines)


def parse_args(argv):
    parser = argparse.ArgumentParser(prog="opticraft-assetgen", description=DESCRIPTION,
                                     epilog=_locations_text(),
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("minecraft", nargs="?",
                        help="Minecraft folder, its versions/1.2.5 folder, or the 1.2.5 jar")
    parser.add_argument("-o", "--output", default="assets.pak.tns",
                        help="pak to write (default: assets.pak.tns)")
    parser.add_argument("--opticraft-pak", help="an assets.pak from an OptiCraft release: adds its "
                        "files that are neither in the jar nor in this tool, such as the "
                        "tutorial world")
    parser.add_argument("--no-tutorial", action="store_true",
                        help="with --opticraft-pak, leave the tutorial world out (about 12 MB)")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser, parser.parse_args(argv)


def main(argv=None):
    parser, args = parse_args(sys.argv[1:] if argv is None else argv)

    if args.minecraft is None:
        parser.print_usage(sys.stderr)
        print("Give the folder Minecraft is installed in (or the 1.2.5 jar).", file=sys.stderr)
        print(_locations_text(), file=sys.stderr)
        return 2
    try:
        jar = locate.resolve(args.minecraft)
    except locate.NotFound as e:
        if not e.tried:
            print(f"{e.path}: not found", file=sys.stderr)
        else:
            print(f"No Minecraft 1.2.5 jar in {e.path}. Looked for:", file=sys.stderr)
            for path in e.tried:
                print("  " + path, file=sys.stderr)
            print('Create an installation with version "release 1.2.5" in the launcher, '
                  "start it once, and try again.", file=sys.stderr)
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
    print("Copy it to the calculator into the same folder as the OptiCraft program, "
          "keeping the name assets.pak.tns.")
    return 0
