---
name: forge-protocol
description: >-
  Builds polished demos, 3D scenes, browser games, simulations, web UIs and data viz, then loops captures
  of the running build past a fresh blind critic that grades every criterion PASS or FAIL against a bar
  derived from the user's goal. A lead agent plans behind a scaled approval gate, splits the work across
  builder subagents, runs capture, critic and punch-list rounds within explicit budgets, diagnoses stuck
  loops, and keeps publishing locked. Instruction-only: the agent uses its environment's tools and writes
  and verifies any small tool it needs. Covers 3D through Blender (live or headless) into Three.js/WebGPU
  or Unity. Use when the user wants a demo, scene, game, prototype or visual experience built to a high
  bar, asks to keep improving it until it is great, or starts a long autonomous build. Not for
  backend-only work or one-line fixes.
license: MIT
compatibility: >-
  Any agent environment. Works best with subagents or fresh sessions and an image-capable critic; without
  one, the user grades the visual criteria. Optional: browser automation, image tools, Blender, Unity.
metadata:
  version: "3.2.0"
---

# Forge Protocol: the goal-driven blind-critic loop

Turn a goal into a demo that holds up under a harsh, independent eye. You are the **Orchestrator**: you write a bar from the user's goal, split the work across builder subagents, and loop captures of the running build past a fresh critic that grades every criterion PASS or FAIL, until the bar is met, a budget runs out, or the user stops it. Working code is the floor, never the exit.

This skill is instructions only. Use the tools your environment already has. When a job needs more, write the smallest tool that does it and verify it before you trust it ([references/capture-and-tools.md](references/capture-and-tools.md)).

## When to use

- Visual or interactive deliverables: 3D worlds and scenes, browser games, physics sims, product demos, landing pages, dashboards and data viz, motion pieces.
- The user wants it great, not just working: "make it look amazing", "keep going until it's great", "forge this".
- Long autonomous runs that need budgets, check-ins and visible progress.

Skip it for backend-only changes, one-line fixes, or work with no visual or interactive output.

## Pick a mode

| | Sprint | Standard | Forge |
| :--- | :--- | :--- | :--- |
| Use for | a quick demo or one screen | a polished demo or small game | multi-hour worlds, games, showcase pieces |
| Plan gate | short plan, then start | plan, wait for a go | full plan, wait for a go |
| Default budget | 3 rounds, 30 min | 8 rounds, 2 h | 25 rounds, 8 h |
| Check-ins | at the end | every 3 rounds or 45 min | every 5 rounds or 90 min |
| Diagnose after | 2 straight fails of one criterion | 3 | 3 |
| Files | BRIEF, BAR | + PLAN | + LEDGER, asset turnarounds |

Pick from the request and say which mode and why in one line. These are defaults: the user's numbers always win ("spend at most 20 minutes"), and you may adjust them in the plan when the goal needs it. A budget of 0 means no limit; use it only when the user asks.

## Rule 0: plan before building

Before writing application code or spawning builders, reply with a plan sized to the mode:

1. **Goal and must-haves**: the goal in one sentence, and the must-haves the critic will check.
2. **The bar**: the criteria you will grade (see The bar).
3. **Tools, probed live**: what is actually available right now, with status and role: subagents or fresh sessions, image viewing for the critic, browser automation, image tools, Blender (installed, and live over MCP or not), engines. Probe; never assume.
4. **Pieces and roles**: what each builder makes and how each piece is judged; mode, budgets and check-in cadence.

Then:
- **Sprint**: start right away unless the request is ambiguous or risky.
- **Standard and Forge**: wait for an explicit go, unless the user already pre-approved ("go ahead", "no need to check with me", "just build it"). Log `APPROVED` with the user's words.
- In autonomous or goal-driven sessions, if the plan still needs approval, end the turn by saying plainly that you are waiting for the user's go.

If the user attached images, read them as part of the goal: intent, mood, must-haves. Never treat them as a pixel target, never keep them as a set to match, and never grade against them.

## Roles

| Role | Does | Never |
| :--- | :--- | :--- |
| Orchestrator (you) | plan, bar, decomposition, dispatch, verdict checks, logging, gates, harsh read, handoff | builds, or grades its own work |
| Builder | code, assets, captures, punch fixes; hands back paths and what was addressed | uses verdict words or claims quality |
| Critic | grades captures against `BRIEF.md` and `art/BAR.md`; returns one verdict block | sees builder chat, edits files, prescribes code |
| Diagnoser | root-causes a stuck loop and writes a steer | grades, edits, or softens the bar |

Spawn every critic and Diagnoser **fresh**, through whatever subagent or task mechanism your environment provides, giving it only the file paths its prompt lists. Without such a mechanism, use a fresh session that receives only those paths, and log `critic=fresh-session`.

**No image-capable critic?** Tell the user and offer them the critic role for the visual criteria. Show them the current stills and `art/BAR.md`, and record their PASS or FAIL for each criterion verbatim in the verdict file, marked `GRADER: user` ([references/critic-prompt.md](references/critic-prompt.md)). Never grade anything yourself. Report BLOCKED only if the user declines.

## The bar

- Write `art/BAR.md` from the goal and domain expertise ([references/visual-bar.md](references/visual-bar.md)). Research facts and techniques when they sharpen a criterion (how real caustics behave, plausible physics constants, type-scale ratios). State observable qualities; never grade against a reference image.
- Keep the shared core: **C1 Goal fit**, **C2 Live capture provenance**, **C3 State and motion integrity**. Add goal-specific criteria from C4 on, starting from [references/criteria-packs.md](references/criteria-packs.md). Each one is observable, binary and motivated by the goal. Use as many as one critic pass can check; most bars land between 4 and 10.
- The bar is a **versioned ratchet**:
  - Publish v1 before the first capture: set `BAR-VERSION: v1`, save a copy in `art/bar-history/`, and log `BAR-PUBLISH`.
  - Revise only **between rounds**, after the verdict is logged and before the next capture. Never mid-round.
  - Adding, raising or clarifying a criterion is fine; log every revision with its type, reason and diff.
  - Editing a criterion that failed last round needs a fresh critic audit (`SCOPE: bar`, BAR-OK) before the next capture.
  - Loosening or retiring a criterion needs the user's explicit approval, quoted in the log. Never lower the bar to rescue a failing build.
  - The critic always grades the current version.

## The loop

**Setup**: create the project files ([references/project-files.md](references/project-files.md)), fill `BRIEF.md` and `art/BAR.md`, publish bar v1, and set up a capture route for the stack ([references/capture-and-tools.md](references/capture-and-tools.md), [references/pipelines.md](references/pipelines.md)). Prove the capture route on the running build before round 1.

**Build**: split the work into the smallest pieces that can be built and judged separately, and dispatch independent pieces in parallel. Gate risky pieces cheaply before integration: a turnaround for each hero mesh, or a critic check with `SCOPE: gate`. After each wave, one smoothing pass harmonizes scale, light, color and type across the pieces.

**Each round R<n>**:
1. **Capture** the running build: one still per must-have view or state at the size `BRIEF.md` names, plus walkthrough frames when there is motion. Re-capture everything every round, write `MANIFEST.md`, and log `CAPTURE` with the build id and bar version.
2. **Record**: copy the round's stills and manifest to `artifacts/history/R<nn>/`. Refresh the optional comparisons and progress page if you keep them.
3. **Grade**: spawn a fresh critic with [references/critic-prompt.md](references/critic-prompt.md) and file paths only, or ask the user to grade when no image-capable critic exists (see Roles).
4. **Check the verdict** by reading it against the checklist in that reference. If it fails, re-run a fresh critic; never edit a verdict. Save accepted verdicts as `artifacts/verdicts/R<nn>.md` and log the result.
5. **Act**: RECAPTURE: fix the capture, same round. FAIL: builders fix the punch list verbatim, then the next round. WIN: go to Handoff.
6. **Report** one status line: `R<n> <FAIL|WIN|RECAPTURE|DIAGNOSE>: failing <ids|none>; punch <count>; rung <n|none>; budget <used>/<limit>; next: <action>`.

**Stuck loop**: when one criterion fails the mode's diagnose count of rounds in a row, two RECAPTUREs come back for the same round, or the build id did not change between rounds, log `DIAGNOSE-HOLD` and spawn a fresh Diagnoser ([references/diagnoser-prompt.md](references/diagnoser-prompt.md)). Builders then work from its steer.

**Budgets and stopping**: stop on a WIN confirmed by your harsh read, an exhausted budget, a user stop, or a hard blocker. Track rounds and time from `artifacts/rounds.log`. When a budget runs out, stop, report best-so-far honestly, and ask whether to extend (log `BUDGET-EXHAUSTED`, then `BUDGET-EXTENDED`). Check-ins are short, non-blocking progress notes at the mode cadence; keep working after them.

**Progress page (optional)**: on longer runs, keep a local page with the current stills, the latest grade per criterion, the bar version and the budget used, and give the user its path.

**Context**: keep the orchestrator lean. Pass file paths, not images or long logs, and let critics open the images.

## Handoff

A critic WIN is required but not enough:
1. **Harsh read**: open every current still yourself. Look for one coherent art system, consistent scale and perspective, coherent light, and nothing a viewer would call unfinished. If it fails, log `WIN-VOIDED`, tell the user once why, and continue rounds.
2. **Pre-handoff checks**: an accepted WIN on the current bar version; `MANIFEST.md` matches the delivered build; no `placeholder` rows in the ledger; every third-party asset licensed for this use; no secrets; the naming rule below holds.
3. **Report** what was built, how to run it, the final stills, rounds used, bar versions and open caveats. Publish stays LOCKED unless the user has unlocked it. Log `HANDOFF`.

## Non-negotiables

1. Builders never grade themselves. Every grade comes from a fresh critic with file inputs only, or from the user when no image-capable critic exists.
2. Each criterion gets PASS or FAIL, backed by cited evidence. No grading scores such as "8/10" or "B+"; numbers that belong to the build (a score counter, frame rate, resolution, progress bar) are evidence, not scores. Soft-pass language invalidates a verdict.
3. The bar only ratchets up unless the user explicitly approves otherwise.
4. Captures come from the live build, re-captured in full each round; no mockups or retouching.
5. Publish stays LOCKED until the user explicitly unlocks it; log `PUBLISH-UNLOCK`.
6. Ship only original work, or third-party assets whose license allows this use, and record each license in `art/LEDGER.md` (kept in any mode once third-party assets appear).
7. Keep secrets out of logs, artifacts and commits.
8. No AI vendor names, model family names or model version identifiers in plans, logs, verdicts, commits or shipped artifacts, unless `BRIEF.md` lists names the product itself must show. Ordinary words that happen to share a name (a llama character, a haiku) are not identifiers.

## Your own tools

Nothing here depends on bundled code. For each job, use what the environment provides first; build a small tool only when it saves real effort, and check it on a case with a known answer before trusting it. A tool never overrides your reading: when a checker flags something plainly fine, or misses something plainly wrong, your judgment wins and the tool gets fixed. [references/capture-and-tools.md](references/capture-and-tools.md) gives the acceptance checks for each job: project files, capture, round comparisons, the progress page, verdict checks, build ids and budget tracking. Blender and engine work is in [references/pipelines.md](references/pipelines.md).

When a tool is missing:
- **No Blender**: build geometry procedurally in code or use licensed models; the bar judges the result, not the tool.
- **No browser automation**: use any route that captures the live build (the environment's browser or screenshot tool, the app's own export), then write `MANIFEST.md` by hand.
- **No image tools**: skip comparison images; the critic grades the stills directly.
- **No engine integration**: use the engine's own batch or command-line render, or pick the web stack at plan time.

## Resuming

Read `BRIEF.md`, `art/BAR.md`, `artifacts/rounds.log` and the latest verdict, then continue at the recorded round. Never restart setup or rewrite earlier history.

## References

- [references/project-files.md](references/project-files.md): project layout, file skeletons, and the log, manifest and handback formats.
- [references/visual-bar.md](references/visual-bar.md): writing criteria, the shared core, the ratchet, automatic FAIL signs.
- [references/criteria-packs.md](references/criteria-packs.md): criteria starters, capture recipes and escalation levers for 3D, web UI, data viz, 2D and interactive work.
- [references/critic-prompt.md](references/critic-prompt.md): the drop-in critic prompt, every verdict format, the verdict check, and grading by the user.
- [references/diagnoser-prompt.md](references/diagnoser-prompt.md): stuck-loop triggers, the escalation ladder, the Diagnoser prompt.
- [references/capture-and-tools.md](references/capture-and-tools.md): capture discipline, and the tools you write and verify yourself.
- [references/pipelines.md](references/pipelines.md): picking a stack; Blender live or headless into Three.js/WebGPU or Unity.
- [references/threejs/router.md](references/threejs/router.md): read first on every Three.js build; routes the plan and each builder to the topic files its piece needs.
- [references/unity/router.md](references/unity/router.md): read first on every Unity build; routes the plan and each builder to the topic files its piece needs.

---

Inspired by Eric Zakariasson's [game-builder skills](https://github.com/ericzakariasson/skills) and Matt Shumer's [Gauntlet Loop](https://somethingbig.ai/gauntlet-loop).
