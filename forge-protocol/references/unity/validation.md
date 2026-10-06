# Unity validation: capture routes, proof, determinism, tests, provenance and diagnosis

API facts verified on Unity 6.6 (6000.6.4f1, 2026-10-06). Check the project's Unity version first (ProjectSettings/ProjectVersion.txt); if it differs, confirm in that version's official docs or the installed packages. The installed version wins.

Read when you write the bar and capture spec for a Unity build (orchestrator), build or prove the capture route and its hooks (builders), or root-cause a stuck loop (Diagnoser). The capture discipline in [../capture-and-tools.md](../capture-and-tools.md) still applies; this file adds what Unity builds need. Running Unity is in [agent-control.md](agent-control.md), and frame budgets are in [performance-and-builds.md](performance-and-builds.md).

## Contents

- From goal to Unity criteria
- The capture set by mode
- Capture routes
- Prove the route on a known answer
- The screenshot-fallback trap
- Overlay UI and Play mode
- Determinism and a fresh process
- Walkthrough frames and video
- Tests from the command line
- Console discipline
- Performance evidence
- Build smoke tests
- Capture provenance
- Tells of an unfinished Unity build
- Symptom → cause

## From goal to Unity criteria

**Goal.** Every Unity criterion comes from the goal and can be judged from the captures alone.

**Build.**
1. Pull critic-check starters from the topic files `PLAN.md` names, keep only those the goal motivates, and rewrite each into `art/BAR.md` as one observable PASS line with FAIL signs ([../visual-bar.md](../visual-bar.md)).
2. Give each primary hero subject a camera envelope: a near view for craft, a design view for the hero shot and a far view for silhouette. Store them as named camera bookmarks in the capture hooks ([router.md](router.md), Contracts builders share) and list them under Captures in `BRIEF.md`.
3. For games, turn rules into observable states reached by scripted input, such as "after the scripted jump, the player stands on the second ledge" or "after three hits, the enemy plays its defeat and the score reads 300".
4. When the build uses post-processing, add a "Form without post" criterion graded on the no-post stills.
5. Never write "matches the reference" or any criterion that grades against a picture.

## The capture set by mode

**Goal.** Each mode captures enough to grade every criterion, and nothing it doesn't need.

**Build.** Capture through the build's hooks with these defaults; decide the exact views from the goal and record them in `BRIEF.md`.

| Capture | Sprint | Standard | Forge |
| --- | --- | --- | --- |
| Final still of every must-have view or state | yes | yes | yes |
| No-post still of every hero view (when the build uses post-processing: same camera, time and quality level; effects off, tone mapping and exposure kept through the tonemapping-only profile) | when post is used | when post is used | when post is used |
| Near, design and far views of each primary hero subject | no | yes | yes |
| Walkthrough frames across the main motion | when there is motion | when there is motion | when there is motion |
| Temporal checkpoints: reset, first response, steady state, a sudden reveal and the recovery | no | when motion is a must-have | yes |
| One stress still: grazing light, another seed, an extreme parameter or the lowest quality level | no | yes | yes |
| Diagnostic stills | only when a criterion needs one | same | same |

Name each variant in the view column of `MANIFEST.md` ([../project-files.md](../project-files.md)): `hero`, `hero no-post`, `hero near`, `hero far`, `hero stress:grazing`, `hero diag:normals`, and the quality level when a still was taken at another one.

**Watch for.**
- URP's tone mapping is an override inside the post-processing stack, so switching the camera's post-processing off drops tone mapping too, and that still is not the no-post still. The no-post variant keeps the final's tone mapper and exposure, and turns off every effect override and every renderer feature that acts as post. [final-image.md](final-image.md) builds that debug profile; this file decides when to capture it.
- A project made from the 3D URP template already uses post-processing: its camera has Post Processing on, and both URP assets apply a profile with Neutral tone mapping, bloom and a vignette to every scene. The no-post still applies unless the plan removes them ([final-image.md](final-image.md)).
- The escalation guard: post-processing is tuned only after the no-post still passes, and a no-post failure sends punch items to geometry, materials or light, never to post.

## Capture routes

**Goal.** Every still is the live build's rendered frame at the `BRIEF.md` size, reached through one route that stays the same for every round.

**Choose.**
- **A built player with a screen capture**, the default route: a Mac player, windowed at the capture size with Run In Background on, launched fresh for each round. A capture script inside the game visits each named view and state, waits for its ready signal and saves the final frame. It is closest to what ships, and every round starts clean.
- **The Editor in Play mode with a screen capture:** the same capture script in a windowed Editor, either launched without `-batchmode` or driven through the live route's screen-source capture. It iterates faster but carries Editor state, so set the Game view to a fixed resolution equal to the capture size.
- **A camera render to a texture**, in Edit mode or batch mode: render the camera stack into a render texture through URP's render request, read it back and encode a PNG. It works without Play mode and leaves out overlay UI. Batch-mode rendering must pass the known-answer proof on this machine first.
- **A Web player in a browser:** serve the build locally and capture it with the browser route in [../capture-and-tools.md](../capture-and-tools.md). The build can expose its view switch to the page.
- **The live route's capture command:** its camera source leaves out overlay UI, and its screen source works only in Play mode.

**Build.** Write the route into the tools table of `PLAN.md`, record it in the provenance line, and keep it for every round.

**Watch for.**
- Captures need a graphics device: never pass `-nographics` to a run that captures.
- A Web build with WebGPU enabled can't use synchronous screen capture; take browser-level screenshots, or capture into a render texture and read it back asynchronously.

**API facts** (check the installed version):
- `ScreenCapture.CaptureScreenshot` saves the final frame shown to the user, with every camera's output combined, and in the Editor resolves a relative path from the project folder (verified on 6000.6).
- `RenderPipeline.SubmitRenderRequest` with a `StandardRequest` renders a base camera's full stack to a target outside the render loop, and URP also accepts `UniversalRenderPipeline.SingleCameraRequest` for a single camera (verified on 6000.6).
- On WebGPU, `ScreenCapture.CaptureScreenshot` and `CaptureScreenshotAsTexture` don't work; use `CaptureScreenshotIntoRenderTexture` with `AsyncGPUReadback` (verified on 6000.6).

## Prove the route on a known answer

**Goal.** Before round 1, the route is shown to produce the right pixels, size and state on a scene whose correct image is known in advance.

**Build.**
1. Add a known-answer test scene: a camera clearing to one flat color, an unlit object of a second color at a known screen position, and, when the build has overlay UI, one overlay label.
2. Capture it through the chosen route, with post-processing off. A small checker reads the pixels: the background and object colors within a small tolerance, the object where it should be, the label present when the route should include it, and the image size equal to the `BRIEF.md` size.
3. Capture it twice in two fresh processes: the stills match.
4. Prove each hook on the real build: final and no-post differ only by the effects (when post is used); every debug view differs visibly from the final; a lower quality level changes both pixels and metrics; reset returns the first state.
5. Treat batch-mode rendering on this Mac as unproven until this test passes there. The Recorder's documentation says batch mode doesn't start the graphics pipeline for recording, while the Manual describes `-nographics` as the flag that skips the graphics device. If the batch proof fails, use the built player or a windowed Editor.
6. Record each proof in the tools table of `PLAN.md`.

**Watch for.** A check that passes on a stale file. Delete the output before capturing, and confirm the new file's time and size.

**API facts** (check the installed version):
- `-nographics` starts Unity without a graphics device, which batch runs that render or bake must not use (verified on 6000.6).

## The screenshot-fallback trap

**Goal.** No still in a round is a picture of the desktop, of another window, or a file left over from an earlier round.

**Build.**
1. The CLI's MCP-mode capture tools fall back to a screenshot of the whole desktop when the Editor is too slow to reply or a dialog blocks it, and they say so in a note attached to the result. Read that note on every capture, and treat any fallback as a RECAPTURE.
2. Have the game's capture script log one line per still: file, view, size, frame number and time. Accept a still only when its log line exists.
3. Check every still's size against `BRIEF.md`; a desktop screenshot has the display's size and shows the menu bar or the Dock.
4. Clear the stills folder before each round, so a failed capture can't leave an old file that passes as new.

**Watch for.** A frozen frame: a player that lost focus with Run In Background off keeps showing its last frame, so every still matches the previous one.

## Overlay UI and Play mode

**Goal.** Stills that should show the UI show it, and no criterion depends on the capture route by accident.

**Build.**
1. UI drawn straight to the screen (overlay canvases, and UI Toolkit panels that render to the screen) exists only at runtime and never passes through a camera. Camera renders and camera-source captures leave it out; screen captures in Play mode or in a player include it.
2. Grade HUD and menu criteria only on screen captures from Play mode or a player.
3. When a hero still must show the world without the HUD, hide the HUD through the build's hook, not by switching routes.
4. Canvases in camera space or world space render through a camera, so they appear in camera renders as well.

**API facts** (check the installed version):
- The Recorder's `RecorderController` throws when `PrepareRecording` or `StartRecording` is called outside Play mode (verified on 6000.6).

## Determinism and a fresh process

**Goal.** The same build captures the same way twice.

**Build.**
1. **A fresh process per round:** launch the player, or a batch run, from scratch for each round's captures. In the live Editor, domain reload is off by default (and the 3D URP template skips the scene reload too), so state from earlier Play sessions leaks into the next. Use the Editor only if the game resets its static state on entering Play mode ([foundation.md](foundation.md)), and prove it by capturing one state twice in a row.
2. **Capture time:** set `Time.captureDeltaTime` so game time advances by a fixed step per frame whatever the real frame time. It doesn't touch unscaled time, so anything animated on unscaled time (UI tweens, camera smoothing) needs the game's own capture clock.
3. **Physics:** keep the fixed timestep constant (the templates use 0.02 s); with a fixed capture step, the physics steps per frame repeat exactly.
4. **Seeds:** one seed source for every visible random choice, passed as a command-line argument and recorded.
5. **Pin the rest:** the quality level, the window size, the graphics API, the camera bookmark, the build profile, and any Timeline, set to its named keyframe with its director's Update Method on Manual ([camera-and-animation.md](camera-and-animation.md), Timeline for cutscenes).
6. **Warm-up:** after the build's ready signal (scene loaded, async loads done, shaders warmed), render warm-up frames before any temporal capture, because temporal anti-aliasing and upscaling need history.
7. **Prove it:** the same view in two fresh processes gives matching stills, and the frame-rate pair (one scripted move at two capture steps, compared at the same game time) shows the same pose.

**Start here** (adjust to the goal): a capture step of 1/60 s, and 60 warm-up frames after the ready signal.

**API facts** (check the installed version):
- A non-zero `Time.captureDeltaTime` advances `Time.time` by that step, times `timeScale`, every frame regardless of real time, and leaves `Time.unscaledTime` alone (verified on 6000.6).
- `Time.captureFramerate` is the rounded reciprocal of `Time.captureDeltaTime`, and setting either sets the other (verified on 6000.6).
- Desktop players accept `-screen-fullscreen 0`, `-screen-width`, `-screen-height` and `-screen-quality <quality level name>` on the command line; these arguments don't apply to Web players (verified on 6000.6).

## Walkthrough frames and video

**Goal.** Motion evidence comes from frames at a fixed step, and video exists only where the brief wants it.

**Build.**
1. Walkthrough frames: the capture script plays a scripted path (a sequence of bookmarks, or recorded input) at the capture step and saves `frame-NN` at even intervals. It works in a player and in Play mode.
2. Video: the Recorder package (bundled with 6000.6) records the Game view or a camera to a movie or an image sequence, in Play mode only. Use a constant frame rate with the cap enabled. To record from the command line, launch a windowed Editor, without `-batchmode`, with an `-executeMethod` entry that starts Play mode, captures a range of frames, then quits.
3. Give critics frames, not video: they grade stills. Video is for the user.

**API facts** (check the installed version):
- The Recorder doesn't work when the Editor runs with `-batchmode`: the recording never starts (verified on 6000.6).
- The Recorder's constant frame-rate mode records at a target rate and can cap the Game view to it (verified on 6000.6).

## Tests from the command line

**Goal.** Rules and setup steps are proven by tests that run unattended, and results are read from the report.

**Build.**
1. EditMode tests check what setup scripts promise (the scene has its objects, prefabs have their components), validate data and test pure logic.
2. PlayMode tests check gameplay rules after scripted input, with a fixed capture step and a fixed seed.
3. Run them in batch mode with `-runTests`, `-testPlatform EditMode` or `PlayMode`, `-testResults <path>` and `-logFile`, and without `-quit`. The CLI's `unity test` does the same and exits with 8 when tests failed, or 6 when the run didn't finish.
4. Read the NUnit XML report for counts and each failure's message, not the Editor's exit code.
5. Narrow runs with `-testFilter` or `-testCategory`. A flaky test is a determinism bug to fix, never something to retry away.
6. Tests support C3 and gameplay criteria with evidence; they never replace the critic's visual grade.

**API facts** (check the installed version):
- `-runTests` runs the project's tests, `-testPlatform` takes `EditMode` (the default), `PlayMode` or a build target, and `-testResults` writes an NUnit XML file, by default in the project root (verified on 6000.6).
- `-quit` isn't supported while tests run, and Unity components report no common exit codes under test, so the report and the log are the evidence (verified on 6000.6).

## Console discipline

**Goal.** A capture round starts only from a clean log, and every message in it has been read.

**Build.**
1. Collect the whole log from process start (the player log or the run's Editor log) and save it with the stills; C3 uses it.
2. Fix these before capturing, never silence them: errors and exceptions; compiler errors; warnings that say obsolete, deprecated or removed; shader compile errors; missing-script warnings; Input System exceptions; missing render pipeline or package messages.
3. Record in `PLAN.md` any third-party warning that can't be fixed, and keep it visible.
4. Have the build hook the log, count errors and warnings, write them next to the stills and show the count in its debug overlay.
5. Then check what logs nothing: magenta error-shader materials, Built-in shaders left in a URP project, a quality level with no pipeline asset, serialized references left empty, statics carried over from a previous session, a scripted scene whose lighting was never baked (new projects never bake on scene load; [lighting-and-shadows.md](lighting-and-shadows.md)), the wrong quality level or graphics API, and a frozen frame.
6. Before diagnosing from pixels, correlate one more channel: the log, the scene contents (an EditMode test or the live route) or the build report.

**API facts** (check the installed version):
- `Application.logMessageReceivedThreaded` fires for every log message on any thread, while `Application.logMessageReceived` fires on the main thread only (verified on 6000.6).
- When a project with a Scriptable Render Pipeline opens despite compile errors, the pipeline may fail to load and objects show the error shader (verified on 6000.6).

## Performance evidence

**Goal.** Frame-time claims come from the build's own measurements, on the target, after warm-up.

**Build.**
1. Measure in a player at the capture size and quality level, after warm-up, over the fixed-step walkthrough: a development build for the Profiler and the Frame Debugger, and a release build for the final numbers. In 6.6, give the development build Managed Code Variant Checked: the default Release variant leaves out URP's per-pass markers, the Rendering Debugger and URP's Frame Debugger support ([performance-and-builds.md](performance-and-builds.md), Reading the profiler).
2. Expose the numbers in the build's metrics readout: frame time, CPU and GPU time, draw calls and batches, triangles and memory, read through `ProfilerRecorder` and `FrameTimingManager`. A frame-budget criterion is graded from that readout in the captures.
3. Stream a Profiler capture from a player to a file with `-profiler-enable`, `-profiler-log-file` and `-profiler-capture-frame-count`.
4. Use the Frame Debugger to see draw order and passes, attached to a development player.
5. Run Project Auditor (built into 6.6) from batch mode and keep its report with the round.
6. Never quote Editor Play-mode timings as player timings; Web timings come from the browser. Budgets and fixes are in [performance-and-builds.md](performance-and-builds.md).

**API facts** (check the installed version):
- `ProfilerRecorder` reads Profiler counters and marker timings in the Editor and in players, including release players (verified on 6000.6).
- `FrameTimingManager` gives CPU and GPU frame times; it is always active in development builds, and release builds need Frame Timing Stats enabled in Player settings (verified on 6000.6).
- The Frame Debugger attaches to a built player only when it is a development build and, on desktop, runs in the background (verified on 6000.6).
- `-profiler-log-file` streams Profiler data to a `.raw` file from startup, and `-profiler-capture-frame-count` sets how many frames a player captures (verified on 6000.6).

## Build smoke tests

**Goal.** The shipped artifact starts, reaches every must-have state and exits cleanly, with nobody watching.

**Build.**
1. After each build, launch the player from the command line in a window at the `BRIEF.md` size, with a fresh `-logFile`, the quality level named, and a project argument that turns on capture mode.
2. In capture mode the game waits for its ready signal, visits each view and state, saves the stills, writes the provenance line, and quits with a non-zero exit code on any error.
3. PASS when the process exits with 0 within its time limit, the log holds no errors, every expected still exists at the right size, and the provenance line is present.
4. For the Web target, serve the build locally, open it through the browser route, and read the browser console as its log.
5. Wait for the ready signal, never a fixed delay: the templates show a splash screen before the first scene. Time any in-game wait or watchdog on the game's clock, an Awaitable or a coroutine: on the Web, `System.Threading` timers and token timeouts never fire ([foundation.md](foundation.md), Async code).

**API facts** (check the installed version):
- `Application.Quit` takes an optional exit code that the player returns on Mac, Windows and Linux; it is ignored in the Editor, and on the Web it stops the player without closing the page (verified on 6000.6).

## Capture provenance

**Goal.** Every still traces back to the exact build, editor, pipeline, device and capture settings that made it.

**Build.** The capture script writes one provenance line to the log at capture time, and the capture tool copies it above the `MANIFEST.md` table ([../project-files.md](../project-files.md)) for each round. It records:
- the Unity version and changeset (version from `Application.unityVersion`, changeset from the probe);
- the render pipeline and its asset (`GraphicsSettings.currentRenderPipeline`);
- the graphics API and GPU (`SystemInfo.graphicsDeviceType`, `SystemInfo.graphicsDeviceName`);
- the quality level, the target and the build profile;
- Editor or player, and Play or Edit mode;
- the capture source (screen, camera render or browser) and the size;
- the time step and the seed, and whether the capture ran in a fresh process.

A still captured on another route, quality level, graphics API or target than `BRIEF.md` names fails a C2 that requires them: fix the route and capture again before grading. For the build id, the product files are `Assets/`, `Packages/` and `ProjectSettings/`; leave out `Library/`, `Temp/`, `Logs/`, `UserSettings/`, built players and the Forge run files ([../capture-and-tools.md](../capture-and-tools.md), Build id).

**API facts** (check the installed version):
- `SystemInfo.graphicsDeviceType` reports the graphics API in use and `SystemInfo.graphicsDeviceName` the GPU's name as its driver reports it (verified on 6000.6).
- `GraphicsSettings.currentRenderPipeline` returns the asset in use: the current quality level's override (`QualitySettings.renderPipeline`) when it has one, otherwise `GraphicsSettings.defaultRenderPipeline`, where null means Built-in (verified on 6000.6).

## Tells of an unfinished Unity build

**Goal.** The orchestrator's harsh read catches what a passing critic can still miss.

**Build.** Before handoff, look for each of these in the current stills; each is a reason to log `WIN-VOIDED`, unless the brief asks for it:
- the template's sample scene, default skybox or a bare gray ground plane;
- primitive stand-ins, or default gray, white or magenta materials;
- a flat, washed-out frame with no tone mapping, or bloom on everything;
- floating objects, missing contact shadows, or shimmering shadow edges;
- a default font or unstyled UI, UI cut off at the capture size, or UI covering the focal subject;
- the splash screen, a loading frame, a development-build label or a debug overlay in a final still;
- a camera that clips into walls, or jitters while following;
- characters sliding on the ground, or bodies jittering at rest;
- errors in the log, or a route, quality level or graphics API different from the brief's.

## Symptom → cause

The Diagnoser's cross-system table. The file named in each first check has its own table with more detail.

| Symptom | Likely cause | First check |
| --- | --- | --- |
| Black, gray or blank capture | `-nographics`, unproven batch rendering, or a capture before the first frame | the known-answer proof (this file) |
| A still shows the desktop or another window | the MCP capture fallback after a timeout or a dialog | the note returned with the capture (this file) |
| The HUD is missing from stills | a camera-source capture of overlay UI | the capture source in provenance (this file) |
| Still size differs from the brief | a free-aspect Game view, or a full-screen player | the window size, Game view resolution and player arguments (this file) |
| Rounds differ with no code change | statics from earlier Play sessions, unpinned time or seed, no fresh process | the same state captured in two fresh processes (this file) |
| Every still matches the previous one | a frozen frame from a player that lost focus | Run In Background ([setup.md](setup.md)) |
| Motion speed differs between captures | real frame time instead of a fixed capture step, or unscaled time | the capture step and the clock ([foundation.md](foundation.md)) |
| The same criterion fails after many tuning rounds | tuning around a core step never checked on a known input | that step alone on a known input (this file) |
| Everything is magenta | non-URP shaders, or no pipeline asset on the quality level | the quality level's pipeline asset ([foundation.md](foundation.md), [materials-and-shaders.md](materials-and-shaders.md)) |
| A flat, gray or washed-out frame | no tone mapping, post-processing off on the camera, or a volume the camera ignores | the output owner ([final-image.md](final-image.md)) |
| The no-post still is identical to the final | the debug profile isn't wired to the camera | final and no-post at one bookmark ([final-image.md](final-image.md)) |
| The no-post still differs from the final in overall brightness or contrast | the debug profile's tone mapper or exposure doesn't match the owner's, or tone mapping was dropped with the effects | the tonemapping-only profile against the owner profile ([final-image.md](final-image.md)) |
| A new sky with old ambient light and reflections | environment lighting not regenerated | the lighting bake state ([lighting-and-shadows.md](lighting-and-shadows.md)) |
| Shadows shimmer, show acne or detach | cascade and bias settings | a slow pan pair ([lighting-and-shadows.md](lighting-and-shadows.md)) |
| Low frame rate, many draw calls | batching, instancing or culling not working | the metrics readout ([performance-and-builds.md](performance-and-builds.md)) |
| The Web build looks or runs differently from the Mac build | a compute feature without its WebGL 2 fallback | the graphics API in provenance ([performance-and-builds.md](performance-and-builds.md)) |
| A model at the wrong scale or orientation, or with dark normals | import settings | the model's import settings ([assets-and-import.md](assets-and-import.md)) |
| Visible tiling or flat surfaces | one texture scale, no detail or variation | a high top-down still ([materials-and-shaders.md](materials-and-shaders.md)) |
| Blockout pieces in a final still | levels never dressed | the level's kit and prefab list ([levels-and-geometry.md](levels-and-geometry.md)) |
| Terrain seams, tiling or popping vegetation | terrain layers and detail settings | a grazing-angle still ([terrain-and-nature.md](terrain-and-nature.md)) |
| Plastic water, or a sky that disagrees with the light | separate sun or weather sources | the sky and water setup ([sky-weather-and-water.md](sky-weather-and-water.md)) |
| Effects appear from nowhere, or read only with bloom | no spawn cause; glow standing in for form | the effect with bloom off ([effects.md](effects.md)) |
| The camera clips, snaps or jitters | camera rig and damping | which systems move the camera ([camera-and-animation.md](camera-and-animation.md)) |
| Characters slide, float or tunnel | controller and physics settings | the collider debug view over frames ([characters-physics-and-feel.md](characters-physics-and-feel.md)) |
| Input does nothing, or throws | input handling setting or actions not enabled | the input setup ([input-ui-and-audio.md](input-ui-and-audio.md)) |
| Blurry or shimmering pixel art | sprite import and camera settings | a native-size crop ([2d.md](2d.md)) |
| A setup script's result is missing from the capture | the scene was never saved, or was captured before the import finished | the save calls ([project-hygiene.md](project-hygiene.md)) |
| Tests pass in the Editor but fail in the player | editor-only code paths, or leftover static state | the assembly setup and the Play mode settings ([project-hygiene.md](project-hygiene.md), [foundation.md](foundation.md)) |
