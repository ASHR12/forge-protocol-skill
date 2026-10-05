"""Shared fixtures for the forge-protocol test suite (standard library only)."""
from __future__ import annotations

import contextlib
import io
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILL = REPO / "forge-protocol"
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))

import forge  # noqa: E402
import make_sxs  # noqa: E402

HAS_FFMPEG = shutil.which("ffmpeg") is not None

BAR_EXTRA = """
## C4 Typography hierarchy
- PASS when: headline, subhead and body read as three distinct levels at a glance in every hero still.
- FAIL signs: one weight everywhere, sizes within a step of each other.

## C5 Lighting and depth
- PASS when: the orb shows a lit side, a shadow side and a rim that separates it from the background.
- FAIL signs: flat fill, no light direction.
"""


def run_script(name: str, *args: str, cwd: Path | None = None, env: dict | None = None,
               stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPTS / name), *args], cwd=cwd, env=env, input=stdin,
                          capture_output=True, text=True, timeout=120)


def call(main, argv: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = main(argv)
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 2
    return code, out.getvalue(), err.getvalue()


def solid_png(path: Path, width: int, height: int, rgb: tuple[int, int, int]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    row = bytes((*rgb, 255)) * width
    make_sxs.write_png(path, width, height, [row] * height)
    return path


def read_png(path: Path) -> tuple[int, int, int, list[bytes]]:
    """Decode an 8-bit non-interlaced RGB/RGBA PNG into (width, height, channels, rows)."""
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    pos, idat, width = 8, b"", 0
    while pos < len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        tag = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        if tag == b"IHDR":
            width, height, depth, ctype, _, _, interlace = struct.unpack(">IIBBBBB", body)
            assert depth == 8 and interlace == 0 and ctype in (2, 6), (depth, ctype, interlace)
            channels = 3 if ctype == 2 else 4
        elif tag == b"IDAT":
            idat += body
        pos += 12 + length
    raw = zlib.decompress(idat)
    stride = width * channels
    rows, prev = [], bytearray(stride)
    for y in range(height):
        ftype = raw[y * (stride + 1)]
        line = bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for x in range(stride):
            a = line[x - channels] if x >= channels else 0
            b = prev[x]
            c = prev[x - channels] if x >= channels else 0
            if ftype == 1:
                line[x] = (line[x] + a) & 0xFF
            elif ftype == 2:
                line[x] = (line[x] + b) & 0xFF
            elif ftype == 3:
                line[x] = (line[x] + (a + b) // 2) & 0xFF
            elif ftype == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 0xFF
        rows.append(bytes(line))
        prev = line
    return width, height, channels, rows


def pixel(decoded, x: int, y: int) -> tuple[int, ...]:
    width, height, channels, rows = decoded
    return tuple(rows[y][x * channels:(x + 1) * channels][:3])


class Project:
    """A scaffolded forge project in a temp dir with a published 5-criterion bar."""

    def __init__(self, mode: str = "standard", publish: bool = True):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "proj"
        code, out, err = call(forge.main, ["--project", str(self.root), "init", "--mode", mode, "--title", "Orb Page",
                                           "--goal", "A launch page for a glowing orb lamp.", "--pack", "web-ui"])
        assert code == 0, err
        bar = self.root / "art" / "BAR.md"
        text = bar.read_text(encoding="utf-8").split("<!-- Add goal-specific")[0] + BAR_EXTRA
        bar.write_text(text, encoding="utf-8")
        if publish:
            code, out, err = self.forge("bar", "publish", "--reason", "initial bar")
            assert code == 0, err

    def close(self) -> None:
        self._tmp.cleanup()

    def forge(self, *args: str) -> tuple[int, str, str]:
        return call(forge.main, ["--project", str(self.root), *args])

    def path(self, rel: str) -> Path:
        return self.root / rel

    def capture(self, stills: int = 3, frames: int = 2, shade: int = 60) -> str:
        for i in range(1, stills + 1):
            solid_png(self.path(f"artifacts/stills/still-{i:02d}.png"), 64, 36, (shade + i, 40, 90))
        for i in range(1, frames + 1):
            solid_png(self.path(f"artifacts/walkthrough-frames/frame-{i:02d}.png"), 64, 36, (shade, 20 + i, 60))
        code, _, err = self.forge("manifest")
        assert code == 0, err
        code, _, err = self.forge("log", "--result", "CAPTURE")
        assert code == 0, err
        code, out, _ = self.forge("build-id")
        return out.strip()


def verdict(kind: str, round_label: str, build: str, bar_version: int = 1, c4: str = "PASS", c5: str = "PASS",
            stills: int = 3, frames: int = 2, extra: str = "") -> str:
    still_ids = ", ".join(f"still-{i:02d}" for i in range(1, stills + 1))
    frame_ids = ", ".join(f"frame-{i:02d}" for i in range(1, frames + 1)) or "no frames"
    lines = [
        f"VERDICT: {kind}", "SCOPE: loop", f"ROUND: {round_label}", f"BUILD: {build}",
        f"BAR: v{bar_version} (5 criteria)", "CRITERIA:",
        f"C1 Goal fit: PASS. {still_ids} show the orb hero, the pricing cards and the signup state.",
        f"C2 Live capture provenance: PASS. MANIFEST.md lists build {build} for {still_ids}.",
        f"C3 State and motion integrity: PASS. {frame_ids} show finished content with no placeholders.",
        f"C4 Typography hierarchy: {c4}. still-01 headline {'dominates clearly' if c4 == 'PASS' else 'shares one weight with the subhead'}.",
        f"C5 Lighting and depth: {c5}. still-03 orb {'shows a lit side, shadow side and rim' if c5 == 'PASS' else 'reads as a flat disc'}.",
    ]
    punch = []
    if c4 == "FAIL":
        punch.append("[C4 Typography hierarchy] still-01, hero: headline and subhead read as one level. Done when the headline dominates at a glance in still-01.")
    if c5 == "FAIL":
        punch.append("[C5 Lighting and depth] still-03, orb: no light direction. Done when still-03 shows a lit side, a shadow side and a rim.")
    if punch:
        lines.append("PUNCH LIST:")
        lines += [f"{i}. {text}" for i, text in enumerate(punch, start=1)]
    return "\n".join(lines) + ("\n" + extra if extra else "") + "\n"
