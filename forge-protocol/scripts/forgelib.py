"""Shared conventions for the forge-protocol scripts: project paths, the rounds.log
event format, BAR.md and verdict parsing, image sizes, and build identifiers.

Standard library only. Imported by forge.py, validate_verdict.py, make_sxs.py and
make_workbench.py when they are run from this scripts/ directory.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path

FORGE_VERSION = "2.0.0"

DEFAULT_PATHS = {
    "brief": "BRIEF.md",
    "plan": "PLAN.md",
    "bar": "art/BAR.md",
    "bar_history": "art/bar-history",
    "look": "art/LOOK.md",
    "ledger": "art/LEDGER.md",
    "artifacts": "artifacts",
    "stills": "artifacts/stills",
    "frames": "artifacts/walkthrough-frames",
    "verdicts": "artifacts/verdicts",
    "history": "artifacts/history",
    "compare": "artifacts/compare",
    "diagnosis": "artifacts/diagnosis",
    "turnarounds": "artifacts/turnarounds",
    "log": "artifacts/rounds.log",
    "workbench": "artifacts/workbench.html",
}

IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".gif")

VERDICT_TYPES = (
    "WIN", "FAIL", "RECAPTURE", "GATE-PASS", "PLAN-OK", "PLAN-GAPS",
    "BAR-OK", "BAR-LOWERED", "AB", "BLOCKED",
)

# Canonical banned soft-pass phrases. references/critic-prompt.md must list every one
# of these; tests/test_consistency.py enforces that.
BANNED_PHRASES = (
    "fine for a browser build", "fine for webgl", "good for webgl", "fine for a prototype",
    "fine for a demo", "fine for a homage", "solid slice", "not photoreal, but", "not a aaa",
    "stylized take", "stylized low-poly is a valid choice", "close enough", "good enough",
    "mostly there", "almost there", "nearly there", "acceptable for now", "passable",
    "with reservations", "conditional win", "conditional pass", "soft win", "soft pass",
    "provisional pass", "pass with notes", "pass with caveats", "given time constraints",
    "given the time", "considering the stack", "impressive for three.js",
    "impressive for webgl", "for an ai", "big improvement over last round",
    "better than last round", "improved since",
)

IDENTIFIER_PATTERNS = (
    r"\banthropic\b", r"\bclaude\b", r"\bopenai\b", r"\bchatgpt\b", r"\bgpt-?\d",
    r"\bgemini\b", r"\bgrok\b", r"\bxai\b", r"\bllama\b", r"\bmistral\b",
    r"\bdeepseek\b", r"\bqwen\b", r"\bsonnet\b", r"\bopus\b", r"\bhaiku\b",
)

LOG_FIELD_ORDER = ("stage", "round", "role", "result", "build", "bar", "session")


class ForgeError(Exception):
    """A user-facing error whose message explains the fix. code 1 = protocol refusal, 2 = usage/file error."""

    def __init__(self, message: str, code: int = 2):
        super().__init__(message)
        self.code = code


def refuse(message: str) -> ForgeError:
    return ForgeError(message, code=1)


def now_iso() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def parse_time(value: str) -> dt.datetime | None:
    try:
        parsed = dt.datetime.fromisoformat(value.strip())
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed


def load_config(project: Path) -> dict:
    cfg: dict = {}
    cfg_path = project / "forge.json"
    if cfg_path.is_file():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ForgeError(f"{cfg_path} is not valid JSON ({exc}); fix or delete it.") from exc
    paths = dict(DEFAULT_PATHS)
    paths.update(cfg.get("paths") or {})
    cfg["paths"] = paths
    return cfg


def resolve(project: Path, cfg: dict, key: str) -> Path:
    return project / cfg["paths"][key]


def round_number(label: str) -> int | None:
    m = re.fullmatch(r"R0*(\d+)", label.strip(), flags=re.I)
    return int(m.group(1)) if m else None


def round_label(n: int) -> str:
    return f"R{n:02d}"


def slot_key(name: str) -> str | None:
    """Pairing key for a capture file: the last number in its stem, without leading zeros."""
    nums = re.findall(r"\d+", Path(name).stem)
    return str(int(nums[-1])) if nums else None


def list_images(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(
        (p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES and not p.name.startswith(".")),
        key=lambda p: (slot_key(p.name) is None, int(slot_key(p.name) or 0), p.name),
    )


# --- rounds.log ---------------------------------------------------------------

def clean_value(value: object) -> str:
    text = str(value).replace("\r", " ").replace("\n", " ").replace("|", "/").strip()
    return text or "n/a"


def format_event(time: str, fields: dict, extras: dict | None = None, note: str = "") -> str:
    parts = [time]
    for key in LOG_FIELD_ORDER:
        parts.append(f"{key}={clean_value(fields.get(key, 'n/a'))}")
    for key, value in (extras or {}).items():
        parts.append(f"{clean_value(key)}={clean_value(value)}")
    parts.append(f"note={clean_value(note) if note else ''}".rstrip())
    return " | ".join(parts)


def parse_log(text: str) -> list[dict]:
    """Event lines start with an ISO time; indented lines continue the previous event."""
    events: list[dict] = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw[0].isspace():
            if events:
                events[-1].setdefault("continuation", []).append(raw.strip())
            continue
        parts = raw.split(" | ")
        event: dict = {"time": parts[0].strip()}
        for i, part in enumerate(parts[1:], start=1):
            if part.startswith("note="):
                event["note"] = " | ".join(parts[i:])[5:].strip()
                break
            if "=" in part:
                key, value = part.split("=", 1)
                event[key.strip()] = value.strip()
        events.append(event)
    return events


def read_log(path: Path) -> list[dict]:
    return parse_log(path.read_text(encoding="utf-8")) if path.is_file() else []


# --- BAR.md ---------------------------------------------------------------------

BAR_VERSION_RE = re.compile(r"^BAR-VERSION:[ \t]*v(\d+)[ \t]*$", re.M)
BAR_HEADING_RE = re.compile(r"^#{2,3}[ \t]+(C\d+)\b[ \t.:\-\u2013\u2014]*(.*?)[ \t]*$", re.M)


def parse_bar(text: str) -> dict:
    m = BAR_VERSION_RE.search(text)
    heads = list(BAR_HEADING_RE.finditer(text))
    criteria = []
    for i, head in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        body = re.sub(r"<!--.*?-->", "", text[head.end():end], flags=re.S)
        body = re.split(r"^#{1,3}[ \t]+(?!C\d)", body, maxsplit=1, flags=re.M)[0]
        criteria.append({"id": head.group(1), "name": head.group(2).strip(), "body": body.strip()})
    return {"version": int(m.group(1)) if m else None, "criteria": criteria}


def bar_without_version(text: str) -> str:
    return BAR_VERSION_RE.sub("BAR-VERSION: v?", text).strip() + "\n"


def set_bar_version(text: str, version: int) -> str:
    line = f"BAR-VERSION: v{version}"
    if BAR_VERSION_RE.search(text):
        return BAR_VERSION_RE.sub(line, text, count=1)
    lines = text.splitlines()
    insert_at = 1 if lines and lines[0].startswith("#") else 0
    lines.insert(insert_at, line)
    return "\n".join(lines) + ("\n" if text.endswith("\n") or not text else "")


def text_sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


# --- verdicts -------------------------------------------------------------------

FENCE_RE = re.compile(r"^\s*```[\w-]*\s*$")
CRITERION_LINE_RE = re.compile(r"^\s*(?:[-*]\s+)?(C\d+)\b[ \t]*(.*?)[ \t]*:[ \t]*(PASS|FAIL)\b[ \t.:\-\u2014]*(.*)$")
NUMBERED_RE = re.compile(r"^\s*(\d+)[.)]\s+(.*)$")
PAIR_RE = re.compile(r"^\s*PAIR\s+(\S+?)\s*:\s*(A|B|SAME)\b[ \t.:\-\u2014]*(.*)$", re.I)
KEY_RE = re.compile(r"^([A-Z][A-Z ]*[A-Z]):[ \t]*(.*)$")
SECTION_KEYS = {"CRITERIA", "PUNCH LIST"}


def parse_verdict(text: str) -> dict:
    lines = [ln for ln in text.splitlines() if not FENCE_RE.match(ln)]
    start = next((i for i, ln in enumerate(lines) if ln.strip().upper().startswith("VERDICT:")), None)
    result: dict = {
        "type": None, "raw_type": None, "fields": {}, "criteria": [], "punch": [], "items": [],
        "pairs": [], "preamble": [], "text": "\n".join(lines),
    }
    if start is None:
        return result
    result["preamble"] = [ln for ln in lines[:start] if ln.strip()]
    raw_type = lines[start].split(":", 1)[1].strip()
    result["raw_type"] = raw_type
    token = raw_type.split()[0].upper() if raw_type else ""
    result["type"] = token if token in VERDICT_TYPES else None
    section = None
    for ln in lines[start + 1:]:
        if not ln.strip():
            continue
        key = KEY_RE.match(ln.strip())
        if key and key.group(1) in SECTION_KEYS:
            section = key.group(1)
            if key.group(2).strip():
                result["fields"][section] = key.group(2).strip()
            continue
        if key and section is None and not CRITERION_LINE_RE.match(ln):
            result["fields"][key.group(1)] = key.group(2).strip()
            continue
        pair = PAIR_RE.match(ln)
        if pair:
            result["pairs"].append({"id": pair.group(1), "pick": pair.group(2).upper(), "evidence": pair.group(3).strip()})
            continue
        if section == "CRITERIA":
            crit = CRITERION_LINE_RE.match(ln)
            if crit:
                result["criteria"].append({
                    "id": crit.group(1), "name": crit.group(2).strip(),
                    "result": crit.group(3), "evidence": crit.group(4).strip(),
                })
            elif result["criteria"]:
                result["criteria"][-1]["evidence"] += " " + ln.strip()
            continue
        numbered = NUMBERED_RE.match(ln)
        target = result["punch"] if section == "PUNCH LIST" else result["items"]
        if numbered:
            target.append({"n": int(numbered.group(1)), "text": numbered.group(2).strip()})
        elif target:
            target[-1]["text"] += " " + ln.strip()
    return result


# --- images ---------------------------------------------------------------------

def image_size(path: Path) -> tuple[int, int] | None:
    """(width, height) for PNG, JPEG, GIF and WebP files, or None if unrecognised."""
    try:
        with open(path, "rb") as fh:
            head = fh.read(32)
            if head.startswith(b"\x89PNG\r\n\x1a\n") and head[12:16] == b"IHDR":
                return struct.unpack(">II", head[16:24])
            if head[:6] in (b"GIF87a", b"GIF89a"):
                return struct.unpack("<HH", head[6:10])
            if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
                chunk = head[12:16]
                if chunk == b"VP8 ":
                    w, h = struct.unpack("<HH", head[26:30])
                    return w & 0x3FFF, h & 0x3FFF
                if chunk == b"VP8L":
                    bits = int.from_bytes(head[21:25], "little")
                    return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
                if chunk == b"VP8X":
                    return int.from_bytes(head[24:27], "little") + 1, int.from_bytes(head[27:30], "little") + 1
                return None
            if head[:2] == b"\xff\xd8":
                fh.seek(2)
                return _jpeg_size(fh)
    except OSError:
        return None
    return None


def _jpeg_size(fh) -> tuple[int, int] | None:
    sof = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
    while True:
        byte = fh.read(1)
        while byte and byte != b"\xff":
            byte = fh.read(1)
        while byte == b"\xff":
            byte = fh.read(1)
        if not byte:
            return None
        marker = byte[0]
        if marker == 0x01 or 0xD0 <= marker <= 0xD8:
            continue
        if marker == 0xD9:
            return None
        length_bytes = fh.read(2)
        if len(length_bytes) < 2:
            return None
        length = struct.unpack(">H", length_bytes)[0]
        if marker in sof:
            data = fh.read(5)
            if len(data) < 5:
                return None
            height, width = struct.unpack(">HH", data[1:5])
            return width, height
        fh.seek(length - 2, 1)


# --- build identity ---------------------------------------------------------------

HASH_SKIP_NAMES = {".git", "node_modules", "__pycache__", ".venv", "venv", ".DS_Store"}
HASH_MAX_FILE_BYTES = 64 * 1024 * 1024


def _git(project: Path, *args: str) -> str | None:
    try:
        out = subprocess.run(["git", *args], cwd=project, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def run_files(cfg: dict | None) -> set[str]:
    """Top-level paths that hold run state rather than the product, so they never change the build id."""
    paths = (cfg or {}).get("paths") or DEFAULT_PATHS
    skip = {"forge.json", Path(paths["artifacts"]).as_posix(), Path(paths["brief"]).as_posix(), Path(paths["plan"]).as_posix()}
    skip.add(Path(paths["bar"]).parent.as_posix() if Path(paths["bar"]).parent.as_posix() != "." else Path(paths["bar"]).as_posix())
    return {s for s in skip if s and s != "."}


def tree_hash(project: Path, skip_rel: set[str] | None = None) -> str:
    skip_rel = skip_rel or set()
    digest = hashlib.sha256()
    for path in sorted(project.rglob("*")):
        rel = path.relative_to(project)
        posix = rel.as_posix()
        if any(part in HASH_SKIP_NAMES for part in rel.parts) or not path.is_file():
            continue
        if any(posix == s or posix.startswith(s + "/") for s in skip_rel):
            continue
        digest.update(posix.encode("utf-8") + b"\0")
        size = path.stat().st_size
        if size > HASH_MAX_FILE_BYTES:
            digest.update(f"{size}:{path.stat().st_mtime_ns}".encode())
        else:
            digest.update(path.read_bytes())
    return digest.hexdigest()[:8]


def build_id(project: Path, cfg: dict | None = None) -> str:
    """Git short sha when the product tree is clean; sha+tree hash when dirty; tree-<hash> without git."""
    skip = run_files(cfg)
    sha = _git(project, "rev-parse", "--short", "HEAD")
    if sha:
        excludes = [f":(exclude){s}" for s in sorted(skip)]
        dirty = _git(project, "status", "--porcelain", "--", ".", *excludes)
        return sha if dirty == "" else f"{sha}+{tree_hash(project, skip)}"
    return f"tree-{tree_hash(project, skip)}"
