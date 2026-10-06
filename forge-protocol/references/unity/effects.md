# Unity effects: Particle System, VFX Graph, impacts, fire and smoke, trails, decals and full-screen passes

API facts verified on Unity 6.6 (6000.6.4f1, 2026-10-06). Check the project's Unity version first (ProjectSettings/ProjectVersion.txt); if it differs, confirm in that version's official docs or the installed packages. The installed version wins.

Read when the build needs particles, sparks, impacts, fire and smoke, explosions, trails and beams, marks left on surfaces, or screen-wide effects such as heat haze and damage flashes. Bloom and the final image are in [final-image.md](final-image.md); rain and snow are in [sky-weather-and-water.md](sky-weather-and-water.md); screen shake is in the camera file ([camera-and-animation.md](camera-and-animation.md), Impulse for screen shake).

## Contents

- Particle System or VFX Graph
- Designing an effect
- Particle materials, soft particles and sorting
- Sparks, debris and impacts
- Fire, smoke and explosions
- Trails, lines and beams
- Decals and residue
- Full-screen passes
- HDR emission and bloom
- Pooling and performance
- Symptom → cause

## Particle System or VFX Graph

**Goal.** Every effect runs on every target the brief names, and any fallback is planned, not discovered.

**Choose.**
- **The Particle System** (the built-in, CPU-simulated one) by default. It works in every pipeline and on WebGL 2, handles thousands of particles, collides with the physics world, gives C# access to every particle, and has sub-emitters, lights and trails. Since 6.6, Shader Graph builds particle shaders fully compatible with it in URP, including GPU-instanced mesh particles.
- **VFX Graph** for effects that need hundreds of thousands to millions of particles, authored as a graph and simulated on the GPU. It needs compute shaders, so it runs on the Mac and on WebGPU, never on WebGL 2; every VFX Graph effect needs a Particle System fallback for the WebGL 2 tier, listed in the plan's tier table.

**Build.**
1. Start every effect as a Particle System; promote it to VFX Graph only when the count or look outgrows the CPU on the Mac tier, and author the WebGL 2 fallback in the same pass.
2. Choose at runtime from `SystemInfo.supportsComputeShaders` together with `SystemInfo.maxComputeBufferInputsVertex` above 0 (storage buffer support), and record which system each capture used in the handback.

**Watch for.** VFX Graph isn't out of preview for URP, so it supports only some URP platforms; test it on each target before relying on it.

**Critic checks.** PASS when the WebGL 2 capture shows the same effect reading as the Mac capture (cause, shape, timing and color), even if sparser. FAIL signs: an effect missing on one target; a fallback that changes what the effect means.

**API facts** (check the installed version):
- VFX Graph needs compute shaders (`SystemInfo.supportsComputeShaders`) and shader storage buffers, and doesn't support OpenGL ES (verified on 6000.6).
- VFX Graph isn't out of preview for URP and supports only some of URP's platforms (verified on 6000.6).
- WebGL 2 has no native compute shaders; WebGPU supports compute and lists VFX Graph among its features (verified on 6000.6).
- Shader Graph in 6.6 creates particle shaders compatible with the Particle System in URP, including mesh particles with GPU instancing (verified on 6000.6).

## Designing an effect

**Goal.** An effect feels designed when every part of it traces back to a single event: it begins at a visible cause, travels through one field of motion, and dies away on a schedule.

**Build.** Before making any layer, describe the effect as a sequence of links, then give each link its Particle System modules:
1. Event (what starts it, where, which way, how hard): a burst in the Emission module, fired by gameplay at the contact point and normal.
2. Envelope (how intensity rises and falls): Color, Size and Velocity over Lifetime curves, against normalized age.
3. Motion field (what moves the pieces): start velocity along the event's direction, gravity, drag (Limit Velocity over Lifetime), Noise, and External Forces for the shared wind.
4. Representation and shading: billboards, stretched billboards, meshes or trails, with lit smoke and additive light.
5. Lifetime and cleanup: Start Lifetime, then a Stop Action (Disable, Destroy, or a Callback that returns it to a pool).
6. Contribution: how bright it is against the rest of the HDR frame (see HDR emission and bloom).

**Watch for.** Layers whose only link is a shared color; give every layer a role (shape, motion, light or aftermath). Secondary bits that ignore the main movement. Auto Random Seed makes every play differ, which breaks repeatable captures: turn it off and set Random Seed from the game's seed.

**Critic checks.** PASS when each effect clearly begins at what caused it (a barrel, a point of impact, a nozzle), its pieces travel together in one direction, and its form is still readable in the no-post still. FAIL signs: blobs defined only by glow; effects appearing in mid-air with no source; layers separating.

**API facts** (check the installed version):
- With Auto Random Seed off, a Particle System plays identically every time from its Random Seed (verified on 6000.6).
- Stop Action can disable or destroy the GameObject, or send `OnParticleSystemStopped` to its scripts (verified on 6000.6).
- Emitter Velocity reads a Rigidbody when one exists, or else the Transform's movement, for the Inherit Velocity and Emission modules (verified on 6000.6).

## Particle materials, soft particles and sorting

**Goal.** Particles meet surfaces softly, layer in a plausible order, and never show sprite rectangles.

**Build.**
1. Use URP's particle shaders (Particles Unlit, Simple Lit, Lit) or a particle Shader Graph; additive blending for pure light, alpha blending for smoke and dust.
2. Turn on Soft Particles (Transparent surface) so sprites fade near geometry, set Surface Fade in meters, and enable Depth Texture in the URP asset; Camera Fading hides sprites that would fill the lens.
3. Flipbooks: animate with Texture Sheet Animation, and enable Flip-Book Blending when frames are few.
4. Sorting: pick the Renderer module's Sort Mode (By Distance for smoke, Oldest or Youngest in Front for trails of puffs), and use Sorting Fudge to order whole systems against each other.
5. Stretched Billboard for sparks and streaks, so they stretch along their velocity.

**Watch for.** Sorting works per system against other transparents, so two overlapping smoke systems can swap order as the camera moves; merge them, or bias one with Sorting Fudge. Lit particles need probes or lights nearby, or they read flat.

**Critic checks.** PASS when sprites dissolve gently where they touch floors and walls, smoke and flame stack in a believable order, and no rectangular sprite outline is visible. FAIL signs: sharp seams where sprites intersect geometry; visible square sprite borders; layers jumping in front of one another.

**API facts** (check the installed version):
- URP particle shaders fade near opaque geometry with Soft Particles (Near and Far in world units) only on a Transparent surface with the URP asset's Depth Texture on (verified on 6000.6).
- The Renderer module's Sort Mode is None, By Distance, Oldest in Front, Youngest in Front or By Depth, and Sorting Fudge biases a whole system against other transparents (verified on 6000.6).

## Sparks, debris and impacts

**Goal.** A hit looks like something physical happened: a flash, sparks flung from the point of contact, fragments that drop and come to rest, and a mark that stays.

**Build.**
1. Spawn at the contact point from gameplay (a collision's contact or a raycast hit), oriented by the surface normal and the incoming direction.
2. Sparks: hot, bright cores on Stretched Billboards, launched in a cone around the reflected direction, losing speed to drag, curving down under gravity, bouncing once off the world (Collision module), and cooling from white through orange to deep red within a short life.
3. Debris: a few mesh particles or pooled rigidbodies that tumble, inherit the source's motion, bounce, settle and fade.
4. A short-lived real light (the Lights module, or one pooled point light) that fades fast, a burst of dust, and a decal (see Decals and residue).
5. Fire the camera impulse, the sound and the hit-stop from the same event ([characters-physics-and-feel.md](characters-physics-and-feel.md)).
6. Vary each impact from a seed, so repeated hits differ.

**Watch for.** Sparks bursting evenly in all directions ignore the surface. The Lights module spawns a real light per lit particle; cap it with its Ratio and maximum.

**Critic checks.** PASS when sparks leave the point of contact around the reflected direction and arc down under gravity, nearby surfaces brighten for an instant, and a mark is left behind. FAIL signs: sparks spreading equally in all directions; surroundings that never light up; nothing left after the hit.

**API facts** (check the installed version):
- The Lights module attaches a light prefab to a Ratio (0 to 1) of particles, optionally scaled by particle color, size and alpha (verified on 6000.6).

## Fire, smoke and explosions

**Goal.** Fire is hot gas, brightest at its core and tapering into tongues, feeding smoke that rises, spreads and is lit from below; an explosion is staged in time.

**Choose.**
- **Flipbook sprites** for torches, campfires and distant fires; **procedural Shader Graph flames** on cards for stylized or mid-distance fire.
- **VFX Graph volumes** for a hero fire on the Mac or WebGPU tier, with flipbooks as the WebGL 2 fallback.

**Build.**
1. Fire: map age to a hot-body color ramp (white, yellow, orange, red) and to emission; rise by buoyancy with Noise for licking turbulence; keep smoke a separate, alpha-blended system that is lit and darkens, never additive.
2. Place a flickering light of the flame's color at its center, and add heat shimmer above the fire when the shot wants it (see Full-screen passes, or a distortion particle).
3. Explosions in beats, each its own system or sub-emitter: flash (a frame or two, real light); fireball (fast, then slowing, cooling to smoke); smoke (slower, lingering); debris (launched at the start, trailing smoke); a ground shockwave ring; fading light; scorch marks.
4. Scale timing with size: bigger explosions unfold more slowly, and distant ones are heard late ([input-ui-and-audio.md](input-ui-and-audio.md)).

**Watch for.** Additive sprites piling up into a white mass; repeating loops in flipbook fire; smoke that glows; a light that stays steady under a flickering fire; flames that pass through walls.

**Critic checks.** PASS when the fire burns brightest near the source and breaks into narrowing tongues, the smoke above is darker and lit from beneath, nearby surfaces flicker in the fire's light, and explosion frames run flash, fireball, rising smoke, debris arcs and fading light in that order. FAIL signs: a shapeless glowing mass; visible flat cards; luminous smoke; every stage starting and stopping together.

## Trails, lines and beams

**Goal.** Trails trace the exact path of whatever made them and thin out to nothing; beams carry a hot inner core inside a softer outer glow and end exactly on what they strike.

**Choose.**
- **Trail Renderer** for one moving object (a sword tip, a projectile, a car's light).
- **The Trails module** for trails on many particles: Particle mode (each particle leaves a trail) or Ribbon mode (one ribbon joining particles by age).
- **Line Renderer** for beams, lasers, ropes and aiming arcs set from code.

**Build.**
1. Taper width and fade color along the trail with the width curve and gradient; set Time (a point's lifetime) from how long the eye should follow the path.
2. Space vertices by distance with Min Vertex Distance, never per frame, so trail length doesn't change with frame rate; toggle Emitting rather than destroying the trail.
3. Beams: an HDR core line inside a wider, softer line, a slight flicker in width, a flare and a light at the end, and a raycast so the beam stops exactly at what it hits.
4. Round corners and caps with Corner Vertices and End Cap Vertices; face the camera with View alignment.

**Watch for.** Kinks at tight turns from too few vertices; ribbons that disappear when seen edge-on with Transform Z alignment; beams ending before they reach their target.

**Critic checks.** PASS when trails narrow smoothly along the path of motion with no kinks, and beams show a hot core within a softer glow and a visible point of contact at their end. FAIL signs: strips of constant width; trails disappearing when seen edge-on; beams stopping in mid-air before the target.

**API facts** (check the installed version):
- The Trail Renderer adds a point when its target has moved Min Vertex Distance, keeps each point for Time seconds, and pauses with Emitting (verified on 6000.6).
- The Trails module runs in Particle or Ribbon mode, with a Ratio of particles that get trails and an optional World Space that drops vertices in the world (verified on 6000.6).

## Decals and residue

**Goal.** Hits, burns and splashes leave marks that lie on the surface they struck, wrap its shape, and fade with time.

**Build.**
1. Use URP's Decal Projector with the Decal Renderer Feature; setup, decal materials, the Decal Shader Graph and the technique per target (Screen Space on WebGL 2, where DBuffer doesn't run) are in [materials-and-shaders.md](materials-and-shaders.md), Decals.
2. Spawn marks at the hit point, oriented by the surface normal and given a random spin, sized by the event.
3. Change more than color: a burn is dark and rough, a splash is shiny and dulls as it dries, a footprint flattens the normals.
4. Keep a capped pool of projectors and fade out the oldest marks.
5. On animated or skinned targets, decals slide; paint into the target's own mask texture instead.

**Watch for.** URP decals affect opaque surfaces only, so marks don't appear on water, glass or other transparents. Decals on terrain displaced in its shader float above or sink into the drawn ground.

**Critic checks.** PASS when marks sit flat on what they hit, bend with its curvature, and fade with time. FAIL signs: decals floating or flickering; marks smeared across corners; marks that pile up without limit.

## Full-screen passes

**Goal.** Screen-wide effects (heat haze, damage and low-health vignettes, frost on a visor, a scan pulse) are authored as passes with a cause, a duration and a strength, and stay off the critic's form checks.

**Build.**
1. Add a Full Screen Pass Renderer Feature to the URP renderer, with a material from a fullscreen Shader Graph (the URP Fullscreen material type).
2. Pick its Injection Point: Before Rendering Transparents for effects that should sit under particles and water, Before Rendering Post Processing so bloom and tonemapping apply on top, or After Rendering Post Processing (the default) for overlays that must keep their exact colors.
3. Request only what it reads in Requirements (Depth, Normal, Color, Motion); Fetch Color Buffer binds the current camera color to `_BlitTexture`.
4. Drive its strength from gameplay through a material property, eased with time, and off by default.
5. For logic beyond one material, write a renderer feature in C# with the Render Graph API; URP's custom passes override `RecordRenderGraph`, and the old compatibility path is gone ([foundation.md](foundation.md)).

**Watch for.** A pass after post-processing escapes tonemapping, so its HDR values clip. Each Requirement adds a render pass; "Everything" costs the most.

**Critic checks.** PASS when each full-screen effect appears only with its cause (a hit, low health, heat), fades on a plan, and leaves the subject readable. FAIL signs: a permanent overlay; an effect with no visible cause; a flat colored wash.

**API facts** (check the installed version):
- Fetch Color Buffer binds the camera's current color target to `_BlitTexture`, which differs from the Color requirement's opaque texture (verified on 6000.6).
- Bind Depth-Stencil gives the pass the camera's depth-stencil target, at a performance cost (verified on 6000.6).

## HDR emission and bloom

**Goal.** Light-emitting effects outrank everything else in the frame by design, and still read as shapes with bloom off.

**Build.**
1. Rank emitters before bloom: the sun, then explosions and muzzle flashes, then fire, then sparks, then magic and UI glows, each with an HDR intensity set on purpose.
2. Put emission in the particle material's HDR color or emission, not in a bright texture that clips.
3. Give every glowing effect a dark-to-bright core and a silhouette, so the no-post still shows its shape.
4. Tune bloom only after the no-post still passes; the bloom settings and their order in the post chain are in [final-image.md](final-image.md).

**Critic checks.** PASS when effects read as shapes with distinct cores in the no-post still, and the brightest emitter in each still is the one the brief ranks highest. FAIL signs: glow as an effect's only edge; a spark outshining the sun; every emitter at the same brightness.

## Pooling and performance

**Goal.** Effects never stutter on bursts, stay inside the frame budget near the camera, and cost nothing when off screen.

**Build.**
1. Pool effect instances instead of instantiating per event: `UnityEngine.Pool.ObjectPool<T>` returns them, and a Stop Action Callback or Disable hands them back.
2. Reuse one Particle System with `Emit` for frequent small bursts (bullet hits, footstep dust) instead of one system per event.
3. Cap Max Particles per system, and choose a Culling Mode: Pause for looping ambience, Always Simulate for one-shots whose state matters when they come into view.
4. Watch overdraw: large transparent sprites near the camera cost the most; shrink them, use fewer and denser sprites, and check the Rendering Debugger's Overdraw view.
5. Count lights from the Lights module against the renderer's light limits ([lighting-and-shadows.md](lighting-and-shadows.md)), and give the Web tier lower emission rates and no particle lights.

**Watch for.** Pause And Catch-up can spike when a complex system comes back into view. Destroying systems on every hit allocates garbage and stalls.

**Critic checks.** PASS when the build's own performance readout stays inside the brief's budget during the heaviest effect in the walkthrough. FAIL signs: a frame-time spike on each burst; a drop when the camera passes through smoke; no readout captured.

**API facts** (check the installed version):
- Culling Mode offers Automatic, Pause And Catch-up, Pause and Always Simulate, and Automatic pauses looping systems while simulating the rest (verified on 6000.6).
- Ring Buffer Mode keeps particles alive until Max Particles is reached and then recycles the oldest (verified on 6000.6).
- URP's Rendering Debugger includes an Overdraw view that shows where pixels are drawn over each other (verified on 6000.6).

## Symptom → cause

| Symptom | Likely cause | First check |
| --- | --- | --- |
| The Web build lacks an effect | VFX Graph on WebGL 2, which has no compute | the effect's system and its Particle System fallback |
| An effect pops into empty air | spawning not tied to its cause | spawn points drawn against the contact points |
| Captures differ between rounds | Auto Random Seed on | the system's Random Seed settings |
| Hard lines where sprites meet surfaces | Soft Particles off, or no Depth Texture | the material's Soft Particles and the URP asset |
| Smoke and fire swap order as the camera moves | sorting per system, not per particle | Sort Mode and Sorting Fudge on each system |
| Fire reads as a white mass | additive layers piling up, with no core and no separate smoke | each layer's blend mode shown alone |
| Smoke shines like a light | smoke drawn with additive blending rather than lit alpha blending | the smoke material's blending |
| Sparks fly out evenly all around | launch velocities ignore the surface | spawn velocities against the normal |
| Trails change length with frame rate | points spaced per frame instead of by distance | Min Vertex Distance at two frame rates |
| Marks missing on water or glass | URP decals affect opaque surfaces only | the target's surface type |
| Stutter on every burst | instantiating and destroying per event | allocations during a burst in the Profiler |
| Frame time climbs near effects | overdraw from large sprites close to the camera | the Rendering Debugger's Overdraw view |
| Full-screen overlay clips or bands | pass injected after post-processing with HDR values | the Injection Point |
| Effects vanish in the no-post still | glow is the only shape | the same still with bloom off |
