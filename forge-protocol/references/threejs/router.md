# Three.js router

API facts verified on r186 (2026-10-05). Check the installed version first; if it differs, confirm in the official docs or the installed source. The installed version wins.

Read first on every Three.js build. It decides which topic files each agent loads, the order of work, the contracts builders share, and how the module hooks into Forge.

## Contents

- How these files work
- Probe before planning
- Route by goal
- Build order
- Routing rules
- Contracts builders share
- Version policy
- Renderer, fallback and tiers
- Forge hooks
- Symptom → cause

## How these files work

- The orchestrator reads this router and [validation.md](validation.md) at Rule 0 and when writing the bar. Each builder reads this router plus the one or two topic files its brief names. The Diagnoser reads [validation.md](validation.md) and the topic files `PLAN.md` names for the failing pieces. The critic reads none of them, so its inputs stay as [../critic-prompt.md](../critic-prompt.md) defines.
- Every topic section uses the same blocks, in this order, skipping any that don't apply: Goal, Choose, Build, Watch for, Critic checks, Diagnose, Start here, API facts. Each file opens with the version note, a line saying when to read it and a Contents list, and ends with a "Symptom → cause" table.
- Critic checks are starters, not a bar. The orchestrator keeps only those the goal motivates and rewrites them as PASS/FAIL criteria in `art/BAR.md` ([../visual-bar.md](../visual-bar.md)).
- "Start here" values are starting points, never requirements; adjust them to the goal.
- If the goal needs a system no file covers, say so in the plan and research it. Never stretch the nearest file to cover it.

## Probe before planning

Add these to the Rule 0 tools probe, and record the results in `BRIEF.md` (Stack) and in the tools table of `PLAN.md`:
- the installed three.js revision, read from the package or lockfile, and which renderer the project uses (`WebGPURenderer` or `WebGLRenderer`);
- the backend and adapter each target device and the capture route actually land on: WebGPU or the WebGL 2 fallback, on a hardware or software adapter ([foundation.md](foundation.md));
- target devices, any frame budget, and the quality tiers the build will offer ([assets-and-performance.md](assets-and-performance.md));
- assets on hand, and Blender status ([../pipelines.md](../pipelines.md)).

## Route by goal

| The goal shows or needs | Read |
| --- | --- |
| Routing, build order, shared contracts, version policy | `router.md`, this file, first for every agent that loads the module |
| Any Three.js build: renderer and backend, color management, loop and time, capture hooks | [foundation.md](foundation.md), for the app-shell builder |
| Custom shaders, TSL or compute passes | [foundation.md](foundation.md) |
| Loaded models and textures, compression, units and scale | [assets-and-performance.md](assets-and-performance.md) |
| Large worlds, many objects, phones, a frame budget, quality tiers | [assets-and-performance.md](assets-and-performance.md) |
| The final image: output owner, tone mapping and exposure, the post chain, the choice of AO and GI, temporal AA, antialiasing, screen-space reflections, god rays, bloom, depth of field, grading | [final-image.md](final-image.md) |
| Light design, environment light, the sun, shadows, contact grounding, bounce, practical and many lights | [lighting-and-shadows.md](lighting-and-shadows.md) |
| Surfaces that read as real materials: identity, PBR textures, anti-tiling, procedural fields, filtering and shader aliasing, weathering and wetness, relief, toon | [materials.md](materials.md) |
| Glass, gems, soap films, foil, cloth, fur, skin, jelly, sand, lava, brushed metal | [special-materials.md](special-materials.md) |
| Vehicles, robots, props and other hard-surface objects; mesh checks and turnarounds | [geometry.md](geometry.md) |
| Buildings, interiors, streets and cities | [architecture.md](architecture.md) with [geometry.md](geometry.md) |
| Landscapes: hills, mountains, real places, erosion, terrain LOD and texturing, 3D tiles | [terrain.md](terrain.md) |
| Grass, trees, flowers, climbing plants, scattered rocks, wind | [nature.md](nature.md) with [terrain.md](terrain.md) |
| Sky, fog and haze, clouds, time of day | [sky-and-weather.md](sky-and-weather.md) with [lighting-and-shadows.md](lighting-and-shadows.md) |
| Rain, snow, aurora, lightning | [sky-and-weather.md](sky-and-weather.md) with [materials.md](materials.md) |
| Puddles, pools, rivers, lakes, oceans, shores, underwater views, boats | [water.md](water.md) |
| Space: stars, planets, black holes, wormholes, nebulae, spacecraft effects | [space.md](space.md) |
| Particles, fire, smoke, explosions, magic, holograms, trails, decals, lens flare | [effects.md](effects.md) |
| Frost or rain on glass, and other screen-space surfaces | [effects.md](effects.md) |
| Shots, framing, camera rigs, transitions, cinematic sequences | [camera-and-animation.md](camera-and-animation.md) |
| Animated characters and objects, procedural motion, easing that settles | [camera-and-animation.md](camera-and-animation.md) |
| Games and interactive demos: game loop, input, picking, physics, UI, audio | [interaction-and-ui.md](interaction-and-ui.md) |
| Evidence: criteria from the goal, the capture set and recipes, diagnostic views, proving hooks, provenance, headless capture traps, silent failures, temporal and performance evidence, the Diagnoser table | [validation.md](validation.md), for the orchestrator, the Diagnoser and builders exposing hooks |

Split work so that no builder needs more than two topic files. Typical splits:
- **Product showcase:** app shell ([foundation.md](foundation.md), [final-image.md](final-image.md)); look ([lighting-and-shadows.md](lighting-and-shadows.md), [materials.md](materials.md)); a special surface ([special-materials.md](special-materials.md)).
- **Island at sunset:** app shell; land ([terrain.md](terrain.md), [nature.md](nature.md)); sea ([water.md](water.md)); sky ([sky-and-weather.md](sky-and-weather.md), [lighting-and-shadows.md](lighting-and-shadows.md)).
- **Browser racing game:** app shell ([foundation.md](foundation.md), [assets-and-performance.md](assets-and-performance.md)); cars ([geometry.md](geometry.md), [materials.md](materials.md)); play ([interaction-and-ui.md](interaction-and-ui.md), [camera-and-animation.md](camera-and-animation.md)).
- **Space flythrough:** app shell; space ([space.md](space.md)); camera ([camera-and-animation.md](camera-and-animation.md)).

## Build order

Form and materials first, then light, shadows and atmosphere, then image effects. Each stage must read in its own captures before the next is added, and post-processing never rescues an earlier stage.
1. **Contract:** subject, units and scale, the camera envelope (near, design and far views), motion, frame budget, and the shared contracts below.
2. **App shell and hooks** ([foundation.md](foundation.md)), with the capture route proven. Choose the output owner and tone mapper here, so every later stage is judged through the final display transform.
3. **Camera and framing** ([camera-and-animation.md](camera-and-animation.md)).
4. **Form without materials:** blockout, terrain and hero geometry, judged in a flat or clay material.
5. **Materials** and the fields that drive them.
6. **Motion:** animation, wind, water and simulation.
7. **Light and shadows.**
8. **Atmosphere:** sky, fog, clouds and weather.
9. **Effects.**
10. **Image effects last:** post-processing passes, tuned only once the no-post still passes.
11. **Evidence:** the capture set and diagnostic views ([validation.md](validation.md)).

## Routing rules

- Find the missing authored system before reaching for post-processing. "Make it beautiful" is never a bloom request.
- One strong rule you can inspect beats several stacked noise layers.
- Keep the mechanism that gives the goal its character: a spectral ocean the brief calls for is not a normal-mapped plane, and a growth hierarchy is not scattered cylinders.
- Choose the cheapest representation that owns the view, and name honestly what a lower tier gives up.
- Keep object-, world- and screen-space systems separate unless coupling them is the point.
- Don't go 3D unless the goal needs it ([../pipelines.md](../pipelines.md)).

## Contracts builders share

Agree these before parallel work starts. The app-shell builder owns them, and `PLAN.md` lists them:
- **Units and axes:** one unit is one meter, +Y is up.
- **Time and seeds:** one clock in seconds, pinnable for capture, and one seed source for everything visible.
- **Sun and sky:** one sun description (direction, color, intensity) that sky, light, fog, water and shadows read ([sky-and-weather.md](sky-and-weather.md)).
- **Wind:** one world-space wind field ([nature.md](nature.md), Wind).
- **Weather:** one weather state passed by reference ([sky-and-weather.md](sky-and-weather.md)).
- **Ground:** one height function and one set of derived fields ([terrain.md](terrain.md), Derived fields).
- **Output:** one owner of tone mapping and display conversion ([final-image.md](final-image.md)).
- **Tiers:** the quality tiers and what each keeps ([assets-and-performance.md](assets-and-performance.md)).
- **Hooks:** one set of names for the ready flag, camera bookmarks, debug modes, the tier switch, reset, pause and step, and metrics ([foundation.md](foundation.md)).

## Version policy

- Pin the installed three.js version in the project's package manifest and lockfile, and record the revision (for example r186) in `BRIEF.md` under Stack.
- Ground truth, in order of authority:
  1. the installed package's own source and doc comments (its `src` and `examples/jsm` folders);
  2. `threejs.org/docs/llms.txt` (short rules) and `threejs.org/docs/llms-full.txt` (inline API and TSL docs);
  3. the Migration Guide on the three.js GitHub wiki;
  4. the official example for the feature, read as source from threejs.org/examples.
- The table of APIs renamed or removed from r180 to r186 is in [foundation.md](foundation.md); read it before writing from memory.
- Deprecation warnings are failures. The console at capture time shows none; fix each by migrating, never by silencing it. Deprecated names keep working for about ten releases, so upgrade in steps.
- Removed names often fail silently, because assigning a property the library no longer reads raises no error. Check names against the installed source; a clean console proves nothing about a misspelled or retired option.
- API facts in these files carry the tag "verified on r186". When the installed revision differs, confirm each fact you rely on in the installed source, and report any mismatch in the handback. On a module upgrade, search for the tag and re-verify every fact.

## Renderer, fallback and tiers

- Choosing between `WebGPURenderer` (node materials, TSL, compute, with an automatic WebGL 2 fallback) and `WebGLRenderer`, probing capabilities, and keeping the backend identical across capture rounds: [foundation.md](foundation.md).
- Quality tiers, what each keeps and gives up, and pinning the tier for capture: [assets-and-performance.md](assets-and-performance.md).
- Every compute-driven feature names its fallback in the tier table: GPU grass becomes vertex-shaded instances ([nature.md](nature.md)), spectral water becomes Gerstner waves ([water.md](water.md)), raymarched clouds become layered or billboard clouds ([sky-and-weather.md](sky-and-weather.md)). The lowest tier still keeps the goal's defining look.

## Forge hooks

- **Rule 0:** the probe above extends the tools probe; its results go into `BRIEF.md` (Stack) and the tools table of `PLAN.md` ([../project-files.md](../project-files.md)).
- **Plan:** each builder's brief names the topic files it reads and the shared contracts it touches.
- **Bar:** start from the 3D pack ([../criteria-packs.md](../criteria-packs.md)), then pull critic-check starters from the topic files in the plan. When adapting C2, require the backend recorded in `MANIFEST.md` to match the one `BRIEF.md` targets.
- **Capture:** a no-post still of every hero view in every mode; near, design and far views in Standard and Forge; diagnostic and stress stills only when a criterion needs them. The capture tool sets debug mode and tier through the build's hooks ([../capture-and-tools.md](../capture-and-tools.md)); the full capture set is in [validation.md](validation.md).
- **Manifest:** every capture records the revision, backend and compatibility mode, adapter, browser, pixel ratio, canvas size and tier ([../project-files.md](../project-files.md)).
- **Escalation:** post-processing is tuned only after the no-post still passes ([../criteria-packs.md](../criteria-packs.md)). A stuck loop's Diagnoser reads [validation.md](validation.md) and the topic files `PLAN.md` names ([../diagnoser-prompt.md](../diagnoser-prompt.md)).
- **Handback:** builders report, as facts, the revision and backend they built against and any API fact that didn't match the installed version.

## Symptom → cause

| Symptom | Likely cause | First check |
| --- | --- | --- |
| Pieces from different builders disagree in scale | no shared units contract, or an asset left in other units | the units contract in `PLAN.md`, and a human-scale reference in the view |
| Pieces move at different rates, or layouts change between rounds | more than one clock or seed source | the time and seed source each piece reads |
| Shadows, sky, fog or water glint disagree about the sun | separate sun descriptions | which sun description each piece reads ([sky-and-weather.md](sky-and-weather.md)) |
| Plants, particles and water blow different ways | no shared wind field | each system's wind source ([nature.md](nature.md), Wind) |
| Rain over dry ground, or falling snow with no cover | particles and surfaces read different weather | the weather state each piece reads ([sky-and-weather.md](sky-and-weather.md)) |
| Plants, water or players float above or sink into the ground | a second height function | each consumer's height source ([terrain.md](terrain.md)) |
| Gray, washed-out or doubled-contrast frame | more than one piece tone-maps or converts to display | the one output owner ([final-image.md](final-image.md)) |
| A must-have shows in some captures but not others | tiers differ between pieces, or the tier wasn't pinned | the tier recorded for each capture in `MANIFEST.md` |
| The capture tool can't reach a view or debug mode | hook names that differ between pieces | the hook names in `PLAN.md` ([foundation.md](foundation.md)) |
| Code that follows a topic file still fails or warns | the installed revision isn't r186, or a name written from memory | the revision in `BRIEF.md` against the installed source |
