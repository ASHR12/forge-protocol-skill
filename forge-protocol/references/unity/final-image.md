# Unity final image: output owner, volumes, tone mapping, exposure, post effects and anti-aliasing

API facts verified on Unity 6.6 (6000.6.4f1, 2026-10-06). Check the project's Unity version first (ProjectSettings/ProjectVersion.txt); if it differs, confirm in that version's official docs or the installed packages. The installed version wins.

Read when you own the final image of a URP build: the camera's post switch, the one Global Volume, tone mapping and exposure, bloom, ambient occlusion, depth of field, motion blur, grading, anti-aliasing and the tonemapping-only profile for the no-post still. Light design is in [lighting-and-shadows.md](lighting-and-shadows.md), lens flares and full-screen effects in [effects.md](effects.md), frame cost in [performance-and-builds.md](performance-and-builds.md), and when to capture the no-post still in [validation.md](validation.md).

## Contents

- The no-post baseline comes first
- One output owner: the camera switch and one Global Volume
- Volume layering, masks and caching
- Tone mapping
- Exposure without auto exposure
- Bloom
- Screen-space ambient occlusion
- Depth of field and motion blur
- Grading, LUTs, grain and vignette
- Choosing anti-aliasing
- HDR rendering and banding
- The tonemapping-only debug profile
- Symptom → cause

## The no-post baseline comes first

**Goal.** Post effects polish an image that already works; they can't add the shape, the material contrast or the light direction a scene is missing.

**Build.**
1. When the build uses post-processing, get every hero view's no-post still to hold up by itself (a clear outline, distinct materials, a visible light direction, one focal point) before tuning any effect.
2. In URP, tone mapping is one of the post stack's Volume overrides, so unticking the camera's Post Processing removes tone mapping as well as the effects. Make the no-post still with the tonemapping-only debug profile (last section), never with the camera switch.
3. Wire that profile, and every renderer feature that acts as post, to the build's debug-mode hook; [validation.md](validation.md) decides when the still is captured.

**Critic checks.** PASS when every hero view's no-post still shows the subject's outline, tells its materials apart and keeps one focal point. FAIL signs: an outline made only of glow; a frame that goes flat or confusing once effects are off; SSAO or bloom doing the work of missing contact shadows or light.

**Diagnose.** Reads only with effects on → something upstream was never authored (a rim light, contrast between values, contact shadows, emitters ranked by brightness); build that instead of adding post.

## One output owner: the camera switch and one Global Volume

**Goal.** One place in the project tone-maps the image and converts it for the display, exactly once, for every camera.

**Build.**
1. Turn on Post Processing on the camera that renders the scene; new cameras start with it off, though the 3D URP template's sample camera has it on. In a camera stack, enable it only on the last camera, so URP applies post once to the whole stack.
2. Give each scene one Global Volume (GameObject > Volume > Global Volume), ideally one prefab shared by every scene, whose profile owns Tonemapping, exposure and the grade. Builders add effects to that profile, never a second global volume.
3. Keep the camera's Volume Mask including that volume's layer. Masks default to the Default layer.
4. Keep the project's Default Volume Profile (Project Settings > Graphics > URP) and each URP asset's Volumes profile neutral, so the scene volume is the only source, and record the owner (volume, profile, tone mapper, exposure) in the PLAN contracts. The bundled URP template points both its URP assets at its sample profile, which carries Neutral tone mapping, bloom at 0.25 and a 0.2 vignette into every scene, so a project left as created already uses post-processing and needs the no-post still ([validation.md](validation.md)): replace that profile with a neutral one, or declare it the owner and keep scene volumes free of the same overrides.

**Watch for.** A second Global Volume arriving with a sample prefab; an overlay camera with its own post switch on; per-tier URP assets pointing at different Volumes profiles, so tiers disagree on tone mapping. For UI that must keep exact colors, capture a UI swatch with post on and off once to see whether the grade reaches it ([input-ui-and-audio.md](input-ui-and-audio.md)).

**API facts** (check the installed version):
- A new camera starts with Post Processing off, anti-aliasing at None and its Volume Mask on the Default layer; scripts reach these through `camera.GetUniversalAdditionalCameraData()` as `renderPostProcessing`, `antialiasing` and `volumeLayerMask` (verified on 6000.6).
- In a camera stack, post-processing belongs on the last camera, so URP renders it once and every camera in the stack gets the same treatment (verified on 6000.6).

## Volume layering, masks and caching

**Goal.** The values on screen are the ones you set, from the volumes you meant.

**Build.**
1. Know the stack. Two default volumes apply to every scene at the lowest priority: the project's Default Volume and the active URP asset's Volumes profile. Scene volumes sit on top by priority, and local ones blend by camera position, Blend Distance and Weight.
2. A property applies only when its override toggle is on; unticked properties fall through to lower volumes. Unticking a whole override removes its contribution, so a lower volume's value shows through instead.
3. Give areas their own exposure or grade with local volumes (Box, Sphere or Convex Mesh Volume objects, or a Volume with a trigger collider), at a priority above the global owner and with a blend distance so the change eases in. Local volumes need the physics module.
4. For third-person views, set the camera's Volume Trigger to the character, so zones follow the character rather than the camera. For static grading, Volume Update Mode can drop from Every Frame to Via Scripting; the camera's stack then refreshes only when a script asks.
5. At runtime, edit the scene volume through `Volume.profile`, a copy owned by that volume. Never script the default or quality-level profiles: URP caches them, so edits do nothing unless you force a recache, which slows volume blending.

**Watch for.** A volume on a layer the camera's mask excludes; two volumes overriding one property at equal priority; editing a profile asset in Play mode, which changes the asset itself.

**Diagnose.**
- A change made in the Inspector shows, the same change from a script doesn't → the script edited a cached default or quality-level profile.
- An effect appears in one tier only, or leaks into every scene → it lives in a URP asset's Volumes profile or the default profile.

**API facts** (check the installed version):
- The Default Volume Profile lists every override and can't drop any; it and the active URP asset's Volumes profile are evaluated on scene load or quality change and cached, so script edits to them have no effect (verified on 6000.6).
- `VolumeManager.instance.OnVolumeProfileChanged(profile)` forces the cache to refresh, at a cost to volume interpolation (verified on 6000.6).
- `Volume.profile` clones the shared profile for that volume, and `sharedProfile` is the asset itself; `camera.UpdateVolumeStack()` refreshes a camera whose updates run via scripting (verified on 6000.6).
- A local volume takes its bounds from a collider on its GameObject, and a Blend Distance of 0 applies its overrides on entry (verified on 6000.6).

## Tone mapping

**Goal.** Bright areas compress gracefully, mid-tones stay crisp, and the brief's key colors come through unchanged.

**Choose.**
- Neutral for products, brand colors, stylized palettes and any project that will be graded heavily: it remaps range while changing hue and saturation as little as it can. URP 17.6 offers only these three modes, so a custom response goes through grading on top of Neutral.
- ACES for a cinematic, contrasty look: it shifts hue and saturation in bright areas, and URP grades in ACES space when it is selected.
- None only for flat, unlit work without HDR values; an HDR scene clips.

**Build.**
1. Set Tonemapping once, in the owner volume, and fix light ratios before tuning it ([lighting-and-shadows.md](lighting-and-shadows.md)); the tone mapper never repairs them.
2. With HDR Output on, the override adds Paper White and brightness limits; take them from the display or a calibration screen.

**Critic checks.** PASS when bright areas fade smoothly toward white instead of clipping into flat patches (the sun and tiny glints excepted), mid-tones stay distinct, and the brief's named colors hold their hue in every still. FAIL signs: blown-out white areas with no detail; skin or brand colors drifting toward orange; a dull frame with no contrast.

**Diagnose.**
- Neon or brand colors drift → ACES used where color accuracy matters.
- Clipped, flat highlights → Tonemapping None, or no owner volume reaching the camera.

**Start here** (adjust to the goal): Neutral for products, brands and stylized looks, and ACES for cinematic realism.

**API facts** (check the installed version):
- `TonemappingMode` has None, Neutral and ACES; Neutral keeps hue and saturation changes minimal, and ACES adds contrast and alters hue and saturation (verified on 6000.6).
- When HDR Output is active, the grading mode is HDR whatever the URP asset says, and ACES offers presets for 1000, 2000 and 4000 nit displays (verified on 6000.6).

## Exposure without auto exposure

**Goal.** Each view sits at a deliberate brightness, and moves between bright and dark areas read as the brief intends, without the eye adaptation URP lacks.

**Choose.**
- Fixed exposure for one lighting situation, which covers most scenes: set light intensities until mid-tones land with Post Exposure at 0, then trim in EV.
- Zone exposure where the camera crosses light levels (interior to exterior, caves, night streets): local volumes with their own Post Exposure and a wide blend distance.
- Scripted exposure only when zones can't express it, such as a sky darkening over time: drive Post Exposure from the same time-of-day or zone state that drives the lights, eased with a time constant. Metering the image needs GPU readback; where `SystemInfo.supportsAsyncGPUReadback` is false, keep the authored curve.

**Build.**
1. Post Exposure lives in the Color Adjustments override. URP applies it after the HDR effects and before tone mapping, so it changes neither how much bloom nor how much depth of field there is. Tune the bloom threshold against the scene's brightness before exposure.
2. Keep the brightness ratio between zones believable; exposure compresses it, never invents it, and never rescues flat, dark lighting.
3. Let zone blends and scripted exposure settle, then pin them before capture ([validation.md](validation.md)).

**Critic checks.** PASS when each still's subject sits at a deliberate brightness and walkthrough frames ease between bright and dark areas without a jump. FAIL signs: a frame that pops brighter or darker at a zone edge; a subject lost in murk or blown out.

**Diagnose.** Brightness jumps at a doorway → a zone volume with no blend distance. Bloom looks weaker after raising exposure → bloom is computed before Post Exposure; retune bloom.

**Start here** (adjust to the goal): Post Exposure 0 EV once the lights read right, and a zone blend distance about as wide as the transition the camera crosses.

**API facts** (check the installed version):
- URP supports fixed exposure only; automatic exposure is HDRP-only on 6.6 (verified on 6000.6).
- Post Exposure is in EV (not EV100) and is applied after the HDR effects and before tone mapping (verified on 6000.6).

## Bloom

**Goal.** Glow looks like a lens reacting to things that are truly bright, and the biggest glow marks the source that matters most.

**Build.**
1. Rank emitters before touching bloom: the source that matters most gets the highest HDR emission, and ordinary lit surfaces stay below the threshold.
2. Raise Intensity from 0, where bloom is off, only until emitters glow. Threshold is a brightness in gamma space; Scatter sets the radius.
3. Use Clamp to cap the brightness bloom considers, so a few extreme pixels such as glints can't flare across the frame.
4. Turn on High Quality Filtering when halos flicker. Changing the Filter (Gaussian by default, Dual or Kawase for speed) changes the look, so recheck the stills of any tier that switches. Add Lens Dirt only when the brief asks for a lens look.

**Watch for.** Bloom as an object's only edge; a haze across the whole frame from a low threshold; halos flickering because glints alias upstream (filter the glints, or resolve TAA first).

**Critic checks.** PASS when every form survives in the no-post still, only light sources and hot glints glow in the final, and the brightest glow sits on the source that matters most. FAIL signs: a milky haze over everything; objects outlined only by glow; halos that shimmer from frame to frame.

**Start here** (adjust to the goal): the bloom threshold set just over the brightest surface that isn't an emitter, and intensity raised until only the emitters glow.

**API facts** (check the installed version):
- Bloom's Threshold is a gamma-space brightness defaulting to 0.9, Intensity defaults to 0 (off), Scatter to 0.7 and Clamp to 65472 (verified on 6000.6).
- The Filter defaults to Gaussian; Dual is the faster choice for mobile and Kawase the fastest at low resolution, and each changes the look (verified on 6000.6).
- High Quality Filtering samples with bicubic filtering to cut flicker, at a performance cost (verified on 6000.6).

## Screen-space ambient occlusion

**Goal.** Shade deepens in corners, cracks and contact points, while sunlit surfaces stay clean and outlines stay free of dark rings.

**Build.**
1. Bake occlusion into textures and baked lighting for static detail in every tier, and add the Screen Space Ambient Occlusion renderer feature for dynamic contact grounding in the tiers that can afford it, on each one's Universal Renderer asset. It isn't a Volume override, so the debug profile can't remove it.
2. Use Depth Normals as the source unless custom shaders lack the DepthNormals pass.
3. Keep Direct Lighting Strength low, so sunlit faces keep their brightness and AO darkens mostly shade.
4. Match Radius to the scale of the contacts, in scene meters, and use Falloff Distance to stop AO far away. Downsample in lower tiers.
5. Leave After Opaque off where baked occlusion exists; it can darken those areas twice.
6. Don't rely on SSAO for grass, hair or other thin moving geometry, where it turns blotchy; bake darkening into the base of each blade instead.

**Critic checks.** PASS when corners, cracks and contact points darken gently, surfaces in direct sun stay at full brightness, and foreground outlines show no dark ring. FAIL signs: sunlit walls dulled to gray; dark auras around characters; blotchy or swimming shade in grass.

**Diagnose.** Gray sunlit walls → Direct Lighting Strength too high. Halos → a radius too large for the scene. Crawling noise → Blue Noise method on a still camera, or too few samples.

**API facts** (check the installed version):
- SSAO is a URP renderer feature with Method (Interleaved Gradient Noise for static noise, Blue Noise for animated), Intensity, Radius, Falloff Distance and Direct Lighting Strength (verified on 6000.6).
- Source is Depth Normals or Depth; Downsample halves the AO resolution; After Opaque can over-darken areas with baked occlusion; Radius, Blur Quality and Samples cost the most (verified on 6000.6).
- `ScriptableRendererFeature.SetActive(bool)` switches a renderer feature on or off from code (verified on 6000.6).

## Depth of field and motion blur

**Goal.** Focus guides the eye only in shots that call for it, and motion blur appears only on camera moves and fast objects.

**Build.**
- Depth of field: Gaussian mode blurs only the far field, from Start to End, and suits lower tiers; Bokeh behaves like a lens through Focus Distance, Focal Length and Aperture and suits desktop. Feed Focus Distance from the distance to the subject the camera rig tracks ([camera-and-animation.md](camera-and-animation.md)), and keep Max Radius at 1 or below.
- Motion blur: Camera Only needs no motion vectors and costs less; Camera and Objects blurs moving objects too. Keep Intensity modest, and Clamp limits blur during fast turns.
- Neither may blur a must-have or the UI, and both get neutral values in the debug profile.

**Critic checks.** PASS when the subject in focus is crisp in every hero still, nearer and farther areas soften gradually with no bright fringe around the subject, and motion blur shows only while things move. FAIL signs: a blurry subject; glowing fringes around near edges; a must-have smeared, or blur on a camera at rest.

**API facts** (check the installed version):
- Depth of Field's Mode is Off, Gaussian (Start, End, Max Radius, where values above 1 can undersample) or Bokeh (Focus Distance, Focal Length in millimeters, Aperture, blade shape) (verified on 6000.6).
- Motion Blur's Mode is Camera Only or Camera and Objects, and Clamp, a fraction of the screen, defaults to 0.05; Unity suggests Gaussian depth of field on low-end hardware and Bokeh on desktop (verified on 6000.6).

## Grading, LUTs, grain and vignette

**Goal.** A grade that serves the brief's mood with restraint and keeps the colors the brief names on their hue.

**Build.**
1. Pick the grading mode in the URP asset first. High Dynamic Range grades before tone mapping, with more precision; Low Dynamic Range grades after it, in a limited range. The template ships Low Dynamic Range.
2. Most grades need only a few small moves among White Balance, Color Adjustments, Channel Mixer, Lift Gamma Gain, Shadows Midtones Highlights and Color Curves.
3. Apply a LUT through Color Lookup, blended by Contribution. Author it for the grading mode in use and at the URP asset's LUT Size; sizes can't be mixed.
4. Recheck skin, product and brand colors after every grade change.
5. Add film grain or a vignette only when the brief asks for a filmic or lens look, keep both low, and never use a vignette to hide unfinished frame edges. Chromatic aberration, lens distortion and Panini projection are rare tools.

**Critic checks.** PASS when the grade keeps every named color on its hue, blacks stay deep without a gray lift, and the corners of the frame stay readable. FAIL signs: skin or brand colors pushed off hue; milky blacks; heavy grain or vignette masking detail; color fringes at edges.

**API facts** (check the installed version):
- The URP asset's Grading Mode is High Dynamic Range (grading before tone mapping) or Low Dynamic Range (a limited grade after it), and LUT Size defaults to 32 (verified on 6000.6).
- Color Lookup takes a Lookup Texture and a Contribution that blends the graded image with the original (verified on 6000.6).

## Choosing anti-aliasing

**Goal.** Silhouettes and thin features stay continuous at native size, with a method each tier and platform can run.

**Choose.**
- MSAA, set in the URP asset: clean geometry edges with no temporal artifacts. It works on forward paths only, can run alongside FXAA or SMAA, can't run with TAA, and doesn't touch shader or texture aliasing.
- FXAA or SMAA, on the camera: FXAA is the cheapest and softest; SMAA is sharper, with three quality levels.
- TAA, on the camera: the best answer to shimmer and specular sparkle, at the risk of ghosting behind fast, contrasting motion. It can't combine with MSAA, camera stacking or dynamic resolution. Transparent materials write no motion vectors, and vertex-animated Shader Graph materials need Additional Motion Vectors set ([materials-and-shaders.md](materials-and-shaders.md)).
- STP, set as the URP asset's Upscaling Filter: a spatial-temporal upscaler that forces TAA, stays active at render scale 1, and needs compute.
- None of them for shader aliasing; filter that at its source ([materials-and-shaders.md](materials-and-shaders.md)).

**Build.**
1. Choose explicitly: the template camera ships with no post AA and its URP assets with MSAA off.
2. Mac top tier: TAA, or STP when rendering below native resolution; keep that tier free of camera stacks.
3. WebGL 2 rule: there is no compute, so no STP. Use SMAA or FXAA on the camera, add MSAA where the browser allows it, and prove TAA in a browser capture before relying on it. On a WebGPU tier, prove STP the same way before shipping it.

**Critic checks.** PASS when outlines and thin details such as wires and railings stay unbroken at native size, and walkthrough frames show steady edges with nothing smeared behind moving objects. FAIL signs: stair-stepped edges on the hero; thin details dissolving into dotted lines; trailing ghosts.

**Diagnose.** Ghost trails → TAA or STP with missing motion vectors, or a history blend set too high. TAA silently missing → a UI or weapon camera stacked on it, MSAA, or dynamic resolution. Jagged edges only in the Web capture → MSAA refused by the browser; rely on post AA there.

**Start here** (adjust to the goal): TAA on the Mac's top tier, and SMAA on WebGL 2 tiers.

**API facts** (check the installed version):
- TAA can't be combined with MSAA, camera stacking or dynamic resolution (verified on 6000.6).
- STP needs compute shaders (Shader Model 5.0), doesn't run on OpenGL ES, turns on TAA itself, stays active at render scale 1.0, and works with Render Scale but not Dynamic Resolution (verified on 6000.6).
- MSAA can run alongside FXAA or SMAA but not TAA, and fixes neither specular nor texture aliasing (verified on 6000.6).
- WebGL 2 is the Web's default graphics API, close to OpenGL ES 3.0, without native compute shaders, and anti-aliasing works on most but not all browser and GPU combinations (verified on 6000.6).

## HDR rendering and banding

**Goal.** The scene renders in HDR at a precision that doesn't band, and gradients stay smooth on 8-bit displays.

**Build.**
1. Keep HDR on in every URP asset, at the default 32-bit precision. Switch to 64-bit when dark or foggy gradients band, accepting more bandwidth, or when post must keep an alpha channel.
2. Turn on the camera's Dithering for skies, fog and dark gradients.
3. Render Scale scales only the 3D render; UI stays at native resolution. Upscaling choices per tier are in [performance-and-builds.md](performance-and-builds.md). Use Stop NaNs only to diagnose black or flashing pixels.

**Critic checks.** PASS when skies, fog and dim gradients shade smoothly, with no visible steps, in every still. FAIL signs: rings or stripes across the sky; fog broken into flat bands; stray black or blinking pixels.

**API facts** (check the installed version):
- HDR Precision is 32-bit by default; 64-bit avoids banding at a bandwidth cost, and Alpha Processing needs it (verified on 6000.6).
- The camera's Dithering applies 8-bit dithering to the final image, and Stop NaNs replaces NaN pixels with black at a performance cost, only with Post Processing on (verified on 6000.6).
- Render Scale leaves UI at native resolution; the Automatic upscaling filter picks Nearest-Neighbor for integer scales and Bilinear otherwise, while FSR 1.0 and STP stay active at scale 1.0 (verified on 6000.6).

## The tonemapping-only debug profile

**Goal.** A no-post still that shows the same image minus every effect, with the display transform kept, so the critic judges form, materials and light alone.

**Build.**
1. Keep the camera's Post Processing on: tone mapping lives in the post stack, and switching post off would change the display transform as well as remove effects.
2. Make a second Volume Profile, for example `NoPost`. Give it Tonemapping in the owner's mode (and HDR Output settings), and Color Adjustments with only Post Exposure toggled on, at the owner's value: in URP, exposure belongs to the display transform. Then add every effect override that any volume in the build can turn on, with its toggles on and its neutral value: Bloom intensity 0, Vignette intensity 0, Film Grain intensity 0, Chromatic Aberration intensity 0, Lens Distortion intensity 0, Panini Projection distance 0, Depth of Field mode Off, Motion Blur intensity 0, Color Lookup contribution 0, Screen Space Lens Flare intensity 0, White Balance at 0, and identity values for every other grading override.
3. Put it on a Global Volume with Weight 1, a Priority above every other volume in the build, and a layer the camera's Volume Mask includes. Keep it disabled.
4. The debug-mode hook enables that volume and turns off SSAO and any full-screen or custom post renderer features with `SetActive(false)`. It leaves the camera, anti-aliasing, render scale and tier unchanged, and switching back restores all of them.
5. Never build it by unticking overrides: an inactive override contributes nothing, so lower volumes' effects show through.
6. Check it on the running build: compared with the final, the no-post still should lose the effects and nothing else. Identical stills mean the switch isn't wired; a change in overall brightness or contrast means the tone mapper or exposure differs.

**Diagnose.** The no-post still still glows, blurs or vignettes → an override missing from `NoPost` (compare the two profiles' override lists whenever either changes), a higher-priority local volume, or a renderer feature left on. The no-post still is darker or flatter overall → Post Exposure or the tone mapper doesn't match the owner.

**API facts** (check the installed version):
- `VolumeComponent.active` switches all of an override's parameters off at once, and each parameter applies only while its `overrideState` is true (verified on 6000.6).
- `VolumeProfile.Add<T>()` and `TryGet<T>()` add and find overrides from an editor script, and `VolumeParameter.Override(value)` sets a value and turns its toggle on (verified on 6000.6).
- A Volume's `isGlobal`, `weight` and `priority` fields, where the highest priority wins a contested property, and the camera's `volumeLayerMask` decide whether the debug volume applies (verified on 6000.6).

## Symptom → cause

| Symptom | Likely cause | First check |
| --- | --- | --- |
| No effects at all | camera's Post Processing off, or the volume's layer outside the Volume Mask | the camera's Rendering section |
| Clipped, flat highlights | Tonemapping None, or no owner volume reaching the camera | the owner profile's Tonemapping |
| One tier or scene has a different look | another Volumes profile on that tier's URP asset, or a second Global Volume | each URP asset's Volumes profile; the scene's volumes |
| Script changes to post do nothing | edits to the cached default or quality-level profile | which profile the script edits |
| Brightness jumps at a doorway | zone volume with no blend distance | the local volume's Blend Distance |
| Everything glows, or halos flicker | bloom threshold too low, or aliased glints upstream | Threshold against the brightest lit surface; High Quality Filtering |
| Gray film on sunlit walls, splotches in grass | SSAO Direct Lighting Strength too high, or SSAO on thin moving geometry | the SSAO renderer feature |
| Ghost trails behind moving things | TAA or STP history, or missing motion vectors | the camera's TAA settings; motion vectors |
| Jagged edges only on the Web | MSAA refused by the browser, or STP unavailable | the Web tier's AA choice |
| Banded sky or fog | 32-bit HDR precision or no dithering | HDR Precision; camera Dithering |
| The no-post still matches the final exactly | the debug switch never reaches the debug volume | the debug-mode hook |
| No-post still darker than the final | Post Exposure or tone mapper missing from the debug profile | `NoPost` against the owner profile |
