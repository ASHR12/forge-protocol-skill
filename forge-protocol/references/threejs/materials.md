# Three.js materials

API facts verified on r186 (2026-10-05). Check the installed version first; if it differs, confirm in the official docs or the installed source. The installed version wins.

Read this when you author surfaces: PBR texture sets, procedural fields, anti-tiling, weathering and wetness, relief, or a stylized look. Glass, gems, films, cloth, fur and other special optical models are in [special-materials.md](special-materials.md); blending terrain layers is in [terrain.md](terrain.md).

## Contents

- Identity from causes
- Texture-based PBR
- Breaking up repetition
- Procedural fields and causal masks
- Filtering and shader aliasing
- Weathering, wetness and accumulation
- Relief: normal maps, parallax and displacement
- Stylized and toon materials
- Symptom → cause

## Identity from causes

**Goal.** Each surface reads as what it is and what happened to it, and every channel follows from those two facts instead of from unrelated noise.

**Build.**
1. Write each identity in a line: the base material (oak, cast iron, basalt, glazed tile), its finish (oiled, painted, polished, lacquered) and its history (wear, grime, sun, moisture).
2. Set the identity's response: a roughness range rather than one value; metalness 0 or 1, with values between only where rust, dust or paint sits on metal; clearcoat for lacquer, car paint or a wet film; sheen for soft fabric.
3. Derive variation from the history: worn edges are smoother and show the base color beneath, grime in cavities is darker and rougher, moisture is darker and glossier.
4. Check that neighboring materials separate under grazing light with post off. If two materials differ only in color, their responses aren't authored yet.

**Watch for.** One roughness value across a whole object (the plastic look); metalness around 0.5 everywhere; base colors too dark or too bright for any real material; the same identity drawn with different responses on different assets.

**Critic checks.** PASS when each material reads as itself under grazing light in the no-post still: highlights vary across a surface, metals and non-metals separate, and no surface has one uniform plastic sheen. FAIL signs: everything equally glossy; materials told apart only by color; flat, even highlights across large surfaces.

**Start here** (adjust to the goal): non-metal base colors between roughly 30 and 240 in sRGB values, and metals at metalness 1 with their color carried by the base color.

## Texture-based PBR

**Goal.** Scanned or authored maps that load with the right meaning, at a consistent density, and hold up at the distances the camera uses.

**Choose.**
- Scanned CC0 sets for ground, rock, bark, plaster and brick: the largest realism gain per hour ([assets-and-performance.md](assets-and-performance.md) covers sourcing and compression).
- Maps baked in Blender from high-poly detail for hero props.
- A hybrid for most surfaces: a scanned base with procedural causal layers on top (below).
- Fully procedural only when variation is the point, or no scan fits.

**Build.**
1. Hold one texel-density target across neighboring assets.
2. Give each map its correct color space ([foundation.md](foundation.md)): base color and emissive are color, everything else is data.
3. Use the green-up normal-map convention, often labeled GL on downloads. If bumps light from the wrong side under a moving light, flip the green channel or negate `normalScale.y`.
4. Pack occlusion, roughness and metalness into one texture in the glTF channel order.
5. Add a detail layer for close views: a fine normal and roughness map tiled at a higher rate and faded out with distance.
6. Check every material under two setups, a low grazing sun and an overcast environment, at near, design and far distances.

**Watch for.** Baked shadows in scanned albedo; normal maps compressed in a color format ([assets-and-performance.md](assets-and-performance.md)); a scan's scale that disagrees with its neighbors (pebbles the size of fists).

**Diagnose.**
- Bumps lit from the wrong side → the opposite normal-map convention.
- Muddy or washed-out color → a color map tagged as data, or a data map tagged as color.
- Glossy where it should be matte → roughness read from the wrong channel, or a roughness map tagged sRGB.

**API facts** (check the installed version):
- Roughness is read from the green channel and metalness from the blue channel of their maps, and AO from the red channel, so one packed glTF-style map can serve all three (verified on r186).
- `normalScale` is a `Vector2`; a negative y flips the normal map's green convention (verified on r186).
- `GLTFLoader` tags glTF color textures as sRGB and corrects the normal-map convention itself when a mesh has no tangents (verified on r186).

## Breaking up repetition

**Goal.** Large surfaces show no tile grid from hero, high or far views, and the variation reads as the surface's history rather than as noise.

**Choose** (stack several):
- Macro variation: a low-frequency field or a low-resolution map over the whole surface that shifts hue, value and roughness by a few percent.
- Hex tiling: three samples per pixel on a hexagonal grid, each with a random offset and rotation, blended with weights sharpened to keep contrast. It works on normal maps too, provided the sampled normals are rotated back.
- Two scales of the same set blended by distance: fine near the camera, broad far away.
- Random rotation or offset per tile, only for textures without a grain direction.
- Decals and painted masks for authored breakup (stains, cracks, worn paths) where the eye lands.
- Terrain layer blending (height-based blends, splat maps, triplanar cliffs) is in [terrain.md](terrain.md).

**Watch for.** Hex or stochastic tiling on strongly directional textures such as planks and brick courses, which breaks their structure; macro variation so strong it looks blotchy; normal maps rotated in UV space without rotating their vectors, which lights them from the wrong side.

**Critic checks.** PASS when no repeating pattern or grid shows on large surfaces in hero, high-angle and far views, and the variation reads as patches, wear or growth. FAIL signs: a checkerboard of identical tiles; the same stain repeating in rows; a blotchy noise overlay.

**Diagnose.** A grid at distance → one UV scale and no macro layer. Lighting seams on rotated tiles → normals not rotated with their UVs. Repeats visible only from above → no macro variation at the scale a high camera sees.

**API facts** (check the installed version):
- `MaterialXLoader` (WebGPU only) compiles MaterialX's `hextiledimage` and `hextilednormalmap` nodes, an official hex-tiling path in r186 (verified on r186).
- `triplanarTexture()` blends three projections in local space by default (`positionLocal`, `normalLocal`), so it moves with the object's own transform; pass world-space position and normal nodes for world-locked mapping (verified on r186).

## Procedural fields and causal masks

**Goal.** A procedural surface built from a few named, inspectable fields that every channel shares, never from stacked noise.

**Build.**
1. Choose coordinates by cause: object space for what travels with the object (wear, moss on a movable rock), world space for what belongs to the place (a water line, a snow line, height bands), UV space for authored flow (planks, fabric), and rest positions for deforming meshes.
2. Start with broad form at the scale the viewer reads first, then mid-scale structure, then fine detail.
3. Derive causes from the form: slope from the normal, cavity and curvature from the geometry or a baked map, exposure from facing up or toward the sun, height above a datum, distance to water or edges.
4. Drive color, roughness and relief from the same fields: one wear field lightens, smooths and rounds an edge together.
5. Warp the coordinates, not the results, and keep category masks broad, so no isolated islands appear.
6. Name parameters by what they look like (`crackWidth`, `mossCoverage`, `edgeWearWidth`), never by how they're computed.
7. Make geometry and shading evaluate the same function: if displacement raises a ridge, color and roughness see the same ridge, and CPU-side placement and collision use it too.
8. Give every field a debug view through the debug-mode hook ([foundation.md](foundation.md)).

**Watch for.** "Visual soup", where each channel samples its own noise; world coordinates on object-locked effects, which slide as the object moves; fields finer than the mesh can displace; hashes built from `sin()`, which repeat.

**Critic checks.** PASS when color, roughness and relief changes line up on the same features (worn edges lighter, smoother and rounder together), and procedural patterns hold still on moving objects. FAIL signs: color blotches unrelated to the relief; patterns sliding across a moving object; detail that reads as static noise.

**Diagnose.** Soup → independent noise per channel. Sliding → world coordinates on an object-locked effect. Seams or steps → coordinates that jump, or precision loss far from the origin.

**API facts** (check the installed version):
- TSL ships MaterialX noise functions such as `mx_noise_float`, `mx_fractal_noise_float` and `mx_worley_noise_float` (verified on r186).
- `positionGeometry` is the untransformed vertex position, which suits object-locked fields; `positionLocal` already includes skinning, instancing and displacement, and `positionWorld` is in world space (verified on r186).

## Filtering and shader aliasing

**Goal.** Procedural and normal-mapped detail never sparkles or crawls, near or far.

**Build.**
1. Fade each detail band toward its average value as its pixel footprint shrinks, using screen-space derivatives of its coordinates or the distance, so far surfaces settle to their mean color and roughness instead of noise.
2. Widen roughness where normals vary inside a pixel. Built-in materials do this only for the mesh's own normals, so dense normal maps seen at a distance need extra roughness (for example from the shortened length of normals averaged in lower mips) or a fade.
3. Box-filter analytic patterns (stripes, scanlines, checkers, grilles) by their footprint, fading them to their mean where they get smaller than a pixel.
4. Inside loops and after a discard, sample with an explicit mip level or gradients ([foundation.md](foundation.md)).
5. Pad atlas tiles so mipmaps don't bleed between neighbors.

**Watch for.** Temporal AA used to hide sparkle, which smears it; bloom amplifying sparkle into flicker ([final-image.md](final-image.md)).

**Critic checks.** PASS when hero surfaces and distant ground show no sparkling pixels, crawling patterns or moiré across consecutive walkthrough frames. FAIL signs: glittering normal-mapped metal at a distance; moiré on fabric, grilles or tiles; flickering highlights that bloom.

**API facts** (check the installed version):
- Built-in physical node materials widen roughness by the screen-space change of the geometry normal (`getGeometryRoughness()`), not by normal-map detail (verified on r186).

## Weathering, wetness and accumulation

**Goal.** History appears where physics would put it, changes every channel together, and stays fixed to the object.

**Build.**
- Wetness makes a surface darker and smoother together: porous materials darken most, and normals flatten as water fills the relief. Drive it from the shared weather state ([sky-and-weather.md](sky-and-weather.md)), streak it down vertical faces below edges and fixtures, and let it dry back over time, edges and high points first.
- Puddles themselves are in [water.md](water.md); the ground around them follows the wetness rule above, darkest at the rim.
- Dirt and grime gather in cavities, at the bottoms of walls and in splash zones near the ground, darker and rougher.
- Dust settles on up-facing surfaces, lightening and slightly desaturating them, and dulls their highlights.
- Moss, lichen and snow sit on up-facing and sheltered faces, with a soft falloff. Give them real thickness through displacement or shell geometry where the silhouette shows.
- Rust and corrosion start at edges, scratches and water paths, and turn metal into a rough non-metal.
- Edge wear removes paint or coating along exposed edges found from curvature, revealing the base material.
- Coordinates: object space for anything that must stay on a moving object; world space only for what belongs to the place, such as a water line or snow line.

**Critic checks.** PASS when accumulation sits where it would physically collect (tops for snow and dust, cavities for dirt, edges for wear, below drips for streaks), stays fixed to objects as they move, and wet areas are darker and glossier together. FAIL signs: snow on vertical walls or undersides; grime spread evenly over everything; wet ground that darkens but stays matte; moss that slides across a moving object.

**Diagnose.** Wet but matte → roughness not tied to wetness. Snow on walls → no facing test. Accumulation sliding → world coordinates on a moving object. Everything evenly dirty → grime not driven by cavity or exposure.

## Relief: normal maps, parallax and displacement

**Goal.** Relief keeps its depth at grazing angles, and deep relief changes the silhouette where it should.

**Choose.**
- Normal maps for small relief: pores, grain, scratches. The silhouette doesn't change.
- Parallax occlusion mapping (a custom TSL height march) for medium relief on near-flat surfaces seen close: cobbles, brick, tiles. The silhouette stays flat unless you clip it.
- Displacement (`displacementMap` on a dense mesh, or a `positionNode` offset) where the silhouette must change; the mesh needs density at the detail's scale.
- Modeled geometry for hero relief ([geometry.md](geometry.md)).

**Build.** For parallax occlusion: march the height once per pixel and reuse the hit for every channel; take more steps at grazing angles, within a hard cap; march toward the light for self-shadowing; make cast and received shadows follow the relief, and carve cut-out edges in the shadow pass; give curved surfaces a real geometric silhouette; test front, grazing and edge-on views.

**Watch for.** Relief that swims as the camera moves; flat, ruler-straight edges on deeply carved walls; shadows that ignore the relief; a normal map implying waves or bumps that the displaced geometry doesn't have.

**Critic checks.** PASS when relief keeps its depth and occlusion at grazing angles without swimming, deep relief breaks the silhouette at edges and against the sky, and shadows follow the relief. FAIL signs: stones that slide when the camera moves; bumpy walls with perfectly straight outlines; flat shadows on deep relief.

**API facts** (check the installed version):
- TSL's `parallaxUV()` offsets UVs once along the view direction: cheap parallax, not occlusion mapping (verified on r186).
- Node materials expose `castShadowPositionNode`, `receivedShadowPositionNode` and `maskShadowNode`, so shadows can follow displaced or carved relief (verified on r186).

## Stylized and toon materials

**Goal.** One deliberate style across every asset, with shading bands, shadow colors and outlines that agree.

**Choose.**
- Banded lighting through a toon material with a gradient ramp, or stepped lighting written in TSL.
- Outlines by inverted hull, scaled with distance to keep a constant screen width, or by edge detection on depth and normals in post.
- Flat color with painted or brush-like breakup, rather than scanned photo textures.

**Build.** Fix the number of bands, the shadow color (tinted from the palette, never black) and the outline weight first, then apply them to every asset, including ones from other sources. Choose tone mapping for the style ([final-image.md](final-image.md)); a realistic tone mapper can muddy flat color.

**Critic checks.** PASS when every asset shares one shading style and outline weight, shadow colors follow the palette, and no realistic asset stands out. FAIL signs: realistic and toon assets mixed; outline weight that changes with distance; smooth gradient shading on surfaces meant to be banded.

**API facts** (check the installed version):
- `MeshToonNodeMaterial` (and `MeshToonMaterial` on `WebGLRenderer`) reads its bands from `gradientMap`, which needs `NearestFilter` for both filters and stays `NoColorSpace` data (verified on r186).

## Symptom → cause

| Symptom | Likely cause | First check |
| --- | --- | --- |
| Everything looks like plastic | one roughness value, or no environment light | roughness range; `scene.environment` |
| Materials differ only in color | responses not authored | identity lines per material |
| Bumps lit from the wrong side | opposite normal-map convention | green channel or `normalScale.y` |
| Muddy or washed-out color | wrong color space on a map | map color spaces |
| Visible tile grid | one UV scale, no macro layer | macro variation, hex tiling |
| Same stain repeating in rows | detail baked into a tiling map | move it to a decal or mask |
| Visual soup | independent noise per channel | shared fields |
| Patterns slide on moving objects | world coordinates on an object-locked effect | coordinate choice |
| Sparkle or crawl on hero surfaces | detail finer than a pixel, normals unfiltered | footprint fade, roughness widening |
| Moiré on fabric or grilles | unfiltered periodic pattern | analytic box filter |
| Wet ground that stays matte | roughness not tied to wetness | wetness drives both channels |
| Snow on vertical walls | no facing test | up-facing mask |
| Moss or dirt sliding across a moving object | world-space accumulation | object-space coordinates |
| Relief swims or slides | parallax without occlusion, or too few steps | march steps at grazing angles |
| Flat outlines on deep relief | relief only in shading | displacement or modeled geometry |
| Shadows ignore relief | shadow pass uses the undisplaced surface | shadow position nodes |
| Realistic asset in a toon scene | style not applied to imported assets | one style pass over every asset |
