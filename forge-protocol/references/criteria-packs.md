# Criteria packs

Starting points for goal-specific criteria (C4 onward), with a default capture recipe and escalation levers for each domain. Pick the closest pack, keep only the criteria the goal motivates, and rewrite each one so a critic can observe it in this project's captures (rules in [visual-bar.md](visual-bar.md)). Mix packs for hybrid work: a 3D scene with an editorial overlay uses `3d` and `web-ui`.

Capture recipes are defaults. Decide views, sizes and frame counts from the goal and record them in `BRIEF.md` under Captures.

## 3d: worlds, scenes, games

**Capture**: one still per key view the brief names (hero, gameplay, detail) at the target display size; walkthrough frames across camera moves, lighting changes and interactions; a turnaround for every hero asset.

**Criteria starters**
- **Materials and light**: surfaces show plausible roughness and specular response with normal or bump breakup; one readable key light casts shadows; contact darkening where objects meet the ground; exposure stays inside a deliberate palette.
- **Form and density**: hero objects are authored multi-part shapes, never primitive stand-ins; silhouettes read at camera distance; ground and set dressing carry the breakup the brief implies; no visible tile seams.
- **Atmosphere and depth**: aerial perspective, haze or fog and value separation give a clear foreground, midground and background.
- **Optical media** (water, glass, smoke): color and transparency change with depth; refraction, reflection or caustics appear where light would produce them; waves layer several scales without grid artifacts.
- **Mood and time of day** (when the goal names one): light angle, shadow length, color temperature and emissive spill express the stated mood consistently across views.
- **Nature craft** (rocks, plants, terrain): rocks show erosion and stratification; trunks curve and leaves are individual, casting foliage shadows; wind moves them; transition debris sits where objects meet the ground.
- **Physics coupling** (vehicles, boats, cloth, crowds): motion responds to the same forces that drive the visuals (waves, wind, terrain) with visible feedback such as wakes, ripples or trails; nothing slides or floats.
- **Diegetic and HUD UI** (when the scene carries UI): type hierarchy, framing and live controls stay legible at capture size and never cover the focal subject.

**Escalation levers**: (1) light and post: shadow cascades and bias, ambient occlusion, tone mapping, fog, restrained bloom; (2) materials and shaders: PBR maps, custom shaders, macro variation against tiling; (3) authored geometry and scatter density: Blender assets, instancing; (4) render passes: depth and refraction targets, reflections, GPU simulation buffers; (5) engine change: WebGL to WebGPU, or the web stack to Unity.

**Tools**: headless Blender for hero meshes and turnarounds, Blender MCP for live look-dev, PolyHaven (CC0) textures and HDRIs. Details in [unity-and-blender-pipelines.md](unity-and-blender-pipelines.md).

## web-ui: landing pages, product UI, app screens

**Capture**: each must-have screen at desktop size and at the smallest target width; the hover, focus, active, empty, loading and error states the brief names; scroll positions for long pages.

**Criteria starters**
- **Typography hierarchy**: display, heading and body levels are distinct at a glance; line length and leading are comfortable; no default system font where the goal calls for brand.
- **Layout and rhythm**: one grid and spacing scale; aligned edges; nothing cramped or floating.
- **Color and contrast**: a deliberate palette; body text meets WCAG AA contrast (4.5:1, or 3:1 for large text).
- **Components and states**: every interactive element shows hover, focus and active states; empty, disabled and error states are designed rather than default.
- **Imagery and icons**: crisp at the device pixel ratio, one consistent style, nothing stretched or placeholder.
- **Motion**: transitions have a purpose and consistent easing and duration; no jank across frames.
- **Responsiveness**: no overflow, overlap or clipped text at any captured width.

**Escalation levers**: (1) type scale and spacing tokens; (2) color system, elevation and imagery; (3) layout and component rebuild; (4) motion and interaction system; (5) framework or rendering change.

## dataviz: charts, dashboards, maps

**Capture**: each view with real or realistic data at the brief's volume; the tooltips, selections and filters it names; the smallest and largest target sizes.

**Criteria starters**
- **Data integrity**: marks encode the data correctly: honest axes and baselines, labeled units, no distortion; a spot-check value in a still matches the data.
- **Encoding fit**: chart types answer the questions in the brief; color scales match the data type (sequential, diverging, categorical) and stay distinguishable for color-blind viewers.
- **Legibility**: labels, ticks and legends are readable at capture size without overlap; direct labels where they fit.
- **Hierarchy and annotation**: the key takeaway dominates visually; annotations explain what matters.
- **Interaction**: hover and selection feedback is immediate, and transitions keep the viewer oriented.
- **Performance**: no dropped frames, blank states or layout jumps in walkthrough frames.

**Escalation levers**: (1) labels, color scale, gridline weight; (2) mark styling and annotation; (3) chart type and layout; (4) rendering approach (SVG to canvas or WebGL) and data aggregation; (5) library change.

## 2d: 2D games, illustration, motion graphics

**Capture**: key gameplay or animation moments; frames across the main motion; title and UI states.

**Criteria starters**
- **Style consistency**: one shape language and rendering style across characters, props, backgrounds and UI.
- **Line, shading and palette**: clean edges at native size, a deliberate palette, one consistent light direction.
- **Animation**: anticipation, follow-through, easing and timing; no sliding feet, popping frames or dead holds.
- **Readability**: the player, threats and interactables separate from the background at a glance.
- **Feedback**: hits, pickups and transitions have visible, well-timed feedback.

**Escalation levers**: (1) palette, values and lighting; (2) sprite and asset detail; (3) animation set and timing; (4) rendering: shaders, particles, post; (5) engine change.

## interactive: physics sims, toys, explorable explanations

**Capture**: the initial state, mid-interaction and edge-case states; walkthrough frames of the main interaction; the parameter extremes the brief names.

**Criteria starters**
- **Physical plausibility**: motion follows the stated model (energy behaves, collisions resolve, nothing tunnels) with constants in a researched, plausible range.
- **Stability**: no explosions, jitter or NaN states at the brief's parameter extremes.
- **Feel**: input produces an immediate, continuous visible response.
- **Explanation** (when the goal teaches): labels and visual cues make cause and effect readable without walls of text.
- **Controls**: parameters are discoverable, labeled with units, and their effect is visible.

**Escalation levers**: (1) visual feedback and presentation; (2) integration step and constants; (3) simulation method, e.g. explicit to semi-implicit or position-based; (4) GPU compute or worker offload; (5) engine change.
