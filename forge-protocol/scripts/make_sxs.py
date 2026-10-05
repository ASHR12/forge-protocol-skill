#!/usr/bin/env python3
"""Round-over-round comparison composites for forge-protocol runs.

Pairs the stills of two rounds by slot number (still-03 with still-03) and writes, per pair:
  sxs-NN.png            left | right, labelled, each side letterboxed to the same canvas, <= --max-edge
  sxs-NN-blur.png       (--blur) both sides blurred with the same sigma, then halved: does it read better at a glance?
  sxs-NN-detail-Q.png   (--detail) quadrant Q of left stacked over right at native scale, for fine detail
With --blind the sides are shuffled per pair and labelled A and B; the side key goes to a separate file so a
fresh critic can judge which round is better without knowing which is which.

  make_sxs.py [--project .] [--prev R02 --curr R03]       two snapshots in artifacts/history (default: latest two)
  make_sxs.py --left DIR --right DIR [--left-label OLD --right-label NEW] [--out DIR]
  options: --blur [--sigma 18] --detail --blind [--key FILE] [--seed N] --max-edge 2000 --pair slot|name --dry-run

Needs ffmpeg on PATH (labels are drawn by this script, so builds without drawtext work).
Exit codes: 0 ok, 1 nothing paired or --strict pairing failure, 2 usage or dependency error, 3 ffmpeg failure.
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import forgelib as fl  # noqa: E402

PAD_COLOR = "0x111111"

FONT_5X7 = {
    "A": (14, 17, 17, 31, 17, 17, 17), "B": (30, 17, 17, 30, 17, 17, 30), "C": (14, 17, 16, 16, 16, 17, 14),
    "D": (28, 18, 17, 17, 17, 18, 28), "E": (31, 16, 16, 30, 16, 16, 31), "F": (31, 16, 16, 30, 16, 16, 16),
    "G": (14, 17, 16, 23, 17, 17, 15), "H": (17, 17, 17, 31, 17, 17, 17), "I": (14, 4, 4, 4, 4, 4, 14),
    "J": (7, 2, 2, 2, 2, 18, 12), "K": (17, 18, 20, 24, 20, 18, 17), "L": (16, 16, 16, 16, 16, 16, 31),
    "M": (17, 27, 21, 21, 17, 17, 17), "N": (17, 17, 25, 21, 19, 17, 17), "O": (14, 17, 17, 17, 17, 17, 14),
    "P": (30, 17, 17, 30, 16, 16, 16), "Q": (14, 17, 17, 17, 21, 18, 13), "R": (30, 17, 17, 30, 20, 18, 17),
    "S": (15, 16, 16, 14, 1, 1, 30), "T": (31, 4, 4, 4, 4, 4, 4), "U": (17, 17, 17, 17, 17, 17, 14),
    "V": (17, 17, 17, 17, 17, 10, 4), "W": (17, 17, 17, 21, 21, 21, 10), "X": (17, 17, 10, 4, 10, 17, 17),
    "Y": (17, 17, 17, 10, 4, 4, 4), "Z": (31, 1, 2, 4, 8, 16, 31),
    "0": (14, 17, 19, 21, 25, 17, 14), "1": (4, 12, 4, 4, 4, 4, 14), "2": (14, 17, 1, 2, 4, 8, 31),
    "3": (31, 2, 4, 2, 1, 17, 14), "4": (2, 6, 10, 18, 31, 2, 2), "5": (31, 16, 30, 1, 1, 17, 14),
    "6": (6, 8, 16, 30, 17, 17, 14), "7": (31, 1, 2, 4, 8, 8, 8), "8": (14, 17, 17, 14, 17, 17, 14),
    "9": (14, 17, 17, 15, 1, 2, 12), " ": (0, 0, 0, 0, 0, 0, 0), "-": (0, 0, 0, 31, 0, 0, 0),
    "(": (2, 4, 8, 8, 8, 4, 2), ")": (8, 4, 2, 2, 2, 4, 8), ".": (0, 0, 0, 0, 0, 12, 12),
    "/": (1, 2, 2, 4, 8, 8, 16), ":": (0, 12, 12, 0, 12, 12, 0), "_": (0, 0, 0, 0, 0, 0, 31),
    "#": (10, 10, 31, 10, 31, 10, 10), "+": (0, 4, 4, 31, 4, 4, 0), "?": (14, 17, 1, 2, 4, 0, 4),
}


class CompareError(Exception):
    def __init__(self, message: str, code: int = 2):
        super().__init__(message)
        self.code = code


def write_png(path: Path, width: int, height: int, rgba_rows: list[bytes]) -> None:
    raw = b"".join(b"\x00" + row for row in rgba_rows)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def render_label(text: str, path: Path, scale: int = 3) -> tuple[int, int]:
    """White 5x7 bitmap text on a translucent dark pill; returns (width, height)."""
    glyphs = [FONT_5X7.get(ch, FONT_5X7["?"]) for ch in text.upper()]
    pad = 3 * scale
    width = pad * 2 + max(1, len(glyphs)) * 6 * scale - scale
    height = pad * 2 + 7 * scale
    bg, fg = bytes((0, 0, 0, 170)), bytes((255, 255, 255, 255))
    rows = []
    for y in range(height):
        row = bytearray(bg * width)
        gy = (y - pad) // scale
        if 0 <= gy < 7 and y >= pad:
            for gi, glyph in enumerate(glyphs):
                bits = glyph[gy]
                for gx in range(5):
                    if bits & (1 << (4 - gx)):
                        x0 = pad + (gi * 6 + gx) * scale
                        for x in range(x0, x0 + scale):
                            row[x * 4:(x + 1) * 4] = fg
        rows.append(bytes(row))
    write_png(path, width, height, rows)
    return width, height


def probe_size(path: Path) -> tuple[int, int]:
    size = fl.image_size(path)
    if size:
        return size
    if shutil.which("ffprobe"):
        out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                              "-of", "csv=p=0:s=x", str(path)], capture_output=True, text=True)
        if out.returncode == 0 and "x" in out.stdout:
            w, h = out.stdout.strip().split("x")[:2]
            return int(w), int(h)
    raise CompareError(f"cannot read image size of {path}")


def even(value: float) -> int:
    return max(2, int(round(value / 2.0)) * 2)


def pair_images(left: list[Path], right: list[Path], mode: str) -> tuple[list[tuple[str, Path, Path]], list[str]]:
    def index(files: list[Path], side: str) -> dict[str, Path]:
        table: dict[str, Path] = {}
        for path in files:
            key = path.stem if mode == "name" else fl.slot_key(path.name)
            if key is None:
                continue
            if key in table:
                raise CompareError(f"two {side} files share slot {key}: {table[key].name}, {path.name}")
            table[key] = path
        return table

    lmap, rmap = index(left, "left"), index(right, "right")
    keys = [k for k in lmap if k in rmap]
    keys.sort(key=lambda k: (not k.isdigit(), int(k) if k.isdigit() else 0, k))
    unpaired = [f"left only: {lmap[k].name}" for k in lmap if k not in rmap]
    unpaired += [f"right only: {rmap[k].name}" for k in rmap if k not in lmap]
    pid = lambda k: f"{int(k):02d}" if k.isdigit() else k  # noqa: E731
    return [(pid(k), lmap[k], rmap[k]) for k in keys], unpaired


def run_ffmpeg(inputs: list[Path], graph: str, out: Path) -> None:
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    for path in inputs:
        cmd += ["-i", str(path)]
    cmd += ["-filter_complex", graph, "-map", "[out]", "-frames:v", "1", "-update", "1", str(out)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = (proc.stderr or "").strip().splitlines()[-5:]
        raise CompareError(f"ffmpeg failed for {out.name}: {' / '.join(tail) or 'no stderr'}", code=3)


def fit(stream: str, w: int, h: int, tag: str) -> str:
    return (f"[{stream}]scale={w}:{h}:force_original_aspect_ratio=decrease:flags=lanczos,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color={PAD_COLOR},format=rgba[{tag}]")


def build_outputs(slot: str, a: Path, b: Path, labels: tuple[Path, Path], out_dir: Path, opts) -> list[str]:
    (aw, ah), (bw, bh) = probe_size(a), probe_size(b)
    aspect = max(aw / ah, bw / bh)
    height = even(opts.height or min(opts.max_edge, max(ah, bh), int(opts.max_edge / (2 * aspect))))
    half_w = even(height * aspect)
    while not opts.height and (2 * half_w > opts.max_edge or height > opts.max_edge) and height > 2:
        height -= 2
        half_w = even(height * aspect)
    inputs = [a, b, labels[0], labels[1]]
    name = f"sxs-{slot}"
    written = []

    graph = (f"{fit('0:v', half_w, height, 'l')};{fit('1:v', half_w, height, 'r')};"
             f"[l][2:v]overlay=12:12[lo];[r][3:v]overlay=12:12[ro];[lo][ro]hstack=inputs=2,format=rgb24[out]")
    run_ffmpeg(inputs, graph, out_dir / f"{name}.png")
    written.append(f"{name}.png")

    if opts.blur:
        sigma = max(0.5, opts.sigma * height / 1080.0)
        bh2, bw2 = even(height / 2), even(half_w / 2)
        graph = (f"{fit('0:v', half_w, height, 'l')};{fit('1:v', half_w, height, 'r')};"
                 f"[l]gblur=sigma={sigma:.2f},scale={bw2}:{bh2}[lb];[r]gblur=sigma={sigma:.2f},scale={bw2}:{bh2}[rb];"
                 f"[lb][2:v]overlay=8:8[lo];[rb][3:v]overlay=8:8[ro];[lo][ro]hstack=inputs=2,format=rgb24[out]")
        run_ffmpeg(inputs, graph, out_dir / f"{name}-blur.png")
        written.append(f"{name}-blur.png")

    if opts.detail:
        dh = even(min(max(ah, bh), opts.max_edge))
        dw = even(dh * aspect)
        if dw // 2 > opts.max_edge:
            dw = even(2 * opts.max_edge)
            dh = even(dw / aspect)
        qw, qh = dw // 2, dh // 2
        for q, (x, y) in enumerate(((0, 0), (qw, 0), (0, qh), (qw, qh)), start=1):
            graph = (f"{fit('0:v', dw, dh, 'l')};{fit('1:v', dw, dh, 'r')};"
                     f"[l]crop={qw}:{qh}:{x}:{y}[lc];[r]crop={qw}:{qh}:{x}:{y}[rc];"
                     f"[lc][2:v]overlay=8:8[lo];[rc][3:v]overlay=8:8[ro];[lo][ro]vstack=inputs=2,format=rgb24[out]")
            run_ffmpeg(inputs, graph, out_dir / f"{name}-detail-{q}.png")
            written.append(f"{name}-detail-{q}.png")
    return written


def resolve_sides(args, project: Path, cfg: dict) -> tuple[Path, Path, str, str, str]:
    if args.left or args.right:
        if not (args.left and args.right):
            raise CompareError("--left and --right go together")
        left, right = Path(args.left).expanduser(), Path(args.right).expanduser()
        llabel = args.left_label or left.name
        rlabel = args.right_label or right.name
        default_name = f"{llabel}-vs-{rlabel}"
    else:
        history = fl.resolve(project, cfg, "history")
        snaps = sorted((p for p in history.iterdir() if p.is_dir() and fl.round_number(p.name) is not None),
                       key=lambda p: fl.round_number(p.name)) if history.is_dir() else []
        by_label = {fl.round_label(fl.round_number(p.name)): p for p in snaps}
        if args.prev or args.curr:
            labels = []
            for value in (args.prev, args.curr):
                n = fl.round_number(value or "")
                if n is None or fl.round_label(n) not in by_label:
                    raise CompareError(f"no snapshot for {value!r} in {history}; snapshot with: forge.py snapshot R<n>")
                labels.append(fl.round_label(n))
            left, right = by_label[labels[0]], by_label[labels[1]]
        else:
            if len(snaps) < 2:
                raise CompareError(f"need two round snapshots in {history} (found {len(snaps)}); run forge.py snapshot R<n> "
                                   "after each round, or pass --left/--right", code=1)
            left, right = snaps[-2], snaps[-1]
        llabel = args.left_label or fl.round_label(fl.round_number(left.name))
        rlabel = args.right_label or fl.round_label(fl.round_number(right.name))
        default_name = f"{llabel}-vs-{rlabel}"
    if not left.is_dir() or not right.is_dir():
        raise CompareError(f"folders not found: {left if not left.is_dir() else right}")
    return left, right, llabel, rlabel, default_name


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=__doc__.split("\n\n", 1)[1])
    parser.add_argument("--project", default=".", help="project root (default: current directory)")
    parser.add_argument("--prev", help="earlier round snapshot, e.g. R02")
    parser.add_argument("--curr", help="later round snapshot, e.g. R03")
    parser.add_argument("--left", help="any capture folder for the left side")
    parser.add_argument("--right", help="any capture folder for the right side")
    parser.add_argument("--left-label")
    parser.add_argument("--right-label")
    parser.add_argument("--out", help="output folder (default: artifacts/compare/<left>-vs-<right>[-blind])")
    parser.add_argument("--pair", choices=["slot", "name"], default="slot", help="pair by slot number or exact file stem")
    parser.add_argument("--blur", action="store_true", help="also write equal-sigma blurred pairs")
    parser.add_argument("--sigma", type=float, default=18.0, help="blur sigma at 1080p (default 18)")
    parser.add_argument("--detail", action="store_true", help="also write quadrant detail tiles at native scale")
    parser.add_argument("--blind", action="store_true", help="shuffle sides per pair, label A/B, write the key separately")
    parser.add_argument("--key", help="where to write the blind key (default: artifacts/compare/keys/<name>.json)")
    parser.add_argument("--seed", type=int, help="seed for the blind shuffle (default: random)")
    parser.add_argument("--max-edge", type=int, default=2000, help="longest composite edge in px (default 2000)")
    parser.add_argument("--height", type=int, help="force the composite height instead of fitting --max-edge")
    parser.add_argument("--strict", action="store_true", help="fail when any file is unpaired")
    parser.add_argument("--dry-run", action="store_true", help="print the pairs and exit")
    args = parser.parse_args(argv)
    try:
        if args.max_edge < 200:
            raise CompareError("--max-edge must be at least 200")
        if args.sigma <= 0:
            raise CompareError("--sigma must be positive")
        project = Path(args.project).expanduser().resolve()
        cfg = fl.load_config(project)
        left, right, llabel, rlabel, default_name = resolve_sides(args, project, cfg)
        pairs, unpaired = pair_images(fl.list_images(left), fl.list_images(right), args.pair)
        for note in unpaired:
            print(f"warning: unpaired {note}", file=sys.stderr)
        if not pairs:
            raise CompareError(f"no pairs between {left} and {right}", code=1)
        if args.strict and unpaired:
            raise CompareError("unpaired files with --strict", code=1)
        name = default_name + ("-blind" if args.blind else "")
        out_dir = Path(args.out).expanduser() if args.out else fl.resolve(project, cfg, "compare") / name
        if args.dry_run:
            for slot, a, b in pairs:
                print(f"{slot}: {a} | {b}")
            return 0
        if not shutil.which("ffmpeg"):
            raise CompareError("ffmpeg is required on PATH (macOS: brew install ffmpeg; Debian/Ubuntu: apt install ffmpeg)")
        out_dir.mkdir(parents=True, exist_ok=True)
        rng = random.Random(args.seed)
        key = {"left": str(left), "right": str(right), "left_label": llabel, "right_label": rlabel, "pairs": {}}
        manifest = {"left_label": "A" if args.blind else llabel, "right_label": "B" if args.blind else rlabel,
                    "blind": args.blind, "pairs": []}
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            for slot, a, b in pairs:
                swap = args.blind and rng.random() < 0.5
                first, second = (b, a) if swap else (a, b)
                names = ("A", "B") if args.blind else (llabel, rlabel)
                lab = (tmpdir / f"{slot}-l.png", tmpdir / f"{slot}-r.png")
                render_label(names[0], lab[0])
                render_label(names[1], lab[1])
                written = build_outputs(slot, first, second, lab, out_dir, args)
                entry = {"slot": slot, "files": written}
                if not args.blind:
                    entry.update({"left": a.name, "right": b.name})
                manifest["pairs"].append(entry)
                if args.blind:
                    key["pairs"][slot] = {"A": rlabel if swap else llabel, "B": llabel if swap else rlabel}
        (out_dir / "pairs.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        if args.blind:
            key_path = Path(args.key).expanduser() if args.key else fl.resolve(project, cfg, "compare") / "keys" / f"{name}.json"
            if key_path.resolve().parent == out_dir.resolve():
                raise CompareError("--key must live outside the output folder the critic sees")
            key_path.parent.mkdir(parents=True, exist_ok=True)
            key_path.write_text(json.dumps(key, indent=2) + "\n", encoding="utf-8")
            print(f"blind key: {key_path} (keep it away from the critic)")
        print(f"Wrote {len(pairs)} comparison pairs to {out_dir}")
        return 0
    except (CompareError, fl.ForgeError) as exc:
        print(f"make_sxs.py: {exc}", file=sys.stderr)
        return exc.code if exc.code in (1, 2, 3) else 2


if __name__ == "__main__":
    sys.exit(main())
