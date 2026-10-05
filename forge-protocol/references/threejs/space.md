# Three.js space: scale, stars, planets and bent light

API facts verified on r186 (2026-10-05). Check the installed version first; if it differs, confirm in the official docs or the installed source. The installed version wins.

Read this for space and sci-fi goals: star fields, planets from orbit to close approach, suns, black holes, wormholes, nebulae and spacecraft effects.

## Contents

- Scale and precision
- Star fields and galactic skies
- Planets
- Atmospheres seen from space
- Suns and bright sources
- Black holes
- Wormholes and portals
- Nebulae and space volumes
- Spacecraft effects
- Symptom → cause

## Scale and precision

**Goal.** Space spans many orders of magnitude. Nearby craft must stay perfectly steady, far bodies must sort correctly, and the background must never drift or clip.

**Choose.**
- One conversion from real units (kilometers, astronomical units) to scene units, applied at a single boundary. Keep simulation state in high precision and render relative to the camera.
- A floating origin when the camera travels far: keep the camera near zero and move the world, re-centering whenever the camera drifts past a threshold. For an authored shot, compute the virtual camera pose, render with the camera at the origin, and offset the world by the inverse.
- For depth, a reversed depth buffer where it is supported, a logarithmic one otherwise, or separate depth ranges: far bodies in one pass, the near scene in another.
- Backgrounds (stars, galaxy, nebula sky) tethered to the camera position, so they show no parallax and never cross the far plane.

**Watch for.** Single-precision positions keep about seven significant digits, so a craft thousands of kilometers from the origin, in meters, jitters visibly. A tiny near plane wastes most of the depth precision.

**Critic checks.** PASS when nearby craft show no vertex wobble at any captured distance, far bodies never flicker through each other, and stars keep their relative positions while the camera translates. FAIL signs: shimmering geometry, flickering bands on distant bodies, stars sliding or vanishing at the far plane.

**API facts** (check the installed version):
- Both renderers take `logarithmicDepthBuffer` and `reversedDepthBuffer` at construction, and reversed depth on the WebGL renderer needs `EXT_clip_control` (verified on r186).
- Logarithmic depth writes depth per fragment. On the WebGL renderer that disables early depth testing, as its docs state (verified on r186); node materials write fragment depth for it too, so expect the same cost on `WebGPURenderer`, though that half is inferred, not documented.
- The WebGL option was spelled `reverseDepthBuffer` until r178 and renamed in r179; r186 silently ignores the old spelling (verified on r186).

## Star fields and galactic skies

**Goal.** A believable sky has a few bright stars above a dense scatter of faint ones, colors from blue-white to orange, a galactic band cut by dust, and stars that hold perfectly still as the camera turns.

**Choose.** A procedural sky on a camera-tethered sphere (resolution-independent and seedable), an HDR panorama (photographic but fixed), or points in 3D when nearby stars must show parallax during a flythrough.

**Build.**
1. Place stars as a function of direction with a seed, never per pixel.
2. Draw brightness from a heavy-tailed distribution, so faint stars vastly outnumber bright ones.
3. Color stars by temperature, and pull faint ones toward white, as the eye sees them.
4. Give each star a small footprint and spread its energy across it, so a sub-pixel star dims smoothly instead of flickering. Where stars outnumber pixels, blend toward the field's average brightness.
5. Add the band: a soft glow along a great circle, a brighter bulge toward the core, dust filaments that dim and redden whatever lies behind them, and a few nebula complexes along its length.
6. Keep bright stars in HDR so bloom treats them correctly. Stars don't twinkle in vacuum.

**Watch for.** Uniform white dots read as noise, point-sampled stars crawl in motion, cube faces show seams, and too many bright stars flatten the sky.

**Critic checks.** PASS when a few bright stars stand over many faint ones, colors range from blue-white to orange, stars stay steady across panning walkthrough frames, and the galactic band shows dark dust lanes. FAIL signs: uniform dots, flicker or crawl, visible seams, a snowstorm of equal stars.

**API facts** (check the installed version):
- On the WebGPU backend `Points` always draw 1-pixel points; for sized stars use a `Sprite` with a `PointsNodeMaterial` fed instanced positions, sized by its `sizeNode`, with `count` set to the number of stars (verified on r186).

## Planets

**Goal.** A planet is one set of fields on a sphere that drives its silhouette, color, roughness and normals together, and holds up from orbit to close approach.

**Choose.**
- Level of detail: a few whole-body resolutions with hysteresis for orbit and flyby views; a chunked quadtree on a cube-sphere for landing and surface travel, with seams stitched or skirted and every chunk positioned relative to the camera.
- Body type: solid worlds take the field stack below. Gas and ice giants take banded flow instead, kept out of the rocky stack: latitude bands rotating at different speeds, turbulence and storms along band edges, seamless longitude coordinates, and limb darkening.

**Build.**
1. Evaluate every field on the undeformed unit direction (store it as an attribute) times the radius. Warp sideways along the surface and renormalize; never warp along the radius.
2. Shape the macro silhouette first (continents, basins, mountain ranges) and judge it unlit.
3. Add named structures: craters with floors, walls, raised rims and ejecta; ridges; volcanoes; ice caps.
4. Derive the causes: slope, altitude, latitude, cavity, distance to the coast.
5. Assign broad biome regions from those causes: snow by latitude and height, deserts in dry bands, forest by moisture and warmth.
6. Feed displacement and normals from one height function, identical on the CPU and the GPU.
7. Fade fine detail with camera altitude and pixel footprint; never fade the macro silhouette.
8. Give rings radial density bands, the planet's shadow across them, and their own shadow on the planet.

**Watch for.** Continents as noise blobs, craters as dark circles, shading that implies relief the silhouette lacks, coasts that swim as the camera moves, chunk seams, pinched poles.

**Critic checks.** PASS when the unlit limb shows relief, craters show floors, walls and lit rims, coastlines stay put between frames, the same body reads from orbit and at close approach, and rings cast and receive shadows. FAIL signs: a smooth silhouette with painted mountains, flat dark crater discs, swimming coasts, visible chunk seams, unshadowed rings.

**API facts** (check the installed version):
- `IcosahedronGeometry`, like every `PolyhedronGeometry`, is non-indexed, so after displacement `computeVertexNormals()` returns flat facets. Weld with `mergeVertices()` first, after deleting the `uv` attribute, which otherwise keeps seam vertices apart (verified on r186).
- `LOD.addLevel(object, distance, hysteresis)` takes hysteresis as a fraction of the switch distance (verified on r186).

## Atmospheres seen from space

**Goal.** From orbit the atmosphere is a thin bright rim on the lit side, a soft warm terminator, and haze that softens surface detail toward the limb, all from the same model as the sky seen from the ground.

**Build.**
- Share one atmosphere description (planet center and radius, density falling with height, scattering colors, sun direction, units) between the shell seen from space, the surface haze, and the ground-level sky in [sky-and-weather.md](sky-and-weather.md).
- Let density fade out toward the top, so the rim thins into space instead of ending at a hard shell.
- As the camera descends, hand over from the shell to depth-based haze through one continuous blend.
- On the night side, dim city lights and other emissive surfaces through the same atmosphere.

**Watch for.** A uniform glowing halo, a hard outer edge, a rim color that differs from the surface haze, a pop on entry, and exposure used to hide brightness that is simply wrong.

**Critic checks.** PASS when the lit limb is a thin bright band fading into space, the terminator passes through warm tones, surface features near the limb fade into haze of the limb's own color, and descent frames show no pop. FAIL signs: a thick even halo, hard edges, different hues for rim and haze.

## Suns and bright sources

**Goal.** The sun is by far the brightest thing in frame, it lights every body from one consistent direction, and its glare behaves like a real optical response.

**Build.**
- Render the sun as an HDR disc with a compact glare, far brighter than anything else, so tone mapping and bloom treat it correctly.
- Give it a minimum footprint so it doesn't pop as it crosses pixel boundaries.
- Use its direction as the key light for every body.
- In vacuum, keep shadow sides deep, with only faint light reflected from nearby planets.
- Allow lens flares only from the sun, and hide them whenever a body occludes it ([effects.md](effects.md)).

**Critic checks.** PASS when the sun is the brightest element with a compact glare, every lit side faces it, shadow sides are deep, and flares vanish while it is occluded. FAIL signs: a flat white disc, bodies lit from different directions, soft fill light in deep space, flares showing through a planet.

## Black holes

**Goal.** The look comes from light paths bending around the hole: the background wraps into a ring around a dark shadow, and the far side of the disk appears above and below it.

**Choose.**
- Integrate light paths through curved space for hero shots and flythroughs.
- Use an artistic bending field for stylized looks, and describe it as stylized, not relativistic.
- Use screen-space distortion only for distant views where the hole is small.

**Build.**
1. Bound the effect with a sphere and start each ray where it enters.
2. Step each ray through the bending field, taking smaller steps where bending is strongest, with a hard iteration cap and an early exit once the ray escapes or falls in.
3. Test for continuous crossings of the disk plane between steps, because large steps skip a thin disk.
4. Shade the disk hotter inside and cooler outside, brighter on the side moving toward the viewer and dimmer near its inner edge, with turbulent bands orbiting faster near the center.
5. Sample the background only after a ray escapes, filtered by how much sky the pixel's ray bundle covers, so the compressed region near the ring averages instead of aliasing.
6. Decide what a ray that hits the cap returns (the sky's average brightness works); never use whatever direction it happened to end on.
7. Control cost with reduced resolution and with accumulation while the camera holds still, reset on any move.

**Critic checks.** PASS when background stars bend continuously into a bright ring around a dark shadow, the disk's far side shows both above and below the shadow, one side of the disk is clearly brighter, and the ring region shows no speckle or banding across frames. FAIL signs: a black disc over a swirl texture, a flat unlensed disk, noise at the edge of the shadow, equal brightness on both sides.

**Diagnose.**
- Speckle around the shadow → capped rays left on arbitrary directions, or a point-sampled sky.
- Gaps or bands in the disk → steps larger than the disk with no crossing test.
- A flat look → screen-space distortion standing in for integration.

## Wormholes and portals

**Goal.** Looking through shows a different, coherent place whose perspective matches the viewer's, with the strongest distortion at the rim.

**Choose.** A render-target portal, where a matched virtual camera renders the far side into a texture mapped in screen space onto the opening, for doorways and game portals; lensing integration with two separate skies for space wormholes and flythroughs.

**Build.** Give each side its own sky (a different galaxy or star field), and put the far side's brightest structure along the throat's axis so the throat reads as a window rather than a black hole. When the camera passes through, carry its orientation through the passage and scale its speed with the local size of the throat.

**Watch for.** Portal views in the wrong perspective because the virtual camera wasn't moved by the portal pair's transform; objects between the virtual camera and the exit portal leaking into the view; an orientation snap during transit.

**Critic checks.** PASS when the view through shows a different place in correct perspective, distortion rises continuously toward the rim, and transit frames show no snap. FAIL signs: a static picture inside the opening, a mismatched perspective, a hard break at the rim.

## Nebulae and space volumes

**Goal.** Nebulae are glowing and absorbing gas: bright filaments with soft edges, dark dust lanes, and stars dimmed and reddened behind the dust.

**Build.** Bound the volume, shape density from warped filaments, color the emission by gas (deep red, teal) with blue reflection near bright stars, absorb light behind dense regions, and march only inside the bounds from a jittered start ([effects.md](effects.md)). Bake the nebula into the sky when the camera never enters it; keep it volumetric when it does.

**Critic checks.** PASS when dust lanes dim the stars behind them, filaments have soft edges, and no banding appears. FAIL signs: flat fog, stepped bands, stars shining through dense dust.

## Spacecraft effects

**Goal.** Effects belong to the craft: they start at its nozzles and hull, scale with it, and light it.

**Build.**
- Engine plumes: an HDR core at the nozzle inside a sheath that widens and fades, faint and wide in vacuum, tight and bright in air, sized from the nozzle.
- Thrusters: short pulses timed to maneuvers.
- Reentry: a glow shell made from the craft's own forward-facing surfaces, slightly enlarged, plus a wake trailing along the flow. Make it white-orange near the hull and violet to blue farther out, with filaments streaming back.
- Light the craft from its own plumes and plasma, and rank all of it in HDR against the sun.

**Watch for.** Generic spheres or cones around the ship, plumes detached from their nozzles, and additive layers drawn through planets.

**Critic checks.** PASS when plumes start at the nozzles and scale with them, reentry glow hugs the craft's leading faces and trails behind it, and the craft is lit by its own effects. FAIL signs: effects floating off the craft, uniform glow spheres, effects visible through bodies in front of them.

## Symptom → cause

| Symptom | Likely cause | First check |
| --- | --- | --- |
| Craft jitters far from the start | single-precision positions far from the origin; no floating origin | the camera's distance from the origin when the jitter starts |
| Distant bodies flicker through each other | depth precision: a tiny near plane, no reversed or logarithmic depth | `near`, `far` and the depth option in use |
| Stars slide or get clipped | background not tethered to the camera | whether the sky follows the camera's position |
| Stars crawl or flicker in motion | point-sampled stars with no footprint | consecutive frames of a slow pan |
| The star field looks like noise | uniform brightness and color | the brightness and color spread of the stars |
| Coastlines swim | geometry and shading using different fields, or unfiltered detail | which field the mesh and the shading each sample |
| Craters look like dark spots | crater painted as a color, not built as a floor, wall and rim | the unlit silhouette across a crater |
| The planet's silhouette is smooth | relief only in the normals | the unlit limb |
| Seams on the planet | chunk edges not stitched, or a longitude seam | a wireframe along chunk edges |
| The atmosphere looks like a halo sprite | a uniform shell with no falloff in density | the density profile with height |
| A pop when entering the atmosphere | shell and haze tuned separately; no continuous blend | descent frames across the handover |
| Speckle at a black hole's ring | capped rays with no defined result, or a point-sampled sky | a view of the rays that hit the step cap |
| Gaps in the accretion disk | steps larger than the disk with no crossing test | the step size where rays cross the disk plane |
| A wormhole reads as a black hole | far sky too dark, or its bright side off the throat axis | the far sky alone, and its brightest direction |
| Engine glow floats off the ship | effect not attached to the nozzle's frame | the effect's parent transform |
