# Unity materials and shaders: URP Lit, map packing, Shader Graph, toon lighting, anti-tiling, decals, special surfaces and variants

API facts verified on Unity 6.6 (6000.6.4f1, 2026-10-06). Check the project's Unity version first (ProjectSettings/ProjectVersion.txt); if it differs, confirm in that version's official docs or the installed packages. The installed version wins.

Read when you author surfaces in a URP project: URP Lit and its texture conventions, a choice of shader, Shader Graph work (toon, full-screen, decals, vertex animation), breaking up repetition, glass, skin, hair and other surfaces URP struggles with, and keeping materials and variants under control. Texture import settings are in [assets-and-import.md](assets-and-import.md), terrain layer blending in [terrain-and-nature.md](terrain-and-nature.md), water in [sky-weather-and-water.md](sky-weather-and-water.md), and particle materials in [effects.md](effects.md).

## Contents

- Identity from causes
- URP Lit and its map conventions
- Choosing a URP shader
- Shader Graph: targets, nodes and motion vectors
- Toon and custom lighting
- Breaking up repetition
- Decals
- Surfaces URP can't do well
- Material instances, variants and property blocks
- Keywords and shader variants
- Symptom → cause

## Identity from causes

**Goal.** A viewer can tell what each surface is made of and what it has been through, and every texture channel derives from those two facts rather than from unrelated noise.

**Build.**
1. Describe each material in one line: what it is (pine, steel, granite), how it's finished (waxed, enameled, brushed, varnished) and what happened to it (scuffing, dirt, sun bleaching, moisture).
2. Set the response from that line: a smoothness range rather than a single value; metallic at 0 or 1, and in between only where rust, dirt or paint covers metal; clear coat (Complex Lit) for lacquer, car paint and varnish.
3. Let the history drive variation: rubbed edges get smoother and reveal what's underneath, dirt collects in hollows as darker, rougher patches, and wet areas turn darker and smoother.
4. Weather and growth are history too: wetness darkens albedo and raises smoothness together, while snow and moss gather on upward-facing and sheltered faces, masked by the world-space normal and driven by the shared weather state ([sky-weather-and-water.md](sky-weather-and-water.md), Rain, snow and wet surfaces).
5. In the no-post still, light neighboring materials from a low angle and confirm they look different; if only their color differs, their response still needs authoring.

**Watch for.** A single smoothness value over a whole object, the classic plastic look; metallic hovering around 0.5; base colors darker or brighter than any real material.

**Critic checks.** PASS when, in the no-post still under low-angle light, each material is recognizable: its highlights change across the surface, metal and non-metal look different, and nothing has an even plastic shine. FAIL signs: every surface equally shiny; materials distinguishable only by hue; broad, uniform highlights.

**Start here** (adjust to the goal): non-metal albedo kept inside about 30 to 240 on the 0 to 255 sRGB scale, and metals set to metallic 1 with their color in the base map.

**API facts** (check the installed version):
- Complex Lit adds a clear coat layer over the base material, for car paint or varnished wood, at the cost of lighting both layers; it needs Shader Model 4.5 and falls back to Lit where that's missing (verified on 6000.6).

## URP Lit and its map conventions

**Goal.** Every map loads with the right meaning, lands in the right channel, and holds up at the distances the camera uses.

**Build.**
1. Use the Metallic workflow unless an asset was authored for Specular.
2. Base Map is color (sRGB). Its alpha is opacity for transparent and alpha-clipped materials, or smoothness when Smoothness Source is Albedo Alpha.
3. Pack metallic, occlusion and smoothness into one data texture for URP Lit: red metallic, green occlusion, blue unused, alpha smoothness, imported with sRGB off and assigned to both the Metallic and Occlusion slots. The Smoothness slider multiplies the map.
4. Convert roughness to smoothness, which is 1 minus roughness, when packing maps from glTF, Blender or scan libraries. glTF's metallic-roughness texture (occlusion red, roughness green, metallic blue) and HDRP's Mask Map (blue holds a detail mask) are both laid out differently and must be repacked.
5. Import normal maps as normal maps. Unity expects green-up (OpenGL-style) normals, so flip the green channel of DirectX-style maps ([assets-and-import.md](assets-and-import.md)).
6. Height Map adds parallax (pixel offset only), Detail Inputs add a close-up layer (mask in the alpha channel, detail albedo, detail normal, own tiling), and Emission takes an HDR color.
7. On low tiers, turn off Specular Highlights or Environment Reflections in materials that don't need them, rather than swapping shaders.

**Watch for.** Roughness plugged in as smoothness; a packed map imported as sRGB; a glTF metallic-roughness map dropped into the Metallic slot; baked shadows in scanned albedo.

**Diagnose.**
- Glossy where it should be matte, or the reverse → roughness not inverted, or smoothness read from the wrong alpha.
- Occlusion in odd places or tinted → channels packed in another order.
- Bumps lit from the wrong side → a DirectX-style normal map.

**API facts** (check the installed version):
- URP Lit and Complex Lit read a packed texture as red metallic, green occlusion, blue unused and alpha smoothness, with sRGB off and the texture in both the Metallic and Occlusion slots (verified on 6000.6).
- Smoothness Source is Metallic Alpha by default or Albedo Alpha, and the map is multiplied by the Smoothness value (verified on 6000.6).
- Unity uses Y+ normal maps, the convention also called OpenGL format (verified on 6000.6).
- HDRP's Mask Map stores metallic in red, ambient occlusion in green, a detail mask in blue and smoothness in alpha (verified on 6000.6).

## Choosing a URP shader

**Goal.** Each surface uses the cheapest built-in shader that still gives it the response its identity needs.

**Choose.**
- Lit for most real materials: the full PBR model and the heaviest built-in shader.
- Complex Lit for clear coat.
- Simple Lit when speed matters more than physical correctness: it isn't PBR and Shader Graph doesn't support it.
- Baked Lit for stylized scenes lit only by lightmaps and light probes.
- Unlit for effects, UI-like surfaces and flat styles that take no lighting.
- Particle shaders for effects ([effects.md](effects.md)) and Terrain Lit for terrain ([terrain-and-nature.md](terrain-and-nature.md)).

**Build.** Keep one shader family per art style. When a tier needs cheaper surfaces, cut features within the same shader before switching shaders, because each switch changes the look between tiers.

**API facts** (check the installed version):
- In the Deferred path, URP renders Complex Lit objects with the Forward path (verified on 6000.6).
- Baked Lit takes light from lightmaps and light probes only, Unlit computes no lighting, and Simple Lit uses a lighting approximation without energy conservation (verified on 6000.6).

## Shader Graph: targets, nodes and motion vectors

**Goal.** Custom surfaces keep URP's lighting, batching and motion vectors, and stay maintainable as the project upgrades.

**Choose.**
- A URP Lit graph for custom PBR inputs (procedural masks, triplanar projection, weathering) on top of URP lighting.
- A URP Unlit graph for effects, UI surfaces and custom lighting models.
- Decal and Fullscreen graphs for projected decals and for full-screen passes ([effects.md](effects.md)).
- Hand-written HLSL only where Shader Graph can't reach; Unity recommends Shader Graph because it upgrades more easily.

**Build.**
1. Start from the template browser when creating a graph, and keep exposed properties on the Blackboard.
2. Vertex animation (wind, waves, flags) writes the Position block in the vertex context. Set the graph's Additional Motion Vectors to Time-Based when the motion depends only on the Time node and constant inputs, or to Custom with a motion vector output otherwise, so TAA doesn't smear it ([final-image.md](final-image.md)). Transparent surfaces, most water included, get no motion vectors whatever this setting says.
3. Scene Color needs the URP asset's Opaque Texture and a transparent surface, and works in the fragment stage only; Scene Depth needs the Depth Texture.
4. On large surfaces, compute UV scrolling and tiling in the vertex stage and pass it through custom interpolators.
5. Study the Shader Graph samples (Package Manager > Shader Graph > Samples): Feature Examples covers detail mapping, parallax occlusion, triplanar projection and vertex animation. The samples ship under the Unity Companion License, so record any you import in the ledger ([assets-and-import.md](assets-and-import.md)).

**Watch for.** The Reflection Probe node, deprecated in 6.5; vertex animation without motion vectors; hand-edited copies of generated graph code, which every recompile overwrites.

**API facts** (check the installed version):
- URP writes motion vectors only for opaque and alpha-clipped materials, and Shader Graph's Lit and Unlit targets offer Additional Motion Vectors as None (the default), Time-Based or Custom (verified on 6000.6).
- The Scene Color node samples URP's Opaque Texture, a copy taken before transparents render, and works only in the fragment stage of a transparent graph (verified on 6000.6).
- Without the URP asset's Depth Texture, the Scene Depth node returns 0.5; its Eye mode returns distance from the camera in meters (verified on 6000.6).
- The Shader Graph package, its samples included, is licensed under the Unity Companion License (verified on 6000.6).

## Toon and custom lighting

**Goal.** A single intentional style on every asset, where light bands, shadow tints and line weights all match.

**Build.**
1. Import the Shader Graph Custom Lighting sample and start from its templates: Basic, Simple (Blinn), Toon (posterized bands) and URP (Lit-based).
2. Build custom lighting on the URP target with the Unlit material type, and in Graph Settings turn Keep Lighting Variants on and Default Decal Blending and Default SSAO off.
3. Keep those materials on the Forward or Forward+ path; Shader Graph custom lighting doesn't work with Deferred.
4. Decide the band count, a palette-derived shadow tint (not black) and the line thickness up front, then use them on every asset, including imported ones.
5. Draw outlines with an inverted hull (a second pass through a Render Objects renderer feature with an override material) or with depth and normal edge detection in a Fullscreen graph.
6. Pick tone mapping for the style, often Neutral, or None for flat unlit work ([final-image.md](final-image.md)).

**Critic checks.** PASS when all assets use the same shading and line thickness, shadows take their tint from the palette, and no photoreal object sticks out. FAIL signs: realistic objects beside toon ones; lines that thicken or thin with distance; soft gradients where bands were intended.

**API facts** (check the installed version):
- Shader Graph custom lighting is meant for the Forward and Forward+ paths; with Deferred, lighting runs in a separate pass the object's shader can't control (verified on 6000.6).
- Custom lighting graphs use the URP target with the Unlit material type, Keep Lighting Variants on, and Default Decal Blending and Default SSAO off (verified on 6000.6).

## Breaking up repetition

**Goal.** Big surfaces never reveal a repeating tile grid, whether seen close, from above or from far away, and their variation looks like wear and history, not noise.

**Choose** (stack several):
- Macro variation: a low-frequency world-space field or low-resolution map that shifts hue, value and smoothness by a few percent.
- Detail maps for close views: URP Lit's Detail Inputs, or a Shader Graph detail layer packing normal, occlusion and smoothness.
- The same texture set at two scales, crossfaded by camera distance.
- Hex-tile (stochastic) sampling: a hexagonal grid in which every cell gets its own random offset and rotation, blending three texture samples per pixel. The Shader Graph Terrain Shaders sample shows it for terrain layers; build the same idea as a subgraph for other materials, rotating normal samples back as you rotate their UVs.
- The Triplanar node for rocks and cliffs without good UVs.
- Decals and painted masks for authored breakup where the eye lands (below).
- Terrain layer blending is in [terrain-and-nature.md](terrain-and-nature.md).

**Build.** Start with macro variation and a detail layer, judge them in a high, top-down still of the largest surfaces, and add hex tiling only where a grid still shows, since it triples texture samples.

**Watch for.** Hex or stochastic tiling on textures with a direction, such as wood planks or brick rows, which scrambles their pattern; macro variation strong enough to look blotchy; triplanar mapping in world space on moving objects, where the texture slides.

**Critic checks.** PASS when hero, overhead and distant views of big surfaces show no repeating grid, and their variation looks like patches, wear or growth. FAIL signs: identical tiles in a checkerboard; one stain repeated in rows; blotchy noise laid over everything.

**API facts** (check the installed version):
- The Triplanar node projects in world space by default, samples its texture three times blended by the normal, has a Normal mode for normal maps, and works in the fragment stage only (verified on 6000.6).
- URP Lit's Detail Inputs take a mask from the alpha channel, a detail base map and a detail normal map, with their own tiling, which doesn't apply to the mask (verified on 6000.6).
- The Terrain Shaders sample's hex-tile layers sample each texture three times, and its docs rate them the most effective way to remove tiling (verified on 6000.6).

## Decals

**Goal.** Stains, cracks, paint and marks sit on surfaces where causes put them, without stretching, floating or landing on the wrong objects.

**Build.**
1. Add the Decal renderer feature to the Universal Renderer of each tier that shows decals.
2. Choose its technique. DBuffer blends the chosen surface data (color, normal, and the metallic, occlusion and smoothness set) but needs a depth-normals prepass and doesn't support OpenGL or OpenGL ES. Screen Space draws after opaques with normals rebuilt from depth, suits tile-based GPUs, and is the WebGL 2 choice. Automatic picks by platform.
3. Place each decal with a Decal Projector whose material uses a Decal Shader Graph; set Width, Height and Projection Depth tight, and use Angle Fade so it doesn't smear down steep faces.
4. Fade decals with distance (Draw Distance and Start Fade on the projector, Max Draw Distance on the feature).
5. Keep decals off characters and props with the feature's Use Rendering Layers, at the cost of a depth-normals prepass.
6. URP decals reach opaque surfaces only; on glass or water, use a mesh decal.

**Watch for.** Decals streaking down walls beside a floor decal; decals on moving objects; DBuffer selected on a Web tier.

**Critic checks.** PASS when decals sit flat on the surfaces they mark, follow their relief, and fade with distance rather than popping. FAIL signs: stretched streaks on steep faces; decals floating over gaps; marks on characters walking through them.

**API facts** (check the installed version):
- The Decal renderer feature's technique is Automatic, DBuffer or Screen Space; DBuffer needs the depth-normals prepass, doesn't support OpenGL or OpenGL ES, and doesn't work on particles or terrain details (verified on 6000.6).
- A Decal Projector needs a material with a Decal Shader Graph, and offers Opacity, Draw Distance, Start Fade and Angle Fade (verified on 6000.6).
- URP decals affect opaque objects only (verified on 6000.6).

## Surfaces URP can't do well

**Goal.** Glass, skin, hair, fabric and translucent leaves read correctly through substitutes the plan names, since URP has no transmission, subsurface, hair, fabric or eye models.

**Build.**
- **Glass and clear plastic:** a Transparent Lit material or graph, high smoothness, metallic 0, and Preserve Specular Lighting so highlights survive low alpha. Refract with Scene Color offset by the normal, and weight reflection with a Fresnel term. Transparents cast shadows only through alpha clipping, write no motion vectors, and sort per object, so give glass a Sorting Priority and keep it out of TAA-critical shots.
- **Skin:** custom lighting with wrapped diffuse, a warm tint toward the shadow terminator and a thickness or curvature mask; soft normal detail.
- **Hair:** alpha-clipped cards rendered with Render Face Both, and a shifted, colored highlight in custom lighting; avoid sorted transparency.
- **Fabric:** a sheen-like rim tinted by the fabric color, plus a detail normal for the weave.
- **Translucent leaves:** Render Face Both, a back-lit term in custom lighting, and alpha clipping so the shadows match the leaf shapes ([terrain-and-nature.md](terrain-and-nature.md)).
- When the goal hinges on these surfaces up close, the HDRP route in [foundation.md](foundation.md) is the alternative, with the user's approval.

**Critic checks.** PASS when glass shows the scene behind it bent and reflected with highlights intact, skin looks soft rather than plastic in shadow, and hair and leaves keep clean, stable edges. FAIL signs: glass as a flat tint; gray, waxy skin; hair or leaves with sorting flicker or halos.

**API facts** (check the installed version):
- Transparent URP materials blend as Alpha, Premultiply, Additive or Multiply, and Preserve Specular Lighting keeps highlights even at full transparency (verified on 6000.6).
- Render Face draws Front (the default), Back or Both, and Alpha Clipping discards pixels below its Threshold, 0.5 by default (verified on 6000.6).
- Subsurface scattering, hair, fabric, eye, anisotropy and iridescence lighting models are HDRP-only (verified on 6000.6).

## Material instances, variants and property blocks

**Goal.** Materials stay few and shared, runtime changes don't leak, and batching survives.

**Build.**
1. Share one material per look, never one per object.
2. Build families (color schemes, clean and damaged versions) as Material Variants that inherit from a parent material.
3. At runtime, `Renderer.material` clones the material for that renderer: change it there for one object, and destroy the clone when the object goes. `sharedMaterial` edits the asset for every user, and in the editor the change persists.
4. A MaterialPropertyBlock sets per-renderer values without a new material, but takes that renderer out of the SRP Batcher and the GPU Resident Drawer; keep it to a handful of objects ([performance-and-builds.md](performance-and-builds.md)).
5. Create material assets from editor scripts, not at runtime, so they get stable files and GUIDs ([project-hygiene.md](project-hygiene.md)).

**Watch for.** Memory that climbs as scripts touch `Renderer.material` in a loop; a property block on hundreds of objects; edits through `sharedMaterial` in Play mode that silently change the asset.

**API facts** (check the installed version):
- `Renderer.material` instantiates a copy the first time it's read when the material is shared, and the caller must destroy it (verified on 6000.6).
- A MaterialPropertyBlock on a renderer makes it incompatible with the SRP Batcher, and the GPU Resident Drawer skips renderers that have one (verified on 6000.6).
- A Material Variant inherits the properties of its parent material, much as a prefab variant inherits from its prefab (verified on 6000.6).

## Keywords and shader variants

**Goal.** Builds stay fast and small, nothing renders pink at runtime, and every feature a tier needs survives stripping.

**Build.**
1. Keep keywords few. In Shader Graph, choose each keyword's Definition: Shader Feature (the default) compiles only variants that materials in the build use; Multi Compile keeps every variant, for features toggled at runtime; Dynamic Branch compiles one program that branches at runtime.
2. Toggle a feature at runtime only through Multi Compile or Dynamic Branch keywords. A Shader Feature variant that no material used was stripped, and drawing with it renders pink.
3. Strip what no tier uses: disable the feature in every URP asset and renderer in the build, keep Strip Unused Variants on (Project Settings > Graphics), and don't ship URP assets with different rendering paths, which doubles variant sets.
4. After a build, set a Shader Variant Log Level and read the Shader Stripping section of the log for kept and total counts.
5. Keep BatchRendererGroup variants only for tiers that use the GPU Resident Drawer ([performance-and-builds.md](performance-and-builds.md)); Web tiers strip them.

**Watch for.** A feature enabled in only one URP asset, which forces both variant sets into the build; Web builds whose memory fills with unused variants.

**API facts** (check the installed version):
- Shader Graph keywords are Boolean or Enum, with a Definition of Shader Feature (the default), Multi Compile or Dynamic Branch; a variant stripped at build time renders as a pink error if used (verified on 6000.6).
- URP compiles variants with each feature on and off unless it can strip them, which needs the feature disabled in every URP asset in the build and Strip Unused Variants enabled (verified on 6000.6).
- Setting Shader Variant Log Level to anything but Disabled makes the build log list, per shader, how many variants it kept out of the total, in its Shader Stripping section (verified on 6000.6).

## Symptom → cause

| Symptom | Likely cause | First check |
| --- | --- | --- |
| Everything looks like plastic | one smoothness value, or no reflections nearby | smoothness range; reflection probes ([lighting-and-shadows.md](lighting-and-shadows.md)) |
| Matte surfaces look glossy | roughness used as smoothness | the packed map's alpha |
| Occlusion in odd places | channels packed in another order | red metallic, green occlusion, alpha smoothness |
| Bumps lit from the wrong side | DirectX-style normal map | the green channel |
| Washed-out or muddy color | a map with the wrong sRGB setting | the texture's import settings |
| Pink material at runtime only | a stripped Shader Feature variant | the keyword's Definition |
| Pink everywhere after import | a Built-in shader under URP | the Render Pipeline Converter ([foundation.md](foundation.md)) |
| Smeared foliage or flags under TAA | vertex animation without motion vectors | Additional Motion Vectors |
| Black or gray refraction | Opaque Texture off, or Scene Color on an opaque graph | the URP asset; the graph's Surface Type |
| Visible tile grid | one UV scale and no macro layer | macro variation, hex tiling |
| Decal streaks down walls | no Angle Fade, projection box too deep | the projector's depth and Angle Fade |
| No decals on the Web build | DBuffer on an OpenGL ES-class target | the feature's technique |
| Glass with no shadow or trails under TAA | transparents shadow only by alpha clip and write no motion vectors | the glass plan in this file |
| Draw calls jump after a script change | property blocks or cloned materials | `MaterialPropertyBlock` and `Renderer.material` use |
