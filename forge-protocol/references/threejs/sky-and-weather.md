# Three.js sky and weather

API facts verified on r186 (2026-10-05). Check the installed version first; if it differs, confirm in the official docs or the installed source. The installed version wins.

Read when the scene shows sky, haze, clouds, a time of day or weather. Environment lighting itself is in [lighting-and-shadows.md](lighting-and-shadows.md); how wet, snowy or mossy surfaces respond is in [materials.md](materials.md).

## Contents

- Choosing a sky
- Sun, moon and stars
- Fog and aerial perspective
- Clouds
- Time of day
- Shared weather state
- Rain
- Snow
- Aurora, lightning and other sky events
- Symptom → cause

## Choosing a sky

**Goal.** Sky, light and distant haze tell one story: the same sun position and color, the same horizon tint, and environment lighting that matches what the sky shows.

**Choose.**
- **A static HDR sky** (a photographed environment): a fixed time of day, photoreal and cheapest. Its sun is baked in, so aim the directional light to match it.
- **The built-in sky mesh** (`SkyMesh` on the WebGPU renderer, `Sky` on WebGL): an analytic daylight model with a movable sun, cheap, with simple clouds since r186. It covers daylight only, weakens at deep twilight, has no night, and is not physically linked to your fog.
- **A physically based atmosphere** (precomputed scattering lookup tables): ground-to-space views, accurate sunsets and twilight, and aerial perspective from the same model as the sky. A community library offers one for the WebGPU renderer (for example `@takram/three-atmosphere`, in beta at the time of writing; check its status and supported three.js range), or write your own from published scattering models.
- **A stylized gradient** (zenith, horizon and sun glow): toon and graphic looks.

**Build.**
1. Keep one sun description (direction, color, intensity), owned by the app shell; the sky, the light, fog, water glint and shadows all read it.
2. Light the scene from the sky it shows: render the sky into the environment map (see Time of day).
3. Match fog color to the sky's horizon color in the view direction.

**Critic checks.** PASS when shadow direction, the sun's position in the sky, specular highlights and sky brightness agree in every still, and sky and fog meet at the horizon without a seam. FAIL signs: the sun on one side and shadows cast from another; a dull sky over bright midday light; a visible band where fog meets sky.

**Diagnose.**
- Objects look pasted in → environment light doesn't match the visible sky.
- The sky changed after an upgrade with no code change → the r183 removal of the sky's legacy gamma.

**API facts** (check the installed version):
- `SkyMesh` (an analytic daylight model) works only with `WebGPURenderer`; the WebGL renderer uses `Sky` (verified on r186).
- `SkyMesh` exposes `turbidity`, `rayleigh`, `mieCoefficient`, `mieDirectionalG` and `sunPosition`, plus simple procedural clouds (`cloudCoverage`, `cloudDensity`, `cloudElevation`, `cloudScale`, `cloudSpeed`) and `showSunDisc` (verified on r186).
- Since r186, `Sky` and `SkyMesh` have no `up` uniform and always assume +Y up; their legacy gamma correction was removed in r183, and the old look can't be restored by retuning (verified on r186).
- A TSL sky can go straight into `scene.backgroundNode` (verified on r186).

## Sun, moon and stars

**Goal.** The sun outshines everything else in the sky, with a small disc and soft glare; at night, moonlight and stars take over under the same direction rules.

**Build.**
1. Draw the sun disc at its true angular size (about half a degree) with HDR brightness and a halo, and let glare and bloom rank it highest ([final-image.md](final-image.md); flares are in [effects.md](effects.md)).
2. At night, make the moon the key light (cool, dim, soft shadows), add stars with a natural brightness spread and a faint sky glow, and let exposure adapt. Star fields as a feature are in [space.md](space.md).
3. Position sun and moon from one time value, and rotate the stars with them when the camera watches long enough to notice.

**Critic checks.** PASS when the sun disc is small and is the brightest point, and night scenes keep readable forms under moonlight. FAIL signs: a giant sun disc; a black night where nothing reads; stars showing through a daytime sky.

## Fog and aerial perspective

**Goal.** Distance reads as atmosphere: far objects lose contrast and take on the horizon's hue gradually, haze pools low in valleys, and no mesh edge shows at the horizon.

**Choose.**
- **Distance fog** (linear or exponential), tinted per view toward the sky's horizon color and brighter toward the sun: most scenes.
- **Height fog** (density falling with altitude): valleys, coasts, mornings.
- **Aerial perspective from the atmosphere model** (transmittance and in-scattered light along each view segment): whenever a physically based sky is used, so haze and sky agree.
- **Volumetric fog with light shafts:** only when the brief wants visible shafts; bound it, since it is costly.

**Build.**
1. Match density to the scene's scale: fog tuned for a 50 m set turns a 20 km landscape into soup.
2. Take the color from the sky at the horizon, brighter and warmer toward the sun.
3. Let fog cover the far ends of terrain and water meshes before they can show.
4. Apply fog to every material, including custom shaders, particles and water.

**Watch for.** Fog used to hide missing depth or detail; one gray fog under a blue sky; transparent or custom materials that skip fog and pop out of the haze.

**Critic checks.** PASS when distant objects grow lighter and lower in contrast in proportion to distance and take on the horizon's hue, the far edge of terrain or water never shows, and fog matches the sky at the horizon. FAIL signs: a gray wall; no haze on distant mountains; fog and sky of different colors; objects that ignore the fog.

**Diagnose.**
- Gray, flat distance → fog color not taken from the sky, or density wrong for the scale.
- Water or particles too vivid in fog → their materials skip fog.

**API facts** (check the installed version):
- With `WebGPURenderer`, a classic `Fog` or `FogExp2` becomes TSL `fog(color, rangeFogFactor(near, far))` or `fog(color, densityFogFactor(density))`, and `scene.fogNode` overrides both for custom fog (verified on r186).
- TSL `rangeFog()` and `densityFog()`, deprecated since r171, were removed in r183, and on r186 importing them fails; use `fog()` with `rangeFogFactor()` or `densityFogFactor()` (verified on r186).
- Official fog examples include `webgpu_fog_height`, `webgpu_custom_fog_scattering` and `webgpu_custom_fog_background` (verified on r186).
- `godrays(depthNode, camera, light)` raymarches the light's shadow map, so it needs shadows enabled on the renderer, the light and the casting objects; set it up per [final-image.md](final-image.md) (verified on r186).

## Clouds

**Goal.** Clouds read as volumes lit by the sun: bright tops and rims, shaded bases and cores, soft eroded edges, types and layers organized by weather, and drift without boiling.

**Choose.**
- **Clouds in an HDR sky or painted backdrop:** cheapest, but they can't follow a changing time of day.
- **The sky mesh's simple clouds:** a light layer for daylight scenes.
- **Lit billboards or impostors:** mid cost, good for stylized skies and flights past single clouds; watch sorting and flat-card lighting.
- **Layered planes** (2D noise layers with approximate lighting): wispy high cloud, cheap, with no parallax depth.
- **Raymarched volumes:** hero skies, flying through clouds, time-of-day lighting. Costly, and they need temporal reconstruction.

**Build** (volumes).
1. Bound the volume (a layer between base and top altitudes, or a shell around a planet), march only the segment inside it, and stop at the nearest opaque surface.
2. Start from a weather map: a 2D field of coverage and cloud type decides where clouds exist and what kind they are. Give each layer its own altitude range, density profile with height, and wind.
3. Shape density as weather times the height profile, carved by a base 3D shape, then eroded at the edges by detail noise (wispy at the base, billowy at the top). Detail removes density; it never adds it.
4. Light each sample by its optical depth toward the sun (a short march, plus a cheap shadow map for longer distances), add sky light and an approximation of multiple scattering so cores aren't black, and use a forward-scattering phase function for the silver lining.
5. Integrate front to back, stop when transmittance is negligible, and cross empty space in long steps.
6. Render at reduced resolution with jitter and reconstruct over time, resetting history on cuts and large changes.
7. Cast cloud shadows on the ground from a separate cheap pass, not from the beauty march.
8. Feed the clouds' depth to aerial perspective so far clouds take on haze.

**Watch for.** Every layer sharing one wind and one profile makes every cloud identical. History accepted across disocclusion leaves trails around cloud edges and moving objects.

**Critic checks.** PASS when clouds show lit sides and shadowed bases and cores, edges are soft and eroded, more than one type or scale appears, distant clouds take on haze, and they drift coherently across frames, with cloud shadows sweeping the ground when the brief calls for them. FAIL signs: porous smoke; flat, bright interiors; black featureless masses; boiling or flicker between frames; trails around moving objects.

**Diagnose.**
- Porous smoke → detail adds density instead of eroding it.
- Flat, bright interiors → no optical depth toward the sun.
- Dark, featureless clouds → no multiple-scattering or sky-light term.
- Boiling → fields move in unrelated directions, or are regenerated each frame.
- Trailing edges → temporal history without rejection.
- Cost grows with view distance → the march isn't bounded.

**Start here** (adjust to the goal): march at a quarter of the screen resolution on each axis and reconstruct over several frames.

**API facts** (check the installed version):
- The official `webgpu_volume_cloud` example raymarches a single cloud in a box with `RaymarchingBox` (from `three/addons/tsl/utils/Raymarching.js`) over a `Data3DTexture` sampled with `texture3D` (verified on r186).

## Time of day

**Goal.** One time value drives the sun, sky, light color and intensity, fog, exposure and practical lights, and every change stays smooth.

**Build.**
1. Map time to the sun's elevation and azimuth (and the moon's), from a real location and date when the brief names one.
2. Drive light color and intensity from sun elevation (warm and dim when low, neutral when high), along with the fog tint and the exposure target ([final-image.md](final-image.md)).
3. Regenerate the environment map from the sky when the sun has moved noticeably, not every frame, and dispose of the previous one. Hide the sun disc during the bake when a directional light already supplies the sun, so the sun isn't counted twice. Environment lighting itself is in [lighting-and-shadows.md](lighting-and-shadows.md).
4. Switch practical lights (windows, street lamps) on through dusk on a staggered ramp.
5. For captures, pin time to each named state the brief lists (dawn, noon, dusk, night).

**Critic checks.** PASS when each named time of day shows a consistent sun angle, shadow length, light color, sky color and practical-light state in every view. FAIL signs: noon shadows under a sunset sky; a sunset sky over neutral white light; reflections showing a different time from the sky.

**Diagnose.**
- Reflections show an old sky → the environment wasn't regenerated after the sun moved.
- Overbright or doubled sun at low angles → the sun is baked into the environment and also cast by the directional light.

**API facts** (check the installed version):
- `PMREMGenerator.fromScene()` bakes a scene holding just the sky into a prefiltered environment; the `webgpu_ocean` example re-bakes it whenever the sun moves and disposes of the previous target (verified on r186).
- `SkyMesh.showSunDisc` switches the solar disc off, for example during that bake (verified on r186).

## Shared weather state

**Goal.** Weather is one event that every system reads: particles, surfaces, sky, fog, light, sound and wind all change together.

**Build.**
1. Keep one small state, owned by the app shell: time, wind (a world-space vector in meters per second, the same field as [nature.md](nature.md), Wind), precipitation type and intensity, wetness, snow cover, cloud cover and storm activity.
2. Ease every value toward its target over time, independently of frame rate.
3. Pass the state by reference to particles, materials, sky, fog and audio. No system keeps its own clock or its own wind.
4. Separate fast and slow responses: streaks start at once, ground wetness builds over minutes and dries slowly, and snow cover accumulates.

**Critic checks.** PASS when, in weather states, rain or snow falls in the direction the wind bends plants and smoke, and surfaces show the state (wet or snowy) consistently across views. FAIL signs: rain falling straight down while trees bend; heavy rain on dry ground; falling snow with no cover after the brief says it has been snowing.

**API facts** (check the installed version):
- `MathUtils.damp(current, target, lambda, dt)` eases weather values toward their targets independently of frame rate (verified on r186).

## Rain

**Goal.** Rain reads through the whole frame: slanted streaks near the camera, splashes and ripples where drops land, and surfaces that darken and gleam.

**Build.**
1. Draw streaks in a volume that wraps around the camera, never a finite emitter box: slanted by the wind, stretched by motion, faint, with heavier rain adding density and a misty veil at distance.
2. Stop drops at surfaces with a top-down height capture of the scene (an orthographic render of what blocks the sky), so drops end on roofs and ground and spawn splashes there, and nothing under cover gets rain.
3. Put splashes only on upward-facing, visible surfaces, and ripples on puddles and water ([water.md](water.md), Rivers, waterfalls and puddles).
4. Make surfaces wet: darker and smoother together, with streaks down vertical faces ([materials.md](materials.md)). Screen-space reflections on wet ground need a mode that reflects non-metals ([final-image.md](final-image.md), Screen-space reflections and god rays).
5. Shift sky and light: overcast, lower contrast, cooler light, more reflection.
6. Wet glass near the camera is a screen-space effect ([effects.md](effects.md)).

**Critic checks.** PASS when rain falls in the direction of the wind seen elsewhere, surfaces look wet (darker and glossier, with reflections), splashes and ripples appear on ground and water, and sheltered ground stays dry. FAIL signs: rain over dry surfaces; splashes under roofs; vertical rain in a windy scene; rain ending at the edge of a box.

**Diagnose.**
- Rain looks pasted over the scene → particles and surfaces don't share the weather state.
- Splashes in the wrong places → placement isn't limited to upward, exposed faces.

**Start here** (adjust to the goal): keep streak opacity low, and let quantity rather than brightness carry heavy rain.

**API facts** (check the installed version):
- The official `webgpu_compute_particles_rain` and `webgpu_compute_particles_snow` examples move particles in compute and stop them on surfaces using a top-down orthographic capture of the scene into a half-float render target; the rain version spawns ripples where drops land (verified on r186).

## Snow

**Goal.** Falling and settled snow agree: flakes drift with the wind, snow lies only where it can settle, on upward faces with real thickness where silhouettes matter, and its edges are soft.

**Build.**
1. Draw flakes as soft, round sprites in a camera-wrapped volume: slow fall, sway and drift with the wind, with varied sizes and speeds so they never fall in step.
2. Build the cover mask from upward-facing normals and exposure (the top-down capture keeps sheltered ground clear) plus a coverage threshold from the weather state; rocks and branches catch snow on top.
3. Take snow height and normals from one snow function, displacing geometry where the silhouette matters and using normals only for a thin dusting.
4. Lock snow on objects to the object's own coordinates, so it doesn't slide when the object moves.
5. Shade snow bright, slightly cool and rough, with a faint sparkle only inside the snow mask, filtered at distance.
6. Tracks and deformable snow are in [special-materials.md](special-materials.md).

**Critic checks.** PASS when snow sits only on upward-facing, exposed surfaces with soft edges and visible thickness on ledges and branches, and flakes drift with the wind at varied speeds. FAIL signs: snow on vertical walls or undersides; flat white decals with no thickness; flakes falling in lockstep; glittering noise.

**Diagnose.**
- Snow slides across moving objects → world coordinates for an effect that belongs to the object.
- Snow rises but lights flat → height and normals come from different functions.

## Aurora, lightning and other sky events

**Goal.** Rare sky events act as emitters and light sources, used with restraint: they light the scene consistently with where they are and still read with bloom off.

**Build.**
1. Aurora: an emissive curtain volume of finite footprint high in the sky, folded along a few curves, with vertical rays and a slow drift; a green main band, red above it, and at most a faint pink or violet fringe along the lower edge. It faintly lights snow and water below.
2. Lightning: a bolt of branching geometry visible for a few frames, a flash that lights the sky and scene in a few pulses, and an afterglow; with audio, delay the thunder by distance.
3. Rainbows: centered opposite the sun, about 42° from that point, and only with the sun behind the viewer and rain in front.
4. Meteors and fireworks are effects ([effects.md](effects.md)).

**Critic checks.** PASS when the event lights nearby surfaces in a way consistent with its position and color, and it reads clearly with bloom off. FAIL signs: an aurora as a flat texture with no depth; lightning that flashes the sky but lights nothing; a rainbow in the wrong part of the sky.

## Symptom → cause

| Symptom | Likely cause | First check |
| --- | --- | --- |
| Shadows disagree with the sun in the sky | light and sky driven by different sun descriptions | which sun description each one reads |
| Objects look pasted into the scene | environment light doesn't match the visible sky, or wasn't regenerated | the environment map shown alone |
| Sky looks different after an upgrade | the r183 removal of the sky's legacy gamma | the installed revision |
| Doubled or overbright sun at low angles | sun baked into the environment and also cast by the directional light | whether the sun disc was on during the bake |
| A band where fog meets the sky | fog color not taken from the sky's horizon | fog color against the horizon color |
| Gray, flat distance | fixed gray fog, or density wrong for the scene's scale | fog density against the scene's extent |
| Terrain or water edge shows at the horizon | fog or far geometry doesn't cover the mesh boundary | fog distance against the mesh extent |
| Some objects too vivid in fog | their materials skip fog | the fog setting on those materials |
| Porous, smoky clouds | detail noise adds density instead of eroding it | density with detail switched off |
| Flat, bright cloud interiors | no optical depth toward the sun | a view of sun transmittance |
| Black, featureless clouds | no multiple-scattering or sky-light term | the clouds with direct sun switched off |
| Clouds boil or flicker | fields move in unrelated directions or are regenerated each frame | each field's offset over time |
| Trails around clouds or moving objects | temporal history accepted across disocclusion | the same frames with history off |
| Cloud cost grows with view distance | the march isn't bounded to the cloud layer and the scene depth | a view of the march interval |
| Rain direction disagrees with plants and smoke | particles and plants read different wind | each system's wind source |
| Rain over dry ground, or splashes under roofs | surfaces don't read the weather state, or there is no top-down occlusion | the wetness mask and the occlusion capture |
| Snow on vertical faces | no upward-facing filter | the snow mask on a wall |
| Snow slides on moving objects | snow sampled in world coordinates | the coordinate space of the snow mask |
| Flat-lit snow cover | height and normals from different functions | a normals view of the snow |
| Night scene unreadable | no moonlight key, or exposure fixed at daytime values | the night key light and the exposure |
