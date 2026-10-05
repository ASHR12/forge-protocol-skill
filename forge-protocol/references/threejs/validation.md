# Three.js validation: captures, provenance and diagnosis

API facts verified on r186 (2026-10-05). Check the installed version first; if it differs, confirm in the official docs or the installed source. The installed version wins.

Read this when you write the bar and capture spec for a Three.js build (orchestrator), expose or prove capture hooks (builders), or root-cause a stuck loop (Diagnoser). The capture discipline in [../capture-and-tools.md](../capture-and-tools.md) still applies; this file adds what Three.js builds need.

## Contents

- From goal to Three.js criteria
- The capture set by mode
- Realism capture recipes
- Diagnostic views by system
- Proving the hooks
- Determinism, warm-up and noisy content
- Motion and temporal evidence
- Capture provenance
- Headless and WebGPU capture traps
- Silent failures and console discipline
- Performance evidence
- Tells of an unfinished Three.js build
- Symptom → cause

## From goal to Three.js criteria

**Build.**
1. Pull critic-check starters from the topic files `PLAN.md` names, keep only those the goal motivates, and rewrite each into `art/BAR.md` as one observable PASS line with FAIL signs ([../visual-bar.md](../visual-bar.md)).
2. Give each hero subject a camera envelope: a near view for craft, a design view for the hero shot, and a far view for silhouette and distance. Name them as camera bookmarks and list them under Captures in `BRIEF.md`.
3. Turn the look's invariants into observables, for example "the subject's rim light is visible in the no-post still", "the horizon shows no mesh edge", "roots stay planted in the strongest gust", "shadow edges hold still while the camera moves".
4. When the build has post-processing, add a "Form without post" criterion graded on the no-post stills.
5. Never write "matches the reference" or any criterion that grades against a picture.

## The capture set by mode

**Build.** Capture through the build's hooks ([foundation.md](foundation.md)), with these defaults; decide the exact views from the goal and record them in `BRIEF.md`.

| Capture | Sprint | Standard | Forge |
| --- | --- | --- | --- |
| Final still of every must-have view or state | yes | yes | yes |
| No-post still of every hero view (same camera, time and tier; effect passes off, tone mapping and display output kept) | yes | yes | yes |
| Near, design and far views of each hero subject | no | yes | yes |
| Walkthrough frames across the main motion | when there is motion | when there is motion | when there is motion |
| Temporal checkpoints (below) | no | when motion is a must-have | yes |
| One stress still: grazing light, another seed, an extreme parameter or the lowest tier | no | yes | yes |
| Diagnostic stills | only when a criterion needs one | same | same |

Name each variant after its view in the view column of `MANIFEST.md` ([../project-files.md](../project-files.md)): `hero`, `hero no-post`, `hero near`, `hero far`, `hero stress:grazing`, `hero diag:normals`, and the tier when a still was taken at a different one.

**Watch for.** The escalation guard: post-processing is tuned only after the no-post still passes. When a no-post still fails a form, material or light criterion, the punch items go to geometry, materials or light, never to post ([final-image.md](final-image.md)).

## Realism capture recipes

**Build.** Use the recipes the bar's criteria need; each names its camera and light so it can repeat exactly.

| Recipe | Camera and light | What it reveals |
| --- | --- | --- |
| Hero | the design bookmark, final and no-post | goal fit, form, material separation, focal point |
| Grazing-angle terrain | 1.5 to 2 m above the ground, looking along it, with a low sun | texture filtering, relief, LOD cracks, shadow acne, grounding |
| Sun-facing and sun-behind vegetation | the same patch, once looking toward the sun and once away | back-light translucency, glints, shadow shape |
| Shoreline | low, looking along the water's edge | depth color, the shore band, foam, hard intersection lines |
| Horizon | level or slightly raised, looking at the far edge | mesh edges, fog against sky, aerial perspective, far tiling and LOD |
| Top-down tiling check | high, looking down on the largest surfaces | repetition, macro variation, seams between layers |
| Fixed-step walkthrough | a scripted path at a fixed time step, frames at even intervals | pops, shimmer, crawling shadows, LOD swaps, temporal ghosting |
| Distance sweep | one subject at several stops along one ray | identity across detail levels, filtering, haze |
| Frame-rate pair | one scripted move rendered at two fixed steps, compared at the same time | motion that depends on frame rate |

**Watch for.** Orbiting by hand until a view "looks close" invalidates comparison; use bookmarks. An isolated subject on a black background hides edge contrast, depth, ground contact and scale, so stage it in context.

**Start here** (adjust to the goal): 16 walkthrough frames along the scripted path, and three to five stops in a distance sweep.

## Diagnostic views by system

**Build.** Request a `diag:` still only when a criterion or a Diagnoser steer needs it, and expose it through the debug-mode hook.

| System | Views that prove it |
| --- | --- |
| Materials | clay (one gray material), roughness only, normals, base color only, grazing light |
| Procedural fields | each named field as color |
| Geometry | wireframe, normals, flat-shaded clay, silhouette against a plain backdrop |
| Shadows | shadow only, cascades tinted by level, a slow pan pair |
| AO and GI | AO only, GI only, the frame with each off |
| Bloom | bloom off, bloom contribution only |
| Temporal AA and motion | the velocity buffer during motion |
| Terrain and LOD | wireframe at an LOD border, detail levels tinted by level |
| Vegetation | clump or patch ids, the wind field, the far tier alone |
| Water | thickness, displacement only, foam state over several frames |
| Clouds and volumes | density without detail, sun transmittance, step-count heat map |
| Particles | overdraw heat map, spawn points |
| Performance | the build's metrics overlay ([assets-and-performance.md](assets-and-performance.md)) |

## Proving the hooks

**Build.** Before round 1, prove each hook on the running build:
1. Capture final and no-post at one bookmark: they differ only by post-processing.
2. Capture every debug view the bar needs: each differs visibly from the final.
3. Switch the tier down: metrics and pixels both change.
4. Set the same time twice and capture: the stills match.
5. Reset after interacting: the state returns to the first capture.

**Watch for.** A hook that changes a label but not the pixels counts as missing, and the capture tool must not proceed on it.

## Determinism, warm-up and noisy content

**Build.**
1. Freeze the seed, the time, the camera (from a bookmark, with field of view, near and far), the viewport and pixel ratio, the tier, the backend and the asset versions.
2. After the ready flag, render warm-up frames before capturing anything temporal: TRAA and TAAU, SSGI, temporal denoisers, exposure adaptation, cloud reconstruction. Paused time still needs warm-up frames, because the temporal jitter keeps running.
3. For stochastic pixels (particles, sparkle, noisy volumes), seed the sequence by frame index or capture the converged result. Never loosen a criterion because the pixels are noisy.
4. Pin exposure, or wait until it settles.

**Start here** (adjust to the goal): 60 warm-up frames after the ready flag, or more until the exposure readout stops changing.

## Motion and temporal evidence

**Build.**
- Capture checkpoints: the reset state, the first response to an input or event, steady state, a sudden reveal (a cut, a teleport, an object moving out of the way), and the recovery after it.
- Watch the walkthrough at normal speed and frame by frame, because a single still can't rule out shimmer, swimming, stale history or pops.
- For the frame-rate pair, render one scripted move at two fixed steps (for example 1/30 s and 1/60 s) and compare the pose at the same time.
- For shimmer, compare crops of hero surfaces and shadow edges across three or more consecutive frames of a slow pan.

**Critic checks.** PASS when walkthrough frames show no pops, shimmer, crawling shadows or ghost trails, motion ends in settled poses, and the two stills of a frame-rate pair show the same pose. FAIL signs: an object or shadow that jumps between consecutive frames; trails behind moving things; poses that differ between the frame-rate pair; motion still drifting after it should have stopped.

## Capture provenance

**Build.** Read these from the running page and record them in the provenance line above the `MANIFEST.md` table ([../project-files.md](../project-files.md)) for each round:
- the three.js revision, read from `REVISION` at runtime;
- the renderer and backend (WebGPU or the WebGL 2 fallback), and WebGPU compatibility mode;
- the adapter's vendor and architecture, marked hardware or software (SwiftShader, llvmpipe and similar);
- the browser and its version, headed or headless;
- the pixel ratio, the canvas size in CSS and device pixels, and the tier.

A WebGPU build captured on the fallback, or on a software adapter, doesn't meet a C2 that requires the target backend, so fix the route and capture again before grading. Software adapters can give correct images, but their timings are never evidence.

## Headless and WebGPU capture traps

**Build.** Detect instead of assuming: after the ready flag, read the backend and adapter through the build's hook, and fix the route before capturing if they differ from the target in `BRIEF.md`.

**Watch for.**
- WebGPU needs a secure context: `https` or `localhost`.
- `navigator.gpu` can exist with no adapter behind it, and three.js then falls back with a single warning.
- Dated note (October 2026): headless Chromium hides WebGPU unless started with an unsafe-WebGPU flag, and on Windows and Linux headless captures of WebGPU canvases can come out black or unsupported, while a headed browser (on a virtual display on Linux) avoids both.
- Machines without GPU acceleration (many CI runners and virtual machines) get a software adapter: slow, and unfit for timings.
- Read pixels with browser-level screenshots, not by reading back the canvas: the WebGL drawing buffer is cleared after compositing.
- Keep one route for every round ([../capture-and-tools.md](../capture-and-tools.md)).

**API facts** (check the installed version):
- `WebGLRenderer`'s `preserveDrawingBuffer` defaults to false, so canvas readback outside the frame returns a cleared image (verified on r186).
- `renderer.backend.isWebGPUBackend` and `renderer.backend.compatibilityMode` give the backend facts for provenance (verified on r186).

## Silent failures and console discipline

**Build.**
1. Collect the browser console from page load, not just around the capture: three.js prints many deprecation warnings only once.
2. Treat as build failures, fixed before capture: any warning that says deprecated, renamed or removed (some add-ons print without the `THREE.` prefix, so match the words); "WebGPU is not available, running under WebGL2 backend" when the brief targets WebGPU; "Multiple instances of Three.js"; shader compile errors; uncaptured GPU errors. Fix each by migrating, never by silencing it.
3. Then check what prints nothing at all. Read the code, or capture a diagnostic still, for each:
   - a color map left untagged, a data map tagged sRGB, or a hex color converted twice ([foundation.md](foundation.md));
   - an assignment to `encoding` or `outputEncoding`, which no longer exist;
   - `NoToneMapping` left on an HDR scene, or tone mapping applied twice;
   - `material.toneMapped = false` under `WebGPURenderer`, where it does nothing;
   - timestamp tracking switched off on an adapter without `timestamp-query`, so GPU time reads zero;
   - MSAA switched off by compatibility mode;
   - `renderer.shadowMap.enabled` left false, or `castShadow` missing on casters;
   - `matrixAutoUpdate` off without `matrixWorldNeedsUpdate`, so objects freeze;
   - vertex-displaced surfaces missing from the velocity buffer, so temporal AA ghosts them;
   - game logic that runs backwards or never triggers: capture a known state from a known angle and compare it with the expected one.
4. Before diagnosing from pixels, correlate at least one more channel: the scene graph, the console or renderer metrics. A black object can be an unlit material, a missing texture, a shader error or clipping.

**API facts** (check the installed version):
- Many deprecation messages go through `warnOnce()`, which prints each distinct message a single time per page load (verified on r186).
- `setConsoleFunction()` routes three.js's own logs, warnings and errors to a handler the build can expose to the capture tool (verified on r186).

## Performance evidence

**Build.**
- Report frame time on the CPU, GPU time where timestamps are supported, draw calls, triangles, render targets and their sizes, GPU memory, the tier, the backend, the adapter, the pixel ratio and the canvas size ([assets-and-performance.md](assets-and-performance.md)).
- Measure after warm-up, with compilation excluded, over the fixed-step walkthrough; on laptops and phones, measure for several minutes as well.
- Put the numbers in the handback and the provenance block; a frame-budget criterion is graded from the build's own on-screen readout in the captures.
- Never infer GPU cost from CPU time, and never report timings from a software adapter.

## Tells of an unfinished Three.js build

For the orchestrator's harsh read before handoff. Each of these is a reason to log `WIN-VOIDED`, unless the brief asks for it:
- a default gray or black backdrop with no environment light, so metals render black;
- untextured gray materials, or one uniform plastic roughness everywhere;
- primitive stand-ins, faceted curves, stretched UVs or visible tile grids;
- floating objects, missing contact shadows, z-fighting or flickering coplanar faces;
- jagged or shimmering edges, crawling or blocky shadows, acne stripes;
- bloom on everything, banded skies, a mesh edge at the horizon;
- identical clones in rows, LOD pops between consecutive frames;
- HTML labels drifting from their 3D anchors, UI glowing or blurred by post;
- the subject small in the middle of the frame under default orbit framing;
- console error overlays, or a backend different from the brief's target.

## Symptom → cause

The Diagnoser's cross-system table. The file named in each first check has its own table with more detail.

| Symptom | Likely cause | First check |
| --- | --- | --- |
| Black or blank capture | headless WebGPU hidden, insecure origin, no adapter, or canvas readback after clearing | the backend and adapter read after the ready flag, and how pixels were read (this file) |
| Capture differs from the user's browser | fallback backend, software adapter, or a different pixel ratio | the provenance line against `BRIEF.md` (this file) |
| Rounds differ with no code change | time or seed not pinned, capture before temporal effects settled, exposure still adapting | the same time set twice, captured after warm-up (this file) |
| The same criterion fails after many tuning rounds | tuning around a core step never verified; test it on a known input first | the core step alone on a known input (this file) |
| Compiles but looks wrong, no error | wrong color space, missing tone mapping, an ignored legacy property | texture color spaces and the output owner ([foundation.md](foundation.md)) |
| Debug view identical to the final | debug switch not wired to the pipeline | final and no-post stills at one bookmark ([foundation.md](foundation.md)) |
| Motion speed differs between displays | per-frame increments instead of time | the frame-rate pair ([foundation.md](foundation.md)) |
| Looks right only with post | an authored system missing upstream | the no-post still ([final-image.md](final-image.md)) |
| Gray, flat or washed-out frame | conversion or tone mapping applied twice | the one output owner ([final-image.md](final-image.md)) |
| Gray sunlit walls, dark halos | AO on the final color, or an oversized radius | the AO-only view ([final-image.md](final-image.md)) |
| Ghost trails under temporal AA | missing velocity, including displaced surfaces | the velocity buffer during motion ([final-image.md](final-image.md)) |
| No reflections on water or wet ground | screen-space reflections in single-ray mode on non-metals | the SSR mode and what feeds its metalness input ([final-image.md](final-image.md)) |
| Everything glows | bloom threshold too low, or exposure too high | HDR values of lit surfaces against the threshold ([final-image.md](final-image.md)) |
| Banded sky or fog | 8-bit output or no dither | `outputBufferType` and dither ([final-image.md](final-image.md)) |
| Black metal, plastic look | no environment light, uniform roughness | `scene.environment` and a roughness view ([lighting-and-shadows.md](lighting-and-shadows.md), [materials.md](materials.md)) |
| Crawling shadow edges or a seam across the ground | no texel snapping, cascades not blended | a slow pan pair with cascades tinted ([lighting-and-shadows.md](lighting-and-shadows.md)) |
| Acne stripes or floating shadows | bias wrong for the cascade, or values from before r183 | `bias` and `normalBias` per cascade ([lighting-and-shadows.md](lighting-and-shadows.md)) |
| Objects look pasted on | no contact shadows, or the environment doesn't match the backdrop | contact darkening in shade, and one environment for both ([lighting-and-shadows.md](lighting-and-shadows.md)) |
| Visible tile grid | one UV scale, no macro variation or anti-tiling | a high, top-down still ([materials.md](materials.md), [terrain.md](terrain.md)) |
| Visual soup | independent noise per channel | each field shown as color ([materials.md](materials.md)) |
| Sparkle or shimmer in the distance | unfiltered detail, missing mipmaps or anisotropy | consecutive frames of a slow pan ([materials.md](materials.md), [assets-and-performance.md](assets-and-performance.md)) |
| Stutter the first time something appears | shaders compiled on demand | `compileAsync()` before reveal ([assets-and-performance.md](assets-and-performance.md)) |
| Pops while walking | detail levels without hysteresis, or lower levels that aren't subsets | detail levels tinted during the walkthrough ([assets-and-performance.md](assets-and-performance.md), [nature.md](nature.md)) |
| Slower on WebGPU than on WebGL | many moving, unbatched meshes | draw calls and object count ([assets-and-performance.md](assets-and-performance.md)) |
| Page reloads on a phone | memory limit | texture sizes, environment size and leaks ([assets-and-performance.md](assets-and-performance.md)) |
| Hero object reads as a pile of shapes | primitives instead of designed forms | the silhouette-only and clay views ([geometry.md](geometry.md)) |
| Interior flat and gray | ambient-only light, no motivated sources or bounce | a clay pass lit by each source alone ([architecture.md](architecture.md), [lighting-and-shadows.md](lighting-and-shadows.md)) |
| Glass like gray plastic, or with black patches | opacity instead of transmission, missing far-surface data | `transmission` and `opacity` on the material ([special-materials.md](special-materials.md)) |
| Uniform grass carpet, or a field swaying in sync | no clump structure; wind driven by time alone | clump ids and the wind field as debug views ([nature.md](nature.md)) |
| Cracks between terrain tiles, or terraces | LOD with no morph or skirt; 8-bit heights | a wireframe view at an LOD border, and the height format ([terrain.md](terrain.md)) |
| Plastic blue water, or a hard shore line | no depth absorption or Fresnel; no thickness fade | a thickness view at the shore ([water.md](water.md)) |
| Shadows disagree with the sun in the sky | light and sky read different sun descriptions | which sun description each one reads ([sky-and-weather.md](sky-and-weather.md)) |
| Porous or boiling clouds | detail adds density instead of eroding it; fields move apart | density with detail switched off ([sky-and-weather.md](sky-and-weather.md)) |
| Jitter far from the origin | single-precision positions, no floating origin | the camera's distance from the origin ([space.md](space.md)) |
| An effect pops into empty air, or reads only with bloom | no event origin; form supplied by glow | the effect with bloom off, and its spawn points ([effects.md](effects.md)) |
| Half-halt or snap at the end of a camera move | two smoothers on one move, no exact final pose | which systems write the camera during the move ([camera-and-animation.md](camera-and-animation.md)) |
| Objects tunnel through walls or jitter at rest | step too coarse, raw physics poses rendered | the collider debug view over consecutive frames ([interaction-and-ui.md](interaction-and-ui.md)) |
