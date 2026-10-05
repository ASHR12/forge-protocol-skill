# Three.js terrain: height, fields, real data, LOD and texturing

API facts verified on r186 (2026-10-05). Check the installed version first; if it differs, confirm in the official docs or the installed source. The installed version wins.

Read when the scene has ground beyond a small flat floor: landscapes, hills, mountains, real places, or any world where plants, water or players follow the ground. Plants on the terrain are in [nature.md](nature.md); water bodies are in [water.md](water.md).

## Contents

- Scale and extent
- Procedural height and erosion
- Derived fields
- Real elevation data
- Data licenses
- Choosing a terrain LOD
- Cracks and seams
- Layer texturing
- Collision and height parity
- 3D tiles and photoreal tiles
- Symptom → cause

## Scale and extent

**Goal.** Landforms read at their true size: a hill looks like a hill next to a person, distant ranges recede, and the reachable and visible extents are settled before any height is generated.

**Build.**
1. Fix the units (one unit is one meter) and the up axis, and keep vertical exaggeration at 1 unless the brief asks for drama.
2. Decide three extents: where the camera can go, how far it can see from its highest point, and what fills the view beyond the detailed terrain (coarser terrain, distant hills as impostors, mountains in the sky backdrop, or haze).
3. Keep a known-size object in every test view: a person, a door, a tree.
4. Plan precision for large worlds: beyond a few kilometers, render relative to the camera or shift the origin ([assets-and-performance.md](assets-and-performance.md), [space.md](space.md)).

**Watch for.** Noise tuned in bare units with no scale in mind gives mountains a few meters tall or bumps a hundred meters wide. A flying camera sees far more ground than a walking one, which changes the LOD choice.

**Critic checks.** PASS when a person, tree or building in the still agrees in scale with the landforms, and distant terrain is hazier and lower in contrast than near terrain. FAIL signs: miniature-looking mountains; a terrain edge or a void at the horizon; landforms that look like bumps on a tabletop.

**Start here** (adjust to the goal): a walkable area of about a kilometer with the camera near the ground needs no terrain LOD at all; spend the budget on texturing and scatter.

## Procedural height and erosion

**Goal.** The ground looks shaped by geology and water: broad forms first, then ridges and valleys, then drainage, with sharp ridges, smooth valley floors and branching gullies instead of uniform noise bumps.

**Choose.**
- A layered noise stack for the base: domain-warped fractal noise for broad forms, ridged noise for sharp mountain crests, and octaves damped by the slope accumulated so far, which keeps steep flanks smooth the way erosion does and leaves detail on the flats.
- Erosion as a filter when terrain is generated on the fly, streamed or endless: an analytic pass, evaluated per point with no neighbor reads, carves gullies along the steepest descent. It needs the height's analytic gradient, and its gullies never join into a true drainage network.
- Erosion as a simulation when rivers and drainage must connect: bake a hydraulic simulation on a grid, offline or at load. Water flows to lower neighbors, erodes where it runs fast, deposits where it slows, carries sediment and evaporates. Store the result as a height texture.
- Painted or sculpted height (in Blender or an image) when the brief names a specific landform; then add erosion detail and fields on top.

**Build.**
1. Lay out the macro form (where mountains, valleys, plains and coast go) at the largest scale, with a low-frequency mask or a painted map.
2. Add the noise stack per region, warping the input coordinates rather than the results.
3. Erode, by filter or by baked simulation.
4. Expose the height as one function or one texture that every consumer samples: mesh, normals, placement, physics and water.
5. Derive normals from that same height, by central differences or the analytic gradient, at the global data resolution rather than per tile.

**Watch for.** Frequencies finer than the mesh can represent alias into sparkling normals or swimming silhouettes; carry sub-mesh detail in normal and material channels only, and fade it with distance. Plain fractal noise everywhere gives blob terrain in which every hill has the same shape.

**Critic checks.** PASS when landforms show drainage (gullies, sharp ridges, smooth valley floors, fans where slopes meet flats) and hills differ in shape and size. FAIL signs: uniform bumps; every peak the same height and form; terraces from quantized heights; faceted lighting.

**Diagnose.**
- Blob terrain → one noise stack everywhere, with no erosion or ridged layer.
- Stair-steps → heights stored at 8 bits or in a lossy format.
- Faceted lighting → normals taken from coarse triangles instead of the height function.

**API facts** (check the installed version):
- TSL provides `mx_noise_float`, `mx_fractal_noise_float` and `mx_worley_noise_float`, with 2D and 3D variants, as noise building blocks (verified on r186).
- The official `webgpu_tsl_procedural_terrain` example warps noise inside a `positionNode` and builds normals by sampling the same height function at neighboring points (verified on r186).

## Derived fields

**Goal.** One shared set of fields explains the whole landscape. Materials, plants, snow, rivers and paths all read from it, so every system agrees about where things are.

**Build.**
1. From the final height, compute slope (from the normal), curvature (convex ridges against concave hollows), flow accumulation (how much ground drains through a point), wetness (flow, nearness to water, low curvature), altitude above the water level, and aspect (which way a slope faces the sun) when the brief cares about sunny and shaded sides.
2. Bake the costly fields (flow, wetness, an erosion filter's ridge and drainage masks) into textures aligned with the height texture; compute the cheap ones (slope, altitude) where they are used.
3. Publish the set as a contract that the nature, water and sky-and-weather builders read: field names, units, ranges and texture layout. Give each field a debug view.
4. Apply it: rock on steep slopes, soil in hollows, grass on flats, sand and mud near water, snow by altitude and aspect, trees along drainage, paths on gentle grades.

**Watch for.** A field computed per tile without neighbor data breaks at tile borders. Fields derived from a different height than the rendered one disagree with what the camera sees.

**Critic checks.** PASS when material and plant changes follow the landform: rock on steep faces, green in gullies and valleys, snow on high or shaded slopes, unless the brief says otherwise. FAIL signs: materials that ignore slope; snow on cliffs but missing from high flats; forest on bare ridges and none in valleys.

**Diagnose.**
- Materials and plants disagree about where the slope is → they read different heights or fields.
- Lines along tile borders in masks → fields computed per tile.

## Real elevation data

**Goal.** A real place looks like itself: correct heights in meters, the right kind of surface (bare ground, or ground plus canopy and roofs), sea level in the right place, and no stair-steps, spikes or holes.

**Choose.**
- Bare-earth data (a terrain model, ground only) whenever you place vegetation, buildings or water yourself. Surface data (canopy and roofs included) only when you want the real skyline without modeling it, because forests and towns otherwise become lumpy plateaus.
- Tiled web elevation (image tiles that pack height into their color channels) for streaming over a map grid; a single clipped raster for a bounded site.
- Resolution that matches the view: global datasets at about 30 m per sample suit landscapes seen from height, while walking-scale scenes need lidar-derived data or procedural detail added on top.

**Build.**
1. Fetch a clip with a margin around the site, and record the source, resolution, date and license in `art/LEDGER.md`.
2. Decode to float or 16-bit height with the format's documented formula (the common tile encodings pack height across the color channels differently); never read a single 8-bit channel as height.
3. Reproject into a local metric frame centered on the site. If you keep web-map tiles, use their true ground spacing, which shrinks with the cosine of latitude, or high-latitude terrain flattens.
4. Check the vertical datum (ellipsoid, geoid or local mean sea level) before placing sea level; a mismatch moves coastlines.
5. Fill voids and clip spikes, which cluster over water, steep slopes and clouds, then smooth only where the data is noisy. Flatten known water surfaces to their level.
6. Add procedural detail below the data's resolution (micro relief, rocks, normal detail) so close views are not smooth ramps.
7. Texture from fields, or drape imagery. Imagery carries baked lighting and shadows that fight a moving sun, so prefer field-driven materials when the light moves.

**Critic checks.** PASS when coastlines and rivers sit where the terrain predicts, slopes show no stair-steps, and no spikes or holes appear. FAIL signs: terraced hillsides; lumpy plateaus over forests or towns; water climbing a slope or leaving a gap at the shore; needle spikes.

**Diagnose.**
- Terraces → an 8-bit or lossy height decode.
- Lumps over forests and towns → surface data where bare earth was needed.
- Coast in the wrong place → a vertical-datum mismatch.

**API facts** (check the installed version):
- `textureBicubic` applies mipped bicubic filtering to a texture sample; use it when height texels are coarser than the mesh, so bilinear creases don't show in the shading (verified on r186).

## Data licenses

Record every dataset in `art/LEDGER.md`, and when terms require on-screen attribution, make it visible in the captures. Each summary below is our reading; check current terms with the provider before relying on it.
- **SRTM (and its reprocessed NASADEM):** US public domain; covers roughly 60° N to 56° S at about 30 m, and behaves like a surface model over forests and towns. Check current terms.
- **USGS 3DEP:** US public domain, bare earth, United States only, free directly from USGS. Check current terms.
- **Copernicus DEM (30 m and 90 m):** free to use, modify and redistribute, but you must show the provider's exact attribution notice (with the wording its license gives for modified data), copied verbatim. It is a surface model. Check current terms.
- **AWS terrain tiles (Terrarium PNG and other formats):** free, but attribution is required, listing the underlying sources the tile project names. Check current terms.
- **Google photorealistic 3D tiles:** need an API key; you must show the provider's logo and the copyright lines of the visible tiles on screen, and you may not prefetch, store, cache beyond what the response headers allow, extract, or use them offline. Check current terms.
- **Imagery** (satellite and aerial basemaps) has its own terms; check them before draping.

**Critic checks.** PASS when any attribution the data requires is legible on screen in the captures. FAIL signs: missing or cropped attribution; a logo hidden under UI.

## Choosing a terrain LOD

**Goal.** The ground keeps its shape as the camera moves: no breathing hills, no pops, and detail concentrated where the camera is.

**Choose.**
- **A single displaced plane, or a few chunks:** bounded areas up to about a kilometer seen from near the ground.
- **Skirted chunks:** a grid or quadtree of tiles at different resolutions, each with a skirt hanging from its edges. The easiest with tiled data and streaming, cheap and robust, but it needs fades to hide popping.
- **CDLOD:** a quadtree of one reusable grid patch displaced from a height texture, where each vertex morphs toward the coarser level by its true 3D distance to the camera. Best for walkable open worlds on uneven ground: no cracks, no skirts, and predictable heights for placed objects.
- **Geometry clipmaps:** nested rings of regular grids centered on the viewer, updated by wraparound, with a morph band at each ring edge. Constant cost for huge areas and flight. Detail follows horizontal distance only, so a high camera wastes detail directly below it, and placed objects can float or sink where rings morph.
- **Streamed 3D tiles:** see 3D tiles and photoreal tiles.

**Build.**
1. Choose from the camera's height range, the extent and the data source.
2. Morph vertices toward the coarser level over a band before each switch (CDLOD, clipmaps), or cross-fade levels (chunks), with hysteresis so a camera hovering at a boundary doesn't flicker.
3. Compute normals from the global height, never from each tile's own triangles.
4. Keep shadow, physics and placement views of the ground consistent with the morphed surface, or within a stated tolerance.

**Watch for.** Objects placed on full-detail height float above a coarse level drawn beneath them. Keep the terrain fine wherever placed objects are visible, or place them on the height the displayed level actually draws. Terrain displaced or morphed in the vertex stage needs the velocity check: view the velocity buffer, and if the ground ghosts or smears under temporal AA, supply the previous frame's displaced position ([final-image.md](final-image.md), Temporal AA, upscaling and motion vectors).

**Critic checks.** PASS when, in forward-motion walkthrough frames, landforms neither jump nor swim and distant hillsides keep their silhouettes. FAIL signs: hills changing shape as the camera approaches; a visible band where detail changes; trees floating over distant slopes.

**Diagnose.**
- Hills breathe as the camera moves → the morph band is too short, or keyed to the wrong distance.
- Wasted detail under a high camera → clipmap rings ignore camera height.

## Cracks and seams

**Goal.** The terrain is watertight at every LOD boundary and lit continuously across tiles.

**Choose.**
- **Morph to the coarser edge:** the finer level's boundary vertices land exactly on the coarser edge. Preferred when the LOD scheme morphs anyway.
- **Stitching:** edge strips or index patterns that drop every other vertex on the finer side, removing T-junctions.
- **Skirts:** vertical flaps along tile edges, shaded like the neighboring ground; they show as curtains at grazing angles if their normals or textures differ.
- **Zero-area triangles** at clipmap ring boundaries keep the mesh closed.

**Watch for.** Cracks show as sky-colored pinholes or slivers, mostly at grazing angles and along silhouettes. T-junctions can sparkle even when the gap is geometrically closed. Bright or dark lines along tile borders come from normals computed per tile.

**Critic checks.** PASS when no still, including one at a grazing angle, shows cracks, holes, slivers or lit seams between patches. FAIL signs: pinholes of sky along lines; curtains of stretched texture; light or dark lines on a grid.

**Diagnose.**
- Pinholes at tile edges → T-junctions with no morph, stitch or skirt.
- Lines along tile edges → per-tile normals without neighbor samples.

## Layer texturing

**Goal.** Materials follow the landform with crisp, natural borders, show no repetition from any height, and stay sharp at grazing angles without shimmering in the distance.

**Choose.**
- Rule-based layers from the derived fields (slope, altitude, curvature, wetness, aspect) by default, with painted weights on top only for authored areas.
- Height-based blending between layers: compare each layer's height map plus its weight and let the higher one win, for crisp transitions (sand filling the cracks between stones) instead of soft crossfades.
- Triplanar projection only on steep faces, since it costs three samples per layer; top-down projection elsewhere.
- Texture arrays (one binding, many layers) once there are more than a few layers; compressed arrays keep them small.
- Anti-tiling on every large layer (macro variation, hex-tile or stochastic sampling, two scales blended by distance), with details in [materials.md](materials.md).

**Build.**
1. Pick a ground texel density for the design view and hold it across layers.
2. Assign layers by field rules, each with its own roughness and normal, not just its own albedo.
3. Blend by height at borders, and warp the borders with noise so they are irregular.
4. Switch to triplanar above a slope threshold, blending over a narrow band, and sample it in world space so chunks line up.
5. Add a macro variation layer (a low-frequency shift in color and roughness, or a low-resolution color map) that breaks repetition at distance.
6. Toward distance, fade normal detail, blend toward each layer's averaged color, and match the far LOD's color to the near ground. Turn on anisotropic filtering for grazing views; compression, anisotropy and texture memory are in [assets-and-performance.md](assets-and-performance.md).
7. Limit layers per pixel, for example to the strongest two to four weights, because every layer multiplies the samples and triplanar triples them.

**Watch for.** Planar UVs on cliffs stretch into streaks. Scanned albedo with baked shadows contradicts the sun.

**Critic checks.** PASS when rock shows on steep faces, soil or grass on flats, and sand, mud or snow by altitude and wetness, with crisp, irregular borders; no repeating pattern shows in near, design, far or high views; and cliffs show no stretched streaks. FAIL signs: wide, blurry crossfades; a tile grid visible from above; smeared cliffs; ground that shimmers or crawls in the distance.

**Diagnose.**
- Smeared cliffs → planar UVs on steep slopes.
- Obvious repeats → one UV scale, with no macro variation or anti-tiling.
- Far shimmer → no mipmaps or anisotropy, or full-strength normal detail at distance.
- Mushy borders → linear weight blending instead of height-based blending.

**API facts** (check the installed version):
- TSL `triplanarTexture` and `triplanarTextures` project in local space by default (`positionLocal`, `normalLocal`); pass world position and normal for chunked terrain so projections line up across tiles (verified on r186).
- A TSL texture node picks one layer of an array texture with `.depth(layer)`, so a per-pixel layer index from the field rules selects terrain layers from one binding; the `webgpu_textures_2d-array_compressed` example loads a compressed array (verified on r186).
- `MaterialXLoader`, whose materials run only on `WebGPURenderer`, compiles the MaterialX `hextiledimage` and `hextilednormalmap` nodes: an official route to hex-tile sampling (verified on r186).

## Collision and height parity

**Goal.** What you see is what you stand on: players, vehicles, plants, rocks and water all meet the rendered surface.

**Build.**
1. Keep a CPU copy of the same height data or function at physics resolution, and build the physics heightfield from it.
2. Query gameplay heights (spawns, AI, the camera's ground clamp) from that copy, interpolated the same way the GPU samples it.
3. Keep GPU-only detail below the scale that changes footing (centimeters), or add it to both copies.
4. Keep physics on the full-detail height, and keep the terrain fine near anything that touches the ground.
5. Test parity: sample a grid of points on the CPU and on the GPU (or read them back), and print the largest difference next to the allowed tolerance.

**Watch for.** Displacement in a vertex stage is invisible to raycasts and physics, which see only the CPU geometry; GPU-displaced terrain needs that CPU copy to be pickable or walkable.

**Critic checks.** PASS when feet, wheels and props touch the ground in every still and frame, and the camera never dips below the surface. FAIL signs: hovering or sunken feet; wheels inside slopes; the camera clipping into hillsides.

**API facts** (check the installed version):
- The official `physics_rapier_terrain` example builds its physics heightfield, through the `RapierPhysics` add-on's `addHeightfield()`, from the same height array as the terrain mesh (verified on r186).

## 3D tiles and photoreal tiles

**Goal.** Streamed real-world tiles (photogrammetry meshes, or elevation tiles with imagery) deliver a real place without authoring, used with their limits in view: baked lighting, heavy streaming and strict terms.

**Choose.**
- Photoreal tiles when the brief is a real-place showcase and you accept the trade: no relighting (baked sun and shadows clash with a moving sun), heavy network use, the provider's terms, and meshes rather than heightfields for physics.
- Elevation tiles plus imagery or your own field-driven materials when you need dynamic light, your own vegetation, or offline use.

**Build.**
1. Use a community 3D-tiles renderer for three.js, such as the `3d-tiles-renderer` package, which has plugins for Terrarium and Terrain-RGB elevation tiles and for Google's photoreal tiles, and collects attributions. Its compatibility with the WebGPU renderer is unverified: test it on the target backend first, or plan this piece on the WebGL renderer.
2. Route the renderer's attribution output to the screen and keep it in every capture.
3. Budget detail and cache size for the device, and fade tiles in to hide pops.
4. Align the tiles' earth-centered frame to a local frame at the site, so the scene's up axis and units stay local.
5. Never bake or cache photoreal tiles into the build when the terms forbid it.

**Critic checks.** PASS when tiles in the focal area have fully loaded in every capture, attribution is visible, and no seams show between tiles. FAIL signs: blurry half-loaded patches; missing attribution; dynamic shadows that contradict baked ones.

**API facts** (check the installed version):
- three.js's own 3D-tiles example, `webgl_loader_3dtiles`, runs on the WebGL renderer (verified on r186).

## Symptom → cause

| Symptom | Likely cause | First check |
| --- | --- | --- |
| Mountains look miniature | wrong unit scale, or no known-size object and no haze to give depth | a person-sized object in the same view |
| Blob terrain: every hill alike | one noise stack everywhere, with no erosion or ridged layer | the bare height under grazing light |
| Stair-step terraces | 8-bit or lossy heights | the height texture's format and decode |
| Faceted or creased lighting | normals from coarse triangles, or bilinear sampling of a coarse height texture | a normals view |
| Lumpy plateaus over forests and towns | surface-model data where bare earth was needed | the dataset's model type |
| Coastline in the wrong place | vertical-datum mismatch | the datum of the heights and of sea level |
| High-latitude terrain looks flattened | web-map tile spacing not corrected for latitude | the horizontal spacing used for the tiles |
| Materials and plants disagree with the slopes | consumers read different heights or fields | each consumer's height source |
| Lines in masks along tile borders | fields or normals computed per tile without neighbors | a mask view across a tile border |
| Pinholes or slivers between tiles | T-junctions with no morph, stitching or skirt | a wireframe view at an LOD border |
| Curtains visible at tile edges | skirts shaded differently from the ground | the skirts' normals and UVs |
| Hills breathe or pop while moving | morph band too short, missing hysteresis, or chunks without fades | an LOD-level view during forward motion |
| Objects float over distant slopes | placed on full-detail height above a coarse displayed level | displayed and placement heights at the object |
| Ground smears or ghosts under temporal AA | vertex displacement or LOD morphing missing from the motion vectors | the velocity buffer on the terrain |
| Smeared cliffs | planar UVs on steep faces | the triplanar slope threshold |
| Visible tiling from above | one UV scale, no macro variation or anti-tiling | a high, top-down still |
| Ground shimmers in the distance | no mipmaps or anisotropy, or full normal detail at distance | mip settings and anisotropy on ground textures |
| Triplanar seams between chunks | projection in each chunk's local space instead of world space | the position and normal passed to the triplanar node |
| Feet or wheels hover or sink | physics or gameplay height differs from the rendered height | the CPU/GPU parity test |
| Raycasts miss the visible ground | displacement only in the vertex stage, with no CPU height copy | what the raycast actually hits |
| Blurry patches in photoreal tiles | captured before tiles loaded, or detail budget too low | the tile load state when the capture fired |
