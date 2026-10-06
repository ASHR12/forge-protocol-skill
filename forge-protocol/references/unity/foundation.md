# Unity foundation: version, pipeline, color, frame loop and script lifecycle

API facts verified on Unity 6.6 (6000.6.4f1, 2026-10-06). Check the project's Unity version first (ProjectSettings/ProjectVersion.txt); if it differs, confirm in that version's official docs or the installed packages. The installed version wins.

Read when you set up a project's shell, choose the render pipeline, write gameplay scripts, or follow code from a tutorial, a forum post or memory. It is the module's source of version truth: the pinned version, every rename and removal since 2022 LTS, the reasons for URP, color and HDR, the frame loop, Play mode state and async code. Installing and creating the project is in [setup.md](setup.md), safe edits to project files in [project-hygiene.md](project-hygiene.md), and driving the editor in [agent-control.md](agent-control.md).

## Contents

- Version pin and ground truth
- Renamed and removed APIs, 2022 LTS to 6.6
- Choosing the render pipeline
- What URP lacks, and where the substitutes are
- The HDRP route
- Color space and HDR
- Frame loop, fixed timestep and time scale
- Script execution order
- Play mode without domain reload
- Async code: Awaitable and coroutines
- Destroyed objects and Unity's null
- Symptom → cause

## Version pin and ground truth

**Goal.** Every API call, menu path and setting matches the editor that is installed. Unity 6 went through seven releases, 6.0 to 6.6, and most of them renamed or removed something, while tutorials, forum answers and remembered code mostly describe 2022 LTS or 6.0.

**Build.**
1. Read the editor version from `ProjectSettings/ProjectVersion.txt` and the URP version from `Packages/packages-lock.json`. Record both in the Stack section of `BRIEF.md` and in every handback. Change the editor version only with the user's go.
2. Confirm an API against these sources, in order: the docs installed with the editor (with the Documentation module, `Documentation/en/Manual` and `Documentation/en/ScriptReference` inside the editor's folder); the online manual for the same version (`docs.unity3d.com/6000.6/Documentation/...`); for a package, the docs for the exact version in the lock file, or its source under `Library/PackageCache`, read only; then Unity's C# reference source. URP's manual lives inside the Unity Manual on 6.x.
3. Read compiler messages in full: an obsolete member's message names its replacement. Fix the warning by migrating, never by suppressing it.
4. Run Project Auditor, which is built into the editor, before and after any upgrade. It reports APIs that went obsolete between versions, URP settings that look wrong, and static fields that may need resetting (Play mode without domain reload, below).
5. 6.7 LTS is due around the end of 2026. After upgrading, check again: reread the table below and confirm each fact tagged "verified on 6000.6" before relying on it.

**Watch for.** Asset packs, samples and tutorials written for Built-in or for 2022 LTS: borrow their ideas, but rewrite their API calls against this version. When old code is opened, the API Updater offers to rewrite members marked upgradable; how it behaves in batch mode is in [agent-control.md](agent-control.md).

**API facts** (check the installed version):
- `Application.unityVersion` reports the version of the running editor or player as a string (verified on 6000.6).
- Version defines such as `UNITY_6000_6_OR_NEWER` let one code base compile against several Unity versions (verified on 6000.6).
- Project Auditor ships inside the editor from 6.4; from 6.5 it lists APIs that became obsolete between editor versions, and 6.6 adds a URP settings analyzer and flags static fields that need a reset (verified on 6000.6).

## Renamed and removed APIs, 2022 LTS to 6.6

**Goal.** No call, setting or menu path from an older Unity reaches the project unchecked.

**Build.** Before writing an API from memory or from a tutorial, look it up in this table. When the compiler reports an obsolete member, migrate to the name its message gives, and log any row this table lacks in the handback.

**API facts** (verified on 6000.6, against the 6.0 to 6.6 upgrade guides, the 6.6 scripting reference, and the installed engine assemblies and packages). An obsolete member that warns still compiles, and the API Updater can rewrite the ones marked upgradable; one that errors, or one that was removed, stops compilation; a setting the engine no longer reads is ignored without a message.

| Old form | New form | Changed | Symptom of the old form on 6.6 |
| --- | --- | --- | --- |
| Built-in Render Pipeline; `Standard` and other Built-in shaders | URP with `Universal Render Pipeline/Lit` and the other URP shaders | Built-in deprecated in 6.5 | Built-in materials draw magenta in the editor; a build on the default Release code variant drops that magenta pass, so they can simply vanish |
| Post Processing Stack v2 (`com.unity.postprocessing`) | URP's own post: Volumes, plus Post Processing enabled on the camera ([final-image.md](final-image.md)) | never worked with URP | effects never appear, though the old package is still installable |
| URP Compatibility Mode; passes built on `Execute()` and `SetupRenderPasses` | the render graph: `RecordRenderGraph`, with passes added in `AddRenderPasses` | deprecated 6.0, removed 6.3; the `URP_COMPATIBILITY_MODE` escape removed 6.4 | old renderer features fail to compile, or compile and draw nothing |
| `Rigidbody.velocity`, `drag`, `angularDrag`; `PhysicMaterial`, `PhysicMaterialCombine`; `Rigidbody2D.velocityX`, `velocityY` | `linearVelocity`, `linearDamping`, `angularDamping`; `PhysicsMaterial`, `PhysicsMaterialCombine`; `linearVelocityX`, `linearVelocityY` | Unity 6.0 | obsolete warnings; the API Updater rewrites them |
| `FindObjectOfType`, `FindObjectsOfType`; `FindFirstObjectByType`; `FindObjectsByType` with a sort mode | `FindAnyObjectByType`; `FindObjectsByType(type)` or with `FindObjectsInactive`, unsorted | the first pair obsolete 6.0, the rest by 6.6 | obsolete warnings; results arrive in no fixed order, so sort them yourself |
| `GetInstanceID()`, `Resources.InstanceIDToObject`, int instance ids, `RaycastHit.colliderInstanceID` | `GetEntityId()`, `Resources.EntityIdToObject`, the 8-byte `EntityId`, `colliderEntityId` | deprecated 6.4, errors 6.5 | the code stops compiling; an id squeezed into an int loses half its data |
| Input Manager: `UnityEngine.Input`, `Input.GetAxis`, axes in Project Settings | Input System actions ([input-ui-and-audio.md](input-ui-and-audio.md)) | legacy and due for removal; new projects use the Input System | an error at the first old call, saying active input handling is set to the Input System package |
| Cinemachine 2: `Cinemachine` namespace, `CinemachineVirtualCamera`, `CinemachineFreeLook`, Transposer, Composer | Cinemachine 3: `Unity.Cinemachine`, `CinemachineCamera` with components such as `CinemachineFollow`, `CinemachineRotationComposer`, `CinemachineOrbitalFollow`, and `CinemachineInputAxisController` for input ([camera-and-animation.md](camera-and-animation.md)) | CM 3.0; a core package in 6.6, which upgrades CM2 projects on open | missing namespace and type errors; a camera that ignores the mouse |
| Navigation window, the Navigation Static flag, `OffMeshLink` | AI Navigation: `NavMeshSurface`, `NavMeshModifier`, `NavMeshModifierVolume`, `NavMeshLink`; Window > AI > Navigation Updater converts old scenes | AI Navigation 2.0 | no bake button where tutorials show one; agents find no NavMesh |
| `com.unity.textmeshpro` package | TextMesh Pro inside `com.unity.ugui`, then Window > TextMeshPro > Import TMP Essential Resources | Unity 6.0; the old package is now a stub | text objects with no default font until the resources are imported |
| Auto Generate lighting; Recalculate Environment Lighting | Generate Lighting in the Lighting window, or `Lightmapping.Bake` and `BakeAsync` ([lighting-and-shadows.md](lighting-and-shadows.md)) | 6.0 | after a sky change, ambient light and reflections still show the default sky |
| Enlighten Baked GI; the Progressive CPU Lightmapper; Enlighten Realtime GI | the Progressive GPU Lightmapper (the default for new projects since 6.3) or the Unity Compute Light Baker (6.6); Adaptive Probe Volumes for probe lighting | Enlighten Baked removed 6.0; CPU deprecated 6.6; Enlighten Realtime support ends after Unity 6 | deprecation notes; a bake that looks different after a backend switch |
| Build Settings window | Build Profiles (File > Build Profiles), with per-profile scene lists and graphics and quality overrides | 6.0; overrides 6.1; classic platform list hidden in new projects 6.4 | tutorial steps that no longer exist; a build that follows a profile's override instead of the project setting |
| "WebGL" platform; WebGPU behind an experimental flag | the "Web" platform; WebGPU supported from 6.6 but opt-in, with WebGL 2 the default ([performance-and-builds.md](performance-and-builds.md)) | renamed 6.0; WebGPU 6.6 | settings searched under the old name; compute-only features missing on WebGL 2 |
| Domain reload on entering Play mode | Reload Scene only in new projects; the bundled URP template skips scene reload too (below) | 6.6 | statics, singletons and static event handlers carry over from the last Play session |
| Dynamic batching | SRP Batcher, GPU instancing, GPU Resident Drawer ([performance-and-builds.md](performance-and-builds.md)) | deprecated 6.5, obsolete 6.6 | the setting is gone; more draw calls than an old tutorial predicts |
| Read/Write enabled for you at build time | Read/Write turned on in the import settings of meshes used by Mesh Colliders, Particle System Shape modules and terrain detail meshes, and of textures used by Shape modules and terrain detail painting ([assets-and-import.md](assets-and-import.md)) | textures 6.5, meshes 6.6 | an Inspector warning, then a failed build |
| `UIDocument`; UXML factory and traits classes | `PanelRenderer` ([input-ui-and-audio.md](input-ui-and-audio.md)); `[UxmlElement]` and `[UxmlAttribute]` | Panel Renderer 6.5; UI Document obsolete and factories and traits removed 6.6 | the Editor won't add a UI Document to a new GameObject, though existing ones keep working; compile errors in custom controls built on traits |
| Coroutines or `Task.Delay` for waits that touch Unity objects | `Awaitable`, each instance awaited once; coroutines still work (below) | a preference, not a removal | a second await of one instance throws or hangs; loops outlive their object |
| `UnityEngine.LowLevelPhysics2D`; `AddComponent(string)`; shortcut properties such as `GameObject.rigidbody`, `.camera` and `.renderer` | `Unity.U2D.Physics`, the Physics Core 2D API ([2d.md](2d.md)); `AddComponent<T>()` and `GetComponent<T>()` | removed or renamed 6.5 | compile errors |
| `UNITY_64`, `DEVELOPMENT_BUILD` | `UNITY_ENABLE_CHECKS`, `UNITY_INCLUDE_INSTRUMENTATION`, or `Debug.isDebugBuild` at runtime, chosen through Player > Other Settings > Managed Code Variant | deprecated 6.6, removal planned for 6.8 | analyzer warnings; a development build left on the default Release variant lacks the Rendering Debugger and URP profiling markers |
| One global `Editor.log` under `~/Library/Logs/Unity` | the project's own `Logs/Editor.log` ([agent-control.md](agent-control.md)) | 6.5 | a log reader watching the old path sees nothing new |
| `ModelImporter.isFileScaleUsed`, `normalImportMode`, `tangentImportMode`, `optimizeMesh`, `resampleRotations`, `splitTangentsAcrossSeams` | the members each error names, such as `useFileScale`, `importNormals`, `importTangents`, `optimizeMeshPolygons`, `resampleCurves` | errors 6.5 | import scripts stop compiling |
| Shader Graph's Reflection Probe node | a Custom Function node that samples reflection probes ([materials-and-shaders.md](materials-and-shaders.md)) | deprecated 6.5 | wrong reflections under Forward+ and Deferred+ |
| `_FORWARD_PLUS` shader keyword | `_CLUSTER_LIGHT_LOOP` | 6.1 | hand-written shaders that test the old keyword skip their Forward+ light loop |
| `LightShadowCasterMode.NonLightmappedOnly`, `Everything` | `ShadowMask`, `DistanceShadowMask` | 6.4 | rewritten automatically |
| PVRTC texture format | ASTC or ETC | deprecated 6.1, removed 6.4 | the format can't be selected |
| Intel (x86_64) macOS editor and players | Apple silicon ([performance-and-builds.md](performance-and-builds.md)) | deprecated 6.6 | deprecation notices; Intel support is set to go |
| `Library/Artifacts` | `Library/DataStore` in new projects | 6.6 | scripts that clear or measure the import cache miss it |
| The Reduce Version Control Noise setting; YAML word wrapping | removed; YAML lines are never wrapped ([project-hygiene.md](project-hygiene.md)) | 6.6 | after an upgrade, untouched assets show YAML diffs |
| `VisualElement.transform` | `style.translate`, `style.rotate`, `style.scale`, read back through `resolvedStyle` | deprecated 6.2 | obsolete warnings |

Changes you will see without touching any code:
- 6.0: light probes now light objects as brightly as lightmaps do; before, they were about 6% dimmer.
- 6.0: `AddForceAtPosition` and `AddExplosionForce` with `ForceMode.VelocityChange` or `ForceMode.Acceleration` now scale torque by the inertia tensor, so pushes spin bodies differently than in 2022 LTS.
- 6.0: textures created at runtime ignore the quality level's mipmap limit unless they opt in.
- 6.2: the `AfterRendering` injection point always runs after the final blit to the screen; a pass that drew into an intermediate texture there belongs at `AfterRenderingPostProcessing`.
- 6.4: `Object.Destroy` calls `OnDisable` on every descendant, not just the object and its direct children; remove workarounds that did this by hand, or the calls double.
- 6.4: the physics module can be removed from a project, but local Volumes stop working without it.
- 6.5 and 6.6: Render Pipeline Core no longer pulls in uGUI (6.5) or the Terrain module (6.6); a project that uses them must list them itself. New projects still include Terrain.
- 6.6: opening a Cinemachine 2 project upgrades it to Cinemachine 3, a different API and data format; keeping Cinemachine 2 means pointing the manifest at a local copy.

## Choosing the render pipeline

**Goal.** One pipeline, chosen before the first asset for reasons the plan can state: URP, unless the user approves otherwise.

**Choose.**
- URP for every new project, created from the Hub's Universal 3D template, or from Universal 2D for a sprite-based game ([2d.md](2d.md)). It runs on Apple silicon Macs through Metal and on the Web through WebGL 2 and WebGPU, it is where Unity is adding new rendering features, and it brings Shader Graph, Adaptive Probe Volumes, decals, Forward+ and its own post stack.
- HDRP only through the route below, with the user's approval, for a Mac-only showcase. HDRP supports neither WebGL nor WebGPU.
- Built-in never for a new project. It has been deprecated since 6.5, and Unity keeps it running through 6.7 LTS for existing games only.
- Decide before building: a URP project isn't compatible with HDRP or Built-in, so switching later means converting materials, shaders, lighting and post.

**Build.**
1. Create the project from Universal 3D ([setup.md](setup.md)). The bundled URP template ships two quality levels, PC and Mobile, each with its own URP asset and renderer: PC renders with Forward+, Mobile with Forward at a render scale of 0.8. Shape these into the project's tiers ([performance-and-builds.md](performance-and-builds.md)). Both URP assets also apply the template's sample volume profile (Neutral tone mapping, bloom 0.25, vignette 0.2) to every scene, and its camera has post-processing on and no anti-aliasing, so a project left as created already uses post ([final-image.md](final-image.md)).
2. Check what is active, not what you expect. Project Settings > Graphics names the default pipeline asset, and each quality level can override it. The template leaves the default empty and assigns an asset per quality level, so any quality level whose pipeline asset field is empty renders with Built-in.
3. Convert Built-in material references, quality levels and prebuilt shaders with Window > Rendering > Render Pipeline Converter. Custom Built-in shaders need rewriting, preferably in Shader Graph ([materials-and-shaders.md](materials-and-shaders.md)).
4. Record the pipeline, its version, and each tier's renderer and rendering path in `BRIEF.md`.

**Watch for.** Packs and tutorials built for Built-in. Surface shaders, `GrabPass`, `OnRenderImage`, `OnPreRender` and camera command buffers don't run in URP. Each has a URP route: Shader Graph or a URP shader, the Scene Color node or a renderer feature, a render pass, or `RenderPipelineManager` callbacks.

**Critic checks.** PASS when no surface, particle or UI element in any still shows the flat magenta of a missing or incompatible shader, and every tier's captures show the same set of objects. FAIL signs: magenta or pink patches; an object present in one tier's still and missing from another's.

**Diagnose.**
- Magenta in the editor → a Built-in or broken shader; the console names it.
- Right in one quality level, magenta or missing in another → that level has no URP asset, or one with different renderer features.
- An effect from a tutorial does nothing → it hooks a Built-in callback that URP never calls.

**Start here** (adjust to the goal): Universal 3D, with the template's PC quality level as the Mac's top tier.

**API facts** (check the installed version):
- `GraphicsSettings.currentRenderPipeline` returns the asset in use: the current quality level's override (`QualitySettings.renderPipeline`) when it has one, otherwise `GraphicsSettings.defaultRenderPipeline`, where null means Built-in (verified on 6000.6).
- The Render Pipeline Converter converts Built-in quality levels, material references and prebuilt shaders, but not custom shaders (verified on 6000.6).
- URP supports neither `GrabPass` nor surface shaders, and doesn't call `OnRenderImage`, `OnPreCull` or `OnPreRender`; the Scene Color node, a renderer feature and `RenderPipelineManager.beginCameraRendering` take their places (verified on 6000.6).

## What URP lacks, and where the substitutes are

**Goal.** The plan knows every gap up front and names the substitute and the file that teaches it, instead of finding mid-build that a feature exists only in HDRP.

**Build.** On 6.6, the feature comparison page lists these as missing from URP. Plan the substitute before the first round:

| Not in URP on 6.6 | Substitute | Taught in |
| --- | --- | --- |
| Automatic exposure (eye adaptation) | fixed exposure per area, blended by script between zones | [final-image.md](final-image.md) |
| Physical light units | intensities set by ratio against one calibrated sun | [lighting-and-shadows.md](lighting-and-shadows.md) |
| Real-time GI: screen-space GI, and Enlighten Realtime after Unity 6 | Adaptive Probe Volumes with lighting scenarios and sky occlusion, reflection probes, placed fill lights | [lighting-and-shadows.md](lighting-and-shadows.md) |
| Screen-space and planar reflections | box-projected reflection probes; a planar reflection pass for water | [lighting-and-shadows.md](lighting-and-shadows.md), [sky-weather-and-water.md](sky-weather-and-water.md) |
| Physical sky, gradient sky, cloud layers, volumetric clouds, atmospheric scattering | skybox materials (procedural, HDRI), sky shaders, layered cloud cards or domes | [sky-weather-and-water.md](sky-weather-and-water.md) |
| Volumetric and local fog | the pipeline's linear or exponential fog, plus height fog in shaders or a full-screen pass | [sky-weather-and-water.md](sky-weather-and-water.md) |
| The water system | Shader Graph water on the depth and opaque textures | [sky-weather-and-water.md](sky-weather-and-water.md) |
| Subsurface scattering, hair, fabric, eye, iridescence and anisotropy models | custom lighting in Shader Graph, wrapped diffuse, thickness masks, hair cards | [materials-and-shaders.md](materials-and-shaders.md) |
| Shadows from semi-transparent surfaces; decals on transparents; tessellation | alpha-clipped or dithered shadows; mesh decals; parallax or real geometry | [materials-and-shaders.md](materials-and-shaders.md) |
| Blending between shadow cascades; contact shadows; real-time area lights | tuned splits and a fade at the shadow distance; SSAO and baked contact; baked area lights or soft spots | [lighting-and-shadows.md](lighting-and-shadows.md) |
| DLSS, the TAA upsampler, software dynamic resolution | STP, FSR 1, or a lower render scale | [final-image.md](final-image.md), [performance-and-builds.md](performance-and-builds.md) |
| VFX Graph on WebGL 2 (it needs compute) | the Particle System | [effects.md](effects.md) |

Unity has announced plans to bring several of these into URP, among them automatic exposure, physical light units, a physical sky, real-time GI and screen-space reflections. After upgrading, check the comparison page again before building a substitute.

**Watch for.** Switching pipelines to get one missing feature. When the goal names one of these features ("volumetric god rays", "a real ocean"), the plan names the substitute and the bar grades what the viewer sees, never which pipeline feature produced it.

## The HDRP route

**Goal.** A Mac-only showcase that truly needs HDRP's light and atmosphere gets it, with the costs stated up front.

**Choose.** Propose HDRP only when every condition holds, and get the user's explicit approval before creating the project:
- The deliverable runs on the Mac only; HDRP has no Web target.
- The goal depends on something URP can't stand in for well: volumetric clouds and fog, the water system, a physical sky with atmospheric scattering, automatic exposure, physical light units, or skin, hair and fabric shading.
- It's a showcase, not a game meant to grow for years: Unity keeps HDRP in maintenance and plans no new features for it.

**Build.** Create the project from the Hub's HDRP template; HDRP 17.6 ships with 6.6 and runs on macOS through Metal. Work from HDRP's own documentation for that version, because this module's URP specifics (the URP asset, renderer features, URP's Volume overrides) don't carry over one for one. Keep the module's process: one output owner, the no-post still, a proven capture route and the same critic checks. Record the pipeline and the user's approval in `BRIEF.md` and `PLAN.md`.

**Watch for.** HDRP's default frame costs far more than URP's on laptop GPUs, so put a frame budget in the brief and measure in the first round. Set HDRP light intensities from real-world values in its physical units, never from URP-style numbers.

## Color space and HDR

**Goal.** Lighting runs in linear space on HDR values, color maps are decoded once, data maps never are, and one tone mapper turns the result into display colors.

**Build.**
1. Keep Color Space at Linear (Project Settings > Player > Other Settings > Rendering), as the URP templates start. Switching it changes how every texture is sampled, and HDR Output needs Linear.
2. Import color maps as sRGB and data maps (normal, mask, metallic-smoothness, height, flow) as linear ([assets-and-import.md](assets-and-import.md)).
3. Keep HDR on in every URP asset and let cameras inherit it; HDR precision and grading mode are set in [final-image.md](final-image.md).
4. Treat emissive and light colors as HDR: an emissive color pushed above 1 is how an emitter reaches bloom.
5. When a script blends or averages colors, convert sRGB values with `Color.linear` first and back with `Color.gamma` for display.
6. HDR Output to HDR displays is a separate Player option, off in the templates. URP supports it on Metal Macs but not on the Web; leave it off unless the brief targets HDR displays ([final-image.md](final-image.md)).

**Watch for.** A project switched to Gamma by an old asset or tutorial; textures whose sRGB setting disagrees with their content; HDR turned off on a URP asset or camera, which clips highlights and starves bloom.

**Critic checks.** PASS when the deepest shadows stay deep with no milky veil, familiar materials sit at believable saturation, and normal-mapped surfaces shade evenly from the key light's side. FAIL signs: a gray film across the frame; neon or crushed mid-tones; lumpy shading on surfaces meant to be smooth.

**Diagnose.**
- One material washed out and pale → its color map imported with sRGB off.
- Flat, clipped highlights and weak bloom → HDR off on the URP asset or the camera.
- Lumpy shading lit from odd sides → a normal map not imported as a normal map.

**API facts** (check the installed version):
- Color Space is a Player setting with Linear and Gamma options; URP supports both, HDRP only Linear (verified on 6000.6).
- URP's HDR Output works only in Linear color space and supports macOS on Metal; the Web isn't on its platform list (verified on 6000.6).
- `Color.linear` converts an sRGB color to linear through the inverse sRGB curve, and `Color.gamma` applies the curve (verified on 6000.6).

## Frame loop, fixed timestep and time scale

**Goal.** Movement is identical whatever the frame rate, physics advances in fixed steps, and a capture can freeze time at an exact value.

**Build.**
1. Put per-frame logic and input reading in `Update`, scaled by `Time.deltaTime`.
2. Put forces, velocity changes and other physics in `FixedUpdate`; by default the physics step runs right after it. Read input in `Update`, store the intent, and apply it on the next fixed step.
3. Move anything that follows a moving thing (cameras, UI anchors, aim lines) in `LateUpdate`, which runs after every `Update`.
4. The fixed timestep defaults to 0.02 s, 50 steps a second. On a 60 or 120 Hz display, bodies moved by physics judder unless their Rigidbody interpolates between steps; [characters-physics-and-feel.md](characters-physics-and-feel.md) owns that setting. Don't shrink the timestep to hide judder: physics cost rises with every extra step.
5. A slow frame is capped at `Time.maximumDeltaTime`, which also limits how much physics catches up, so after a hitch the world slows down instead of jumping ahead.
6. Pause and slow motion change `Time.timeScale`; code that must keep real speed (pause menus, UI tweens) reads `Time.unscaledDeltaTime`.
7. For deterministic capture, set `Time.captureDeltaTime`, so game time advances one fixed step per frame whatever the real frame time. Unscaled time ignores it, so pin anything driven by unscaled time separately ([validation.md](validation.md)).
8. Draw every visible random choice from a seeded generator owned by its system and keyed by stable ids, so load order can't change a layout. `UnityEngine.Random` is one static stream shared with every other script, and reseeding it with `Random.InitState` reseeds it for all of them.
9. Cap the frame rate on purpose: on desktop, `Application.targetFrameRate` is ignored while `QualitySettings.vSyncCount` is above 0. The template's quality levels both leave vSync off, so an empty scene runs as fast as it can ([performance-and-builds.md](performance-and-builds.md)).

**Watch for.** Physics in `Update`; movement without `deltaTime`; smoothing by a fixed fraction per frame; a second clock inside a plugin; timers on `Time.time` that keep counting through a pause meant to freeze them.

**Diagnose.**
- Things move faster on a faster display → changes applied per frame instead of per second, or physics in `Update`.
- A body judders while the camera follows it → no interpolation on a body stepped at 50 Hz and shown faster, or a camera that moves before its target.
- Fast objects pass through walls → the collision detection mode, not the timestep ([characters-physics-and-feel.md](characters-physics-and-feel.md)).
- Two captures of the same moment differ → unpinned time, or a random draw outside the seeded generators.

**Start here** (adjust to the goal): keep the default 0.02 s fixed timestep, and interpolate every body the camera follows.

**API facts** (check the installed version):
- With `Physics.simulationMode` at `FixedUpdate`, the physics step runs directly after `MonoBehaviour.FixedUpdate`; the `Update` and `Script` modes move it after `Update` or hand it to `Physics.Simulate` (verified on 6000.6).
- `Time.maximumDeltaTime` defaults to a third of a second and also caps the physics time simulated between two frames (verified on 6000.6).
- `Time.timeScale` scales the time reported to `Update` and `FixedUpdate`, and 0 stops game time (verified on 6000.6).
- A non-zero `Time.captureDeltaTime` advances `Time.time` by that step, times `timeScale`, every frame regardless of real time, and leaves `Time.unscaledTime` alone (verified on 6000.6).

## Script execution order

**Goal.** Code that depends on order runs in an order you set, never in one that merely happened to work.

**Build.**
1. Within one component, `Awake`, `OnEnable` and `Start` run before its first `Update`; each frame runs any fixed steps, then `Update`, then `LateUpdate`; `OnDisable` and `OnDestroy` run at teardown.
2. Between scripts, order is undefined until you set it. When one system must run first (input, then movement, then camera), order those scripts with `[DefaultExecutionOrder]` or in Project Settings > Script Execution Order.
3. Between instances of the same script, order can't be set. When it matters, let one manager update them in a defined order.
4. Run setup that must exist before any scene object wakes in a `[RuntimeInitializeOnLoadMethod]` method, choosing its load type.
5. `Destroy` takes effect only after the current update loop, so the object still answers queries for the rest of that frame (last section).

**Watch for.** One object's `Awake` reading another object's state; one `Start` depending on another `Start`; additive scene loads, where the configured order runs scene by scene.

**Diagnose.** A bug that comes and goes between runs or machines → undefined order between two scripts; give them an explicit order. A camera a frame behind its target → it moves in `Update`, possibly before the target.

**API facts** (check the installed version):
- `[DefaultExecutionOrder]` values don't appear in the Script Execution Order window, and the window's value wins when both set one; neither affects `[RuntimeInitializeOnLoadMethod]`, `OnDisable` or `OnDestroy` (verified on 6000.6).
- Scripts with equal or default order run in an order Unity doesn't promise, which can change between builds, machines and editor versions (verified on 6000.6).
- `RuntimeInitializeLoadType.SubsystemRegistration` runs at startup before the first scene loads, and `BeforeSceneLoad` and `AfterSceneLoad` fall on either side of the first scene's `Awake` calls (verified on 6000.6).
- Since 6.4, `Object.Destroy` on a GameObject calls `OnDisable` on the components of all its descendants (verified on 6000.6).

## Play mode without domain reload

**Goal.** Every Play session starts from the same state, so two captures in a row show the same thing.

**Build.**
1. Read Project Settings > Editor > Enter Play Mode Settings and record the choice in `PLAN.md`. New 6.6 projects use Reload Scene only, and the bundled URP template's saved setting turns scene reload off as well. Unity recommends keeping domain reload off, so make the code correct rather than turning it back on.
2. Reset static state when Play starts. Mark static fields with `[AutoStaticsCleanup]`, which needs the containing type to be `partial`, or write a reset method marked `[OnEnteringPlayMode]`. Give statics that must survive between sessions, such as id counters, `[NoAutoStaticsCleanup]`.
3. Clear static events and static handler lists on Play entry, and unsubscribe instance handlers in `OnDisable` or `OnDestroy`.
4. With scene reload off too, scene objects aren't rebuilt, and non-serialized fields keep the values they had when Play last ended. Initialize them in `Awake` or `OnEnable`, never in field initializers or constructors.
5. Find what still needs a reset: turn on the statics analyzer with a `.globalconfig` file beside the assembly definition (or in a folder under `Assets/` for scripts without one), or open Project Auditor's domain reload issues.
6. Stop background work when Play ends by passing `Application.exitCancellationToken` to anything that runs off the main thread or loops forever (next section).
7. Prove it: enter Play twice in one editor session and capture the same state both times; the stills and logs must match ([validation.md](validation.md)).

**Watch for.** Singletons that test "already exists" against a stale static; `DontDestroyOnLoad` managers that remember the last session; runtime writes to ScriptableObject assets, which the editor keeps whatever the reload setting.

**Diagnose.**
- The second Play session differs from the first → static state left over from the first.
- Handlers fire twice, or once per past session → a static event never cleared.
- A counter or score starts where the last session ended → a static field with no reset.
- Logs, requests or file writes continue after Play stops → background work with no exit token.

**API facts** (check the installed version):
- New 6.6 projects default to Reload Scene only; with domain reload off, static fields keep their values and static events keep their subscribers from one Play session to the next, and non-serialized fields keep their Play mode values (verified on 6000.6).
- `[AutoStaticsCleanup]` and `[NoAutoStaticsCleanup]`, in `Unity.Scripting.LifecycleManagement`, generate resets on entering Play mode; code generation is on by default, and the analyzer's UAL warnings stay off until a `.globalconfig` enables them (verified on 6000.6).
- `EnterPlayModeOptions` is a flags enum with `DisableDomainReload` and `DisableSceneReload`; `[OnEnteringPlayMode]` and `[OnExitingPlayMode]` mark methods to run on those transitions (verified on 6000.6).
- Unity doesn't stop background code when Play mode ends, and `Application.exitCancellationToken` is the documented way to cancel it (verified on 6000.6).

## Async code: Awaitable and coroutines

**Goal.** Waits and sequences run where Unity objects may be touched, end when their owner goes away, and never outlive Play mode.

**Choose.**
- A coroutine for a simple timed sequence owned by one MonoBehaviour. It stops when its GameObject is deactivated or the component is destroyed, but not when the component is merely disabled.
- `Awaitable` with `async` and `await` for sequences that return values, chain scene loads or web requests, or hop to a background thread and back.
- A .NET `Task` only when a result must be awaited more than once or combined with WaitAll or WaitAny; started on the main thread, it resumes on the next frame's `Update`. Never `Task.Delay`, `Task.Run` or a thread-pool task on a Web build (Watch for).
- The job system with Burst for parallel number crunching, which Awaitable isn't built for.

**Build.**
1. Pass `destroyCancellationToken` to waits owned by a MonoBehaviour, caching it before the object is destroyed, and `Application.exitCancellationToken` to anything that could outlive Play mode.
2. Await each Awaitable exactly once; keep the result, never the instance.
3. Expect an Awaitable's continuation to run at once, in the frame its completion fires.
4. After `Awaitable.BackgroundThreadAsync`, touch no Unity API until `Awaitable.MainThreadAsync`. Release builds don't check for this, and the result can be a crash.
5. Drive per-frame work for many objects from one manager's `Update`, not from an await loop inside each object.

**Watch for.** A coroutine that yields an `Awaitable<T>`, which isn't allowed; long chains that no token can cancel. On the Web, managed threads don't run: `System.Threading` and `System.Timers` timers never fire, `CancellationTokenSource` timeouts never trigger, and `Task.Delay`, `Task.Run` and `Parallel` hang the page for good. Time every wait and timeout there with an Awaitable, a coroutine or the game clock; the Web thread settings are in [performance-and-builds.md](performance-and-builds.md).

**Diagnose.**
- An exception or a hang on a second await → one Awaitable awaited twice.
- A loop still logging after its object is gone or Play has stopped → no cancellation token.
- A crash only in release builds → a Unity API called from a background thread.

**API facts** (check the installed version):
- Awaitable instances are pooled, so awaiting one more than once is undefined and can throw or deadlock; there is no built-in WaitAll or WaitAny (verified on 6000.6).
- Awaitable continuations run synchronously when completion fires, while a `Task` awaited on the main thread resumes on the next frame's `Update` (verified on 6000.6).
- `NextFrameAsync`, `WaitForSecondsAsync`, `EndOfFrameAsync`, `FixedUpdateAsync`, `BackgroundThreadAsync` and `MainThreadAsync` cover frame, time and thread waits, and `AwaitableCompletionSource` completes an Awaitable from code (verified on 6000.6).
- A coroutine may `yield return` an `Awaitable` but not an `Awaitable<T>`, and setting `enabled = false` on its component doesn't stop it (verified on 6000.6).

## Destroyed objects and Unity's null

**Goal.** No code trusts a reference to an object that has been destroyed.

**Build.**
1. Test Unity objects with `== null`, `!= null` or `if (obj)`. Unity overloads these, so an object whose engine side is gone compares equal to null even while its C# shell lives on.
2. Never use `?.`, `??`, `??=`, `is null`, `is not null` or `ReferenceEquals` on Unity objects: they test only the C# reference, so a destroyed object looks alive.
3. A Unity object held in an interface or `object` variable compares with plain C# equality, which skips Unity's overload; cast it to its Unity type before testing.
4. `Destroy` takes effect after the current update loop, so for the rest of that frame the object still exists and `== null` is false. When later code in the same frame must skip it, disable it or drop it from your lists yourself. `DestroyImmediate` belongs to editor code.
5. Unsubscribe destroyed listeners from events, or the event calls into a dead object.

**Watch for.** Null-conditional chains pasted from general C# code; caches of components that outlive their objects; serialized references to deleted assets or missing scripts, which read as null in the same way.

**Diagnose.** A null check passes but the next call throws → a destroyed object reached through `?.`, `??` or an interface. An object still counted after it was destroyed → `Destroy` hasn't taken effect yet this frame.

**API facts** (check the installed version):
- Unity's `==` on `UnityEngine.Object` also checks whether the native object still exists, so a destroyed object compares equal to null while `Object.ReferenceEquals(obj, null)` returns false (verified on 6000.6).
- The `?.` and `??` operators are unsupported on Unity objects, because they can't be overloaded to treat destroyed objects as null (verified on 6000.6).
- `Object.Destroy` removes the object after the current Update loop and before rendering; with a delay, it fires that many seconds later even if the caller is disabled or destroyed meanwhile (verified on 6000.6).

## Symptom → cause

| Symptom | Likely cause | First check |
| --- | --- | --- |
| Code from a tutorial or memory won't compile | a member renamed or removed since 2022 LTS | the table above and the full compiler message |
| Magenta surfaces | a Built-in or broken shader under URP | the console; the Render Pipeline Converter |
| One quality tier renders differently, or magenta | that quality level has no URP asset, or another renderer | each quality level's pipeline asset |
| Post effects from a tutorial never appear | Post Processing v2, or the camera's Post Processing toggle off | the package list; the camera ([final-image.md](final-image.md)) |
| New sky, but old ambient light and reflections | lighting not generated since the sky changed | Generate Lighting ([lighting-and-shadows.md](lighting-and-shadows.md)) |
| One material looks washed out | its color map imported with sRGB off | the texture's import settings |
| Flat, clipped highlights and weak bloom | HDR off on the URP asset or the camera | the URP asset's HDR setting |
| Motion speed depends on the display | per-frame increments, or physics in `Update` | where the motion is applied |
| A followed body judders | no Rigidbody interpolation, or the camera moves before its target | interpolation; camera code in `LateUpdate` |
| The second Play session differs from the first | statics or static events survived | Enter Play Mode Settings; the static resets |
| Handlers fire twice | a static event never cleared | where the event is subscribed and cleared |
| Logs keep coming after Play stops | background work with no exit token | `Application.exitCancellationToken` |
| A null check passes, then the next call fails | `?.`, `??` or an interface on a destroyed object | the comparison used |
| A Web build hangs, or a timer never fires there | `Task.Delay`, `Task.Run`, a `System.Threading` timer or a token timeout on the Web | the waits in the code path (Async code) |
| A log reader sees nothing new after an upgrade | `Editor.log` moved into the project in 6.5 | the project's `Logs/Editor.log` |
| A development build lacks the Rendering Debugger | Managed Code Variant left at Release | Player > Other Settings > Managed Code Variant |
