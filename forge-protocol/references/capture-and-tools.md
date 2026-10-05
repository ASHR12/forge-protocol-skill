# Capture and your own tools

This skill bundles no code. The orchestrator and builders use what the environment already provides and write small tools only when they pay for themselves. This file says, for each job, when a tool is worth writing, what a good result looks like, and how to prove the tool works before you trust it.

## Rules for any tool you write

1. **Environment first.** Use the browser, screenshot, image, file and MCP tools you already have before writing anything.
2. **Smallest thing that works.** One job per tool, in whatever language the project already uses. Keep it in the project (for example under `tools/`), never in this skill.
3. **Verify before trusting.** Run it on a case where you already know the right answer, open its output yourself, and fix it before it touches a real round. Verify again after every change to it.
4. **Judgment wins.** A tool assists the orchestrator's reading and never overrides it. A false alarm or a miss is a bug in the tool, not a reason to change a grade.
5. **Record it.** List each tool and how you verified it in the tools table in `PLAN.md`.

## Capture discipline

- Capture the running build only: no mockups, design files or edited screenshots. Cropping and labeling are the only edits allowed.
- Re-capture every still every round. Fixes change every frame, so a partial re-capture is invalid.
- One still per must-have view or state at the size `BRIEF.md` names, and walkthrough frames across the main motion when there is motion.
- Pin what you can, so the same build captures the same way twice: viewport and pixel ratio, locale and time zone, random seeds, and time itself where the stack allows it.
- Wait until the build is actually ready (assets loaded, fonts in, first frames drawn) before you capture.
- Save the build's console or runtime errors from the capture next to the stills; C3 uses them.
- Name files `still-NN` and `frame-NN` so ids stay stable across rounds, and write `MANIFEST.md` with one build id for every still ([project-files.md](project-files.md)).

## Jobs

### Project files

No tool needed: create the files by hand from [project-files.md](project-files.md).
Good when: every file for the mode exists, `BRIEF.md` has no empty sections, `art/BAR.md` has no placeholder criteria, and `rounds.log` starts with an `INIT` line.

### Capture harness for web builds

Use first: the environment's browser or screenshot tool, if it can set the viewport and reach every view and state.
Write one when: you need many views, repeatable state or walkthrough frames. A short script on whatever browser automation library is installed is enough.
Good when it:
- sets a fixed viewport and pixel ratio;
- reaches each named view or state by URL, hash or a hook the build exposes, such as a ready flag and a set-view function;
- sets the debug mode and quality tier through the build's hooks, and names each variant (final, no-post, a diagnostic view, another tier) in `MANIFEST.md`;
- waits for the ready signal, and optionally pins time and seeds randomness;
- takes walkthrough frames at even intervals across the main motion;
- saves console errors, and writes `MANIFEST.md` with the build id and each image's real size;
- on Three.js builds, reads from the running page and records in `MANIFEST.md` the three.js revision, the backend (WebGPU, noting compatibility mode, or the WebGL 2 fallback), the adapter (vendor and architecture, hardware or software), the browser (headed or headless), the pixel ratio, the canvas size and the tier.
Verify: capture the same build twice and compare (same framing and state; animation timing within a frame); open every still and confirm it shows the view it claims; confirm the sizes match `BRIEF.md`. Prove each hook changes pixels: the no-post still differs from the final only where post-processing acts, and each debug mode and tier visibly changes the image. A hook that changes only a label is a bug.
Headless browsers may hide WebGPU (the build then falls back to WebGL 2 with only a console warning), render it in software, or capture a black canvas. If stills differ from a real browser, or the recorded backend or adapter is not the one `BRIEF.md` targets, use a GPU-backed or headed browser, and keep one route for every round. Timings from a software adapter are not performance evidence. Three.js specifics are in [threejs/validation.md](threejs/validation.md).

### Capture for engines and native apps

Use the engine's own render-to-image route: one camera render per view at the `BRIEF.md` size (an editor or batch script in Unity, a render script in Blender, the app's screenshot export or the OS capture for native apps). Engine specifics are in [pipelines.md](pipelines.md). The capture discipline and the checks above apply unchanged.

### Round comparisons (optional)

Use first: any image tool at hand (an image command-line tool, a graphics library, an HTML canvas).
Worth it when: rounds are close and you want to see what changed, or you want a blind A/B check.
Good when:
- stills are paired by id across two rounds, on canvases of the same size, each side labeled;
- an optional blurred pair, with the same blur on both sides, supports a glance read;
- optional detail crops at native scale show fine craft;
- for blind pairs, the sides are shuffled per pair and labeled A and B, and the key is kept in `artifacts/compare/keys/`, outside the critic's inputs.
Verify: open two pairs and confirm the right rounds and ids are paired and labeled; for blind pairs, decode one with the key.
Comparisons inform. They never decide a WIN: the critic grades the current captures against the bar.

### Progress page (optional deliverable)

Worth it when: the run is Standard or Forge, or the user wants to watch.
Good when: one local page shows the current stills, the latest grade per criterion, the bar version with its revision reasons, round history with links to the verdicts, budget used, and the next action. It loads images by relative path, works offline, and is refreshed or regenerated after every round. A markdown page is fine when HTML is overkill.
Verify: open it after a round and confirm it shows that round's stills and verdict.

### Verdict checks

The orchestrator checks every verdict by reading it against [Checking a verdict](critic-prompt.md#checking-a-verdict). On long runs a small checker can help: parsing the block, matching criterion ids against `BAR.md`, and matching cited ids against the stills folder.
Verify it on a known-good verdict and on known-bad ones: a missing criterion, an invented still id, a banned phrase, a grading score. Also confirm that it passes ordinary text: "impassable" is not "passable", a game's score counter or "40% complete" on a loader is not a grade, and a llama character is not a model name. Language checks are judgments of meaning; a word list only flags candidates for you to read.

### Build id

Use the commit id when the product files are clean, plus a marker or content hash when they have uncommitted changes; without version control, use a hash of the product files. Leave out the run files themselves (`BRIEF.md`, `PLAN.md`, the bar and ledger files, `artifacts/`) so logging never changes the id, but keep product assets in, wherever they live.
Verify: change one product file and confirm the id changes; append to `rounds.log` and confirm it does not.

### Budget and status

Read these from `rounds.log` and the saved verdicts after each round:
- rounds used: rounds closed by FAIL or WIN;
- minutes since `APPROVED`, or since the first event when no approval was needed;
- fail streaks per criterion since the last `DIAGNOSE-STEER`, and the RECAPTURE streak for the open round;
- whether the last two `CAPTURE` lines carry the same build id;
- whether a check-in is due.
Whatever computes this, you or a helper, spot-check it against the log by hand once.

### Blender: live session and turnarounds

See [pipelines.md](pipelines.md).
