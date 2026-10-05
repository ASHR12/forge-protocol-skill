import json
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path

from helpers import HAS_FFMPEG, call, make_sxs, pixel, read_png, run_script, solid_png

import forgelib as fl

RED, BLUE = (220, 30, 30), (30, 60, 220)


class PairingTests(unittest.TestCase):
    def test_pairs_by_slot_number_and_reports_leftovers(self):
        left = [Path("still-1.png"), Path("still-02.png"), Path("still-04.jpg")]
        right = [Path("still-01.png"), Path("still-2.png"), Path("still-03.png")]
        pairs, unpaired = make_sxs.pair_images(left, right, "slot")
        self.assertEqual([(slot, a.name, b.name) for slot, a, b in pairs],
                         [("01", "still-1.png", "still-01.png"), ("02", "still-02.png", "still-2.png")])
        self.assertEqual(sorted(unpaired), ["left only: still-04.jpg", "right only: still-03.png"])

    def test_duplicate_slots_are_an_error(self):
        with self.assertRaises(make_sxs.CompareError):
            make_sxs.pair_images([Path("still-01.png"), Path("hero-1.png")], [Path("still-01.png")], "slot")

    def test_pair_by_name(self):
        pairs, unpaired = make_sxs.pair_images([Path("hero.png"), Path("menu.png")], [Path("hero.png")], "name")
        self.assertEqual([p[0] for p in pairs], ["hero"])
        self.assertEqual(unpaired, ["left only: menu.png"])


class ImageSizeTests(unittest.TestCase):
    def test_png_gif_webp_jpeg_headers(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.assertEqual(fl.image_size(solid_png(tmp / "a.png", 37, 21, RED)), (37, 21))
            (tmp / "a.gif").write_bytes(b"GIF89a" + struct.pack("<HH", 300, 200) + b"\0" * 20)
            self.assertEqual(fl.image_size(tmp / "a.gif"), (300, 200))
            vp8x = b"RIFF" + b"\0" * 4 + b"WEBPVP8X" + b"\0" * 8 + (1919).to_bytes(3, "little") + (1079).to_bytes(3, "little")
            (tmp / "a.webp").write_bytes(vp8x + b"\0" * 8)
            self.assertEqual(fl.image_size(tmp / "a.webp"), (1920, 1080))
            jpeg = b"\xff\xd8\xff\xe0" + struct.pack(">H", 16) + b"JFIF\0" + b"\0" * 9 + \
                   b"\xff\xc0" + struct.pack(">HBHH", 17, 8, 720, 1280) + b"\0" * 12 + b"\xff\xd9"
            (tmp / "a.jpg").write_bytes(jpeg)
            self.assertEqual(fl.image_size(tmp / "a.jpg"), (1280, 720))
            (tmp / "a.txt").write_text("nope")
            self.assertIsNone(fl.image_size(tmp / "a.txt"))

    def test_label_renders_a_valid_png(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "label.png"
            width, height = make_sxs.render_label("R02 a/b", path)
            decoded = read_png(path)
            self.assertEqual(decoded[:3], (width, height, 4))
            self.assertIn((255, 255, 255), {pixel(decoded, x, y) for x in range(width) for y in range(height)})


class CliTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        for rnd, color, slot2 in (("R01", RED, (120, 260)), ("R02", BLUE, (260, 260))):
            solid_png(self.root / f"artifacts/history/{rnd}/still-01.png", 320, 180, color)
            solid_png(self.root / f"artifacts/history/{rnd}/still-02.png", *slot2, color)

    def tearDown(self):
        self._tmp.cleanup()

    def test_help_and_dry_run_need_no_ffmpeg(self):
        env = {"PATH": "/nonexistent"}
        self.assertEqual(run_script("make_sxs.py", "--help", env=env).returncode, 0)
        res = run_script("make_sxs.py", "--project", str(self.root), "--dry-run", env=env)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("01:", res.stdout)
        res = run_script("make_sxs.py", "--project", str(self.root), env=env)
        self.assertEqual(res.returncode, 2)
        self.assertIn("ffmpeg is required", res.stderr)

    def test_needs_two_snapshots(self):
        code, _, err = call(make_sxs.main, ["--project", str(self.root), "--prev", "R01", "--curr", "R09"])
        self.assertEqual(code, 2)
        self.assertIn("no snapshot", err)
        empty = self.root / "empty"
        empty.mkdir()
        self.assertEqual(call(make_sxs.main, ["--project", str(empty)])[0], 1)

    @unittest.skipUnless(HAS_FFMPEG, "ffmpeg not on PATH")
    def test_composites_respect_max_edge_and_letterbox(self):
        code, _, err = call(make_sxs.main, ["--project", str(self.root), "--blur", "--detail", "--max-edge", "640"])
        self.assertEqual(code, 0, err)
        out = self.root / "artifacts/compare/R01-vs-R02"
        pairs = json.loads((out / "pairs.json").read_text())
        self.assertEqual(len(pairs["pairs"]), 2)
        self.assertEqual(len(pairs["pairs"][0]["files"]), 6)
        wide = read_png(out / "sxs-01.png")
        self.assertLessEqual(max(wide[0], wide[1]), 640)
        self.assertGreater(pixel(wide, wide[0] // 4, wide[1] // 2)[0], 150)
        self.assertGreater(pixel(wide, 3 * wide[0] // 4, wide[1] // 2)[2], 150)
        tall = read_png(out / "sxs-02.png")
        self.assertLessEqual(max(tall[0], tall[1]), 640)
        pad = pixel(tall, 2, tall[1] // 2)
        self.assertTrue(all(v < 40 for v in pad), f"expected dark letterbox, got {pad}")
        blur = read_png(out / "sxs-01-blur.png")
        self.assertEqual((blur[0], blur[1]), (wide[0] // 2, wide[1] // 2))
        detail = read_png(out / "sxs-01-detail-1.png")
        self.assertEqual((detail[0], detail[1]), (160, 180))

    @unittest.skipUnless(HAS_FFMPEG, "ffmpeg not on PATH")
    def test_blind_key_matches_pixels_and_stays_outside_output(self):
        code, _, err = call(make_sxs.main, ["--project", str(self.root), "--blind", "--seed", "4"])
        self.assertEqual(code, 0, err)
        out = self.root / "artifacts/compare/R01-vs-R02-blind"
        key = json.loads((self.root / "artifacts/compare/keys/R01-vs-R02-blind.json").read_text())
        listing = json.loads((out / "pairs.json").read_text())
        self.assertTrue(listing["blind"])
        self.assertNotIn("left", listing["pairs"][0])
        for slot in ("01", "02"):
            image = read_png(out / f"sxs-{slot}.png")
            left_px = pixel(image, image[0] // 4, image[1] // 2)
            left_round = "R01" if left_px[0] > left_px[2] else "R02"
            self.assertEqual(key["pairs"][slot]["A"], left_round)
        code, _, err = call(make_sxs.main, ["--project", str(self.root), "--blind", "--key",
                                            str(self.root / "artifacts/compare/R01-vs-R02-blind/key.json")])
        self.assertEqual(code, 2)
        self.assertIn("outside the output folder", err)

    @unittest.skipUnless(HAS_FFMPEG, "ffmpeg not on PATH")
    def test_explicit_folders_and_labels(self):
        code, _, err = call(make_sxs.main, ["--left", str(self.root / "artifacts/history/R01"),
                                            "--right", str(self.root / "artifacts/history/R02"),
                                            "--left-label", "before", "--right-label", "after",
                                            "--out", str(self.root / "cmp"), "--project", str(self.root)])
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads((self.root / "cmp/pairs.json").read_text())["left_label"], "before")
        probe = subprocess.run(["ffprobe", "-v", "error", str(self.root / "cmp/sxs-01.png")], capture_output=True)
        self.assertEqual(probe.returncode, 0)


if __name__ == "__main__":
    unittest.main()
