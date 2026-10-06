# Unity assets and import: sources and licenses, models, glTF, Blender, textures, Read/Write, audio and the ledger

API facts verified on Unity 6.6 (6000.6.4f1, 2026-10-06). Check the project's Unity version first (ProjectSettings/ProjectVersion.txt); if it differs, confirm in that version's official docs or the installed packages. The installed version wins.

Read when assets enter a Unity project: choosing sources and checking licenses, importing models, glTF files and Blender exports, setting texture and audio import options, and keeping the ledger. Material setup after import is in [materials-and-shaders.md](materials-and-shaders.md), texture budgets per tier in [performance-and-builds.md](performance-and-builds.md), `.meta` files and what to commit in [project-hygiene.md](project-hygiene.md), and Blender workers in [../pipelines.md](../pipelines.md).

## Contents

- Sources and licenses
- Asset Store and Mixamo files
- The engine's generators
- The sourcing ledger and provenance
- Units, axes and scale
- Importing FBX and other model files
- Importing glTF with glTFast
- Blender to Unity
- Texture import: color, data and normal maps
- Compression, size and mipmaps per platform
- Read/Write in 6.6
- Audio import basics
- Symptom → cause

## Sources and licenses

**Goal.** Every asset in the project may be shown, shipped and committed under its license, and the default sources need no permission at all.

**Choose**, in this order:
1. Original work: geometry and textures made in code, in Blender by agents, or by the user.
2. CC0 libraries: Poly Haven (HDRIs, textures, models), ambientCG (materials and textures), Kenney (2D, 3D, UI and audio packs), and Quaternius (low-poly models, many of them animated).
3. Other libraries asset by asset, reading each license: CC-BY needs on-screen or end-credit attribution, a non-commercial license never belongs in a game that could be sold, and share-alike terms can bind the whole project. No stated license means don't use it.
4. Asset Store and Mixamo files only as the next section allows.

**Build.**
1. Download through each site's normal pages, or through an API under that API's own terms; never scrape.
2. Keep the license text or license page URL with every download, and write the ledger row before the asset is used (below).
3. Use the asset files themselves, not a site's preview renders, logos or page images, which those sites keep under their own rights.

**Watch for.**
- Sites that mix licenses per asset, so "free" doesn't mean CC0; paid tiers of a CC0 library with their own terms; a credit logo used without permission.
- Dated note (October 2026): Poly Haven, ambientCG and Kenney state that their assets are CC0, with no attribution required and redistribution allowed; Kenney asks that its logo not be used; Quaternius marks its free pack contents CC0, and its paid Source tier, which adds ready Unity URP projects, comes with that tier's own terms. Poly Haven's terms forbid scraping its site without permission and put its public API under separate terms.

## Asset Store and Mixamo files

**Goal.** One policy, kept here, governs Asset Store and Mixamo files: they stay within their terms, never reach a public repository, and Asset Store files reach the agent only when the user has allowed a specific asset.

**Build.**
1. **By default, agents don't open, read, edit or import Asset Store files**, Unity's Starter Assets included. Build from CC0 sources, the user's own assets and code the agent writes, such as its own character controller ([characters-physics-and-feel.md](characters-physics-and-feel.md)). Reference an Asset Store file only by path or GUID, and stop and ask when a task needs its contents.
2. **The user can explicitly allow a specific Asset Store asset for a private project.** Then record the decision (asset, version, project, date) under Policies in `BRIEF.md` and in the asset's ledger row; keep its files out of every public repository (a folder git ignores, a README line saying what to download, and CC0 stand-ins in the public repository; [project-hygiene.md](project-hygiene.md)); and import it into a scratch copy of the project first, reading the console there before it enters the real one.
3. Why the default is closed: the end-user license lets an asset be embedded in a product that adds substantial original content, and distributed only as part of that product, and section 2.2.1.1(g) bars using Asset Store assets for training AI or machine-learning models, and names using them as inputs to such programs, without consent from the provider or Unity. This is a cautious reading, not legal advice.
4. Asset Store editor extensions, scripting and services assets are licensed per seat, on at most two computers.
5. **Mixamo files are user-brought:** the user downloads them (an Adobe sign-in). They are free for any project with no credit required, but raw character and animation files may not be distributed, free distribution included, except to members of the project team, and the content may not train machine-learning models. Commit raw files only to a private repository the team shares, never to a public one, and ship them only inside builds.
6. Samples imported from Unity packages (Shader Graph, URP, Cinemachine) come under the Unity Companion License; give each a ledger row.

**Watch for.**
- "Free" Asset Store assets, which are still under the same license; an allowed asset's demo scene pulled into the build; an Asset Store script pasted into the agent's own context to "see how it works".
- Dated note (October 2026): the Asset Store terms were last updated on December 4, 2024, and Mixamo's licensing is described in Adobe's Mixamo FAQ; read the current versions before relying on either. Starter Assets' own pages disagree about their license (the Unity Companion License in the description, the Asset Store license in the license field, and a support article that forbids redistribution) and list 2022.3 and 6000.0 LTS, not 6.6.

## The engine's generators

**Goal.** Assets from Unity's built-in generative tools appear only by the user's choice, and stay traceable and removable.

**Build.**
1. Leave Unity AI and its generators off; this module never needs them. Use them only when the user turns them on, since they cost Unity Credits (a Personal license gets a trial, then a paid credit subscription).
2. Partner models behind some generators carry their own terms, which the user accepts, not the agent.
3. Every generated asset carries "UnityAI" metadata that the editor's search finds. Give each a ledger row marked as generated, with that tag, so it can be found and removed later.
4. The user owns inputs and outputs but stays responsible for making sure a generated asset doesn't infringe anyone's rights.

**Watch for.** Dated note (October 2026): Unity's AI guiding principles, last updated August 19, 2026, describe the metadata tag, input and output ownership, and the credit model; check them again before relying on these points.

## The sourcing ledger and provenance

**Goal.** Every visible element traces to a source and a license, as Forge's ledger requires, and the handoff check can prove it.

**Build.**
1. Keep `art/LEDGER.md` in Forge's format from the first third-party asset ([../project-files.md](../project-files.md)).
2. Fill Source with one of: authored (by whom, with what), procedural (the script's path), downloaded (site, asset page URL, date), user-supplied (Mixamo, or an Asset Store asset the user allowed: name and version, the user's decision, and where the files live outside any public repository), or generated (the engine tool and its UnityAI tag).
3. Fill License with CC0, CC-BY plus the exact credit text, the Asset Store license, Mixamo's terms, the Unity Companion License, or the user's own.
4. Note import settings that change an asset's meaning, such as a channel swizzle or a scale factor.
5. Before handoff: no placeholder rows, every CC-BY asset credited in the build, no non-commercial asset, and no Asset Store or raw Mixamo files in a public repository.

## Units, axes and scale

**Goal.** Every asset arrives at real-world scale and upright, so physics, light and pieces from different builders agree.

**Build.**
1. One unit is one meter, and +Y is up. Record both in the PLAN's units contract ([router.md](router.md), Contracts builders share).
2. Fix scale at export where possible, so imports keep a Scale Factor of 1; otherwise set Scale Factor or Convert Units on the model.
3. For Z-up sources, Bake Axis Conversion writes the axis change into the mesh and animation data rather than rotating the root at runtime, so the root keeps an identity rotation.
4. Check every new asset next to a human-scale reference (a 1.8 m figure or a 1 m cube) in its gate still.

**Critic checks.** PASS when doors, steps, furniture and characters sit at believable human scale against each other in every still. FAIL signs: knee-high doorways; giant pebbles; props that dwarf the player.

**API facts** (check the installed version):
- The model importer's Scale Factor exists because Unity's physics treats one unit as one meter; Convert Units applies the file's own unit scale (verified on 6000.6).
- Bake Axis Conversion bakes the axis conversion into vertex and animation data; turned off, Unity compensates on the root Transform at runtime instead (verified on 6000.6).

## Importing FBX and other model files

**Goal.** Models import with correct meshes, normals, UVs and colliders, and end up on project materials in URP.

**Build.**
1. Use FBX where possible; Unity also reads OBJ, DAE and DXF. Never commit `.blend`, `.max` or `.ma` files expecting them to import: those need the authoring application installed on every machine that opens the project.
2. On the Model tab: Mesh Compression off for hero assets; Read/Write only where 6.6 requires it (below); Normals set to Import, or Calculate with a smoothing angle for raw scans; Tangents for normal-mapped meshes; Generate Lightmap UVs for lightmapped static meshes ([levels-and-geometry.md](levels-and-geometry.md)); Generate Colliders only for static scenery; Generate Mesh LODs for dense meshes ([performance-and-builds.md](performance-and-builds.md)).
3. On the Materials tab, Import via MaterialDescription lets URP build a Lit material from the file's basic color, glossiness and opacity. Treat that as a starting point and remap each material slot to a project material, authored with real maps ([materials-and-shaders.md](materials-and-shaders.md)).
4. Leave rigs and animation clips to [camera-and-animation.md](camera-and-animation.md), and gate each hero asset with a turnaround before it enters a scene ([../pipelines.md](../pipelines.md)).

**Watch for.** Search Textures Globally, a legacy option that can bind the wrong texture when names repeat; sRGB Albedo Colors left on from legacy material modes in a linear project; moving meshes with generated mesh colliders.

**API facts** (check the installed version):
- Unity reads FBX, DAE, DXF and OBJ as standard model formats and uses FBX internally; proprietary files such as `.blend` import only where their application is installed (verified on 6000.6).
- Material Creation Mode is None, Standard (Legacy) or Import via MaterialDescription, and Location defaults to Use Embedded Materials, with external materials marked legacy (verified on 6000.6).
- URP's model import maps an FBX material's diffuse color to `_BaseColor`, its glossiness to `_Smoothness` and its opacity to transparency on a URP Lit material (verified on 6000.6).

## Importing glTF with glTFast

**Goal.** glTF and GLB files import in the editor, or load at runtime, with their PBR materials intact.

**Build.**
1. Unity doesn't read glTF on its own, and the editor doesn't bundle an importer. The agent adds Unity's glTFast package (`com.unity.cloud.gltfast`) through the Package Manager, with the user's yes for a new package ([project-hygiene.md](project-hygiene.md)), and confirms in its docs that the installed version supports this editor.
2. Editor import turns `.gltf` and `.glb` files into assets through a scripted importer. Materials use glTFast's own shader graphs rather than URP Lit, and the glTF conventions (roughness, occlusion, texture transforms) are handled for you.
3. Runtime loading needs every shader variant the files will use in the build: capture a ShaderVariantCollection while loading representative files in the editor, or keep placeholder materials in a Resources folder. A missing shader renders magenta; a stripped variant renders subtly wrong unless strict shader variant matching is on.
4. glTFast frees mesh data after uploading it to the GPU by default, so meshes meant for colliders need its keep-mesh-data define.
5. If another package also imports glTF, turn one importer off; glTFast has a define for its own.

**Watch for.** Draco, meshopt and KTX2 compressed files, which need glTFast's optional packages; runtime loading on the Web, where memory is tight ([performance-and-builds.md](performance-and-builds.md)).

**API facts** (check the installed version):
- With strict shader variant matching on (Player > Other Settings), a player build draws a missing variant with the error shader and logs the shader and keywords; off, Unity silently uses the closest variant (verified on 6000.6).

## Blender to Unity

**Goal.** Assets built by Blender workers arrive with the same scale, orientation, names and normals every time.

**Build.**
1. Export FBX (or glTF through glTFast) from a headless worker per asset; the command shape, exit codes and turnaround gate are in [../pipelines.md](../pipelines.md).
2. Before export, apply scale and rotation and model in meters, so the Unity import keeps a Scale Factor of 1.
3. Export only the asset's own objects, with meaningful mesh and material names, because Unity remaps materials by name.
4. Export authored normals and smoothing, and import with Normals set to Import; blend shape normals need smoothing groups in the FBX.
5. Unwrap a second UV set for lightmaps in Blender when lightmap quality matters, or let Unity generate one.

**Watch for.** `.blend` files saved into `Assets/`, which import only where Blender is installed; Blender's numbered backup files committed alongside them.

## Texture import: color, data and normal maps

**Goal.** Every texture is decoded with its true meaning: color once, data never, and normals in the convention Unity expects.

**Build.**
1. Use Texture Type Default for color and data maps, Normal map for normal maps, and Sprite for 2D ([2d.md](2d.md)).
2. Turn sRGB (Color Texture) on for base color, emission and UI art, and off for metallic-smoothness, occlusion, masks, height and flow maps.
3. Import normal maps as Normal map, flip the green channel for DirectX-style maps, and use Create From Grayscale only for quick bumps from a height map.
4. Repack channels at import with Swizzle. For example, a glTF-style metallic-roughness texture (occlusion red, roughness green, metallic blue) maps to URP's layout with red from blue, green from red, blue at Zero and alpha from One Minus Green; check the alpha in the preview.
5. For transparent or cut-out color maps, enable Alpha Is Transparency to stop dark fringes; for alpha-tested foliage, Preserve Coverage keeps leaves from thinning out in the distance.
6. On detail textures, Fadeout to Gray fades the detail out over the lower mipmaps.

**Diagnose.** A dark halo around cut-out leaves → Alpha Is Transparency off. Foliage that thins and vanishes far away → no coverage preservation on its mipmaps. Glossy, flat-looking packed maps → sRGB left on.

**API facts** (check the installed version):
- sRGB (Color Texture) marks a texture as gamma-encoded color; turn it off for textures whose exact values matter (verified on 6000.6).
- The Normal map type offers Create From Grayscale and Flip Green Channel (verified on 6000.6).
- Swizzle sources each channel from R, G, B or A, from one minus any of them, or from Zero or One (verified on 6000.6).
- Alpha Is Transparency dilates color under transparent pixels, and Preserve Coverage keeps alpha-test coverage through the mipmaps (verified on 6000.6).

## Compression, size and mipmaps per platform

**Goal.** Textures are as small as the views allow, in formats each target decodes natively, with no filtering shimmer.

**Build.**
1. Set Max Size from the largest size the texture covers on screen in the nearest view that matters, and keep one texel density across neighboring assets.
2. Mac: let Format stay Automatic, which gives DXT and BC formats on desktop, with BC6H for HDR textures.
3. Web: choose one default compression per build, DXT for desktop browsers or ASTC for mobile browsers, in the Player settings or from the build script, and make two builds when both matter. Formats a browser can't decode fall back to software decompression, costing memory and speed.
4. Keep mipmaps on for 3D textures, and turn them off for UI and sprites drawn at one-to-one. Use Kaiser filtering for textures that blur too soon, a higher Aniso Level for floors and ground, and Mipmap Limit groups for tier-specific texture quality.
5. Crunch compression shrinks downloads, which helps on the Web, but decompresses on the CPU at load.

**Watch for.** The Texture Compression in the Web build settings (File > Build Profiles) overrides the Player setting but is stored in `Library/`, outside version control. Leave it at Use Player Settings, or set it from the build script ([agent-control.md](agent-control.md), [project-hygiene.md](project-hygiene.md)).

**API facts** (check the installed version):
- Max Size caps a texture's imported dimensions, the Resize Algorithm defaults to Mitchell, and Use Crunch Compression decompresses to DXT or ETC on the CPU before upload (verified on 6000.6).
- On desktop GPUs, Unity recommends DXT1 for RGB, BC7 or DXT5 for RGBA, and BC6H for HDR textures (verified on 6000.6).
- On the Web, the build settings' Texture Compression overrides the Player setting and is stored in the `Library` folder, outside version control; formats a device can't decode are decompressed in software (verified on 6000.6).

## Read/Write in 6.6

**Goal.** Meshes and textures are CPU-readable exactly where the engine or the project's code needs them, and nowhere else.

**Build.**
1. Turn Read/Write on for meshes used by Mesh Colliders, Particle System Shape modules or terrain detail meshes, for textures used by Shape modules or terrain detail painting, and for any mesh or texture a script reads.
2. Leave it off everywhere else: a readable asset keeps a CPU copy, doubling a texture's memory.
3. Read the Inspector warnings and the build log before shipping: a missing Read/Write flag now fails the build.

**API facts** (check the installed version):
- In 6.6, a mesh that a Particle System Shape module, a Terrain Detail Mesh or a Mesh Collider needs to read must have Read/Write enabled, or the Inspector warns and the build fails (verified on 6000.6).
- Since 6.5, the same rule covers textures read by Particle System Shape modules and terrain detail painting (verified on 6000.6).
- A readable texture keeps an extra copy of its data for scripts, doubling its memory (verified on 6000.6).

## Audio import basics

**Goal.** Clips load without hitches and play the same on the Mac and the Web. Mixing and spatial design are in [input-ui-and-audio.md](input-ui-and-audio.md).

**Build.**
1. Short, frequent effects: ADPCM for noisy ones such as footsteps and impacts, PCM for the shortest and crispest, loaded with Decompress On Load. Music and long ambience: Vorbis, with Compressed In Memory, or Streaming on the Mac only.
2. Avoid Decompress On Load for long Vorbis clips, which then take about ten times their compressed memory.
3. Turn on Force To Mono for sounds positioned in 3D, and Load In Background for large clips.
4. Web: browsers block audio until the player clicks or taps, so start sound from the first input. Clips are imported as AAC, so loops can click at the loop point; use WAV sources with at least 1024 samples of silence at the start and the loop point moved past them. The Audio Mixer on the Web only changes group volume.

**API facts** (check the installed version):
- Load Type is Decompress On Load, Compressed In Memory or Streaming; streaming clips carry about 200 KB of overhead, and Compressed In Memory falls back to Decompress On Load in Chromium-based browsers (verified on 6000.6).
- Web builds import AudioClips as AAC, and compressed audio on the Web needs Compressed In Memory or Decompress On Load (verified on 6000.6).
- On the Web, Audio Mixer groups support volume changes only; other properties and effects don't run (verified on 6000.6).

## Symptom → cause

| Symptom | Likely cause | First check |
| --- | --- | --- |
| Asset at the wrong size | file units, or scale not applied at export | Scale Factor, Convert Units; the export |
| Model lying on its side | Z-up source without axis conversion | Bake Axis Conversion |
| Model imports flat gray or with odd materials | imported material description, not project materials | the Materials tab remaps |
| `.blend` file won't import on another machine | Blender not installed there | export FBX or glTF instead |
| glTF fine in the editor, magenta in the build | glTFast shader or variants not in the build | shader preloading; strict variant matching |
| Washed-out or muddy color | wrong sRGB setting | the texture's sRGB (Color Texture) |
| Bumps lit from the wrong side | DirectX-style normal map | Flip Green Channel |
| Dark fringes on cut-out edges | color not dilated under transparent pixels | Alpha Is Transparency |
| Distant foliage thins out | alpha-test coverage lost in mipmaps | Preserve Coverage |
| Blurry or shimmering ground | mipmap or anisotropy settings | Mipmap Filtering, Aniso Level |
| Build fails with a Read/Write error | 6.5 and 6.6 Read/Write rules | Inspector warnings on the asset |
| Web build huge or slow to load | uncompressed or software-decoded textures | the Web profile's texture compression |
| No sound on the Web until a click | browser autoplay policy | start audio on first input |
| Clicks at a loop point on the Web | AAC encoding shifted the loop | WAV source with leading silence |
| An asset nobody can trace | no ledger row | `art/LEDGER.md` |
