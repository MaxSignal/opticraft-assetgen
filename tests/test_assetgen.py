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

    def test_opticraft_pak_fills_gaps(self):
        entries = make_jar(self.jar)
        release = os.path.join(self.dir, "release.pak")
        mcpk.write_pak(release, {
            "assets/terrain.png": b"release terrain",          # jar wins
            "assets/ctm.png": b"ctm",                           # added
            "assets/legacy/tutorial/level.dat": b"world",       # added
            "assets/legacy/tutorial/session.lock": b"lock",     # never needed
            "resources/newsound/step/grass1.ogg": b"sound",     # no sound on Nspire
        })
        report = build.build(self.jar, self.out, release)
        files = mcpk.read_pak(self.out)
        self.assertEqual(files["assets/terrain.png"], entries["terrain.png"])
        self.assertEqual(files["assets/ctm.png"], b"ctm")
        self.assertIn("assets/legacy/tutorial/level.dat", files)
        self.assertNotIn("assets/legacy/tutorial/session.lock", files)
        self.assertFalse(any(name.startswith("resources/") for name in files))
        self.assertEqual(report.from_opticraft_pak, 2)

        build.build(self.jar, self.out, release, tutorial=False)
        self.assertNotIn("assets/legacy/tutorial/level.dat", mcpk.read_pak(self.out))


class FromOptiCraftTests(unittest.TestCase):
    RELEASE = {
        "assets/terrain.png": b"terrain",
        "assets/legacy/title.png": b"release title",
        "assets/legacy/tutorial/level.dat": b"world",
        "assets/legacy/tutorial/session.lock": b"lock",
        "resources/newsound/step/grass1.ogg": b"sound",
    }

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        self.out = os.path.join(self.dir, "assets.pak.tns")

    def tearDown(self):
        self.tmp.cleanup()

    def check(self, files, tutorial=True):
        self.assertEqual(files["assets/terrain.png"], b"terrain")
        self.assertEqual(files["assets/legacy/title.png"], b"release title")  # the release's own wins
        self.assertIn("assets/cursor.png", files)                             # bundled fills the gap
        self.assertNotIn("assets/legacy/tutorial/session.lock", files)
        self.assertFalse(any(name.startswith("resources/") for name in files))
        self.assertEqual("assets/legacy/tutorial/level.dat" in files, tutorial)

    def test_from_pak(self):
        release = os.path.join(self.dir, "assets.pak")
        mcpk.write_pak(release, self.RELEASE)
        report = build.build_from_opticraft(release, self.out)
        self.check(mcpk.read_pak(self.out))
        self.assertEqual(report.from_opticraft_pak, 3)
        build.build_from_opticraft(release, self.out, tutorial=False)
        self.check(mcpk.read_pak(self.out), tutorial=False)

    def test_from_data_folder(self):
        data = os.path.join(self.dir, "data")
        for name, content in self.RELEASE.items():
            os.makedirs(os.path.dirname(os.path.join(data, name)), exist_ok=True)
            with open(os.path.join(data, name), "wb") as f:
                f.write(content)
        build.build_from_opticraft(data, self.out)
        self.check(mcpk.read_pak(self.out))

    def test_rejects_other_files(self):
        path = os.path.join(self.dir, "not.pak")
        with open(path, "wb") as f:
            f.write(b"not a pak at all, just some bytes padding the header out")
        with self.assertRaises(build.OptiCraftPakError):
            build.build_from_opticraft(path, self.out)
        empty = os.path.join(self.dir, "empty.pak")
        mcpk.write_pak(empty, {"assets/lang/en_US.lang": b""})
        with self.assertRaises(build.OptiCraftPakError):
            build.build_from_opticraft(empty, self.out)

    def test_cli(self):
        release = os.path.join(self.dir, "assets.pak")
        mcpk.write_pak(release, self.RELEASE)
        self.assertEqual(cli.main(["--opticraft-pak", release, "-o", self.out, "--no-tutorial"]), 0)
        self.check(mcpk.read_pak(self.out), tutorial=False)
        self.assertEqual(cli.main(["--opticraft-pak", os.path.join(self.dir, "missing"), "-o", self.out]), 2)


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

    def test_folder_is_required(self):
        self.assertEqual(cli.main(["-o", self.out]), 2)
        self.assertFalse(os.path.exists(self.out))


if __name__ == "__main__":
    unittest.main()
