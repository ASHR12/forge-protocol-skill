# Three.js effects: particles, fire, light and screen surfaces

API facts verified on r186 (2026-10-05). Check the installed version first; if it differs, confirm in the official docs or the installed source. The installed version wins.

Read this when the goal includes effects: particles, sparks, fire and smoke, explosions, trails and beams, magic and holograms, lens flare, decals, raymarched volumes, or frost and rain on glass. Bloom and the final image are in [final-image.md](final-image.md).

## Contents

- Designing an effect
- Particles: CPU, GPU and pools
- Sparks, debris and impacts
- Fire and smoke
- Explosions and shockwaves
- Trails, ribbons and beams
- Energy, magic and holograms
- Lens flare and glare
- Screen-space surfaces: frost and rain on glass
- Decals and residue
- Raymarched volumes in general
- Symptom → cause

## Designing an effect

**Goal.** An effect looks authored when all of it comes from one event: it starts at a cause, moves through one field, and fades on a plan.

**Build.** Write the effect as a chain before building any layer:
1. Event: what starts it, where, in which direction, and how strongly.
2. Envelope: how its intensity rises and falls over time.
3. Motion field: what moves the pieces, whether the event's own direction, gravity, wind or a flow field.
4. Representation: particles, ribbons, meshes, volumes or a screen-space layer.
5. Shading: emission, lit smoke, refraction.
6. Lifetime: when each piece dies, with normalized curves over age (0 at birth, 1 at death).
7. Contribution: how bright it is relative to the rest of the HDR frame, ranked against other emitters before bloom ([final-image.md](final-image.md)).

**Watch for.** Layers that only share a color; each layer needs a job (silhouette, motion, light or residue). Secondary pieces that ignore the main motion. Randomness without a seed, which breaks repeatable captures.

**Critic checks.** PASS when effects visibly start at their cause (a muzzle, an impact point, a nozzle), their parts move in one coherent direction, and their shape still reads in the no-post still. FAIL signs: effects popping into empty air, layers drifting apart, glow-only blobs.

## Particles: CPU, GPU and pools

**Goal.** Particles stay cheap, stable and well ordered: no stutter on bursts, no hard edges against surfaces, no layering errors.

**Choose.**
- CPU updates into instanced attributes for up to a few thousand particles, or when game logic needs each one individually.
- GPU compute over storage buffers for tens of thousands and more, or when particles react to fields every frame.
- Analytic GPU particles, whose position is computed from spawn time, start velocity and acceleration with no stored state, for simple ballistic bursts.

**Build.**
1. Preallocate a fixed pool. Spawning writes into free slots; when a particle dies, move the last live one into its slot, copying all of its per-instance data, and draw only the live count.
2. Drive size, color and opacity from normalized age.
3. Face particles toward the camera, or stretch them along their velocity for sparks and streaks.
4. Blend pure light additively, where order doesn't matter. Smoke needs alpha blending drawn back to front: sort small sets on the CPU, and use hashed or weighted-blended transparency for large ones.
5. Fade particles where they approach opaque geometry (soft particles) by comparing their depth with the scene's.
6. Watch overdraw: large transparent sprites close to the camera cost the most, so shrink or thin them there, or draw particles at reduced resolution.

**Critic checks.** PASS when particles fade softly where they meet floors and walls, smoke and fire layer in a plausible order, and no sprite rectangles show. FAIL signs: hard lines where sprites cut through geometry, square sprite edges, layers popping in front of each other.

**API facts** (check the installed version):
- Both renderers sort transparent objects as whole objects, by `renderOrder` and then the depth of each bounding-sphere center; particles inside one instanced mesh draw in buffer order (verified on r186).
- TSL's `instancedArray(count, type)` creates a per-instance storage buffer that `renderer.compute()` passes write and materials read, on the WebGPU renderer (verified on r186).
- `BufferAttribute.addUpdateRange()` uploads only the changed span; it replaced `updateRange`, which was deprecated in r159 and removed in r169 (verified on r186).
- On node materials, soft particles can fade by the gap between `viewportLinearDepth` (the scene) and `linearDepth()` (the particle) (verified on r186).

## Sparks, debris and impacts

**Goal.** An impact reads as a physical event: a flash, sparks thrown from the contact, pieces that fall and settle, and marks left behind.

**Build.**
- Sparks: very bright cores stretched along their velocity, thrown in a cone around the surface's mirror direction, slowed by drag, pulled down by gravity, bouncing once, and cooling from white through orange to dark red within a short life.
- Debris: chunks that tumble, inherit their source's motion (including the spin of a rotating object), bounce, settle, and then dissolve or fade.
- A flash of real light with a short envelope, a puff of dust, and a residue decal.
- Seeded variation, so repeated impacts differ.

**Critic checks.** PASS when sparks spray from the contact point around the surface's mirror direction and fall under gravity, nearby surfaces light up briefly, and a mark remains afterwards. FAIL signs: sparks bursting evenly in every direction, no lighting response, no aftermath.

## Fire and smoke

**Goal.** Fire is hot gas: brightest and whitest at its core, tapering into licking tongues, and feeding smoke that is lit from below as it rises, spreads and fades.

**Choose.**
- Flipbook sprites (pre-simulated frames) for distant or numerous fires, such as torches and campfires.
- Procedural shaders on cards or simple volumes for stylized or mid-distance fire.
- A GPU fluid volume (velocity, density, temperature, pressure) for a hero fire that must react to objects and wind.

**Build.** Map temperature to color along a hot-body ramp and to emission, and map density to opacity. Let heat rise by buoyancy and add swirling turbulence so tongues lick and break apart. Keep smoke separate from flame, lit and absorbing, never additive. Wrap fire around colliders. Put a flickering light of matching color at the fire's heart, and add heat shimmer above when the shot calls for it.

**Watch for.** Additive sprites stacking into a white blob, visible repeats in looping flipbooks, glowing smoke, fire passing through walls, and a steady light under a flickering fire.

**Critic checks.** PASS when flames are brightest at the base and taper into orange tongues that break up, smoke above is darker and lit from below, the surroundings flicker with the fire's light, and no sprite edges show. FAIL signs: a glowing blob, visible cards, glowing smoke, flames passing through objects.

**API facts** (check the installed version):
- `Storage3DTexture` holds 3D fields that compute passes write and materials sample, the usual home for a voxel fire; it needs the WebGPU backend, not the WebGL fallback (verified on r186).

## Explosions and shockwaves

**Goal.** An explosion is staged in time: each beat has its own shape, speed and lifetime, and the whole sequence scales with the explosion's size.

**Build.**
1. Flash: the brightest moment, a frame or two long, with real light.
2. Fireball: expands fast, then slows, cooling as it turns to smoke.
3. Smoke: rises more slowly and lingers.
4. Debris: launched at the start under gravity, trailing smoke when large.
5. Shockwave: a ring of distortion and ground dust expanding at a steady speed.
6. Light pulse: decays on the surroundings, while camera shake runs on its own envelope.
7. Aftermath: scorch decals and drifting smoke.

Larger explosions unfold more slowly, and the sound of a distant one arrives late.

**Critic checks.** PASS when walkthrough frames show a flash, then an expanding fireball turning into rising smoke, debris arcs, a ground ring, and fading light on the surroundings. FAIL signs: a single sprite burst, every beat starting and ending together, no aftermath.

## Trails, ribbons and beams

**Goal.** Trails follow their source's path and taper to nothing; beams have a hot core inside a softer sheath and touch what they hit.

**Build.**
- Trails: record positions by distance traveled rather than per frame, build a camera-facing strip from them, smooth sharp turns, and taper width and opacity with age. Contrails widen and drift with the wind.
- Beams: an HDR core line inside a softer glow, a slight flicker in width, a flare where they strike, and light cast on the surroundings.

**Watch for.** Trails whose length changes with frame rate, kinks at sharp turns, ribbons that vanish when seen edge-on, and beams that stop short of their target.

**Critic checks.** PASS when trails taper smoothly and follow the motion path without kinks, and beams show a bright core inside a softer sheath with visible contact where they end. FAIL signs: uniform-width strips, trails that vanish edge-on, beams floating short of their target.

**API facts** (check the installed version):
- Both renderers ignore `linewidth` and always draw 1-pixel lines; for width, use `Line2` with `LineMaterial` on WebGL, or the `Line2` in `lines/webgpu/` with `Line2NodeMaterial` on WebGPU (verified on r186).

## Energy, magic and holograms

**Goal.** Projected or magical light reads as light rather than solid matter: rims brighter than centers, crisp but stable bands, and transitions that never double up.

**Build.**
- Make holograms rim-lit shells: brightness from the viewing angle, additive blending, no depth writes.
- Put scanlines in world or object space and filter them by pixel footprint. As bands shrink below a pixel, fade them toward their average brightness, not to black.
- Make glitches rare, gated bands that travel through the shape, not constant noise everywhere.
- Drive shape-to-shape transitions with one sweep value over the combined bounds of all the shapes, with complementary masks so two shapes never overlap.
- Shape magic from the caster's motion, with particles following the same field and a limited palette ranked in HDR.
- Measure rim angles with the normal matrix, so stretched objects still light at their silhouettes.

**Critic checks.** PASS when hologram edges glow brighter than face-on centers, scanlines stay crisp up close and smooth at a distance without moiré, and transitions sweep cleanly with no double-bright overlap. FAIL signs: moiré, flat sheets of color, constant flicker, a brightness spike mid-transition.

## Lens flare and glare

**Goal.** A flare is a lens responding to an extremely bright source: a small set of ghosts on the line through the frame center, fading when the source hides.

**Build.**
- Trigger flares only from HDR sources: the sun, explosions, lamps seen directly.
- Place ghosts on the line from the source through the image center, in a small finite set with varied sizes and subtle color.
- Flatten ghost shapes as the source moves toward the frame edge.
- Fade them as the source leaves the frame or goes behind something.
- Keep the effect subtle and in one lens style.

**Critic checks.** PASS when ghosts line up through the frame center, disappear when the source is hidden, and stay subordinate to the image. FAIL signs: flares through walls, long chains of identical sprites, flares with no visible source.

**API facts** (check the installed version):
- `Lensflare` works with the WebGL renderer and `LensflareMesh` with the WebGPU renderer; the `lensflare()` TSL node instead builds ghosts from a bloom pass's output (verified on r186).

## Screen-space surfaces: frost and rain on glass

**Goal.** View-aligned surfaces (a window, a visor, a camera lens) bend and blur the scene behind them, and change at the same rate on any display.

**Choose.**
- Persistent history, two render targets swapped every frame, when the state depends on past input: frost cleared by touch, wiped condensation, paint on glass.
- Analytic state, a function of time and coverage, when the look runs on its own schedule, such as drops sliding down a window.
- Keep world footprints and object paint out of screen space; they belong to the surfaces they mark.

**Build.** Render the scene, make a blurred copy at reduced resolution, derive the surface field (a frost mask or drop coverage), take normals from that same field, then refract and blur the scene through it. For history, use half-float targets, read the previous state and write the next, decay by a rate times elapsed time, and decide what resizing and resetting do. Generate static textures once.

**Watch for.** Decay per frame instead of per second, which thaws twice as fast at 120 Hz; drops sampled in texture space, so they stretch with the background; refraction from unrelated noise; blur sized in CSS pixels while the shader works in device pixels.

**Critic checks.** PASS when drops and frost show the scene behind them bent and blurred, running drops leave trails, and cleared areas regrow gradually across walkthrough frames. FAIL signs: painted drops with no refraction, frost as a flat white overlay, regrowth that snaps back.

**API facts** (check the installed version):
- `viewportSharedTexture()` gives node materials a shared copy of the frame drawn so far, the cheap way to refract or blur what lies behind a pane (verified on r186).
- `MathUtils.damp(x, y, lambda, dt)` smooths toward a target independently of frame rate (verified on r186).

## Decals and residue

**Goal.** Events leave marks that sit on surfaces, follow their shape, and fade over time.

**Build.** Project decals for impacts, scorch, footprints and splashes, aligned to the surface normal with a random rotation. Change roughness and normals as well as color: scorch is dark and rough, a splash is glossy. Keep a capped pool and fade the oldest marks. On skinned or animated targets, paint into a texture instead. On terrain displaced in the shader, which a decal mesh can't see, draw ground marks and dust in the terrain material or place them from its CPU height copy ([terrain.md](terrain.md), Collision and height parity); footprints that sink in are a heightfield ([special-materials.md](special-materials.md), Granular and deformable ground).

**Critic checks.** PASS when marks lie on their surfaces, follow the curvature, and fade over time. FAIL signs: floating or flickering decals, marks stretched across corners.

**API facts** (check the installed version):
- `DecalGeometry` cuts its mesh from the target's stored vertices when it is created (no skinning or shader displacement) and can stretch around corners; give its material `polygonOffset` so it doesn't z-fight (verified on r186).

## Raymarched volumes in general

**Goal.** Marched volumes (smoke, clouds, nebulae, aurora, fog, bent space) look smooth and solid when the march is bounded, jittered, and capped with a defined result.

**Build.**
1. Bound the domain (a box, sphere or slab), march only between its entry and exit, and stop at scene depth.
2. Pick a step policy: uniform steps inside a tight, bounded slab; adaptive steps where density or bending changes quickly.
3. Test thin features (disks, sheets, shells) for crossings between samples, rather than hoping a sample lands inside them.
4. Accumulate front to back with transmittance, and stop once the result is nearly opaque.
5. Jitter each pixel's starting point, then hide the noise with temporal accumulation or a small blur.
6. Cap the iterations, and decide what a capped ray returns.
7. Sample textures at explicit mip levels inside the loop, and run expensive volumes at reduced resolution with depth-aware upsampling.

**Critic checks.** PASS when volumes show smooth density without onion-ring banding, clean edges against geometry, and no speckle in the hardest regions. FAIL signs: stepped rings, sparkling noise, halos around foreground objects.

**API facts** (check the installed version):
- `VolumeNodeMaterial` (WebGPU) marches its mesh with a fixed `steps` count (default 25) and takes an `offsetNode` to jitter each pixel's start (verified on r186).
- TSL texture nodes take an explicit mip through `.level()` or explicit gradients through `.grad()`; use them for lookups inside loops and branches (verified on r186).

## Symptom → cause

| Symptom | Likely cause | First check |
| --- | --- | --- |
| An effect pops into empty air | no event origin; spawning not tied to its cause | the spawn points drawn against the cause |
| Layers of one effect drift apart | each layer moved by its own field | which field moves each layer |
| Stutter on every burst | allocating per burst instead of pooling | allocations during a burst in a profile |
| Old effect state shows on new particles | pool slots reused without copying all per-instance data | the per-instance attributes copied when a particle dies |
| Hard lines where sprites meet surfaces | no soft-particle depth fade | the depth fade near geometry |
| Smoke and fire swap order | transparent sorting per object, not per particle | how the effect is split into sorted objects |
| Frame rate drops near effects | overdraw from large transparent sprites near the camera | an overdraw heat map |
| Fire is a white blob | additive layers stacking, with no temperature or density structure | the temperature and density fields shown alone |
| Smoke glows | smoke blended additively instead of lit and absorbing | the blending mode of the smoke material |
| Sparks spray in every direction | velocities not tied to the surface and impact direction | spawn velocities against the surface normal |
| Trails change length with frame rate | history recorded per frame instead of by distance | the same trail at two frame rates |
| Scanlines shimmer into moiré | bands not filtered by pixel footprint | the bands at a distance across consecutive frames |
| Flares show through walls | no occlusion test on the source | the flare with its source hidden |
| Frost thaws faster on fast displays | decay per frame instead of per second | the same thaw at two frame rates |
| Decals flicker | coplanar with the surface; no polygon offset | `polygonOffset` on the decal material |
| Volumes show banding rings | no start jitter, or steps too coarse | a step-count heat map |
| Speckle in a marched effect | capped rays with no defined result | a view of the rays that hit the cap |
