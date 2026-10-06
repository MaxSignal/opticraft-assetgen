"""python -m unittest discover -s tests   (from the assetgen directory)"""
import os
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from opticraft_assetgen import build, cli, jarsource, mcpk  # noqa: E402


def make_jar(path, extra=None, drop=()):
    """A stand-in client jar: the required files plus classes and a manifest."""
    entries = {name: f"<{name}>".encode() for name in jarsource.REQUIRED + jarsource.EXPECTED}
    entries.update({
        "net/minecraft/client/Minecraft.class": b"\xca\xfe\xba\xbe",
        "aa.class": b"\xca\xfe\xba\xbe",
        "META-INF/MANIFEST.MF": b"Manifest-Version: 1.0\n",
        "META-INF/MOJANG_C.SF": b"",
    })
    entries.update(extra or {})
    for name in drop:
        entries.pop(name, None)
    with zipfile.ZipFile(path, "w") as jar:
        jar.writestr("lang/", b"")  # a directory entry
        for name, data in entries.items():
            jar.writestr(name, data)
    return entries


class McpkTests(unittest.TestCase):
    def test_round_trip(self):
        files = {"assets/terrain.png": b"x" * 100, "assets/lang/en_US.lang": b"a=b\n", "assets/empty": b""}
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "a.pak")
            size = mcpk.write_pak(path, files)
            self.assertEqual(size % mcpk.DATA_ALIGN, 0)
            self.assertEqual(mcpk.read_pak(path), files)

    def test_case_collision(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                mcpk.write_pak(os.path.join(tmp, "a.pak"), {"assets/A.png": b"", "assets/a.png": b""})

    def test_hash(self):
        # FNV-1a 32 reference values.
        self.assertEqual(mcpk.fnv1a32(""), 0x811C9DC5)
        self.assertEqual(mcpk.fnv1a32("a"), 0xE40C292C)


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        self.jar = os.path.join(self.dir, "1.2.5.jar")
        self.out = os.path.join(self.dir, "assets.pak.tns")

    def tearDown(self):
        self.tmp.cleanup()

    def test_jar_resources_bundle_and_no_classes(self):
        entries = make_jar(self.jar)
        report = build.build(self.jar, self.out)
        files = mcpk.read_pak(self.out)
        for name in jarsource.REQUIRED:
            self.assertEqual(files["assets/" + name], entries[name])
        self.assertFalse(any(name.endswith(".class") or "META-INF" in name for name in files))
        for rel in build.bundled_files():
            self.assertIn("assets/" + rel, files)
        self.assertIn("assets/legacy/title.png", files)
        self.assertEqual(report.warnings, [])
        self.assertEqual(report.count, len(files))

    def test_bundled_tutorial_world(self):
        make_jar(self.jar)
        build.build(self.jar, self.out)
        files = mcpk.read_pak(self.out)
        self.assertIn("assets/legacy/tutorial/level.dat", files)
        self.assertIn("assets/legacy/tutorial/region/r.0.0.mca", files)
        self.assertNotIn("assets/ctm.png", files)
        build.build(self.jar, self.out, tutorial=False)
        files = mcpk.read_pak(self.out)
        self.assertFalse(any(name.startswith("assets/legacy/tutorial/") for name in files))
        self.assertIn("assets/legacy/title.png", files)

    def test_jar_file_wins_over_bundle(self):
        make_jar(self.jar, extra={"cursor.png": b"mine"})
        build.build(self.jar, self.out)
        self.assertEqual(mcpk.read_pak(self.out)["assets/cursor.png"], b"mine")

    def test_unpacked_jar_directory(self):
        entries = make_jar(self.jar)
        unpacked = os.path.join(self.dir, "unpacked")
        with zipfile.ZipFile(self.jar) as jar:
            jar.extractall(unpacked)
        build.build(unpacked, self.out)
        self.assertEqual(mcpk.read_pak(self.out)["assets/terrain.png"], entries["terrain.png"])

    def test_missing_expected_is_a_warning(self):
        make_jar(self.jar, drop=["title/splashes.txt"])
        report = build.build(self.jar, self.out)
        self.assertEqual(report.warnings, ["missing title/splashes.txt"])

    def test_rejects_other_versions(self):
        make_jar(self.jar, drop=["terrain.png"])
        with self.assertRaises(jarsource.JarError):
            build.build(self.jar, self.out)
        make_jar(self.jar, extra={"textures/blocks/stone.png": b""})
        with self.assertRaisesRegex(jarsource.JarError, "1.5"):
            build.build(self.jar, self.out)
        make_jar(self.jar, extra={"assets/minecraft/textures/block/stone.png": b""})
        with self.assertRaisesRegex(jarsource.JarError, "1.6"):
            build.build(self.jar, self.out)

    def test_not_a_jar(self):
        with open(self.jar, "wb") as f:
            f.write(b"not a zip")
        with self.assertRaises(jarsource.JarError):
            build.build(self.jar, self.out)


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        self.out = os.path.join(self.dir, "assets.pak.tns")

    def tearDown(self):
        self.tmp.cleanup()

    def run_with(self, path):
        code = cli.main([path, "-o", self.out])
        if code == 0:
            self.assertIn("assets/terrain.png", mcpk.read_pak(self.out))
        return code

    def test_game_folder(self):
        game = os.path.join(self.dir, ".minecraft")
        os.makedirs(os.path.join(game, "versions", "1.2.5"))
        make_jar(os.path.join(game, "versions", "1.2.5", "1.2.5.jar"))
        self.assertEqual(self.run_with(game), 0)

    def test_versions_folder_and_jar(self):
        version = os.path.join(self.dir, "versions", "1.2.5")
        os.makedirs(version)
        jar = os.path.join(version, "1.2.5.jar")
        make_jar(jar)
        self.assertEqual(self.run_with(version), 0)
        self.assertEqual(self.run_with(jar), 0)

    def test_prism_data_folder(self):
        lib = os.path.join(self.dir, "libraries", "com", "mojang", "minecraft", "1.2.5")
        os.makedirs(lib)
        make_jar(os.path.join(lib, "minecraft-1.2.5-client.jar"))
        self.assertEqual(self.run_with(self.dir), 0)

    def test_unpacked_jar_folder(self):
        jar = os.path.join(self.dir, "1.2.5.zip")
        make_jar(jar)
        unpacked = os.path.join(self.dir, "unpacked")
        with zipfile.ZipFile(jar) as z:
            z.extractall(unpacked)
        self.assertEqual(self.run_with(unpacked), 0)

    def test_folder_without_jar(self):
        self.assertEqual(self.run_with(self.dir), 2)
        self.assertEqual(self.run_with(os.path.join(self.dir, "missing")), 2)

    def test_no_tutorial_option(self):
        jar = os.path.join(self.dir, "1.2.5.jar")
        make_jar(jar)
        self.assertEqual(cli.main([jar, "-o", self.out, "--no-tutorial"]), 0)
        self.assertFalse(any(n.startswith("assets/legacy/tutorial/") for n in mcpk.read_pak(self.out)))
        self.assertEqual(cli.main([jar, "-o", self.out]), 0)
        self.assertIn("assets/legacy/tutorial/level.dat", mcpk.read_pak(self.out))

    def test_import_option_is_gone(self):
        with self.assertRaises(SystemExit):
            cli.main(["--opticraft-pak", "assets.pak"])

    def test_folder_is_required(self):
        self.assertEqual(cli.main(["-o", self.out]), 2)
        self.assertFalse(os.path.exists(self.out))


if __name__ == "__main__":
    unittest.main()
