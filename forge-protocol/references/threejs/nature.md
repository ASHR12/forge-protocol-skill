# Three.js nature: vegetation, rocks and wind

API facts verified on r186 (2026-10-05). Check the installed version first; if it differs, confirm in the official docs or the installed source. The installed version wins.

Read when the scene has grass, trees, flowers, climbing plants, scattered rocks or wind. The ground itself, its height and the fields that drive placement come from [terrain.md](terrain.md).

## Contents

- Placement and ecology
- Grass fields
- Trees
- Flowers and ground cover
- Climbing plants
- Rocks and debris
- Wind
- Symptom → cause

## Placement and ecology

**Goal.** Plants look as if they grew where they stand: each species occupies the ground that suits it, populations gather in patches with soft edges, and every stem meets the ground at exactly the height the terrain renders.

**Choose.**
- Place on the GPU, re-deriving each candidate from a hash of its cell, when counts run to hundreds of thousands (grass, flowers, pebbles). Place once on the CPU and bake into instance buffers for trees, rocks and anything that is picked, collided with or saved.
- Drive placement from rules over terrain fields by default. Paint masks only for authored paths, clearings and play lanes, and multiply them into the rules instead of replacing them.

**Build.**
1. Read height, normal, slope, altitude and wetness through the terrain's shared field functions ([terrain.md](terrain.md), Derived fields). Never write a second height function for placement.
2. Give each species a suitability from those fields (a slope range, an altitude band, moisture, shade, distance to water and paths), and multiply in a slow cluster field so populations form patches instead of even static.
3. Lay candidates on a jittered grid for even coverage, thin them by suitability, and derive every per-instance value (rotation, scale, tint, variant) from a hash of the cell's integer coordinates.
4. Fill the layers in order: canopy, then shrubs where canopy shade and moisture allow, then ground cover, then debris (leaf litter, twigs, stones) at contacts and under crowns.
5. Exclude by footprint: no trunk inside a rock, no grass on a path, clear ground around roots, and nothing below the water line except aquatic species.

**Watch for.** Plants float or sink by a few centimeters, often only on slopes, when placement samples a different height than the terrain draws: a separate noise on the CPU, an LOD level that has morphed, or a smoothed collision copy. Seeds taken from camera-snapped cells instead of world cells re-seed the field whenever the camera moves.

**Critic checks.** PASS when each species occupies plausible ground (lush growth along water, sparse cover on steep or high ground, nothing rooted on bare cliff faces), populations form patches with gradual edges, and stems meet the ground on slopes in every still. FAIL signs: even salt-and-pepper scatter; plants on cliffs or in open water; plants hovering or buried on slopes; rows or a grid.

**Diagnose.**
- Rows or a grid → jitter smaller than the cell, or a hash that correlates with the grid.
- Floating only on slopes → placement and rendering read different height functions or LOD states.
- Plants change as the camera moves → seeds come from camera-relative cells.

**Start here** (adjust to the goal): jitter each candidate by up to a full cell, and let the cluster field vary over tens of meters.

**API facts** (check the installed version):
- TSL `hash` converts its seed to an unsigned integer before a PCG-style hash, so seed it with an integer cell or instance index; raw fractional positions within one unit all hash alike (verified on r186).

## Grass fields

**Goal.** Grass reads as real when it has structure at three scales (patches, clumps, single blades), grows out of the ground rather than sitting on it, moves as one field under one wind, and keeps its coverage and hue out to the horizon. More blades without that structure only make a denser carpet.

**Choose.**
- Hero grass at eye height on a WebGPU target: a compute pass places blades around the camera, culls them by distance and frustum, writes per-blade data to a storage buffer and sets the instance counts for indirect draws, in two or three detail tiers. The compute, culling and indirect-draw mechanics are in [assets-and-performance.md](assets-and-performance.md), GPU-driven scatter; this section covers the grass itself.
- Grass that must look the same on the WebGL 2 fallback, on phones, or that plays a supporting role: instanced blades shaped in the vertex stage from a per-instance hash, in tiles that snap to the camera. Collapse blades outside the view to zero area instead of compacting a list.
- Alpha-tested cards only for far rings, stylized looks or the lowest tier. Wind moves a whole card, overdraw climbs with density, and cards look flat up close.
- Every tier ends in terrain-only grass: beyond the last blades, the ground's albedo and normal carry the field, tinted to the blades' average color.

**Build.**
1. Place blades with the terrain's own height and normal (see Placement and ecology), masked by paths, slope, shade and water.
2. Group blades into clumps taken from the nearest cell of a jittered grid. A clump shares height, lean, facing and a slight tint; blend the two nearest clump centers so borders don't seam, then vary each blade within its clump.
3. Shape each blade as a strip bent along a curved spine from a planted root: tilt decides where the tip lands, bend decides the curve, and the normal follows the spine.
4. Bend with the shared wind (see Wind): the field sets lean and facing, and each blade adds a small bob phased by its hash and by position along the blade.
5. Shade from root to tip: bake darker, occluded bases into the blade, brighten toward the tip, and let backlit blades glow warmer near the tip when the camera faces the sun. Tilt normals outward across the blade's width so it reads as rounded.
6. LOD: make each lower tier a strict subset of the tier above (same blade positions) and dither across the boundary. Widen surviving blades as density drops, thicken blades seen edge-on so they never thin to slivers, and keep a no-cull radius around the camera.
7. Far field: blend blade normals toward the clump normal, lower gloss and fade wind with distance, then hand over to the terrain tint with no ring.
8. Interaction last: push blades away from movers with a radial falloff weighted toward the tip, shorten them so they compress instead of sliding, and let a trail texture that fades a little every frame bring them back.

**Watch for.** Grass defeats screen-space AO and temporal accumulation, because blades constantly hide and reveal each other: AO turns blotchy and history smears. Bake occlusion into the blade, and check temporal AA on grass specifically. Let grass receive shadows everywhere but cast them only near the camera, since grass self-shadowing is expensive. If blades ghost under temporal AA, run the velocity check in Wind.

**Critic checks.** PASS when patches and clumps read at a glance, blade bases are darker than tips, roots stay planted in the strongest gust, gusts visibly travel across the field, sun-facing views show bright backlit edges, and the far field meets the ground with no band or ring. FAIL signs: a uniform carpet, or per-blade color noise; blades floating or buried on slopes; the field swaying in lockstep; a ring where density drops; mid-distance sparkle that changes from frame to frame; edge-on views that look thin or bald.

**Diagnose.**
- Carpet look → no clump structure, or one shared color.
- Wobble instead of wind → blades animated independently, with no traveling field.
- Bald ring at mid distance → density drops without wider blades or a takeover by the ground color.
- Pops while walking → tiers aren't subsets of each other, or seeds come from snapped cells.
- Far sparkle → per-blade normals and full gloss survive at distance.

**Start here** (adjust to the goal): fade blades into the ground color over the last third of their drawn distance.

**API facts** (check the installed version):
- `InstancedMesh` keeps the previous frame's instance matrices, so moving instances get correct motion vectors, though displacement inside the material still needs the check in Wind (verified on r186).
- With `alphaTest` set, `alphaToCoverage = true` makes a node material discard only fully transparent pixels and smooth the cut-out edge over about a pixel; the WebGPU pipeline turns that into coverage only on a multisampled target, so use it on cards only with MSAA, which temporal AA rules out (verified on r186).

## Trees

**Goal.** A tree reads as its species through branching, taper and crown shape; leaves only finish it. It must stay the same tree from the hero view to the horizon.

**Choose.**
- Authored or licensed glTF trees for heroes when the species must be exact. Procedural growth when a scene needs many varied individuals of one species from seeds.
- By distance: the full mesh near, a simplified mesh in the middle, and an impostor far away. Use an octahedral bake for roughly convex crowns and card clusters for thin, airy plants. Instancing, LOD switching, simplification and when to swap in an impostor are in [assets-and-performance.md](assets-and-performance.md).

**Build.**
1. For each branch level, write down the species' traits: how long and thick branches are and how fast they thin, how many children each carries, where along the parent those may start, the angle they leave at, their twist, and how much randomness the level allows. Identity lives in the uneven differences between levels.
2. Grow level by level from a queue, so depth and triangle budget stay inspectable. Let each branch continue from its own tip as well as sprouting laterals; laterals alone give clipped, candelabra crowns.
3. Spread children along the parent in stratified slots with jitter, and shuffle their angles independently, so no two share a height and no helix forms. Take each child's radius from the parent's radius where it emerges.
4. Bend each section by its inherited direction, seeded curvature and a growth force (up toward light, or droop); thin branches respond more than the trunk.
5. Flare the trunk at the root and sink it slightly into the ground. Hold one bark texel density from trunk to twig by choosing each branch's circumference wrap count from its radius.
6. Add leaves only once the branch topology is final, along the last-level branches. Blend foliage normals from the card toward the crown's volume so the canopy lights as one mass, and leave gaps where light passes. Backlit leaf translucency is in [special-materials.md](special-materials.md).
7. Build lower LODs from the generator (drop the finest levels, merge leaves into cluster cards) instead of generic decimation, and bake impostors from the final material.

**Watch for.** Judge trees in their setting, with ground, sky, haze and neighbors. A tree isolated on black hides edge contrast, ground contact and scale. Fix framing by moving the camera, never by editing the tree. Impostors can't sway, so fade wind out before the swap distance.

**Critic checks.** PASS when trunks flare and taper, branches leave the parent at varied heights and angles, the canopy has volume with see-through gaps, bark scale matches from trunk to twig, and distant trees keep their silhouette and color. FAIL signs: corkscrew or candelabra branching; flat leaf cards visible edge-on; bark stretched on thin branches or shrunk on the trunk; a pop or color shift when a tree changes detail level.

**Diagnose.**
- Candelabra or clipped crown → branches never continue from their tips.
- Spirals → child angles not shuffled independently of child heights.
- Pop at distance → the impostor swapped in while the tree still covered more pixels than the bake.

**Start here** (adjust to the goal): a trunk plus three branch levels, with leaves only on the last.

**API facts** (check the installed version):
- The shadow pass takes alpha from `map` and `colorNode`, copies `alphaTest` and `alphaMap`, and never reads `opacityNode`; cut-outs made only in `opacityNode` need `maskShadowNode` to cut the shadow too (verified on r186).

## Flowers and ground cover

**Goal.** A meadow keeps species identity at every distance: each flower shows its species' head shape, color and size near and far, heads follow their bent stems, and density follows ecology rather than painted bands.

**Choose.**
- Instanced stems and heads per species for counts in the thousands.
- For hundreds of thousands to millions, reconstruct each candidate on the GPU from its index, with no stored per-flower records. Cull per tile, compact visible IDs per distance tier, and draw with indirect draws. This path leans on compute, storage buffers and indirect draws, so plan a reduced tier in case the fallback can't run it.
- Ground cover (clover, moss, leaf litter) as terrain material detail, plus sparse instanced clumps where the camera comes close.

**Build.**
1. Presence comes from ecology: suitability times a broad patch field with a little fine detail. Choose the species per candidate from its hash, so mixing stays local instead of forming stripes.
2. Tiers: near heads with curved petals; a mid tier with fewer segments but the same species and variant; a far tier with a rooted stem and a simple head that still carries species color, size and petal count.
3. Bend stems from the root, with lean, wind and contact all weighted toward the top, and orient each head along its stem's tip direction.
4. Share one palette between stems and the surrounding grass so flowers sit in the sward, not on it.

**Watch for.** Placement reconstructed one way in the cull pass and another in the draw pass makes flowers flicker or jump; both must call the same function. Whether storage buffers and indirect draws work on the WebGL 2 fallback is unverified, so test with the renderer's `forceWebGL` option before promising parity.

**Critic checks.** PASS when flowers grow in drifts that thin gradually, each species stays recognizable near and far, and heads tilt with their stems. FAIL signs: one generic colored dot at distance; heads pointing straight up on bent stems; species in bands; flowers hovering above the grass.

**Diagnose.**
- The far meadow turns into uniform noise → the far tier dropped species identity or uses one billboard color.
- Flowers flicker or jump → cull and draw reconstruct candidates differently.

## Climbing plants

**Goal.** Climbers read as attached: stems hug the host surface and follow its corners, creep across it, droop where support ends, and leaves hang from their stalks.

**Build.**
1. Grow a seeded path over the host: step along the surface's tangent plane, project back onto the surface after every step, and droop under gravity where the surface falls away or ends.
2. Sweep a tube along the path with a twist-free (parallel-transported) frame, so rings never flip at seams.
3. Place leaves along the stem, each hinged at its stalk and facing out from the host, sized by age along the path.
4. In wind, rotate each leaf about its stalk, never about its center, and keep attached stems almost still.

**Critic checks.** PASS when stems touch the host along their length with no gaps or penetration, follow its corners, and leaves face outward. FAIL signs: stems floating off the wall or cutting into it; kinks or flipped rings; leaves spinning about their centers.

**Diagnose.**
- Stems drift off the wall → the path isn't projected back onto the surface each step.
- Twisting rings → a frame rebuilt per segment instead of carried along.

## Rocks and debris

**Goal.** Rocks look geological and settled: one formation process per site, a natural size spread (a few large, many small), bases sunk into the ground, and debris gathered at their contacts. Cliffs and large outcrops are terrain features ([terrain.md](terrain.md)).

**Choose.**
- A small kit of authored or scanned rocks per geology, instanced with rotation, scale and tint variation, covers most scenes. Generate rocks (a deformed base form, then fractures, erosion and strata) when variety or a specific formation matters.
- Batch static rocks; keep separate meshes only for rocks that move or are picked.

**Build.**
1. Pick the formation (layered sedimentary, blocky granite, rounded river stones, sharp scree) and keep strata running the same way across the site.
2. Scatter by size class: a few anchors, mid rocks clustered around them, and many small stones and gravel, gathered below cliffs, in stream beds and around anchors.
3. Sink each rock part of its height into the ground, aligned to the local terrain normal, and add a contact band of darker, damper soil, gravel and litter.
4. Drive the material from cavity, exposure and orientation: moss and lichen on upward and shaded faces, darker crevices, lighter weathered edges ([materials.md](materials.md) covers weathering).

**Critic checks.** PASS when rocks sit in the ground with no visible base edge or gap, sizes vary naturally, no single rock is recognizable twice in one view, and moss sits on upward or shaded faces. FAIL signs: rocks resting on the surface like props; identical rocks side by side; one size everywhere; moss on undersides.

**Diagnose.**
- Rocks look placed, not settled → no burial depth or contact debris.
- Repeats are visible → too few variants, or no random rotation and non-uniform scaling.

**Start here** (adjust to the goal): bury each rock by a quarter to a third of its height.

**API facts** (check the installed version):
- `BatchedMesh.setColorAt()` gives each instance its own tint, so one batch can hold a whole varied rock kit under a single material (verified on r186).

## Wind

**Goal.** One wind moves everything: grass, trees, flowers, particles, cloth, flags and water ripples agree on direction and gust timing, deformation stays rooted, and gusts travel across the land.

**Build.**
1. Define one world-space wind field, owned by the app shell ([router.md](router.md), Contracts builders share): a direction and strength plus a slow gust pattern, such as scrolled 2D noise, that travels with the wind. Evaluate the same function on the CPU (gameplay, particles, sound) and in shaders.
2. Give each scope its own motion: blades and stems bend along their length, leaves rotate about their stalks, branches bend by level (thin ones more and later), and whole trees sway slowly.
3. Layer the motion: a slow gust envelope, a body sway, and a quick, small flutter near the tips, phased by per-instance hash plus world position so neighbors stay coherent without moving in lockstep.
4. Weight every displacement by position along the plant, from zero at the root to full at the tip, so roots never move.
5. Fade wind with distance, and to zero before impostors take over.
6. Make shadows and motion vectors follow the same deformation as the visible surface.

**Watch for.** Shadows pick up material displacement automatically, but motion vectors may not. Check every vertex-displaced surface (grass, leaves, branches): view the velocity buffer, and if those surfaces ghost under temporal AA, supply the previous frame's displaced position, which the velocity node reads from `positionPrevious` ([final-image.md](final-image.md), Temporal AA, upscaling and motion vectors).

**Critic checks.** PASS when, across walkthrough frames, gusts sweep across grass and trees in the same direction as smoke, particles, flags and water ripples, roots and trunk bases stay fixed, and motion shows at least two scales (sway and flutter). FAIL signs: plants and particles moving different ways; the whole field pulsing in sync; roots sliding; leaves spinning about their centers; ghost trails on moving foliage.

**Diagnose.**
- The field pulses as one → wind driven by time alone, with no spatial field.
- Roots slide → displacement isn't weighted to zero at the root.
- Ghosting on foliage only → motion vectors miss the vertex displacement.

**Start here** (adjust to the goal): let gusts take a few seconds to cross the view, with flutter several times faster than sway.

**API facts** (check the installed version):
- The shadow pass reuses the material's `positionNode` unless `castShadowPositionNode` is set, so wind bending appears in cast shadows (verified on r186).
- The `velocity` node compares the displaced current position with `positionPrevious`, which defaults to the undisplaced geometry; instancing, batching and skinning update it, but displacement in the material's `positionNode` doesn't (verified on r186).

## Symptom → cause

| Symptom | Likely cause | First check |
| --- | --- | --- |
| Rows, stripes or a grid in grass or scatter | jitter smaller than the cell, or a hash that correlates with the grid | the jitter range and what the hash is seeded with |
| Uniform carpet, or salt-and-pepper color | no clump or patch structure; random tint per blade | a debug view of clump ids and tint |
| Plants float or sink on slopes | placement reads a different height than the terrain renders: a separate function, an LOD morph, or a CPU/GPU mismatch | both heights sampled at one slope point |
| A ring or line where grass ends | no widening of surviving blades, or no takeover by the terrain tint | blade width and ground tint across the last tier |
| Pops while walking | lower tiers aren't subsets of higher ones, seeds come from snapped cells, or impostors swap in too early | tier membership and the seed source |
| Mid-distance sparkle that changes every frame | per-blade normals and full gloss at distance; wind not faded | normal blending and gloss against distance |
| The whole field pulses together | wind driven by time alone | a debug view of the wind field |
| Roots or trunk bases slide | displacement not weighted to zero at the root | the displacement weight at root vertices |
| Ghost trails on grass, leaves or branches | motion vectors miss the vertex displacement (the velocity check in Wind) | the velocity buffer on those surfaces |
| Dark blotches under grass | screen-space AO running on thin, moving blades | the same frame with screen-space AO off |
| Candelabra crowns or corkscrew branches | no continuation from branch tips; child angles not shuffled | a debug view colored by branch level |
| Flat leaf cards visible | card normals not blended toward the crown volume | a normals view of the canopy |
| Leaf shadows are solid rectangles | cut-out only in `opacityNode`, with no `maskShadowNode` | where the leaf alpha is computed |
| Bark scale jumps between trunk and twigs | wrap count not chosen from each branch's radius | a UV checker on the tree |
| A distant forest turns into a flat blob | impostors or the far tier lost silhouette and color variation | the far tier alone against the sky |
| Flowers become noise far away | the far tier dropped species identity | the far tier with a single species |
| Climbers float off walls | the growth path isn't projected back onto the host each step | the path's distance from the host surface |
| Rocks look set on top of the ground | no burial depth or contact debris | a grazing view at a rock's base |
