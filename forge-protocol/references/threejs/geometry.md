# Three.js geometry: crafted, checked meshes

API facts verified on r186 (2026-10-05). Check the installed version first; if it differs, confirm in the official docs or the installed source. The installed version wins.

Read this when a builder makes objects, vehicles, robots or props, in code, in Blender or from licensed models. Buildings also need [architecture.md](architecture.md); surfaces are in [materials.md](materials.md).

## Contents

- Where geometry comes from
- The dimension contract
- Choosing modeling operations
- Edges, bevels and silhouettes
- Joins, openings and thickness
- Normals, smoothing and UVs
- Parts, materials and assembly
- Mesh checks you write yourself
- Turnarounds and inspection views
- Hard-surface assemblies: vehicles, robots, props
- Procedural variation and LOD
- Symptom → cause

## Where geometry comes from

**Goal.** A hero object looks made, not assembled: one coherent form with deliberate parts, whichever tool produced it.

**Choose.**
- Blender, live or headless ([pipelines.md](../pipelines.md)), for sculpted or organic forms, heavy modifier stacks (bevels, subdivision, cleaned booleans), and hero assets where its tools save real effort.
- Code for parametric forms whose dimensions drive the shape, for seeded variants, and for parts that must follow other geometry at runtime: rails, cables, track pieces, trim wrapping a generated building.
- Licensed models when a recognizable everyday object is needed quickly and its license allows the use. Re-pivot and rescale it to the contract, run the same checks, and restyle it so it belongs to the scene's art system.
- Mixing sources is normal. One dimension contract governs all of them, so an imported wheel and a coded chassis read the same axle position.
- Primitives (box, cylinder, sphere) only where the real part has that shape, such as a ball bearing or a straight pipe, or where nobody will see it.

**Critic checks.** PASS when every hero object reads, at its closest captured view, as one designed form with deliberate parts and transitions. FAIL signs: visible box, cylinder or sphere stand-ins; primitives pushed through each other with no designed joint; an imported model whose scale, finish or detail level differs from everything around it.

## The dimension contract

**Goal.** Every number that shapes the object lives in one place, so geometry, placement, motion and checks all agree.

**Build.**
1. Before any vertices, write the contract beside the generator: the unit (meters unless the project says otherwise), the up and forward axes, the origin and ground datum, the overall bounds, and the few profiles that define the silhouette.
2. List the parts and how each relates to its neighbors: what touches what, what holds what up, required clearances, deliberate penetrations such as a bolt through a plate, and the space every moving part sweeps.
3. Record budgets per object: a part count and triangle band, the material slots, and the views that must hold up (closest, design, farthest).
4. Derive mating dimensions from shared datums. A hinge pin and its bracket read one axis; a wheel and its arch read one hub center.

**Watch for.** A part nudged after a visual check ("drop it 2 cm until it touches") means the contract is wrong; fix the datum instead. Two builders computing the same dimension separately will drift apart.

**Critic checks.** PASS when parts that should touch visibly touch, and proportions fit the kind of object (seat height beside a figure, wheel size against the body, doors against people). FAIL signs: hovering parts, gaps at mounts, a chair seat at knee height, wheels sunk into the ground.

**Diagnose.**
- A part floats or sinks → it was placed by eye, not from the shared datum.
- Proportions look toy-like → the bounds were invented instead of taken from real dimensions.

**API facts** (check the installed version):
- `Box3.setFromObject(object, true)` returns the smallest world-axis-aligned box; the default (`false`) can return a looser one. Update world matrices first (verified on r186).

## Choosing modeling operations

**Goal.** Each visible form comes from the operation that owns its shape, so curvature, edge flow and UVs follow the design instead of fighting it.

**Choose.**
- Constant cross-section (trim, moldings, beams, rails): extrude a profile, or sweep it along a path.
- A cross-section that changes along an axis (hulls, bodies, fuselages, bottles): loft through authored sections that share one vertex count and one seam position.
- Round about an axis (wheels, knobs, vases, nozzles): revolve a profile.
- Tubes, cables and handrails: sweep a section along a curve whose frame cannot flip.
- Thin parts with real thickness (casings, shells, sheet metal): paired inner and outer surfaces, or solidify, with the rim closed.
- Holes through a solid (vents, windows, ports): build the opening into the topology with an inner loop and a jamb.
- Rounded blocks and machined edges: bevel. Smooth organic forms: subdivide a low cage.
- Booleans only when no direct construction can make the cut, and clean the result before trusting it.

**Build.** Design in polygons (quads, n-gons, named parts) and triangulate only when emitting buffers. Apply modifiers in one written order: shape operations, then solidify, then subdivision, then bevels, then cleanup and normals. The order changes the result (beveling a thick shell differs from thickening a beveled surface), so record it.

**Watch for.**
- Sections with different vertex counts, or a seam that wanders between sections, twist a loft.
- Curves that overshoot between section values print ripples under grazing light. Interpolate dimension tracks with a monotone, shape-preserving method, and space control points wider than the stations.
- UVs indexed by segment number change density when resolution changes; parameterize them by accumulated length.

**API facts** (check the installed version):
- `LatheGeometry` revolves its points about the Y axis, reading x as the distance from the axis (verified on r186).
- `ExtrudeGeometry` bevels by default (`bevelThickness` 0.2, `bevelSize` 0.1, in scene units); an unset `bevelSize` becomes `bevelThickness` minus 0.1, which goes negative on small parts, so set both or turn bevels off. Extrusion along an `extrudePath` never bevels (verified on r186).
- `TubeGeometry` and path extrusions take frames from `Curve.computeFrenetFrames()`, which rotates a normal between successive tangents from a start normal it picks itself; a profile that must keep a set "up" needs frames you build (verified on r186).

## Edges, bevels and silhouettes

**Goal.** The silhouette carries identity at a distance, and small rounded edges carry finish up close: a thin highlight along each manufactured edge tells the eye a real object was made here.

**Build.**
1. Block the silhouette first and judge it in a silhouette-only view (a flat dark shape on a light ground) from several angles before adding detail.
2. Bevel every visible manufactured edge. Larger parts get larger bevels, so edge sizes follow the part hierarchy instead of one global radius.
3. Use several bevel segments where the camera comes close; a single chamfer is enough farther away.
4. Keep bevel faces in their own smoothing group, so flats stay flat and the curve stays on the edge.

**Watch for.** One global bevel radius flattens the scale hierarchy: a bolt and a body panel end up with the same edge. A bevel narrower than a pixel at the closest view costs triangles and shows nothing. Smoothing across a bevel and its faces makes edges look melted.

**Critic checks.** PASS when, under grazing light in the closest view, every visible manufactured edge of a hero object shows a thin highlight line, and the silhouette-only view is distinctive from each captured angle. FAIL signs: razor-sharp edges, uniformly melted edges, identical edge widths on parts of very different size.

**Start here** (adjust to the goal and the closest camera): make each bevel about two pixels wide at the closest planned view, grow it with part size, and round molded or cast parts more softly than machined ones.

## Joins, openings and thickness

**Goal.** Where parts meet, the viewer can tell how they were made: one continuous surface, one part sitting on another, a gap between panels, or a pin entering a hole.

**Choose.** Give every join one of four states and record it in the contract:
- Continuous: one mesh where the real object is one piece, such as a cast body or a molded shell.
- Proud: an applied part sitting on its host (trim, a badge, a rivet), offset enough never to z-fight at the farthest view.
- Reveal: a deliberate gap or panel line (doors, hatches, covers) wide enough to read at the design view.
- Declared penetration: one part entering another on purpose (a bolt, a post into soil), named so the checks skip it.

Coincident faces from different parts fit none of these states, and they flicker.

**Build.**
- Openings are real holes: an outer loop, an inner loop, and a jamb that shows the wall's depth, with glass or mesh sitting inside the jamb.
- Shells show thickness wherever an edge is visible: offset the surface and close the rim.
- Alpha cut-outs suit only distant or flat detail, such as a far grille or a perforated sheet, never an opening the camera looks into.

**Critic checks.** PASS when, in the closest view, openings show wall depth and see through where they should, panel lines keep one width, rims show thickness, and applied parts sit on their hosts without flicker. FAIL signs: black decals standing in for holes, paper-thin rims, trim floating with light behind it, flicker where two parts meet.

**Start here** (adjust to the goal and the design view): make each reveal at least two pixels wide at the design view, and offset proud parts enough that depth precision at the farthest view still separates them.

## Normals, smoothing and UVs

**Goal.** Curves shade smoothly, flats shade flat, and normal maps read correctly on every copy of a part.

**Build.**
- Smooth by angle, per part: faces meeting at less than the crease angle share normals, and sharper edges split. Caps never share normals with the sides they close.
- Give normal-mapped parts tangents that follow the baker's convention.
- Keep texel density even across parts that sit side by side, scaling UVs by real size rather than by segment count.
- Mirrored parts flip triangle winding and UV handedness. Rebuild the winding after mirroring vertex data, and give mirrored lettering its own UVs or material so it doesn't read backwards.

**Critic checks.** PASS when curved surfaces show continuous highlights, flat panels shade evenly, and grazing light reveals no seams along UV or mirror lines. FAIL signs: faceted curves, blotchy dark patches on flats, a visible line down the middle of a mirrored object, backwards text.

**Diagnose.**
- Dark or see-through faces on one side → mirrored vertex data with the winding left as it was, or an inside-out shell.
- A curve stays faceted despite smooth shading → too few profile segments; raise the resolution before adding subdivision.

**API facts** (check the installed version):
- `computeVertexNormals()` averages every face sharing an indexed vertex, with no crease limit, and gives flat normals on non-indexed geometry; `BufferGeometryUtils.toCreasedNormals(geometry, creaseAngle)` (radians, default π/3, non-indexed result) keeps hard edges (verified on r186).
- `computeTangents()` needs an index plus position, normal and uv; `BufferGeometryUtils.computeMikkTSpaceTangents()` matches common bakers but needs the MikkTSpace module and de-indexes the geometry (verified on r186).
- A negative object scale is handled at draw time, because both renderers flip the front face when the world matrix determinant is negative. Mirroring the buffers with `scale(-1, 1, 1)` or `applyMatrix4()` leaves the triangles inside out until you reverse the index (verified on r186).
- `BufferGeometryUtils.mergeVertices()` welds only vertices whose every attribute matches within the tolerance, so UV seams and split normals stay split (verified on r186).

## Parts, materials and assembly

**Goal.** The assembly stays inspectable while it is built and cheap to draw once it ships.

**Build.**
1. While authoring and checking, keep each semantic part (hull, door-left, hinge-upper) as its own named mesh with its material slot.
2. Run the mesh checks on the named parts.
3. Only then merge by material slot for drawing, and run the checks again, since merging can put overlapping faces inside one mesh.
4. Instance parts that repeat exactly (bolts, rivets, blades, spokes) instead of copying their triangles.
5. Keep the named hierarchy behind a debug switch, so a later defect can be traced to its part.

**Watch for.** Report the part count beside the triangle count. Triangles alone can't reveal an object made of hundreds of loose primitives, and parts alone can't reveal an over-tessellated hero.

**API facts** (check the installed version):
- `BufferGeometryUtils.mergeGeometries()` replaced `mergeBufferGeometries()` in r151, and r186 no longer has the old name. It returns `null` unless every input has the same attributes and all are indexed or none are (verified on r186).
- With `useGroups` true, each input keeps its own group, and a mesh with a material array draws once per group; merge same-material parts without groups to actually cut draw calls (verified on r186).

## Mesh checks you write yourself

**Goal.** Defects that one frame can hide are caught by a small audit the builder writes and proves first, as [capture-and-tools.md](../capture-and-tools.md) asks of every tool.

**Build.** Write a short audit in the project's language. Run it per part before emission, and again on the assembled scene in world space. It reports:
- open edges (used by one face) and non-manifold edges (used by more than two), after welding positions;
- loose or duplicate vertices and zero-area triangles;
- inverted shells: a negative signed volume for any closed component, or a shared edge running the same way in both of its faces;
- overlapping coplanar faces between parts, measured as the real overlap area of same-facing triangles on nearly one plane, never by bounding boxes alone;
- solids passing through each other beyond a small depth, skipping declared penetrations by name;
- unsupported parts: their lowest points tested against the surfaces they are declared to rest on;
- semantic measurements: opening sizes, clearances, seat and handle heights, and the smallest clearance across a moving part's full range, sampled through the motion with the worst pose recorded.

**Watch for.**
- Tolerances scale with the world unit; a millimeter tolerance in a kilometer-scale scene finds nothing.
- Print every measured value beside its allowed range. A bare "pass" hides a result one step from failing.
- Prove each check on planted defects (a deliberate z-fight, a hole, an inverted shell, a buried part) and on a clean case before trusting it.
- Welding or cleaning the whole assembly fuses parts that must stay separate; clean inside each part.
- Passing every check doesn't make the shape right. Your reading of the views decides.

## Turnarounds and inspection views

**Goal.** Fixed views expose what a hero shot hides: the back, the underside, the joins, and how the topology was built.

**Build.** For each hero asset, render a turnaround (the Blender route is in [pipelines.md](../pipelines.md)) with:
- front, back, both sides, top, underside, and two opposite three-quarter views at one distance;
- a silhouette-only view, a clay view (one neutral material) under grazing light, wireframe over clay, a normals view, and a material-slot view with one flat color per slot;
- a view from the height people use it at: seated, standing, or the driver's eye;
- moving parts at both extremes and one pose between them.

Stage the asset on a ground plane with a contact shadow and a human-scale cue. A model floating on black hides contact, scale and edge contrast.

**Critic checks.** PASS when every turnaround view shows finished surfaces with no holes or dark inverted faces, visible undersides are finished, the wireframe concentrates density where curvature and silhouette need it, and moving parts clear each other at both extremes. FAIL signs: missing back faces, unfinished visible undersides, dense flat panels beside faceted curves, parts colliding at an extreme pose.

**API facts** (check the installed version):
- `EdgesGeometry(geometry, thresholdAngle)` keeps only edges whose faces meet above the threshold (degrees, default 1), a cheap crease overlay for clay views (verified on r186).
- A clay pass can set `scene.overrideMaterial`. On the WebGPU renderer the override keeps each material's `positionNode`, displacement map and alpha test, and `allowOverride = false` exempts a material (verified on r186).

## Hard-surface assemblies: vehicles, robots, props

**Goal.** A machine is believable when its big forms are right, its parts visibly hold each other up, and its detail sits where people look.

**Build.**
1. Primary forms: the body, hull or chassis as one or a few continuous lofts with real proportions, judged in silhouette from every side.
2. Secondary forms: panels, intakes, arches, housings and joints, each cut into or seated on the primary with a declared join.
3. Fine detail last (fasteners, seams, vents, lamps, labels), added only after the first two stages read, and densest at the focal areas: cockpit, face, controls, wheels.
4. Plausibility: every part has a visible mount, bracket or hinge; moving parts clear each other through their whole range; wheels meet the ground and flatten slightly under load; robot joints have covers that don't collide at full bend.
5. Graphics: project livery and decals in one shared space, for example a side projection and a top projection blended by surface direction, so stripes continue across panel boundaries.
6. Mirror one authored half, then fix winding and UV handedness on the copy.

**Watch for.** Detail scattered over a weak primary form never rescues it. Fasteners at the wrong scale. Perfect symmetry on an object that has been used. Hidden faces modeled as finely as the hood.

**Critic checks.** PASS when every part has a visible support, wheels or feet meet the ground, moving parts captured at their extremes don't intersect, graphics continue across panel joins, and detail is densest at the focal areas. FAIL signs: floating parts, hovering or buried wheels, mirrored text, even detail density everywhere, a scatter of detail on a lumpy base form.

## Procedural variation and LOD

**Goal.** Variants and lower detail levels come from the same generator, so every seed and every distance shows the same designed object.

**Build.**
- Give parameters valid ranges and dependent constraints (a longer body moves the axle; a taller back raises the armrest), drawn from a seeded generator per object.
- Let randomness choose among valid options; never let it produce invalid geometry that something later patches.
- Run the mesh checks across a sweep of seeds, not only the one you looked at.
- Build lower levels from the generator: fewer profile samples that keep the extremes (a crown, a groove), fewer radial segments, small relief moved into normal maps. Every level keeps the same silhouette, texel density and material slots.

**Watch for.** Generic decimation of a hero mesh erases the narrow features that catch light. Level switches without hysteresis flicker at the boundary. General switching, fades and impostors are in [assets-and-performance.md](assets-and-performance.md); ground LOD and the cracks between terrain tiles are in [terrain.md](terrain.md) (Choosing a terrain LOD, Cracks and seams).

**Critic checks.** PASS when a stress view of other seeds shows variants that all look intentional, and walkthrough frames show no pops or identity changes between levels. FAIL signs: broken or intersecting variants, a level switch that changes silhouette or color.

**API facts** (check the installed version):
- `LOD.addLevel(object, distance, hysteresis)` takes hysteresis as a fraction of the switch distance, which stops flicker at the boundary (verified on r186).

## Symptom → cause

| Symptom | Likely cause | First check |
| --- | --- | --- |
| Hero object looks like a pile of shapes | primitives standing in for designed forms; no declared joins | the silhouette-only view, and the join states in the contract |
| A part floats or sinks | placed by eye instead of from a shared datum | the part's position against the datum it should read |
| Faceted curves | too few profile or radial segments for the closest view | a wireframe at the closest view |
| Hard edges look melted | smoothing across bevels and caps; crease angle too high | a normals view along the edge |
| Dark or see-through faces on one side | winding not reversed after mirroring vertex data, or an inside-out shell | the audit's inverted-shell check |
| Flicker where parts meet | coincident faces from different parts; no proud offset or reveal | the audit's coplanar-overlap check at that join |
| Black patches where holes should be | openings faked with dark planes or decals | a wireframe over clay at the opening |
| Rims look paper-thin | a single surface where an edge is visible; no solidify | a grazing view along the rim |
| Ripples under grazing light | overshooting interpolation of section values, or control points closer than stations | the clay view under grazing light, and the interpolation method |
| A sweep twists or flips | unstable frames along the path, or a duplicated path point | the frame vectors drawn along the path |
| Texture density changes along a part | UVs indexed by segment instead of length | a UV checker on the part |
| Lettering reads backwards on one side | mirrored UVs sharing a lettered texture | a UV checker on the mirrored half |
| A defect appears only after merging | same-slot parts overlapping inside one merged mesh | the audit rerun on the merged mesh |
| Every bevel has the same width | one global radius instead of a part hierarchy | bevel widths against part sizes |
| Detail pops or changes with distance | generic decimation, or LOD without hysteresis | the levels side by side, and the `LOD` hysteresis |
