# Unity project hygiene: who writes what, meta files, serialization, prefabs, assemblies and git

API facts verified on Unity 6.6 (6000.6.4f1, 2026-10-06). Check the project's Unity version first (ProjectSettings/ProjectVersion.txt); if it differs, confirm in that version's official docs or the installed packages. The installed version wins.

Read when a builder is about to write into a Unity project, and again when a move, a rename, a merge or a missing reference breaks something. It sets which files agents write, which only Unity writes, and how the repository stays clean. Running Unity itself is in [agent-control.md](agent-control.md); the settings floor is in [setup.md](setup.md).

## Contents

- Who writes which files
- Meta files and GUIDs
- Reading and editing YAML
- Renaming scripts and serialized fields
- Marking dirty and saving
- Prefabs as the unit of work
- Assemblies and Editor code
- Packages and the lock file
- Git: ignore rules, LFS and smart merge
- Parallel builders in one project
- Symptom → cause

## Who writes which files

**Goal.** Every file in the project has one kind of writer, so nothing Unity regenerates is fought over and nothing it owns is forged.

**Build.**
1. **Agents write as text:** C# scripts, assembly definitions (`.asmdef`, `.asmref`), UXML and USS, HLSL include files, plain JSON or CSV data, `.gitignore` and `.gitattributes`, and the Forge files.
2. **Unity writes, driven by an editor script, the CLI's editor package or the Editor:** scenes, prefabs, materials, ScriptableObject assets, animation and controller assets, import settings (inside `.meta` files), project settings and the package lock file.
3. **Nobody edits:** `Library/`, `Temp/` and `UserSettings/`. `Logs/` is for reading only.
4. Keep Forge's files at the repository root, beside `Assets/`, never inside it: Unity would import every capture as a texture and give it a `.meta`. Capture scripts write to `artifacts/` at the root.
5. A file written into `Assets/` by the file system reaches Unity only on its next refresh. The refresh and compile loop is in [agent-control.md](agent-control.md).

**Watch for.** Folder names that Unity treats specially: `Editor` (code that never ships), `Resources` (always included in builds, which bloats them), `StreamingAssets` (copied as is) and `Plugins`. Use them only for their purpose.

**API facts** (check the installed version):
- Inside `Assets/`, Unity ignores hidden folders, names that start with a dot, names that end with `~`, and `.tmp` files, so none of them is imported (verified on 6000.6).
- `Library/` is a local cache that Unity regenerates; it stays out of version control and must never be edited, and `Temp/` is cleared every time Unity closes (verified on 6000.6).

## Meta files and GUIDs

**Goal.** Every asset keeps its identity through moves and renames, so no reference ever breaks.

**Build.**
1. Every file and folder under `Assets/` has a `.meta` beside it that holds its GUID and import settings. Commit each asset together with its `.meta`, always.
2. Move and rename through Unity (the Project window, `AssetDatabase.MoveAsset` or `RenameAsset`, or the CLI package's move command), so Unity carries the `.meta` along.
3. When you must move files with the file system, close the Editor first and move the `.meta` with its asset under the matching name.
4. Never write, copy or edit a `.meta` by hand. Duplicate an asset with `AssetDatabase.CopyAsset`, which gives the copy a new identity.
5. Before deleting an asset, search its GUID across `Assets/` (scenes, prefabs, materials and other assets) to find everything that uses it.
6. After each change, check git status: no asset without its `.meta`, and no `.meta` without its asset.

**Watch for.** Git doesn't store empty folders, but it does store their `.meta` files. When Unity finds an empty folder whose `.meta` is gone, it assumes someone deleted it and deletes the folder too. Don't commit empty folders, or a folder's `.meta` without the folder.

**Diagnose.**
- "The referenced script on this Behaviour is missing" → the script's `.meta` was lost or regenerated, so its GUID changed.
- A material lost its texture → the texture moved outside Unity without its `.meta`.

**API facts** (check the installed version):
- Unity creates a `.meta` for every file and folder in `Assets/`, holding the asset's ID and import settings; moving or renaming in the Project window moves the `.meta` too (verified on 6000.6).
- An asset that loses its `.meta` is treated as new: it gets a new ID and every reference to it breaks, so objects lose their scripts and materials their textures (verified on 6000.6).

## Reading and editing YAML

**Goal.** Agents use the text format to read, diff and review, and leave the writing to Unity.

**Choose.**
- **Read freely:** grep scene, prefab and asset files to find which GUID a reference points at, which components an object carries, or what a diff changed.
- **Change values through Unity:** an editor script using the component API or `SerializedObject`, the CLI package's property commands, or the Inspector.
- **Hand-edit only as a last resort,** for one scalar value, with the Editor closed and a backup taken. Then let Unity reimport and resave the file, and confirm the change in the log and a capture.
- **Never hand-author** a scene or a prefab, never change a `fileID` or a GUID, and never resolve a scene conflict by hand when smart merge can do it.

**Build.** Make every bulk or repeated change an editor script ([agent-control.md](agent-control.md)), and keep any hand edit to one value in its own commit, so the diff is easy to review and to revert.

**Watch for.** A hand-written scene can load without an error and still drop components, cut prefab links or come back rewritten on the next save. Generate scenes and prefabs with editor scripts instead ([agent-control.md](agent-control.md), Editor scripts are the main lever).

**API facts** (check the installed version):
- Force Text stores scenes and other assets as text so that version control can merge them (verified on 6000.6).
- Editing through `SerializedObject` and `ApplyModifiedProperties` marks the object dirty, records an undo step and creates prefab overrides where they apply (verified on 6000.6).

## Renaming scripts and serialized fields

**Goal.** A refactor never wipes the values already saved in scenes, prefabs and assets.

**Build.**
1. Unity saves public and `[SerializeField]` fields by name. When renaming one, give the renamed field `[FormerlySerializedAs("oldName")]`, then resave the assets that use it.
2. To upgrade many assets at once and on purpose, resave them from a menu item with `AssetDatabase.ForceReserializeAssets`, and commit the result as its own change.
3. Name each MonoBehaviour or ScriptableObject file after its class, one such class per file, inside a namespace.
4. Rename a script file through Unity, or with its `.meta`: scenes refer to the script by the GUID in that `.meta`, not by its name.
5. Remember that values changed in Play mode are temporary. Changes that must persist go through an editor script outside Play mode.

**Diagnose.** Values back at their defaults after a refactor → a serialized field renamed without `FormerlySerializedAs`.

**API facts** (check the installed version):
- `FormerlySerializedAs` lets a field be renamed without losing its serialized value (verified on 6000.6).
- `AssetDatabase.ForceReserializeAssets` loads, upgrades and writes back the given assets; call it from a direct user action such as a menu item, never from a callback like `OnEnable` (verified on 6000.6).
- A script's file name should match its class; for MonoBehaviour and ScriptableObject types Unity resolves a mismatch only in limited cases, and warns when the match is ambiguous (verified on 6000.6).
- Changes made in Play mode are temporary and reset when Play mode ends (verified on 6000.6).

## Marking dirty and saving

**Goal.** Every scripted change reaches disk, so a fresh process, git and the next capture all see it.

**Build.**
1. Before changing an object from an editor script, call `Undo.RecordObject`, or `EditorUtility.SetDirty` when no undo step is wanted. For a prefab instance, also record its property modifications so they become overrides.
2. Save scenes with `EditorSceneManager.SaveScene` and an explicit project-relative path whose folders already exist, or with `SaveOpenScenes`.
3. Save assets (materials, ScriptableObjects) with `AssetDatabase.SaveAssets` after marking them dirty.
4. In batch mode, save before the method returns. Batch mode suppresses the Save Scene dialog, so unsaved changes vanish when the process exits.
5. Prove it: open the result in a fresh process, or grep the saved file, and check that the change is there.

**Watch for.** `SaveScene` on a scene that was never saved, called without a path, opens a save dialog. Always pass the path.

**API facts** (check the installed version):
- `EditorSceneManager.SaveScene` takes a project-relative path whose folders must exist, saves whether or not the scene is dirty, and shows a save dialog for a never-saved scene given no path (verified on 6000.6).
- `EditorUtility.SetDirty` records a change without an undo entry, while `Undo.RecordObject` before the change marks it dirty and adds an undo entry; objects inside a prefab instance also need `PrefabUtility.RecordPrefabInstancePropertyModifications` (verified on 6000.6).
- `EditorApplication.Exit` quits at once without asking to save (verified on 6000.6).

## Prefabs as the unit of work

**Goal.** Reusable things live in prefabs, each with one owner, so scenes stay small and merges rare.

**Build.**
1. Build each reusable thing (the player, an enemy, a pickup, a kit piece, a UI screen) as a prefab asset from an editor script: assemble it, save it with `PrefabUtility.SaveAsPrefabAsset`, and to change it later, load it with `LoadPrefabContents`, edit, save and `UnloadPrefabContents`.
2. Let scenes hold instances and layout, not hand-built hierarchies.
3. Use prefab variants for versions of one thing, and nested prefabs for shared parts.
4. Give every object in a prefab's hierarchy a unique name.
5. Keep instance overrides deliberate: apply them to the prefab or revert them, and never leave strays behind.

**Watch for.** Saving from the root of a prefab instance makes a variant, not a new prefab; unpack the instance first when a new, independent prefab is the goal.

**API facts** (check the installed version):
- `PrefabUtility.SaveAsPrefabAsset` called on a prefab instance root creates a prefab variant (verified on 6000.6).
- When saving over an existing prefab, Unity keeps references by matching object names, so duplicate names make the match unpredictable (verified on 6000.6).
- Between `AssetDatabase.StartAssetEditing` and `StopAssetEditing`, `SaveAsPrefabAsset` returns null even when the save succeeded, because the asset isn't imported yet (verified on 6000.6).

## Assemblies and Editor code

**Goal.** Editor-only code never reaches a player build, and each area of code compiles on its own.

**Build.**
1. Put editor code (setup scripts, menu items, build and capture scripts) in a folder named `Editor`, or in an assembly definition limited to the Editor platform. Command-line entry points for `-executeMethod` are static methods in an `Editor` folder.
2. When game code gets an `.asmdef`, give every `Editor` folder below it its own Editor-only `.asmdef` or an `.asmref` that points at one. Otherwise those editor scripts join the runtime assembly and the player build fails on `UnityEditor` references.
3. Keep tests in test assemblies: EditMode tests Editor-only, PlayMode tests referencing the game assembly ([validation.md](validation.md)).
4. For a first game, three assemblies are plenty: game, editor tools and tests.
5. Guard any `UnityEditor` call in runtime code with the `UNITY_EDITOR` define.

**API facts** (check the installed version):
- Scripts in folders named `Editor` compile into the predefined editor assembly, unless an assembly definition sits in a folder above them, which pulls them into that assembly instead (verified on 6000.6).
- A MonoBehaviour class defined inside an `Editor` folder is unavailable as a component on any GameObject (verified on 6000.6).
- `-executeMethod` runs a static method whose script sits in an `Editor` folder (verified on 6000.6).

## Packages and the lock file

**Goal.** The package set rebuilds the same way on any machine from two committed files.

**Build.**
1. Add or remove packages through the Package Manager window, the `PackageManager.Client` API from an editor script, or the CLI package's package commands. A new package is new code in the project, so it needs the user's yes.
2. Editing `Packages/manifest.json` directly is documented; do it with the Editor closed, then let the next open resolve it and rewrite `packages-lock.json`.
3. Commit `manifest.json` and `packages-lock.json`, and embedded packages under `Packages/` with their `.meta` files. Never commit `Library/PackageCache/`.
4. A community editor bridge package goes in only with the user's yes ([agent-control.md](agent-control.md)).

**API facts** (check the installed version):
- `PackageManager.Client.Add`, `Remove` and `AddAndRemove` run asynchronously and return a request to poll, and each Client call should wait until the previous one finishes (verified on 6000.6).
- Unity reads `Packages/manifest.json` when it loads a project, and the Package Manager window writes its changes back to that file (verified on 6000.6).

## Git: ignore rules, LFS and smart merge

**Goal.** The repository holds exactly the project's source, merges scenes by meaning rather than by line, and leaks nothing.

**Build.**
1. Start from the standard Unity ignore file (GitHub's `Unity.gitignore`). It leaves out `Library/`, `Temp/`, `Obj/`, `Build/`, `Builds/`, `Logs/`, `UserSettings/`, `MemoryCaptures/`, `Recordings/`, IDE project files and build outputs. Add whatever `BRIEF.md` decides about `artifacts/`.
2. Commit `Assets/` with every `.meta`, `ProjectSettings/`, and the two package files: `Packages/manifest.json` and its lock file, `Packages/packages-lock.json`.
3. Put large binary sources in Git LFS: textures, models, audio, video, fonts, `.psd`, `.blend`, `.exr` and `.hdr`. Keep Unity's text assets (`.unity`, `.prefab`, `.asset`, `.mat`, `.anim`, `.controller`, `.meta`) as plain text so diffs and smart merge keep working. Write `.gitattributes` before the first binary commit; moving history into LFS later rewrites it and needs the user's yes.
4. Register UnityYAMLMerge, which ships with the Editor, as the merge tool for `.unity` and `.prefab` files, or let the CLI's `vcs merge-setup` do it.
5. Before every commit: nothing from `Library/`, `Temp/`, `Logs/`, `UserSettings/` or a build is staged; every new asset has its `.meta`; no keys, tokens or bridge settings with secrets are staged.
6. Commit only after Unity has saved, and never while a batch run is still writing.

**Watch for.** Asset Store and Mixamo files go only where the policy in [assets-and-import.md](assets-and-import.md) (Asset Store and Mixamo files) allows. A setting stored in `Library/` never reaches the repository: the Web build settings' Texture Compression is one, and it overrides the Player setting, so leave it at Use Player Settings or set it from the build script ([performance-and-builds.md](performance-and-builds.md)). The CLI package's access token sits in `Library/Pipeline/`, which stays ignored, and a development build running the package's runtime server writes its own token file inside the `.app`: one more reason never to commit builds.

**API facts** (check the installed version):
- UnityYAMLMerge ships inside the installed `Unity.app`, at `Contents/Helpers/UnityYAMLMerge`; as a git merge tool its command is `merge -p` followed by the base, remote, local and merged paths, with `trustExitCode` set to false (verified on 6000.6).

## Parallel builders in one project

**Goal.** Builders working at the same time never write the same Unity file, and never run Unity on the same project at once.

**Build.**
1. Name one owner for each scene, prefab, settings asset and folder in `PLAN.md`. The folder layout is a shared contract ([router.md](router.md), Contracts builders share).
2. Builders who write only C# and text can work in parallel in their own folders.
3. Anything that needs Unity to run (import, compile, bake, capture, build) goes through one queue the orchestrator owns, because a second Unity process can't open a project that is already open. A builder that must run Unity on its own works in a separate git worktree with its own `Library/`, and pays a full first import.
4. The app-shell builder owns the main scenes and the project settings, and places the prefabs that other builders deliver.

**Watch for.** Two builders saving one scene: even with smart merge, a scene conflict costs a round. Split the work by prefab instead.

## Symptom → cause

| Symptom | Likely cause | First check |
| --- | --- | --- |
| "The referenced script on this Behaviour is missing" | the script's `.meta` was lost or regenerated, or the file and class names disagree | the script's `.meta` in git history, then its file and class names |
| A material lost its texture after a move | the texture moved outside Unity without its `.meta` | the texture's GUID before and after the move |
| Saved values reset after a refactor | a serialized field renamed without `FormerlySerializedAs` | that field's history |
| Scripted scene changes are gone after the run | the scene was never marked dirty or saved before the process exited | the save call, and the scene file's modified time |
| A player build fails on `UnityEditor` types | editor code compiled into a runtime assembly | which assembly the script belongs to (Inspector, Assembly Information) |
| Two assets share a reference, or one goes missing, after a copy | a `.meta` duplicated by hand | a search for the GUID across `Assets/` |
| An empty folder vanished after a pull | its `.meta` was removed elsewhere, so Unity deleted it | git history of the folder's `.meta` |
| A merge left a broken scene | merged as plain text instead of with UnityYAMLMerge | the git merge-tool setup |
| Clones are huge and slow | binaries committed outside LFS | `.gitattributes`, and what LFS tracks |
| A key or token appears in a commit | a bridge config, descriptor or build was staged | the staged file list against the ignore file |
| Packages differ between machines | `packages-lock.json` wasn't committed | the lock file in git |
| One builder's edits disappear | two processes wrote the same asset | that asset's owner in `PLAN.md` |
