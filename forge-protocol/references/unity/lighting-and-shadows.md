# Unity lighting and shadows: sun and sky, environment light, probes and lightmaps, reflections, shadows and time of day

API facts verified on Unity 6.6 (6000.6.4f1, 2026-10-06). Check the project's Unity version first (ProjectSettings/ProjectVersion.txt); if it differs, confirm in that version's official docs or the installed packages. The installed version wins.

Read when you design the light of a URP scene: the sun and sky, ambient light and reflections, baked or probe-based bounce, shadows, additional lights and time of day. Tone mapping and exposure are in [final-image.md](final-image.md), the sky itself, fog and clouds in [sky-weather-and-water.md](sky-weather-and-water.md), lightmap UVs on level meshes in [levels-and-geometry.md](levels-and-geometry.md), and the URP feature gaps behind these choices in [foundation.md](foundation.md).

## Contents

- Light design
- Sun and sky first
- Environment light and the regenerate-lighting trap
- Light modes, units and intensities
- Indirect light: Adaptive Probe Volumes or lightmaps
- Choosing and running the light baker
- Reflection probes
- Shadows: cascades, distance, bias and softness
- Additional lights, Forward+ and light layers
- Emissive surfaces and practical lights
- Time of day
- Symptom → cause

## Light design

**Goal.** Light explains shape and carries the mood: a single main direction, clear steps from dark to light, and a subject that stands out from what's behind it.

**Build.**
1. Let the brief's mood and hour pick the main light (sun, window or lamp), and light the subject before its surroundings; where that light comes from sets the shadow shapes that tell the eye about form.
2. Take the fill from the sky and from bounced light, and choose how much brighter the key is than the fill by mood: a big gap for drama, a small one for softness.
3. Lift products and characters off the background with a rim or back light, kept to the subject with light layers (below).
4. Arrange values around the focal point, deciding where the deepest shadows and the brightest highlights fall, so the image reads at a glance.
5. Color each light from what motivates it, for instance warm sunlight with cool skylight in the shadows, using color temperature where the project enables it.
6. Judge form before materials in a clay pass: the Rendering Debugger's Lighting Debug Mode set to Lighting Without Normal Maps renders every surface with a neutral material.

**Watch for.** A key placed near the camera, which flattens everything; several lights of equal strength with no clear leader; ambient pushed up until shadows turn gray; exposure fixed by nudging each light in turn.

**Critic checks.** PASS when each hero still has one clear main light direction, shadowed sides still show detail, and the subject stands apart from the background by brightness or hue. FAIL signs: flat light from the camera's side; shadows pointing several ways; uniform gray shadows; a subject lost against its background.

**Start here** (adjust to the goal): a key about four times as bright as the fill for daylight, more for drama and less for soft product light.

**API facts** (check the installed version):
- The Rendering Debugger's Lighting Debug Mode offers Shadow Cascades, Lighting Without Normal Maps and Lighting With Normal Maps (both with neutral materials), and Reflections views; its Material Override and Material Validation views (albedo, smoothness, metallic, normals, lighting complexity) serve as diagnostic stills (verified on 6000.6).

## Sun and sky first

**Goal.** One sun and one sky agree on direction and color, and every system that shows the sun reads the same description.

**Build.**
1. Use one Directional Light as the sun and assign it as Sun Source in the Lighting window (Window > Rendering > Lighting > Environment). Left empty, the brightest directional light becomes the sun, which changes the moment someone adds a brighter one.
2. Keep the sky consistent with the sun: a procedural skybox follows the Sun Source, while an HDRI sky must be rotated until its bright side matches the light ([sky-weather-and-water.md](sky-weather-and-water.md)).
3. Drive the light, the sky, fog tint and water glints from the PLAN's one sun contract ([router.md](router.md), Contracts builders share).
4. When an HDRI already contains a bright sun and a directional light plays the sun too, tame one of them, or the sun is counted twice in ambient light and reflections. Never let two directional lights act as suns: URP shadows only one.

**Critic checks.** PASS when shadows fall away from where the sun appears in the sky, at a length that suits its height, and glints on water or gloss line up beneath it. FAIL signs: shadows reaching toward the sun; short midday shadows under a sunset sky; a doubled sun highlight.

**API facts** (check the installed version):
- With Sun Source set to None, the brightest directional light is the sun, and lights with Render Mode Not Important don't affect the skybox (verified on 6000.6).
- URP shadows one directional light at a time, and the URP asset's Main Light can be Per Pixel or None (verified on 6000.6).

## Environment light and the regenerate-lighting trap

**Goal.** Ambient light and reflections come from the sky the viewer sees, in the editor and in builds.

**Build.**
1. Set Environment Lighting Source to Skybox (the default, ambient from the sky material), Gradient (sky, equator and ground colors) or Color, with its Intensity Multiplier. Set Environment Reflections to the skybox or a custom cubemap.
2. The trap: since 6.0, neither the ambient probe nor the sky's reflection gets baked on its own anymore. A new scene borrows a built-in lighting data asset made for the default skybox, so after you change the sky or the ambient settings, ambient light and reflections keep showing the default sky until you select Generate Lighting, or an editor script calls `Lightmapping.Bake` or `BakeAsync`. New Unity 6 projects also never bake on scene load.
3. A scene built by an editor script must end its setup with a lighting bake, and the generated lighting data gets committed with the scene ([project-hygiene.md](project-hygiene.md)).
4. At runtime, after changing `RenderSettings.skybox` or the ambient settings, call `DynamicGI.UpdateEnvironment` to refresh the ambient probe. It reads the sky back asynchronously where the device supports it and may lag a frame or more; elsewhere it stalls the thread. Reflections need a real-time reflection probe (below).
5. Gradient and Color ambient can change at runtime with no readback, which makes them the cheap route for a changing sky.

**Watch for.** A capture taken right after a sky change in a scripted setup; a runtime sky switch with no environment update; Environment Reflections pointing at a missing cubemap.

**Critic checks.** PASS when metal and glossy surfaces mirror surroundings consistent with the sky on screen, and shadows pick up the sky's color. FAIL signs: a blue noon tint under an orange sunset; reflections of some other sky; metal that looks black or dull gray.

**Diagnose.**
- New sky, old ambient light and reflections → Generate Lighting not run since the change.
- A runtime sky change with no change in ambient → no `DynamicGI.UpdateEnvironment` call.

**API facts** (check the installed version):
- Since 6.0, Unity bakes neither the ambient probe nor the sky's reflection probe until lighting is generated; until then a new scene uses a built-in lighting data asset made for the default skybox, so environment changes appear only after Generate Lighting (verified on 6000.6).
- Auto Generate is gone; `Lightmapping.Bake` and `Lightmapping.BakeAsync` replace it, and Bake On Scene Load defaults to Never in new Unity 6 projects (verified on 6000.6).
- After the skybox changes in Play mode, `DynamicGI.UpdateEnvironment` refreshes the ambient probe, asynchronously when `SystemInfo.supportsAsyncGPUReadback` is true and by stalling otherwise (verified on 6000.6).

## Light modes, units and intensities

**Goal.** Lights relate to each other believably, so one exposure suits the whole frame, and each light's mode matches whether it moves.

**Choose.**
- Realtime for lights that move or change: they cost every frame and cast real-time shadows.
- Mixed for lights whose direct part stays live while their bounce is baked. In the Baked Indirect lighting mode, small runtime changes work: direct light follows the change, baked bounce doesn't.
- Baked for static lights in static scenes. Area lights are always baked in URP.

**Build.**
1. URP has no physical light units: intensity scales the light's color. With linear intensity on, as in the template, it scales the linear color. Set every intensity as a ratio to the sun and keep the table in `PLAN.md`, so builders don't drift.
2. Use color temperature (Light Appearance: Filter and Temperature) for natural sources, on a Kelvin scale where D65 white is 6500 K, a warm bulb about 2700 K and a candle about 1800 K.
3. Point and spot lights fall off with inverse square; Range cuts them off.
4. Leave exposure to [final-image.md](final-image.md); never fix it light by light.

**Watch for.** Raising the ambient Intensity Multiplier to rescue dark shadows; a Baked light moved at runtime, whose light stays where it was baked; builders who each invent their own intensity scale.

**Start here** (adjust to the goal): the template's sun at intensity 2, with skybox ambient at an Intensity Multiplier of 1.

**API facts** (check the installed version):
- A URP light's Mode is Realtime, Mixed or Baked; Area lights are forced to Baked, and Rendering Layers apply only to Realtime and Mixed lights (verified on 6000.6).
- A new Directional light's intensity is 0.5 and a Point, Spot or Area light's is 1; Light Appearance is either Color or Filter and Temperature (verified on 6000.6).
- `GraphicsSettings.lightsUseLinearIntensity` multiplies intensity with the linear color and must be on for `lightsUseColorTemperature`, which multiplies the temperature's color with the filter color (verified on 6000.6).
- URP lights use inverse-square attenuation, and physical light units are HDRP-only (verified on 6000.6).

## Indirect light: Adaptive Probe Volumes or lightmaps

**Goal.** Rooms and shaded areas receive plausible bounced light (not inky black, not flat gray, unless the mood wants it) on every target, the Web included.

**Choose.**
- Adaptive Probe Volumes (APV) by default for agent-built scenes: probes placed automatically, sampled per pixel, no lightmap UVs needed, and lighting scenarios plus sky occlusion for changing light.
- Lightmaps for static architecture where crisp baked shadows and contact detail matter. They need lightmap UVs ([levels-and-geometry.md](levels-and-geometry.md)).
- Both together: lightmaps on static geometry, APV for dynamic objects and small props.
- Light Probe Groups only in a project that already depends on them; the template still ships with this legacy system selected.
- Nothing real-time: URP has no real-time GI on 6.6, and the Web supports baked GI only, with non-directional lightmaps.

**Build.**
1. In every tier's URP asset, choose Adaptive Probe Volumes as the Light Probe System (under Lighting); then create GameObject > Light > Adaptive Probe Volume with Mode set to Global.
2. Lights that bounce are Mixed or Baked; static meshes enable Contribute Global Illumination, and receivers set Receive Global Illumination to Light Probes.
3. In the Lighting window, enable Baked Global Illumination, set the APV baking mode (Single Scene, or a Baking Set across scenes), and Generate Lighting, or Bake Probe Volumes alone.
4. Fix leaks in this order: walls about as thick as the probe spacing; a Probe Volumes Options override that shifts where surfaces sample; interior and exterior Rendering Layer Masks; Virtual Offset and Dilation in the baking set; a Probe Adjustment Volume that invalidates probes in a small area.
5. Size the data per tier with the URP asset's APV Memory Budget and spherical harmonics bands (L1 or L2), and stream it when scenes are large.
6. For Web tiers, bake non-directional lightmaps (check the directional mode in Lightmapping Settings) and prove APV in a browser capture before relying on it.

**Critic checks.** PASS when room corners and shade keep readable detail and take on color bounced from nearby lit surfaces, unless darkness is the point. FAIL signs: black corners in a sunny room; flat gray shade with no colored bounce; light bleeding through walls; visible seams where probe spacing changes.

**Diagnose.**
- A moving object darker than its surroundings → it isn't inside a volume, or Receive Global Illumination isn't set to Light Probes.
- A seam across a floor → adjacent bricks with different probe densities.

**API facts** (check the installed version):
- APV samples probes per pixel rather than per object, supports streaming, automatic placement and blending between bakes, and has no manual placement (verified on 6000.6).
- APV leak fixes include a Probe Volumes Options override, up to 4 Rendering Layer Masks (which need Use Rendering Layers), Virtual Offset and Dilation, and Probe Adjustment Volumes (verified on 6000.6).
- The Web supports baked GI only, with non-directional lightmaps, and no real-time GI (verified on 6000.6).

## Choosing and running the light baker

**Goal.** Bakes finish on the Mac, repeat with the same result, and get re-tuned whenever the backend changes.

**Choose.**
- The Progressive GPU Lightmapper, the default for new projects since 6.3, for most bakes. On macOS it falls back to the CPU more readily, because free GPU memory is harder to read there.
- The Unity Compute Light Baker (new in 6.6, opt-in, URP and HDRP only) when the GPU baker runs short of memory: it bakes lightmaps, light probes and APV data on compute shaders, with hardware ray tracing where available.
- Never the Progressive CPU Lightmapper: deprecated in 6.6, and it counts bounced sky light twice when sky occlusion is on. Avoid Enlighten Realtime GI too: it needs Rosetta 2 on Apple silicon and loses support after Unity 6.

**Build.**
1. Set Project Settings > Graphics > Light Baker > Default Light Baker, and record the backend in `BRIEF.md`.
2. Bake from an editor script with `Lightmapping.BakeAsync`; batch runs belong to [agent-control.md](agent-control.md), and a baking run can't use `-nographics`.
3. Re-tune after a backend switch: the GPU lightmapper needs up to four times the indirect samples of the CPU one for equal quality, and the Compute baker has no Environment Samples setting.
4. On the Mac, keep bakes light: smaller lightmaps, fewer anti-aliasing samples, a lower-memory baking profile.
5. Bake when lighting changes, not in every capture round, and commit the baked data so every round shows the same light. Edits made while a bake runs don't reach it.

**API facts** (check the installed version):
- The Default Light Baker setting in Graphics settings chooses the backend; the Unity Compute Light Baker runs on compute shaders through the Unified Ray Tracing API, emulated or hardware-accelerated (verified on 6000.6).
- The Progressive CPU Lightmapper is deprecated, and the GPU lightmapper became the default for new projects in 6.3 (verified on 6000.6).
- On macOS the GPU lightmapper is likelier to fall back to the CPU, and Unity suggests the Compute baker for GPU memory problems (verified on 6000.6).
- Running with `-nographics` can't bake GI (verified on 6000.6).

## Reflection probes

**Goal.** Reflections show the surroundings each surface would really see, inside and out.

**Build.**
1. Outdoors, the environment reflection covers distant views; add box-projected probes near reflective surfaces that must show nearby objects.
2. Indoors, place one baked probe per room with its box fitted to the room and Box Projection on, both on the probe and in the URP asset; a closed room must not reflect the outdoor sky.
3. Where probes overlap, set Importance and Blend Distance, and keep Probe Blending on in the URP asset.
4. For moving light, use a Realtime probe with Refresh Mode Via Scripting, re-rendered when the sun has moved noticeably, with time slicing and a low resolution. Baked probes update with Generate Lighting, or alone with Bake Reflection Probes.
5. With the GPU Resident Drawer, probes need Forward+ or Deferred+, because the Forward and Deferred paths pick probes per object on the CPU ([performance-and-builds.md](performance-and-builds.md)).

**Watch for.** Metal with no probe nearby, which reflects the sky indoors; reflections that slide across a floor because box projection is off; probes captured before lighting was generated.

**Critic checks.** PASS when glossy floors, metals and windows reflect the room or street they stand in, and reflections don't pop as objects move between areas. FAIL signs: sky in an indoor reflection; reflections sliding over a surface as the camera moves; a reflection that switches abruptly.

**API facts** (check the installed version):
- At most two probes affect an object in URP, chosen by Importance, then by smaller box; leftover weight comes from the environment reflection (verified on 6000.6).
- Box Projection works only when it is enabled on the probe and in the URP asset; Blend Distance fades a probe from its box faces inward (verified on 6000.6).
- Realtime probes refresh On Awake, Every Frame or Via Scripting, and time slicing spreads one update over nine frames (all faces at once) or fourteen (face by face) (verified on 6000.6).
- The Forward and Deferred paths choose probes per object on the CPU, while Forward+ and Deferred+ support probes with indirect draws (verified on 6000.6).

## Shadows: cascades, distance, bias and softness

**Goal.** Objects sit on the ground through steady shadows that are sharp up close and reach as far as the shot requires, at a cost each tier can afford.

**Build.**
1. Set Max Distance first. The shadow map spreads over that distance, so a shorter one gives sharper near shadows at the same resolution; set it to the farthest view that needs shadows.
2. Use 1 to 4 cascades for the main light. URP doesn't blend between cascades, so place splits where a change in sharpness won't draw the eye, and use Last Border to fade shadows out before Max Distance instead of cutting them off.
3. Set resolution per tier: the main light's shadow map, and one shared atlas for spot and point shadows, sized for every shadowed light (a point light takes six maps).
4. Tune bias in the URP asset, and per light only where needed: too little shows acne stripes, too much detaches shadows and leaks light.
5. Soft shadows come in Low, Medium (the default) and High quality, settable per light.
6. Debug with the Rendering Debugger: Lighting Debug Mode Shadow Cascades, and Map Overlays for the shadow maps.

**Watch for.** Shadows that pop in and out because the scene has more visible lights than the limit allows (next section); semi-transparent casters, which shadow only through alpha clipping ([materials-and-shaders.md](materials-and-shaders.md)).

**Critic checks.** PASS when, across walkthrough frames, shadow edges stay put as the camera travels, lit surfaces carry no striping, shadows touch the objects that cast them, and the far end of the shadow range fades out. FAIL signs: edges that crawl; striped acne; shadows detached from their casters; a hard line on the ground where shadows stop or suddenly blur.

**Diagnose.**
- Soft, blocky near shadows → Max Distance too long for the resolution.
- A line where sharpness changes → a cascade split in plain view.
- Floating shadows or light leaking under walls → bias too high.

**Start here** (adjust to the goal): Max Distance at the farthest view that needs crisp shadows, and 4 cascades on the Mac's top tier.

**API facts** (check the installed version):
- Max Distance is in meters, Cascade Count applies to the main light only, and Last Border fades shadows out toward Max Distance (verified on 6000.6).
- Soft shadow quality is Low (4 PCF taps), Medium (5×5 tent, the default) or High (7×7 tent) (verified on 6000.6).
- URP has no blending between shadow cascades and casts transparent shadows only through alpha clipping (verified on 6000.6).
- When visible lights exceed the per-camera limit, URP disables some of them, which can make shadows flicker (verified on 6000.6).

## Additional lights, Forward+ and light layers

**Goal.** Many practical lights render without dropping, popping or costing more than the tier allows.

**Choose.**
- Forward+, the template's PC path: no per-object light limit, up to 256 visible lights per camera on desktop including the main light, no per-vertex lights, and a main light that can't be switched off.
- Forward, the template's Mobile path: 1 main and 8 additional lights per object, per-vertex lights allowed.
- Deferred or Deferred+: unlimited lights on opaque objects, but no MSAA, and never on WebGL 2, whose tier stays on Forward or Forward+.

**Build.**
1. Set the rendering path per tier on each Universal Renderer asset.
2. Give real-time shadows only to the few additional lights that need them.
3. Light layers: enable Use Rendering Layers in the URP asset's lighting settings (an advanced property), name the layers in Tags and Layers, then set each light's Rendering Layers and each renderer's Rendering Layer Mask so a rim light touches only the hero. Custom Shadow Layers keeps the hero's shadow from that light.
4. On WebGL 2, an OpenGL ES 3.0-class API, keep additional lights few and prove them in a browser capture.

**Watch for.** Lights that vanish as the camera turns; Forward+ shader builds that slow as the visible-light maximum grows, which the URP Config package can lower.

**API facts** (check the installed version):
- In the Forward path, an object takes 1 main and up to 8 additional lights; per camera, the limit is 256 additional lights on desktop, 32 on mobile and 16 on OpenGL ES 3.0 and earlier (verified on 6000.6).
- Forward+ ignores the URP asset's per-object limit and has no per-vertex lights (verified on 6000.6).
- Deferred has no MSAA, and in a camera stack its overlay cameras render with Forward (verified on 6000.6).
- Forward and Forward+ run on OpenGL and OpenGL ES, while Deferred and Deferred+ need shader model 4.5 and support neither (verified on 6000.6).

## Emissive surfaces and practical lights

**Goal.** Lamps, screens and signs actually illuminate the surfaces they face, and how brightly they glow follows how much they matter.

**Build.**
1. Pair each practical emitter with a real light: a point or spot for lamps, a baked area light for windows and panels, or a soft spot where the panel must move.
2. Emission lights other objects only through baked GI: set the material's emission Global Illumination to Baked, and dynamic objects pick that light up through probes. In real time, emission lights nothing around it.
3. Rank emissive HDR intensity by importance, for bloom ([final-image.md](final-image.md)).

**Critic checks.** PASS when lamps and screens throw visible light onto the walls, floors and objects in front of them, and the strongest glow is on the source that matters most. FAIL signs: bright lamps with no light around them; screens that spill nothing; all emitters at the same brightness.

**API facts** (check the installed version):
- URP area lights come in Rectangle and Disc shapes, baked only, and take no cookies (verified on 6000.6).
- A URP Lit material's emission Global Illumination is Realtime (Enlighten only), Baked or None (verified on 6000.6).

## Time of day

**Goal.** A moving sun drives light, sky, ambient, reflections and shadows together, at a cost each tier can carry, with a believable Web fallback.

**Choose.**
- A fixed time for most scenes: everything baked, with a real-time sun for shadows.
- A few set times (dawn, noon, dusk, night): one Lighting Scenario per time, blended with Scenario Blending, and a real-time sun.
- A continuous cycle: a real-time sun, Gradient or Color ambient driven by script, APV sky occlusion baked once so a changing sky color still respects occlusion, and a reflection probe refreshed when the sun has moved enough.
- On the Web: the fixed-time or scenario route, since there is no real-time GI, and no per-frame environment updates, which stall without async readback.

**Build.**
1. Let one time-of-day state drive the sun's rotation, color temperature and intensity, the ambient colors, fog, the sky material and exposure ([final-image.md](final-image.md)).
2. Update the expensive parts on thresholds, such as a probe re-render after the sun moves a set angle, never every frame.
3. Fade the sun's intensity and shadows near the horizon, so no shadows come from a sun below it, and pin the time for capture ([validation.md](validation.md)).

**Critic checks.** PASS when shadow length and direction agree with the sun's height and the sky at every captured time, and light warms near the horizon. FAIL signs: long shadows under a high sun; a dusk sky over noon-colored light; reflections from another time of day.

**API facts** (check the installed version):
- Sky occlusion dims sky light where probes can't see the sky, and updates at runtime from the ambient probe; that needs Gradient or Color ambient, or Skybox ambient refreshed with `DynamicGI.UpdateEnvironment` at a very large cost (verified on 6000.6).
- Lighting Scenarios and Scenario Blending are enabled in the URP asset, and `ProbeReferenceVolume.instance` switches scenarios through `lightingScenario` and blends them with `BlendLightingScenario` (verified on 6000.6).
- In the Baked Indirect lighting mode, small runtime changes to a Mixed light affect its direct light only, while its baked bounce stays as baked (verified on 6000.6).

## Symptom → cause

| Symptom | Likely cause | First check |
| --- | --- | --- |
| Flat light or shadows filled to gray | frontal key, or ambient raised to fix dark shadows | key direction in the clay pass; Intensity Multiplier |
| New sky, old ambient light and reflections | lighting not generated since the change | Generate Lighting |
| Right in the editor, wrong in the build | lighting data not generated or committed | the scene's lighting data |
| Shadows disagree with the sky's sun | Sun Source unset, or two suns | the Lighting window's Sun Source |
| Pitch-black interior corners | no probes or lightmaps receiving bounce | the APV setup and Receive Global Illumination |
| Light leaking through walls | probes on the far side of thin walls | APV leak fixes |
| Bake falls back to the CPU on the Mac | GPU memory | baking profile, lightmap size, the Compute baker |
| Sky reflected indoors, or reflections sliding | no probe for the room, or box projection off | the room's probe and the URP asset's Box Projection |
| Soft, blocky near shadows | Max Distance too long for the map | Max Distance, resolution |
| Acne stripes or floating shadows | bias too low or too high | URP asset and per-light bias |
| Hard line where shadows end | no fade at Max Distance | Last Border |
| Lights or shadows flicker as the camera turns | visible lights over the limit | light count; the rendering path |
| Rim light spills onto everything | no light layers | Rendering Layers on the light and renderer |
| Glowing lamps that light nothing | emission without a real light, or not baked | a paired light; emission Global Illumination |
