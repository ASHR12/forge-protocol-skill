# Unity levels and geometry: grayboxing, scale, modular kits, prefabs, splines, interiors, colliders and lightmap UVs

API facts verified on Unity 6.6 (6000.6.4f1, 2026-10-06). Check the project's Unity version first (ProjectSettings/ProjectVersion.txt); if it differs, confirm in that version's official docs or the installed packages. The installed version wins.

Read when a builder lays out a playable space: blockouts, modular kits on a grid, prefabs as level parts, Blender pieces, roads and rails on splines, interiors and doors, collision, and geometry that bakes cleanly. Prefab override hygiene is in [project-hygiene.md](project-hygiene.md), landscapes in [terrain-and-nature.md](terrain-and-nature.md), motion along splines in [camera-and-animation.md](camera-and-animation.md), lighting the result in [lighting-and-shadows.md](lighting-and-shadows.md), and Blender workers in [../pipelines.md](../pipelines.md).

## Contents

- Grayboxing with ProBuilder or code
- Scale and readability
- Modular kits and snapping
- Prefabs as level parts
- Blender pieces for levels
- Paths, roads and rails with Splines
- Interiors: rooms, doors and occlusion
- Colliders for level geometry
- Lighting-friendly geometry
- Symptom → cause

## Grayboxing with ProBuilder or code

**Goal.** Layout, scale, sightlines and traversal are proven in flat geometry before any art goes in.

**Choose.**
- Code-built blockouts from editor scripts, the agent's main route: a script reads the layout from data and rebuilds the level the same way every time ([agent-control.md](agent-control.md)).
- ProBuilder for shaping by hand or from those scripts: parametric shapes (cube, stairs, arch, door), PolyShape footprints extruded into rooms, face extrusion and insets, and in-scene UV editing. It is maintained and ships among the editor's bundled packages for 6.6.
- Plain primitives for the very first pass.

**Build.**
1. Add ProBuilder through the Package Manager if the project will shape blockouts with it.
2. Lay the level out at true scale around a human-height capsule, with one flat clay-toned material per function (floor, wall, hazard, goal).
3. Walk it in Play mode with the real character controller before any art ([characters-physics-and-feel.md](characters-physics-and-feel.md)), and judge each view in a clay still ([lighting-and-shadows.md](lighting-and-shadows.md)).
4. Keep blockout meshes as collision or as templates for art; ProBuilder exports them as OBJ, STL, PLY, Asset or Prefab for Blender work.
5. On large levels, turn ProBuilder's Auto Lightmap UVs off while editing and build missing lightmap UVs once at the end.

**Watch for.** Hand edits to geometry that a script regenerates, which the next run overwrites; gray blockout pieces left visible in a final build; re-imported exports that need ProBuilderize before ProBuilder can edit them again.

**Critic checks.** PASS when a clay still of each level view shows a readable route, a landmark to steer by, and doors, steps and ledges at human scale. FAIL signs: no visible way forward; doors the character can't fit through; a layout that reads only once textures arrive.

**API facts** (check the installed version):
- ProBuilder 6.1.2 is among the packages bundled with the 6000.6.4f1 editor and requires Unity 6000.0 or later (verified on 6000.6).
- ProBuilder's API builds meshes with `ShapeGenerator.CreateShape`, `GenerateCube` and `GenerateStair`, or `ProBuilderMesh.Create` from positions and faces, extrudes faces and edges, and applies changes with `ToMesh` and `Refresh` (verified on 6000.6).
- ProBuilder exports OBJ, STL, PLY, Asset and Prefab, and an exported mesh needs ProBuilderize before ProBuilder tools work on it again (verified on 6000.6).

## Scale and readability

**Goal.** The level reads at human scale from every camera the game uses, and guides the eye toward where the player should go.

**Build.**
1. Keep one unit as one meter ([assets-and-import.md](assets-and-import.md)), and leave a human-scale reference in every blockout scene until art replaces it.
2. Give every area a landmark visible from its far views, and frame routes with value contrast: lit, open paths against darker walls.
3. Size spaces for the camera as well as the character: third-person cameras need ceiling height and corridor width to orbit ([camera-and-animation.md](camera-and-animation.md)).
4. Check each named view at its near, design and far framings ([validation.md](validation.md)).

**Critic checks.** PASS when doors, steps, railings and props read at believable human scale against each other, and each view shows where to go next. FAIL signs: knee-high doorways; cavernous corridors; a route lost against same-valued walls.

**Start here** (adjust to the goal): a 1.8 m human capsule as the scale reference, and doors about 2.1 m tall.

## Modular kits and snapping

**Goal.** Kit pieces meet exactly, with no gaps, overlaps or flickering faces, on one shared grid.

**Build.**
1. Choose the kit's grid unit, author every piece as a multiple of it, and put every pivot in the same place (a floor corner or the floor's center).
2. Place pieces from scripts by integer grid cells times the unit, never by eyeballed coordinates, so a layout rebuilds identically.
3. When working by hand, use world grid snapping with Global handle orientation, increment snapping, vertex snapping to join piece to piece, and surface snapping to drop props onto colliders.
4. Hide seams with trim pieces rather than overlapping faces.
5. Keep one texel density across kit pieces ([materials-and-shaders.md](materials-and-shaders.md)).

**Watch for.** Coplanar faces from overlapping pieces, which flicker; hairline gaps that leak light; pieces whose pivots differ, which drift off grid when rotated.

**Critic checks.** PASS when walls, floors and trims meet cleanly in near views, with no light leaks or flickering faces. FAIL signs: bright cracks along wall joints; shimmering overlapped faces; a visible step between floor tiles.

**API facts** (check the installed version):
- The Scene view offers world grid snapping (with Global or Grid handle orientation), increment snapping, vertex snapping between meshes, and surface snapping onto colliders with Shift+Ctrl (Shift+Command on macOS) (verified on 6000.6).

## Prefabs as level parts

**Goal.** Every repeated piece is a prefab, so one edit reaches every copy, and differences live in variants rather than copies.

**Build.**
1. Make each kit piece a prefab that carries its mesh, collider, LOD setup and static flags.
2. Make versions (damaged, recolored, alternate trim) as prefab variants, which inherit from the base and override only what differs.
3. Nest pieces inside room or module prefabs; each nested piece still points back to its own prefab asset.
4. Set static flags on the prefab: Contribute GI for baked lighting, Occluder Static and Occludee Static for baked occlusion, Reflection Probe for baked probes. Use Batching Static only where the tier uses static batching ([performance-and-builds.md](performance-and-builds.md)).
5. Keep override hygiene (apply, revert, no stray overrides) as [project-hygiene.md](project-hygiene.md) sets out.

**Watch for.** The Navigation Static flag from old tutorials, which is gone: walkable surfaces come from the AI Navigation components ([characters-physics-and-feel.md](characters-physics-and-feel.md)). Copies of a piece made by duplicating instead of variants, which drift apart.

**API facts** (check the installed version):
- A prefab variant inherits from a base prefab, its overrides take precedence, and a variant can be based on another variant (verified on 6000.6).
- A nested prefab instance stays connected to its own prefab asset even while it is part of another prefab (verified on 6000.6).
- Static Editor Flags include Contribute GI, Occluder Static, Occludee Static, Batching Static and Reflection Probe; Navigation Static and Off Mesh Link Generation are deprecated and can't be set from the menu (verified on 6000.6).

## Blender pieces for levels

**Goal.** Art pieces from Blender drop into the kit's grid and prefabs without per-piece fixes.

**Build.**
1. Export each piece separately from a headless worker, with the kit's pivot convention and grid size ([../pipelines.md](../pipelines.md)), scale and rotation applied, in meters.
2. For detailed pieces, export a simplified collision mesh alongside the visible one, and use it in the prefab's collider.
3. Unwrap lightmap UVs into the second UV set in Blender when baked quality matters, or let Unity generate them on import (below).
4. Import with the settings in [assets-and-import.md](assets-and-import.md), then swap the blockout piece for the art piece in its prefab, so every placement updates at once.

**Watch for.** Pieces exported with a different pivot from the blockout they replace; detailed visual meshes used directly as Mesh Colliders.

## Paths, roads and rails with Splines

**Goal.** Roads, rails, fences and racing lines follow one authored curve that art, gameplay and AI all read.

**Build.**
1. Add the Splines package (bundled with 6.6). A SplineContainer holds one or more splines, built from knots.
2. Choose each knot's tangent mode: Linear for corners, Auto for smooth curves computed from neighbors, Bezier for hand-shaped tangents.
3. Generate road strips, pipes and rails with Spline Extrude (circle, square, road or a profile spline). It replaces any mesh already on the GameObject and rebuilds as the spline changes.
4. Line paths with fences, lamps and trees through Spline Instantiate, by count, spline distance or straight-line distance, with weighted random choices and offsets. Freeze the placed result in the scene before capture rounds if its randomness isn't pinned.
5. Sample positions along the spline in scripts for spawn points, AI lines and camera rails; motion along splines is in [camera-and-animation.md](camera-and-animation.md).
6. Give generated meshes colliders (with Read/Write on) and lightmap UVs if they're baked.

**Watch for.** Extruded roads that z-fight with the terrain beneath ([terrain-and-nature.md](terrain-and-nature.md)); Auto tangents that overshoot at tight corners; instantiated props that change on every regeneration.

**Critic checks.** PASS when roads, rails and fences follow smooth, continuous curves, sit on the ground, and props along them are evenly spaced without overlaps. FAIL signs: kinks or twists in a road; floating or buried road edges; fence posts that collide or leave gaps.

**API facts** (check the installed version):
- The Splines package (2.9.1 with 6.6) supports Unity 2022.3 and later, and its knots use Linear, Auto or Bezier tangent modes (verified on 6000.6).
- Spline Extrude builds Circle, Square, Road or Spline Profile cross-sections and replaces any existing mesh on its GameObject (verified on 6000.6).
- Spline Instantiate places items by Instance Count, Spline Distance or Linear Distance, with per-item probability and position and rotation offsets (verified on 6000.6).
- `SplineContainer.EvaluatePosition(t)` and `Evaluate(...)` return points, and tangents and up vectors, along a spline (verified on 6000.6).

## Interiors: rooms, doors and occlusion

**Goal.** Interiors stay dark where walls block light, reflect their own room, and draw only what can be seen.

**Build.**
1. Give walls real thickness and closed joints; thin walls leak baked light ([lighting-and-shadows.md](lighting-and-shadows.md)).
2. Give each room its own box-projected reflection probe, fitted to the room.
3. For baked occlusion, mark static walls and large static props Occluder Static, everything static Occludee Static, add Occlusion Areas covering where the camera can go, then bake.
4. Put an Occlusion Portal on each door, leave the door itself non-static, and open or close the portal with the door.
5. On Mac tiers with the GPU Resident Drawer, GPU occlusion culling handles this without a bake ([performance-and-builds.md](performance-and-builds.md)).

**Watch for.** Doors marked static, which bake as permanent walls; no Occlusion Areas, so the bake covers everything at once.

**Critic checks.** PASS when no light bleeds through walls or under doors, interior reflections show the room rather than the sky, and nothing pops into view as doors open. FAIL signs: sunlight streaks inside closed rooms; sky in an interior mirror; rooms that appear a moment after a door opens.

**API facts** (check the installed version):
- Occlusion Areas define view volumes where the camera can be; with none, Unity makes one volume around all occluder and occludee geometry, which inflates the data and the bake time (verified on 6000.6).
- An Occlusion Portal occludes while closed and not while open, and its GameObject must not be marked Occluder Static or Occludee Static (verified on 6000.6).

## Colliders for level geometry

**Goal.** Collision matches what the player sees, at the lowest cost that does.

**Choose.**
- Box, sphere and capsule colliders, or compounds of them, for most level pieces and for anything that moves.
- A non-convex Mesh Collider only for static, irregular surfaces such as cave floors, never on a non-kinematic Rigidbody.
- A convex Mesh Collider for moving irregular objects, within its triangle limit.
- A simplified collision mesh for detailed art pieces, rather than the visible mesh.

**Build.**
1. Put colliders on the prefab, and level geometry on its own physics layer ([characters-physics-and-feel.md](characters-physics-and-feel.md)).
2. Turn on Read/Write for every mesh a Mesh Collider uses; in 6.6 the build fails without it.
3. Use the model importer's Generate Colliders only for static scenery.
4. Walk every route with the real character, and check steps, slopes and doorways for snags.

**Watch for.** Invisible walls from oversized colliders; gaps where colliders and visible geometry disagree; detailed Mesh Colliders on props that never needed them.

**Critic checks.** PASS when walkthrough frames show the character standing on visible surfaces, moving through doorways without snagging, and never passing into walls. FAIL signs: feet sinking into floors; the character stopped by nothing; clipping through thin walls.

**API facts** (check the installed version):
- A convex Mesh Collider can use at most 255 triangles; non-convex ones are the most expensive collider type, suit static geometry only, and can't sit on non-kinematic Rigidbodies (verified on 6000.6).
- Compound colliders built from primitives are generally cheaper than one complex Mesh Collider (verified on 6000.6).
- A Mesh Collider's mesh must have Read/Write enabled (verified on 6000.6).

## Lighting-friendly geometry

**Goal.** Level geometry bakes cleanly: no leaks, seams or blotches, and lightmap texels spent where the camera looks.

**Build.**
1. Light most props with Adaptive Probe Volumes, which need no lightmap UVs, and reserve lightmaps for large static architecture ([lighting-and-shadows.md](lighting-and-shadows.md)).
2. Put lightmap UVs in the second UV set: author them in Blender, or turn on Generate Lightmap UVs in the model's import settings.
3. Set each renderer's Receive Global Illumination: Lightmaps for large statics, Light Probes for small props. Use Scale In Lightmap to spend texels on surfaces the camera sees, and 0 to skip lightmapping while still bouncing light.
4. Build closed, thick meshes without interpenetrating walls; back faces seen by probes make dark blotches.
5. Enable Stitch Seams on meshes whose lightmap UVs split across visible edges.
6. Mark only geometry that never moves as Contribute GI.

**Watch for.** Overlapping or cramped lightmap UVs; a whole level at one Scale In Lightmap; moving props marked static.

**Critic checks.** PASS when baked lighting is smooth across surfaces and joints, with no dark blotches, bright seams or leaks along edges. FAIL signs: stair-step seams along UV edges; dark smudges on walls; light bleeding at floor corners.

**API facts** (check the installed version):
- Baked lightmaps read UVs from `Mesh.uv2` (the "UV1" channel), and Generate Lightmap UVs in the model's import settings writes them there (verified on 6000.6).
- A renderer's Receive Global Illumination takes Lightmaps or Light Probes, and a Scale In Lightmap of 0 leaves it out of lightmaps while it still lights other renderers (verified on 6000.6).
- Stitch Seams turns on lightmap seam stitching per renderer (verified on 6000.6).

## Symptom → cause

| Symptom | Likely cause | First check |
| --- | --- | --- |
| Level reads too big or too small | no human-scale reference, or mixed units | the reference capsule; import scale |
| Script-built level differs between runs | unpinned randomness or eyeballed positions | grid-cell placement; seeds |
| Hand edits vanish | a script regenerates that geometry | which pieces the builder script owns |
| Flickering faces at joints | overlapping, coplanar kit pieces | pivots and grid unit |
| Bright cracks along wall joints | gaps between pieces, or thin walls | piece sizes; wall thickness |
| Copies of a piece drift apart | duplicates instead of prefab variants | the prefab and its variants |
| Road kinks or twists | tangent modes at sharp knots | knot tangent modes |
| Props along a path change every rebuild | Spline Instantiate randomness | bake or pin the placement |
| Light leaks into a closed room | thin walls or open joints | wall thickness; APV leak fixes |
| Sky reflected indoors | no room probe, or box projection off | the room's reflection probe |
| A door blocks the view after opening | door marked static, or no portal | the door's static flags; Occlusion Portal |
| Occlusion bake slow or huge | no Occlusion Areas | Occlusion Areas where the camera goes |
| Character snags or sinks | colliders don't match the visible mesh | colliders on the prefab |
| Build fails on a Mesh Collider | Read/Write off on its mesh | the mesh's import settings |
| Dark blotches or seams in baked light | overlapping lightmap UVs, or back faces | UV2 layout; Stitch Seams; mesh closure |
