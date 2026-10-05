---
name: forge-protocol
description: >-
  Builds polished demos, 3D scenes, browser games, simulations, web UIs and data viz, then loops captures
  of the running build past a fresh blind critic that grades every criterion PASS or FAIL against a bar
  derived from the user's goal. A lead agent plans behind a scaled approval gate, splits the work across
  builder subagents, runs capture, critic and punch-list rounds within explicit budgets, diagnoses stuck
  loops, keeps a live workbench page, and keeps publishing locked. Supports Blender (MCP or headless) with
  Three.js/WebGPU or Unity. Use when the user wants a demo, scene, game, prototype or visual experience
  built to a high bar, asks to keep improving it until it is great, or starts a long autonomous build. Not
  for backend-only work or one-line fixes. Adapts Matt Shumer's Gauntlet Loop and Eric Zakariasson's
  game-builder skills.
license: MIT
compatibility: >-
  Needs subagents or fresh sessions and a critic that can view images. Scripts need Python 3.9+;
  make_sxs.py needs ffmpeg. Optional: Node 18+ with Playwright, Blender, Unity 6 with
  com.unity.ai.assistant.
metadata:
  version: "2.0.0"
---

# Forge Protocol: the goal-driven blind-critic loop

Turn a goal into a demo that holds up under a harsh, independent eye. You are the **Orchestrator**: you write a bar from the user's goal, split the work across builder subagents, and loop captures of the running build past a fresh critic that grades every criterion PASS or FAIL, until it wins, a budget runs out, or the user stops it. Working code is the floor, never the exit.

## When to Use

- Visual or interactive deliverables: 3D worlds and scenes, browser games, physics sims, product demos, landing pages, dashboards and data viz, motion pieces.
- The user wants it great, not just working: "make it look amazing", "keep going until it's great", "forge this".
- Long autonomous runs that need budgets, check-ins and a progress page.

Skip it for backend-only changes, one-line fixes, or work with no visual or interactive output.

## Pick a mode

| | Sprint | Standard | Forge |
| :--- | :--- | :--- | :--- |
| Use for | a quick demo or one screen | a polished demo or small game | multi-hour worlds, games, showcase pieces |
| Plan gate | short plan, then start | plan, wait for a go | full plan, wait for a go |
| Default budget | 3 rounds, 30 min | 8 rounds, 2 h | 25 rounds, 8 h |
| Check-ins | at the end | every 3 rounds or 45 min | every 5 rounds or 90 min |
| Files | BRIEF, BAR | + PLAN, LOOK | + LEDGER, turnarounds |
| Blender | optional | when hero meshes need it | default route for hero meshes |

Choose from the request and say which mode and why in one line. The user's numbers override every default ("spend at most 20 minutes"). A budget of 0 means no limit; use it only when the user asks.

## Rule 0: plan before building

Before writing application code or spawning builders, reply with a plan sized to the mode:

1. **Goal and must-haves**: the goal in one sentence, and the must-haves the critic will check.
2. **The bar**: the criteria you will grade (see The bar).
3. **Tools, probed live**: a table of tool, status and role. Probes: `python3 <skill-dir>/scripts/blender_mcp_cli.py status`, `blender --version`, `node --version` plus Playwright, `ls ~/.unity/relay/`.
4. **Pieces and roles**: what each builder makes and how each piece is judged; mode, budgets, check-in cadence.

Then:
- **Sprint**: start right away unless the request is ambiguous or risky.
- **Standard and Forge**: wait for an explicit go, unless the user already pre-approved ("go ahead", "no need to check with me", "just build it"). Log `APPROVED` with the user's words.
- **Autonomous or goal modes**: when the plan still needs approval, end the plan turn by saying plainly that you are waiting for the user's go, then stop.

If the user attached images, treat them as part of the goal description: read them for intent, never as a pixel target or a set to store.

## Roles (non-negotiable)

| Role | Does | Never |
| :--- | :--- | :--- |
| Orchestrator (you) | plan, bar, decomposition, dispatch, verdict validation, logging, gates, harsh read, handoff | builds, or grades its own work |
| Builder | code, assets, captures, punch fixes; hands back paths and what was addressed | uses verdict words or claims quality |
| Critic | grades captures against `BRIEF.md` and `art/BAR.md`; returns one verdict block | sees builder chat, edits files, prescribes code |
| Diagnoser | root-causes a stuck loop and writes a steer | grades, edits, or softens the bar |

Spawn every critic and Diagnoser **fresh** through the environment's subagent or task mechanism, giving it only the file paths its prompt lists. If there is no such mechanism, start a fresh session that receives only those paths, and log `critic=fresh-context`. If no available critic can view images, the loop is invalid: report BLOCKED.

## The bar

- Write `art/BAR.md` from the goal and domain expertise. Research facts and techniques when they sharpen a criterion (how real caustics behave, plausible physics constants, type-scale ratios). Never phrase a criterion against a picture.
- Shared core: **C1 Goal fit**, **C2 Live capture provenance**, **C3 State and motion integrity**. Add goal-specific criteria from C4 on, starting from [references/criteria-packs.md](references/criteria-packs.md), each observable, binary and motivated by the goal. Use as many as one critic pass can check; most bars land between 4 and 10.
- The bar is a **versioned ratchet** ([references/visual-bar.md](references/visual-bar.md)):
  - Publish v1 before the first capture: `forge.py bar publish --reason "initial bar"`.
  - Revise only **between rounds**, after a verdict and before the next capture. Never mid-round.
  - Adding, raising or clarifying is fine; every revision logs its type, reason and diff in `rounds.log`.
  - Editing a criterion that failed last round needs a fresh critic audit (`SCOPE: bar`, BAR-OK) before the next capture.
  - Loosening or retiring a criterion needs the user's explicit approval, quoted in the log. Never lower the bar to rescue a failing build.
  - The critic always grades the current version; the validator rejects verdicts on a stale bar or one edited mid-round.

## The loop

**Setup**: `forge.py init --mode <mode> --title "<title>" [--pack 3d|web-ui|dataviz|2d|interactive] [--stack web|blender-web|unity|other]`, fill `BRIEF.md` and `art/BAR.md`, publish bar v1, set up capture (`tools/capture.mjs` for web stacks, a render script for Blender or Unity), then generate the workbench and give the user its path.

**Build**: split the work into the smallest pieces that can be built and judged separately, and dispatch independent pieces in parallel. Gate risky pieces cheaply before integration: a turnaround for each hero mesh ([references/unity-and-blender-pipelines.md](references/unity-and-blender-pipelines.md)), or a critic check with `SCOPE: gate`. After each wave, one smoothing pass harmonizes scale, light, color and type across the pieces.

**Each round R<n>**:
1. **Capture** the running build: one still per must-have view or state at the size `BRIEF.md` names, plus walkthrough frames when there is motion. Re-capture everything every round and write `MANIFEST.md`. Log `CAPTURE`; it records the build id and the bar hash.
2. **Record**: `forge.py snapshot R<n>`, `make_sxs.py` for round-over-round composites, then `make_workbench.py`.
3. **Grade**: spawn a fresh critic with [references/critic-prompt.md](references/critic-prompt.md) and file paths only.
4. **Validate**: `validate_verdict.py <file> --project .`. If it is invalid, re-run the critic; never edit a verdict. Save valid verdicts as `artifacts/verdicts/R<nn>.md` and log the result.
5. **Act**: RECAPTURE: fix the capture, same round. FAIL: builders fix the punch list verbatim, then the next round. WIN: go to Handoff.
6. **Report** one status line: `R<n> <FAIL|WIN|RECAPTURE|DIAGNOSE>: failing <ids|none>; punch <count>; rung <n|none>; budget <used>/<limit>; next: <action>`.

**Stuck loop**: when one criterion fails `stuck_after` rounds in a row (Sprint 2, otherwise 3), captures keep coming back RECAPTURE, or the build id did not change between rounds, log `DIAGNOSE-HOLD` and spawn a fresh Diagnoser ([references/diagnoser-prompt.md](references/diagnoser-prompt.md)). Builders then work from its steer. `forge.py status` flags all of these.

**Budgets and stopping**: stop on a harsh-read-confirmed WIN, an exhausted budget, a user stop, or a hard blocker. When a budget runs out, stop, report best-so-far honestly with the workbench, and ask whether to extend (log `BUDGET-EXHAUSTED`, then `BUDGET-EXTENDED` with `--field rounds=+N`). Check-ins are non-blocking progress notes at the mode cadence; keep working after them.

**Context**: keep the orchestrator lean. Pass file paths, not images or long logs; let critics open the images; read `forge.py status` instead of re-reading history.

## Handoff

A critic WIN is necessary, not sufficient:
1. **Harsh read**: open every current still yourself. One coherent art system, consistent scale and perspective, coherent light, nothing a viewer would call unfinished. If it fails, log `WIN-VOIDED`, tell the user once why, and continue rounds.
2. **Pre-handoff checks**: a valid WIN on the current bar version; `MANIFEST.md` matches the delivered build; no `placeholder` rows in the ledger; third-party assets licensed; no secrets; no model or vendor names in artifacts unless `BRIEF.md` allows them (then validate verdicts with `--allow-identifiers`).
3. **Report** what was built, how to run it, the final stills, rounds used, bar versions and open caveats, with Publish still LOCKED unless the user unlocked it. Log `HANDOFF`.

## Non-negotiables

1. Builders never grade themselves; every grade comes from a fresh critic with file inputs only.
2. Every criterion is PASS or FAIL with cited evidence. No numeric scores; banned soft-pass phrases invalidate a verdict.
3. The bar only ratchets up without the user's explicit approval.
4. Captures come from the live build, re-captured in full each round; no mockups or retouching.
5. Publish stays LOCKED until the user explicitly unlocks it; log `PUBLISH-UNLOCK`.
6. Ship only original work, or third-party assets whose license allows it (PolyHaven is CC0; check others per asset), and record each license in the ledger.
7. Keep secrets out of logs, artifacts and commits.

## Tools

Scripts live in this skill's `scripts/` folder. Call them by path with `--project <project root>`, for example `python3 <skill-dir>/scripts/forge.py --project . status`. All are standard-library Python unless noted, and every one has `--help`.

| Script | Use |
| :--- | :--- |
| `forge.py` | `init`, `log`, `bar publish` / `bar diff`, `snapshot`, `manifest`, `status`, `build-id` |
| `validate_verdict.py` | gate every verdict before acting on it |
| `make_sxs.py` | round-over-round composites with optional blur, detail tiles and blind A/B (needs ffmpeg) |
| `make_workbench.py` | writes `artifacts/workbench.html`, a self-refreshing progress page |
| `blender_mcp_cli.py` | talks to a live Blender through the blender-mcp addon socket |
| `blender_turnaround.py` | headless turnaround strip and mesh stats (runs inside Blender) |
| `templates/capture.mjs` | Playwright capture for web stacks (Node; copied by `init`) |

## When tools are missing

- **No Blender**: build geometry procedurally in code or use licensed models; the bar judges the result, not the tool.
- **No Playwright**: use any capture route (the host's browser tool, the app's own screenshots), then `forge.py manifest`.
- **No ffmpeg**: skip composites; the critic grades stills directly and the workbench slider still compares rounds.
- **No Unity MCP**: use Unity batch-mode capture, or pick the web stack at plan time.
- **No scripts at all**: keep the same files and log lines by hand; the rules do not depend on the tooling.

## Resuming

Read `forge.json`, `BRIEF.md`, `art/BAR.md`, the latest verdict and `forge.py status`, then continue at the recorded round. Never restart setup or rewrite earlier history.

## References

- [references/visual-bar.md](references/visual-bar.md): writing criteria, the shared core, the ratchet, automatic FAIL signs.
- [references/criteria-packs.md](references/criteria-packs.md): 3D, web UI, data viz, 2D and interactive criteria starters, capture recipes, escalation levers.
- [references/critic-prompt.md](references/critic-prompt.md): the drop-in critic prompt and every verdict schema.
- [references/diagnoser-prompt.md](references/diagnoser-prompt.md): stuck-loop triggers, the escalation ladder, the Diagnoser prompt.
- [references/unity-and-blender-pipelines.md](references/unity-and-blender-pipelines.md): Blender MCP, headless Blender, web capture, Unity MCP.

## Credits

- **The Gauntlet Loop** by Matt Shumer ([somethingbig.ai/gauntlet-loop](https://somethingbig.ai/gauntlet-loop)): goal over implementation, a bar the agent cannot talk its way around, agent-chosen decomposition, a separate builder and fresh critic per piece, looping past the first decent result, a live progress page, and wave smoothing passes.
- **`game-builder` and `game-builder-blender-assets`** by Eric Zakariasson ([github.com/ericzakariasson/skills](https://github.com/ericzakariasson/skills), MIT License): the binary PASS/FAIL visual bar, critic verdict schemas and banned soft-pass phrases, the stuck-loop Diagnoser and escalation ladder, the `rounds.log` format, turnaround gates for authored assets, `Publish: LOCKED`, and the orchestrator's harsh read after a critic WIN. License text in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
- **blender-mcp** (Siddharth Ahuja) and **Unity MCP** (`com.unity.ai.assistant`) are separate projects this skill talks to; neither is bundled.
