# Three.js water

API facts verified on r186 (2026-10-05). Check the installed version first; if it differs, confirm in the official docs or the installed source. The installed version wins.

Read when any water appears: puddles, pools, rivers, lakes, coasts, oceans or underwater views. The ground beneath and around the water is in [terrain.md](terrain.md); rain and the weather state are in [sky-and-weather.md](sky-and-weather.md).

## Contents

- Choosing a water type
- Waves and surface motion
- Reflections and refraction
- Absorption and color
- Foam
- Shores
- Caustics and light shafts
- Underwater
- Buoyancy and interaction
- Rivers, waterfalls and puddles
- Symptom → cause

## Choosing a water type

**Goal.** Pick the representation that owns the view. Water is moving geometry, a surface orientation that bends and reflects light, and a body that absorbs it; a blue transparent material is none of these.

**Choose.**
- **Puddles and wet ground:** a material change on the ground (darker, glossier, flatter, rippling) driven by the weather state; see Rivers, waterfalls and puddles.
- **Pools, fountains and tanks:** a bounded volume. Use a heightfield simulated in compute for interactive ripples, with depth-based absorption and caustics.
- **Calm lakes and ponds:** a flat surface with normal-mapped waves, planar or screen-space reflection, depth absorption and shore foam.
- **Rivers and streams:** a surface driven by a flow map along the current, with foam at obstacles and banks.
- **Open ocean as a hero:** a spectral surface computed with FFTs in two or three wavelength bands, with choppy horizontal motion and foam where the surface compresses; a few long swells underneath; noise blended in toward the horizon. It needs compute.
- **Stylized or secondary seas, phones, and the WebGL 2 fallback:** a sum of Gerstner (trochoidal) waves, which is analytic, cheap and exact to query on the CPU, but looks periodic with too few waves or aligned directions.
- **Beaches and coasts:** an ocean surface coupled to the terrain's depth, a moving waterline, wet sand and shore foam; see Shores.
- **Underwater views:** a camera-medium state that switches the whole frame's optics; see Underwater.

**Watch for.** A handful of analytic waves is a different representation from a spectral ocean, not its low tier; name it honestly in the plan and the quality tiers. three.js ships no spectral ocean, so plan either to write one or to choose Gerstner waves.

**Critic checks.** PASS when water shows color and clarity that change with depth, reflection that changes with viewing angle, and motion at more than one scale. FAIL signs: a flat, uniformly transparent blue plane; the same clarity at every depth; a still mirror where the brief describes moving water.

**API facts** (check the installed version):
- three.js ships no FFT ocean; the official `webgpu_ocean` example is a flat, normal-mapped, reflective `WaterMesh` with `SkyMesh` and bloom (verified on r186).
- `WaterMesh` (flat reflection) and `Water2Mesh` (reflection, refraction and flow maps; its class is also named `WaterMesh`) work only with `WebGPURenderer`; the WebGL renderer uses `Water` and `Water2` (verified on r186).
- `WaterMesh`'s reflection resolution is `resolutionScale` (renamed from `resolution` in r181), defaulting to 0.5 (verified on r186).

## Waves and surface motion

**Goal.** One wave evaluation drives the geometry, the normals, crest foam and every CPU height query, with several scales and directions, so the surface reads as one body of water and never as a repeating tile.

**Choose.**
- **Spectral bands:** realistic open sea. Split wavelengths into disjoint bands (long swell, mid chop, short ripples), each with its own patch size, all from one sea state and one seed. A single patch repeats visibly at distance.
- **Gerstner sum:** a modest set of waves with spread directions and wavelengths. Steepness sharpens crests, and the horizontal motion makes troughs broad and crests narrow.
- **Scrolled normal maps** (two or more scales and directions): calm water and far fields. They change no silhouettes, so avoid them where waves should break the horizon line.
- **A simulated heightfield** (a wave equation on a grid): bounded, interactive water.

**Build.**
1. Evaluate displacement in world space, so neighboring tiles and distant patches share phase.
2. Derive normals from the same waves (the analytic gradient, or the spectral slope maps corrected for horizontal displacement), never from an unrelated normal texture.
3. Add sub-resolution ripples only as normal detail below the smallest resolved wave, and fade them by pixel footprint so they don't sparkle.
4. Tessellate where the camera is: a camera-following grid, finer near the camera and snapped to world increments so it doesn't swim. Make far waves, fog or haze hide the mesh's edge before it can show.
5. For a spectral surface, test the transform on inputs with known answers (a constant, and a single frequency) before connecting the spectrum. If it fails, stop and fix the transform; never tune the spectrum or shading around it.
6. Expose debug views: height, normals, each band alone, and the foam state.

**Watch for.** Waves all traveling one way read as corrugated sheet; spread the directions. Vertex-displaced waves need the velocity check: view the velocity buffer, and if the waves ghost or smear under temporal AA, supply the previous frame's displaced position ([final-image.md](final-image.md), Temporal AA, upscaling and motion vectors).

**Critic checks.** PASS when at least three scales of motion read (swell, chop, ripples), waves come from more than one direction, crests are sharper than troughs, and no repeating tile shows toward the horizon. FAIL signs: a square repeating pattern; parallel stripes; an egg-crate of identical bumps; a horizon where the water's edge or a flat silhouette shows.

**Diagnose.**
- Square repeating pattern → a single band size, or the camera sees too many repeats of one patch.
- Parallel stripes → directional spread too narrow, or wind waves and swell share one angle.
- Shading lags the geometry → normals and displacement come from different evaluations or stale maps.
- Corrupted blocks in spectral water → no barrier between transform stages.

**API facts** (check the installed version):
- The official `webgpu_compute_water` example simulates a heightfield in compute with `instancedArray` buffers swapped each step, and floats objects on it (verified on r186).
- The official `webgpu_tsl_raging_sea` example displaces a plane in `positionNode` with TSL noise and rebuilds normals by sampling the same function at neighboring points (verified on r186).

## Reflections and refraction

**Goal.** Water reflects the sky and scenery that are really there, more strongly at grazing angles and distorted by the waves; through clear water you see the bottom, bent by the surface, with no foreground objects bleeding in.

**Choose.**
- **Environment reflection** from a prefiltered sky: the base layer everywhere, and the fallback for every other method.
- **Planar reflection** (a mirrored camera render): flat water whose nearby objects must reflect sharply. It costs a second scene render, so render it at reduced resolution.
- **Screen-space reflection:** no extra scene render, but it misses whatever is off screen, so always keep the environment fallback underneath. Its default single-ray mode weights reflections by metalness, so water reflects nothing in it; use the stochastic mode, which reflects dielectrics by Fresnel, or feed a reflectivity mask in place of metalness. Setup and pass order are in [final-image.md](final-image.md).
- **Screen-space refraction** (the scene color behind the surface, offset by the wave normal and depth-tested): pools, lakes and shallows seen from above.

**Build.**
1. Blend reflection and the transmitted body by Fresnel. Water reflects about 2% looking straight down and nearly everything at grazing angles; never use a constant opacity.
2. Reflect the environment, then add planar or screen-space reflection for nearby objects, distorted by the wave normal and less so with distance.
3. Refract by sampling the scene behind at UVs offset by the normal, and reject any sample whose scene depth lies in front of the water, falling back to the unshifted UV.
4. Add a sun glint from the same sun as the sky, and widen it with distance or roughness so it doesn't alias into sparkle.
5. Make the reflected sky and the visible sky one function, with the same sun direction and color, so reflections never look pasted on.

**Watch for.** Mirror-perfect reflections on choppy water; reflections that don't move with the waves; screen-space reflections cut off at the screen edges; water that ignores the fog the land receives.

**Critic checks.** PASS when grazing views reflect more of the sky and scenery than steep views, reflections distort with the waves and match the visible sky and nearby objects, the sun glint sits under the visible sun, and clear water shows the bottom bent by the surface. FAIL signs: constant opacity; reflections of a different sky; foreground objects smeared into the refraction; reflection holes at screen edges.

**Diagnose.**
- Foreground objects bleed into the refraction → offset UVs are not depth-tested.
- Reflections vanish at screen edges → screen-space reflection with no environment fallback.
- Glint in the wrong place or color → sky and water use different sun parameters.

**Start here** (adjust to the goal): render planar reflections at half resolution.

**API facts** (check the installed version):
- With `WebGPURenderer`, use the TSL `reflector()` node for planar mirrors (its options include `resolutionScale`); the `Reflector` object is the WebGL renderer's version (verified on r186).
- For screen-space refraction, build the effect in the material's `backdropNode`, sample `viewportSharedTexture` at offset UVs and depth-test against `viewportDepthTexture`; the official `webgpu_backdrop_water` example does exactly this (verified on r186).

## Absorption and color

**Goal.** Water color comes from depth. Shallow water is clear and shows the color of its bed; deeper water loses red first, then green, toward blue-green; particles in suspension add a body color; and thin crests glow where light passes through them.

**Build.**
1. Measure thickness along the view: the linear depth of the scene behind minus the linear depth of the water surface, or a known depth near the shore.
2. Absorb each color channel exponentially with thickness, red fastest, and add an in-scattered color that grows with thickness toward the water's body color.
3. Fade opacity to zero as thickness approaches zero at the shore, so the edge dissolves into wet ground.
4. Brighten thin crests lit from behind (sun beyond the wave) with a light, saturated version of the body color.
5. Set the body color from the brief's water: clear tropical blue-green, a green-brown lake, a deep blue ocean.

**Watch for.** A fixed fallback depth passed off as measured thickness; distance fog standing in for absorption, when haze over the water and absorption within it are separate effects.

**Critic checks.** PASS when water near the shore is visibly clearer and lighter than deep water, with a gradual transition, and crests lit from behind show a lighter, more saturated color. FAIL signs: the same transparency at every depth; a hard line where the water meets its bed; muddy gray water.

**Diagnose.**
- Plastic blue → no depth absorption, and constant opacity.
- A hard shore line → no thickness fade, or the depth texture isn't sampled.

**API facts** (check the installed version):
- `viewportLinearDepth` minus the surface's own `linearDepth()` gives water thickness along the view; the `webgpu_backdrop_water` example computes it this way (verified on r186).

## Foam

**Goal.** Foam marks where water is stressed (breaking crests, shores, obstacles and wakes); it builds quickly and fades slowly.

**Build.**
1. Take foam from causes: crest compression (the spectral surface's fold measure, or Gerstner steepness), shallow depth at the shore, contact where objects cut the surface (a small depth difference), and wakes behind movers.
2. Keep foam as state: a texture or buffer, updated every frame, that jumps toward the current source and recovers slowly. Never recompute all foam from scratch each frame.
3. Shade it last: break the continuous foam field into a bubble pattern only when shading, and let foam change the surface's response (rougher, brighter, opaque) instead of laying a white texture on top.
4. Fade foam detail by pixel footprint at distance.

**Critic checks.** PASS when foam sits on crests, along shores and around obstacles, and across walkthrough frames it forms, spreads and fades gradually. FAIL signs: uniform white noise; foam scrolling independently of the waves; foam blinking between frames; no foam where breaking waves meet the shore.

**Diagnose.**
- White speckle → the finest band is thresholded without persistent state.
- Foam vanishes instantly → no persistent state.
- Foam never clears → the recovery term is wrong or clamped.

## Shores

**Goal.** Water and land meet as one system: the waterline moves with the waves, sand darkens and gleams where the water has just left, foam lines follow the coast, and no hard intersection line shows.

**Build.**
1. Know the water depth over the terrain everywhere (the terrain's height below the water level, plus wave height), and drive opacity, color, foam and wave damping from it.
2. Shoal the waves: shorter and steeper as the depth drops, damped in very shallow water, with crests turning toward the shore.
3. Run a thin sheet of water up and down the beach, timed by the incoming waves, and leave a wet band behind it.
4. Make the wet band darker, smoother and flatter, drying back over time, with the same wetness rule as other wet surfaces ([materials.md](materials.md)).
5. Carry shore foam lines with the moving waterline.

**Watch for.** A static decal for the wet band; a hard line where the water plane crosses the terrain; an orbit camera that can dip below the terrain and expose the edges of the water mesh.

**Critic checks.** PASS when no hard intersection line shows, the waterline moves with the waves across frames, and the wet band is darker and glossier than dry ground. FAIL signs: a hard waterline; a frozen shoreline; wet sand that darkens but stays matte.

**Diagnose.**
- A hard line at the shore → no depth-based opacity fade or shore foam.
- A frozen beach → swash and the wet band aren't driven by the wave state.

## Caustics and light shafts

**Goal.** Under clear, shallow water, light focused by the waves dances over the bed and submerged objects; underwater, shafts of light slant down from the surface. Both follow the actual surface and fade with depth.

**Build.**
1. Derive caustics from the water's own normals, either computed from the surface or as an animated pattern tied to the wave motion, and project them through the light onto surfaces below the water only.
2. Fade them with depth, and toward their mean brightness at distance (never to black, or the bed darkens as the camera pulls back).
3. Add light shafts only below the surface or in murky water, and keep them subtle; [final-image.md](final-image.md) covers god-ray passes.

**Critic checks.** PASS when caustics appear only on underwater surfaces, move with the waves and fade with depth. FAIL signs: caustics above the waterline; static or scrolling patterns unrelated to the waves; caustics as bright as the sunlit surface above.

**API facts** (check the installed version):
- The official `webgpu_caustics` example projects caustics through a spot light's shadow map with `castShadowNode`, which requires `renderer.shadowMap.transmitted = true`, and sets the shadow `mapType` to `HalfFloatType` for HDR caustics; `webgpu_volume_caustics` covers the volumetric case (verified on r186).

## Underwater

**Goal.** Being underwater feels like being inside a medium: color shifts toward blue-green with distance, visibility is limited, the surface seen from below shows a bright window to the sky ringed by mirrored water, and particles drift.

**Build.**
1. Decide above or below from one camera-medium state for the whole frame, never per triangle or by which way a face points.
2. Add absorption fog in the water's color by distance, plus in-scattered light that fades with depth.
3. Seen from below, show a refracted window to the sky within about 49° of vertical (water's critical angle), and outside it total internal reflection that mirrors the bright water below, never black.
4. Close distant sightlines with geometry (a rising seabed, rocks) rather than a hard fog wall.
5. Add drifting particles, caustics on the bed and light shafts.
6. Handle the camera crossing the surface: a waterline across the lens and a short blend between the two optics.

**Watch for.** Screen-space refraction offsets hold only for a bounded volume seen from air. A camera that crosses an open surface needs refraction solved per vertex, or none.

**Critic checks.** PASS when color and contrast fall off with distance toward the water tint, the surface from below shows both the bright window and the mirrored ring around it, and particles or shafts give depth. FAIL signs: underwater views as clear as air; a black ceiling outside the window; a hard horizon line of fog.

**Diagnose.**
- Black ceiling outside the window → total internal reflection isn't given the color of the lit water.
- Wrong optics on part of the frame → the medium is decided per draw or per face instead of once per camera.

## Buoyancy and interaction

**Goal.** Floating things ride the waves the camera sees, and moving things leave traces: ripples, wakes and splashes.

**Build.**
1. Sample the wave height at several hull points around the waterline, compute a buoyant force at each from how deep it sits, and integrate with damping; bob, pitch and roll follow.
2. Get heights from the Gerstner sum evaluated on the CPU (exact); from a low-resolution readback of the spectral displacement, which arrives late but is dominated by the large waves anyway; or from a simulated heightfield read back.
3. Add a local interaction layer on top of the base waves (ripples or a small simulated grid around the player) for wakes and impacts, with splash particles and foam at entry points.
4. Hide water inside hulls with a hull mask or distance field.

**Critic checks.** PASS when floating objects bob and tilt with the local waves, movers leave wakes or ripples that spread and fade, and no water shows inside boats. FAIL signs: objects riding rigidly while waves pass; boats full of water; wakes that never spread.

**API facts** (check the installed version):
- `renderer.getArrayBufferAsync()` reads a storage buffer back to the CPU, and `readRenderTargetPixelsAsync()` reads a render target; both return promises, so plan for heights that arrive late (verified on r186).

## Rivers, waterfalls and puddles

**Goal.** Flowing water runs downhill along its channel, piles foam against obstacles and banks, and mists where it falls; puddles are wet ground with water collected in the low spots.

**Build.**
1. For rivers, author or derive a flow map (direction and speed along the channel) from the terrain's flow field ([terrain.md](terrain.md)) or a spline, and scroll two normal layers along it, cross-faded on offset phases so the stretching never shows.
2. Make water glassy and slow on the insides of bends, faster and rougher at narrows and drops, with foam where the flow hits rocks and banks.
3. Build waterfalls as a sheet of flowing geometry streaked along the fall, with foam, mist particles and a ring of ripples at the base.
4. Puddles: a mask from low terrain curvature or paint, filled as the weather's wetness rises; inside, near-mirror roughness and a flat normal with rain ripples; at the rim, darkened wet ground ([materials.md](materials.md) covers wet surfaces).

**Critic checks.** PASS when river surface patterns move downstream consistently, foam gathers at obstacles and banks, and puddles reflect the sky and ripple in rain. FAIL signs: water flowing uphill, or one way regardless of the channel; visible pulsing as normal layers reset; puddles that are only darker ground.

**API facts** (check the installed version):
- `Water2Mesh` reads an RG `flowMap` (or one `flowDirection`) and cross-fades two phases of its normal maps at `flowSpeed` (verified on r186).

## Symptom → cause

| Symptom | Likely cause | First check |
| --- | --- | --- |
| Flat, plastic blue water | no depth absorption, no Fresnel, constant opacity | a thickness view, and a grazing still |
| A hard line where water meets land | no thickness-based fade or shore foam, or the depth texture isn't sampled | a thickness view at the shore |
| Square tiles repeating toward the horizon | one wave band size, with no other bands or distance noise | each wave band shown alone |
| Parallel stripes of waves | directional spread too narrow, or swell and wind waves share an angle | the wave directions in use |
| Normals move but the silhouette doesn't | normal-map-only water where displacement was needed | a wireframe or silhouette view |
| Shading lags the waves | normals and displacement from different evaluations | where the normal is computed |
| The water mesh's edge shows at the horizon | no fog or far waves covering the mesh boundary | fog distance against the mesh extent |
| Reflections show a different sky, or the glint is off-sun | sky and water use different sun or sky functions | the sun parameters each one reads |
| Reflection holes at screen edges | screen-space reflection with no environment fallback | the frame with screen-space reflection off |
| Foreground objects smeared into refraction | refraction UVs offset without a depth test | a view of where refraction samples are rejected |
| Ghost trails on waves under temporal AA | motion vectors miss the vertex displacement | the velocity buffer on the water |
| White-noise foam | thresholding fine detail without persistent state | the foam state shown alone |
| Foam blinks out instantly, or never clears | foam state missing, or its recovery term wrong | the foam state across several frames |
| Wet sand darker but still matte | wetness changes albedo without lowering roughness | a roughness view of the wet band |
| Caustics above the waterline or static | caustics not masked to underwater surfaces, or not tied to the waves | the caustic term shown alone |
| Underwater view as clear as air | no absorption fog in the camera's medium | the medium state at the camera |
| Black ring around the window seen from below | total internal reflection given no water color | the underside with the window masked out |
| Boats full of water | no hull mask or distance field | the hull mask |
| Floating objects ignore the waves | buoyancy samples a different wave function than the surface, or one point only | CPU heights against the rendered surface |
| River normals pulse or stretch | flow layers not cross-faded on offset phases | the two flow-phase weights over time |
