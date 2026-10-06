# Unity performance and builds: budgets, quality tiers, batching, culling and LOD, profiling, Web builds, scripting backends and Apple silicon

API facts verified on Unity 6.6 (6000.6.4f1, 2026-10-06). Check the project's Unity version first (ProjectSettings/ProjectVersion.txt); if it differs, confirm in that version's official docs or the installed packages. The installed version wins.

Read when a build has a frame budget, ships to the Web, or needs quality tiers: budgets for the Mac and the Web, one URP asset per tier, draw-call methods, culling and LOD, reading the profiler, Web build limits, and the scripting backend. Running builds from the command line is in [agent-control.md](agent-control.md), capturing performance evidence in [validation.md](validation.md), anti-aliasing and upscaling per tier in [final-image.md](final-image.md), and texture formats in [assets-and-import.md](assets-and-import.md).

## Contents

- Budgets as decision rules
- Quality tiers: one URP asset per tier
- Draw calls: SRP Batcher, GPU Resident Drawer, instancing and batching
- Culling, occlusion and LOD
- Loading big content: Addressables and content directories
- Reading the profiler
- Web builds: WebGL 2, WebGPU and the fallbacks
- Web memory, compression, audio, fonts and threads
- Scripting backend: IL2CPP or Mono
- Apple silicon builds
- Symptom → cause

## Budgets as decision rules

**Goal.** Each target meets a frame budget the brief names, measured in a build rather than guessed in the editor.

**Build.**
1. Take the frame-time target from the brief; without one, propose one per target at Rule 0. Work in milliseconds: 60 fps leaves 16.7 ms per frame, 30 fps leaves 33.3 ms.
2. Measure the top tier as a Mac build and the Web tier in a desktop browser on the same Mac, at the capture size, on the scene's worst view (the most objects, lights and effects at once).
3. Find the bound before optimizing. When GPU frame time is close to the whole frame, cut pixels: render scale, post, shadow cost, overdraw. When the main or render thread dominates, cut work per object: draw calls, culling, scripts, physics.
4. Keep headroom: Web builds pay more CPU per draw call than the Mac, and the browser shares the machine.
5. Budget memory too: keep the Web heap well inside its maximum (below), and watch download size.
6. Record each measured number with its tier, target and view; [validation.md](validation.md) decides how it becomes evidence.

**Watch for.** Editor numbers taken as final: the editor's main-thread figure includes its own windows. FPS without frame times. An empty scene that looks fast only because the template leaves vSync off.

**Critic checks.** PASS when the frame-time readout the build draws itself, visible in walkthrough frames or a still made for it, stays at or below the brief's target at capture size and the declared tier, without jumps while the camera moves. FAIL signs: readings over the target; jumps as effects or new areas load; no readout in the captures.

**API facts** (check the installed version):
- The Rendering Statistics window reports frame rate, global and GPU frame time, main versus render thread share, triangles, vertices, Set Pass calls, and draw calls split into SRP Batcher, BRG and GPU Resident Drawer, GPU instancing and incompatible draws (verified on 6000.6).
- In the editor, the main-thread share includes time spent updating the Scene view and other editor windows (verified on 6000.6).
- On desktop and the Web, `Application.targetFrameRate` is ignored while `QualitySettings.vSyncCount` is above 0; on the Web, vSync 0 with a target of -1 renders at the display's refresh rate (verified on 6000.6).

## Quality tiers: one URP asset per tier

**Goal.** Each tier is one quality level with its own URP asset, a declared list of what it keeps and drops, and a fixed pin during capture.

**Build.**
1. Make one quality level per tier (for example Mac High, Mac Low and Web), each pointing at its own URP asset and renderer. Never leave a level's pipeline asset empty, or that level renders with Built-in ([foundation.md](foundation.md)).
2. Set each platform's default quality level in the Quality settings, so the Mac build starts on a Mac tier and the Web build on the Web tier.
3. Per tier, set in the URP asset: render scale and upscaling, HDR precision, MSAA, shadow distance, cascades and resolution, soft shadow quality, additional lights and their shadows, the light probe system and the GPU Resident Drawer; in the renderer: rendering path, SSAO, decals and other renderer features.
4. Per tier, set in Quality settings: LOD Bias, Maximum LOD Level, the mipmap limit and its groups, anisotropic filtering, real-time reflection probes and vSync.
5. Keep the tone mapper and grade identical across tiers ([final-image.md](final-image.md)), and write the tier table into `PLAN.md`: what each tier keeps and what it gives up. Every compute-only or Mac-only feature names its Web fallback there ([router.md](router.md)).
6. Pin the tier for capture through the build's tier hook with `QualitySettings.SetQualityLevel`, and record it in `MANIFEST.md`.

**Watch for.** Maximum LOD Level: the build keeps only levels the lowest setting across all quality levels allows. Two tiers on different rendering paths, which doubles shader variants. A Build Profile override that silently changes a tier's settings in one build.

**Critic checks.** PASS when every tier's captures keep the goal's defining look and the same set of must-haves, with lower tiers giving up only what the tier table says. FAIL signs: a must-have missing in one tier; a tier with a different tone or grade.

**API facts** (check the installed version):
- Quality settings hold a default quality level per platform, and Maximum LOD Level strips lower LOD meshes from the build, using the smallest value among all quality levels (verified on 6000.6).
- `QualitySettings.SetQualityLevel(index, applyExpensiveChanges)` switches the quality level at runtime (verified on 6000.6).
- Since 6.1, a Build Profile can override the global Graphics and Quality settings for the builds made from it (verified on 6000.6).

## Draw calls: SRP Batcher, GPU Resident Drawer, instancing and batching

**Goal.** CPU time per draw stays low, using the method each tier and platform supports.

**Choose**, following Unity's URP recommendations for 6.6:
- The SRP Batcher, always on. It batches by shader variant, so many materials on few variants batch well.
- The GPU Resident Drawer on the Mac tiers. It needs renderers on Forward+ or Deferred+, the SRP Batcher, BatchRendererGroup variants set to Keep All, and shaders that support DOTS instancing. It runs on Vulkan, DirectX, Metal and consoles, not on the Web. It silently skips renderers with property blocks, custom sorting, per-renderer visibility callbacks or more than 128 materials.
- GPU occlusion culling on top of the Resident Drawer, where many objects sharing meshes hide behind others.
- The material GPU Instancing checkbox left off in URP, since it adds shader variants; scripted crowds of one mesh can call `Graphics.RenderMeshInstanced`.
- Static batching off on tiers with the Resident Drawer, which it conflicts with. On the Web tier, it trades memory for draw calls; measure before keeping it.
- Dynamic batching no longer exists in 6.6.

**Build.**
1. Check Set Pass calls and the draw-call breakdown in Rendering Statistics; incompatible draws should be near zero.
2. On the Mac tiers, confirm the Resident Drawer actually engaged (its counts are non-zero), and exclude special objects with the Disallow GPU Driven Rendering component.
3. On the Web tier, merge static props into fewer meshes, share materials and atlases, and cull hard, because WebGL dispatches draw calls more slowly than native.

**Watch for.** The Resident Drawer's longer builds (it compiles every BatchRendererGroup variant); animated LOD cross-fades, which it turns into static dithered fades; MaterialPropertyBlocks, which drop renderers from both the SRP Batcher and the Resident Drawer ([materials-and-shaders.md](materials-and-shaders.md)).

**API facts** (check the installed version):
- Unity's 6.6 guidance for URP: enable the SRP Batcher and GPU Resident Drawer, keep the material GPU Instancing checkbox off to avoid extra variants, and leave static batching off because it isn't compatible with the Resident Drawer (verified on 6000.6).
- The GPU Resident Drawer needs renderers on Forward+ or Deferred+, BatchRendererGroup Variants set to Keep All, the SRP Batcher on and GPU Resident Drawer set to Instanced Drawing; otherwise objects fall back to normal drawing (verified on 6000.6).
- The Resident Drawer and GPU occlusion culling are supported on Vulkan, DirectX 11 and 12, Metal and consoles, and disabled on other platforms (verified on 6000.6).
- On the Web, WebGL dispatches draw calls more slowly on the CPU than native OpenGL, so Unity advises keeping draw calls per frame low (verified on 6000.6).

## Culling, occlusion and LOD

**Goal.** Unity draws only what can be seen, at the detail the screen can show, without visible pops.

**Build.**
1. Set each camera's far clip plane to the view's real depth, and cull small props earlier with per-layer cull distances.
2. Use LOD Groups for authored LOD chains, impostors or per-level materials; turn on LOD Cross Fade in the URP asset and set Fade Mode to Cross Fade so levels blend.
3. Use Mesh LOD (generated on import) for dense meshes that only need fewer triangles. Don't combine it with a LOD Group, and remember that particles, VFX Graph and static batching always draw its full-detail level.
4. Occlusion: on the Mac tiers with the Resident Drawer, use GPU occlusion culling. Elsewhere, bake occlusion culling for static, enclosed levels: mark large opaque statics Occluder Static and other statics Occludee Static, and bake in the Occlusion Culling window ([levels-and-geometry.md](levels-and-geometry.md)).
5. With the Resident Drawer, Small-Mesh Screen-Percentage in the URP asset culls tiny objects.

**Watch for.** Baked occlusion in open landscapes, where it costs CPU and memory and hides little; thin or transparent occluders; LOD swaps that pop because cross-fade is off. Worlds wider than a few kilometers: single-precision positions far from the origin make meshes, physics and the camera jitter, so keep play near the origin, shifting the whole world back in one step when the player travels far.

**Critic checks.** PASS when walkthrough frames show objects neither appearing nor vanishing suddenly, no visible LOD switches near the camera, and nothing culled while it should be in view. FAIL signs: props appearing as the camera turns; a building changing shape at a set distance; objects flickering behind thin walls.

**API facts** (check the installed version):
- `Camera.layerCullDistances` takes 32 per-layer distances, where 0 means the far clip plane (verified on 6000.6).
- Mesh LOD stores generated LODs in the original mesh's index buffer; Particle System, VFX Graph and static batching always use LOD0, and mixing it with LOD Group isn't recommended (verified on 6000.6).
- Baked occlusion culling runs on the CPU at runtime, helps most when the GPU is bound by overdraw, lets dynamic objects be occluded but not occlude, and doesn't suit geometry generated at runtime (verified on 6000.6).
- LOD Group cross-fading needs LOD Cross Fade on in the URP asset and Fade Mode set to Cross Fade (verified on 6000.6).

## Loading big content: Addressables and content directories

**Goal.** Content loads on demand only when the build truly needs it; most first projects need neither system.

**Choose.**
- Scenes in the Build Profile's scene list for most projects.
- Addressables (bundled with 6.6) when content must load on demand or the Web download must shrink. Its groups can now build content directories.
- Content directories (new in 6.6), Unity's replacement for AssetBundles: incremental, self-deduplicating content builds loaded through `Loadable<T>`, for local content only.
- Progressive Asset Loading for Web builds (6.6), which downloads assets scene by scene instead of all before startup.
- Never a Resources folder for bulk content: everything in it ships.

**Build.** Decide at plan time, because switching later moves assets and references; the build commands belong to [agent-control.md](agent-control.md).

**API facts** (check the installed version):
- Content directories replace AssetBundles with de-duplication and lower memory overhead, support only local content builds, and work with the Addressables package (verified on 6000.6).
- Progressive Asset Loading loads assets per scene, and enabling it disables Name Files As Hashes and Decompression Fallback (verified on 6000.6).

## Reading the profiler

**Goal.** Every optimization starts from a measured bottleneck in a build; capturing that evidence is in [validation.md](validation.md).

**Build.**
1. Profile development builds of each target, with Autoconnect Profiler on. In 6.6, also set Managed Code Variant to Checked: the default Release variant leaves out URP's per-pass markers, the Rendering Debugger and URP's Frame Debugger support, and Instrumented keeps only the markers.
2. Read in order: CPU against GPU frame time; the main thread's largest samples (scripts, physics, animation, render setup); the render thread; then passes on the GPU.
3. Use the Frame Debugger on the Mac to see draw order and why batches break; it doesn't work on the Web.
4. Profile Web builds through the Profile button that the Default and PWA templates include, by Build and Run or by IP; only basic draw-call data comes through.
5. Use the Memory Profiler package for leaks across scene loads, and Project Auditor for static problems.
6. Use Deep Profiling only for short, targeted runs, since it slows every script.

**Diagnose.**
- High GPU time with few draw calls → pixels: post, shadows, overdraw or render scale.
- High main-thread time in rendering → too many draw calls or unbatched renderers.
- Spikes when new objects appear → shader compilation or loading; warm up or preload.
- Memory that climbs with every scene load → leaks, often cloned materials ([materials-and-shaders.md](materials-and-shaders.md)).

**API facts** (check the installed version):
- A development build includes the Profiler by default, Autoconnect Profiler connects it automatically, and Deep Profiling slows script execution (verified on 6000.6).
- In 6.6, a development build on the default Release code variant leaves out the Rendering Debugger and URP's render pass profiling markers; Checked (or Debug) keeps both, and Instrumented keeps only the markers (verified on 6000.6).
- Web builds are profiled only as development builds, the Frame Debugger isn't available for Web builds, and the Profile button comes with the Default and PWA templates (verified on 6000.6).

## Web builds: WebGL 2, WebGPU and the fallbacks

**Goal.** The Web tier runs on WebGL 2 everywhere it must, and uses WebGPU only where it has been proven, with WebGL 2 behind it.

**Choose.**
- WebGL 2 by default, for reach. It is an OpenGL ES 3.0-class API without compute shaders, so the Web tier uses these fallbacks: the Particle System instead of VFX Graph ([effects.md](effects.md)); SMAA, FXAA or MSAA instead of STP ([final-image.md](final-image.md)); merged meshes and baked occlusion instead of the Resident Drawer; Screen Space decals instead of DBuffer ([materials-and-shaders.md](materials-and-shaders.md)); and baked GI with non-directional lightmaps ([lighting-and-shadows.md](lighting-and-shadows.md)).
- WebGPU only by explicit opt-in, keeping WebGL 2 in the list as the fallback. It brings compute, but no async compute, dynamic resolution or cubemap arrays, and no synchronous GPU readback.

**Build.**
1. To opt in: Player settings > Web > Other Settings, turn off Auto Graphics API, add WebGPU, and drag it above WebGL 2. The first API a browser supports wins.
2. Capture the same views under both APIs, and record the API in `MANIFEST.md` ([validation.md](validation.md)).
3. Under WebGPU, read pixels back with `AsyncGPUReadback`, and capture the screen through `ScreenCapture.CaptureScreenshotIntoRenderTexture`; the synchronous calls fail.
4. Use the WebGPU device filter asset (6.6) to keep known-bad browsers on WebGL 2.

**Watch for.** Older devices drop into WebGPU's compatibility mode, with lower limits; some WebGPU features are missing in some browsers; WebGL clears its drawing buffer every frame unless the template asks to preserve it.

**API facts** (check the installed version):
- Unity enables WebGL 2 automatically but not WebGPU; WebGPU is added in the Web Graphics API list, and Unity falls back to the next API in the list when a browser can't run the first (verified on 6000.6).
- WebGPU in Unity has no async compute, dynamic resolution or cubemap arrays, and Unity falls back to WebGPU's compatibility mode on devices that lack core support (verified on 6000.6).
- Under WebGPU, `Texture2D.GetPixels`, `ComputeBuffer.GetData`, `ScreenCapture.CaptureScreenshot` and `CaptureScreenshotAsTexture` don't work; `AsyncGPUReadback` and `CaptureScreenshotIntoRenderTexture` replace them (verified on 6000.6).

## Web memory, compression, audio, fonts and threads

**Goal.** Web builds load fast, stay inside browser memory, and behave the same as the Mac build where the platform allows.

**Build.**
1. Memory: keep Maximum Memory Size at the recommended 2048 MB with Geometric growth. The heap is one contiguous block, so growth can fail in a fragmented browser; for mobile browsers, set Initial Memory Size near typical use.
2. Garbage collection runs only at the end of a frame on the Web, so avoid large per-frame temporary allocations and long allocating loops.
3. Compression: Brotli or Gzip for release builds, served with matching headers; Decompression Fallback only when the server's headers can't be set. Turn on Data Caching to keep assets between visits.
4. Size: strip shader variants (BatchRendererGroup variants Strip All on the Web tier), compress textures per browser class ([assets-and-import.md](assets-and-import.md)), and choose a size-focused Code Optimization. Choose the Web texture format in the Player settings or the build script: the build settings' Texture Compression overrides it and lives in `Library/`, outside version control.
5. Audio starts only after the player clicks or taps ([input-ui-and-audio.md](input-ui-and-audio.md)).
6. Fonts: the Web can't use system fonts, so ship every font the UI needs, including fallbacks and bold or italic faces.
7. Threads: C# threads don't run on the Web, `System.Threading` timers never fire, and token timeouts never trigger. Use Awaitable or coroutines ([foundation.md](foundation.md)); Burst jobs and the engine's own threads need Enable Native C/C++ Multithreading plus cross-origin isolation headers on the server.

**Watch for.** WebAssembly64 to raise memory past 4 GB: Safari doesn't support it, and builds above 2048 MB hit known browser bugs. Videos, which play only by URL from StreamingAssets on the Web.

**API facts** (check the installed version):
- Maximum Memory Size defaults to 2048 MB, the recommended value; it can go to 16384 MB, with known Chrome and Firefox bugs above 2048 MB (verified on 6000.6).
- The Compression Format for release builds is Gzip, Brotli or Disabled, and Decompression Fallback exists for servers whose response headers can't be configured (verified on 6000.6).
- Managed threads don't run on the Web, Timer callbacks and CancellationTokenSource timeouts never fire, and native and Burst multithreading need Enable Native C/C++ Multithreading plus COOP, COEP and CORP response headers (verified on 6000.6).
- Web builds can't reach the user's installed fonts, so every font must ship in the project (verified on 6000.6).

## Scripting backend: IL2CPP or Mono

**Goal.** Each platform builds with the backend it requires or benefits from, and code avoids features the ahead-of-time backend can't run.

**Choose.**
- Web: IL2CPP, ahead of time, always; code can't generate code at runtime.
- Mac, while iterating: Mono, which builds faster and is installed with the editor.
- Mac, for release: IL2CPP for runtime speed, which needs the Mac IL2CPP build module ([setup.md](setup.md)).

**Build.** Set Scripting Backend per platform in Player settings; for IL2CPP release builds use the Release or Master C++ compiler configuration, and keep Managed Stripping Level in mind when reflection-heavy code breaks after stripping.

**API facts** (check the installed version):
- Mono compiles C# just in time, while IL2CPP converts IL to C++ ahead of time and is required where JIT isn't allowed (verified on 6000.6).
- The Web is an ahead-of-time platform, so `System.Reflection.Emit` is unavailable there (verified on 6000.6).

## Apple silicon builds

**Goal.** Mac builds target Apple silicon natively, run on Metal, and start in a state capture can rely on.

**Build.**
1. Set the macOS build's Architecture to Apple silicon, the recommended target. Build Intel or universal players only if the user needs Intel Macs: Intel support is deprecated in 6.6.
2. Leave Auto Graphics API for Mac on, which selects Metal.
3. Window mode, size and Run In Background for capture runs are set by [validation.md](validation.md) and [agent-control.md](agent-control.md).
4. Keep the editor and builds on the same machine class as the user's, and record the architecture in `BRIEF.md`.

**API facts** (check the installed version):
- The macOS build's Architecture is Intel 64-bit, Apple silicon, or both; Intel support is deprecated, and Apple silicon is the recommended target (verified on 6000.6).

## Symptom → cause

| Symptom | Likely cause | First check |
| --- | --- | --- |
| Fine in the editor, slow in the build | editor numbers taken as final, or a different tier | the tier recorded for the build |
| Fast in the empty scene, slow in the real one | the worst view never measured | frame time on the busiest view |
| GPU-bound frame | post, shadows, overdraw or render scale | GPU time with effects and shadows off |
| High Set Pass calls | many shader variants or incompatible renderers | Rendering Statistics breakdown |
| GPU Resident Drawer counts at zero | Forward path, property blocks, or variants stripped | the requirements in this file |
| Objects missing only in the Mac build | BatchRendererGroup variants stripped | Graphics settings, BRG variants Keep All |
| One tier renders with Built-in | quality level without a URP asset | Quality settings, each level's asset |
| Props pop in and out | no cross-fade, or cull distances too short | LOD Group fade mode; layer cull distances |
| Web build blank or pink on some browsers | a compute or WebGPU-only feature on WebGL 2 | the Web tier's feature list |
| Screenshot fails on WebGPU | synchronous capture API | `CaptureScreenshotIntoRenderTexture` |
| Web build runs out of memory | heap growth or per-frame allocations | Maximum Memory Size; allocations per frame |
| Web load is slow | uncompressed build or wrong server headers | Compression Format; Decompression Fallback |
| Timers or timeouts never fire on the Web | `System.Threading` timers don't run there | replace with Awaitable or coroutines |
| UI text missing on the Web | system font not shipped | fonts in the project |
| No URP markers in a development build | Managed Code Variant at Release | Player > Other Settings |
