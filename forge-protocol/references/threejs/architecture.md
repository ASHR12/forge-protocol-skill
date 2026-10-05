# Three.js architecture: buildings, interiors and cities

API facts verified on r186 (2026-10-05). Check the installed version first; if it differs, confirm in the official docs or the installed source. The installed version wins.

Read this for buildings, interiors and city blocks, together with [geometry.md](geometry.md) for mesh craft and checks.

## Contents

- Plan before triangles
- Massing and skyline
- Façades on exposed edges
- Modules and detail
- Real dimensions and texture scale
- Interiors
- Streets, blocks and cities
- Symptom → cause

## Plan before triangles

**Goal.** A generated building reads as designed when its decisions (the masses, which walls face out, what goes on each wall) exist as data you can inspect before any mesh is emitted.

**Build.**
1. Fix the dimensional anchors: floor heights per tier, a nominal bay width, plinth and parapet heights. On a slope, take the ground line from the terrain's shared height and let the plinth step with it, so no corner floats or sinks ([terrain.md](terrain.md), Collision and height parity).
2. Generate masses as tiers with roles (base, body, crown, bridge), sized in whole bays and floors.
3. Find the exposed wall intervals of every mass (next sections).
4. Place modules on those intervals as plain records: which module, where, at what size.
5. Check the plan, then compile it: every module builder writes into shared buffers grouped by material slot.

**Watch for.** Emitting triangles while still deciding the design leaves nothing to inspect or test. Fail loudly when a placement names a module with no builder, or when two placements claim the same patch of wall. An exact-duplicate test misses partial overlaps, so compare the placement rectangles themselves.

**Critic checks.** PASS when the clay view (one flat material) still shows a deliberate building: a legible base, body and top, a regular rhythm, clear entrances. FAIL signs: a box with windows scattered over it, rhythm that breaks between floors, no readable entrance.

## Massing and skyline

**Goal.** The silhouette identifies the building from far away: its proportions, setbacks, roof line, and how the masses stack.

**Choose.** A single block, a podium with a tower, a ring around a court, an L, T or U footprint, or paired towers joined by a bridge. In a city, let district rules choose among them.

**Build.** Size tiers in whole bays so façades divide cleanly, keep every upper tier wide enough to carry a full façade rhythm, and give the top its own treatment: a setback, parapet, crown, roof form or rooftop equipment.

**Watch for.** Upper tiers shrinking into slivers, every tier the same height, and flat roofs with nothing on them.

**Critic checks.** PASS when the silhouette-only view shows a distinct base, body and top, and neighboring buildings differ in height and roof line. FAIL signs: extruded footprints with flat tops, slivers on top, a skyline of equal heights.

## Façades on exposed edges

**Goal.** Façades exist only where a wall faces out, and their rhythm comes from real bays that turn corners on purpose.

**Build.**
1. For each side of each footprint piece, start from the full wall interval and subtract the spans where another piece touches it; what remains is exposed. Use interval subtraction, never a test at the wall's midpoint.
2. Divide each exposed interval into a whole number of bays, adjusting the bay width slightly rather than leaving a thin remainder.
3. Reserve zones before filling bays: entrances and lobbies, cores and service bands, corner piers, loading docks at the back.
4. Fill the remaining bays from a rhythm (every third bay wider, pilasters every two), keeping vertical structure, horizontal bands (floor lines, sills, lintels) and window infill as separate layers.
5. Give the façade depth: recessed windows with reveals, projecting entrances and cornices. Flat rectangles on one plane read as wallpaper.
6. Generate trim per exposed edge, so cornices and bands wrap compound corners.

**Watch for.** Façade modules on walls hidden inside the mass where wings touch; half-bays at corners; windows filling a reserved zone; cornices that stop short at an inside corner. Courtyard walls do face out and need their own façades.

**Critic checks.** PASS when every visible wall carries a façade whose bays align floor to floor and resolve at the corners, windows show recessed reveals under raking light, and the ground floor makes its entrances obvious. FAIL signs: windows painted flat on the wall, thin leftover bays at corners, façade parts poking out of walls that should be hidden, trim ending in mid-air.

## Modules and detail

**Goal.** Detail modules are authored once in their own space and placed many times, and ornament arrives only after the mass and rhythm work.

**Build.**
- Author each module (window bay, door, pier, cornice run, balcony) in a local frame with a declared width, height, depth and anchor points. The compiler, not the module, handles orientation and winding for each side.
- Let the mass compiler close the structure: soffits under overhangs and setbacks, decks on terraces, roofs, and connectors between touching masses. No gap in the mass may depend on a window module happening to cover it.
- Add ornament (carving, medallions, finials) once the rhythm reads in clay, seated on the surfaces it decorates.

**Watch for.** Modules that work out their own global placement disagree about normals. Ornament never fixes a weak mass.

**Critic checks.** PASS when the undersides of overhangs and setbacks are closed, and ornament sits on its host with a contact shadow. FAIL signs: sky showing through gaps at setbacks, floating cornices or finials.

## Real dimensions and texture scale

**Goal.** Buildings read at the right size because their parts have real dimensions and their materials keep a real texture scale on every wall.

**Build.**
- Take floor heights, door and window sizes, sill heights, stair risers and trim depths from the building's type and era.
- Map wall UVs in meters, so a brick course or stone block has the same real size on every wall, and subdivide very large faces so one texture tile never stretches up a tower.
- Pad atlas tiles so mipmaps don't bleed between neighbors, and vary the tile choice per module to avoid visible repeats.

**Critic checks.** PASS when doors, windows, railings and steps look right next to people and vehicles, and bricks or stone blocks keep one size on every wall. FAIL signs: giant bricks, stone stretched up a whole wall, doors sized for giants.

**Start here** (adjust to the goal, the building type and the era): floor-to-floor near 3 m for housing and near 4 m for offices.

## Interiors

**Goal.** A room reads as real when its shell has depth, its scale fits people, its light comes from sources you can see, and its contents say what the room is for.

**Build.**
- Walls with real thickness, so door and window jambs show it; floors, ceilings, baseboards and trim that close every join.
- Windows that frame a real outside (an environment, a skyline, a garden), never a blank.
- Furniture at human scale with walkways between pieces, and clutter that shows use, such as a mug beside the keyboard or books in uneven stacks, rather than random scatter.
- Light from motivated sources: daylight through the openings (sun plus sky fill entering at the window), practical lights where lamps and screens are, and bounce so corners keep detail. Use baked light maps for static rooms, light probes, or soft fills placed where bounce would come from ([lighting-and-shadows.md](lighting-and-shadows.md)).
- Contact darkening where furniture meets the floor and where walls meet each other.
- For architectural shots inside, keep verticals vertical and use very wide lenses only when the room itself is the subject ([camera-and-animation.md](camera-and-animation.md)).

**Watch for.** A room lit only by ambient light looks flat. A lamp that glows without lighting anything reads as a sticker. Walls built as single planes leak light at the corners.

**Critic checks.** PASS when every visible lighting effect has a visible source, corners and contacts show soft darkening, and counters, chairs and doors read at human scale. FAIL signs: flat ambient lighting, glowing lamps that light nothing, bright seams at wall corners, floating furniture, a blank void outside the window.

**API facts** (check the installed version):
- `RectAreaLight` casts no shadows, lights only PBR materials, and needs `RectAreaLightUniformsLib.init()` on the WebGL renderer or `RectAreaLightNode.setLTC(RectAreaLightTexturesLib.init())` on the WebGPU renderer (verified on r186).
- Since r151, light maps and AO maps read the UV set chosen by `texture.channel` (default 0); set `channel` to 1 when the bake used a second UV set (verified on r186).

## Streets, blocks and cities

**Goal.** A city reads as real when its streets have a hierarchy, its buildings vary at several scales, and the camera's eye level is full of detail.

**Build.**
1. Lay out the street network first (arterials, streets, alleys); it sets the block and parcel sizes.
2. Fill parcels with the building generator under district rules (height range, style, age, density), so variation comes at three scales: the district, the building and the module.
3. Dress the ground where the camera goes: curbs, sidewalks, crossings, street furniture, signs, trees, parked cars and people.
4. Draw efficiently: instance repeated props and modules, batch varied modules that share a material, and replace far buildings with simplified masses or impostors that keep their silhouette and window-light pattern ([assets-and-performance.md](assets-and-performance.md)).
5. At night, light windows from a seeded pattern per building rather than all at once.

**Watch for.** Rows of identical buildings, equal heights, empty sidewalks, far buildings as flat cards with no light variation, and one draw call per unique mesh.

**Critic checks.** PASS when no two adjacent buildings are copies, street widths step down from avenue to alley, the skyline keeps its height variety, and eye-level frames show curbs, furniture and life. FAIL signs: copy-paste rows, a flat skyline, bare ground at camera height, cardboard buildings in the distance.

**API facts** (check the installed version):
- Since r166, `BatchedMesh.addGeometry()` only stores a geometry and returns its id, `addInstance(geometryId)` draws that geometry again without copying it, and `setMatrixAt()` takes the instance id (verified on r186).
- After moving instances with `setMatrixAt()`, call `computeBoundingSphere()` on the `InstancedMesh`; culling keeps the sphere computed at the first render, so moved instances can vanish near the screen edge (verified on r186).

## Symptom → cause

| Symptom | Likely cause | First check |
| --- | --- | --- |
| Façade parts on walls hidden inside the mass | touching pieces not subtracted from each side's interval | the exposed intervals drawn over the plan |
| Upper tiers turn into slivers | no minimum span per tier | each tier's span against one full façade rhythm |
| Windows collide with entrances or cores | reserved zones filled again by ordinary bays | the reserved zones drawn on the façade plan |
| Cornices stop at inside corners | trim built for the whole tier rather than for each exposed edge | the trim runs listed per exposed edge |
| Thin leftover bay at a corner | a fixed bay width leaving a remainder | bay count and width per interval |
| Sky visible under setbacks | closure left to façade modules instead of the mass compiler | a view from below the setback |
| Windows look painted on | the whole façade on one plane; no reveals or projections | a grazing view of the façade under raking light |
| Stone or brick stretched across a wall | UVs not in meters, or large faces not subdivided | a UV checker in meters on the tallest wall |
| Ornament floats off the wall | module anchors not tied to the host surface | the anchor points against the host surface |
| Broken or overlapping bays on some seeds | randomness patching invalid layouts, or only exact duplicates checked | the placement-rectangle overlap test across a sweep of seeds |
| Pieces missing with no error | module builders not checked before compiling | the plan's module names against the registered builders |
| Interior looks flat and gray | ambient-only light; no motivated sources or bounce | the room lit by each source alone |
| Light leaks at room corners | single-plane walls with open joins | wall thickness at the corner in wireframe |
| City reads as copy-paste | one building repeated without district or module variation | an overhead view colored by building variant |
| Instanced props vanish near the screen edge | stale instance bounding sphere after moving instances | `computeBoundingSphere()` after `setMatrixAt()` |
