#!/usr/bin/env python3
"""Build artifacts/workbench.html: a self-contained, auto-refreshing progress page for a forge-protocol run.

Reads forge.json, BRIEF.md, art/BAR.md, art/bar-history/, artifacts/rounds.log, artifacts/verdicts/,
artifacts/history/, artifacts/stills/, artifacts/compare/ and artifacts/turnarounds/. Images are linked by
relative path with a cache-busting stamp, so re-running after each round updates the open page in place.
Open it directly, or serve the artifacts folder: python3 -m http.server --directory artifacts 8000

  make_workbench.py [--project .] [--out artifacts/workbench.html] [--refresh 20]

Standard library only. Exit codes: 0 ok, 2 usage or file error.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import forge  # noqa: E402
import forgelib as fl  # noqa: E402

E = html.escape


def rel(path: Path, base: Path) -> str:
    stamp = int(path.stat().st_mtime) if path.exists() else 0
    return E(Path(os.path.relpath(path, base)).as_posix()) + f"?v={stamp}"


def goal_line(brief: Path) -> str:
    if not brief.is_file():
        return ""
    m = re.search(r"^##\s+Goal\s*\n+(.+?)(?:\n\s*\n|\n##|\Z)", brief.read_text(encoding="utf-8"), re.S | re.M)
    text = m.group(1).strip() if m else ""
    return "" if text.startswith("<") else " ".join(text.split())


def pass_line(body: str) -> str:
    m = re.search(r"PASS when:\s*(.+)", body)
    return m.group(1).strip() if m else ""


def bar_versions(events: list[dict]) -> list[dict]:
    out = []
    for ev in events:
        if ev.get("result") == "BAR-PUBLISH":
            out.append({"version": ev.get("bar", "?"), "type": ev.get("type", "?"), "time": ev.get("time", ""),
                        "reason": ev.get("note", ""), "audit": ev.get("audit", "none"),
                        "approved": ev.get("approved"), "diff": ev.get("continuation", [])})
    return out


def compare_sets(compare: Path) -> list[dict]:
    sets = []
    if not compare.is_dir():
        return sets
    for folder in sorted(p for p in compare.iterdir() if p.is_dir() and p.name != "keys"):
        manifest = folder / "pairs.json"
        if not manifest.is_file():
            continue
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        sets.append({"name": folder.name, "folder": folder, "data": data})
    return sets


def chip(result: str) -> str:
    cls = {"PASS": "pass", "FAIL": "fail", "WIN": "pass", "GATE-PASS": "pass"}.get(result, "muted")
    return f'<span class="chip {cls}">{E(result)}</span>'


def render(project: Path, cfg: dict, out: Path, refresh: int) -> str:
    base = out.parent
    events = fl.read_log(fl.resolve(project, cfg, "log"))
    status = forge.compute_status(project, cfg)
    bar_path = fl.resolve(project, cfg, "bar")
    bar = fl.parse_bar(bar_path.read_text(encoding="utf-8")) if bar_path.is_file() else {"version": None, "criteria": []}
    verdicts = forge.load_round_verdicts(project, cfg)
    history = fl.resolve(project, cfg, "history")
    snaps = sorted((p for p in history.iterdir() if p.is_dir() and fl.round_number(p.name) is not None),
                   key=lambda p: fl.round_number(p.name)) if history.is_dir() else []
    stills = fl.list_images(fl.resolve(project, cfg, "stills"))
    turnarounds = fl.list_images(fl.resolve(project, cfg, "turnarounds"))
    diagnosis = sorted(fl.resolve(project, cfg, "diagnosis").glob("*.md")) if fl.resolve(project, cfg, "diagnosis").is_dir() else []
    title = cfg.get("title") or project.name
    budgets = status["budgets"]

    last = status["last_verdict"]
    if status["terminal"] == "HANDOFF" and last and last["type"] == "WIN":
        state, state_cls = "FINAL WIN", "pass"
    elif status["terminal"]:
        state, state_cls = status["terminal"], "muted"
    elif status["budget_exhausted"]:
        state, state_cls = "BUDGET REACHED", "warn"
    elif last:
        state, state_cls = f"{last['round']} {last['type']}", "pass" if last["type"] == "WIN" else "fail"
    else:
        state, state_cls = "BUILDING", "accent"
    publish = "UNLOCKED" if any(ev.get("result") == "PUBLISH-UNLOCK" for ev in events) else "LOCKED"
    limit = lambda v: "&infin;" if not v else str(v)  # noqa: E731

    parts: list[str] = []
    add = parts.append
    add(f"""<header class="top"><div class="title"><h1>{E(title)}</h1>
<span class="chip accent">{E(str(cfg.get('mode', '?')).upper())}</span><span class="chip {state_cls} big">{E(state)}</span></div>
<p class="goal">{E(goal_line(fl.resolve(project, cfg, 'brief')))}</p>
<div class="stats">
<div><b>{status['rounds_used']}</b><span>/ {limit(budgets['rounds'])} rounds</span></div>
<div><b>{status['minutes_elapsed']}</b><span>/ {limit(budgets['minutes'])} min</span></div>
<div><b>v{E(str(status['bar_version'] or '-'))}</b><span>bar, {len(bar['criteria'])} criteria</span></div>
<div><b>{E(publish)}</b><span>publish</span></div>
<div class="next"><span>next</span>{E(status['next'])}</div></div>
<div class="toolbar"><span id="updated">updated {E(fl.now_iso().replace('T', ' '))}</span>
<button id="pause" type="button">pause refresh</button></div></header>""")

    add('<nav><a href="#now">Now</a><a href="#progress">Progress</a><a href="#matrix">Criteria</a>'
        '<a href="#rounds">Rounds</a><a href="#bar">Bar</a><a href="#log">Log</a></nav><main>')

    add('<section id="now"><h2>Current captures</h2>')
    if stills:
        add('<div class="grid">' + "".join(
            f'<figure><img loading="lazy" src="{rel(p, base)}" alt="{E(p.stem)}" data-full="{rel(p, base)}"><figcaption>{E(p.stem)}</figcaption></figure>'
            for p in stills) + "</div>")
    else:
        add('<p class="empty">No captures yet.</p>')
    add("</section>")

    add('<section id="progress"><h2>Round over round</h2>')
    if len(snaps) >= 2:
        a, b = snaps[-2], snaps[-1]
        pairs, _ = pair_slots(a, b)
        add(f'<p class="hint">Drag to compare {E(a.name)} (left) with {E(b.name)} (right).</p><div class="grid wide">')
        for slot, pa, pb in pairs:
            add(f'<figure class="ba"><div class="ba-frame"><img src="{rel(pb, base)}" alt="{E(b.name)} {E(slot)}">'
                f'<img class="ba-top" src="{rel(pa, base)}" alt="{E(a.name)} {E(slot)}"><span class="ba-line"></span></div>'
                f'<input type="range" min="0" max="100" value="50" aria-label="compare slot {E(slot)}">'
                f'<figcaption>slot {E(slot)}: {E(a.name)} | {E(b.name)}</figcaption></figure>')
        add("</div>")
    elif snaps:
        add(f'<p class="empty">One snapshot so far ({E(snaps[0].name)}). Snapshot each round with forge.py snapshot.</p>')
    else:
        add('<p class="empty">No round snapshots yet.</p>')
    if snaps:
        add('<div class="filmstrip">' + "".join(
            f'<div class="film"><b>{E(s.name)}</b>' + "".join(
                f'<img loading="lazy" src="{rel(p, base)}" alt="{E(s.name)} {E(p.stem)}" data-full="{rel(p, base)}">'
                for p in fl.list_images(s)) + "</div>" for s in reversed(snaps)) + "</div>")
    for cset in compare_sets(fl.resolve(project, cfg, "compare")):
        data, folder = cset["data"], cset["folder"]
        label = "blind A/B" if data.get("blind") else f"{data.get('left_label')} vs {data.get('right_label')}"
        files = [folder / f for pair in data.get("pairs", []) for f in pair.get("files", []) if not f.endswith(tuple(f"-detail-{q}.png" for q in "1234"))]
        if files:
            add(f'<h3>{E(cset["name"])} <span class="muted">({E(label)})</span></h3><div class="grid wide">' + "".join(
                f'<figure><img loading="lazy" src="{rel(f, base)}" alt="{E(f.stem)}" data-full="{rel(f, base)}"><figcaption>{E(f.name)}</figcaption></figure>'
                for f in files if f.exists()) + "</div>")
    add("</section>")

    add('<section id="matrix"><h2>Criteria by round</h2>')
    if bar["criteria"] and verdicts:
        add('<div class="scroll"><table class="matrix"><thead><tr><th>criterion</th>' + "".join(
            f'<th><a href="{rel(v["path"], base)}">{E(fl.round_label(v["round"]))}</a></th>' for v in verdicts) + "</tr></thead><tbody>")
        for crit in bar["criteria"]:
            cells = []
            for v in verdicts:
                res = next((c["result"] for c in v["criteria"] if c["id"] == crit["id"]), "")
                cls = {"PASS": "pass", "FAIL": "fail"}.get(res, "none")
                cells.append(f'<td class="{cls}" title="{E(crit["id"])} {E(fl.round_label(v["round"]))}: {E(res or "not graded")}">{E(res[:1] if res else "")}</td>')
            add(f'<tr><th title="{E(pass_line(crit["body"]))}"><code>{E(crit["id"])}</code> {E(crit["name"])}</th>{"".join(cells)}</tr>')
        add("</tbody></table></div>")
    else:
        add('<p class="empty">Appears after the first graded round.</p>')
    add("</section>")

    add('<section id="rounds"><h2>Rounds</h2>')
    if verdicts:
        snap_by_round = {fl.round_number(s.name): s for s in snaps}
        for v in reversed(verdicts):
            failing = [c for c in v["criteria"] if c["result"] == "FAIL"]
            add(f'<article class="card"><header><h3>{E(fl.round_label(v["round"]))}</h3>{chip(v["type"])}'
                f'<a class="muted" href="{rel(v["path"], base)}">verdict</a></header>')
            if failing:
                add('<p>' + " ".join(f'<span class="chip fail" title="{E(c["evidence"])}">{E(c["id"])} {E(c["name"])}</span>' for c in failing) + "</p>")
            if v["punch"]:
                add(f'<details><summary>{len(v["punch"])} punch items</summary><ol>' + "".join(
                    f"<li>{E(item['text'])}</li>" for item in v["punch"]) + "</ol></details>")
            snap = snap_by_round.get(v["round"])
            if snap:
                add('<div class="thumbs">' + "".join(
                    f'<img loading="lazy" src="{rel(p, base)}" alt="{E(p.stem)}" data-full="{rel(p, base)}">' for p in fl.list_images(snap)) + "</div>")
            add("</article>")
    else:
        add('<p class="empty">No graded rounds yet.</p>')
    if diagnosis:
        add('<h3>Diagnoser steers</h3><ul>' + "".join(f'<li><a href="{rel(p, base)}">{E(p.name)}</a></li>' for p in diagnosis) + "</ul>")
    if turnarounds:
        add('<h3>Turnarounds</h3><div class="grid wide">' + "".join(
            f'<figure><img loading="lazy" src="{rel(p, base)}" alt="{E(p.stem)}" data-full="{rel(p, base)}"><figcaption>{E(p.stem)}</figcaption></figure>'
            for p in turnarounds) + "</div>")
    add("</section>")

    add(f'<section id="bar"><h2>Bar v{E(str(bar["version"] or "-"))}</h2>')
    if bar["criteria"]:
        add("<dl class=\"bar\">" + "".join(
            f'<dt><code>{E(c["id"])}</code> {E(c["name"])}</dt><dd>{E(pass_line(c["body"]))}</dd>' for c in bar["criteria"]) + "</dl>")
    versions = bar_versions(events)
    if versions:
        add("<h3>Revisions</h3>")
        for ver in reversed(versions):
            flags = f" audit {ver['audit']}" if ver["audit"] not in ("none", None) else ""
            approved = f' <span class="chip warn">user-approved: {E(ver["approved"])}</span>' if ver.get("approved") else ""
            add(f'<details class="rev"><summary><b>{E(ver["version"])}</b> {E(ver["type"])}{E(flags)}: {E(ver["reason"])}'
                f' <span class="muted">{E(ver["time"].replace("T", " "))}</span>{approved}</summary><pre>'
                + "\n".join(diff_line(line) for line in ver["diff"]) + "</pre></details>")
    add("</section>")

    add('<section id="log"><h2>Event log</h2><div class="scroll"><table class="log"><thead><tr>'
        "<th>time</th><th>stage</th><th>round</th><th>role</th><th>result</th><th>note</th></tr></thead><tbody>")
    for ev in list(reversed(events))[:300]:
        res = ev.get("result", "")
        cls = "pass" if res in ("WIN", "GATE-PASS", "BAR-OK", "HANDOFF") else "fail" if res in ("FAIL", "GATE-FAIL", "WIN-VOIDED", "BAR-LOWERED", "BLOCKED") else ""
        add(f'<tr><td>{E(ev.get("time", "").replace("T", " "))}</td><td>{E(ev.get("stage", ""))}</td><td>{E(ev.get("round", ""))}</td>'
            f'<td>{E(ev.get("role", ""))}</td><td class="{cls}">{E(res)}</td><td title="{E(ev.get("note", ""))}">{E(ev.get("note", ""))}</td></tr>')
    add("</tbody></table></div></section></main>")
    add(f'<footer>forge-protocol {E(fl.FORGE_VERSION)} workbench. Regenerate with make_workbench.py after each round; '
        f'this page reloads every {refresh}s.</footer>')
    add('<div id="lightbox" hidden><img alt=""><span id="lb-cap"></span></div>')
    body = "\n".join(parts)
    return PAGE.replace("{{TITLE}}", E(title)).replace("{{REFRESH}}", str(refresh)).replace("{{BODY}}", body)


def diff_line(line: str) -> str:
    cls = "add" if line.startswith("+") and not line.startswith("+++") else "del" if line.startswith("-") and not line.startswith("---") else ""
    return f'<span class="{cls}">{E(line)}</span>' if cls else E(line)


def pair_slots(a: Path, b: Path) -> tuple[list[tuple[str, Path, Path]], list[str]]:
    left = {fl.slot_key(p.name): p for p in fl.list_images(a) if fl.slot_key(p.name)}
    right = {fl.slot_key(p.name): p for p in fl.list_images(b) if fl.slot_key(p.name)}
    keys = sorted((k for k in left if k in right), key=int)
    return [(k, left[k], right[k]) for k in keys], [k for k in set(left) ^ set(right)]


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{TITLE}} | workbench</title>
<noscript><meta http-equiv="refresh" content="{{REFRESH}}"></noscript>
<style>
:root{--bg:#0b0d12;--panel:#131722;--line:#232a3a;--text:#e7eaf2;--muted:#8b93a7;--accent:#7aa2ff;--pass:#3ecf8e;--fail:#ff6b6b;--warn:#f5b942}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:radial-gradient(1200px 600px at 10% -10%,#1a2340 0,transparent 60%),var(--bg);color:var(--text);
font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,Helvetica,Arial,sans-serif}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
code,pre,.log td{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:13px}
.top{padding:28px clamp(16px,4vw,48px) 12px;border-bottom:1px solid var(--line);background:linear-gradient(180deg,rgba(122,162,255,.08),transparent)}
.title{display:flex;align-items:center;gap:12px;flex-wrap:wrap}h1{margin:0;font-size:clamp(22px,3vw,32px);letter-spacing:-.02em}
.goal{color:var(--muted);max-width:900px;margin:6px 0 16px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px}
.stats>div{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:10px 14px}
.stats b{font-size:22px;margin-right:6px}.stats span{color:var(--muted)}
.stats .next{grid-column:1/-1;display:flex;gap:10px;align-items:baseline}.stats .next span{text-transform:uppercase;font-size:12px;letter-spacing:.08em}
.toolbar{display:flex;justify-content:space-between;align-items:center;color:var(--muted);font-size:13px;margin-top:10px}
button{background:var(--panel);color:var(--text);border:1px solid var(--line);border-radius:8px;padding:6px 12px;cursor:pointer}
nav{position:sticky;top:0;z-index:5;display:flex;gap:18px;padding:10px clamp(16px,4vw,48px);background:rgba(11,13,18,.85);backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}
main{padding:8px clamp(16px,4vw,48px) 40px}section{padding-top:18px}h2{font-size:18px;margin:12px 0}h3{font-size:15px;margin:16px 0 8px}
.chip{display:inline-block;padding:2px 10px;border-radius:999px;border:1px solid var(--line);font-size:12px;font-weight:600;letter-spacing:.03em;margin:2px 4px 2px 0}
.chip.big{font-size:14px;padding:4px 14px}.chip.pass{background:rgba(62,207,142,.14);color:var(--pass);border-color:rgba(62,207,142,.4)}
.chip.fail{background:rgba(255,107,107,.14);color:var(--fail);border-color:rgba(255,107,107,.4)}
.chip.warn{background:rgba(245,185,66,.14);color:var(--warn);border-color:rgba(245,185,66,.4)}
.chip.accent{background:rgba(122,162,255,.14);color:var(--accent);border-color:rgba(122,162,255,.4)}.chip.muted,.muted{color:var(--muted)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}.grid.wide{grid-template-columns:repeat(auto-fill,minmax(420px,1fr))}
figure{margin:0;background:var(--panel);border:1px solid var(--line);border-radius:12px;overflow:hidden}
figure img{display:block;width:100%;height:auto;cursor:zoom-in}figcaption{padding:6px 10px;color:var(--muted);font-size:13px}
.ba-frame{position:relative;line-height:0}.ba-frame img{width:100%;cursor:default}
.ba-top{position:absolute;inset:0;height:100%;object-fit:cover;clip-path:inset(0 50% 0 0)}
.ba-line{position:absolute;top:0;bottom:0;left:50%;width:2px;background:#fff;box-shadow:0 0 8px rgba(0,0,0,.6)}
.ba input{width:calc(100% - 20px);margin:8px 10px 0}
.filmstrip{display:flex;flex-direction:column;gap:8px;margin-top:14px}.film{display:flex;gap:8px;align-items:center;overflow-x:auto}
.film b{min-width:44px;color:var(--muted)}.film img,.thumbs img{height:84px;border-radius:6px;border:1px solid var(--line);cursor:zoom-in}
.thumbs{display:flex;gap:8px;overflow-x:auto;margin-top:8px}
.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%}th,td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}
.matrix td{text-align:center;font-weight:700;min-width:38px}.matrix td.pass{background:rgba(62,207,142,.22);color:var(--pass)}
.matrix td.fail{background:rgba(255,107,107,.22);color:var(--fail)}.matrix td.none{color:var(--muted)}
.matrix th{white-space:nowrap}.log td{max-width:520px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
td.pass{color:var(--pass)}td.fail{color:var(--fail)}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px 16px;margin:10px 0}
.card header{display:flex;gap:10px;align-items:center}.card h3{margin:0}
details summary{cursor:pointer;color:var(--muted)}ol{margin:8px 0;padding-left:22px}
dl.bar dt{margin-top:10px;font-weight:600}dl.bar dd{margin:2px 0 0;color:var(--muted)}
pre{background:#0d1018;border:1px solid var(--line);border-radius:8px;padding:10px;overflow-x:auto;white-space:pre-wrap}
pre .add{color:var(--pass)}pre .del{color:var(--fail)}.rev{margin:6px 0}
.empty,.hint{color:var(--muted)}footer{color:var(--muted);font-size:13px;padding:20px clamp(16px,4vw,48px);border-top:1px solid var(--line)}
#lightbox{position:fixed;inset:0;z-index:20;background:rgba(5,6,10,.92);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;cursor:zoom-out}
#lightbox[hidden]{display:none}#lightbox img{max-width:96vw;max-height:88vh;border-radius:8px}#lb-cap{color:var(--muted)}
</style></head><body>
{{BODY}}
<script>
(() => {
  const refreshMs = {{REFRESH}} * 1000;
  const key = 'forge-wb-scroll:' + location.pathname;
  const paused = () => localStorage.getItem('forge-wb-paused') === '1';
  const btn = document.getElementById('pause');
  const sync = () => { btn.textContent = paused() ? 'resume refresh' : 'pause refresh'; };
  btn.addEventListener('click', () => { localStorage.setItem('forge-wb-paused', paused() ? '0' : '1'); sync(); });
  sync();
  const saved = sessionStorage.getItem(key);
  if (saved) window.scrollTo(0, Number(saved));
  setInterval(() => { if (!paused() && document.getElementById('lightbox').hidden) { sessionStorage.setItem(key, String(window.scrollY)); location.reload(); } }, refreshMs);
  document.querySelectorAll('.ba').forEach((fig) => {
    const top = fig.querySelector('.ba-top'); const line = fig.querySelector('.ba-line'); const range = fig.querySelector('input');
    const set = (v) => { top.style.clipPath = `inset(0 ${100 - v}% 0 0)`; line.style.left = v + '%'; };
    range.addEventListener('input', () => set(range.value)); set(range.value);
  });
  const lb = document.getElementById('lightbox'); const lbImg = lb.querySelector('img'); const cap = document.getElementById('lb-cap');
  const imgs = [...document.querySelectorAll('img[data-full]')]; let idx = -1;
  const show = (i) => { idx = (i + imgs.length) % imgs.length; lbImg.src = imgs[idx].dataset.full; cap.textContent = imgs[idx].alt; lb.hidden = false; };
  imgs.forEach((img, i) => img.addEventListener('click', () => show(i)));
  lb.addEventListener('click', () => { lb.hidden = true; });
  document.addEventListener('keydown', (e) => {
    if (lb.hidden) return;
    if (e.key === 'Escape') lb.hidden = true;
    if (e.key === 'ArrowRight') show(idx + 1);
    if (e.key === 'ArrowLeft') show(idx - 1);
  });
})();
</script></body></html>
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=__doc__.split("\n\n", 1)[1])
    parser.add_argument("--project", default=".", help="project root (default: current directory)")
    parser.add_argument("--out", help="output file (default: artifacts/workbench.html)")
    parser.add_argument("--refresh", type=int, default=20, help="auto-refresh interval in seconds (default 20)")
    args = parser.parse_args(argv)
    try:
        if args.refresh < 2:
            raise fl.ForgeError("--refresh must be at least 2 seconds")
        project = Path(args.project).expanduser().resolve()
        cfg = fl.load_config(project)
        out = Path(args.out).expanduser().resolve() if args.out else fl.resolve(project, cfg, "workbench")
        out.parent.mkdir(parents=True, exist_ok=True)
        page = render(project, cfg, out, args.refresh)
        tmp = out.with_suffix(".tmp")
        tmp.write_text(page, encoding="utf-8")
        tmp.replace(out)
    except (OSError, fl.ForgeError) as exc:
        print(f"make_workbench.py: {exc}", file=sys.stderr)
        return 2
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
