# Unity characters, physics and feel: controllers, physics settings, navigation, hit-stop, feedback and respawn

API facts verified on Unity 6.6 (6000.6.4f1, 2026-10-06). Check the project's Unity version first (ProjectSettings/ProjectVersion.txt); if it differs, confirm in that version's official docs or the installed packages. The installed version wins.

Read when the build has a player or NPCs that move, physics bodies, vehicles, or game feel to tune: controllers, collisions, navigation, jumps, hits, knockback and respawn. Camera rigs and screen shake are in [camera-and-animation.md](camera-and-animation.md); input actions are in [input-ui-and-audio.md](input-ui-and-audio.md); the frame loop and fixed timestep are in [foundation.md](foundation.md); 2D bodies are in [2d.md](2d.md).

## Contents

- CharacterController or Rigidbody
- Your own controller, not Starter Assets
- Physics settings and the fixed step
- Interpolation and collision detection
- Layers, the collision matrix and Physics Materials
- Navigation with AI Navigation
- Movement feel: buffering, coyote time and acceleration
- Hit-stop and time scale
- Layered feedback and screen shake
- Checkpoints and respawn
- Symptom → cause

## CharacterController or Rigidbody

**Goal.** Each mover uses the body that gives the feel and the physics the game needs, and nothing moves one body two ways.

**Choose.**
- **CharacterController** for walkers (players and NPCs that walk, run and jump): an upright capsule moved by `Move`, stopped by collisions, sliding along walls, climbing steps up to Step Offset and slopes up to Slope Limit. It applies no gravity, ignores forces and doesn't push rigidbodies unless your `OnControllerColliderHit` does it.
- **A dynamic Rigidbody** for vehicles, rolling balls, physics props, ragdolls and anything pushed by forces, driven by forces and velocity changes in `FixedUpdate`.
- **A kinematic Rigidbody** for moving platforms, doors and lifts: moved with `MovePosition` and `MoveRotation`, it pushes dynamic bodies and isn't pushed back.
- **Vehicles:** a Rigidbody with raycast suspension for an arcade feel, or WheelColliders for a simulation feel.

**Build.**
1. Size the capsule from the character: about 2 m tall for a person, with the pivot and center matching the mesh.
2. For a CharacterController, add gravity to a stored vertical velocity yourself, and confirm grounding with a short downward sphere cast as well as `isGrounded`, which reflects only the last `Move`.
3. Read input every frame and keep the intent; apply Rigidbody forces in `FixedUpdate` ([foundation.md](foundation.md), Frame loop, fixed timestep and time scale).
4. Give moving platforms a kinematic Rigidbody, and carry riders by the platform's per-step delta.

**Watch for.** A CharacterController and a Rigidbody on one object fight each other. `com.unity.charactercontroller` in the Package Manager is a different thing: a controller for Entities, not the built-in component. Setting `transform.position` on a body that physics owns can be overwritten on the next step (see Checkpoints and respawn).

**Critic checks.** PASS when walkers climb steps and slopes without jitter, slide along walls instead of sticking, and stand flush on the ground, and vehicles and props respond to slopes, hits and forces. FAIL signs: a character walking into walls or floating above steps; a crate that ignores a push; a car that slides like a puck.

**Start here** (adjust to the goal): Skin Width about a tenth of the capsule radius, and Step Offset between 0.1 and 0.4 m for a 2 m person, as Unity's own guidance suggests.

**API facts** (check the installed version):
- A CharacterController doesn't react to forces or push rigidbodies on its own, and `CharacterController.Move` applies no gravity (verified on 6000.6).
- With `isKinematic` on, forces, collisions and joints no longer move the body, but it still pushes other rigidbodies (verified on 6000.6).
- The `com.unity.charactercontroller` package (1.4.5 on 6000.6) is a character controller for Entities (verified on 6000.6).

## Your own controller, not Starter Assets

**Goal.** The player controller is the project's own code: small, fully understood, safe to commit and built against 6.6.

**Choose.**
- **Your own controller** by default: a CharacterController, Input System actions and a Cinemachine third-person rig.
- **Unity's Starter Assets** (free first- and third-person controllers on the Asset Store, built on the CharacterController, the Input System and Cinemachine) only as the Asset Store policy in [assets-and-import.md](assets-and-import.md) (Asset Store and Mixamo files) allows.

**Build.**
1. Write the controller from the sections below; the simple player controller in the Cinemachine samples is a Unity Companion License sample you may study, with a ledger row if you import it ([assets-and-import.md](assets-and-import.md)).
2. If Starter Assets do come in under that policy, expect Cinemachine 2 code (6.6 upgrades it to Cinemachine 3), input errors and pink materials on first import, and fix each before trusting it.

**Watch for.** The newer Starter Assets package bundles a UI Toolkit mobile joystick; remove what the targets don't use. An update can overwrite local fixes; record the version imported.

## Physics settings and the fixed step

**Goal.** The simulation is stable, runs at a known rate, and behaves the same at any frame rate.

**Build.**
1. Keep the fixed timestep explicit: the templates ship 0.02 s (50 Hz); raise the rate for fast action and vehicles, knowing the cost grows with it.
2. Maximum Allowed Timestep caps how much physics catches up after a slow frame (the templates ship a third of a second), so a stall slows the game instead of spiraling.
3. Keep Simulation Mode at Fixed Update, units in meters, gravity at −9.81, and masses plausible in kilograms; a world built at the wrong scale feels floaty.
4. Raise Default Solver Iterations for stacks, joints and ragdolls that won't settle, and leave Default Contact Offset and Bounce Threshold near their defaults, since very small values jitter.
5. Auto Sync Transforms is off by default: after moving transforms in `Update` or `LateUpdate`, call `Physics.SyncTransforms` before a raycast in the same frame.

**Watch for.** Physics in `Update` makes speed depend on frame rate. Time scale also scales the fixed step, because `fixedDeltaTime` is measured in game time (see Hit-stop and time scale).

**Critic checks.** PASS when stacks and resting props stay still across consecutive frames, and the same scripted motion covers the same distance whether the game runs fast or slow ([validation.md](validation.md)). FAIL signs: jittering stacks; props creeping at rest; a character faster at higher frame rates.

**Start here** (adjust to the goal): a fixed timestep of 1/60 s for action games.

**API facts** (check the installed version):
- Simulation Mode is Fixed Update (the default, right after `FixedUpdate`), Update, or Script (`Physics.Simulate`) (verified on 6000.6).
- `Time.fixedDeltaTime` is measured in game time, so a time scale of 0.5 halves the real-time physics rate; its documented default is 0.02 s (verified on 6000.6).
- Auto Sync Transforms is off by default; `Physics.SyncTransforms` flushes transform changes before a physics query and isn't needed in `FixedUpdate` (verified on 6000.6).
- Default Contact Offset is 0.01 by default, and values near zero cause jitter (verified on 6000.6).

## Interpolation and collision detection

**Goal.** Bodies the camera follows render smoothly between physics steps, and fast bodies never pass through walls.

**Build.**
1. Turn on Interpolate for the player's Rigidbody and anything the camera follows; leave it off elsewhere.
2. Once interpolation is on, physics owns the transform: move with forces, `MovePosition` or `linearVelocity`, and teleport with `Rigidbody.position`, never by writing the transform.
3. Set collision detection per body: Discrete by default; Continuous for fast bodies against static geometry; Continuous Dynamic for fast bodies against other fast bodies (the slowest mode); Continuous Speculative for kinematic and spinning bodies (cheaper, though very fast bodies can still tunnel).
4. Use raycasts or sphere casts per fixed step for small, very fast projectiles instead of rigidbodies.
5. Set `linearVelocity` for instant changes such as a jump, not every step, and use `linearDamping` for drag; the old `velocity` and `drag` names are in the drift table in [foundation.md](foundation.md).

**Watch for.** Interpolation on everything costs time and can make attached objects lag a step. A camera parented directly to a physics body jitters; let Cinemachine follow it.

**Critic checks.** PASS when the followed body moves smoothly in consecutive frames and nothing passes through thin walls or floors. FAIL signs: a stuttering player at steady speed; bullets or balls through walls; a car dropping through the road at speed.

**API facts** (check the installed version):
- Interpolation is off by default and recommended for the main character and camera-followed bodies only; with it on, direct transform changes need `Physics.SyncTransforms` or are ignored (verified on 6000.6).
- Continuous covers static geometry, Continuous Dynamic also covers other continuous bodies and is the slowest, and Continuous Speculative works for kinematic bodies but can still tunnel (verified on 6000.6).
- `linearVelocity` is in world space and isn't meant to be set every step; `linearDamping` scales velocity by one minus damping times the step (verified on 6000.6).
- `Rigidbody.position` teleports the body, applied after the next physics step, while `MovePosition` moves it with interpolation (verified on 6000.6).

## Layers, the collision matrix and Physics Materials

**Goal.** Things collide only with what they should, triggers fire reliably, and surfaces feel like their material.

**Build.**
1. Make layers for the player, enemies, projectiles, the environment, trigger zones and camera-only geometry, and set which pairs collide in the Layer Collision Matrix (Project Settings > Physics). Use a collider's Layer Overrides (Include Layers, Exclude Layers, Layer Override Priority) for exceptions.
2. Give every raycast and overlap query a layer mask, and keep the camera's obstacle layers tight ([camera-and-animation.md](camera-and-animation.md)).
3. Triggers fire only when one of the two objects has a physics body; give pickups or the player a kinematic Rigidbody, and test that a CharacterController player fires every trigger.
4. Physics Materials: dynamic and static friction, bounciness, and how each combines (Average, Minimum, Maximum, Multiply). Ice has low friction, rubber high bounce; a player capsule with zero friction and a Minimum friction combine slides off walls instead of sticking mid-jump.

**Watch for.** Everything left on the Default layer collides with everything, including the shooter's own projectiles.

**Critic checks.** PASS when pickups trigger on contact, the player slides along walls rather than sticking, projectiles ignore their shooter, and materials answer as the brief describes (ice slides, rubber bounces). FAIL signs: a player stuck to a wall mid-air; bullets stopping at the gun; pickups that never trigger.

**API facts** (check the installed version):
- A trigger fires only when at least one of the two objects carries a physics body, either a Rigidbody or an ArticulationBody (verified on 6000.6).
- A Physics Material sets dynamic friction, static friction and bounciness, combined by Average, Minimum, Maximum or Multiply (verified on 6000.6).
- Colliders carry Layer Overrides (Include Layers, Exclude Layers, Layer Override Priority) on top of the Layer Collision Matrix in the Physics settings (verified on 6000.6).

## Navigation with AI Navigation

**Goal.** NPCs find paths over the walkable world, start on it, avoid each other, and move with believable speed, turns and stops.

**Build.**
1. Use the AI Navigation package (2.0.14 on 6.6; the URP template bundled with 6000.6.4f1 lists it, so check `Packages/manifest.json`). Add a NavMesh Surface (Add Component > Navigation > NavMesh Surface) for each agent type on a root object, choose Use Geometry (Physics Colliders matches what characters stand on), Collect Objects and Include Layers, then Bake; the result is saved as an asset.
2. Mark exceptions with NavMesh Modifier (Remove Object, or Override Area for costs such as water and roads) and NavMesh Modifier Volume for regions.
3. Connect gaps, ledges and ladders with NavMesh Link (Width, Bidirectional, Area Type), or turn on Generate Links on the surface.
4. Tune each NavMesh Agent: the Agent Type that matches its surface, speed, angular speed, acceleration, Stopping Distance, Auto Braking (off for patrols through waypoints), Obstacle Avoidance quality and Area Mask.
5. Carve doors and crates with NavMesh Obstacle (Carve Only Stationary by default), and rebuild procedural levels at runtime with `NavMeshSurface.BuildNavMesh` before enabling agents.
6. Before `SetDestination`, place agents on the mesh: snap the spawn point with `NavMesh.SamplePosition`, move them with `Warp`, and check `isOnNavMesh`.
7. Drive animation from the agent's velocity, or let root motion move the body and sync the agent ([camera-and-animation.md](camera-and-animation.md), Root motion and Humanoid retargeting).

**Watch for.** The agent-not-on-NavMesh trap: no baked or loaded NavMesh (a disabled surface loads none), an agent type that differs from the surface's, a spawn point off the mesh, or agents enabled before a runtime bake. The old Navigation window and Navigation Static are gone ([foundation.md](foundation.md)).

**Critic checks.** PASS when NPCs walk around obstacles without clipping walls, stop at a sensible distance, turn before moving, and their feet match their speed. FAIL signs: NPCs frozen at spawn; sliding sideways; walking through doors that look shut; bunching into a single file that jitters.

**Diagnose.**
- NPCs never move and the console logs the SetDestination error → no NavMesh under them, or a mismatched agent type.
- NPCs take absurd detours → area costs or a missing link.

**API facts** (check the installed version):
- Calling `SetDestination` on an agent that isn't on a NavMesh logs "\"SetDestination\" can only be called on an active agent that has been placed on a NavMesh.", and agents too far from the mesh fail with "Failed to create agent because it is not close enough to the NavMesh" (verified on 6000.6).
- NavMesh Surface bakes per agent type from Render Meshes or Physics Colliders (both include terrains), excludes objects with a NavMesh Agent or NavMesh Obstacle, and stores the result in an asset (verified on 6000.6).
- `NavMesh.SamplePosition` finds the nearest point on the mesh within a distance, `NavMeshAgent.Warp` moves an agent there, and `isOnNavMesh` reports whether it is bound to a mesh (verified on 6000.6).
- `NavMeshSurface.BuildNavMesh` rebuilds a surface at runtime in AI Navigation 2.0.14 (verified on 6000.6).

## Movement feel: buffering, coyote time and acceleration

**Goal.** Controls feel responsive and forgiving: no press is lost, ledges forgive a late jump, and movement has weight without lag.

**Build.**
1. Buffer presses: record the time of each jump or attack press when the action fires (the Input System processes events in the dynamic update by default), and consume it within a short window once the move becomes possible.
2. Coyote time: allow a jump for a short window after the character leaves the ground.
3. Variable jump height: cut upward velocity when the button is released, fall faster than you rise, and hang briefly at the apex.
4. Acceleration and deceleration from curves, with separate ground and air values, a turnaround boost, and air control below ground control.
5. Move relative to the camera: project its forward onto the ground plane. On slopes, move along the ground normal and stay snapped to the ground going downhill.
6. Keep every tuning value in one data asset or the Inspector, and report the values in the handback.

**Watch for.** Reading a "pressed this frame" state inside `FixedUpdate` misses presses on frames with no fixed step; buffer in `Update` and consume in `FixedUpdate`. Input read as raw values for movement but buffered for actions keeps both responsive.

**Critic checks.** PASS when frames after a scripted input show a response within a frame or two, a scripted jump pressed just after leaving a ledge still jumps, and a short tap gives a lower jump than a held press. FAIL signs: no response to a tap between fixed steps; a late jump that fails; floaty, uniform jumps.

**Start here** (adjust to the goal): a jump buffer of about 0.1 to 0.15 s and coyote time of about 0.1 s.

**API facts** (check the installed version):
- The Input System's Update Mode is Process Events In Dynamic Update by default, with Fixed Update and Manual as the alternatives (verified on 6000.6).

## Hit-stop and time scale

**Goal.** Heavy impacts land with a brief freeze that sells weight, without breaking physics, audio, UI or the next frame.

**Choose.**
- **Global hit-stop:** set `Time.timeScale` to zero or near it for a few frames, timed in unscaled time, then restore it. Simple, and it freezes everything that uses scaled time.
- **Local hit-stop:** freeze only the attacker and the target (pause their animators, store and restore their velocities), so the world keeps moving; better for crowds and multiplayer.

**Build.**
1. Give time scale one owner (pause, hit-stop and slow motion all ask it), and take the longest pending stop instead of stacking them.
2. Time the stop with unscaled time (`Time.unscaledDeltaTime`, `WaitForSecondsRealtime`), never with `WaitForSeconds`, which stops at a scale of zero, and never with a `System.Threading` timer or `Task.Delay`, which fail on the Web ([foundation.md](foundation.md), Async code).
3. Decide what keeps running: UI and menus on unscaled time; the camera's input controller with Ignore Time Scale; animators that must move with Unscaled Time; effects with Delta Time set to Unscaled when they should play through the stop ([effects.md](effects.md)).
4. Decide what audio does (keep playing, dip pitch, or pause through `AudioListener.pause`), and listen to a build to confirm it ([input-ui-and-audio.md](input-ui-and-audio.md)).
5. Leave `fixedDeltaTime` alone during a short stop; physics pauses with time and resumes cleanly.

**Watch for.** A restore that waits on scaled time never fires, and the game stays frozen. Time scale changes take effect from the next frame.

**Critic checks.** PASS when frames around a heavy hit show a hold of a few frames and then motion resuming at full speed, while UI and camera stay responsive. FAIL signs: a permanent freeze; a stop on every small hit; motion that never returns to full speed.

**Start here** (adjust to the goal): 50 to 120 ms of stop for heavy hits, and none for light ones.

**API facts** (check the installed version):
- At a time scale of zero, `FixedUpdate` isn't called and coroutines waiting on `WaitForSeconds` don't resume; a new time scale takes effect on the following frames (verified on 6000.6).
- `Time.unscaledDeltaTime` ignores the time scale (verified on 6000.6).
- An Animator in Unscaled Time mode animates at full speed regardless of the time scale (verified on 6000.6).

## Layered feedback and screen shake

**Goal.** Every important action answers on several channels at once (sound, particles, animation, camera and UI), all on the same frame and scaled to the event.

**Build.**
1. Write a feedback table per event before tuning: for a heavy hit, a short hit-stop, a flash on the target, knockback, sparks at the contact, an impact sound from a randomized container, a camera impulse, and a damage readout.
2. Fire every channel from one event dispatched on the impact frame, with the contact point, normal and strength.
3. Shake the camera through Cinemachine Impulse ([camera-and-animation.md](camera-and-animation.md), Impulse for screen shake), never by moving the player.
4. Scale with strength: small events stay small, and only the biggest use every channel.
5. Give the player strength settings for shake and flashes, honor reduced motion, and never flash more than three times a second.
6. Log each feedback trigger with its time and event, so sound and haptics can be checked even though captures are silent.

**Critic checks.** PASS when frames show several responses (flash, particles, pose, camera) starting within a frame or two of each event, the log shows the matching sounds, and feedback scales with the event. FAIL signs: a hit with no response; every hit at maximum; strobing flashes.

## Checkpoints and respawn

**Goal.** Failing returns the player quickly to a fair state, with the camera already framed and nothing left over from the last attempt.

**Build.**
1. Checkpoints save a respawn pose (position, rotation, camera state) and the minimal game state they restore.
2. Teleport the right way for each body: disable a CharacterController, set the position, enable it again (or set it and call `Physics.SyncTransforms`); for a Rigidbody, set `position` and `rotation` and zero its linear and angular velocity; for a NavMesh Agent, use `Warp`.
3. Tell Cinemachine about the jump (`OnTargetObjectWarped`, or `ForceCameraPosition` on the camera), so it cuts instead of swooping across the level.
4. Reset hazards, enemies, pooled effects and time scale near the checkpoint, and fade on unscaled time.
5. When reloading the scene instead, reset statics yourself; Play mode keeps them without a domain reload ([foundation.md](foundation.md)).

**Watch for.** A CharacterController snapping back to where it died. A body that respawns still carrying its old velocity. A camera blending from the death spot. A time scale left at zero by a hit-stop during death.

**Critic checks.** PASS when frames after a respawn show the player at the checkpoint, the camera framed at once, no leftover effects, and the restart within the brief's time. FAIL signs: a camera swoop; the player at the death spot; leftover particles or enemies; a frozen game.

**API facts** (check the installed version):
- Cinemachine cameras provide `OnTargetObjectWarped` and `ForceCameraPosition`, and `CinemachineCore.OnTargetObjectWarped` notifies every camera that follows a warped target (verified on 6000.6).

## Symptom → cause

| Symptom | Likely cause | First check |
| --- | --- | --- |
| Character walks into walls or floats over steps | capsule sized wrong, or Step Offset and Skin Width off | the capsule against the mesh, and the controller settings |
| A CharacterController snaps back after a teleport | position set while the controller was enabled | the teleport code: disable, move, enable |
| A crate ignores the player | CharacterController without push code | `OnControllerColliderHit` |
| Speed differs between displays | movement in `Update` without delta time, or physics in `Update` | one scripted run timed at a high and a low frame rate ([validation.md](validation.md)) |
| The followed body stutters | no interpolation, or the transform written directly | Interpolate on the body, and how it is moved |
| Fast objects pass through walls | Discrete collision detection on a fast body | the body's collision detection mode |
| Stacks jitter or creep | too few solver iterations, or a tiny contact offset | Default Solver Iterations and Default Contact Offset |
| Bullets hit the shooter | the projectile layer collides with the player layer | the Layer Collision Matrix |
| Player sticks to walls mid-jump | friction on the player capsule | the capsule's Physics Material and friction combine |
| Triggers never fire | neither object has a physics body | a kinematic Rigidbody on one side |
| NPCs frozen with a SetDestination error | no NavMesh under them, a disabled surface, or another agent type | the surface's bake, its agent type and the spawn point |
| NPCs slide sideways | animation not driven by agent velocity | the blend-tree parameters against the agent velocity |
| Taps get lost | presses read in `FixedUpdate` | where the press is buffered |
| Game freezes after a hit | restore timed with scaled time | `WaitForSeconds` against unscaled timing |
| Camera swoops after respawn | Cinemachine not told about the warp | `OnTargetObjectWarped` or `ForceCameraPosition` |
| Imported Starter Assets fail to compile | Cinemachine 2 code or input settings | the console right after the import |
