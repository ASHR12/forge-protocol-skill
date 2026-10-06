# Unity genres and scope: first projects, starting kits, finish lines and scope traps

API facts verified on Unity 6.6 (6000.6.4f1, 2026-10-06). Check the project's Unity version first (ProjectSettings/ProjectVersion.txt); if it differs, confirm in that version's official docs or the installed packages. The installed version wins.

Read when the goal is a Unity game, at Rule 0: to pick a first project that agents can finish, its template and packages, and the finish line the bar grows from. The craft lives in the topic files this one points to; [router.md](router.md) has the build order, and [setup.md](setup.md) the template choice.

## Contents

- Scope rules for a first game
- What agents build well
- Third-person explorer
- 2D platformer
- Top-down arena
- Physics puzzle
- Arcade racer
- Other small first projects
- Scope traps
- Symptom → cause

## Scope rules for a first game

**Goal.** A first game that is small enough to finish and polish inside the mode's budget, and complete enough to feel like a game rather than a demo.

**Build.**
1. One core verb (explore, jump, shoot, push, drive), one environment, and a few minutes of content.
2. A full loop around it: title screen, play, pause with settings, a fail state with a quick retry, and an ending or a score screen.
3. Feedback on every interaction: a visual response, a sound and, where it fits, a camera response.
4. Content generated from rules and data where possible (arenas, levels, scatter), so a fix lands everywhere at once.
5. A cut list in `PLAN.md`: what to drop first if the budget runs short. Cut content before cutting the loop or the feedback.

**Start here** (adjust to the goal): three to five minutes of play, and one level or arena polished before a second is started.

## What agents build well

**Goal.** The project's hardest parts fall where agents are strong.

**Choose.**
- **Strong:** systems written in code (movement, physics, rules, spawning, scoring), procedural or data-driven levels, terrain and scatter from rules, UI built as text (UI Toolkit), camera rigs, and anything an editor script can rebuild.
- **Workable with care:** imported characters with ready-made animations, modular kits assembled into levels, effects built from particles, and lighting tuned through captures.
- **Weak:** hand-keyed character animation, bespoke hero art made inside Unity, hand-sculpted terrain, cutscenes that need an animator's timing, and anything that relies on hand-editing scene files.

**Build.**
1. Lean the genre choice and the art direction toward the strong column: a stylized look from clean shapes and good light beats a realistic one that needs hand-made assets.
2. Default to CC0 art (Kenney, Quaternius, Poly Haven, ambientCG), the user's own assets and code the agents write. Asset Store packages (Unity's Starter Assets included) and Mixamo animations follow the policy in [assets-and-import.md](assets-and-import.md) (Asset Store and Mixamo files).

## Third-person explorer

**Goal.** Walk or run through one outdoor space toward landmarks, collect things, and reach an ending.

**Choose.** Universal 3D. Add Cinemachine (a core package) for the follow camera, Terrain Tools or ProBuilder from the 3D World Building feature set for the ground and blockout, and AI Navigation (already in the template) for any wandering creatures. Timeline only if there is an intro shot.

**Build.** A character controller with acceleration and a camera-relative move ([characters-physics-and-feel.md](characters-physics-and-feel.md)); a follow camera that avoids walls ([camera-and-animation.md](camera-and-animation.md)); terrain and scatter from rules ([terrain-and-nature.md](terrain-and-nature.md)); a sky and one sun ([sky-weather-and-water.md](sky-weather-and-water.md)); landmarks that pull the player forward ([levels-and-geometry.md](levels-and-geometry.md)); collectibles with pickup feedback; footsteps that vary by surface; pause and settings; an ending.

**Watch for.** An open world with nothing in it. A smaller space with three dense, distinct areas beats a large empty one.

**Critic checks.** PASS when the camera stays clear of walls and terrain across the walkthrough frames, a landmark reads in the design view from the start point, feet stay planted on slopes, and every pickup frame shows a visible response. FAIL signs: the camera inside geometry; a horizon with nothing to aim for; floating or sinking feet; collectibles that vanish with no effect.

**Start here** (adjust to the goal): an area about 200 m across, and three landmarks visible from the start.

## 2D platformer

**Goal.** Run and jump through one short level of hand-tuned challenges, with tight controls and instant retries.

**Choose.** Universal 2D, whose template already carries the 2D sprite, tilemap, animation and importer packages, and URP's Pixel Perfect Camera for pixel art; never the standalone 2D Pixel Perfect package, a Built-in-only component ([2d.md](2d.md)). Add Cinemachine for a follow camera confined to the level.

**Build.** Tilemap levels laid out from data or a generator ([2d.md](2d.md)); a controller with coyote time, a jump buffer, variable jump height and quick acceleration ([characters-physics-and-feel.md](characters-physics-and-feel.md)); landing squash, dust and screen shake on hits; parallax layers; checkpoints; death and respawn in under a second.

**Watch for.** Physics-driven jumping that feels floaty. A platformer's feel comes from a hand-written controller, not from default rigid-body physics.

**Critic checks.** PASS when sprites are crisp at native size, the player separates from the background at a glance, walkthrough frames show squash on landing and dust at take-off, and a death returns to a checkpoint within one second of game time. FAIL signs: blurry or shimmering pixels; the player lost against the tiles; jumps with no anticipation or landing; a long fade before every retry.

**Start here** (adjust to the goal): one level of 60 to 90 seconds for a skilled player, and a respawn under 1 s.

## Top-down arena

**Goal.** Survive waves of enemies in one arena, with readable threats and punchy hits.

**Choose.** Universal 3D, or Universal 2D for a sprite look. Input System actions for gamepad aiming and mouse aiming ([input-ui-and-audio.md](input-ui-and-audio.md)), Cinemachine for a top-down follow with impulse shake, and the built-in particle system for hits. VFX Graph needs compute shaders, so it never runs on WebGL 2; plan its particle-system fallback for the Web target ([effects.md](effects.md)).

**Build.** An arena generated from rules; enemies with a wind-up before each attack; hit-stop, a flash and knockback on every hit; a wave and score loop; game over with a one-press retry; a score screen.

**Watch for.** Enemy variety before feel: one enemy with great hit feedback beats five that feel the same.

**Critic checks.** PASS when each enemy's wind-up shows in the frames before it attacks, hit frames show a flash and knockback, the HUD stays legible over the action, and the frame after game over offers a retry. FAIL signs: attacks with no warning; hits that only change a number; a HUD lost against the floor; a dead end after losing.

**Start here** (adjust to the goal): three enemy types across five waves, and a hit-stop of a few frames at the capture step.

## Physics puzzle

**Goal.** Solve a handful of short puzzles by pushing, stacking or launching things, each with one clear goal.

**Choose.** Universal 3D, or Universal 2D for a flat look. ProBuilder for quick blockout pieces. The physics settings and layers are in [characters-physics-and-feel.md](characters-physics-and-feel.md).

**Build.** Puzzles defined as data (start state, goal condition), a fixed physics step so solutions repeat, a reset to the start state in one press, undo where it fits, a clear goal marker, and a satisfying sound and effect per material on impact.

**Watch for.** Puzzles that only the designer can read. Each one needs a single new idea, shown before it is tested.

**Critic checks.** PASS when the goal of each puzzle reads in its first still, bodies come to rest without jitter, the same scripted solution gives the same end state in two runs, and the solved state shows a clear success response. FAIL signs: an unclear goal; objects buzzing at rest or sinking into each other; a solution that works only sometimes.

**Start here** (adjust to the goal): five puzzles, each solvable in under a minute once understood.

## Arcade racer

**Goal.** Drive laps of one track against a timer or a ghost, with a strong sense of speed.

**Choose.** Universal 3D. Splines (pre-bundled with the editor) for the track and the racing line, Cinemachine for a chase camera with impulse, and either wheel colliders or a simpler raycast vehicle, decided in [characters-physics-and-feel.md](characters-physics-and-feel.md).

**Build.** A track mesh and barriers built along a spline ([levels-and-geometry.md](levels-and-geometry.md)); a car that drifts and boosts with visible feedback (trails, sparks, a camera field-of-view kick); a lap timer, a best-lap ghost, and a reset that puts the car back on the track.

**Watch for.** Realistic vehicle physics. Arcade handling tuned for fun is less code and feels better than a simulation.

**Critic checks.** PASS when the walkthrough frames show speed (trackside detail streaming past, a wider field of view at boost, trails), the car stays on the road surface, and the HUD shows lap and time legibly. FAIL signs: a car that hovers or clips into the road; speed you can't see in still frames; a camera that lags into scenery.

**Start here** (adjust to the goal): one track with a 45 to 60 second lap, and one car.

## Other small first projects

**Goal.** A goal that fits none of the genres above still gets a project agents can finish.

**Choose.**
- **Endless runner:** Universal 3D or 2D; generated track segments from a pool; the risk is sameness, so vary the segments by rule.
- **Tower defense, small:** Universal 3D; a grid, three tower types, waves along a path; the risk is a long balancing tail, so cap the waves.
- **Walking showcase:** Universal 3D, built for the look of one scene rather than play; route it through the showcase recipe in [router.md](router.md), and judge it with the 3D pack.
- **Card or board game:** Universal 2D with UI Toolkit; rules in code and tested; the risk is UI polish, so budget for it ([input-ui-and-audio.md](input-ui-and-audio.md)).

**Build.** Multiplayer, open worlds, branching dialogue and procedural quest systems are not first projects. Say so in the plan, propose a smaller cut, and add packages only from what the editor already ships unless the user agrees to more.

**API facts** (check the installed version):
- The 3D World Building feature set bundles ProBuilder, the FBX Exporter and Terrain Tools, and the editor ships ProBuilder 6.1.2, Terrain Tools 5.3.3 and Splines 2.9.1 as local package files (verified on 6000.6).
- The 2D feature set bundles 2D Animation, the Built-in-only 2D Pixel Perfect package, the PSD and Aseprite importers, Sprite, Sprite Shape, Tilemap with its extras, and 2D Tooling (verified on 6000.6).
- Cinemachine 6.6.0 and Timeline 6.6.0 ship with the editor as core packages, and the Gameplay and Storytelling feature set groups them with Visual Scripting (verified on 6000.6).

## Scope traps

**Goal.** The plan names the traps it is most likely to fall into, so the orchestrator can spot them between rounds.

**Build.** Pick the two or three traps below that fit this genre, write each into the risks section of `PLAN.md` with its fallback, and check them at every check-in.

**Watch for.**
- **Content before the loop:** levels and enemies built before the controls feel right. Lock the feel in a test room first.
- **Art before form:** detailed materials on a blockout that hasn't been judged. Follow the build order in [router.md](router.md).
- **Many systems at once:** inventory, crafting, dialogue and saving in a first game. Each one doubles the testing surface.
- **Realism by default:** physically simulated vehicles, ragdolls and realistic materials cost far more than stylized ones, and read worse when half-finished.
- **Menus last:** a game without title, pause, settings and retry looks unfinished in its first still. Build the loop shell early.
- **Platform creep:** add a target only when the brief needs it; each one adds builds, input and performance work.
- **Hand-made content an agent can't rebuild:** anything placed by hand in the Editor has to be rebuilt by hand. Generate it from scripts and data instead ([agent-control.md](agent-control.md)).

## Symptom → cause

| Symptom | Likely cause | First check |
| --- | --- | --- |
| Rounds pass but the game still feels unfinished | the loop shell (title, pause, retry, ending) was never built | the loop list in `PLAN.md` |
| The budget runs out with half the levels done | content started before the feel was locked | the cut list in `PLAN.md` |
| Controls feel floaty or slippery | default rigid-body physics where a hand-written controller was needed | the controller choice ([characters-physics-and-feel.md](characters-physics-and-feel.md)) |
| Hits feel weak | no hit-stop, flash or knockback | the feedback layers ([characters-physics-and-feel.md](characters-physics-and-feel.md), [effects.md](effects.md)) |
| A large world looks empty | the extent grew while the content stayed fixed | the area size against the landmark count |
| The Web build loses its effects | VFX Graph without a particle-system fallback on WebGL 2 | the effect's Web fallback ([effects.md](effects.md)) |
| Characters look stiff or slide | hand-keyed motion, or animation not matched to speed | the animation source ([camera-and-animation.md](camera-and-animation.md)) |
| A public repository holds Asset Store or Mixamo files | third-party files committed against their policy | the ignore rules, the ledger and the policy ([assets-and-import.md](assets-and-import.md)) |
| A fix in one level never reaches the others | levels placed by hand instead of generated | the level data and its generator ([levels-and-geometry.md](levels-and-geometry.md)) |
