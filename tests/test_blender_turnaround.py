import contextlib
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from helpers import SCRIPTS, run_script

import blender_turnaround as bt

BLENDER = shutil.which("blender")
REAL = os.environ.get("FORGE_TEST_BLENDER") == "1" and BLENDER is not None


class ArgumentTests(unittest.TestCase):
    def test_views_become_even_angles(self):
        args = bt.parse_args(["blender", "--", "--input", "a.glb", "--output", "o.png", "--views", "4"])
        self.assertEqual(args.angle_list, [0.0, 90.0, 180.0, 270.0])

    def test_explicit_angles(self):
        args = bt.parse_args(["blender", "--", "--input", "a.glb", "--output", "o.png", "--angles", "10, 200"])
        self.assertEqual(args.angle_list, [10.0, 200.0])

    def test_bad_arguments_exit_2(self):
        for extra in (["--views", "0"], ["--angles", "x"], ["--size", "8"]):
            with self.subTest(extra=extra), self.assertRaises(SystemExit) as ctx, \
                    contextlib.redirect_stderr(io.StringIO()):
                bt.parse_args(["blender", "--", "--input", "a.glb", "--output", "o.png", *extra])
            self.assertEqual(ctx.exception.code, 2)

    def test_outside_blender_explains_itself(self):
        res = run_script("blender_turnaround.py", "--", "--input", "a.glb", "--output", "o.png")
        self.assertEqual(res.returncode, 2)
        self.assertIn("must run inside Blender", res.stderr)


@unittest.skipUnless(REAL, "set FORGE_TEST_BLENDER=1 with blender on PATH to render for real")
class RealBlenderTests(unittest.TestCase):
    def test_renders_strip_and_stats(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            asset = tmp / "asset.glb"
            make = ("import bpy; bpy.ops.wm.read_factory_settings(use_empty=True); "
                    "bpy.ops.mesh.primitive_monkey_add(); bpy.ops.mesh.primitive_torus_add(location=(2.5, 0, 0)); "
                    f"bpy.ops.export_scene.gltf(filepath={str(asset)!r})")
            subprocess.run([BLENDER, "-b", "--factory-startup", "--python-exit-code", "1", "--python-expr", make],
                           check=True, capture_output=True, timeout=300)
            out = tmp / "turn" / "asset.png"
            res = subprocess.run([BLENDER, "-b", "--factory-startup", "--python-exit-code", "1", "-P",
                                  str(SCRIPTS / "blender_turnaround.py"), "--", "--input", str(asset), "--output",
                                  str(out), "--size", "128", "--samples", "4", "--engine", "workbench"],
                                 capture_output=True, text=True, timeout=300)
            self.assertEqual(res.returncode, 0, res.stdout[-2000:] + res.stderr[-2000:])
            self.assertIn("FORGE_TURNAROUND", res.stdout)
            stats = json.loads(out.with_suffix(".json").read_text())
            self.assertEqual(stats["mesh_objects"], 2)
            self.assertGreater(stats["triangles"], 500)
            self.assertEqual(out.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
            missing = subprocess.run([BLENDER, "-b", "--factory-startup", "--python-exit-code", "1", "-P",
                                      str(SCRIPTS / "blender_turnaround.py"), "--", "--input", str(tmp / "nope.glb"),
                                      "--output", str(out)], capture_output=True, timeout=300)
            self.assertEqual(missing.returncode, 2)


if __name__ == "__main__":
    unittest.main()
