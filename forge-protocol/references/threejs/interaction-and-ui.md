# Three.js interaction and UI

API facts verified on r186 (2026-10-05). Check the installed version first; if it differs, confirm in the official docs or the installed source. The installed version wins.

Read this for games and interactive demos: the game loop, input, picking, physics, UI, audio, loading and comfort. Camera rigs and controls are in [camera-and-animation.md](camera-and-animation.md).

## Contents

- Loop and app structure
- Input mapping
- Picking and raycasting
- Physics hookup
- UI overlays and in-world text
- Audio hooks
- Loading, errors and resilience
- Accessibility and comfort
- Symptom → cause

## Loop and app structure

**Goal.** Play feels identical on every display, and every screen of the app is a finished, separate state.

**Build.**
- Run one loop: read input, advance the simulation in fixed steps from an accumulator (with a cap on steps per frame), interpolate render transforms by the leftover fraction, render, then update the UI.
- Treat screens as states (boot and loading, title or menu, play, pause, results), each owning its scene objects, listeners and UI.
- On leaving a state, dispose of its geometries, materials, textures and render targets, and remove its listeners.
- Pause stops simulation time, and a hidden tab pauses play.

**Critic checks.** PASS when every captured state (loading, menu, play, pause, results) looks finished and distinct. FAIL signs: placeholder menus, overlapping states, a paused game that still moves.

**API facts** (check the installed version):
- On the WebGPU renderer, `setAnimationLoop()` awaits `init()` before the first frame (verified on r186).

## Input mapping

**Goal.** Players act through named actions that behave the same on every device, and every action gets an immediate visible response.

**Build.**
- Map keys, buttons, pointer and touch to actions ("jump", "fire", a movement axis) in one table, and read actions in the simulation step. Buffer presses, so a quick tap between two steps isn't lost.
- Bind movement to physical key positions so other keyboard layouts work.
- Handle mouse, pen and touch together through pointer events, and stop browser scrolling and zooming on the canvas only.
- On touch screens, add an on-screen stick and buttons sized for fingers (WCAG suggests at least 44 by 44 CSS pixels).
- On gamepads, apply dead zones and response curves.
- Clear held input on focus loss and on pointer-lock exit, and allow rebinding.

**Critic checks.** PASS when frames captured after a scripted input show its response within a frame or two: movement, a highlight, an effect. FAIL signs: late or missing responses, an input that works on one device only.

## Picking and raycasting

**Goal.** The pointer always selects what is under it, quickly, with clear feedback.

**Choose.** Ray tests against pickable objects for ordinary scenes; simplified proxy meshes for complex models; a spatial acceleration library (three-mesh-bvh is one example) for dense meshes; GPU picking, which renders object ids and reads the pixel under the pointer, for huge counts or shader-displaced surfaces.

**Build.** Pick only on a dedicated layer or list, raycast hover on pointer moves rather than every frame, and show feedback: a hover highlight, a changed pointer icon, a selection state, and a tooltip where it helps. For ground points and heights on terrain displaced in the shader, intersect the ray with the terrain's CPU height copy instead of its mesh ([terrain.md](terrain.md), Collision and height parity).

**Critic checks.** PASS when hovered and selected objects show a clear highlight, and the highlighted object is the one under the pointer. FAIL signs: no feedback, or the wrong object highlighted.

**API facts** (check the installed version):
- `Raycaster` tests only objects that share a layer with `raycaster.layers`, and `setFromCamera()` takes normalized device coordinates from −1 to 1, which you compute from the canvas rectangle (verified on r186).
- `Mesh.raycast()` applies morph targets and skinning on the CPU but not `displacementMap` or `positionNode`, so pick displaced surfaces through proxies or GPU picking (verified on r186).
- Hits on an `InstancedMesh` carry `instanceId` and hits on a `BatchedMesh` carry `batchId`; `raycaster.params.Points.threshold` defaults to 1 world unit (verified on r186).

## Physics hookup

**Goal.** Objects behave physically and look attached to their colliders: nothing tunnels, jitters at rest, or hovers.

**Choose.**
- A few analytic collisions (ballistic motion, boxes on a grid) when the game needs little more.
- A rigid-body engine, for example Rapier, cannon-es or Jolt compiled to WebAssembly, for stacks, joints, ragdolls and vehicles.
- A kinematic character controller (a capsule that handles steps and slopes) for players, instead of a free dynamic body.
- A raycast-wheel vehicle controller for driving.

**Build.**
1. Step physics at a fixed rate from an accumulator, in meters, with real gravity and plausible masses.
2. Let physics own the transforms, and render poses interpolated between the last two physics states.
3. Approximate visuals with primitive or convex colliders, keeping triangle-mesh colliders for static level geometry, and build terrain colliders as heightfields from the height data the terrain renders ([terrain.md](terrain.md), Collision and height parity).
4. Let resting bodies sleep, and enable continuous collision for small, fast objects.
5. Draw colliders behind a debug switch, and send collision events to effects and audio.

**Watch for.** Visuals offset from their colliders (floating or sinking), raw physics poses rendered at a different rate from the step (jitter), centimeter-scale worlds that feel floaty, and dynamic bodies with triangle-mesh colliders.

**Critic checks.** PASS when resting objects sit flush on surfaces with contact shadows and no jitter across consecutive frames, fast objects never pass through thin walls, and a captured collider debug view matches the visuals. FAIL signs: floating, sinking, tunneling, jittering stacks.

**Start here** (adjust to the goal and the speeds involved): a 60 Hz fixed step, with at most a few steps per frame.

## UI overlays and in-world text

**Goal.** UI is crisp, legible at capture size and accessible, and never hides what the viewer came to see.

**Choose.**
- HTML and CSS over the canvas for HUDs, menus and settings: crisp at any pixel ratio, accessible, and easy to lay out.
- DOM labels anchored to projected world positions for markers and annotations.
- Signed-distance-field text meshes (troika-three-text is one example) for text that lives in the 3D world.
- Extruded text geometry only for hero titles and logos.
- Canvas textures for signs and in-world screens, redrawn only when their content changes.

**Build.** Respect safe areas and aspect ratios. Use a type scale with strong contrast (4.5:1 for body text, as in the web-ui pack of [criteria-packs.md](../criteria-packs.md)). Hide or fade labels when geometry occludes them, declutter overlaps, and pin off-screen markers to the screen edge. Keep UI out of tone mapping, bloom and grading. Let overlay elements take pointer input only where they should.

**Critic checks.** PASS when HUD text is crisp and legible at capture size, labels sit beside their objects and hide when occluded, and nothing covers the focal subject. FAIL signs: blurry or bloomed UI, labels showing through walls, cluttered overlaps, a HUD over the subject.

**API facts** (check the installed version):
- `CSS2DRenderer` positions DOM labels over the canvas. It needs its own `render(scene, camera)` call and `setSize()` on resize, and it never hides labels behind geometry, so test occlusion yourself (verified on r186).
- `TextGeometry` defaults to `size` 100 and `depth` 50 in scene units; `height` became `depth` in r163, and r186 ignores the old name (verified on r186).

## Audio hooks

**Goal.** Sound confirms actions and places events in space, and it can be verified even though captures are silent.

**Build.**
- Start or resume audio on the first user gesture.
- Attach one listener to the camera. Give world events positional sources with distance falloff tuned to the scene's scale, and keep music and UI sounds non-positional.
- Vary repeated sounds with several samples and small seeded changes in pitch and volume.
- Mix in groups (music, effects, UI, ambience), duck music under key sounds, and offer mute and volume controls.
- Log every sound trigger with its time and source, so audio can be checked from the log or by the user; the handback says which check was used.

**API facts** (check the installed version):
- three.js audio shares one native context through `AudioContext.getContext()` and never resumes it for you; call its `resume()` inside the first click, tap or key press (verified on r186).
- `PositionalAudio` uses an HRTF panner; tune `setRefDistance()`, `setRolloffFactor()` and `setMaxDistance()` to the scene's scale (verified on r186).

## Loading, errors and resilience

**Goal.** The app never shows a silent black canvas: it reports progress, explains failures, and recovers when it can.

**Build.**
- A loading screen with real progress and a ready signal, lifted only once assets are in and shaders are compiled ([assets-and-performance.md](assets-and-performance.md)).
- Clear messages on unsupported devices, with a lower tier where one exists.
- Asset failures retried or reported; placeholders never reach a capture.
- On context or device loss, a message, then a rebuild of the renderer and GPU resources, or a reload.

**API facts** (check the installed version):
- `WebGPURenderer` calls `onDeviceLost(info)` on device loss, and on context loss in its WebGL fallback; by default it logs an error, and rendering stops; `WebGLRenderer` handles context loss itself and offers `forceContextLoss()` for testing recovery (verified on r186).

## Accessibility and comfort

**Goal.** More people can play comfortably, and nothing in the build risks harm.

**Build.** Honor the system's reduced-motion setting with less shake, head bob and motion blur and gentler camera moves. Avoid flashing more than three times a second (WCAG). Never carry meaning by color alone. Allow remapping, adjustable text size and pausing anywhere, and caption important sounds.

**Critic checks.** PASS when important states can be told apart without color (icons, shapes or labels accompany it), and no captured sequence shows rapid full-screen flashing. FAIL signs: cues that rely on red versus green alone, strobing.

## Symptom → cause

| Symptom | Likely cause | First check |
| --- | --- | --- |
| Game speed differs between displays | per-frame updates instead of fixed steps | the frame-rate pair ([validation.md](validation.md)) |
| Moving objects stutter | physics poses rendered without interpolation | the rendered pose against the last two physics states |
| Quick taps get lost | actions read only at render time, with no buffering | a scripted tap shorter than one step |
| Keys stay held after switching windows | held input not cleared on focus loss | the input state after a blur |
| The wrong object gets picked | coordinates from the window instead of the canvas, or picking on every layer | the pointer's normalized coordinates and `raycaster.layers` |
| Clicks miss displaced terrain | raycasts against undisplaced CPU geometry | the hit point against the terrain's CPU height copy ([terrain.md](terrain.md)) |
| Objects float or sink | colliders offset from the visuals | the collider debug view over the visuals |
| Fast objects pass through walls | no continuous collision, or a step too coarse | continuous collision on fast bodies, and the step size |
| Stacks jitter | too few solver iterations, or raw poses rendered | solver iterations and render interpolation |
| UI looks blurry or glows | UI drawn inside the post chain | where the UI is drawn relative to the output pass |
| Labels show through walls | DOM labels with no occlusion test | the occlusion test for each label |
| No sound | audio context never resumed on a user gesture | the audio context's state after the first click |
| Black canvas after a GPU reset | no context or device loss handling | `onDeviceLost`, and a forced context loss |
| Memory grows with each scene change | the old state never disposed of | renderer memory counters before and after a scene change |
