# Three.js foundation: version, renderer, color, loop and hooks

API facts verified on r186 (2026-10-05). Check the installed version first; if it differs, confirm in the official docs or the installed source. The installed version wins.

Read this when you set up the app shell, pick a renderer, write shaders or wire capture hooks. It owns the module's version truth: the pin, the backend, the renamed and removed APIs, the color defaults and the loop.

## Contents

- Version pin and ground truth
- Renamed and removed APIs, r180 to r186
- Renderer and backend
- Capability probe and fallback detection
- Entry points and one copy of the library
- Color management
- Output ownership, briefly
- Loop, time and determinism
- Inspection and capture hooks
- Resize and pixel ratio
- Writing shaders: node materials, TSL and raw code
- Resource lifecycle and device loss
- Symptom → cause

## Version pin and ground truth

**Goal.** Every API call matches the release that is actually installed. Each of the four 2026 releases changed or retired APIs, and memory, tutorials and older examples still use the old names.

**Build.**
1. Pin an exact version in the package manifest, with no caret range. Record the revision in the Stack section of `BRIEF.md`, and log it when the app starts.
2. Check an API in this order: the installed package's source and JSDoc; `threejs.org/docs/llms.txt` (short rules) and `threejs.org/docs/llms-full.txt` (inline API and TSL docs); the migration guide on the three.js GitHub wiki; the official example for the feature, read as source from `threejs.org/examples`.
3. Upgrade ten releases at a time or less. Deprecation warnings last ten releases, so a bigger jump turns warnings into silent breakage.

**Watch for.** Third-party packs and samples pinned to older releases: learn their ideas, never copy their API calls. A console deprecation warning is a failure to fix, not noise ([validation.md](validation.md)).

**API facts** (check the installed version):
- `REVISION` exports the release as a string (`'186'`), and the core also sets `window.__THREE__` to it, so the page can report its own version (verified on r186).

## Renamed and removed APIs, r180 to r186

**API facts** (verified on r186, against the installed source and the official migration guide). A deprecated name still runs and logs a warning; a removed one either breaks or is ignored without a message.

| Old name or call | Use instead | Changed | Behavior on r186 |
| --- | --- | --- | --- |
| `PostProcessing` | `RenderPipeline` | r183 | works, warns |
| `renderAsync()`, `clearAsync()`, `initTextureAsync()`, `hasFeatureAsync()` | `await renderer.init()`, then `render()`, `clear()`, `initTexture()`, `hasFeature()` | r181 | work, warn |
| `computeAsync()` | `compute()` after `init()` | r181 in the guide | still runs, no warning |
| `waitForGPU()` | nothing | r181 | logs an error |
| `Clock` | `Timer` | r183 | works, warns |
| `RGBELoader` | `HDRLoader` | r180 | works, warns |
| `PCFSoftShadowMap` | `PCFShadowMap`, which is soft now | r182 (WebGL), r186 (WebGPU) | both renderers swap it and warn |
| TSL `rangeFog()`, `densityFog()` | `fog(color, rangeFogFactor(near, far))`, `fog(color, densityFogFactor(density))` | deprecated r171, removed r183 | the import fails |
| TSL `viewportResolution` | `screenSize` | deprecated r169, removed r186 | the import fails |
| TSL `directionToColor()`, `colorToDirection()` | `packNormalToRGB()`, `unpackRGBToNormal()` | r185 | work, warn |
| TSL `PI2` | `TWO_PI` | r181 | works, no warning |
| `PassNode.setResolution()` | `setResolutionScale()` | r181 | works, warns |
| `colorBufferType` option, `getColorBufferType()` | `outputBufferType`, `getOutputBufferType()` | r182 | renamed |
| `WebGLCubeRenderTarget` under `WebGPURenderer` | `CubeRenderTarget` | r183 | unusable |
| `TiledLighting`, `AnamorphicNode` | `ClusteredLighting`; `BloomNode` | r185 | removed |
| `LightProbeGrid` for `WebGLRenderer` | `LightProbeGridWebGL`; the old name is now the WebGPU version | r186 | renamed |
| `Source` | `TextureSource` | r186 | works, warns |
| `KTX2Loader.detectSupportAsync()` | `detectSupport()` after `init()` | r181 | works, warns |
| `DRACOLoader.setDecoderConfig()` | nothing; the decoder is WASM only | r185 | warns; removal planned for r194 |
| `texture.encoding`, `renderer.outputEncoding`, `sRGBEncoding` | `colorSpace`, `outputColorSpace`, `SRGBColorSpace` | r152 | gone: assigning them does nothing and logs nothing |
| synchronous `SimplifyModifier.modify()` | `await modify()`; results now come from meshoptimizer | r186 | async |
| GTAO `distanceExponent`, `distanceFallOff` | nothing | r186 | no effect |
| `up` uniform of `Sky` and `SkyMesh` | nothing; +Y is assumed | r186 | removed |

Changes that alter the look or behavior with no change to your code:
- r181: physically based materials conserve energy better, so rough surfaces get brighter, and PMREM reflections changed.
- r183: `WebGPURenderer` shadows improved, so bias values tuned earlier may now detach shadows. The legacy gamma of `Sky` was removed, and its old look can't be restored.
- r184: background and environment rotation now follow the rotation convention of objects; `FBXLoader` converts Z-up files to Y-up by itself.
- r185: `WebGPURenderer` changed premultiplied alpha; use an opaque `scene.background` or clear color unless the page must show through. GTAO became darker and wider. `updateWorldMatrix()` now honors `matrixWorldNeedsUpdate`, so code that writes `matrix` by hand with `matrixAutoUpdate` off must set that flag.
- r186: `Object3D` gained `dispose()`; a custom subclass with its own `dispose()` must call `super.dispose()`.
- If the installed version is r187 or newer, check how custom lights register with `WebGPURenderer` and how PMREMs are built before using either: the migration guide lists changes to both, and this module hasn't verified them.

## Renderer and backend

**Goal.** Pick the renderer whose features the look needs, and always know which backend actually ran.

**Choose.**
- `WebGPURenderer` (from `three/webgpu`) for new builds that use node materials and TSL, compute, or the current post stack (`RenderPipeline`, temporal AA, SSGI, voxel GI). It runs on WebGPU and falls back to a WebGL 2 backend on its own.
- `WebGLRenderer` (from `three`) as a first-class choice when the build uses custom GLSL (`ShaderMaterial` or `onBeforeCompile`), depends on WebGL-only add-ons, draws thousands of independently moving meshes that can't be instanced or batched (per-object cost is higher on `WebGPURenderer` today; [assets-and-performance.md](assets-and-performance.md)), or when the headless capture route has no hardware WebGPU adapter. Never mix `ShaderMaterial` or `onBeforeCompile` with `WebGPURenderer`.
- "WebGPU required" only when compute or storage buffers are the mechanism itself, such as GPU-placed grass drawn indirectly or FFT water. Then plan a reduced tier for the fallback, or a clear message on unsupported devices.

**Build.**
1. Create the renderer and `await renderer.init()` before the first render, feature query or precompile.
2. Read the backend, pick the tier, and log both (next section).
3. Keep the backend the same on every capture round, and record it in `MANIFEST.md` ([validation.md](validation.md)).

**Watch for.** The fallback announces itself with one console warning; after that everything still runs, with fewer features and different performance. Code written for one renderer can also do nothing at all on the other (see the last fact below).

**Diagnose.**
- Works locally but blank or different in capture → the capture route landed on the WebGL 2 fallback or a software adapter.
- Dark or haloed transparent edges after an upgrade → the r185 premultiplied-alpha change; use an opaque background or clear color.

**API facts** (check the installed version):
- `WebGPURenderer` falls back to a WebGL 2 backend when no WebGPU adapter is available and warns "WebGPU is not available, running under WebGL2 backend"; `forceWebGL: true` forces that path for testing, and `renderer.backend.isWebGPUBackend` or `isWebGLBackend` says which backend ran (verified on r186).
- `render()`, `clear()` and `hasFeature()` throw if called before `init()`, while `setAnimationLoop()` awaits `init()` itself (verified on r186).
- `WebGPURenderer` converts classic materials such as `MeshStandardMaterial` into node materials, but has no path for `ShaderMaterial`; `material.toneMapped` and `onBeforeCompile` are read only by `WebGLRenderer` (verified on r186).
- `WebGLRenderer.setNodesHandler()` with the `WebGLNodesHandler` add-on renders TSL node materials on the classic renderer, as a compatibility path for migrating (verified on r186).

## Capability probe and fallback detection

**Goal.** Features and the quality tier follow what the device really has, and the decision shows in logs and captures.

**Build.**
1. After `init()`, read the backend and compatibility mode, then query `hasFeature()` for each feature a path needs, such as timestamp queries or a texture compression family.
2. Read the adapter's description from the browser: the WebGPU adapter info, or the WebGL debug renderer string. Flag software adapters such as SwiftShader or llvmpipe. Their images may be right, but their timings are never evidence.
3. Pick the tier from the backend, the adapter and the frame time measured after warm-up. Log the decision with its reason, for example `tier=medium: webgl2 backend`, let the user override it, and test the fallback on purpose with one `forceWebGL` capture.

**Watch for.**
- `navigator.gpu` can exist while the adapter request returns nothing, without any error.
- WebGPU needs a secure context (`https` or `localhost`); a plain `http` address on the local network gets the fallback.
- Support changes month to month, so detect at runtime instead of reading the user agent. Dated note (October 2026): WebGPU is on by default in Chromium on Windows, macOS, ChromeOS and recent Android, in Safari 26, and in Firefox on Windows and macOS; Linux and many Android devices still vary.

**Diagnose.** Fine on one machine, fallback on another → no adapter, an insecure origin, or a blocked driver; read the probe log. Wrong tier for the device → the tier came from the user agent instead of the probe.

**API facts** (check the installed version):
- `WebGPU.isAvailable()` from `three/addons/capabilities/WebGPU.js` awaits a real adapter request, so it is false when `navigator.gpu` exists without an adapter (verified on r186).
- r186 requests a compatibility-level WebGPU adapter; on a device without core features, `renderer.backend.compatibilityMode` is true and MSAA is switched off (verified on r186).

## Entry points and one copy of the library

**Build.**
- Import `WebGPURenderer`, node materials and `RenderPipeline` from `three/webgpu`, TSL functions from `three/tsl`, add-ons from `three/addons/`, and the classic renderer from `three`. `three` and `three/webgpu` share one core module, so mixing them is safe as long as both resolve to one installed copy.
- Without a bundler, the import map must map `three`, `three/webgpu`, `three/tsl` and `three/addons/` to the same pinned version.
- Keep exactly one copy in the bundle: look in the lockfile for a second `three` pulled in by another dependency, and dedupe it. Use ES modules.

**Diagnose.**
- A "Multiple instances of Three.js being imported" warning, failing `instanceof` checks, or objects that don't render with the other module's renderer → two copies loaded.
- "Failed to resolve module specifier" for `three/webgpu` or `three/tsl` → an import map entry is missing.
- A 404 for a `.min.js` file → minified builds are gone in r186.

**API facts** (check the installed version):
- The package exports `three`, `three/webgpu`, `three/tsl` and `three/addons/*`; the TSL build imports `three/webgpu` by its bare name, which is why the import map needs both (verified on r186).
- r186 ships no minified builds, and `require('three')` still works but emits a deprecation warning: the package is moving to ES modules only (verified on r186).

## Color management

**Goal.** Every color enters the linear working space exactly once and leaves it exactly once, and data maps are never treated as color.

**Build.**
1. Tag color maps `SRGBColorSpace`: base color, emissive, sheen and specular color, sprites and UI art, and video or canvas textures that show pictures. Leave data maps at the default `NoColorSpace`: normal, roughness, metalness, AO, height, masks, flow maps and lookup data.
2. Let `GLTFLoader` tag glTF textures, and set the color space by hand on every texture you load yourself.
3. Write color constants as hex or CSS strings: they are read as sRGB and converted once. Never convert them again.
4. Keep HDR environments (`.hdr`, `.exr`) linear, as they already are, and leave the output conversion to its one owner (next section).

**Watch for.** Tuning by eye hides a double conversion: brighter lights "fix" the scene, and every later change fights the error. Check the color path in code before you tune light.

**Critic checks.** PASS when the deepest shadows read as deep with no milky veil, familiar materials such as foliage, skin, stone and wood sit at plausible saturation, and normal-mapped surfaces light evenly from the key's side. FAIL signs: a gray film over the whole frame; neon or crushed mid-tones; blotchy, lumpy shading on smooth normal-mapped surfaces.

**Diagnose.**
- Washed out and milky → a color map left untagged, or the output converted twice.
- Too dark and saturated → a hex color converted a second time, or no output conversion at all.
- Too glossy, or occlusion too dark → a roughness or AO map tagged sRGB.
- Lumpy or warped shading → a normal map tagged as color.

**API facts** (check the installed version):
- `ColorManagement.enabled` is true and the working space is `LinearSRGBColorSpace`; renderers output `SRGBColorSpace` by default (verified on r186).
- New textures default to `NoColorSpace`; `GLTFLoader` sets `SRGBColorSpace` on base-color and other color textures (verified on r186).
- `Color.setHex()` and `setStyle()` treat their input as sRGB, while `setRGB()` treats its numbers as already linear (verified on r186).

## Output ownership, briefly

**Goal.** One place tone-maps and converts to the display.

**Build.** Without a post chain that place is the renderer (`toneMapping`, `outputColorSpace`); with a `RenderPipeline` it is the pipeline's output transform or a single `renderOutput()` node. It is never also a material or a final custom shader. The renderer's default `toneMapping` is `NoToneMapping`, so an HDR scene needs a tone mapper chosen on purpose. The full treatment is in [final-image.md](final-image.md).

## Loop, time and determinism

**Goal.** Motion looks the same at any frame rate, and any moment can be reproduced exactly for capture.

**Build.**
1. Keep one app-owned clock. Advance it from a `Timer` updated once per frame, clamp the delta after stalls, and let capture pause it, step it by a fixed delta, or set it to an exact time.
2. Make everything that moves read that one time: animation mixers, shader time uniforms, particles, simulations and game logic.
3. Run simulation (physics, cloth, crowds, stateful particles, gameplay) on a fixed step with an accumulator. Cap the steps per frame, and draw the state interpolated between the last two steps.
4. Smooth with damping that takes the delta, never with a fixed fraction per frame.
5. Draw every visible random choice from one seeded generator, keyed by stable ids such as the world cell or instance index, so load order can't change the result. `Math.random()` never decides layout.
6. Keep shader time small: pass it relative to a recent origin, or wrap it where the effect is periodic, so float precision doesn't make animation step in long sessions.
7. Prove it: the same pose at the same time at two frame rates ([validation.md](validation.md) has the method).

**Watch for.** Logic counted in frames; effects that draw a fresh random number every frame, so no two captures match; a second clock hidden inside an add-on or animation library.

**Diagnose.**
- Speed changes with the display's refresh rate → per-frame increments.
- A jump after switching tabs → the delta isn't clamped, or the timer isn't connected to the document.
- A different layout on every reload → unseeded randomness.
- Bodies jitter at rest, or motion stutters on fast displays → a fixed step without interpolation.

**Start here** (adjust to the goal): clamp the delta at 0.1 s, and step simulations at 1/60 s.

**API facts** (check the installed version):
- `Timer` replaces `Clock`, which is deprecated since r183. Call `update()` once per frame; `getDelta()` and `getElapsed()` then return seconds (verified on r186).
- `timer.connect(document)` uses the Page Visibility API to zero the delta while the tab is hidden, and `setTimescale()` scales the delta for slow motion (verified on r186).
- `MathUtils.damp(current, target, lambda, dt)` smooths independently of frame rate (verified on r186).

## Inspection and capture hooks

**Goal.** Capture can reach any named state exactly, and every debug switch proves a mechanism by changing real pixels.

**Build.** Expose one object on `window`, named in the PLAN contracts, with:
- a ready flag, set only after assets load, `compileAsync()` resolves and warm-up frames have rendered;
- named camera bookmarks that store position, target or rotation, field of view, near and far;
- a debug-mode switch: final, no-post (effect passes off, tone mapping and display output kept), and the system views the bar needs, such as normals, AO, velocity, masks and wireframe;
- a quality-tier switch, pinned during capture;
- pause, step by a fixed delta, set time, and reset, which restores seed, state and temporal history together;
- metrics: draw calls, triangles, GPU time when available, memory, tier and backend ([assets-and-performance.md](assets-and-performance.md));
- an error surface: renderer errors, device loss and shader failures, shown on the page or kept in a log the capture saves.

Then prove each hook on the running build: when the build uses post-processing, the final and no-post stills differ only by the effect passes, and each debug view visibly differs from the final ([validation.md](validation.md)).

**Watch for.** A debug switch that changes a label but not the pipeline is worse than none, because it creates false evidence. A switch that rebuilds materials on every call adds compile stutter to captures. A ready flag set before precompiling lets the first capture miss shaders.

**Diagnose.**
- The no-post still is identical to the final on a build with post-processing → the switch isn't wired to the pipeline.
- Objects missing only in the first round → the ready flag was set before loading or compiling finished.

**Start here** (adjust to the goal): one object, `window.app`, with `ready`, `setView(name)`, `setDebugMode(mode)`, `setTier(name)`, `pause()`, `step(seconds)`, `setTime(seconds)`, `reset()` and `metrics()`. Keep whatever names the project already uses.

**API facts** (check the installed version):
- `renderer.onError` receives uncaptured backend errors, such as WebGPU validation and out-of-memory errors, and logs them by default; override it to show them on the page (verified on r186).
- `renderer.onDeviceLost` fires on WebGPU device loss or WebGL context loss; by default it logs an error, and rendering stops (verified on r186).
- `setConsoleFunction()`, exported from the core, routes three.js's own logs, warnings and errors to your handler. Some add-ons call `console.warn` directly, so keep the browser console as well (verified on r186).

## Resize and pixel ratio

**Build.**
- Choose the pixel ratio from a pixel budget: take the device ratio, cap it, then lower it until the canvas's device-pixel count fits the tier's budget.
- On every resize, call `setSize()`, update the camera's aspect and projection matrix, and resize every render target you created yourself. Pass nodes follow the renderer's size on their own.
- When the canvas sits inside a layout, watch its container with a resize observer, not just the window.
- Capture at a fixed CSS size and pixel ratio ([validation.md](validation.md)).

**Diagnose.**
- A soft image on dense displays, or slowness only on large monitors → the ratio is stuck at 1, or uncapped.
- A stretched image → aspect or projection not updated.
- HTML labels drifting from their 3D anchors → CSS pixels and canvas pixels mixed in the projection math.

**Start here** (adjust to the goal): cap the ratio at 2 on desktop and 1.5 on phones, then lower it while a post-heavy frame misses its budget.

## Writing shaders: node materials, TSL and raw code

**Goal.** Custom looks that run on both backends, keep built-in lighting correct, and can be inspected one node at a time.

**Choose.**
- First, the built-in `MeshStandardNodeMaterial` or `MeshPhysicalNodeMaterial` with node inputs. Lighting, shadows, fog, environment and tone mapping stay correct; motion vectors need a check once vertices move ([final-image.md](final-image.md)).
- TSL functions (`Fn`) for custom logic shared across materials, and compute nodes for GPU simulation.
- Raw WGSL or GLSL only when nothing else works, because each ties the material to one backend. `ShaderMaterial` and shader patching exist only on `WebGLRenderer`.
- A full replacement of the lighting model (`fragmentNode`, `outputNode`) only for a deliberate stylized look. Shadows, environment light and energy balance then become yours to rebuild.

**Build.** A material's node graph is compiled into WGSL or GLSL the first time it renders, so:
1. Put live parameters in `uniform` nodes; setting `.value` recompiles nothing.
2. Assign nodes, and change properties that alter the program, only at load time: each change compiles a new pipeline.
3. Pass per-vertex values to the fragment stage as varyings, and per-instance data through attributes or storage arrays. Build control flow with `If` and `Loop`, with bounded loop counts.
4. Dispatch compute nodes with `renderer.compute()`; they can share storage buffers with rendering.

**Watch for.**
- Texture samples that rely on implicit derivatives inside divergent loops or after a discard: they pick wrong mip levels and show seams. Give those samples an explicit level or gradients.
- Hashes built from `sin()`, which band and repeat on some GPUs; use integer hashes.
- World positions far from the origin in 32-bit floats, which make vertices and patterns jitter ([space.md](space.md)).
- Procedural detail finer than a pixel; filter it at the source ([materials.md](materials.md)).

**Diagnose.**
- Unsure what a node holds → route it to the output color for one capture, or publish it to the Inspector.
- A stutter the first time something appears → it compiled on demand; precompile it ([assets-and-performance.md](assets-and-performance.md)).
- Correct on WebGPU but black on the fallback → a raw WGSL function, or a storage-only path with no WebGL route.

**API facts** (check the installed version):
- Node materials expose slots such as `colorNode`, `normalNode`, `roughnessNode`, `metalnessNode`, `emissiveNode`, `positionNode`, `castShadowPositionNode`, `receivedShadowPositionNode`, `maskShadowNode` and `outputNode` (verified on r186).
- `wgslFn()` and `glslFn()` embed raw shader code and bind the material to the matching backend (verified on r186).
- Texture nodes take an explicit mip level with `.level()` or explicit gradients with `.grad()` (verified on r186).
- `.toInspector(name)` publishes any node to the Inspector add-on, on the WebGPU backend only (verified on r186).

## Resource lifecycle and device loss

**Build.**
- Share geometries, materials and textures, and cache loaded textures by URL.
- When content leaves for good, dispose its geometries, materials, textures and render targets. After a scene change, check that the memory counters return to their baseline.
- Handle device loss: show a clear message, then rebuild the renderer and reload GPU resources, or offer a reload. Test the WebGL path by forcing a context loss through the `WEBGL_lose_context` extension.

**Diagnose.** Memory climbs with every scene change → missing disposal. A black canvas after sleep or a driver reset → device loss isn't handled.

**API facts** (check the installed version):
- `Object3D.dispose()`, new in r186, frees only the object's own GPU resources; shared geometries, materials and textures still need their own `dispose()` (verified on r186).

## Symptom → cause

| Symptom | Likely cause | First check |
| --- | --- | --- |
| Blank canvas | rendering before `init()`, an exception in the loop, or a missing import-map entry | the console from page load |
| Fine locally, blank or different in capture | WebGL 2 fallback or a software adapter on the capture route | backend and adapter in `MANIFEST.md` |
| Washed-out, milky frame | color map left untagged, or output converted twice | texture color spaces; the one output owner |
| Dark, oversaturated frame | hex color converted again, or no output conversion | color constants; the output owner |
| Flat white, clipped highlights | `NoToneMapping` left on an HDR scene | `renderer.toneMapping` |
| Black metals, flat gray plastic look | no environment light | `scene.environment` ([lighting-and-shadows.md](lighting-and-shadows.md)) |
| Z-fighting far from the camera | near plane too close for the depth range | raise `near`, or use the `reversedDepthBuffer` or `logarithmicDepthBuffer` renderer option |
| Stutter the first time something appears | shaders compiled on demand | `compileAsync()` before showing it |
| Objects stop following their matrices after an upgrade | `matrixAutoUpdate` off without `matrixWorldNeedsUpdate` (r185) | code that writes `matrix` by hand |
| "Multiple instances of Three.js" warning | two copies of the library | lockfile and bundle |
| Dark or haloed transparent edges after an upgrade | r185 premultiplied-alpha change | opaque background or clear color |
