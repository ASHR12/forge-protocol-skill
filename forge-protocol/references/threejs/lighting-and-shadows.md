# Three.js lighting and shadows

API facts verified on r186 (2026-10-05). Check the installed version first; if it differs, confirm in the official docs or the installed source. The installed version wins.

Read this when you design the light, set up the sun, environment or shadows, ground objects, or add bounce and practical lights. The choice of AO and GI technique is in [final-image.md](final-image.md).

## Contents

- Light design
- Physical units and light ratios
- Environment light and reflections
- Sun and time of day
- Choosing a shadow technique
- Shadow stability, filtering and bias
- Contact shadows and grounding
- Indirect light: probes, lightmaps and bounce
- Practical and many lights
- Symptom → cause

## Light design

**Goal.** Light reveals form and sets the mood: one dominant direction, a readable value structure, and a subject that separates from its background.

**Build.**
1. Choose the key from the brief's mood and time of day (sun, window, lamp). Its direction decides the shadow shapes that describe form, so light the subject first and the world second.
2. Let fill come from the sky or environment, and set the key-to-fill ratio for the mood: wide for drama, narrow for softness.
3. Add a rim or back light where the subject must lift off the background, such as products and characters.
4. Plan the values: where the darkest darks and brightest lights sit relative to the focal point, so the glance read holds.
5. Take color from the motivating sources, for example a warm key against a cool sky fill, or the reverse at night.
6. Judge form in a clay pass (every material one mid-gray) under the key before materials go on. If form doesn't read in clay, materials won't rescue it.

**Watch for.** A frontal key that flattens form; several equal lights with no dominant direction; ambient light raised until shadows turn gray; lights tuned one by one to fix exposure.

**Critic checks.** PASS when every hero still shows one readable key direction, shadow sides keep visible detail, and the subject separates from the background in value or color. FAIL signs: flat frontal light; competing shadow directions; shadows filled to a uniform gray; a subject that merges with its background.

**Start here** (adjust to the goal): a key-to-fill brightness ratio near 4:1 for daylight, wider for drama, narrower for soft product light.

## Physical units and light ratios

**Goal.** Lights relate to each other as they would in the world, so one exposure suits the whole frame.

**Build.** Set lights in physical units from real-world values (sun far above sky, sky far above interior lamps), get the ratios right, and only then choose the exposure ([final-image.md](final-image.md)). Keep inverse-square falloff for point and spot lights unless the look is stylized.

**Watch for.** Raising the ambient level to rescue dark shadows, which flattens everything; per-light tweaks that hide a wrong exposure.

**API facts** (check the installed version):
- `PointLight` and `SpotLight` intensity is in candela, and setting `power` in lumens converts to it (verified on r186).
- `PointLight` defaults to `decay` 2 (physical inverse-square falloff) and `distance` 0 (no cutoff) (verified on r186).

## Environment light and reflections

**Goal.** Ambient light and reflections belong to the visible world: metals reflect the surroundings the viewer sees, and every object shares the scene's ambient color.

**Choose.**
- An HDR image (CC0 sources such as Poly Haven) for fixed-time realism, used for `scene.environment` and for the backdrop, or a ground-projected backdrop.
- A procedural sky baked into the environment, so ambient light and reflections follow the time of day ([sky-and-weather.md](sky-and-weather.md) owns the sky itself).
- A generated studio environment for products, with practical lights for the key shapes.
- Local probes indoors, because an outdoor sky must not reflect inside a closed room.

**Build.**
1. Match the environment's bright direction to the scene's key, rotating the environment to line up.
2. Use the same environment for the backdrop and the reflections.
3. Re-bake a procedural sky's environment when the sun has moved noticeably, never every frame, and dispose of the old one.
4. When a directional light already plays the sun, hide or clamp the sun in the HDR image or the sky bake, so the sun isn't counted twice.

**Watch for.** Black metals with no environment (metals reflect nothing else); an environment of a different place than the one shown; two sun highlights; large prefiltered maps on phones ([assets-and-performance.md](assets-and-performance.md)).

**Critic checks.** PASS when metals and glossy surfaces reflect surroundings consistent with the visible sky or set, and objects share the scene's ambient color. FAIL signs: black or flat gray metal; reflections of a different place; objects that look pasted in.

**Diagnose.**
- Black metal → no environment.
- A pasted-in look → environment and backdrop don't match.
- Doubled sun highlights → the sun is in the HDR image and in a light.
- The environment turned after an upgrade past r183 → r184 aligned environment rotation with object rotation.

**API facts** (check the installed version):
- An equirectangular or cube HDR texture assigned to `scene.environment` is prefiltered into a PMREM automatically by `WebGPURenderer` and cached; `PMREMGenerator.fromScene()` bakes a live scene, such as a procedural sky, into one (verified on r186).
- `scene.environmentIntensity` and `environmentRotation` scale and turn the image-based light; `backgroundIntensity`, `backgroundBlurriness` and `backgroundRotation` do the same for the backdrop (verified on r186).
- `HDRLoader` (renamed from `RGBELoader` in r180), `EXRLoader` and `UltraHDRLoader` load HDR images, and `GroundedSkybox` projects one onto a ground (verified on r186).

## Sun and time of day

**Goal.** One sun direction drives the light, sky, fog, glints and shadows, and its color and brightness follow its height.

**Build.** Read the shared sun description from the PLAN contracts ([router.md](router.md)). Warm and dim the sun near the horizon, cool and brighten it high up. Feed the same direction to the sky, the fog's sun-side tint, water glints and the shadow camera.

**Watch for.** If the installed version is r187 or newer, check how `SunLight` registers with `WebGPURenderer`: the migration guide changes how custom lights register, and this module hasn't verified the new way.

**Critic checks.** PASS when shadow direction and length agree with the sun's position in the sky (or the direction the light implies), and glints on water or glossy surfaces sit under the sun. FAIL signs: shadows pointing toward the sun; a low sunset sky over short noon shadows; a glint on the wrong side.

**API facts** (check the installed version):
- `SunLight` (an r186 add-on) has no target: it shines from its position toward the origin. `WebGPURenderer` needs `renderer.library.addLight(SunLightNode, SunLight)` before use, and `WebGLRenderer` supports it directly (verified on r186).
- `SunLightShadow` fits two cascades to the view frustum up to `shadow.camera.far`, blends them, ignores the shadow camera's left, right, top and bottom, and defaults to 1024² per cascade (verified on r186).

## Choosing a shadow technique

**Goal.** Every visible object is grounded by stable shadows that reach as far as the view needs, at a cost the budget can carry.

**Choose.**
- One shadow map fitted to the play area for bounded scenes: a room, an arena, a product stage.
- `SunLight` for open outdoor views with a moving camera.
- `CSMShadowNode` (on `WebGLRenderer`, the `CSM` add-on) when more cascades or custom splits are needed.
- `TileShadowNode` to split one large shadow map into tiles for wide scenes.
- Cached maps, refreshed only when casters or the light move, for static worlds and slow suns.
- Clipmap or virtual shadow schemes for very large worlds: nothing in the core provides them, so plan them as custom work.
- Baked shadows in lightmaps for static interiors (Indirect light below).

**Build.** Budget by shadow-casting lights × cascades × map size × refresh rate, since each cascade draws its casters again. Turn `castShadow` off for small or distant objects whose shadows no one would see, and remember that the renderer's shadow map starts disabled.

**Critic checks.** PASS when objects in every still are grounded by shadows, nearby shadows are crisp, and shadows reach as far as the brief's views need. FAIL signs: shadows that end abruptly at a distance band; blocky or blurry near shadows; objects that float.

**API facts** (check the installed version):
- `CSMShadowNode` works only with `WebGPURenderer`; it defaults to three cascades with practical splits and leaves `fade` off, so turn `fade` on to blend cascade seams (verified on r186).
- `TileShadowNode` splits one shadow map into tiles with their own cameras, and doesn't support `VSMShadowMap` (verified on r186).
- On both renderers, setting a light's `shadow.autoUpdate` to false and `shadow.needsUpdate` to true when something changes refreshes its shadow only on demand (verified on r186).
- `renderer.shadowMap.enabled` is false by default, and `WebGPURenderer` defaults to `PCFShadowMap` (verified on r186).

## Shadow stability, filtering and bias

**Goal.** No crawling, seams, acne or detached shadows, near or far.

**Build.**
1. Fit each shadow camera tightly around what must cast and receive. For custom cascades, snap each cascade's light-space center to its own texel grid, so shadow edges stay put as the camera moves.
2. Start from zero `bias` and raise `normalBias` in world units, more for coarser cascades. Lower values tuned before r183, when WebGPU shadows improved.
3. Blend between cascades, so no line marks where resolution changes.
4. Let the shadow pass see the same deformed geometry as the visible frame: wind, displacement and relief ([materials.md](materials.md)). Moving casters must also refresh any cached map.
5. Pick the filter: `PCFShadowMap` for soft, general shadows; `VSMShadowMap` for very soft ones, accepting light bleeding and that every receiver also casts; `BasicShadowMap` for hard, stylized shadows.

**Watch for.** Acne stripes on lit faces; shadows detached from their casters by too much bias; shimmering edges in walkthrough frames; visible seams between cascades; shadows frozen in place.

**Critic checks.** PASS when walkthrough frames show shadow edges holding still as the camera moves, no stripes on lit surfaces, no gap between objects and their shadows, and no visible line where shadow detail changes. FAIL signs: shimmering shadow edges; moiré stripes; floating shadows; a line across the ground where shadows go soft.

**Diagnose.**
- Crawling edges → shadow cameras that follow the view without texel snapping.
- A seam across the ground → cascades without blending.
- Acne only far away → bias not scaled up for the coarse cascade.
- Shadows detached after an upgrade → old bias values after the r183 change.
- Frozen shadows → a cached map never refreshed.
- Swaying plants with still shadows → the shadow pass skips the vertex displacement.

**Start here** (adjust to the goal): `bias` 0 and a `normalBias` near one texel's size in world units; the official sun example uses 0.05.

**API facts** (check the installed version):
- `PCFSoftShadowMap` was replaced on `WebGLRenderer` in r182 and on `WebGPURenderer` in r186; on r186 both swap it for `PCFShadowMap`, which is soft now, and log a warning (verified on r186).
- With `VSMShadowMap`, every shadow receiver also casts shadows (verified on r186).

## Contact shadows and grounding

**Goal.** Everything that touches a surface reads as touching it, in light and in shade.

**Choose.** Shadow maps give the base. Screen-space shadows add fine contact detail from the main directional light. Ambient occlusion grounds objects in shade, and its technique choice lives in [final-image.md](final-image.md). Baked contact blobs or decals suit stylized or very cheap builds.

**Critic checks.** PASS when every object resting on a surface shows darkening at its contact in every still, including in shade. FAIL signs: objects that look pasted on; feet that hover; props with no contact darkening in shaded areas.

**API facts** (check the installed version):
- `sss()` (screen-space shadows, also called contact shadows) complements shadow maps for one directional light. It sees only on-screen casters, grows expensive beyond about one meter of shadow length, and can need a blur before compositing (verified on r186).

## Indirect light: probes, lightmaps and bounce

**Goal.** Shaded areas and interiors get plausible bounce, never pitch black or flat gray unless the mood asks for it.

**Choose.**
- Lightmaps baked in Blender for static interiors at the highest quality.
- A light-probe grid for baked diffuse light that moving objects receive too.
- Fill lights placed where bounce would come from (a sunlit floor, a bright wall), as a cheap approximation.
- Screen-space GI or voxel GI for dynamic bounce ([final-image.md](final-image.md)).

**Build.**
1. Bake with final geometry and materials, and match the bake's sun to the runtime sun.
2. Give lightmapped meshes non-overlapping UVs with padding, usually in a second UV set that the lightmap selects with `channel` set to 1.
3. Place probes densely where light changes quickly (doorways, under overhangs), and keep them out of walls.
4. Remember that emissive surfaces light nothing nearby; add a real light where they should (next section).

**Critic checks.** PASS when interior corners and shaded areas keep visible detail and pick up color from nearby lit surfaces, unless the brief asks for darkness. FAIL signs: pitch-black corners in a sunlit room; uniformly gray shade with no bounce color; light leaking through walls.

**Diagnose.**
- Light leaks → probes inside walls, or overlapping lightmap UVs.
- Seams along lightmap UV edges → too little padding.
- Moving objects lit differently from their surroundings → no probes for dynamic objects.

**API facts** (check the installed version):
- Since r151, AO maps and lightmaps read the UV set chosen by their texture's `channel` (0 is `uv`, 1 is `uv1`), so they no longer require a second UV set (verified on r186).
- `LightProbeGrid`, the WebGPU version (`LightProbeGridWebGL` for `WebGLRenderer` since r186), is a light added to the scene. It applies baked spherical-harmonic irradiance to every lit node material, and it bakes on the GPU (verified on r186).

## Practical and many lights

**Goal.** Lamps, screens, neon and headlights light what they visibly shine on, and their glow matches their importance.

**Build.**
1. Pair each emissive practical with a real light wherever it should illuminate its surroundings, and rank emissive brightness for bloom ([final-image.md](final-image.md)).
2. Give shadows only to the practicals that matter: a shadowed point light renders six faces.
3. Use rectangular area lights for soft windows, panels and screens.
4. Many point lights need a lighting system built for them (facts below).

**Critic checks.** PASS when practical lights visibly light the walls, floor and objects they face, and the brightest glow belongs to the most important source. FAIL signs: glowing lamps that light nothing; screens with no spill; every emitter equally bright.

**API facts** (check the installed version):
- `ClusteredLighting` (Forward+ clustered shading, which replaces `TiledLighting`, removed in r185) handles many point lights with real depth complexity, and `DynamicLighting` lets the light count change without recompiling materials. Both are set through `renderer.lighting` on `WebGPURenderer` (verified on r186).

## Symptom → cause

| Symptom | Likely cause | First check |
| --- | --- | --- |
| Flat, frontal-looking light | key too close to the camera axis | key direction in a clay pass |
| Shadows filled to gray | ambient raised to fix dark shadows | key-to-fill ratio |
| Black or flat gray metal | no environment light | `scene.environment` |
| Objects look pasted in | environment doesn't match the backdrop | one environment for both |
| Two sun highlights | sun in the HDR image and in a light | hide or clamp the image's sun |
| Shadows disagree with the sky's sun | separate sun descriptions | the shared sun contract |
| No shadows at all | shadow map disabled, or `castShadow` missing | `renderer.shadowMap.enabled`, casters, light |
| Crawling shadow edges | no texel snapping | shadow camera updates |
| A line across the ground where shadows soften | cascades without blending | `fade`, or `SunLight` |
| Acne stripes | bias too low for the cascade | `normalBias` per cascade |
| Floating shadows | bias too high, often values from before r183 | lower `bias` and `normalBias` |
| Frozen shadows | cached map never refreshed | `shadow.needsUpdate` on change |
| Still shadows under swaying plants | shadow pass skips the displacement | shadow position nodes ([materials.md](materials.md)) |
| Objects hover or sit on the ground like stickers | no contact darkening | `sss()`, AO, contact shadows |
| Pitch-black interior corners | no bounce | probes, lightmaps or fills |
| Light leaking through walls | probes inside walls, overlapping lightmap UVs | probe placement, UV layout |
| Lamps that light nothing | emissive without a real light | paired practical light |
