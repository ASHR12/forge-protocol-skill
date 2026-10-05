#!/usr/bin/env python3
"""Run-state helper for forge-protocol projects (standard library only).

  init      scaffold BRIEF.md, art/BAR.md, ... for a mode: sprint | standard | forge
  log       append one event line to artifacts/rounds.log
  bar       publish the next bar version (reason + diff logged) or show the pending diff
  snapshot  copy the current stills into artifacts/history/<round>/
  manifest  write artifacts/stills/MANIFEST.md for stills captured by other tools
  status    budgets, streaks, pending bar audits and the recommended next action
  build-id  print an identifier for the current build (git sha, or a tree hash)

Run from anywhere; --project points at the project root (default: current directory).
Exit codes: 0 ok, 1 refused by a protocol rule, 2 usage or file error.
"""
from __future__ import annotations

import argparse
import datetime
import difflib
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import forgelib as fl  # noqa: E402

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL_DIR / "templates"

MODES = {
    "sprint": {"rounds": 3, "minutes": 30, "check_in_rounds": 0, "check_in_minutes": 0, "stuck_after": 2},
    "standard": {"rounds": 8, "minutes": 120, "check_in_rounds": 3, "check_in_minutes": 45, "stuck_after": 3},
    "forge": {"rounds": 25, "minutes": 480, "check_in_rounds": 5, "check_in_minutes": 90, "stuck_after": 3},
}
DOCS = {
    "sprint": ["brief", "bar"],
    "standard": ["brief", "plan", "bar", "look"],
    "forge": ["brief", "plan", "bar", "look", "ledger"],
}
TEMPLATE_FOR = {"brief": "BRIEF.md", "plan": "PLAN.md", "bar": "BAR.md", "look": "LOOK.md", "ledger": "LEDGER.md"}
DIRS = {
    "sprint": ["stills", "verdicts", "history"],
    "standard": ["stills", "verdicts", "history", "frames", "compare", "diagnosis"],
    "forge": ["stills", "verdicts", "history", "frames", "compare", "diagnosis", "turnarounds"],
}
RESULTS = (
    "INIT", "PLAN", "APPROVED", "TOOLS", "BUILD", "GATE-PASS", "GATE-FAIL", "CAPTURE", "RECAPTURE",
    "FAIL", "WIN", "WIN-VOIDED", "BLOCKED", "DIAGNOSE-HOLD", "DIAGNOSE-STEER", "ESCALATE", "SMOOTHING",
    "BAR-PUBLISH", "BAR-OK", "BAR-LOWERED", "CHECK-IN", "BUDGET-EXHAUSTED",
    "BUDGET-EXTENDED", "PUBLISH-UNLOCK", "STOP", "HANDOFF", "NOTE",
)
STAGES = ("plan", "setup", "build", "gate", "loop", "handoff")
ROLES = ("orchestrator", "builder", "critic", "diagnoser", "user")
ROUND_CLOSERS = ("FAIL", "WIN", "RECAPTURE", "BLOCKED")
LOOP_RESULTS = ("CAPTURE", "RECAPTURE", "FAIL", "WIN", "WIN-VOIDED")
DEFAULT_STAGE = {"PLAN": "plan", "APPROVED": "plan", "TOOLS": "plan", "INIT": "setup", "BUILD": "build",
                 "GATE-PASS": "gate", "GATE-FAIL": "gate", "HANDOFF": "handoff"}
BAR_TYPES = ("initial", "add", "raise", "clarify", "loosen", "retire")
DIFF_LINE_CAP = 200
RELATIVE_RE = re.compile(r"\b(references?|refs?|inspiration|screenshots? of|looks? like the)\b", re.I)


def project_and_config(args) -> tuple[Path, dict]:
    project = Path(args.project).expanduser().resolve()
    if not project.is_dir():
        raise fl.ForgeError(f"project directory not found: {project}")
    return project, fl.load_config(project)


def append_event(log_path: Path, fields: dict, extras: dict | None = None, note: str = "",
                 continuation: list[str] | None = None) -> str:
    line = fl.format_event(fl.now_iso(), fields, extras, note)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
        for extra_line in continuation or []:
            fh.write("    | " + extra_line.rstrip("\n") + "\n")
    return line


# --- init -------------------------------------------------------------------------

def render_template(name: str, values: dict) -> str:
    path = TEMPLATES / name
    if not path.is_file():
        raise fl.ForgeError(f"template missing: {path}")
    text = path.read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", str(value))
    return text


def cmd_init(args) -> int:
    project = Path(args.project).expanduser().resolve()
    project.mkdir(parents=True, exist_ok=True)
    cfg_path = project / "forge.json"
    if cfg_path.exists() and not args.force:
        raise fl.refuse(f"{cfg_path} already exists; this project is initialised (use --force to rewrite templates).")
    budgets = dict(MODES[args.mode])
    for key in ("rounds", "minutes", "check_in_rounds", "check_in_minutes", "stuck_after"):
        value = getattr(args, key)
        if value is not None:
            if value < 0:
                raise fl.ForgeError(f"--{key.replace('_', '-')} must be >= 0")
            budgets[key] = value
    cfg = {
        "forge_version": fl.FORGE_VERSION,
        "title": args.title,
        "mode": args.mode,
        "packs": args.pack or [],
        "stack": args.stack,
        "budgets": budgets,
        "paths": dict(fl.DEFAULT_PATHS),
        "created": fl.now_iso(),
    }
    values = {
        "TITLE": args.title, "GOAL": args.goal or "<one sentence: what the user wants to exist and why>",
        "MODE": args.mode, "DATE": cfg["created"][:10],
        "ROUNDS": budgets["rounds"] or "no limit", "MINUTES": budgets["minutes"] or "no limit",
        "CHECKIN": describe_check_in(budgets), "STUCK": budgets["stuck_after"],
        "PACKS": ", ".join(cfg["packs"]) or "decide from the goal", "STACK": args.stack,
    }
    written, kept = [], []
    for key in DOCS[args.mode]:
        target = fl.resolve(project, cfg, key)
        if target.exists() and not args.force:
            kept.append(target)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_template(TEMPLATE_FOR[key], values), encoding="utf-8")
        written.append(target)
    dirs = list(DIRS[args.mode])
    if "3d" in cfg["packs"] and "turnarounds" not in dirs:
        dirs.append("turnarounds")
    for key in dirs:
        fl.resolve(project, cfg, key).mkdir(parents=True, exist_ok=True)
    if args.stack in ("web", "blender-web"):
        capture = project / "tools" / "capture.mjs"
        if not capture.exists() or args.force:
            capture.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(TEMPLATES / "capture.mjs", capture)
            written.append(capture)
        else:
            kept.append(capture)
    cfg_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    log_path = fl.resolve(project, cfg, "log")
    append_event(log_path, {"stage": "setup", "role": "orchestrator", "result": "INIT"},
                 {"mode": args.mode}, note=f"forge-protocol {fl.FORGE_VERSION}: {args.title}")
    print(f"Initialised {args.mode} project in {project}")
    for path in written:
        print(f"  wrote {path.relative_to(project)}")
    for path in kept:
        print(f"  kept  {path.relative_to(project)} (exists)")
    print(f"  budgets: {json.dumps(budgets)}")
    print("Next: fill BRIEF.md and art/BAR.md, then run: forge.py bar publish --reason \"initial bar\"")
    return 0


def describe_check_in(budgets: dict) -> str:
    parts = []
    if budgets["check_in_rounds"]:
        parts.append(f"every {budgets['check_in_rounds']} rounds")
    if budgets["check_in_minutes"]:
        parts.append(f"every {budgets['check_in_minutes']} minutes")
    return " or ".join(parts) if parts else "at the end or when a budget runs out"


# --- state ------------------------------------------------------------------------

def published_versions(history: Path) -> dict[int, Path]:
    found = {}
    if history.is_dir():
        for path in history.glob("BAR-v*.md"):
            num = path.stem[len("BAR-v"):]
            if num.isdigit():
                found[int(num)] = path
    return found


def open_round(events: list[dict]) -> str | None:
    state: str | None = None
    for ev in events:
        result = ev.get("result")
        if ev.get("stage") == "loop" and result == "CAPTURE":
            state = ev.get("round")
        elif ev.get("stage") == "loop" and result in ROUND_CLOSERS and ev.get("round") == state:
            state = None
    return state


def pending_audit(events: list[dict]) -> str | None:
    """'pending' while a published bar revision awaits a BAR-OK, 'lowered' after BAR-LOWERED."""
    state = None
    for ev in events:
        result = ev.get("result")
        if result == "BAR-PUBLISH":
            state = "pending" if ev.get("audit") == "pending" else None
        elif result == "BAR-OK":
            state = None
        elif result == "BAR-LOWERED":
            state = "lowered"
    return state


def latest_loop_verdict(project: Path, cfg: dict) -> dict | None:
    rounds = load_round_verdicts(project, cfg)
    return rounds[-1] if rounds else None


def load_round_verdicts(project: Path, cfg: dict) -> list[dict]:
    folder = fl.resolve(project, cfg, "verdicts")
    out = []
    if folder.is_dir():
        for path in folder.glob("R*.md"):
            n = fl.round_number(path.stem)
            if n is None:
                continue
            parsed = fl.parse_verdict(path.read_text(encoding="utf-8"))
            if parsed["type"] in ("WIN", "FAIL"):
                out.append({"round": n, "path": path, **parsed})
    return sorted(out, key=lambda v: v["round"])


def closed_rounds(events: list[dict]) -> list[str]:
    seen: list[str] = []
    for ev in events:
        if ev.get("stage") == "loop" and ev.get("result") in ("FAIL", "WIN") and ev.get("round") not in seen:
            seen.append(ev.get("round"))
    return seen


def next_round_label(events: list[dict]) -> str:
    numbers = [fl.round_number(r) or 0 for r in closed_rounds(events)]
    current = open_round(events)
    if current:
        return current
    last_capture = [ev.get("round") for ev in events if ev.get("stage") == "loop" and ev.get("result") == "CAPTURE"]
    if last_capture:
        last = last_capture[-1]
        recaptured = any(ev.get("result") == "RECAPTURE" and ev.get("round") == last for ev in events)
        if recaptured and last not in closed_rounds(events):
            return last
    return fl.round_label((max(numbers) if numbers else 0) + 1)


# --- log --------------------------------------------------------------------------

def parse_fields(pairs: list[str]) -> dict:
    extras = {}
    for pair in pairs or []:
        if "=" not in pair:
            raise fl.ForgeError(f"--field expects key=value, got: {pair}")
        key, value = pair.split("=", 1)
        if key in fl.LOG_FIELD_ORDER or key == "note":
            raise fl.ForgeError(f"--field cannot set reserved key '{key}'; use its own flag")
        extras[key.strip()] = value.strip()
    return extras


def cmd_log(args) -> int:
    project, cfg = project_and_config(args)
    log_path = fl.resolve(project, cfg, "log")
    events = fl.read_log(log_path)
    result = args.result.upper()
    if result not in RESULTS:
        raise fl.ForgeError(f"unknown result '{args.result}'. Use one of: {', '.join(RESULTS)}")
    has_loop = any(ev.get("stage") == "loop" for ev in events)
    stage = args.stage or ("loop" if result in LOOP_RESULTS else DEFAULT_STAGE.get(result, "loop" if has_loop else "build"))
    extras = parse_fields(args.field)
    round_label = args.round
    if round_label and fl.round_number(round_label) is not None:
        round_label = fl.round_label(fl.round_number(round_label))
    bar_label = "n/a"
    bar_path = fl.resolve(project, cfg, "bar")
    versions = published_versions(fl.resolve(project, cfg, "bar_history"))
    if versions:
        bar_label = f"v{max(versions)}"
    current = open_round(events)
    if result == "CAPTURE" and stage == "loop":
        if not versions:
            raise fl.refuse("no published bar yet; run: forge.py bar publish --reason \"initial bar\"")
        if current:
            raise fl.refuse(f"round {current} is still open (CAPTURE without a verdict); log its verdict or RECAPTURE first")
        working = bar_path.read_text(encoding="utf-8") if bar_path.is_file() else ""
        published = versions[max(versions)].read_text(encoding="utf-8")
        if fl.bar_without_version(working) != fl.bar_without_version(published):
            raise fl.refuse("art/BAR.md has unpublished edits; publish them between rounds with: forge.py bar publish --type ... --reason ...")
        audit = pending_audit(events)
        if audit == "pending":
            raise fl.refuse("bar revision awaits audit: run a fresh critic with SCOPE: bar, then log BAR-OK (or revert the revision)")
        if audit == "lowered":
            raise fl.refuse("the last bar revision was judged BAR-LOWERED; revert it and publish again, or get explicit user approval and publish with --type loosen --user-approved")
        round_label = round_label or next_round_label(events)
        extras["barsha"] = fl.text_sha(working)
    elif result in ROUND_CLOSERS and stage == "loop":
        if not current:
            raise fl.refuse(f"no open round: log CAPTURE before recording {result}")
        if round_label and round_label != current:
            raise fl.refuse(f"open round is {current}, not {round_label}")
        round_label = current
    elif result == "WIN-VOIDED":
        wins = [ev.get("round") for ev in events if ev.get("stage") == "loop" and ev.get("result") == "WIN"]
        if not wins:
            raise fl.refuse("WIN-VOIDED needs an earlier WIN")
        round_label = round_label or wins[-1]
    build = args.build or (fl.build_id(project, cfg) if result == "CAPTURE" else "n/a")
    fields = {
        "stage": stage, "round": round_label or "n/a", "role": args.role, "result": result,
        "build": build, "bar": bar_label, "session": args.session or "n/a",
    }
    line = append_event(log_path, fields, extras, note=args.note or "")
    print(line)
    return 0


# --- bar --------------------------------------------------------------------------

def bar_changes(old: dict, new: dict) -> tuple[list[str], list[str], list[str]]:
    old_map = {c["id"]: c for c in old["criteria"]}
    new_map = {c["id"]: c for c in new["criteria"]}
    added = [cid for cid in new_map if cid not in old_map]
    removed = [cid for cid in old_map if cid not in new_map]
    norm = lambda c: " ".join((c["name"] + " " + c["body"]).split())  # noqa: E731
    changed = [cid for cid in new_map if cid in old_map and norm(new_map[cid]) != norm(old_map[cid])]
    return added, removed, changed


def cmd_bar(args) -> int:
    project, cfg = project_and_config(args)
    bar_path = fl.resolve(project, cfg, "bar")
    history = fl.resolve(project, cfg, "bar_history")
    log_path = fl.resolve(project, cfg, "log")
    if not bar_path.is_file():
        raise fl.ForgeError(f"bar file not found: {bar_path}")
    working_text = bar_path.read_text(encoding="utf-8")
    working = fl.parse_bar(working_text)
    versions = published_versions(history)
    latest = max(versions) if versions else 0
    previous_text = versions[latest].read_text(encoding="utf-8") if latest else ""

    if args.bar_cmd == "diff":
        diff = unified(previous_text, working_text, latest)
        print("\n".join(diff) if diff else "No unpublished changes.")
        return 0

    events = fl.read_log(log_path)
    current = open_round(events)
    if current:
        raise fl.refuse(f"round {current} is open; bar revisions apply only between rounds (after the verdict is logged)")
    if not working["criteria"]:
        raise fl.ForgeError(f"{bar_path} has no criteria (expected headings like '## C1 Goal fit')")
    ids = [c["id"] for c in working["criteria"]]
    duplicates = sorted({cid for cid in ids if ids.count(cid) > 1})
    if duplicates:
        raise fl.ForgeError(f"duplicate criterion ids in {bar_path.name}: {', '.join(duplicates)}")
    unfilled = [c["id"] for c in working["criteria"]
                if "<" in c["name"] or not c["name"] or re.search(r"PASS when:\s*(<|\.\.\.|$)", c["body"], re.M)
                or "PASS when:" not in c["body"]]
    if unfilled:
        raise fl.ForgeError(f"fill in or delete placeholder criteria before publishing: {', '.join(unfilled)} "
                            "(each needs a name and a 'PASS when:' line)")
    relative = [c["id"] for c in working["criteria"] if RELATIVE_RE.search(c["name"] + " " + c["body"])]
    if relative:
        raise fl.refuse(f"criteria {', '.join(relative)} are phrased against an image; state the observable quality itself "
                        "(e.g. 'shadows darken where objects meet the ground'), not a comparison to a picture")

    kind = (args.type or ("initial" if not latest else "")).lower()
    audit = "none"
    if latest:
        if fl.bar_without_version(previous_text) == fl.bar_without_version(working_text):
            print(f"No changes since v{latest}; nothing to publish.")
            return 0
        if kind not in BAR_TYPES or kind == "initial":
            raise fl.ForgeError("--type is required for revisions: add | raise | clarify | loosen | retire")
        added, removed, changed = bar_changes(fl.parse_bar(previous_text), working)
        if kind == "add" and (removed or changed):
            raise fl.refuse(f"--type add allows new criteria only; edited {changed or '-'}, removed {removed or '-'}. Use raise/clarify, or loosen/retire with user approval.")
        if kind in ("add", "raise", "clarify") and removed:
            raise fl.refuse(f"removing criteria ({', '.join(removed)}) lowers the bar; it needs --type retire --user-approved \"<user's words>\"")
        if kind in ("loosen", "retire") and not (args.user_approved or "").strip():
            raise fl.refuse("loosening or retiring criteria requires --user-approved \"<the user's approval, verbatim>\"")
        last = latest_loop_verdict(project, cfg)
        failing = {c["id"] for c in (last or {}).get("criteria", []) if c["result"] == "FAIL"}
        if kind in ("raise", "clarify") and failing & set(changed):
            audit = "pending"
    elif kind != "initial":
        raise fl.ForgeError("the first publish is the initial bar; omit --type or use --type initial")
    if not (args.reason or "").strip():
        raise fl.ForgeError("--reason is required: say why the bar changes")

    new_version = latest + 1
    new_text = fl.set_bar_version(working_text, new_version)
    bar_path.write_text(new_text, encoding="utf-8")
    history.mkdir(parents=True, exist_ok=True)
    (history / f"BAR-v{new_version}.md").write_text(new_text, encoding="utf-8")
    diff = unified(previous_text, new_text, latest)
    if len(diff) > DIFF_LINE_CAP:
        diff = diff[:DIFF_LINE_CAP] + [f"... diff truncated; full text in {history.name}/BAR-v{new_version}.md"]
    extras = {"type": kind, "audit": audit, "criteria": len(working["criteria"]), "barsha": fl.text_sha(new_text)}
    if args.user_approved:
        extras["approved"] = args.user_approved
    stage = "loop" if any(ev.get("stage") == "loop" for ev in events) else "setup"
    fields = {"stage": stage, "round": "n/a", "role": "orchestrator",
              "result": "BAR-PUBLISH", "build": "n/a", "bar": f"v{new_version}", "session": "n/a"}
    append_event(log_path, fields, extras, note=args.reason, continuation=diff)
    print(f"Published bar v{new_version} ({len(working['criteria'])} criteria, type {kind}).")
    if audit == "pending":
        print("Edited criteria that failed last round: run a fresh critic with SCOPE: bar and log BAR-OK before the next CAPTURE.")
    return 0


def unified(old: str, new: str, old_version: int) -> list[str]:
    return list(difflib.unified_diff(
        old.splitlines(), new.splitlines(),
        fromfile=f"BAR-v{old_version}" if old_version else "(none)", tofile="BAR (new)", lineterm="", n=1,
    ))


# --- snapshot / manifest ------------------------------------------------------------

def cmd_snapshot(args) -> int:
    project, cfg = project_and_config(args)
    n = fl.round_number(args.round)
    if n is None:
        raise fl.ForgeError(f"round must look like R3 or R03, got: {args.round}")
    source = Path(args.source).expanduser() if args.source else fl.resolve(project, cfg, "stills")
    images = fl.list_images(source)
    if not images:
        raise fl.ForgeError(f"no images to snapshot in {source}")
    target = fl.resolve(project, cfg, "history") / fl.round_label(n)
    if target.exists() and any(target.iterdir()) and not args.force:
        raise fl.ForgeError(f"{target} already has files (use --force to replace)")
    if target.exists() and args.force:
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    for path in images:
        shutil.copy2(path, target / path.name)
    manifest = source / "MANIFEST.md"
    if manifest.is_file():
        shutil.copy2(manifest, target / "MANIFEST.md")
    print(f"Snapshot {fl.round_label(n)}: {len(images)} images -> {target}")
    return 0


def cmd_manifest(args) -> int:
    project, cfg = project_and_config(args)
    stills = Path(args.stills).expanduser() if args.stills else fl.resolve(project, cfg, "stills")
    images = fl.list_images(stills)
    if not images:
        raise fl.ForgeError(f"no stills found in {stills}")
    build = args.build or fl.build_id(project, cfg)
    views = dict(item.split("=", 1) for item in args.view or [] if "=" in item)
    rows = ["# Capture manifest", "", f"Generated by forge.py manifest at {fl.now_iso()}.", "",
            "| still | build | size | view | captured |", "| --- | --- | --- | --- | --- |"]
    for path in images:
        size = fl.image_size(path)
        size_text = f"{size[0]}x{size[1]}" if size else "unknown"
        captured = datetime.datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(timespec="seconds")
        rows.append(f"| {path.name} | {build} | {size_text} | {views.get(path.stem, views.get(path.name, '-'))} | {captured} |")
    (stills / "MANIFEST.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"Wrote {stills / 'MANIFEST.md'} ({len(images)} stills, build {build})")
    return 0


# --- status -----------------------------------------------------------------------

def criterion_streaks(verdicts: list[dict], reset_after_round: int) -> dict[str, int]:
    streaks: dict[str, int] = {}
    for verdict in verdicts:
        if verdict["round"] <= reset_after_round:
            continue
        results = {c["id"]: c["result"] for c in verdict["criteria"]}
        for cid in set(streaks) | set(results):
            streaks[cid] = streaks.get(cid, 0) + 1 if results.get(cid) == "FAIL" else 0
    return {cid: n for cid, n in streaks.items() if n}


def compute_status(project: Path, cfg: dict) -> dict:
    events = fl.read_log(fl.resolve(project, cfg, "log"))
    budgets = dict(MODES.get(cfg.get("mode", "standard"), MODES["standard"]))
    budgets.update(cfg.get("budgets") or {})
    for ev in events:
        if ev.get("result") == "BUDGET-EXTENDED":
            for key in ("rounds", "minutes"):
                try:
                    budgets[key] += int(ev.get(key, "0").lstrip("+") or 0)
                except ValueError:
                    pass
    start_ev = next((ev for ev in events if ev.get("result") == "APPROVED"), None) or (events[0] if events else None)
    start = fl.parse_time(start_ev["time"]) if start_ev else None
    now = fl.parse_time(fl.now_iso())
    elapsed = int((now - start).total_seconds() // 60) if start and now else 0
    rounds_done = closed_rounds(events)
    verdicts = load_round_verdicts(project, cfg)
    steer_rounds = [fl.round_number(ev.get("round", "")) or 0 for ev in events if ev.get("result") == "DIAGNOSE-STEER"]
    streaks = criterion_streaks(verdicts, max(steer_rounds) if steer_rounds else 0)
    stuck_after = budgets.get("stuck_after", 3)
    stuck = sorted(cid for cid, n in streaks.items() if n >= stuck_after)
    last_capture = next((ev for ev in reversed(events) if ev.get("result") == "CAPTURE"), None)
    recapture_streak = 0
    if last_capture:
        for ev in reversed(events):
            if ev.get("round") != last_capture.get("round"):
                continue
            if ev.get("result") == "RECAPTURE":
                recapture_streak += 1
            elif ev.get("result") in ("FAIL", "WIN"):
                break
    check_ins = [ev for ev in events if ev.get("result") == "CHECK-IN"]
    last_check = check_ins[-1] if check_ins else start_ev
    rounds_since_check = len([r for r in rounds_done if not last_check or round_after(events, r, last_check)])
    minutes_since_check = int((now - fl.parse_time(last_check["time"])).total_seconds() // 60) if last_check and now else 0
    check_due = bool(
        (budgets["check_in_rounds"] and rounds_since_check >= budgets["check_in_rounds"])
        or (budgets["check_in_minutes"] and minutes_since_check >= budgets["check_in_minutes"])
    )
    exhausted = bool(
        (budgets["rounds"] and len(rounds_done) >= budgets["rounds"])
        or (budgets["minutes"] and elapsed >= budgets["minutes"])
    )
    versions = published_versions(fl.resolve(project, cfg, "bar_history"))
    bar_path = fl.resolve(project, cfg, "bar")
    unpublished = False
    if versions and bar_path.is_file():
        unpublished = fl.bar_without_version(bar_path.read_text(encoding="utf-8")) != fl.bar_without_version(
            versions[max(versions)].read_text(encoding="utf-8"))
    last_verdict = verdicts[-1] if verdicts else None
    capture_builds = [ev.get("build") for ev in events if ev.get("stage") == "loop" and ev.get("result") == "CAPTURE"]
    capture_rounds = [ev.get("round") for ev in events if ev.get("stage") == "loop" and ev.get("result") == "CAPTURE"]
    build_unchanged = (len(capture_builds) >= 2 and capture_builds[-1] == capture_builds[-2]
                       and capture_rounds[-1] != capture_rounds[-2] and capture_builds[-1] not in (None, "n/a"))
    terminal = next((ev.get("result") for ev in reversed(events) if ev.get("result") in ("HANDOFF", "STOP")), None)
    voided_after_win = bool(last_verdict and last_verdict["type"] == "WIN" and any(
        ev.get("result") == "WIN-VOIDED" and fl.round_number(ev.get("round", "")) == last_verdict["round"] for ev in events))
    status = {
        "title": cfg.get("title"), "mode": cfg.get("mode"), "budgets": budgets,
        "rounds_used": len(rounds_done), "minutes_elapsed": elapsed,
        "open_round": open_round(events), "next_round": next_round_label(events),
        "bar_version": max(versions) if versions else None, "bar_unpublished_edits": unpublished,
        "bar_audit": pending_audit(events),
        "last_verdict": {"round": fl.round_label(last_verdict["round"]), "type": last_verdict["type"],
                         "failing": [c["id"] for c in last_verdict["criteria"] if c["result"] == "FAIL"]} if last_verdict else None,
        "fail_streaks": streaks, "diagnose_due": bool(stuck) or recapture_streak >= 2,
        "stuck_criteria": stuck, "recapture_streak": recapture_streak,
        "check_in_due": check_due, "budget_exhausted": exhausted, "terminal": terminal,
        "build_unchanged": build_unchanged,
    }
    status["next"] = next_action(status, voided_after_win)
    return status


def round_after(events: list[dict], round_label: str, marker: dict) -> bool:
    idx_marker = events.index(marker)
    for i, ev in enumerate(events):
        if ev.get("round") == round_label and ev.get("result") in ("FAIL", "WIN"):
            return i > idx_marker
    return False


def next_action(s: dict, voided_after_win: bool) -> str:
    if s["terminal"]:
        return f"run ended ({s['terminal']}); start a new run or extend with the user's go-ahead"
    if s["bar_version"] is None:
        return "fill art/BAR.md from the goal, then: forge.py bar publish --reason \"initial bar\""
    if s["open_round"]:
        return f"round {s['open_round']} is open: spawn the critic (or validate its verdict) and log FAIL/WIN/RECAPTURE"
    if s["bar_audit"] == "pending":
        return "bar revision awaits audit: run a fresh critic with SCOPE: bar, then log BAR-OK"
    if s["bar_audit"] == "lowered":
        return "bar audit said BAR-LOWERED: revert the revision or get explicit user approval"
    if s["bar_unpublished_edits"]:
        return "art/BAR.md has unpublished edits: forge.py bar publish --type ... --reason ..."
    last = s["last_verdict"]
    if last and last["type"] == "WIN" and not voided_after_win:
        return "critic WIN: run the orchestrator harsh read and pre-handoff checks, then HANDOFF or WIN-VOIDED"
    if s["budget_exhausted"]:
        return "budget exhausted: stop, report best-so-far with the workbench, and ask the user whether to extend"
    if s["diagnose_due"]:
        what = ", ".join(s["stuck_criteria"]) or "capture"
        return f"stuck on {what}: log DIAGNOSE-HOLD and spawn a fresh Diagnoser before more punch rounds"
    if s["check_in_due"]:
        return "check-in due: post a short progress summary with the workbench link, log CHECK-IN, keep going"
    if last:
        return f"dispatch builders on the {last['round']} punch list, then capture {s['next_round']}"
    return f"build, then capture {s['next_round']}"


def cmd_status(args) -> int:
    project, cfg = project_and_config(args)
    status = compute_status(project, cfg)
    if args.json:
        print(json.dumps(status, indent=2))
        return 0
    b = status["budgets"]
    lim = lambda v: "no limit" if not v else v  # noqa: E731
    print(f"{status['title'] or project.name} [{status['mode']}]")
    print(f"  rounds   {status['rounds_used']} / {lim(b['rounds'])}    minutes {status['minutes_elapsed']} / {lim(b['minutes'])}")
    print(f"  bar      v{status['bar_version'] or '-'}"
          + ("  (unpublished edits)" if status["bar_unpublished_edits"] else "")
          + (f"  (audit {status['bar_audit']})" if status["bar_audit"] else ""))
    if status["last_verdict"]:
        lv = status["last_verdict"]
        print(f"  last     {lv['round']} {lv['type']}" + (f"  failing {', '.join(lv['failing'])}" if lv["failing"] else ""))
    if status["fail_streaks"]:
        print("  streaks  " + ", ".join(f"{k}x{v}" for k, v in sorted(status["fail_streaks"].items())))
    if status["build_unchanged"]:
        print("  warning  the last two rounds captured the same build id: the punch round changed nothing in the product")
    print(f"  next     {status['next']}")
    return 0


def cmd_build_id(args) -> int:
    project, cfg = project_and_config(args)
    print(fl.build_id(project, cfg))
    return 0


# --- cli --------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="forge.py", description=__doc__.split("\n\n")[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split("\n\n", 1)[1])
    parser.add_argument("--project", default=".", help="project root (default: current directory)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="scaffold a project for a mode")
    p.add_argument("--mode", choices=sorted(MODES), default="standard")
    p.add_argument("--title", required=True)
    p.add_argument("--goal", help="one-sentence goal to seed BRIEF.md")
    p.add_argument("--pack", action="append", choices=["3d", "web-ui", "dataviz", "2d", "interactive"],
                   help="criteria pack(s) to start from (repeatable)")
    p.add_argument("--stack", default="other", choices=["web", "blender-web", "unity", "other"],
                   help="web stacks also get tools/capture.mjs")
    for flag in ("rounds", "minutes", "check-in-rounds", "check-in-minutes", "stuck-after"):
        p.add_argument(f"--{flag}", type=int, help=f"override the mode default for {flag} (0 = no limit)")
    p.add_argument("--force", action="store_true", help="rewrite templates and forge.json")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("log", help="append one event to rounds.log")
    p.add_argument("--result", required=True, help="event result, e.g. CAPTURE, FAIL, WIN, CHECK-IN")
    p.add_argument("--stage", choices=STAGES)
    p.add_argument("--round", help="R<n>; CAPTURE picks the next round when omitted")
    p.add_argument("--role", choices=ROLES, default="orchestrator")
    p.add_argument("--build", help="build id (default: detected for CAPTURE)")
    p.add_argument("--session", help="host session id for the subagent, if any")
    p.add_argument("--field", action="append", metavar="KEY=VALUE", help="extra field, e.g. rung=2 (repeatable)")
    p.add_argument("--note", help="short free text")
    p.set_defaults(func=cmd_log)

    p = sub.add_parser("bar", help="publish or diff the bar")
    bar_sub = p.add_subparsers(dest="bar_cmd", required=True)
    pub = bar_sub.add_parser("publish", help="publish art/BAR.md as the next version")
    pub.add_argument("--type", choices=BAR_TYPES, help="initial | add | raise | clarify | loosen | retire")
    pub.add_argument("--reason", required=True)
    pub.add_argument("--user-approved", help="the user's approval, verbatim (required for loosen/retire)")
    pub.set_defaults(func=cmd_bar)
    dif = bar_sub.add_parser("diff", help="show unpublished edits")
    dif.set_defaults(func=cmd_bar)

    p = sub.add_parser("snapshot", help="copy current stills into history/<round>/")
    p.add_argument("round", help="round label, e.g. R03")
    p.add_argument("--source", help="folder to copy (default: stills path)")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_snapshot)

    p = sub.add_parser("manifest", help="write MANIFEST.md for existing stills")
    p.add_argument("--stills", help="stills folder (default from forge.json)")
    p.add_argument("--build", help="build id (default: detected)")
    p.add_argument("--view", action="append", metavar="STEM=NAME", help="view name per still, e.g. still-01=hero")
    p.set_defaults(func=cmd_manifest)

    p = sub.add_parser("status", help="budgets, streaks and next action")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("build-id", help="print the current build id")
    p.set_defaults(func=cmd_build_id)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except fl.ForgeError as exc:
        print(f"forge.py: {exc}", file=sys.stderr)
        return exc.code
    except OSError as exc:
        print(f"forge.py: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
