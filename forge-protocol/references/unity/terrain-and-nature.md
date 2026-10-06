# Unity terrain and nature: heightmaps, real data, layers, LOD, collision, trees, grass and wind

API facts verified on Unity 6.6 (6000.6.4f1, 2026-10-06). Check the project's Unity version first (ProjectSettings/ProjectVersion.txt); if it differs, confirm in that version's official docs or the installed packages. The installed version wins.

Read when the build needs real ground or growth: open landscapes, real places, forests and meadows, scattered rocks, wind, or any level whose players, plants or water sit on uneven land. Lakes, rivers and seas are in [sky-weather-and-water.md](sky-weather-and-water.md); general anti-tiling and material maps are in [materials-and-shaders.md](materials-and-shaders.md); blockouts, modular kits and splines are in [levels-and-geometry.md](levels-and-geometry.md).

## Contents

- Terrain or mesh ground
- Sculpting and Terrain Tools
- Heightmaps and the height API
- Real elevation data and licenses
- Terrain layers and holes
- Terrain LOD and distances
- Collision and height parity
- Trees
- Details and grass
- Wind
- Scatter outside the terrain
- Terrain on the Web
- Symptom → cause

## Terrain or mesh ground

**Goal.** The ground uses the representation that owns the view, at true scale, with its extents settled before any height is written.

**Choose.**
- **Unity Terrain** (a heightmap tile with its own layers, LOD, collider, trees and details) for open ground, from a few hundred meters to many kilometers, that people walk or drive across.
- **Meshes** (from Blender, ProBuilder or code) for small sets, overhangs, caves, arches, floating islands, planets and faceted low-poly looks. A heightmap stores one height per point, so it can't fold over itself.
- **Both:** Terrain for the open land, meshes for cliffs and cave mouths sunk into it, and holes cut where a mesh replaces the ground (see Terrain layers and holes).

**Build.**
1. Work in meters with +Y up, and leave heights unexaggerated unless the brief wants a dramatic look.
2. Settle the reach before sculpting: the area the camera can visit, the distance it can see from its highest vantage, and what closes the view beyond the detailed tiles (more tiles, cheap distant tiles, ranges painted into the skybox, or fog).
3. Size each tile in meters with Terrain Width, Length and Height, then pick the heightmap resolution from the sample spacing the closest view needs, and keep a known-size object (a person, a door) in every test view.

**Watch for.** Terrain Height is the span from the tile's base to its highest possible point, not an altitude, and heights can't go below the base; to dig below the world's zero, lower the tile, or raise the whole surface first and carve down. Resizing a tile later stretches everything already on it. Past a few kilometers from the origin, float precision shows as jitter ([performance-and-builds.md](performance-and-builds.md)).

**Critic checks.** PASS when the figures, trees and buildings in each still match the size the landforms suggest, and distant land is paler and flatter in contrast than the foreground. FAIL signs: ranges that look like a tabletop model; the end of the terrain or empty space on the horizon; hills that read as small mounds.

**Start here** (adjust to the goal): one tile about a kilometer on a side, with the camera near the ground; spend the budget on layers and scatter before adding tiles.

**API facts** (check the installed version):
- Terrain Width and Length accept 1 to 100,000 world units and Terrain Height 1 to 10,000, with no negative values (verified on 6000.6).
- A build that creates terrain only at runtime still needs one Terrain component in a scene listed in the build profile, or Unity leaves the terrain resources out (verified on 6000.6).

## Sculpting and Terrain Tools

**Goal.** Landforms look carved by rock and water over time: large shapes first, ridges and valleys within them, and drainage on top, instead of even noise.

**Choose.**
- **Heights generated in code** from a seed by default. An editor script or a runtime generator writes the heightmap, so an agent can regenerate, diff and capture the same ground every round.
- **The built-in brushes** (Raise or Lower, Set Height, Smooth, Stamp, Paint Holes) for touch-ups a person makes in the Editor, or heights from an external landscape tool imported as RAW.
- **The Terrain Tools package** when a person sculpts: erosion (hydraulic, thermal, wind), noise brushes and brush mask filters, plus the Terrain Toolbox, which creates tiles from presets or imported heightmaps, changes settings across many tiles at once, and imports and exports heightmaps and splatmaps. It is editor tooling; none of it ships in the build.

**Build.**
1. Block in the macro form (ranges, valleys, plains, coast) with a low-frequency mask. Add noise per region: warp its input coordinates, use ridged noise for crests, and damp octaves by the slope found so far, so steep flanks stay smooth.
2. Erode: an analytic filter in the generator for streamed or endless ground, or a baked hydraulic pass (in code, or with Terrain Tools) when drainage must connect.
3. Write the result once, save the TerrainData asset and log the seed ([project-hygiene.md](project-hygiene.md) covers marking assets dirty and saving). Publish height, slope, altitude and wetness as the shared ground contract the layer, scatter and water builders read ([router.md](router.md), Contracts builders share).

**Watch for.** Brush strokes can't be rebuilt from a seed; when a person sculpts, commit the TerrainData asset and treat it as source. Detail finer than the heightmap spacing aliases into sparkle; carry it in layer normal maps instead.

**Critic checks.** PASS when the land shows how water drains it (branching gullies, crisp ridgelines, flat valley bottoms, debris fans at the foot of slopes) and no two hills share a shape or size. FAIL signs: evenly spaced lumps; peaks that repeat one height and outline; stepped slopes; faceted shading.

**API facts** (check the installed version):
- Terrain Tools 5.3.3 is the package release for 6000.6, and hydraulic erosion exists only with that package installed (verified on 6000.6).

## Heightmaps and the height API

**Goal.** Heights reach Unity without loss and in the right orientation, and every system reads them from one TerrainData.

**Build.**
1. Pick Heightmap Resolution as a power of two plus one (513, 1025, 2049, 4097). Sample spacing is the tile width divided by the resolution minus one; choose it from the closest view.
2. Import RAW from Terrain Settings, Texture Resolutions, Import Raw: 16-bit depth, the file's byte order, its resolution, the tile size, and Flip Vertically when north lands on the wrong edge. Export Raw writes the same format back.
3. From code, write heights as floats from 0 to 1 (1 is Terrain Height) into a 2D array indexed [y, x]: the first index walks along Z, the second along X. Splatmaps use the same row order.
4. For repeated edits, write with `SetHeightsDelayLOD` and finish with `SyncHeightmap`; plain `SetHeights` rebuilds LOD and vegetation data on every call.
5. Read heights back with `Terrain.SampleHeight`, then add the tile's Y position, because it returns height relative to the terrain.

**Watch for.** Swapped indices mirror the land across its diagonal, which looks plausible until someone compares it with a map. A 16-bit file read with the wrong byte order becomes spiky static. Changing the resolution after sculpting resamples the data and loses detail.

**Critic checks.** PASS when slopes stay smooth under grazing light, with no steps or spikes, and landforms sit where the brief or the data put them. FAIL signs: terraces; needle spikes or static-like noise; a landmark on the wrong side of the map.

**API facts** (check the installed version):
- `TerrainData.SetHeights` takes values from 0 to 1 in an array indexed [y, x] and recomputes LOD and vegetation on each call; `SetHeightsDelayLOD` followed by `SyncHeightmap` defers that work (verified on 6000.6).
- Heightmap Resolution accepts only a power of two plus one, such as 513, and Unity advises storing heightmaps as 16-bit RAW files (verified on 6000.6).
- `Terrain.SampleHeight` takes a world position, returns the height relative to the terrain, and clamps the position to the tile (verified on 6000.6).
- `TerrainData.SetAlphamaps` takes splat weights in a [y, x, layer] array (verified on 6000.6).

## Real elevation data and licenses

**Goal.** A real place looks like itself: heights at true scale, the right kind of surface, sea level where it belongs, no steps, spikes or pits, and its data credited as its license asks.

**Choose.**
- **Bare-earth data** (the ground surface alone) when your own plants, buildings and water will sit on it. **Surface data** (with treetops and roofs) only when the real skyline is the point and nothing is modeled on top; otherwise woods and towns turn into raised slabs.
- **Resolution that suits the view:** roughly 30 m between samples is enough for land seen from the air; scenes at walking height need lidar-based elevation, or generated detail layered over coarser data.
- **SRTM and the reprocessed NASADEM:** public domain in the US, near-global between about 60° N and 56° S at about 30 m; over woods and towns it behaves like surface data.
- **USGS 3DEP:** public domain in the US, bare earth, covering the United States only, downloadable free from USGS.
- **Copernicus DEM (30 m and 90 m editions):** may be used, changed and shared at no cost, as long as the provider's attribution text appears exactly as its license words it, with the variant for modified data; it is surface data.
- **Imagery and tile services** carry their own terms, often with attribution or caching limits; read them before draping imagery or baking tiles into the build.

**Build.**
1. Cut out the site plus a margin, and log the dataset, its resolution, its date and its license in `art/LEDGER.md`. When a license asks for attribution, put it on screen (a credits panel or a corner line) so the captures show it.
2. Outside Unity, reproject into a local metric grid centered on the site, fill voids, clip spikes (they cluster over water, steep slopes and cloud), and flatten known water bodies to their level.
3. Resample to a square of a power of two plus one samples, and save it as 16-bit RAW with a known byte order.
4. Set Terrain Width and Length to the clip's extent in meters and Terrain Height to the elevation range (highest minus lowest), so a vertical meter stays a meter; place the tile at the lowest elevation, so world Y equals elevation. Check the vertical datum before placing sea level.
5. For several tiles, use one resolution and make neighboring edges share identical samples, then connect the tiles (see Terrain LOD and distances).

**Watch for.** The license summaries above are our reading, not legal advice; confirm current terms with each provider, and see [assets-and-import.md](assets-and-import.md) for other assets. At 16 bits, Terrain Height splits into 65,536 steps, so a 4,000 m range steps about 6 cm, fine for most views; at 8 bits it steps about 16 m and terraces. Aerial imagery used as a layer carries baked sun and shadows that fight a moving sun.

**Critic checks.** PASS when rivers and coasts follow the valleys and lowlands the heights imply, hillsides stay smooth under grazing light, the surface has no spikes or pits, and every required attribution is readable. FAIL signs: stepped hillsides; plateaus where forests or towns stand; water running up a slope or a dry gap along the waterline; missing or cropped credits.

## Terrain layers and holes

**Goal.** Ground materials follow the landform with crisp, irregular borders, never repeat visibly from any height, and holes open cleanly where meshes take over.

**Choose.**
- **Four strong layers per tile with height-based blending** in URP's Terrain Lit material: at each pixel the layer with the greater height wins, so sand fills between stones instead of cross-fading. URP's height blending covers four layers; more on a tile fall back to weight blending.
- **A Terrain Lit Shader Graph** (Create > Shader Graph > URP > Terrain Lit Shader Graph) when the look needs rules in the shader: triplanar cliffs, macro variation, distance blending, texture arrays. The Shader Graph terrain samples show common setups.
- **Rule-driven splatmaps** written from code by default, with paint only for authored paths and clearings, multiplied into the rules.

**Build.**
1. Make one Terrain Layer asset per material (diffuse, normal map, mask map), with Tile Size in meters chosen for one ground texel density across layers.
2. Pack mask maps for URP: red metallic, green ambient occlusion, blue height (read by height blending), alpha smoothness.
3. Compute weights per splatmap texel from slope, altitude, curvature, wetness and aspect, warp the borders with noise, normalize so they sum to one, and write them with `SetAlphamaps`.
4. On the material, turn on Enable Height-based Blend and tune Height Transition, the width of the blend band in world units. Break repetition with macro variation and two scales ([materials-and-shaders.md](materials-and-shaders.md)).
5. Holes: paint them, or write them with `SetHoles` at the heightmap resolution minus one. Turn on Terrain Holes in every URP asset the build uses, and hide the stepped rim under rocks or the replacing mesh.

**Watch for.** Without a mask map, URP reads smoothness from the diffuse alpha, so an albedo with an empty alpha channel makes the ground glossy or matte by accident; once a mask map is assigned, that alpha means density instead. Every layer costs texture samples even where it isn't painted: the default Terrain Lit shader samples three textures per layer plus the control map.

**Critic checks.** PASS when steep faces show bare rock, flatter ground carries soil, grass, sand or snow by height and moisture, the edges between them are sharp and uneven, no repeating texture grid appears from above or afar, and geometry covers every hole's rim. FAIL signs: wide, blurry cross-fades; a grid visible from above; smeared cliffs; a jagged hole rim or a see-through gap at a cave mouth.

**Diagnose.**
- Mushy borders → height blending off, more than four layers on the tile, or flat blue channels in the mask maps.
- Holes in the Editor, solid ground in the build → Terrain Holes off in the URP asset.

**API facts** (check the installed version):
- URP's Terrain Lit blends up to four Terrain Layers by height and any number by alpha weight (verified on 6000.6).
- With height-based blending on, URP takes each layer's height from the blue channel of its mask map (verified on 6000.6).
- In URP, terrain holes vanish from builds unless Terrain Holes is enabled in the URP asset (verified on 6000.6).
- `TerrainData.SetHoles` takes a [y, x] array of booleans in which true is ground and false is a hole (verified on 6000.6).

## Terrain LOD and distances

**Goal.** Landforms hold steady while the camera travels: hills don't swell or shrink, no circle marks where texture or grass changes, and tiles meet without gaps.

**Build.**
1. **Pixel Error** trades fidelity for triangles: lower values follow the heightmap more closely and cost more. Set it from a walkthrough, at the lowest value the budget allows, and per quality tier through the Quality settings' Terrain Setting Overrides rather than tile by tile.
2. **Draw Instanced** renders the tile with GPU instancing and takes normals from the heightmap texture; URP's Enable Per-pixel Normal needs it and keeps lighting detailed on coarse LOD.
3. **Base Map Dist.** sets where the full layer blend gives way to a low-resolution composite. Push it past the distance where layer detail stops reading, and give the composite (Base Texture Resolution) enough texels to match the near ground's color.
4. **Detail Distance** and **Tree Distance** cull grass and trees; Max Mesh Trees, Billboard Start and Fade Length apply only to trees that aren't SpeedTree.
5. **Several tiles:** one heightmap resolution, identical edge samples, and connected neighbors (one Grouping ID with Auto Connect on, or `SetNeighbors` from code), so LOD matches across seams.

**Watch for.** Props set on the full-resolution surface can hover above a simplified far level; look at distant slopes in a moving capture. A short Base Map Dist. shows as a ring where the ground's color and sharpness change.

**Critic checks.** PASS when forward-motion frames show hills holding their silhouettes, no band where texture or detail changes, and no cracks or lighting seams between tiles. FAIL signs: slopes that reshape as the camera nears them; a circular band where the ground color shifts; slivers of sky along a tile seam.

**API facts** (check the installed version):
- URP Terrain Lit's Enable Per-pixel Normal works only when the tile's Draw Instanced setting is on (verified on 6000.6).
- The Quality settings carry Terrain Setting Overrides, including a basemap distance applied to every tile (verified on 6000.6).
- `Terrain.SetNeighbors` takes the tiles to the left (−X), top (+Z), right (+X) and bottom (−Z) (verified on 6000.6).

## Collision and height parity

**Goal.** The surface the camera shows is the surface everything stands on: feet, wheels, plants, rocks, water and the camera all meet the drawn ground.

**Build.**
1. The Terrain Collider builds its shape from the TerrainData it references; when code swaps or regenerates the TerrainData, point the collider at the same asset. Painted holes leave the collider automatically.
2. Trees collide only through their prefabs: put a capsule on the trunk, and keep Enable Tree Colliders on (the default) only when gameplay touches trees.
3. Query gameplay heights (spawns, AI, camera clamps) with `SampleHeight` plus the tile's Y, or a raycast against the collider; never with a second height function. Keep any vertex displacement in a Terrain Lit Shader Graph below footing scale (centimeters), because the collider never sees it.
4. Test parity after every height change: sample a grid of points with `SampleHeight` and with a downward raycast, and put the largest difference and the allowed tolerance in the handback.

**Watch for.** A collider left on old TerrainData after regeneration gives invisible hills and ghost holes. After a runtime height edit, raycast at an edited point to confirm the collider sees the change.

**Critic checks.** PASS when every foot, wheel and prop rests on the visible ground in each still and frame, and no view looks up from under the surface. FAIL signs: feet floating above or buried in the ground; wheels sunk into a slope; the camera inside a hill; a character falling through ground that looks solid.

**API facts** (check the installed version):
- The Terrain Collider builds its shape from its Terrain Data field, leaves painted holes out automatically, and has Enable Tree Colliders on by default (verified on 6000.6).

## Trees

**Goal.** Each tree is recognizable as its species from its trunk, branch pattern and crown, looks like itself at every distance, and swaps detail levels invisibly.

**Choose.**
- **SpeedTree assets** (8 or 9; in URP, version 9 uses Shader Graph shaders only), when licensed. They import as prefabs with an LOD Group, billboards and their own wind.
- **Your own prefabs with an LOD Group** (from Blender or generated meshes): the terrain accepts any such prefab as a tree prototype, with no limit on mesh size or material count. Use plain prefab instances instead for hero trees that need scripts or interaction.
- **Never the Tree Editor:** it works only with the Built-in pipeline, and its trees render pink in URP.

**Build.**
1. Make three to five variants per species, each with two or three LOD levels and a last level of crossed cards or an impostor, cross-faded by the LOD Group ([performance-and-builds.md](performance-and-builds.md) covers LOD Groups, Mesh LOD and cross-fade).
2. Place trees from code with rules over the shared ground fields (slope, altitude, wetness, distance to paths and water), a slow cluster field and a seed; `TreeInstance.position` is normalized to the tile.
3. Write them with `SetTreeInstances` with snapping on, so trunks land on the heightmap; vary height, width and rotation per instance, and gather debris at the bases (see Scatter outside the terrain).
4. Light trees from the scene's probes ([lighting-and-shadows.md](lighting-and-shadows.md), Indirect light); the terrain's Bake Light Probes For Trees setting instead bakes an internal probe at each tree, which lights nothing else.
5. Wind: SpeedTree trees move with the wind imported with them, which reacts to changes in wind strength and direction; check in a walkthrough that they follow the scene's Wind Zone. Your own trees need vertex wind in their material that reads the shared wind (see Wind).

**Watch for.** SpeedTree trees often carry three or four materials each, which multiplies draw calls; budget them on the Web. Color Variation tints only shaders that read `_TreeInstanceColor`. Judge trees in place, with ground, sky, haze and neighbors.

**Critic checks.** PASS when trunks widen at the root and narrow upward, branches start at uneven heights and angles, crowns read as volumes with holes of sky, forests mix variants and sizes, and far trees hold their outline and tint through a detail switch. FAIL signs: one tree cloned in rows; flat cards visible edge-on; a pop or color jump at a distance band; pink trees.

**API facts** (check the installed version):
- Tree Editor trees need the Built-in Render Pipeline; under URP, use SpeedTree or any prefab with an LOD Group as a tree prototype (verified on 6000.6).
- `TreeInstance.position` is in the terrain's local space, clamped from 0 to 1 as a fraction of its width, height and length (verified on 6000.6).
- Assigning `TerrainData.treeInstances` doesn't snap trees to the heightmap; `SetTreeInstances` can (verified on 6000.6).
- SpeedTree trees ignore Max Mesh Trees, Tree Distance, Billboard Start and Fade Length, and follow their LOD Group instead (verified on 6000.6).

## Details and grass

**Goal.** Grass shows structure at three sizes (patches, tufts, single blades), roots into the soil, sways with the shared wind, and holds its density and color all the way to the horizon.

**Choose.**
- **Instanced detail meshes** (Add Detail Mesh, with Use GPU Instancing on) by default. Unity recommends this mode; it draws with the prefab's own material and shader, so a Shader Graph can supply color variation and wind. Healthy and Dry Color don't apply in this mode.
- **Grass-mode meshes and grass textures** when the terrain's own grass wind and tint are enough: simple lighting, only the base map is read, and the terrain's Wind Settings for Grass move them.
- **Your own instanced draws** (`Graphics.RenderMeshInstanced` from a placement list) for hero grass the detail system can't express. On WebGL 2, keep placement on the CPU, since there is no compute ([performance-and-builds.md](performance-and-builds.md) covers instancing and the GPU Resident Drawer).

**Build.**
1. Model a clump of a few blades with darker bases baked in, and enable Read/Write in its mesh import settings.
2. Give its material a vertex wind that leaves the root still and moves the tip most, reading the shared wind; instanced details get no terrain wind.
3. Drive density from the ground fields with `SetDetailLayer` (an integer per detail texel), zeroing it on paths, cliffs, water and tree bases; Detail Scatter Mode decides whether the numbers mean coverage or instance counts.
4. Set Align to Ground, Position Jitter, Noise Spread, a fixed Noise Seed, and Hole Edge Padding to keep grass off hole rims.
5. Tint the ground layer under the grass to the grass's average color, and fade blades out over the end of Detail Distance, so the field hands over to the ground with no ring.

**Watch for.** Instanced details get no light probe or lightmap lighting and draw in batches of up to 1,023. Vertex wind smears under temporal anti-aliasing unless the grass graph sets Additional Motion Vectors, Time-Based when the wind comes only from time and constant inputs, Custom otherwise ([materials-and-shaders.md](materials-and-shaders.md)); grass-mode details use the terrain's own shader, which has no such setting, so weigh the AA choice in [final-image.md](final-image.md). An even density everywhere reads as fuzz, not grass.

**Critic checks.** PASS when patches and tufts are obvious at first look, blades darken toward their bases, roots hold still while gusts roll across the field, and distant grass blends into the ground without a visible line. FAIL signs: a uniform carpet; grass standing still while trees sway; a ring where grass ends; grass on paths, cliffs or in water.

**Start here** (adjust to the goal): Detail Resolution Per Patch of 16, the value Unity recommends.

**API facts** (check the installed version):
- With Use GPU Instancing, a detail renders with its prefab's material and shader, without Healthy and Dry Color, in batches of at most 1,023, and without instanced light probe or lightmap lighting (verified on 6000.6).
- Only Grass render mode meshes and grass textures move in the terrain's grass wind; non-instanced details read only the base map (`_MainTex`) (verified on 6000.6).
- A detail mesh needs Read/Write enabled; in 6.6, a Terrain Detail Mesh without it shows an Inspector warning and fails the build (verified on 6000.6).
- `TerrainData.SetDetailLayer` writes a detail density map whose values the Detail Scatter Mode interprets (verified on 6000.6).

## Wind

**Goal.** A single wind drives every moving thing: grass, trees, particles, cloth, flags, clouds and water share its direction and the timing of its gusts, everything stays anchored at the base, and each gust visibly rolls across the land.

**Build.**
1. Own one wind in the app shell, as the shared wind contract in [router.md](router.md) (Contracts builders share): a direction, a speed in meters per second, and a slow gust pattern that travels with it. Publish it to every shader as global values (`Shader.SetGlobalVector`), so materials read the field the scripts use.
2. Drive Unity's three wind inputs from those values: one Directional Wind Zone (Main, Turbulence, Pulse Magnitude, Pulse Frequency) for particles and SpeedTree trees; the terrain's Wind Settings for Grass (Speed, Size, Bending) for grass-mode details; your own material wind for everything else. Add Spherical Wind Zones only for local events, such as an explosion or a rotor's downwash.
3. Particles feel it through their External Forces module ([effects.md](effects.md)); SpeedTree trees through their imported wind, tuned on the importer.
4. Scale every displacement by height along the plant (none at the root, most at the tip), fade it with distance, and stop it before billboards or impostors take over.

**Watch for.** Wind Zones don't move terrain grass, and the terrain's grass wind doesn't move trees, so the two disagree unless one script sets both. A second Directional Wind Zone adds no local variation; it only stacks.

**Critic checks.** PASS when the walkthrough frames show gusts crossing grass and trees in the direction smoke, particles, flags and ripples also take, plant bases stay put, and both a slow sway and a quick flutter are visible. FAIL signs: plants and particles disagreeing on direction; a whole field moving in unison; bases that slide; smeared trails behind swaying leaves.

**Start here** (adjust to the goal): gusts that need two to five seconds to cross the frame, with flutter running about four times the sway's speed.

**API facts** (check the installed version):
- A Wind Zone is Directional or Spherical, with Main, Turbulence, Pulse Magnitude and Pulse Frequency; Spherical zones add to a Directional one (verified on 6000.6).
- Wind Zones move trees and particle systems that use the External Forces module, but not terrain grass (verified on 6000.6).
- A SpeedTree 9 asset's wind is set on the importer's Wind tab: Enable Wind, Strength Response, Direction Response and Randomness (verified on 6000.6).

## Scatter outside the terrain

**Goal.** Rocks, debris, flowers and props on meshes, or on terrain where details won't do, look settled, follow ecology, and stay cheap.

**Choose.**
- **Prefab instances** for anything picked, collided with, scripted or saved: rocks with colliders, props, plants the player touches. Mark the static ones static so batching and occlusion can use them.
- **Instanced draws without GameObjects** (`Graphics.RenderMeshInstanced`) for thousands of non-interactive pieces such as pebbles and petals.

**Build.**
1. Scatter from an editor script with a seed, so the result can be rebuilt: raycast down onto the target colliders (or sample the terrain), reject by slope, footprint and exclusion masks, and save the instances into the scene or a prefab.
2. Spread sizes: a few anchors, mid pieces clustered around them, and many small pieces at contacts, below cliffs and along stream beds.
3. Bury each rock partway, tilt it partly toward the surface normal, and add a darker band of soil and litter where it meets the ground. Vary rotation, non-uniform scale and tint; put moss on upward and shaded faces through the material ([materials-and-shaders.md](materials-and-shaders.md)).

**Critic checks.** PASS when rocks are bedded into the ground with no visible underside, a few large pieces stand among many small ones, no rock repeats within a view, and litter collects at contacts. FAIL signs: rocks perched on top of the ground; twin rocks next to each other; a single size throughout; moss on overhangs.

**Start here** (adjust to the goal): sink rocks by about a quarter of their height.

**API facts** (check the installed version):
- `Graphics.RenderMeshInstanced` draws many copies of a mesh from an instance-data array and a `RenderParams` struct, with no GameObjects involved (verified on 6000.6).

## Terrain on the Web

**Goal.** The Web build keeps the landscape's defining look within WebGL 2's limits: the landform, crisp layer borders, living grass near the camera and a clean horizon.

**Build.**
1. Make a Web quality tier (a Quality level with its own URP asset) with a higher Pixel Error, shorter Detail and Tree Distances, a lower Detail Density Scale and a shorter Base Map Dist., set through Terrain Setting Overrides.
2. Stay at four layers per tile, so height blending survives, with smaller compressed layer textures ([assets-and-import.md](assets-and-import.md)). Prefer a few tiles at 1025 or less over many large ones; heightmaps, splatmaps and detail maps all count against Web memory and download size ([performance-and-builds.md](performance-and-builds.md)).
3. Use instanced details with CPU placement. WebGL 2 has no compute shaders, so GPU-driven grass needs WebGPU, which stays opt-in with WebGL 2 as its fallback.
4. Light with baked data only, since the Web supports baked global illumination with non-directional lightmaps and no real-time GI ([lighting-and-shadows.md](lighting-and-shadows.md)); close the view with fog and distant shapes rather than more terrain.
5. Decals on the ground (tracks, scorch marks, puddles) use the Screen Space technique on WebGL 2, where DBuffer decals don't run; DBuffer decals never land on terrain details on any target ([materials-and-shaders.md](materials-and-shaders.md), Decals).

**Critic checks.** PASS when the Web tier still shows the landform, the layer borders and moving grass near the camera, and the build's own frame-time readout meets the brief's Web budget. FAIL signs: bald ground where the desktop tier had grass; a visible ring where grass or texture ends; a readout over budget.

**Start here** (adjust to the goal): halve Detail Distance and detail density on the Web tier before cutting layers or heightmap resolution.

## Symptom → cause

| Symptom | Likely cause | First check |
| --- | --- | --- |
| Ranges look like a tabletop model | tile size or Terrain Height wrong, or nothing of known size and no haze in view | the tile's size and height against the data, and a person-sized figure in the shot |
| Stair-step terraces | 8-bit heights | the RAW depth at import, or the generator's output format |
| Spiky static over the whole tile | 16-bit RAW read with the wrong byte order | Byte Order at import |
| Land mirrored across its diagonal | heights written [x, y] instead of [y, x] | the index order where heights are written |
| A hill or hole players can't feel | the collider references other TerrainData, or the edit never reached it | the collider's Terrain Data field, and a raycast at the edited point |
| Holes in the Editor, solid ground in the build | Terrain Holes off in the URP asset | Terrain Holes in every URP asset the build uses |
| Blurry, wide layer borders | height blending off, more than four layers, or flat mask-map blue channels | the material's height-blend toggle and the tile's layer count |
| Ground glossy or matte for no reason | no mask map, so smoothness comes from the diffuse alpha | each layer's mask map and diffuse alpha |
| Hills breathe as the camera moves | Pixel Error too high | the same walkthrough at a lower Pixel Error |
| A ring where ground color changes | Base Map Dist. too short, or a coarse composite | the base map distance against the view |
| Cracks or seams between tiles | neighbors not connected, or mismatched edge samples | Grouping ID, Auto Connect and the shared edge rows |
| Pink trees | Built-in tree shaders in URP | the tree prefab's shaders |
| Trees pop or float | LOD Group with no cross-fade, or instances written without snapping | the LOD Group's fade mode, and the snap argument to `SetTreeInstances` |
| Grass and trees blow different ways, or grass doesn't move | terrain grass wind and Wind Zone set separately, or instanced details with no material wind | the script that sets both, and the detail material's vertex stage |
| A whole field pulses in lockstep | wind driven by time alone, with no traveling gust pattern | the wind field shown alone as a debug view |
| The build fails on terrain details | a detail mesh without Read/Write | the mesh's import settings and the Inspector warning |
| Grass ghosts under TAA | vertex wind without Additional Motion Vectors, or grass-mode details | the grass graph's Additional Motion Vectors, then the same frames with another AA mode ([final-image.md](final-image.md)) |
| Runtime-generated terrain missing in the build | no Terrain placeholder in any built scene | the build profile's scenes for a Terrain component |
| Feet hover or sink on slopes | gameplay heights from another source than the collider | the parity test between `SampleHeight` and a raycast |
