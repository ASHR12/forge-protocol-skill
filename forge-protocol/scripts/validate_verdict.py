#!/usr/bin/env python3
"""Validate a critic verdict before the orchestrator acts on it (standard library only).

Checks the schema for the verdict type; that it grades the current bar version and that BAR.md has not
changed since the round's CAPTURE; that every bar criterion is graded once with evidence; that every still
is cited and no missing still is cited; the punch-item shape; banned soft-pass phrases; numeric scores;
and model or vendor names.

  validate_verdict.py artifacts/verdicts/R03.md [--project .] [--scope loop] [--json]
  validate_verdict.py - --project . < verdict.md

Exit codes: 0 valid, 1 invalid, 2 usage or file error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import forgelib as fl  # noqa: E402

SCOPES = {
    "WIN": {"loop"}, "FAIL": {"loop", "gate"}, "RECAPTURE": {"loop", "gate"}, "GATE-PASS": {"gate"},
    "PLAN-OK": {"plan"}, "PLAN-GAPS": {"plan"}, "BAR-OK": {"bar"}, "BAR-LOWERED": {"bar"}, "AB": {"ab"},
    "BLOCKED": {"loop", "gate", "plan", "bar", "ab"},
}
CAPTURE_ID_RE = re.compile(r"\b((?:still|frame)-\d+)\b", re.I)
SCORE_PATTERNS = (
    (re.compile(r"\b\d+(?:\.\d+)?\s*/\s*(?:10|100)\b"), "x/10-style score"),
    (re.compile(r"\b\d+(?:\.\d+)?\s+out\s+of\s+(?:10|100)\b", re.I), "'out of 10' score"),
    (re.compile(r"\b(?:score|scored|scores|rating|rated|grade|graded)\b[^.\n]{0,20}?\d", re.I), "numeric score or rating"),
    (re.compile(r"\b(?:grade|rating|rated|graded)\b[^.\n]{0,12}?\b[A-F][+-]?(?=[\s.,;)]|$)", re.I), "letter grade"),
)
PERCENT_RE = re.compile(r"\b\d{1,3}(?:\.\d+)?\s*%")
PERCENT_SCORE_HINT = re.compile(r"(similar|match|quality|score|complete|done|confiden|accura|polish|fidelity|there)", re.I)
BAR_FIELD_RE = re.compile(r"^v(\d+)\s*\((\d+)\s+criteri(?:on|a)\)\s*$", re.I)


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


def stems(folder: Path) -> list[str]:
    return [p.stem for p in fl.list_images(folder)]


def manifest_rows(path: Path) -> list[list[str]]:
    rows = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and re.search(r"\.(png|jpe?g|webp|gif)$", cells[0], re.I):
            rows.append(cells)
    return rows


def check_language(text: str, rep: Report, allow_identifiers: bool) -> None:
    flat = " ".join(text.lower().split())
    for phrase in fl.BANNED_PHRASES:
        if phrase in flat:
            rep.error(f"banned soft-pass phrase: \"{phrase}\"")
    for pattern, label in SCORE_PATTERNS:
        for m in pattern.finditer(text):
            rep.error(f"{label}: \"{m.group(0).strip()}\" (grades are PASS or FAIL only)")
    for m in PERCENT_RE.finditer(text):
        window = text[max(0, m.start() - 30): m.end() + 30]
        if PERCENT_SCORE_HINT.search(window):
            rep.error(f"percentage used as a score: \"{window.strip()}\"")
        else:
            rep.warn(f"percentage in verdict (fine for measurements, not for quality): \"{m.group(0)}\"")
    if not allow_identifiers:
        for pattern in fl.IDENTIFIER_PATTERNS:
            m = re.search(pattern, text, re.I)
            if m:
                rep.error(f"model or vendor identifier in verdict: \"{m.group(0)}\"")


def check_bar_field(value: str | None, bar: dict, rep: Report) -> None:
    if not value:
        rep.error("missing BAR: line (expected 'BAR: v<N> (<count> criteria)')")
        return
    m = BAR_FIELD_RE.match(value.strip())
    if not m:
        rep.error(f"BAR line must read 'v<N> (<count> criteria)', got: {value}")
        return
    version, count = int(m.group(1)), int(m.group(2))
    if bar["version"] is not None and version != bar["version"]:
        rep.error(f"verdict grades bar v{version} but art/BAR.md is v{bar['version']}; re-run the critic on the current bar")
    if count != len(bar["criteria"]):
        rep.error(f"BAR line says {count} criteria but art/BAR.md has {len(bar['criteria'])}")


def check_round_against_log(verdict: dict, project: Path, cfg: dict, bar_text: str, rep: Report) -> None:
    events = fl.read_log(fl.resolve(project, cfg, "log"))
    if not events:
        return
    round_field = (verdict["fields"].get("ROUND") or "").strip()
    n = fl.round_number(round_field) if round_field else None
    captures = [ev for ev in events if ev.get("stage") == "loop" and ev.get("result") == "CAPTURE"]
    if n is not None:
        captures = [ev for ev in captures if fl.round_number(ev.get("round", "")) == n]
        if not captures:
            rep.error(f"rounds.log has no CAPTURE for {round_field}")
            return
    if not captures:
        return
    capture = captures[-1]
    sha = capture.get("barsha")
    if sha and sha != fl.text_sha(bar_text):
        rep.error(f"art/BAR.md changed after the {capture.get('round')} CAPTURE (bar edits are allowed only between rounds)")
    build = (verdict["fields"].get("BUILD") or "").strip()
    if build and capture.get("build") not in (None, "n/a") and build != capture.get("build"):
        rep.error(f"verdict BUILD {build} differs from the build captured for {capture.get('round')} ({capture.get('build')})")


def check_criteria(verdict: dict, bar: dict, rep: Report, require_all: bool, require_ids: bool) -> None:
    bar_ids = [c["id"] for c in bar["criteria"]]
    names = {c["id"]: c["name"] for c in bar["criteria"]}
    seen: dict[str, int] = {}
    if not verdict["criteria"]:
        rep.error("no CRITERIA lines (expected 'C1 <name>: PASS. <evidence>')")
        return
    for crit in verdict["criteria"]:
        cid = crit["id"]
        seen[cid] = seen.get(cid, 0) + 1
        if cid not in names:
            rep.error(f"{cid} is not in art/BAR.md")
            continue
        if crit["name"] and " ".join(crit["name"].lower().split()) != " ".join(names[cid].lower().split()):
            rep.warn(f"{cid} name '{crit['name']}' differs from art/BAR.md '{names[cid]}'")
        if len(crit["evidence"]) < 12:
            rep.error(f"{cid} has no real evidence; cite what the captures show")
        elif require_ids and not CAPTURE_ID_RE.search(crit["evidence"]):
            rep.error(f"{cid} evidence cites no still or frame id")
    for cid, count in seen.items():
        if count > 1:
            rep.error(f"{cid} graded {count} times")
    if require_all:
        missing = [cid for cid in bar_ids if cid not in seen]
        if missing:
            rep.error(f"criteria not graded: {', '.join(missing)}")


def check_captures(verdict: dict, project: Path, cfg: dict, rep: Report, strict_manifest: bool) -> None:
    text = verdict["text"]
    still_dir = fl.resolve(project, cfg, "stills")
    frame_dir = fl.resolve(project, cfg, "frames")
    still_stems = stems(still_dir)
    frame_stems = stems(frame_dir)
    if not still_stems:
        rep.error(f"no stills found in {still_dir}; a loop verdict needs captures")
    lowered = text.lower()
    for stem in still_stems:
        if not re.search(rf"(?<![\w-]){re.escape(stem.lower())}(?![\w-])", lowered):
            rep.error(f"still not cited: {stem}")
    known = {s.lower() for s in still_stems + frame_stems}
    for m in CAPTURE_ID_RE.finditer(text):
        if m.group(1).lower() not in known:
            rep.error(f"cites {m.group(1)}, which does not exist")
    if frame_stems and not any(re.search(rf"\b{re.escape(s.lower())}\b", lowered) for s in frame_stems):
        rep.error("walkthrough frames exist but none are cited")
    rows = manifest_rows(still_dir / "MANIFEST.md")
    say = rep.error if strict_manifest else rep.warn
    if not rows:
        say("artifacts/stills/MANIFEST.md missing or empty (capture set under spec; expected RECAPTURE)")
        return
    listed = {Path(r[0]).stem for r in rows}
    unlisted = [s for s in still_stems if s not in listed]
    if unlisted:
        say(f"stills missing from MANIFEST.md: {', '.join(unlisted)}")
    builds = {r[1] for r in rows if len(r) > 1}
    if len(builds) > 1:
        say(f"MANIFEST.md mixes builds {sorted(builds)} (partial re-capture)")
    build = (verdict["fields"].get("BUILD") or "").strip()
    if build and builds and build not in builds:
        rep.error(f"verdict BUILD {build} is not the build in MANIFEST.md ({', '.join(sorted(builds))})")


def check_punch(verdict: dict, rep: Report, require_ids: bool) -> None:
    failing = {c["id"] for c in verdict["criteria"] if c["result"] == "FAIL"}
    passing = {c["id"] for c in verdict["criteria"] if c["result"] == "PASS"}
    if not verdict["punch"]:
        rep.error("FAIL verdict without a PUNCH LIST")
        return
    covered = set()
    for item in verdict["punch"]:
        m = re.match(r"\[(C\d+)\b[^\]]*\]", item["text"])
        if not m:
            rep.error(f"punch item {item['n']} must start with '[C<id> <name>]'")
            continue
        cid = m.group(1)
        covered.add(cid)
        if cid in passing:
            rep.warn(f"punch item {item['n']} targets {cid}, which PASSed")
        elif cid not in failing:
            rep.error(f"punch item {item['n']} targets {cid}, which was not graded")
        if require_ids and not CAPTURE_ID_RE.search(item["text"]):
            rep.error(f"punch item {item['n']} names no still or frame")
        if not re.search(r"\bdone when\b", item["text"], re.I):
            rep.error(f"punch item {item['n']} has no 'Done when <observable condition>'")
    for cid in sorted(failing - covered):
        rep.error(f"{cid} FAILs but has no punch item")


def validate(text: str, project: Path, scope: str | None = None, allow_identifiers: bool | None = None) -> dict:
    rep = Report()
    cfg = fl.load_config(project)
    if allow_identifiers is None:
        allow_identifiers = str(cfg.get("identifiers", "")).lower() == "allowed"
    verdict = fl.parse_verdict(text)
    vtype = verdict["type"]
    if verdict["raw_type"] is None:
        rep.error("no 'VERDICT: <TYPE>' line")
        return finish(rep, None)
    if vtype is None:
        rep.error(f"unknown verdict type '{verdict['raw_type']}' (allowed: {', '.join(fl.VERDICT_TYPES)})")
        return finish(rep, None)
    if verdict["preamble"]:
        rep.warn("text before the VERDICT line; the critic should output only the verdict block")
    fields = verdict["fields"]
    vscope = (fields.get("SCOPE") or "").strip().lower()
    if vtype != "BLOCKED" or vscope:
        if not vscope:
            rep.error("missing SCOPE: line")
        elif vscope not in SCOPES[vtype]:
            rep.error(f"{vtype} is not valid for SCOPE {vscope} (allowed: {', '.join(sorted(SCOPES[vtype]))})")
    if scope and vscope and vscope != scope:
        rep.error(f"expected SCOPE {scope}, got {vscope}")
    check_language(text, rep, allow_identifiers)

    bar_path = fl.resolve(project, cfg, "bar")
    bar_text = bar_path.read_text(encoding="utf-8") if bar_path.is_file() else ""
    bar = fl.parse_bar(bar_text)
    needs_bar = vtype in ("WIN", "FAIL", "GATE-PASS", "PLAN-OK", "PLAN-GAPS", "BAR-OK", "BAR-LOWERED")
    if needs_bar and not bar["criteria"]:
        rep.error(f"cannot validate against the bar: {bar_path} missing or has no criteria")
        return finish(rep, vtype)
    if needs_bar:
        check_bar_field(fields.get("BAR"), bar, rep)

    if vtype == "BLOCKED":
        if not (fields.get("REASON") or "").strip():
            rep.error("BLOCKED needs a REASON: line")
    elif vtype in ("WIN", "FAIL") and vscope == "loop":
        for key in ("ROUND", "BUILD"):
            if not (fields.get(key) or "").strip():
                rep.error(f"missing {key}: line")
        if fields.get("ROUND") and fl.round_number(fields["ROUND"]) is None:
            rep.error(f"ROUND must look like R3 or R03, got {fields['ROUND']}")
        check_criteria(verdict, bar, rep, require_all=True, require_ids=True)
        check_captures(verdict, project, cfg, rep, strict_manifest=(vtype == "WIN"))
        check_round_against_log(verdict, project, cfg, bar_text, rep)
        if vtype == "WIN":
            failing = [c["id"] for c in verdict["criteria"] if c["result"] != "PASS"]
            if failing:
                rep.error(f"WIN with non-PASS criteria: {', '.join(failing)}")
            if verdict["punch"]:
                rep.error("WIN must not carry a PUNCH LIST")
        else:
            if not any(c["result"] == "FAIL" for c in verdict["criteria"]):
                rep.error("FAIL verdict where every criterion PASSes; that is a WIN or an invalid verdict")
            check_punch(verdict, rep, require_ids=True)
    elif vtype in ("FAIL", "GATE-PASS") and vscope == "gate":
        for key in ("COMPONENT", "BUILD"):
            if not (fields.get(key) or "").strip():
                rep.error(f"missing {key}: line")
        check_criteria(verdict, bar, rep, require_all=False, require_ids=False)
        if vtype == "GATE-PASS":
            failing = [c["id"] for c in verdict["criteria"] if c["result"] != "PASS"]
            if failing:
                rep.error(f"GATE-PASS with non-PASS criteria: {', '.join(failing)}")
        else:
            check_punch(verdict, rep, require_ids=False)
    elif vtype == "RECAPTURE":
        if not verdict["items"]:
            rep.error("RECAPTURE needs a numbered list of capture defects")
    elif vtype in ("PLAN-GAPS", "BAR-LOWERED"):
        if not verdict["items"]:
            rep.error(f"{vtype} needs a numbered list")
        if vtype == "BAR-LOWERED":
            for item in verdict["items"]:
                if not re.search(r"\bC\d+\b", item["text"]):
                    rep.error(f"BAR-LOWERED item {item['n']} must name the criterion it loosens")
    elif vtype == "AB":
        if not verdict["pairs"]:
            rep.error("AB needs 'PAIR <id>: A|B|SAME. <evidence>' lines")
        for pair in verdict["pairs"]:
            if len(pair["evidence"]) < 12:
                rep.error(f"PAIR {pair['id']} needs evidence")
        overall = (fields.get("OVERALL") or "").strip().upper()
        if overall.split(".")[0] not in ("A", "B", "SAME"):
            rep.error("AB needs 'OVERALL: A|B|SAME'")
        if re.search(r"\bR\d+\b", text):
            rep.warn("AB verdict mentions a round label; the pairing may not have been blind")
    return finish(rep, vtype)


def finish(rep: Report, vtype: str | None) -> dict:
    return {"valid": not rep.errors, "type": vtype, "errors": rep.errors, "warnings": rep.warnings}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=__doc__.split("\n\n", 1)[1])
    parser.add_argument("verdict", help="verdict file, or - for stdin")
    parser.add_argument("--project", default=".", help="project root (default: current directory)")
    parser.add_argument("--scope", choices=["loop", "gate", "plan", "bar", "ab"], help="expected scope")
    parser.add_argument("--allow-identifiers", action="store_true", help="skip the model/vendor name check")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)
    try:
        text = sys.stdin.read() if args.verdict == "-" else Path(args.verdict).read_text(encoding="utf-8")
        project = Path(args.project).expanduser().resolve()
        result = validate(text, project, args.scope, True if args.allow_identifiers else None)
    except (OSError, fl.ForgeError) as exc:
        print(f"validate_verdict.py: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(("VALID" if result["valid"] else "INVALID") + (f" ({result['type']})" if result["type"] else ""))
        for msg in result["errors"]:
            print(f"  error: {msg}")
        for msg in result["warnings"]:
            print(f"  warning: {msg}")
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
