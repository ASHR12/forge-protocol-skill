# Three.js final image

API facts verified on r186 (2026-10-05). Check the installed version first; if it differs, confirm in the official docs or the installed source. The installed version wins.

Read this when you own the final image: the output transform, tone mapping and exposure, the post chain, the choice of AO and GI, temporal AA, reflections, bloom, lens effects and grading.

## Contents

- The no-post baseline comes first
- One output owner
- Tone mapping and exposure
- Building the chain: passes, MRT, order and ownership
- Ambient occlusion and screen-space GI
- Temporal AA, upscaling and motion vectors
- Choosing and ordering antialiasing
- Screen-space reflections and god rays
- Bloom
- Depth of field and motion blur
- Grading, grain and banding
- Resolution policies
- Symptom → cause

## The no-post baseline comes first

**Goal.** Post-processing presents a finished image. It never supplies the form, material separation or light direction the scene lacks.

**Build.**
1. Before adding any pass, make the no-post still of every hero view read on its own: silhouette, material separation, light direction and focal point.
2. Tune post-processing only after that still passes. This is the escalation guard, and [validation.md](validation.md) applies it to the loop.
3. Give every pass an off switch wired to the debug-mode hook, plus an effect-only view where that helps. The no-post mode switches off the effect passes but keeps tone mapping and display output, so it shows the same image minus effects.

**Critic checks.** PASS when the no-post still of each hero view keeps the subject's silhouette, material separation and focal point. FAIL signs: an edge that exists only as glow; a frame that turns flat or illegible with post off; AO or bloom standing in for missing contact or light.

**Diagnose.** Right only with post → an authored system is missing upstream, such as emissive ranking, a rim light, value contrast or contact shadows; fix it there.

## One output owner

**Goal.** Tone mapping and the conversion to display happen exactly once.

**Choose.**
- No post chain: the renderer owns output through `toneMapping` and `outputColorSpace`.
- A `RenderPipeline` whose passes all work on scene-referred color: keep the default output transform, which applies the renderer's settings at the end.
- A chain that needs display-referred input after tone mapping (FXAA, a display-domain lookup table, grain, UI composites): switch the automatic transform off and place one `renderOutput()` where the scene-referred part ends.
- `DirectRenderPipeline` only for simple scenes without post or transmission: it saves a framebuffer, at the cost of the limits in the facts below.
- HTML and CSS UI stays outside the chain. In-world UI drawn by the scene pass gets tone-mapped with everything else, so draw it in a separate pass composited after output when its colors must stay exact.

**Watch for.** Tone mapping in a custom material and again at output; a manual sRGB encode in a final shader on top of the renderer's own.

**Critic checks.** PASS when bright areas roll off smoothly instead of forming flat or banded plateaus, and the darkest areas stay deep without a gray veil. FAIL signs: doubled contrast or a washed-out look across the whole frame; posterized highlights.

**API facts** (check the installed version):
- `RenderPipeline`, renamed from `PostProcessing` in r183, works only with `WebGPURenderer`; set `needsUpdate = true` after changing `outputNode` (verified on r186).
- `outputColorTransform` (default true) applies the renderer's tone mapping and output color space at the end of the chain; set it to false and end the scene-referred part with one `renderOutput()` when later passes need display-referred input (verified on r186).
- `DirectRenderPipeline`, new in r186, applies output processing inside material shaders and skips the intermediate framebuffer; it changes blending and doesn't support transmissive or other framebuffer-sampling materials (verified on r186).
- `material.toneMapped` is read only by `WebGLRenderer`; under `WebGPURenderer` the whole scene pass is tone-mapped at output (verified on r186).

## Tone mapping and exposure

**Goal.** Highlights roll off, mid-tones keep their contrast, and the colors the brief cares about stay true.

**Choose.**
- `AgXToneMapping` for natural scenes with strong HDR (sun, fire, emitters): bright saturated colors fade gracefully toward white instead of shifting hue.
- `ACESFilmicToneMapping` for a punchier, more contrasty look; it skews and saturates bright colors, so oranges and skies shift.
- `NeutralToneMapping` for products, brand colors and UI-matched colors under near-neutral, well-exposed light: it keeps base color and hue, but shows hard contours when pushed by strong HDR or colored volumes.
- `NoToneMapping` or `LinearToneMapping` only for flat, UI-like work without HDR values.

**Build.**
1. Fix the light ratios first ([lighting-and-shadows.md](lighting-and-shadows.md)); exposure never repairs them.
2. Hold exposure fixed when lighting is stable, which covers most scenes, and pin it or let it settle before capture ([validation.md](validation.md)).
3. Meter and adapt exposure only when lighting swings (tunnels, interiors to exteriors, day to night). Measure the log-average luminance of a small downsampled HDR target, never the final 8-bit image; adapt faster toward bright than toward dark, with delta-based smoothing; clamp the range; expose the meter in a debug view.

**Critic checks.** PASS when highlights roll off rather than clip to flat white (apart from the sun disc and small glints), mid-tones keep their separation, and every color the brief names (brand, product, skin) reads as its intended hue in every still. FAIL signs: flat white plateaus; neon or skin hues pushed toward orange or yellow; a muddy, low-contrast frame.

**Diagnose.**
- Brand or neon colors shift hue → ACES on content that needs fidelity.
- Hard contours in bright volumes → Neutral pushed by strong HDR.
- A gray, flat frame → tone mapping applied twice.
- Clipped highlights → `NoToneMapping` on an HDR scene.

**Start here** (adjust to the goal): AgX for natural scenes, and Neutral when exact product or brand color matters.

**API facts** (check the installed version):
- The tone mappers are `NoToneMapping` (the renderer default), `LinearToneMapping`, `ReinhardToneMapping`, `CineonToneMapping`, `ACESFilmicToneMapping`, `AgXToneMapping`, `NeutralToneMapping` and `CustomToneMapping`; `toneMappingExposure` defaults to 1 (verified on r186).
- `NeutralToneMapping` implements the Khronos commerce-standard tone mapper (verified on r186).

## Building the chain: passes, MRT, order and ownership

**Goal.** An explicit, inspectable order in which each signal is produced once and each pass reads only what it needs.

**Build.**
1. Render the scene once with `pass(scene, camera)`, adding MRT outputs only for what later passes read: normals, velocity, emissive, metalness and roughness, diffuse color. Store data outputs at 8 bits where precision allows, to save bandwidth.
2. Keep this order, scene-referred until the output transform: the scene pass and its MRT; AO or GI applied through the material lighting; SSR added on top; volumetric and atmosphere composites; the temporal resolve (TRAA or TAAU); bloom; depth of field or motion blur; tone mapping and display conversion; then display-referred passes such as FXAA, display-domain grading, grain and dither.
3. Keep effect-local passes (a portal view, frost on glass, a minimap) on their own targets, outside this order unless they must share its buffers.
4. Count scene renders: every extra `pass()` of the scene draws the whole scene again.
5. Before building three or more passes, list every signal in the builder's notes or `PLAN.md`: what produces it, what reads it, its color space and format, its resolution, whether it keeps history, and how to switch it off. Allow one producer per signal (a second depth or normal prepass needs a measured reason), reset history on cuts, teleports, resizes and tier changes, and remove any pass that nothing reads.

**Watch for.** Thresholds or lookup tables tuned for display-referred values sitting in the scene-referred part, or the reverse; MSAA multiplying the memory of every MRT attachment.

**API facts** (check the installed version):
- `pass(scene, camera)` renders the scene into a target, and `setMRT(mrt({ ... }))` adds named outputs built from TSL nodes such as `output`, `velocity`, `emissive`, `metalness`, `roughness` and `normalView`; later nodes read each one with `getTextureNode(name)` (verified on r186).
- `packNormalToRGB()`, renamed from `directionToColor()` in r185, packs `normalView` into a color attachment (verified on r186).
- `pass()` accepts a `samples` option and otherwise inherits the renderer's MSAA setting (verified on r186).
- `setResolutionScale()`, renamed from `setResolution()` in r181, renders a pass below full resolution (verified on r186).

## Ambient occlusion and screen-space GI

**Goal.** Ambient light darkens in creases and at contacts, and picks up bounce color where it matters, without graying sunlit faces or haloing silhouettes.

**Choose.**
- Baked AO in the assets for static detail: cheap and stable, so use it in every tier.
- GTAO (`ao()`) for dynamic contact grounding in most scenes.
- SSGI (`ssgi()`) when color bleeding matters and most bouncing surfaces are on screen. It outputs its own AO, so don't add GTAO on top.
- Voxel GI (`vxgi()`) for static architecture under moving lights.
- Baked probes or lightmaps when indirect light must be cheap and stable ([lighting-and-shadows.md](lighting-and-shadows.md)).

**Build.**
1. Apply screen-space AO through the material lighting, so it scales indirect light only. That needs a depth and normal prepass, so the scene renders twice. Multiplying AO onto the final color is cheaper but darkens direct sunlight too.
2. Keep the radius in world units matched to the scene's scale, and let AO fade out where its radius shrinks below a pixel.
3. Keep thin, moving geometry such as grass and hair out of screen-space AO, which turns splotchy and sparkly there; bake AO along those elements instead.

**Critic checks.** PASS when creases, corners and contacts darken softly, sunlit faces keep their full brightness, and no dark outline rims foreground silhouettes. FAIL signs: a gray film on sunlit walls; dark halos around characters; splotchy or crawling darkness in grass.

**Diagnose.** Gray sunlit walls → AO multiplied onto the final color. Halos → a radius that is too large, or a blur that ignores depth. Darker everywhere after an upgrade past r184 → GTAO became darker and wider in r185; lower its radius and scale.

**API facts** (check the installed version):
- `ao()` (GTAO) writes AO to the red channel. Pass it to `builtinAOContext()` and set that as the scene pass's `contextNode`: it multiplies only indirect light and skips transparent materials (verified on r186).
- `ssgi()` outputs GI plus a separate AO texture, and `builtinGIContext()` applies both, adding GI to irradiance without occluding it twice (verified on r186).
- `vxgi()` needs a real WebGPU backend, suits static geometry (it re-voxelizes only when flagged), and handles moving lights (verified on r186).
- GTAO's `distanceExponent` and `distanceFallOff` have no effect in r186 (verified on r186).

## Temporal AA, upscaling and motion vectors

**Goal.** Stable edges and quiet noise during motion, with no trails behind anything that moves.

**Build.**
1. Write `velocity` into the scene pass's MRT, and turn MSAA off.
2. Resolve with TRAA at full resolution. Or render the scene pass at a reduced scale and resolve with TAAU, which anti-aliases and upscales in one step. Use FSR1 only for a fragment-bound scene whose input is already anti-aliased.
3. Reset history on cuts, teleports, resizes and tier changes.
4. View the velocity buffer during motion: moving objects show their motion, and static surfaces show only the camera's.
5. For vertex-displaced surfaces (wind-bent foliage, waves, displaced terrain, any `positionNode` deformation), check the velocity buffer while they move. If they ghost or smear under temporal AA, supply the previous frame's displaced position; in r186 the velocity node reads it from `positionPrevious`.

**Watch for.** Transparent effects that write no velocity (composite them after the resolve, or accept softness); thin geometry that flickers in and out; UI inside the resolved image.

**Critic checks.** PASS when walkthrough frames show crisp, stable edges, no crawling, and no trails behind moving objects or displaced surfaces. FAIL signs: ghost trails; smeared foliage or water; edges that crawl while the camera pans.

**Diagnose.**
- Trails behind one kind of object → that material writes missing or wrong velocity.
- Smear on waves or foliage → the displacement isn't reflected in the previous position.
- Ghosting right after a cut → history wasn't reset.
- A soft image overall → TAAU input scale set too low.

**API facts** (check the installed version):
- `traa()` and `taau()` read color, depth and the MRT `velocity` output, and both require MSAA off (verified on r186).
- `taau()` expects input rendered below full size with `setResolutionScale()` and resolves it at full size; `fsr1()` is a spatial upscaler meant for anti-aliased, fragment-bound input (verified on r186).
- The official TRAA example views velocity with `.toInspector('Velocity')`; do the same when checking motion vectors (verified on r186).

## Choosing and ordering antialiasing

**Choose.**
- MSAA for geometry edges when no temporal resolve runs. Its cost grows with every MRT attachment, and compatibility-mode WebGPU devices run without it.
- SMAA as the general post AA, on scene-referred color before the output transform.
- FXAA as the cheapest option, on display-referred color after `renderOutput()`.
- TRAA when shimmer and specular sparkle matter most and velocity is in place.
- None of them for shader aliasing (sparkling normal maps, procedural stripes, glints): filter it where it is made ([materials.md](materials.md)). MSAA never touches it, and post AA only blurs it.

**Critic checks.** PASS when silhouette edges and thin features such as wires, rails and leaf edges stay continuous at native size, without stair-steps or broken dashes. FAIL signs: jagged hero edges; thin features breaking into dots.

**API facts** (check the installed version):
- `smaa()` runs before the conversion to sRGB, while `fxaa()` requires sRGB input and so comes after tone mapping and color-space conversion (verified on r186).
- `antialias: true` on `WebGPURenderer` means 4× MSAA unless `samples` says otherwise (verified on r186).

## Screen-space reflections and god rays

**Choose.**
- SSR for glossy floors, wet streets and water near the camera, always on top of environment reflections, because it can't see anything off screen.
- Planar reflections ([water.md](water.md)) when a flat surface must mirror off-screen objects; each costs another scene render.
- God rays only where haze and a strong, partly blocked light motivate them (canopies, windows, murky water), and kept subtle.

**Build.**
1. Feed SSR normals, metalness and roughness from the scene pass's MRT, add its result to the scene color before the temporal resolve, and keep the environment reflection underneath.
2. Pick the SSR mode by surface. The default single ray weights reflections by the metalness input, so it suits metals. For water, wet ground, marble and polished wood, use the stochastic mode with a denoiser, or feed a reflectivity mask in place of metalness. `reflectNonMetals` only stops the single-ray path skipping zero-metalness pixels; it doesn't make them reflect.
3. For god rays, enable shadows on the renderer, the light and the casting objects, blur the result with a bilateral filter, and composite it with a depth-aware blend.

**Watch for.** Reflections that end in a hard line at the screen edge with nothing beneath; speckled noise on rough surfaces with no denoiser; rays streaking through walls whose meshes cast no shadow.

**Critic checks.** PASS when reflections on wet or polished surfaces line up with the objects above them and fade smoothly where screen data runs out, with environment reflection still beneath. FAIL signs: reflections cut off in a hard line; reflections of objects that aren't there; speckled reflections.

**API facts** (check the installed version):
- By default `ssr()` traces one mirror ray and weights it by its metalness input, so non-metal surfaces get no reflection; `stochastic: true` traces GGX rays with Fresnel, so dielectrics reflect, and expects a denoiser (verified on r186).
- SSR results are added to the scene color (since r183), and its environment fallback takes an equirectangular HDR texture with CPU-side data, not a PMREM or the `scene.environment` cube (verified on r186).
- `godrays()` supports point and directional lights only, and needs shadows enabled on the renderer, the light and the casters (verified on r186).

## Bloom

**Goal.** Glow reads as the camera's response to genuinely bright sources, and the brightest glow belongs to the most important one.

**Build.**
1. Rank emitters before touching bloom: give the source that matters most the highest HDR value, and keep ordinary lit surfaces below the threshold. Set exposure first, because the threshold lives in HDR.
2. Choose whole-scene bloom with an HDR threshold, or selective bloom that reads only the scene pass's emissive output.
3. Composite bloom before tone mapping, and keep its radius stable across canvas sizes; check at two sizes.
4. If an older technique swaps materials to isolate emitters, restore every material even when a render throws, or a single error leaves meshes black.

**Watch for.** Bloom that is the only edge of an object; halos that flicker because glints upstream alias (filter them, or resolve TAA first); gray highlights from values clamped before bloom.

**Critic checks.** PASS when the no-post still keeps every form, only emitters and bright glints glow with bloom on, and the strongest glow belongs to the most important source. FAIL signs: a haze over the whole frame; glow as an object's only outline; halos that flicker between frames.

**Diagnose.** Everything glows → threshold too low or exposure too high. Gray highlights → values clamped before bloom. Flickering glow → unstable sparkle upstream.

**Start here** (adjust to the goal): a threshold just above the brightest lit non-emissive surface, measured in the HDR buffer.

**API facts** (check the installed version):
- `bloom()` from `three/addons/tsl/display/BloomNode.js` blooms its whole input; for selective bloom, give it the scene pass's `emissive` MRT output instead of the color (verified on r186).

## Depth of field and motion blur

**Build.** Use depth of field only for hero and cinematic shots where focus guides the eye, and motion blur only for camera moves and fast objects; neither may hide detail the brief needs or touch UI. Drive focus from the camera rig's subject distance ([camera-and-animation.md](camera-and-animation.md)), keep the subject sharp, run both after the temporal resolve and before tone mapping, and give each an off switch.

**Critic checks.** PASS when the focal subject is sharp in every hero still, and blur grows smoothly with depth without halos at the subject's edges. FAIL signs: a soft subject; bright halos around foreground edges; blur over a must-have.

**API facts** (check the installed version):
- `dof()` has had a new implementation and API since r180; follow the official `webgpu_postprocessing_dof` example (verified on r186).
- `motionBlur()` blurs color along the `velocity` output with a bounded number of samples (verified on r186).

## Grading, grain and banding

**Build.**
- Decide the domain first. White balance and exposure shifts are scene-referred and come before tone mapping; a display-referred lookup table comes after the output transform. A table built for one domain is wrong in the other.
- Serve the brief's mood with restraint, and recheck skin, product and brand colors after grading.
- Stop banding in skies, fog and dark gradients with dither or fine grain at display output, and keep the output buffer at half float.
- Use vignette and chromatic aberration sparingly; lens flares belong to [effects.md](effects.md).

**Critic checks.** PASS when skies, fog and dark gradients show no bands or contour steps in any still, and the grade keeps the colors the brief names. FAIL signs: stepped sky bands; posterized fog; skin or brand colors pushed off their hue.

**API facts** (check the installed version):
- `outputBufferType`, renamed from `colorBufferType` in r182, defaults to `HalfFloatType`; `UnsignedByteType` saves bandwidth but bands HDR gradients (verified on r186).
- `lut3D()` applies a 3D lookup table to its input (verified on r186).

## Resolution policies

**Build.**
- The global pixel ratio sets the whole scene's cost ([foundation.md](foundation.md)), and per-pass scale sets one effect's cost; use both on purpose. Run AO, SSR, SSGI, bloom and volumetric passes at half or quarter scale where they hold up, then upsample with depth-aware weights so edges don't halo.
- Keep blur radii and sample spacing in resolution-independent units, so the look survives a change of canvas size.

**Diagnose.** Halos along depth edges → naive upsampling. A look that changes with the window size → radii set in pixels.

## Symptom → cause

| Symptom | Likely cause | First check |
| --- | --- | --- |
| Looks right only with post on | a missing authored system upstream | the no-post still |
| Gray, flat or washed-out frame | tone mapping or display conversion applied twice | one output owner, `outputColorTransform` |
| Brand or skin colors shift hue | ACES where color fidelity matters | try Neutral or AgX |
| FXAA output looks wrong | FXAA ran on scene-referred color | place it after `renderOutput()` |
| Gray sunlit walls | AO multiplied onto the final color | AO through `builtinAOContext()` |
| Dark halos around silhouettes | AO radius too large, or a depth-blind blur | AO debug view |
| Splotchy darkness in grass | screen-space AO on thin moving geometry | exclude it, bake AO along blades |
| Ghost trails behind moving things | missing velocity, or history not reset | velocity in the Inspector |
| Smeared waves or foliage under TAA | displacement absent from the previous position | velocity buffer while they move |
| No reflections on water or wet ground | SSR in single-ray mode on non-metals | `stochastic` mode with a denoiser |
| Reflections end in a hard line | SSR without an environment beneath | `scene.environment` |
| Everything glows | bloom threshold too low, or exposure too high | HDR values of lit surfaces |
| Flickering bloom halos | aliased glints upstream | specular filtering, TRAA first |
| Banded sky or fog | 8-bit output or no dither | `outputBufferType`, dither |
