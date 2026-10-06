# Unity router: probe, routes, recipes, build order, contracts and Forge hooks

API facts verified on Unity 6.6 (6000.6.4f1, 2026-10-06). Check the project's Unity version first (ProjectSettings/ProjectVersion.txt); if it differs, confirm in that version's official docs or the installed packages. The installed version wins.

Read when any Unity build starts, before every other file in this module: it says which topic files each agent loads, in what order the work happens, which contracts builders agree on, and how the module plugs into Forge.

## Contents

- How these files work
- Probe before planning
- Route by goal
- Recipes by goal
- Build order
- Routing rules
- Contracts builders share
- Version policy
- Pipeline, targets and tiers
- Forge hooks
- Symptom → cause

## How these files work

- The orchestrator reads this router, [setup.md](setup.md), [agent-control.md](agent-control.md) and [validation.md](validation.md) at Rule 0 and when writing the bar, and [genres-and-scope.md](genres-and-scope.md) when the goal is a game. Each builder reads this router, [project-hygiene.md](project-hygiene.md), and the one or two topic files its brief names. The Diagnoser reads [validation.md](validation.md) and the topic files `PLAN.md` names for the failing pieces. The critic reads none of them, so its inputs stay as [../critic-prompt.md](../critic-prompt.md) defines.
- Every topic section uses the same blocks, in this order, skipping any that don't apply except Goal and Build: Goal, Choose, Build, Watch for, Critic checks, then Diagnose, Start here and API facts. Each file opens with the version note, a line saying when to read it and a Contents list, and ends with a "Symptom → cause" table.
- Critic checks are starters, not a bar. The orchestrator keeps only those the goal motivates and rewrites them as PASS/FAIL criteria in `art/BAR.md` ([../visual-bar.md](../visual-bar.md)).
- "Start here" values are starting points, never requirements; adjust them to the goal.
- If the goal needs a system no file covers (multiplayer, for example), say so in the plan and research it. Never stretch the nearest file to cover it.

## Probe before planning

Add these to the Rule 0 tools probe, without launching the Editor or the Hub ([setup.md](setup.md), Probe without launching anything), and record the results in `BRIEF.md` (Stack) and in the tools table of `PLAN.md`:
- the installed editors, each one's version and changeset, and its modules (Mac with Mono or IL2CPP, Web, Documentation);
- the license state: the Hub signed in, Personal or a paid plan; never the license file's contents;
- the project's version from `ProjectVersion.txt`, and its packages from `Packages/manifest.json` and `packages-lock.json`;
- the render pipeline asset on each quality level, and the Graphics default;
- the Active Input Handling setting;
- the engine CLI: on the path or not, its version, whether it is signed in, and whether the project holds its editor package `com.unity.pipeline`;
- any community editor bridge, by name only;
- the targets, any frame budget, and the quality tiers the build will offer ([performance-and-builds.md](performance-and-builds.md));
- git, Git LFS, a .NET SDK and a C# editor extension, and Blender's status ([../pipelines.md](../pipelines.md)).

## Route by goal

| The goal shows or needs | Read |
| --- | --- |
| Routing, build order, shared contracts, version policy | `router.md`, this file, first for every agent that loads the module |
| Installs, license and sign-in, the first project, the settings floor, coaching a new user | [setup.md](setup.md), for the orchestrator |
| Which files agents write, meta files and GUIDs, serialization, prefabs, assemblies, packages, git | [project-hygiene.md](project-hygiene.md), for every builder |
| Routes into Unity, readiness and dialogs, the compile loop, editor scripts, the engine CLI, batch mode, logs, command-line builds | [agent-control.md](agent-control.md), for the orchestrator and the app-shell builder |
| Evidence: criteria from the goal, the capture set and routes, proving the route, determinism, tests, console discipline, performance evidence, smoke tests, provenance, the Diagnoser table | [validation.md](validation.md), for the orchestrator, the Diagnoser and the capture builder |
| A first game: genre, template, packages, finish line, scope traps | [genres-and-scope.md](genres-and-scope.md), at Rule 0 |
| Version truth and renamed APIs, the render pipeline choice and the HDRP route, color space and HDR, the frame loop, Play mode without domain reload, async code | [foundation.md](foundation.md), for the app-shell builder |
| Imported models (FBX, glTF, Blender), textures and audio, Read/Write, units and axes, asset licenses, the Asset Store and Mixamo policy, and the ledger | [assets-and-import.md](assets-and-import.md) |
| Budgets for Mac and Web, quality tiers, batching and instancing, culling and LOD, content loading, profiling, Web build limits, the scripting backend | [performance-and-builds.md](performance-and-builds.md) |
| The final image: volumes, tone mapping and exposure, post effects, anti-aliasing, the tonemapping-only no-post profile | [final-image.md](final-image.md) |
| Light design, the sun, environment light, baked light and probes, shadows, reflection probes | [lighting-and-shadows.md](lighting-and-shadows.md) |
| URP materials, Shader Graph, texture maps, toon lighting, transparency, decals, anti-tiling, shader variants | [materials-and-shaders.md](materials-and-shaders.md) |
| Blockout, modular kits, level pieces as prefabs, exports from Blender, roads and rails on splines, interiors and occlusion, colliders, lightmap UVs | [levels-and-geometry.md](levels-and-geometry.md) |
| Terrain: heights, layers, trees, grass, scatter and wind | [terrain-and-nature.md](terrain-and-nature.md) |
| Sky, fog, clouds, weather and water | [sky-weather-and-water.md](sky-weather-and-water.md) |
| Particles, VFX Graph and its Web fallback, trails, full-screen effects, effects from causes | [effects.md](effects.md) |
| Cameras and Cinemachine, shake, Animator, Timeline, motion along splines | [camera-and-animation.md](camera-and-animation.md) |
| Character controllers, physics settings, navigation, game feel, hit-stop, respawn | [characters-physics-and-feel.md](characters-physics-and-feel.md) |
| Input System actions and rebinding, UI Toolkit and uGUI, text and fonts, menus and HUD, audio | [input-ui-and-audio.md](input-ui-and-audio.md) |
| 2D renderer, sprites and atlases, tilemaps, sorting, 2D lights, the pixel-perfect camera, 2D physics and animation, parallax | [2d.md](2d.md) |

Split work so that no builder needs more than two topic files beyond this router and [project-hygiene.md](project-hygiene.md).

## Recipes by goal

- **3D third-person explorer:** app shell ([foundation.md](foundation.md), [agent-control.md](agent-control.md)); land ([terrain-and-nature.md](terrain-and-nature.md), [levels-and-geometry.md](levels-and-geometry.md)); sky and light ([sky-weather-and-water.md](sky-weather-and-water.md), [lighting-and-shadows.md](lighting-and-shadows.md)); player ([characters-physics-and-feel.md](characters-physics-and-feel.md), [camera-and-animation.md](camera-and-animation.md)); UI and audio ([input-ui-and-audio.md](input-ui-and-audio.md)); look ([materials-and-shaders.md](materials-and-shaders.md), [final-image.md](final-image.md)). Scope from [genres-and-scope.md](genres-and-scope.md).
- **2D platformer:** app shell ([foundation.md](foundation.md), [2d.md](2d.md)); levels ([2d.md](2d.md), [levels-and-geometry.md](levels-and-geometry.md)); player ([characters-physics-and-feel.md](characters-physics-and-feel.md), [2d.md](2d.md)); camera and UI ([camera-and-animation.md](camera-and-animation.md), [input-ui-and-audio.md](input-ui-and-audio.md)); juice ([effects.md](effects.md)).
- **Showcase scene, no gameplay:** app shell ([foundation.md](foundation.md), [final-image.md](final-image.md)); set ([levels-and-geometry.md](levels-and-geometry.md), [materials-and-shaders.md](materials-and-shaders.md)); environment ([terrain-and-nature.md](terrain-and-nature.md), [sky-weather-and-water.md](sky-weather-and-water.md)); light ([lighting-and-shadows.md](lighting-and-shadows.md)); camera moves ([camera-and-animation.md](camera-and-animation.md)). The HDRP route is possible here, Mac only and with the user's approval ([foundation.md](foundation.md)).
- **Top-down arena:** app shell ([foundation.md](foundation.md), [performance-and-builds.md](performance-and-builds.md)); arena ([levels-and-geometry.md](levels-and-geometry.md)); combat feel ([characters-physics-and-feel.md](characters-physics-and-feel.md), [effects.md](effects.md)); camera and HUD ([camera-and-animation.md](camera-and-animation.md), [input-ui-and-audio.md](input-ui-and-audio.md)).
- **Arcade racer:** app shell ([foundation.md](foundation.md), [performance-and-builds.md](performance-and-builds.md)); track ([levels-and-geometry.md](levels-and-geometry.md), [terrain-and-nature.md](terrain-and-nature.md)); car and camera ([characters-physics-and-feel.md](characters-physics-and-feel.md), [camera-and-animation.md](camera-and-animation.md)); HUD ([input-ui-and-audio.md](input-ui-and-audio.md)).

## Build order

Feel and form first, then materials, light and atmosphere, then image effects. Each stage must read in its own captures before the next is added, and post-processing never rescues an earlier stage.
1. **Contract:** the genre and the scope cut ([genres-and-scope.md](genres-and-scope.md)), the subject and its scale, the camera envelope (near, design and far views), targets and budgets, and the shared contracts below.
2. **Project and routes:** the project, the settings floor and the first commit ([setup.md](setup.md), [project-hygiene.md](project-hygiene.md)); the control routes approved ([agent-control.md](agent-control.md)).
3. **App shell and hooks:** the boot scene, the capture hooks, the debug overlay and the quality tiers, with the capture route proven on a known answer ([validation.md](validation.md)). Choose the output owner and tone mapper here, so every later stage is judged through the final display transform ([final-image.md](final-image.md)).
4. **The core loop on a blockout:** controls, camera, rules and the loop shell (title, pause, retry), on blockout geometry in one flat material. Lock the feel here.
5. **Form:** levels, terrain and hero geometry, still in a flat material.
6. **Materials.**
7. **Motion:** animation, wind, water and physics props.
8. **Light and shadows,** baked once the form has settled.
9. **Atmosphere:** sky, fog, clouds and weather.
10. **Effects and audio.**
11. **UI polish.**
12. **Image effects last:** post-processing, tuned only once the no-post still passes.
13. **Builds and evidence:** a player per target, smoke tests, the capture set and performance evidence ([validation.md](validation.md)).

## Routing rules

- Find the missing authored system before reaching for post-processing. "Make it beautiful" is never a bloom request.
- Generate, don't place: anything an editor script can rebuild beats hand placement in the Editor ([agent-control.md](agent-control.md)).
- Keep the mechanism that gives the goal its character, and name honestly what a lower tier gives up.
- Every feature that depends on compute shaders or on Mac-only rendering names its Web fallback in the tier table, such as the particle system standing in for VFX Graph ([effects.md](effects.md)); the lowest tier still keeps the goal's defining look.
- Don't go 3D, or to Unity at all, unless the goal needs it ([../pipelines.md](../pipelines.md)).
- Asset Store files, Unity's Starter Assets included, and Mixamo files follow the policy in [assets-and-import.md](assets-and-import.md) (Asset Store and Mixamo files).

## Contracts builders share

Agree these before parallel work starts. The app-shell builder owns them, and `PLAN.md` lists them:
- **Units and axes:** one unit is one meter, +Y is up ([assets-and-import.md](assets-and-import.md)).
- **Scene list:** the boot scene, each game scene and the known-answer test scene, their order in each build profile, and one owner per scene.
- **Folder layout:** one root folder for the project's own content, with subfolders for scripts, editor code, prefabs, scenes, art, settings and tests; third-party content in its own folders; one owner per folder ([project-hygiene.md](project-hygiene.md)).
- **Input actions:** one project-wide input actions asset with named action maps, read by every system ([input-ui-and-audio.md](input-ui-and-audio.md)).
- **Render pipeline asset and quality tiers:** a URP asset on every quality level, what each tier keeps, which tier each target uses, and the tier pinned for capture ([performance-and-builds.md](performance-and-builds.md)).
- **Output:** one owner of tone mapping and exposure, in one global volume, plus the tonemapping-only debug profile ([final-image.md](final-image.md)).
- **Time and seeds:** one capture clock with a fixed step, a list of anything driven by unscaled time, and one seed source for everything visible ([foundation.md](foundation.md), [validation.md](validation.md)).
- **Sun and sky:** one sun description (direction, color, intensity) that sky, light, fog, water and shadows read ([sky-weather-and-water.md](sky-weather-and-water.md), [lighting-and-shadows.md](lighting-and-shadows.md)).
- **Wind:** one world wind (direction, speed in meters per second, gusts) published as global shader values ([terrain-and-nature.md](terrain-and-nature.md)).
- **Weather:** one weather state that every consumer reads ([sky-weather-and-water.md](sky-weather-and-water.md)).
- **Ground:** one height source and its derived fields (slope, altitude, wetness), read by layers, scatter, water and characters ([terrain-and-nature.md](terrain-and-nature.md)).
- **Layers and tags:** named physics and rendering layers, the collision matrix and the tags code relies on, all created by one editor script ([characters-physics-and-feel.md](characters-physics-and-feel.md)).
- **Capture hooks:** one capture component with a ready signal, named camera bookmarks, view and state setters, debug modes (final; no-post, which turns on the `NoPost` profile from [final-image.md](final-image.md); the diagnostic views the bar needs), the tier switch, pause, step, set time, reset, a HUD toggle, metrics and the provenance line. Players reach it through a command-line argument and the Editor through menu items ([validation.md](validation.md)).

## Version policy

- Pin the editor version per project (`ProjectVersion.txt`) and the packages through `manifest.json` and `packages-lock.json`, and record the version and changeset under Stack in `BRIEF.md`.
- Ground truth, in order of authority:
  1. the installed editor's offline Manual and Scripting Reference (the Documentation module) and the installed packages' own docs and source;
  2. the official 6000.6 Manual and Scripting Reference online, and the docs for the package versions the lock file names;
  3. Unity's C# reference source at the project's exact version;
  4. the official sample for the feature.
- For the engine CLI, its own `--help` output is the authority, because it changes weekly.
- The table of APIs renamed or removed between 2022 LTS and 6.6 is in [foundation.md](foundation.md); read it before writing from memory.
- Warnings that say obsolete or deprecated are failures: fix each by migrating, never by silencing it ([validation.md](validation.md), Console discipline).
- Removed settings, and Built-in callbacks that URP never calls, fail without a message, so check names against the installed docs; a clean console proves nothing about them.
- API facts in these files carry the tag "verified on 6000.6". When the installed version differs, confirm each fact you rely on and report any mismatch in the handback. After an upgrade, for example to the 6.7 LTS due around the end of 2026, search for the tag and check every fact again.

## Pipeline, targets and tiers

- URP, starting from the Universal 3D template (Universal 2D when the game is sprite-based); HDRP only as a short route the user approves, for a Mac-only showcase; Built-in never ([foundation.md](foundation.md)). The bundled copy of Universal 3D names itself 3D URP; what each template includes, and what the agent adds, is in [setup.md](setup.md).
- Targets: an Apple silicon Mac and the Web. On the Web, WebGL 2 is the default, for reach. WebGPU is opt-in only: the Web target enables WebGL 2 by itself, and WebGPU must be added to the Player settings' graphics API list, with WebGL 2 kept behind it as the fallback ([performance-and-builds.md](performance-and-builds.md)).
- HDRP runs on neither WebGL 2 nor WebGPU, which is one reason it stays a Mac-only route ([foundation.md](foundation.md)).
- Quality tiers are quality levels, each with its own URP asset; build profiles choose them per target, and capture pins one.
- Unity AI and Unity Cloud stay off by default and are never required ([setup.md](setup.md)).

## Forge hooks

- **Rule 0:** the probe above extends the tools probe; its results go into `BRIEF.md` (Stack) and the tools table of `PLAN.md` ([../project-files.md](../project-files.md)), together with the control routes approved for this build ([agent-control.md](agent-control.md)).
- **Plan:** each builder's brief names the topic files it reads, the shared contracts it touches, the Unity route it uses, and the scenes, prefabs and folders it owns.
- **Bar:** start from the 3D pack, or the 2D pack for sprite games ([../criteria-packs.md](../criteria-packs.md)), then pull critic-check starters from the topic files in the plan. When adapting C2, require the capture route, quality level, graphics API and target recorded in `MANIFEST.md` to match the ones `BRIEF.md` names.
- **Capture:** when the build uses post-processing, a no-post still of every hero view in every mode, keeping tone mapping through the tonemapping-only profile; near, design and far views of each primary hero subject in Standard and Forge; diagnostic and stress stills only when a criterion needs them. Capture from a freshly launched player by default, and prove the route on a known answer before round 1; the full set is in [validation.md](validation.md).
- **Manifest:** every capture records the Unity version and changeset, the render pipeline and its asset, the graphics API, the GPU, the quality level, the target and build profile, Editor or player, Play or Edit mode, the capture source, the size, the time step and seed, and whether it ran in a fresh process ([../project-files.md](../project-files.md)).
- **Escalation:** post-processing is tuned only after the no-post still passes ([../criteria-packs.md](../criteria-packs.md)). A stuck loop's Diagnoser reads [validation.md](validation.md) and the topic files `PLAN.md` names ([../diagnoser-prompt.md](../diagnoser-prompt.md)). Moving from URP to HDRP is a stack-level change: it needs the user's agreement and gives up the Web target.
- **Handback:** builders report, as facts, the Unity version and package versions they built against, the route they used, any API fact that didn't match the installed version, and any one-off code run along with the user's approval.

## Symptom → cause

| Symptom | Likely cause | First check |
| --- | --- | --- |
| Pieces from different builders disagree in scale | no shared units contract, or an asset imported at another scale | the units contract in `PLAN.md`, and a human-scale reference in the view ([assets-and-import.md](assets-and-import.md)) |
| Pieces move at different rates, or layouts change between rounds | more than one clock or seed source | the time and seed contract ([foundation.md](foundation.md)) |
| Shadows, sky, fog or water disagree about the sun | separate sun descriptions | which sun description each piece reads ([sky-weather-and-water.md](sky-weather-and-water.md)) |
| Plants, particles and water blow different ways | no shared wind | the wind values each system reads ([terrain-and-nature.md](terrain-and-nature.md)) |
| Plants, water or characters float above or sink into the ground | a second height source | each consumer's height source ([terrain-and-nature.md](terrain-and-nature.md)) |
| A gray, washed-out or doubled-contrast frame | more than one volume or camera owns tone mapping | the one output owner ([final-image.md](final-image.md)) |
| A must-have shows in some captures but not others | tiers differ between pieces, or the quality level wasn't pinned | the quality level recorded in `MANIFEST.md` ([performance-and-builds.md](performance-and-builds.md)) |
| Input works in one scene but not in another | a second actions asset, or an action map never enabled | the input actions contract ([input-ui-and-audio.md](input-ui-and-audio.md)) |
| Raycasts or collisions miss in one builder's piece | layers or the collision matrix differ | the layers and tags contract ([characters-physics-and-feel.md](characters-physics-and-feel.md)) |
| The capture tool can't reach a view or debug mode | hook names differ between pieces | the capture hooks in `PLAN.md` ([validation.md](validation.md)) |
| Two builders' edits collide | two writers for one scene, prefab or folder | the owners in `PLAN.md` ([project-hygiene.md](project-hygiene.md)) |
| A builder can't run Unity on the project | another Unity process has it open | the run queue ([agent-control.md](agent-control.md)) |
| Code that follows a topic file still fails or warns | the installed version isn't 6000.6, or a name written from memory | the version in `BRIEF.md` against the installed docs ([foundation.md](foundation.md)) |
