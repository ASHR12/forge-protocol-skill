# Unity camera and animation: Cinemachine 3, rigs, Impulse, framing, Animator, retargeting, rigging, Timeline and splines

API facts verified on Unity 6.6 (6000.6.4f1, 2026-10-06). Check the project's Unity version first (ProjectSettings/ProjectVersion.txt); if it differs, confirm in that version's official docs or the installed packages. The installed version wins.

Read when a builder is responsible for what the camera shows or for anything that moves: rigs and shots, screen shake, character animation, IK and aiming, cutscenes, and motion along paths. Character controllers, physics and game feel are in [characters-physics-and-feel.md](characters-physics-and-feel.md); spline authoring basics are in [levels-and-geometry.md](levels-and-geometry.md); 2D cameras are in [2d.md](2d.md).

## Contents

- The camera contract
- Cinemachine 3 in Unity 6.6
- Follow, orbit and third-person rigs
- Collision and deoccluding
- Impulse for screen shake
- Framing and lens
- Animator, state machines and blend trees
- Root motion and Humanoid retargeting
- Animation Rigging: IK and aim
- Timeline for cutscenes
- Motion along splines
- Procedural motion and settling
- Symptom → cause

## The camera contract

**Goal.** Every camera mode works alone, producing a correct position and orientation, and one system at a time controls the Unity camera.

**Build.**
1. Write down, per mode, before any rig exists: the subject and how big it is, the lens (vertical field of view or focal length), the clipping planes, the positioning method (follow, orbit, path, mounted), the up direction, accepted input, spatial limits, and which system holds the camera during each transition.
2. Use one Unity Camera with a `CinemachineBrain`; make each mode its own `CinemachineCamera`. The live camera is the one with the highest priority, and the Brain blends between them.
3. While a Brain is in charge, no other script writes the main camera's transform; scripts adjust the Cinemachine cameras instead. Join modes together only once each of them gives a correct pose by itself.

**Watch for.** A script moving the main camera while the Brain also moves it gives a fight that looks like jitter. A near plane too close and a far plane too distant cost depth precision and cause flicker on distant surfaces.

**API facts** (check the installed version):
- The Brain's Update Method is Smart Update (recommended; each camera updates with its target), Fixed Update (in step with physics) or Late Update; its Blend Update Method is Late Update by default, with Fixed Update for blend judder when the cameras update in Fixed Update (verified on 6000.6).
- `Camera.fieldOfView` is the vertical field of view in degrees, and `focalLength` (millimeters) takes effect with `usePhysicalProperties` on (verified on 6000.6).

## Cinemachine 3 in Unity 6.6

**Goal.** Rigs are built on the Cinemachine that ships with 6.6, not on the Cinemachine 2 most tutorials show.

**Build.**
1. In 6.6, Cinemachine ships inside the Editor as a core package (version 6.6.0, the continuation of the 3.x line). Neither bundled template lists it, so add it from the Package Manager ([setup.md](setup.md)), then create rigs from GameObject > Cinemachine.
2. Code uses the `Unity.Cinemachine` namespace. A `CinemachineCamera` takes its behavior from separate components on the same GameObject: Position Control (`CinemachineFollow`, `CinemachineOrbitalFollow`, `CinemachineThirdPersonFollow`, `CinemachinePositionComposer`, `CinemachineSplineDolly`), Rotation Control (`CinemachineRotationComposer`, `CinemachinePanTilt`, `CinemachineHardLookAt`), Noise (`CinemachineBasicMultiChannelPerlin`), and extensions (`CinemachineDeoccluder`, `CinemachineDecollider`, `CinemachineImpulseListener`, `CinemachineConfiner3D`, `CinemachineFollowZoom`).
3. Cinemachine cameras never read input. A `CinemachineInputAxisController` maps Input System actions to the camera's axes, with gain and acceleration and deceleration times per axis ([input-ui-and-audio.md](input-ui-and-audio.md)).
4. Set blends on the Brain (a default blend, plus a blends asset for specific pairs), and cut instead of blending when poses are far apart or a blend would pass through walls.

**Watch for.** Cinemachine 2 names (`CinemachineVirtualCamera`, `CinemachineFreeLook`, Transposer, `GetCinemachineComponent`, the `Cinemachine` namespace) don't compile against 6.6; the full rename list is in [foundation.md](foundation.md). Turn on Ignore Time Scale on the input controller when the camera must stay controllable during pause or hit-stop.

**API facts** (check the installed version):
- Cinemachine 6.6.0 is a core package embedded in Unity, and its runtime code lives in the `Unity.Cinemachine` namespace (verified on 6000.6).
- A FreeLook is a `CinemachineCamera` with Orbital Follow, Rotation Composer and an Input Axis Controller, plus an optional Free Look Modifier (verified on 6000.6).
- `CinemachineInputAxisController` drives axes from Input System actions or the legacy Input Manager, with Gain, Accel Time, Decel Time, Ignore Time Scale and Suppress Input While Blending (verified on 6000.6).

## Follow, orbit and third-person rigs

**Goal.** Every rig holds its subject in frame, keeps clear of geometry, and moves with weight but never trails behind.

**Choose.**
- **Follow (chase):** Follow plus Rotation Composer, for vehicles and runners; the offset comes from the subject's length and height.
- **Orbit (free look):** Orbital Follow plus Rotation Composer and an Input Axis Controller, for explorers, products and overviews.
- **Third person, over the shoulder:** Third Person Follow, attached rigidly to an aim target that the player rotates; Third Person Aim keeps the crosshair point locked to screen center. **First person:** Pan Tilt at the head position, with no follow damping.
- **Top-down and 2D:** Position Composer with a confiner ([2d.md](2d.md)).

**Build.**
1. Track an empty child at the subject's visual center (chest or head height), not the pivot at the feet.
2. Derive offsets and orbit radii from the subject's size, so one rig suits every character or vehicle; set damping in seconds, lighter on rotation than on position.
3. Place the subject with the Rotation Composer's screen position, dead zone and damping; Lookahead Time aims slightly ahead of a moving target. Widen the lens a little with speed, or let Follow Zoom hold a target's size on screen.
4. When the target moves in physics, turn on interpolation on its Rigidbody and keep the Brain on Smart Update ([characters-physics-and-feel.md](characters-physics-and-feel.md)).

**Watch for.** Heavy damping reads as lag, not weight. An orbit's vertical range that allows the camera below the target's feet shows the ground from below. Lookahead on a noisy target makes the camera twitch.

**Critic checks.** PASS when, throughout the walkthrough, the camera never enters geometry or drops below the ground, the subject stays in frame while moving, and the follow distance fits the subject's size. FAIL signs: the lens passing into walls or terrain; a view of the ground from underneath; the subject sliding out of frame; jitter on a moving subject.

**API facts** (check the installed version):
- Third Person Follow keeps the camera rigidly attached to its target, so the camera aims only when the target rotates (verified on 6000.6).
- The Rotation Composer offers Lookahead Time, Lookahead Smoothing, Damping and a Dead Zone around the target's screen position (verified on 6000.6).
- Follow Zoom adjusts the lens field of view to keep the target at a constant size on screen (verified on 6000.6).

## Collision and deoccluding

**Goal.** The camera is never inside walls or terrain, and the subject isn't lost behind obstacles for longer than a beat.

**Choose.**
- **Deoccluder** to keep line of sight: it pulls the camera forward, or moves it around the obstacle while keeping its height or its distance.
- **Decollider** only to push the camera out of colliders, with terrain resolution that lifts it onto terrain layers; it doesn't preserve line of sight.
- **Third Person Follow's own collision resolution** for over-the-shoulder rigs.

**Build.**
1. Give everything the camera must avoid a collider; trees, props and terrain without colliders let the camera straight through.
2. Set Collide Against (or the third-person Camera Collision Filter) to the obstacle layers, exclude the player's layer, and set Ignore Tag to the player's tag.
3. Keep Camera Radius small; put foliage and thin poles on Transparent Layers, use Minimum Occlusion Time so brief occluders don't jerk the camera, and damp the move in and the return separately (Damping When Occluded, Damping).

**Watch for.** Each obstacle query is a physics raycast; keep the layers tight. A near plane larger than the camera radius still clips into walls.

**Critic checks.** PASS when the camera stays out of geometry in every frame and the subject stays visible, or returns to view quickly from behind cover, without snapping. FAIL signs: the camera inside a wall or tree; the subject hidden behind a pillar for seconds; the camera lurching toward its target.

**API facts** (check the installed version):
- The Deoccluder needs collider volumes on obstacles and offers Pull Camera Forward, Preserve Camera Height and Preserve Camera Distance; objects on its Transparent Layers never block the view (verified on 6000.6).
- The Decollider pushes the camera out of overlapping obstacles and can lift it onto terrain layers by casting down from above, without keeping line of sight (verified on 6000.6).
- Third Person Follow resolves collisions itself, with Camera Collision Filter, Ignore Tag, Camera Radius, Damping Into Collision and Damping From Collision (verified on 6000.6).

## Impulse for screen shake

**Goal.** Shake comes from events, travels from where they happen, decays on its own, and can be turned down or off.

**Build.**
1. Add a `CinemachineImpulseListener` extension to every Cinemachine camera that should shake; set its Gain and, for shake relative to the view, Use Camera Space.
2. Put a `CinemachineImpulseSource` on whatever causes the event and call one of its `GenerateImpulse` methods from gameplay at that moment; use a `CinemachineCollisionImpulseSource` for collisions and trigger zones.
3. Choose the Impulse Shape (Recoil, Bump, Explosion, Rumble, or a custom curve) and its duration; Default Velocity sets the shake's direction, and the call's force scales it.
4. Shape the reach with Dissipation Distance, Dissipation Rate and Propagation Speed, and use channels to keep a UI camera still. Set the listener's Signal Combination Mode to Use Largest when many hits land at once, so they don't stack into a wild shake.
5. Expose a shake-strength setting that scales listener Gain, with an off position, and honor reduced motion ([input-ui-and-audio.md](input-ui-and-audio.md)); keep handheld drift (Noise) separate from impulses, so either can be turned off alone.

**Watch for.** Shaking the follow target instead of the camera makes the rig re-frame and drift. Check how shake behaves during a hit-stop; if it freezes with time, fire the impulse as the stop ends ([characters-physics-and-feel.md](characters-physics-and-feel.md)).

**Critic checks.** PASS when walkthrough frames show shake starting on the event's frame, scaled to the event, decaying within its duration, and leaving the camera exactly where it was. FAIL signs: shake with no visible cause; shake that never settles; the frame drifting off target after a hit; constant jitter.

**Start here** (adjust to the goal): a Bump shape of about a fifth of a second for a hit, and an Explosion shape near half a second for a blast.

**API facts** (check the installed version):
- Impulse pairs a source component with a listener extension on the camera; `CinemachineExternalImpulseListener` lets other GameObjects react (verified on 6000.6).
- Predefined Impulse Shapes are Recoil, Bump, Explosion and Rumble, with a duration in seconds, or a custom curve (verified on 6000.6).
- Propagation Speed defaults to 343 m/s, the speed of sound, so distant listeners shake later (verified on 6000.6).
- The listener's Signal Combination Mode is Additive (the default) or Use Largest (verified on 6000.6).

## Framing and lens

**Goal.** Each still has a single obvious subject, deliberately sized and placed, inside a frame that has depth.

**Choose.** Match the lens to the subject: a wide lens for interiors, scale and speed, accepting stretched corners; a normal lens for people and things in their setting; a short telephoto for products and portraits, with almost no distortion; a long lens to stack distant landscape layers or tighten a chase.

**Build.**
1. Decide how much of the frame the subject should fill, and where it sits: on a third, on a leading line, with space in front of the way it faces or travels.
2. Keep the horizon level and vertical lines upright unless a tilt is intended; set the camera's height deliberately (at eye level, low to make the subject loom, high to show the layout).
3. Stack depth: something near, something in the middle distance, and something far.
4. Set lenses on the Cinemachine camera: Field of View in vertical degrees, or physical properties (focal length, sensor size) when a real-lens look matters.
5. Frame groups with a Target Group and Group Framing, so several players or a boss and a hero stay in view.

**Critic checks.** PASS when every still has one subject that fills the share of the frame planned for it, a level horizon unless the tilt is intended, and separate near, middle and far planes. FAIL signs: a tiny subject centered in empty space; a tilt nobody intended; busy frames with nothing to look at; buildings whose verticals lean together.

**Start here** (adjust to the goal): a 35 to 50 mm equivalent for people in their setting, and 85 mm or longer for products and portraits.

## Animator, state machines and blend trees

**Goal.** Characters switch actions without pops, their feet match their speed, and no one flashes a bind pose.

**Build.**
1. Build an Animator Controller with a base locomotion layer, and upper-body layers with Avatar Masks for aiming, carrying or attacking while moving.
2. Make locomotion a blend tree: 1D by speed, or 2D by local velocity on X and Z for strafing, fed from the character's real velocity rather than raw input.
3. Transitions: Has Exit Time off for responsive actions gated by conditions, on for one-shots that must finish; Fixed Duration for durations in seconds; Interruption Source so a dodge can cancel an attack.
4. Keep Evaluate Entry Transitions On Start on (the default for new controllers), so a state machine can start in its right state without a one-frame flash of the default.
5. Update Mode: Normal for most characters, Animate Physics when the character is a physics body, Unscaled Time for menus that animate during pause. Culling Mode: Always Animate when bones drive gameplay or the camera. Cache parameter IDs with `Animator.StringToHash`.

**Watch for.** Blend-tree thresholds that don't match each clip's real speed make feet slide. An animator in Normal mode on a body moved in `FixedUpdate` jitters.

**Critic checks.** PASS when walking feet hold their ground, changes between actions blend smoothly, and no frame shows a character in a T-pose. FAIL signs: feet skating or sliding; hard pops between states; a bind pose on the opening frame.

**Start here** (adjust to the goal): transitions of 0.1 to 0.25 seconds between locomotion states.

**API facts** (check the installed version):
- Evaluate Entry Transitions On Start, on by default for new controllers since 6.4, removes the one-frame delay from the default state (verified on 6000.6).
- Animator Update Mode is Normal, Animate Physics (in step with `FixedUpdate`) or Unscaled Time (ignores the time scale) (verified on 6000.6).
- Culling Mode is Always Animate, Cull Update Transforms or Cull Completely (verified on 6000.6).
- With Has Exit Time, the exit time is in normalized time; Fixed Duration makes the transition length seconds instead of a fraction of the source state (verified on 6000.6).

## Root motion and Humanoid retargeting

**Goal.** Animation-driven movement lands where physics and navigation expect, and one clip set animates many humanoid models.

**Choose.**
- **In-place clips with code-driven movement** for responsive controls; most agent-built games start here.
- **Root motion** (Apply Root Motion) for weighty, grounded characters whose steps are authored, with the clips' motion handed to the controller in `OnAnimatorMove`. With navigation, feed the agent's velocity into a 2D blend tree, or let root motion move the body and sync the agent's position ([characters-physics-and-feel.md](characters-physics-and-feel.md)).

**Build.**
1. For people, set Animation Type to Humanoid on the model's Rig tab, create the Avatar from the model, and configure it in a T-pose; Humanoid clips then retarget across humanoid models. Creatures and machines use Generic rigs, which don't retarget across different skeletons.
2. On each clip, set Loop Time, and Bake Into Pose for Root Transform Rotation, Position (Y) and Position (XZ) as the clip needs: idles bake XZ, straight walks bake rotation, jumps leave Y free.
3. In `OnAnimatorMove`, apply the animator's deltas through the character's own mover (a `CharacterController.Move` or a Rigidbody move), never both at once.
4. Mixamo and Asset Store clips follow the policy in [assets-and-import.md](assets-and-import.md) (Asset Store and Mixamo files).

**Watch for.** Moving the body in code while root motion also moves it doubles the motion. Baking Y into pose hands vertical movement to physics, so a character with no mover then floats or sinks.

**Critic checks.** PASS when characters stay on paths and floors, their steps match ground speed, and every humanoid in the scene animates without stretched or twisted limbs. FAIL signs: drift through walls; skating; twisted shoulders or knees on a retargeted model.

**API facts** (check the installed version):
- Retargeting needs each model set to Humanoid with a configured Avatar, created from the model in a T-pose (verified on 6000.6).
- `OnAnimatorMove` runs every frame after the state machines and animations are evaluated and before `OnAnimatorIK` (verified on 6000.6).
- Bake Into Pose on Root Transform Position (Y) sets `Animator.gravityWeight` to 1, so physics handles vertical motion when root motion is on (verified on 6000.6).

## Animation Rigging: IK and aim

**Goal.** Limbs reach their targets and heads look at things procedurally, layered over clips, without robotic snaps.

**Build.**
1. Animation Rigging is a core package in 6.6. Put a Rig Builder on the GameObject that has the Animator, add a child with a Rig component, and assign that Rig to one of the Rig Builder's layers.
2. Add constraints under the Rig: Two Bone IK (with a target and a hint) for arms and legs, Multi-Aim for head and spine, Multi-Parent for props that switch hands, Damped Transform for tails and antennae, Chain IK for longer chains.
3. Foot placement on uneven ground: raycast down from each foot, set the IK targets on the hits aligned to the normal, and lower the pelvis by the larger offset.
4. Blend each Rig's weight in and out over a few frames instead of switching it.

**Watch for.** IK targets parented under the bones they move create feedback loops. A weight of 1 everywhere looks robotic; let clips lead and IK correct.

**Critic checks.** PASS when hands meet handles and weapons, feet sit on slopes and steps, and heads turn smoothly toward targets. FAIL signs: hands floating off grips; feet hovering on stairs; heads snapping to a target.

**API facts** (check the installed version):
- Animation Rigging 6.6.0 is a core package; a Rig Builder must sit with the Animator and assemble Rigs assigned to its layers (verified on 6000.6).
- Its constraints include Two Bone IK, Chain IK, Multi-Aim, Multi-Parent, Damped Transform and Twist Chain (verified on 6000.6).

## Timeline for cutscenes

**Goal.** Intros, cutscenes and scripted beats are paced, skippable, and capturable at identical frames every round.

**Build.**
1. Make a Timeline asset played by a Playable Director, with Animation, Activation, Audio and Signal tracks, and a Cinemachine Track whose shot clips cut or blend between Cinemachine cameras.
2. Plan the beats (an establishing wide shot, the approach, a detail, the reveal, a held moment), give each enough time to read, and line them up with music cues when there are any.
3. Use signals for gameplay events (spawn, unlock, hand control back), never polling the director's time; offer a skip that jumps to the end state, and hand control back on a cut.
4. For captures, set the director's Update Method to Manual, set its time to the named keyframe and evaluate, so each still lands on the same frame; name the keyframes ("beat-3-reveal") for [validation.md](validation.md).

**Watch for.** Play On Awake starts cutscenes in scenes used for gameplay captures. Bindings point at scene objects, so a re-instantiated prefab loses them until rebound.

**Critic checks.** PASS when every keyframe still shows a clear, well-composed subject, and a looping sequence ends on the frame it began with. FAIL signs: stills caught halfway through a transition; a visible jump where the loop restarts; a cutscene that can't be skipped.

**API facts** (check the installed version):
- The Playable Director's Update Method is DSP, Game Time, Unscaled Game Time or Manual, and its Wrap Mode is Hold, Loop or None (verified on 6000.6).
- Timeline is a core package in 6.6, and Cinemachine drives cameras from Timeline through Cinemachine Shot Clips on a Cinemachine Track (verified on 6000.6).

## Motion along splines

**Goal.** Objects and cameras travel along paths at controlled speed, with clean ends and no bumps at control points.

**Build.**
1. Author the path as a `SplineContainer` ([levels-and-geometry.md](levels-and-geometry.md)).
2. Move objects with the Spline Animate component: the Speed method (meters per second) when speed must stay constant, the Time method for a fixed duration, plus Easing, Loop Mode and Align To.
3. Move cameras with Spline Dolly as the Cinemachine camera's Position Control, with a separate look target, and carts with Spline Cart; ease in and out at the ends, and add roll only when it is motivated.

**Watch for.** Knots bunched in one stretch can show as speed changes; confirm constant speed in consecutive frames, and prefer the Speed method when it matters.

**Critic checks.** PASS when movers keep the intended speed, ease into their ends, and stay level unless banking is motivated. FAIL signs: a bump at control points; a snap at the end of the path; unexplained roll.

**API facts** (check the installed version):
- Spline Animate moves an object by Time (seconds) or Speed (meters per second), with Easing, Loop Mode, Start Offset (0 to 1) and Align To (None, Spline Element, Spline Object, World Space) (verified on 6000.6).

## Procedural motion and settling

**Goal.** Motion driven by code plays identically at any frame rate and ends fully at rest.

**Build.**
1. Use one clock for the whole game ([foundation.md](foundation.md)); scale per-frame motion by `Time.deltaTime`, and step springs and simulations in fixed steps.
2. Describe moves as phases with start and end times, the frame each lives in (world, parent, subject, camera), and the owner of each property.
3. Smooth with time-based functions (`Mathf.SmoothDamp` and its vector form) or springs near critical damping, never a fixed fraction per frame.
4. When a move nearly arrives, jump to the exact final pose and set its velocity to zero; snap to rest once the remaining error is tiny.
5. Layer shake over the path as a separate, limited offset (see Impulse for screen shake), and draw all variation from a seed.

**Watch for.** A fractional approach per frame never arrives and creeps by sub-pixel amounts. Euler-angle interpolation wobbles and can flip; interpolate rotations as quaternions.

**Critic checks.** PASS when consecutive frames at rest are identical, moves finish in a clean settle, and orientation turns smoothly with the direction of travel. FAIL signs: trembling at rest; slow drift after arriving; repeated overshoot; sudden orientation flips.

## Symptom → cause

| Symptom | Likely cause | First check |
| --- | --- | --- |
| Camera code doesn't compile | Cinemachine 2 names against Cinemachine 6.6 | the namespace and class names ([foundation.md](foundation.md)) |
| Camera ignores the mouse or stick | no Input Axis Controller, or its actions not enabled | the controller's mapped actions and Auto Enable Inputs |
| Jitter on a moving subject | target moved in physics without interpolation, or a script fighting the Brain | Rigidbody interpolation, and who writes the camera transform |
| Camera clips into walls or trees | obstacles without colliders, or wrong layers | colliders on the obstacles and the Collide Against mask |
| Camera jerks behind thin poles | occluders handled instantly | Transparent Layers and Minimum Occlusion Time |
| Shake never settles or drifts | target shaken instead of the camera, or Noise left on | where the shake is applied, and the Noise component |
| Hits stack into a wild shake | Additive signal combination | the listener's Signal Combination Mode |
| Feet slide | blend-tree thresholds not matched to clip speeds | each clip's speed against ground speed |
| A T-pose flashes on the first frame | default state shown before the entry transition | Evaluate Entry Transitions On Start |
| Character moves twice as far | code and root motion both moving the body | `OnAnimatorMove` and Apply Root Motion |
| Retargeted limbs twist | Avatar not configured in a T-pose | the Avatar's mapping and pose |
| Cutscene stills differ between rounds | director playing on game time during capture | Update Method set to Manual for captures |
| Camera creeps after arriving | fractional per-frame approach | the camera's position over frames after arrival |
