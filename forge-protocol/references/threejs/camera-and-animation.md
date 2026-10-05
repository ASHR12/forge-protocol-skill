# Three.js camera and animation

API facts verified on r186 (2026-10-05). Check the installed version first; if it differs, confirm in the official docs or the installed source. The installed version wins.

Read this when a builder owns how the scene is seen or how things move: shots, rigs, transitions, controls, clips and procedural motion. Most demos need it.

## Contents

- The camera contract
- Shot design and composition
- Camera rigs
- Transitions and handoffs
- Controls and feel
- Animation sources
- Procedural and authored motion
- Time, easing and settling
- Cinematic sequences for demos
- Symptom → cause

## The camera contract

**Goal.** Each camera mode can produce a valid pose on its own, and it is always clear which system owns the camera.

**Build.** Before building rigs, record for every mode:
- the subject and its size, from which offsets and limits are derived;
- the lens (focal length or vertical field of view) and the near and far planes;
- how position is set: an authored path, mounted to the subject, orbiting, relative to a planet, or floating-origin;
- what "up" means: the world's up, the subject's, or a planet's local radial direction;
- the input it accepts, its spatial limits (ground, walls, distances), and which system owns the camera during each transition.

Combine modes only after each one produces a correct position and orientation alone.

**API facts** (check the installed version):
- `fov` is the vertical angle in degrees; `setFocalLength()` sets it from a lens length against the 35 mm `filmGauge` and updates the projection itself (verified on r186).
- Call `updateProjectionMatrix()` after changing `fov`, `aspect`, `near`, `far` or `zoom` (verified on r186).

## Shot design and composition

**Goal.** Every still has one clear subject, sized and placed on purpose, in a frame with depth.

**Choose.** Pick the lens by subject: wide for spaces, scale and speed, accepting stretched edges; normal for people and objects in context; short telephoto for products and portraits, with little distortion; long to compress layers of landscape or a chase.

**Build.**
- Decide each shot's share of the frame for the subject, and where it sits: on thirds, along leading lines, with room ahead in the direction it faces or moves.
- Keep horizons level and off center unless symmetry or a tilt is the point, and keep verticals vertical in architectural shots.
- Layer a foreground, a midground and a background for depth.
- Choose camera height on purpose: eye level for realism, low for heroic scale, high for an overview.
- Stage subjects in the shot's own frame, placing them along the camera's forward, right and up axes, instead of nudging world positions until the shot looks right.

**Critic checks.** PASS when each still has one clear focal subject filling its planned share of the frame, the horizon is level unless deliberately tilted, verticals stay vertical in architectural shots, and foreground, midground and background are distinct. FAIL signs: a small centered subject in an empty frame, an accidental tilt, clutter with no focal point, converging verticals on buildings.

**Start here** (adjust to the goal and the subject): in 35 mm-equivalent focal lengths, about 35–50 mm for normal framing and 85–135 mm for products and portraits.

## Camera rigs

**Goal.** Each rig keeps the subject framed, stays outside geometry, and feels weighted without lagging.

**Build.**
- Orbit (products, overviews): target the subject's visual center, not its pivot; set distance limits from the subject's size; limit the polar angle so the camera never dips below the ground; damp it; offer a reset.
- Follow or chase: derive the offset behind and above from the subject's length and height, so one rig suits every vehicle; aim slightly ahead; lag position with a critically damped spring and rotation less; pull back and widen the lens a little with speed; cast from subject to camera and pull in when something blocks the view.
- First person: pointer lock, pitch clamped just short of straight up and down, a collision capsule, and head bob that is subtle and can be switched off.
- Cinematic paths: one spline for position and another for the look target, parameterized by length so speed doesn't bump at control points, eased at the ends, with no roll unless it is motivated.
- On planets, up is the direction from the body's center to the camera; build forward in the plane tangent to the surface.
- Over terrain, keep every rig a margin above the ground, read from the terrain's CPU height copy sampled the way the GPU draws it, because a raycast misses displacement done in the shader ([terrain.md](terrain.md), Collision and height parity).

**Critic checks.** PASS when, across walkthrough frames, the camera stays outside geometry and above ground, the subject stays framed through motion, and the chase distance suits the subject's size. FAIL signs: clipping into walls or terrain, the ground seen from below, the subject leaving the frame.

**API facts** (check the installed version):
- `Object3D.lookAt()` uses the object's own `up`; cameras and lights aim their −Z axis at the target while other objects aim +Z, so on a planet set `camera.up` to the radial direction before calling it (verified on r186).
- `OrbitControls` limits are `minDistance`, `maxDistance`, `minPolarAngle` and `maxPolarAngle` (radians); a `maxPolarAngle` below π/2 keeps the camera above the target's height (verified on r186).

## Transitions and handoffs

**Goal.** A change of camera mode is one smooth move that ends exactly on the new pose and hands control over cleanly.

**Build.**
1. Capture the starting position and orientation when the transition begins.
2. Let one system own the camera for the transition. Interpolate position (linearly or along a path) and orientation (spherically) from a single eased parameter, and switch off every other smoother meanwhile.
3. At the end, copy the target pose exactly and give control to the new mode.
4. Cut instead of blending when the poses are far apart, when a blend would pass through geometry, or when the scene itself changes.

**Watch for.** Two smoothers acting on one move cause a half-halt in the middle. Interpolating Euler angles wobbles and can flip. An approach that closes only a fraction of the gap each frame never arrives, and keeps creeping by sub-pixel amounts.

**Critic checks.** PASS when walkthrough frames across a handoff show steady easing into the new framing, with no pause, overshoot, snap at the end, or creeping afterwards. FAIL signs: a hitch mid-move, a jump at the end, slow drift after arrival.

## Controls and feel

**Goal.** Input moves the camera immediately and predictably, on every device and at every frame rate.

**Build.**
- Map mouse motion to an angle per pixel moved, independent of frame rate.
- Damp with time-based decay (one minus the exponential of rate times elapsed time), never a fixed fraction per frame.
- On touch: one finger to orbit or look, two to pan, a pinch to zoom, and an on-screen stick for movement.
- On gamepads: dead zones and a response curve on each stick.
- With pointer lock, re-read yaw and pitch from the camera whenever lock is acquired, and clear held keys on blur and on unlock.
- Apply bounds and collision as a separate layer after input.
- Offer invert-Y, sensitivity and, in first person, a field-of-view setting.

**Watch for.** Jumps after re-locking the pointer, keys stuck after focus loss, zooming through the subject, and page scrolling fighting the canvas on touch.

**API facts** (check the installed version):
- With `enableDamping`, `OrbitControls.update()` must run every frame, and the glide decays by `dampingFactor` per call rather than per second, so it ends sooner at higher refresh rates (verified on r186).
- `PointerLockControls` re-reads the camera's orientation on every mouse move (Euler order `YXZ`), and `lock(true)` asks the browser for unaccelerated mouse input (verified on r186).

## Animation sources

**Goal.** Each moving thing uses the source that gives the right control at the right cost.

**Choose.**
- Authored clips (skeletal or morph, from Blender or motion capture through glTF) for characters, creatures and crafted mechanical cycles; blend them with cross-fades, and add layers for breathing or aiming.
- Morph targets for faces and simple shape changes.
- Procedural motion for machines, cameras, UI, cinematics and gameplay responses, where timing must be exact.
- Simulation (physics, springs, cloth) where motion responds to forces and contact.
- Layers that mix them: procedural look-at and foot placement over clips.

**Build.** Update every mixer with the same elapsed time as everything else, match a locomotion clip's speed to ground speed so feet don't slide, and decide how root motion is handled.

**Critic checks.** PASS when feet stay planted while walking, switches between actions blend without pops, and no character flashes a bind pose. FAIL signs: sliding feet, popping, a T-pose on the first frame.

**API facts** (check the installed version):
- To hold a one-shot clip's last pose, set its loop to `LoopOnce` and `clampWhenFinished` to true; otherwise the action disables itself at the end and the bones fall back to whatever else drives them (verified on r186).
- Clone skinned models with `SkeletonUtils.clone()`. A plain `clone()` of a `SkinnedMesh` keeps the source's skeleton, so the copies move with the original (verified on r186).

## Procedural and authored motion

**Goal.** Motion is described as phases with clear frames and owners, so every move is intentional and ends exactly where it should.

**Build.**
1. Define phases with named start and end times, the frame each motion lives in (world, parent, subject, orbit, docking axis, camera shot), and which system owns each property.
2. Drive authored travel with closed-form curves of time, such as eased arcs and ballistic paths, never by repeatedly blending toward a moving point.
3. Use springs near critical damping for responsive settling.
4. Near the end, switch to the exact final pose and zero the velocity.
5. Measure approach errors in the target's own frame (along its axis and sideways), so corrections look deliberate.
6. Point the object along its direction of travel first, and add any roll or spin afterwards as its own rotation.
7. Keep shake as a bounded offset on top of the path, so either can be switched off on its own.
8. Let released parts inherit their source's motion, including the sideways speed that comes from its spin.
9. Use seeded randomness for any variation.

**Watch for.** Easing that never arrives, Euler-angle interpolation, a jump when reparenting, shake baked into the path, and phase times that depend on each other in hidden ways.

**Critic checks.** PASS when moving objects decelerate into exact rest poses with no drift afterwards, orientation follows travel smoothly, and released parts carry on with their source's motion. FAIL signs: creeping after arrival, flips in orientation, pieces flying off in directions unrelated to the motion.

**API facts** (check the installed version):
- `Object3D.attach()` reparents while keeping the world transform, where `add()` keeps the local one; `attach()` doesn't support non-uniformly scaled nodes (verified on r186).
- `MathUtils.damp(x, y, lambda, dt)` smooths toward a target independently of frame rate (verified on r186).

## Time, easing and settling

**Goal.** Motion looks the same at any frame rate and comes to a complete rest.

**Build.**
- Use one clock in seconds for the whole app ([foundation.md](foundation.md)), clamp the frame delta after stalls, and step springs and simulations in fixed substeps.
- Choose easing per move: ease-out for arrivals, ease-in-out for camera moves, linear for sweeps that must read as constant speed.
- Smooth with time-based exponential decay, re-normalize quaternions after many multiplications, and snap to rest below a small threshold.

**Critic checks.** PASS when consecutive walkthrough frames at rest show no movement at all, and moves end in clean settles. FAIL signs: jitter at rest, repeated overshoot.

**Start here** (adjust to the goal and the simulation): clamp each frame's delta to about a tenth of a second.

**API facts** (check the installed version):
- `Clock` is deprecated since r183; use `Timer`, call its `update()` once per frame, and `connect(document)` so the delta is zero while the tab is hidden. It doesn't clamp other stalls (verified on r186).

## Cinematic sequences for demos

**Goal.** Intros, attract loops and hero turntables are paced in beats, and their key moments can be captured identically every round.

**Build.**
- Structure the sequence in beats (establish wide, approach, detail, reveal, hold), each long enough to read and each a shot with an authored camera path and subject motion.
- Sync beats to music or sound cues when there are any.
- Loop attract modes seamlessly: end on the starting pose, or cut on a dark or bright frame.
- Turn turntables at a constant angular speed through one full turn, with lights fixed to the world or turning with the object, chosen on purpose.
- Offer a skip control.
- Name keyframes ("beat-3-reveal") and expose a timeline hook, so captures land on the same frames every round ([validation.md](validation.md)).

**Critic checks.** PASS when each keyframe still shows a clear, composed subject, and a loop's last frame matches its first. FAIL signs: stills caught mid-transition, a visible jump at the loop point.

## Symptom → cause

| Symptom | Likely cause | First check |
| --- | --- | --- |
| Subject off-center in an orbit view | orbit target at the pivot instead of the visual center | the orbit target against the center of the subject's bounds |
| Chase camera too close for one vehicle, too far for another | fixed offsets instead of offsets from the subject's size | the offsets against each subject's size |
| Camera clips into walls or terrain | no collision layer or polar limit | the camera's clearance from geometry and ground across the walkthrough |
| Half-halt during a transition | two smoothers acting on the same move | which systems write the camera during the move |
| Snap at the end of a move | no exact final pose, or control handed over early | the last frame's pose against the target pose |
| Camera creeps after arriving | a fractional approach that never reaches the target | the camera's position over frames after arrival |
| Orientation flips near straight up or down | Euler interpolation, or an `up` parallel to the view | the interpolation method and the `up` vector |
| Camera tilts on a planet | world up used instead of the local radial direction | `camera.up` against the radial direction |
| Jump after re-entering pointer lock | yaw and pitch not re-read from the camera | the yaw and pitch read on lock |
| Damping feels different on another display | per-frame decay instead of time-based decay | the same move at two frame rates |
| Feet slide | clip speed not matched to ground speed | clip speed against ground speed |
| Copies of a character move together | skinned meshes cloned without `SkeletonUtils.clone()` | how the copies were cloned |
| A one-shot animation snaps back | action not clamped when finished | `clampWhenFinished` and the loop mode |
| A part jumps when detached | reparented with `add()` instead of `attach()` | the reparenting call |
| Motion speed varies by display | per-frame increments instead of elapsed seconds | the frame-rate pair ([validation.md](validation.md)) |
| Jitter at rest | springs with no rest threshold, or unclamped deltas | consecutive frames at rest |
