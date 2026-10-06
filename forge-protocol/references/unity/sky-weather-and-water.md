# Unity sky, weather and water: skyboxes, fog, clouds, rain, snow, URP water and the HDRP route

API facts verified on Unity 6.6 (6000.6.4f1, 2026-10-06). Check the project's Unity version first (ProjectSettings/ProjectVersion.txt); if it differs, confirm in that version's official docs or the installed packages. The installed version wins.

Read when the frame includes open sky, distance haze, clouds, a changing hour, weather, or water of any size, from a puddle to an ocean. Environment lighting, and the bake it needs after the sky changes, is in [lighting-and-shadows.md](lighting-and-shadows.md); wet, snowy and mossy materials are in [materials-and-shaders.md](materials-and-shaders.md); the ground under the water and the shared wind are in [terrain-and-nature.md](terrain-and-nature.md).

## Contents

- Choosing a sky in URP
- Time of day and environment refresh
- Fog and height fog
- Clouds without volumetrics
- Weather state
- Rain, snow and wet surfaces
- Choosing URP water
- Depth color, foam and shores
- Refraction and reflections
- Waves and buoyancy
- The HDRP route
- Symptom → cause

## Choosing a sky in URP

**Goal.** The sky, the light and the haze agree: one sun in one place with one color, a horizon tint shared by sky and fog, and ambient light taken from the sky the player actually sees.

**Choose.**
- **The procedural skybox** (`Skybox/Procedural`): an analytic day sky whose sun disc follows the Sun Source light, with Sun Size, Atmosphere Thickness, Sky Tint, Ground and Exposure. Cheap and movable; it has no clouds, stars or night.
- **An HDRI as a cubemap or panoramic skybox** (`Skybox/Cubemap`, `Skybox/Panoramic`), from a CC0 source such as Poly Haven: photoreal and fixed in time. Its sun is baked in, so turn the skybox's Rotation until that sun sits where the directional light points.
- **Six-sided** for painted or stylized skies, and a hand-written skybox shader when the sky must react to time and weather; the Shader Graph 17.6 docs list no skybox target.
- URP has no physically based sky, gradient sky, cloud layers or volumetric clouds. Their substitutes are in [foundation.md](foundation.md), and the HDRP versions in The HDRP route.

**Build.**
1. Make a material with a skybox shader, and assign it in Window > Rendering > Lighting, Environment tab, Skybox Material; set Sun Source to the scene's directional light.
2. Let the app shell own a single sun record (its direction, color and intensity) that the light, the sky, fog, water highlights and shadows all read ([router.md](router.md), Contracts builders share).
3. After any sky change, regenerate the environment lighting: ambient and reflections stay on the old sky until you do. The Editor bake and its trap are in [lighting-and-shadows.md](lighting-and-shadows.md); at runtime, see Time of day and environment refresh.
4. Match fog color to the sky's horizon (see Fog and height fog).

**Watch for.** An HDRI with its own sun plus a directional light at another bearing gives two suns. Skybox Exposure brightens only the background; scene exposure belongs to the final image ([final-image.md](final-image.md)).

**Critic checks.** PASS when, in each still, shadows point away from the visible sun, highlights sit where that sun would put them, the sky's brightness suits the light on the ground, and no line marks where fog ends and sky begins. FAIL signs: shadows falling toward the sun; a luminous sky over murky, flat ambient; a visible stripe at the fog's edge.

**API facts** (check the installed version):
- URP supports Procedural, 6 Sided, Cubemap and Panoramic skyboxes, and not Physically Based Sky, Gradient Sky, Cloud Layers or Volumetric Clouds (verified on 6000.6).
- With Sun Source set to None, Unity treats the brightest directional light as the sun (verified on 6000.6).
- The Cubemap skybox's Rotation turns it around +Y, with Tint Color and Exposure beside it (verified on 6000.6).

## Time of day and environment refresh

**Goal.** A single clock sets the sun, the sky, the light's color and strength, fog, exposure and lamps, and moving the clock changes them all together and gradually.

**Build.**
1. Turn the hour into a sun angle (height above the horizon and compass bearing) by rotating the directional light; the procedural sky's sun follows through Sun Source.
2. Derive the light's color and strength from how high the sun stands (warmer and weaker near the horizon), together with the sky's tint and exposure, the fog color and density, and the fixed exposure value URP uses ([final-image.md](final-image.md)), all from one set of curves.
3. Refresh ambient light with `DynamicGI.UpdateEnvironment` and real-time reflection probes with `ReflectionProbe.RenderProbe` after the sun has moved a visible amount, rather than on every frame.
4. The procedural sky has no stars or moon, so for night, cross-fade to a night cubemap, light the scene from a moon (a cool, faint key with soft shadows), and keep shapes readable.
5. Switch practical lights on through dusk on a staggered ramp, and pin time to each named state for captures (dawn, noon, dusk, night).

**Watch for.** Baked lighting doesn't follow a moving sun, and the Web supports only baked global illumination; on the Web, keep the sun real-time, change ambient through Gradient or Color values or lighting scenarios rather than frequent environment refreshes, and plan the tier with [lighting-and-shadows.md](lighting-and-shadows.md), Time of day. An environment refresh can arrive a frame or more late, so let it settle before a capture.

**Critic checks.** PASS when every named hour shows matching sun height, shadow length, light color, sky color and lamp state across all its views. FAIL signs: short midday shadows beneath a sunset sky; white midday light under an orange sky; reflections from another hour than the sky shows; a night where nothing reads.

**API facts** (check the installed version):
- After changing `RenderSettings.skybox` in Play mode, `DynamicGI.UpdateEnvironment` is needed to update the ambient probe (verified on 6000.6).
- `DynamicGI.UpdateEnvironment` schedules the update; with asynchronous readback it can lag one or more frames, and requests faster than Unity can serve are dropped silently (verified on 6000.6).
- `ReflectionProbe.RenderProbe` refreshes a probe's cubemap and returns an ID for checking time-sliced progress (verified on 6000.6).

## Fog and height fog

**Goal.** Depth reads as air: far things fade in contrast and shift toward the horizon color, haze may settle in low ground, and no mesh boundary is visible where land or sea ends.

**Choose.**
- **Built-in fog** (Lighting window, Environment, Other Settings, Fog): Linear with Start and End, or Exponential and Exponential Squared with Density, in one color. URP's own shaders apply it; most scenes start here.
- **Height fog as a full-screen pass:** a Full Screen Pass Renderer Feature with a fullscreen Shader Graph that rebuilds world position from scene depth and thickens fog with distance and with low altitude, tinted brighter toward the sun.
- **Per-material fog** in custom shaders through the Shader Graph Fog node, which returns the scene's fog color and density, so custom water and sky shaders join the same haze.
- Volumetric fog and light shafts aren't in URP; use the HDRP route, or a bounded raymarch on the desktop tier only.

**Build.**
1. Set density for the size of the scene, and sample the fog color from the sky just above the horizon.
2. Thicken it enough to swallow the far boundary of terrain and water meshes before that boundary comes into view.
3. For the full-screen pass, request Depth in its Requirements and inject it Before Rendering Transparents, so water and particles draw over it with their own fog; enable Depth Texture in the URP asset.
4. Check every custom material in fog next to the ground; anything that stays vivid skips fog.

**Watch for.** A depth-based pass after transparents fogs water by the depth behind it. Fog used to hide missing distant detail reads as a gray wall.

**Critic checks.** PASS when the farther an object is, the paler and lower in contrast it looks and the nearer its tint comes to the horizon color, no edge of land or water shows, and fog and sky meet in one color. FAIL signs: a flat gray wall; distant hills as sharp as near ones; fog one color and sky another; water or particles standing out unfogged.

**API facts** (check the installed version):
- The Lighting window's fog offers Linear (Start, End), Exponential and Exponential Squared (Density) with one color (verified on 6000.6).
- The Full Screen Pass Renderer Feature injects at Before Rendering Transparents, Before Rendering Post Processing or After Rendering Post Processing (the default), and its Requirements can add depth, normal, color and motion passes (verified on 6000.6).
- Shader Graph's Fog node, supported in URP only, outputs the scene's fog color and a 0 to 1 density (verified on 6000.6).
- The Scene Depth node returns 0.5 everywhere when the URP asset's Depth Texture is off (verified on 6000.6).

## Clouds without volumetrics

**Goal.** Clouds look like sunlit volumes, brighter on top and at the rim, with darker undersides and softly eroded edges, arranged by the weather and drifting smoothly.

**Choose.**
- **Clouds in the HDRI:** cheapest, but frozen in time.
- **Cloud layers in a custom skybox shader:** scrolled noise blended over the sky, lit from the sun direction and thinned by a coverage value from the weather state; moving, time-aware, cheap, and the Web default.
- **Cloud cards:** lit billboards or soft particles at distance, for flybys and stylized skies; watch their sorting and flat lighting.
- **A raymarched cloud volume** in a full-screen pass or on a dome: hero skies only, desktop tier, at reduced resolution. The HDRP route has volumetric clouds built in.

**Build.**
1. Drive coverage and cloud type from the weather state, with each layer at its own altitude and drift speed, moving with the shared wind.
2. Light by sun direction: brighter on the sun side, darker bases, a silver rim when backlit; tint with the time-of-day curves.
3. Cast cloud shadows by giving the directional light a cookie texture and scrolling its Cookie Offset with the wind; Light Cookies must be on in the URP asset.
4. Fade far clouds into the horizon haze.

**Critic checks.** PASS when clouds have a lit side and a darker underside, soft edges, more than one size, steady drift from frame to frame, and, when the brief asks, shadows that slide across the land. FAIL signs: flat white shapes pasted on the sky; churning or flickering between frames; clouds drifting against the wind on the ground.

**API facts** (check the installed version):
- A URP directional light takes a 2D cookie with Cookie Size and Cookie Offset, and the offset can be animated to scroll the cookie (verified on 6000.6).

## Weather state

**Goal.** Weather is a single event: when it shifts, so do the particles, the ground and other surfaces, the sky and fog, the light, the sound and the wind.

**Build.**
1. Give the app shell one compact weather record, the shared weather contract in [router.md](router.md) (Contracts builders share): the time, the wind (the field from [terrain-and-nature.md](terrain-and-nature.md), Wind), what is falling and how hard, ground wetness, snow depth, cloud amount and storm level.
2. Ease each value toward its target with scaled delta time, so it behaves the same at any frame rate and pauses with the game.
3. Push it out from one place: global shader values for materials, emission and velocity for particle systems, the Wind Zone, fog and sky parameters, and mixer volumes for rain and wind loops ([input-ui-and-audio.md](input-ui-and-audio.md)).
4. Give each value its own pace: falling streaks react at once, wet ground takes minutes to soak and longer to dry, and snow builds up gradually.

**Critic checks.** PASS when, in each weather state, falling rain or snow leans the way plants and smoke are bent, and every view shows the same surface state (wet, or snow-covered). FAIL signs: rain dropping vertically beside bending trees; a downpour over dry ground; snow falling for a long time with nothing settled.

## Rain, snow and wet surfaces

**Goal.** Rain is visible across the whole frame: angled streaks close to the camera, splashes at the points where drops hit, and surfaces turning darker and shinier at the same time; snow drifts with the wind and settles only where it can.

**Build.**
1. Emit precipitation from a box above and around the camera that moves with it, with World simulation space, so drops keep falling straight when the camera turns.
2. Rain: thin streaks (a Stretched Billboard render mode, stretched by speed), slanted by the wind, faint, with density rather than brightness carrying heavy rain. Snow: soft round sprites, slow fall, sway from the Noise module, varied sizes and speeds.
3. Stop drops at surfaces with the Collision module in World mode and a Lifetime Loss of 1, and spawn splashes from a Collision sub-emitter; on the Web, collide only a fraction of drops and scatter extra splashes on exposed, upward-facing ground near the camera.
4. Keep sheltered ground dry: world collision ends drops on roofs, and splash placement skips anything with cover above it.
5. Wet surfaces: a global wetness value darkens albedo and raises smoothness together, flattens normals, fills puddle masks and streaks vertical faces ([materials-and-shaders.md](materials-and-shaders.md)).
6. Snow cover: a mask from upward-facing normals times the weather's coverage, bright, slightly cool and rough, locked to each object's own space so it doesn't slide.
7. Shift sky and light with the weather: overcast, lower contrast, a dimmer, cooler sun, denser fog.

**Watch for.** Local simulation space makes rain swing with every camera turn. A box that's too small shows its edges at the frame border. A mesh used in a particle Shape module needs Read/Write in 6.6, or the build fails.

**Critic checks.** PASS when rain slants with the wind seen elsewhere, wet surfaces are both darker and shinier and reflect, splashes and ripples mark ground and water, covered ground stays dry, and snow rests only on exposed, upward faces. FAIL signs: rain over dry ground; splashes under a roof; straight-down rain in a windy scene; rain stopping at an invisible box edge; snow stuck to walls.

**Start here** (adjust to the goal): faint streaks, with heavier rain shown by more of them rather than brighter ones.

**API facts** (check the installed version):
- The Collision module works against Planes or the World, with Dampen, Bounce and Lifetime Loss, and Send Collision Messages reports hits to `OnParticleCollision` (verified on 6000.6).
- Sub-emitters fire on Birth, Collision, Death, Trigger or Manual (`TriggerSubEmitter`); all but Birth support a single burst (verified on 6000.6).
- Simulation Space is Local, World or Custom, and Delta Time is Scaled or Unscaled (verified on 6000.6).
- In 6.6, a mesh that a Particle System Shape module reads must have Read/Write enabled, or the Inspector warns and the build fails (verified on 6000.6).

## Choosing URP water

**Goal.** The water uses the representation that owns the view. URP has no built-in water system, so water here is a transparent surface with a custom shader, plus probes and scripts.

**Choose.**
- **Puddles and wet ground:** handled in the ground's material, not as water (see Rain, snow and wet surfaces).
- **Calm lakes, ponds and pools:** a flat plane with a transparent Shader Graph: depth color, foam, refraction from the opaque texture, a reflection probe, and normal-mapped ripples at two scales and directions.
- **Rivers and streams:** a mesh along the channel (Splines can extrude one, see [levels-and-geometry.md](levels-and-geometry.md)) with normals and foam scrolled along a flow direction, two layers cross-faded on offset phases so the stretch never shows.
- **Open sea:** a sum of Gerstner waves displaced in the vertex stage, mirrored in C# for buoyancy. A spectral (FFT) ocean needs compute, so it runs on the Mac and on WebGPU only, with Gerstner waves as its WebGL 2 fallback.
- **The HDRP Water System:** only on the HDRP route.

**Build.**
1. Enable Depth Texture and Opaque Texture in every URP asset the tiers use.
2. Make the water material Transparent, so it draws after the opaque copy and Scene Color can see what lies below.
3. Give the mesh enough vertices for displacement near the camera, or use a grid that follows the camera in world-snapped steps.
4. Expose debug views for thickness, foam and normals.

**Watch for.** A blue transparent material is none of the things that make water read: depth color, angle-dependent reflection and layered motion.

**Critic checks.** PASS when the water's color and clarity vary with its depth, reflections grow stronger at shallow viewing angles, and the surface moves at several scales. FAIL signs: a flat, evenly transparent blue sheet; the same clarity everywhere; a calm mirror when the brief calls for moving water.

**Diagnose.**
- Uniform color with no depth → Depth Texture off, so Scene Depth reads 0.5.
- Black or frozen refraction → Opaque Texture off, or the water rendered as opaque.

**API facts** (check the installed version):
- Every Water System feature (its shader, wave simulation, foam, currents, underwater) is HDRP only (verified on 6000.6).
- The URP Opaque Texture is a copy of the scene taken just before transparent objects draw (verified on 6000.6).
- In URP, the Scene Color node samples that opaque texture, works only in the fragment stage, and needs a Transparent surface or a render queue of 2999 or 3000 (verified on 6000.6).

## Depth color, foam and shores

**Goal.** Depth sets the color: shallows show the bed beneath, deeper water loses its reds first, the waterline melts into damp ground, and foam gathers where the water is disturbed.

**Build.**
1. Measure thickness along the view in meters: the Scene Depth Difference node in Eye mode, or Scene Depth in Eye mode minus the surface's own eye depth.
2. Attenuate red, green and blue at different exponential rates as thickness grows (red drops out first), and blend in a body color that strengthens with depth; choose it from the brief (tropical blue-green, a green-brown lake, deep ocean blue).
3. Drive opacity toward zero as the water thins, so the shoreline has no hard edge.
4. Put foam where something causes it: thin water along shores, places where an object pierces the surface (a tiny depth gap), steep crests, and wakes. Apply the bubbly texture only at the shading step, and soften it with distance.
5. Darken and gloss the ground in a band above the water level, from the same water level the water uses ([terrain-and-nature.md](terrain-and-nature.md)).

**Watch for.** A constant stand-in depth presented as a measurement. Fog doing the job of absorption; the haze above water and the light lost inside it are different things.

**Critic checks.** PASS when the shallows are visibly lighter and clearer than deep water with a smooth change between them, foam lines the shore and wraps objects, and the wet strip of shore is both darker and shinier than dry ground. FAIL signs: equal transparency everywhere; a sharp seam at the waterline; foam as even white static; wet sand that darkens without any shine.

**API facts** (check the installed version):
- The Scene Depth node samples the camera depth texture in Linear 01, Raw or Eye mode, where Eye is the distance from the camera in meters (verified on 6000.6).
- The Scene Depth Difference node returns the depth gap between a world position and the depth buffer, in meters in Eye mode, negative when the buffer is closer (verified on 6000.6).

## Refraction and reflections

**Goal.** Reflections show the sky and surroundings that actually exist, grow stronger toward low viewing angles and wobble with the waves; clear water reveals a refracted bottom with nothing from the foreground smeared into it.

**Choose.**
- **Reflection probes:** the base layer everywhere. The skybox reflection covers open water; add a probe at the water for nearby scenery, with box projection for indoor pools. URP has no screen-space reflections.
- **A planar reflection camera:** for calm water where nearby objects need crisp reflections. A second camera mirrored across the water plane renders into a render texture at reduced resolution, with an oblique clip plane at the surface (`Camera.CalculateObliqueMatrix`); it costs a second scene render, so strip its post and shadows.
- **Refraction from Scene Color:** sample the opaque texture at screen UVs offset by the wave normal.

**Build.**
1. Blend reflection and the refracted body by Fresnel: about 2% reflection looking straight down, nearly all of it at grazing angles; never a constant opacity.
2. Distort reflections by the wave normal, less with distance.
3. Depth-test refraction: if the scene depth at the offset UV is in front of the water surface, fall back to the unshifted UV, so foreground objects don't smear into the water.
4. Take the sun glint from the main light, widened with distance so it doesn't alias into sparkle.
5. Refresh the probe whenever the sky changes, so reflections show the visible sky.

**Watch for.** A mirrored camera flips triangle winding, so faces can vanish in the reflection until culling is corrected. Opaque Downsampling blurs refraction, which suits murky water and spoils clear pools.

**Critic checks.** PASS when low views mirror more sky and scenery than steep views, reflections wobble with the waves and show the sky that is visible, the sun's glint lies beneath the sun, and clear water reveals a bed displaced by the surface. FAIL signs: one opacity at every angle; a reflected sky unlike the real one; foreground objects smeared into what lies below; a flawless mirror on rough water.

**API facts** (check the installed version):
- The URP asset's Opaque Downsampling copies the opaque texture at full resolution, half (2x Bilinear) or a quarter with box filtering (4x Box) (verified on 6000.6).
- `Camera.CalculateObliqueMatrix` builds a projection whose near plane is a given clip plane, for clipping a reflection camera at the water (verified on 6000.6).

## Waves and buoyancy

**Goal.** One wave function drives the mesh, the normals, crest foam and every gameplay height, so boats, swimmers and splashes ride the waves the camera sees.

**Build.**
1. Sum a modest set of Gerstner waves in world space in the water's vertex stage, spread in direction and wavelength, with normals from the same sum's derivative.
2. Evaluate the same sum in C# from the same clock: set the shader's time from script as a global value instead of relying on the built-in shader time, so CPU and GPU waves stay in phase.
3. Float objects in `FixedUpdate`: read the wave height under a few points around each hull, push each point up with `AddForceAtPosition` in proportion to how deep it sits, and damp with linear and angular damping; bob, pitch and roll follow.
4. Hide water inside hulls with a mask drawn before the water that writes depth only.
5. Leave wakes and splashes: foam particles at entry points and a fading foam trail behind movers.

**Watch for.** Physics never sees vertex displacement; only the C# copy does. URP writes no motion vectors for transparent materials, whatever the graph's Additional Motion Vectors says, so displaced transparent water can ghost under temporal anti-aliasing; compare its views with SMAA ([final-image.md](final-image.md)). All waves traveling one way read as corrugated sheet.

**Critic checks.** PASS when swell, chop and ripples all read, waves arrive from several directions, peaks are sharper than troughs, floating objects rise, fall and tilt with the water under them, and hulls stay dry inside. FAIL signs: a tiled square pattern; parallel bands; boats holding still as waves pass; water inside a boat.

**Diagnose.**
- Boats bob out of step with the water → shader time and C# time come from different clocks.
- Boats jitter or launch → force applied per frame in `Update`, or no damping.

**API facts** (check the installed version):
- `Rigidbody.AddForceAtPosition` takes a world-space force and a world-space point, which also produces torque (verified on 6000.6).
- URP writes motion vectors only for opaque and alpha-clipped materials, so Shader Graph's Additional Motion Vectors can't give a transparent water surface any for TAA (verified on 6000.6).

## The HDRP route

**Goal.** A Mac-only showcase gets a physically based sky, volumetric clouds and simulated water, only after the user has approved HDRP for it. HDRP has no Web target and gets maintenance only; the reasons are in [foundation.md](foundation.md).

**Build.**
1. Physically Based Sky: on a Volume, Add Override > Sky > Physically Based Sky, then set the Visual Environment override's sky type to it. Give the sun a realistic intensity (the docs suggest 130,000 lux) and Affect Physically Based Sky.
2. Volumetric Clouds: enable them in the HDRP asset (Lighting > Volumetrics), in the Frame Settings, and as a Volume override.
3. Water: switch on Water under Rendering in the HDRP asset's quality settings, in three Frame Settings sections (Camera, Realtime Reflection, Custom or Baked Reflection), and set the Water Rendering override's State to Enabled; then add a surface from GameObject > Water Surface.
4. Buoyancy: turn on Script Interactions on the surface and query heights with `WaterSurface.ProjectPointOnWaterSurface`.
5. Keep the same contracts (one sun, one wind, one weather state) and the same capture set as the URP build ([validation.md](validation.md)).

**Watch for.** Upgraded projects leave water off until all three switches are set. After baking, Physically Based Sky ignores lights in Baked mode; use Realtime or Mixed for the sun.

**Critic checks.** PASS when one sun agrees across sky, shadows and water glint, clouds show lit tops and shaded bases, water shows depth color, foam and layered motion, and floating objects ride the visible waves. FAIL signs: sky and shadows that disagree; water as clear at depth as in the shallows; objects ignoring the waves.

**API facts** (check the installed version):
- HDRP water needs Water enabled in the HDRP asset, in the Camera, Realtime Reflection and Custom or Baked Reflection Frame Settings, and the Water Rendering override set to Enabled (verified on 6000.6).
- `WaterSurface.ProjectPointOnWaterSurface` takes `WaterSearchParameters` and returns a `WaterSearchResult` with the projected position, once Script Interactions is on (verified on 6000.6).
- Physically Based Sky considers only lights with Affect Physically Based Sky, and ignores Baked lights after a bake (verified on 6000.6).

## Symptom → cause

| Symptom | Likely cause | First check |
| --- | --- | --- |
| New sky, old ambient and reflections | environment lighting not regenerated after the sky changed | the Editor bake, or `DynamicGI.UpdateEnvironment` at runtime ([lighting-and-shadows.md](lighting-and-shadows.md)) |
| Shadows point the wrong way for the visible sun | the light and the sky read different sun records, or an HDRI's sun isn't aligned | the skybox Rotation against the light's direction |
| Two suns, or a doubled glare at low angles | an HDRI sun plus a directional light at another bearing | the HDRI's sun position against the light |
| A stripe at the fog's edge against the sky | fog color chosen without sampling the horizon | fog color beside the horizon color |
| Water or particles too vivid in fog | custom shaders skipping fog | the Fog node in those shaders |
| Height fog darkens the water wrongly | the depth pass injected after transparents | the Full Screen Pass injection point |
| Clouds move against the ground wind | sky and wind from different sources | the weather state each one reads |
| Rain swings when the camera turns | Local simulation space | the emitter's Simulation Space |
| Dry ground under rain, or splashes beneath roofs | surfaces ignoring the weather record, or drops without world collision | the wetness value and the Collision module |
| Wet ground looks dark but dull | wetness darkens albedo but leaves smoothness unchanged | a smoothness view of the wet area |
| Water one flat color at every depth | Depth Texture off, so Scene Depth reads 0.5 | Depth Texture in the active URP asset |
| Black or frozen refraction | Opaque Texture off, or the water drawn as opaque | Opaque Texture and the water's Surface Type |
| Foreground objects smeared into the water | refraction offset without a depth test | the depth check at the offset UV |
| Reflections show a different sky | probe not refreshed after the sky changed | the probe's last render against the sky change |
| Faces missing in the planar reflection | mirrored camera with uncorrected winding | culling on the reflection camera |
| Boats bob out of step with the waves | shader and C# waves on different clocks | the time value each one reads |
| Boats full of water | no depth-only hull mask before the water | the mask's render order |
| Waves ghost under TAA | transparent water writes no motion vectors in URP | the same frames with SMAA ([final-image.md](final-image.md)) |
| HDRP water invisible | one of the three water switches off | the HDRP asset, Frame Settings and Water Rendering override |
