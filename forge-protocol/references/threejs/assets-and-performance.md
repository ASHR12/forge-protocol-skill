# Three.js assets and performance

API facts verified on r186 (2026-10-05). Check the installed version first; if it differs, confirm in the official docs or the installed source. The installed version wins.

Read this when you load and compress content, source third-party assets, draw large counts, stream big worlds, work to a frame budget or target phones.

## Contents

- Units, scale and axes
- glTF delivery and geometry compression
- Textures: KTX2, mipmaps, filtering and memory
- Sourcing and the license ledger
- Loading and compiling ahead
- Instancing, batching and per-object cost
- GPU-driven scatter: compute culling and indirect draws
- Level of detail, impostors and culling
- Large worlds and streaming
- Budgets and profiling
- Mobile and low-power devices
- Quality tiers
- Symptom → cause

## Units, scale and axes

**Goal.** One unit is one meter, +Y is up, and every object has its real size. Shadow ranges, fog density, AO radius, physics and camera speed all assume it.

**Build.** Export at real scale with transforms applied, check each asset against a human-scale reference (a 2 m door, a 1.75 m person), and fix scale in the source asset instead of with a runtime multiplier.

**Critic checks.** PASS when people, doors, vehicles and props agree in scale in every still and walkthrough frame. FAIL signs: doors a character couldn't walk through; trees the size of shrubs; fog or AO that make the scene read as a miniature.

**Diagnose.** Shadows, fog and AO all look wrong at once → scale off by 10× or 100×, typically centimeters exported as meters.

**API facts** (check the installed version):
- `FBXLoader` has converted Z-up files to Y-up by itself since r184, so remove manual rotations left over from older code (verified on r186).

## glTF delivery and geometry compression

**Goal.** Small files that decode fast and arrive ready to render.

**Build.**
1. Use binary glTF (`.glb`) by default. Before export: transforms applied, normals present, tangents for normal-mapped meshes or none at all (see the facts below), materials and nodes named, no stray cameras or lights, one material per surface identity.
2. Optimize offline with a glTF processing tool such as glTF-Transform: weld and dedupe, prune unused data, resample animations, turn repeated meshes into GPU instances, and resize textures to the texel-density target.
3. Pick the geometry compression:
   - meshopt: fast decoding, and it also compresses animation and morph targets; pair it with quantization. The default for web delivery.
   - Draco: the smallest static meshes, at a higher decode cost in a worker. Suits large static scans.
   - none: for small assets, or when weak CPUs would spend longer decoding than downloading.
4. Ship the decoders and transcoders with the build, and point the loaders at them.

**Watch for.** Quantization so coarse that tile edges crack or normals shimmer; decoder paths that 404 and leave the load hanging; extensions the loader was never set up for.

**Diagnose.**
- A long blank load → uncompressed geometry or textures.
- Cracks or shimmer that appear only after optimizing → quantization too coarse for that mesh.

**API facts** (check the installed version):
- `GLTFLoader` needs `setDRACOLoader()`, `setMeshoptDecoder()` (the decoder ships as `libs/meshopt_decoder.module.js`) and `setKTX2Loader()` before it loads files that use those extensions; a KTX2 texture without the KTX2 loader throws (verified on r186).
- When a glTF mesh has no tangents, `GLTFLoader` flips `normalScale.y` so the derived tangents match glTF's normal-map convention (verified on r186).
- `DRACOLoader.setDecoderConfig()` is deprecated since r185: the decoder is WASM only, and the call is due to be removed in r194 (verified on r186).

## Textures: KTX2, mipmaps, filtering and memory

**Goal.** Ground near the camera stays sharp at grazing angles, distant surfaces don't shimmer, and textures fit the tier's memory budget.

**Choose.**
- KTX2 with ETC1S for base color, emissive and other color maps where size matters: small files, with visible blocking in fine detail.
- KTX2 with UASTC for normal maps, packed occlusion-roughness-metalness maps and hero color maps: larger and far cleaner. Add Zstandard supercompression to cut the download.
- Uncompressed PNG or WebP for small UI art, exact-value data textures and lookup tables, or a hero map that shows compression damage.
- Encode color maps with the sRGB transfer and data maps as linear, so they load with the right color space. Store mipmaps inside the KTX2 file.

**Build.** Set a texel-density target per tier and hold it across neighboring assets. Put many same-size layers, such as terrain layers, decals and variants, into array textures. Give ground, roads and walls seen at grazing angles high anisotropic filtering. Budget GPU memory per tier with rough arithmetic: a 4096² RGBA8 texture with mips takes about 85 MiB, about 21 MiB in a one-byte-per-texel format (BC7, ASTC 4×4), and about 11 MiB in a half-byte format (BC1, ETC1).

**Critic checks.** PASS when ground and walls near the camera stay crisp at grazing angles, and distant surfaces hold steady without shimmer or moiré across walkthrough frames. FAIL signs: ground smeared a few meters ahead; sparkling or crawling distant textures; blocky artifacts on normal-mapped hero surfaces.

**Diagnose.**
- Smeared ground → anisotropy left at 1.
- Shimmer or moiré → missing mipmaps.
- Blocky normal detail → normal maps stored as ETC1S.
- Black or missing textures → a wrong transcoder path, or `detectSupport()` not called after init.
- The tab reloads on phones → large uncompressed maps.

**Start here** (adjust to the goal): ground and wall textures at the renderer's maximum anisotropy, and about 512 texels per meter for surfaces a walking camera passes close to.

**API facts** (check the installed version):
- `KTX2Loader` needs `setTranscoderPath()`, then `detectSupport(renderer)` after `await renderer.init()`; loading before `detectSupport()` throws, and `detectSupportAsync()` is deprecated since r181 (verified on r186).
- Compressed textures never generate mipmaps at runtime (`generateMipmaps` is false), so the mips must ship in the file (verified on r186).
- `Texture.DEFAULT_ANISOTROPY` is 1, meaning off, and `renderer.getMaxAnisotropy()` reports the device's ceiling (verified on r186).
- `DataArrayTexture` and `CompressedArrayTexture` hold many same-size layers in one binding (verified on r186).

## Sourcing and the license ledger

**Goal.** Every shipped asset is legal to serve from a public web page and can be traced back to its source.

**Choose.**
- Authored or procedural content first: it carries no license risk.
- CC0 libraries such as Poly Haven and ambientCG for textures, HDRIs and models: no attribution required, and redistribution is allowed.
- Marketplace assets under a project-use license, whose typical terms allow use inside a project but forbid redistributing the raw files. A web build serves its files to anyone who asks, and whether that counts as redistribution is a gray area, so prefer CC0 for public demos and record the caveat for anything else.
- CC-BY assets, with the creator's credit shown where the license asks for it.
- Meshes from image-to-3D or other generators: check the tool's terms, then gate them like any hero mesh ([geometry.md](geometry.md)).
- Elevation data, map tiles and photogrammetry carry terms of their own ([terrain.md](terrain.md)).

**Build.** Give each third-party element a row in `art/LEDGER.md`, adding columns where needed: the element; its file paths in the build; source URL; author; license name and version; the required attribution text and where the build shows it; changes made; whether the raw file can be fetched from the deployed site; date retrieved; status. Before handoff, every row is final and every required credit is visible.

**Watch for.** Scanned albedo with baked shadows that contradict the scene's sun (de-light it or pick another set); texel density that jumps between neighbors; assets at the wrong scale or orientation.

## Loading and compiling ahead

**Goal.** The first visible frame is complete, and nothing hitches the first time it appears.

**Build.**
1. Show real progress, load what the first view needs first, and stream the rest.
2. Once the scene, lights and environment are in place, precompile, then render a few warm-up frames before revealing the scene.
3. Set the ready flag only after that ([foundation.md](foundation.md)).
4. Precompile objects that appear later before they enter the view.

**Watch for.** Placeholders that reach a capture, which fails C3; precompiling under different lights or a different environment than the ones that render, so everything compiles again on first use.

**API facts** (check the installed version):
- `renderer.compileAsync(scene, camera)` compiles every material ahead of time to avoid first-use stutter. Set the scene's lights and environment first, and to precompile an object you will add later, pass the target scene as the third argument (verified on r186).
- `renderer.compileComputeAsync()`, new in r186, precompiles compute nodes (verified on r186).

## Instancing, batching and per-object cost

**Goal.** Draw many things with few draw calls and little CPU work per object, without visible cloning.

**Choose.**
- Many copies of one mesh → `InstancedMesh` with per-instance transforms, colors and attributes. Split it into spatial chunks, because each instanced mesh is culled as a single object.
- Many different meshes that share a material → `BatchedMesh`.
- Static mixed geometry → merge by material once the mesh checks pass ([geometry.md](geometry.md)).
- Static subtrees on the WebGPU backend → `BundleGroup`, plus `static` on objects that never change.
- Objects animated, picked or streamed one by one → separate meshes, watching the per-object cost below.

**Watch for.**
- `WebGPURenderer` is not automatically faster. Thousands of independently moving, unbatched meshes can run several times slower than on `WebGLRenderer`, because each object costs uniform updates and refresh checks every frame. Instance, batch, bundle or mark them static, or stay on `WebGLRenderer`.
- A cloned material per object instead of per-instance attributes: more shader programs, and batching breaks.
- One instanced mesh spanning the whole world, which can never be culled.

**Critic checks.** PASS when instances don't pop in or out at frame edges in walkthrough frames, and repeated objects vary in scale, rotation or tint so copies don't read as clones. FAIL signs: objects popping at the screen border; rows of identical copies.

**Diagnose.**
- Slower on WebGPU than on WebGL → many moving, unbatched meshes.
- High CPU on a scene that never changes → per-object checks; batch, bundle or mark static.
- Low GPU time but a low frame rate → CPU-bound draw submission.

**API facts** (check the installed version):
- `BatchedMesh` culls and sorts per object by default (`perObjectFrustumCulled`, `sortObjects`), and `addInstance()` draws a stored geometry again without copying it (verified on r186).
- `BundleGroup` records its subtree as one WebGPU render bundle; it accepts only renderable objects, not lights, and gives no speedup on the WebGL backend (verified on r186).
- `Object3D.static = true` tells `WebGPURenderer` that an object's geometry and material settings won't change after the first render, so some per-frame checks are skipped (verified on r186).

## GPU-driven scatter: compute culling and indirect draws

**Goal.** Hundreds of thousands to millions of small instances (grass, pebbles, flowers, debris) placed and culled on the GPU, and stable from frame to frame. Grass craft itself is in [nature.md](nature.md).

**Build.**
1. A compute pass writes per-instance data to a storage array, seeded by a hash of world position so instances stay put while the camera moves.
2. A culling pass tests distance and frustum, compacts the visible indices with an atomic counter, and writes the count into an indirect draw buffer. Keep a radius around the camera where nothing is culled.
3. Give each detail tier its own indirect draw: one buffer with several offsets.
4. Give the WebGL fallback a tier of its own, such as CPU-placed instanced chunks, and test every compute path with `forceWebGL`.

**Watch for.** Reading GPU counts back to the CPU every frame, which stalls; draw order decided by atomic races, which flickers; displaced instances that write no motion vectors ([final-image.md](final-image.md)).

**API facts** (check the installed version):
- `geometry.setIndirect(buffer, offset)` draws from an indirect buffer, and an array of offsets issues one draw per offset (verified on r186).
- `IndirectStorageBufferAttribute`, exported from `three/webgpu`, holds the draw arguments that compute writes (verified on r186).
- TSL's `instancedArray`, `compute`, `atomicAdd` and `instanceIndex` build the placement and culling passes, and `renderer.compute()` dispatches them (verified on r186).
- On the WebGL 2 fallback, compute runs through transform feedback, so storage-heavy paths need their own test there (verified on r186).

## Level of detail, impostors and culling

**Goal.** Distant content costs little and keeps its identity: silhouette, color and species survive every detail level.

**Build.**
1. Derive detail levels from the generator, or simplify while keeping UV seams and material borders.
2. Where you can, make each lower level a subset of the higher one (same positions, fewer parts), and cross the boundary with hysteresis or a dithered fade.
3. Use impostors for far trees, rocks and buildings: octahedral impostors for roughly convex shapes, card clusters for thin plants. Swap to the impostor only once the object covers no more pixels than the impostor was baked at, and fade motion such as wind to zero before the swap.
4. Bake impostors with each instance's variation (tint, scale), or apply it at draw time, so far forests keep their color variety.
5. Add occlusion culling only where whole rooms or blocks hide each other, as in dense interiors and cities.

**Critic checks.** PASS when walkthrough frames show no pops, silhouette jumps, or color or species swaps as objects change detail, and far groups keep the variety of near ones. FAIL signs: trees flicking between shapes; a far forest turned into one flat-colored blob; buildings that change color with distance.

**Diagnose.**
- Pops → no hysteresis or fade, or levels that aren't subsets of each other.
- A uniform far blob → impostors baked without per-instance variation.
- Shimmering far canopies → cards without mipmaps or alpha-to-coverage.

**API facts** (check the installed version):
- `LOD.addLevel(object, distance, hysteresis)` takes a hysteresis fraction of the distance (default 0) that stops flicker at a boundary (verified on r186).
- `SimplifyModifier` is based on meshoptimizer since r186, and its `modify()` is async (verified on r186).

## Large worlds and streaming

**Build.**
- Split the world into chunks. Load and unload them by distance with hysteresis, under per-frame budgets for decoding and object creation, and load first whatever covers the most screen.
- Decode in workers, and precompile a chunk before it becomes visible.
- Build chunk edges from global data so neighbors match; terrain seams are in [terrain.md](terrain.md).
- Past a few kilometers from the origin, 32-bit positions jitter: shift the origin or render relative to the camera ([space.md](space.md)).
- When a chunk unloads, dispose everything it owned.

**Diagnose.**
- A hitch at chunk borders → synchronous creation or on-demand compiling.
- Jitter far from the origin → float precision.
- Memory climbing during a long flight → chunks that never unload or never dispose.

## Budgets and profiling

**Goal.** The cost of every system comes from measurement, so each fix lands where the time actually goes.

**Build.**
1. Put the budget in `BRIEF.md`: a target frame time per device class and tier.
2. Measure in steady state after warm-up, with compilation excluded, at the capture resolution and tier: draw calls, triangles, render targets and their sizes, GPU time from timestamp queries, CPU time per system from performance marks, and GPU memory.
3. Find the bound. If lowering the resolution speeds the frame up, the GPU limits it; if cutting draws or objects does, the CPU does.
4. Fix in this order: lower the resolution of the expensive pass, cut draw calls and objects, simplify shaders and passes, then reduce counts.
5. On laptops and phones, measure for several minutes, because thermal throttling arrives late.
6. Report the numbers in the handback and the capture provenance ([validation.md](validation.md)).

**Watch for.** The usual costs: overdraw from transparent particles and foliage cards; shadow passes, where every cascade draws its casters again; full-resolution SSGI, SSR or depth of field; an uncapped pixel ratio; per-frame allocations that trigger garbage collection. Never infer GPU cost from CPU frame time.

**Critic checks** (only when `BRIEF.md` names a frame budget). PASS when the build's own performance readout, captured on the declared tier and backend, shows frame time at or under the target in every walkthrough frame. FAIL signs: the readout above target; spikes when new areas or effects appear.

**API facts** (check the installed version):
- `renderer.info.render` reports `drawCalls`, `frameCalls` and `triangles` for the current frame, and `renderer.info.compute` counts compute calls (verified on r186).
- GPU timings need `trackTimestamp: true` at creation and `await renderer.resolveTimestampsAsync()`. Without the `timestamp-query` feature the WebGPU backend turns tracking off silently, and the WebGL backend needs a timer-query extension (verified on r186).
- `WebGPURenderer`'s `info.memory` counts textures, geometries and render targets, with byte totals such as `texturesSize` and `total` (verified on r186).
- The Inspector add-on (`renderer.inspector = new Inspector()`) shows performance, memory and intermediate buffers, as the official examples use it (verified on r186).

## Mobile and low-power devices

**Build.**
- Lower the pixel ratio first. Run fewer post passes, at reduced resolution, and use smaller shadow maps with fewer cascades.
- Compress every texture, keep prefiltered environment maps small, and dispose render targets as soon as they are unused.
- Pick the tier from the capability probe, since WebGPU support varies widely across phones ([foundation.md](foundation.md)). Touch input is in [interaction-and-ui.md](interaction-and-ui.md).
- Test on a real device, or state in the handback that phone behavior is unverified.

**Watch for.** Mobile browsers kill a page that crosses a memory limit and reload it without any script error, and the limit depends on the device and its state, so budget conservatively. Frame time climbs after minutes of play as the device heats up.

**Diagnose.**
- The page reloads on a phone → the memory limit: uncompressed textures, large environment maps or leaks.
- Smooth at first, a slideshow a few minutes later → thermal throttling.

## Quality tiers

**Goal.** Each tier drops expensive mechanisms on purpose, says what it keeps, and never loses a must-have.

**Choose** (one ladder per system, cheapest rung first; give each tier the highest rung its measured budget holds):
- Pixel ratio: capped ([foundation.md](foundation.md)), then reduced with upscaling, then native.
- Shadows: one map or `SunLight` at a small map size, then `SunLight` at a larger size, then `CSMShadowNode` with more cascades plus contact shadows ([lighting-and-shadows.md](lighting-and-shadows.md)).
- AO and GI: baked AO only, then GTAO at reduced resolution, then GTAO or SSGI, then SSGI or voxel GI plus SSR ([final-image.md](final-image.md)).
- Antialiasing: FXAA or SMAA, then TRAA, or TAAU when the scene renders below full size.
- Dense scatter: instanced cards near and ground texture beyond, then instanced blades in two detail levels, then compute-placed blades, denser and interactive at the top.
- Water and clouds: normal-mapped or Gerstner water with layered or billboard clouds, then Gerstner water with refraction, then spectral water with raymarched clouds at reduced resolution, temporally upscaled at the top.
- Textures: compressed 1K sets, then 2K, then 4K hero sets.

**Build.** Name the tiers in the PLAN contracts with what each keeps and gives up. Pick the tier from the backend, the adapter and the frame time measured after warm-up; log every switch with its reason; let the user override it; pin it during capture. A compute-driven feature's fallback is often a different representation (analytic waves are not a low-resolution spectral ocean), so name it as such in the plan; details are in [nature.md](nature.md), [water.md](water.md) and [sky-and-weather.md](sky-and-weather.md).

**Critic checks.** PASS when stills on the lowest supported tier still show every must-have: fewer blades or softer shadows are fine, bare ground where the brief promised a meadow is not. FAIL signs: a must-have that disappears, or turns into a placeholder, on a lower tier.

**Start here** (adjust to the goal): two tiers, a low one for phones and the WebGL 2 fallback and a high one for desktop GPUs on WebGPU; add a tier between them only where measurements show a gap.

## Symptom → cause

| Symptom | Likely cause | First check |
| --- | --- | --- |
| Long blank load | uncompressed or oversized assets | file sizes and compression |
| Hitch when something first appears | shaders compiled on demand | `compileAsync()` before reveal |
| Smeared ground ahead of the camera | anisotropy off | `texture.anisotropy` |
| Shimmering distant textures | missing mipmaps | KTX2 export settings |
| Black or missing textures | KTX2 transcoder path, or no `detectSupport()` | loader setup after `init()` |
| Blocky normal detail | normal maps in ETC1S | UASTC for data maps |
| Page reloads on phones | memory limit | texture sizes, environment size, leaks |
| Slower on WebGPU than on WebGL | many moving, unbatched meshes | instancing, batching, `static`, bundles |
| High CPU on a static scene | per-object checks every frame | `static`, `BundleGroup`, `BatchedMesh` |
| Low GPU time, low frame rate | CPU-bound submission | draw calls and object count |
| GPU time always reads zero | timestamps unsupported or never resolved | `trackTimestamp`, adapter features |
| Pops while walking | detail levels without hysteresis or subsets | `LOD` hysteresis, fades |
| Far forest becomes a flat blob | impostors lost per-instance variation | impostor bake |
| Hitch at chunk borders | synchronous creation or compiling | streaming budget, precompile |
| Jitter far from the origin | float precision | floating origin ([space.md](space.md)) |
| Frame rate falls after minutes | thermal throttling | sustained measurement |
| Doors too big, trees too small | unit mismatch at export | export scale |
