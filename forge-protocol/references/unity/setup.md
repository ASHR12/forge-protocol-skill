# Unity setup: versions, installs, license, first project and coaching

API facts verified on Unity 6.6 (6000.6.4f1, 2026-10-06). Check the project's Unity version first (ProjectSettings/ProjectVersion.txt); if it differs, confirm in that version's official docs or the installed packages. The installed version wins.

Read when a Unity build starts on a new machine or a new project: at Rule 0, before the first project exists, and whenever a person has to install, sign in or click something. How agents drive the project afterward is in [agent-control.md](agent-control.md), what to commit is in [project-hygiene.md](project-hygiene.md), and the reasons behind the render pipeline choice are in [foundation.md](foundation.md).

## Contents

- Versions and the pin
- What to install
- License and sign-in
- Probe without launching anything
- Template and render pipeline
- Create the project
- The first open
- The settings floor
- Recommended installs
- Coaching a first-time user
- The human steps, fewest clicks
- Symptom → cause

## Versions and the pin

**Goal.** Every agent writes against the editor that is actually installed, and the project records which one that is.

**Choose.**
- Unity 6.6 (6000.6) by default: it is the supported update release installed on this machine. It is not an LTS release. The 6.7 LTS is due around the end of 2026; after any upgrade, check the facts in this module again.
- One editor version per project. Opening a project in another version reimports everything and can rewrite scripts through the API Updater, so an upgrade or a downgrade needs the user's yes.

**Build.**
1. List installed editors from the folder names under `/Applications/Unity/Hub/Editor/`. Each editor's `Unity.app/Contents/Info.plist` carries the full version and its changeset, and the `modules.json` next to the app lists what the Hub installed.
2. In an existing project, read `ProjectSettings/ProjectVersion.txt` and open the project only with that version.
3. Record the version and changeset under Stack in `BRIEF.md`, and have the game print its version to the log at startup ([validation.md](validation.md), Capture provenance).
4. Before writing an API call from memory, check the installed Documentation module: the offline Manual and Scripting Reference live in the editor folder under `Documentation/en/`, so an agent can confirm a name or a default without a network.

**Watch for.** Tutorials, forum answers and older agent skills mostly target 2021 or 2022 LTS, so their menu paths, package names and APIs have drifted. The table of renamed and removed APIs is in [foundation.md](foundation.md).

**API facts** (check the installed version):
- `Application.unityVersion` returns the version of the engine that is running, so a build can log its own version (verified on 6000.6).
- The Editor's `-version` argument prints the version number without opening the Editor (verified on 6000.6).

## What to install

**Goal.** The editor and the modules the targets need, and nothing the brief doesn't use.

**Build.**
1. Unity Hub, unless the probe already found it.
2. The Apple silicon editor (the pinned 6000.6.4f1) with Mac Build Support (Mono), which comes with the macOS editor, Web Build Support for the Web target, and the Documentation module for offline checks. Add Mac Build Support (IL2CPP) only when the plan asks for it; the backend choice belongs to [performance-and-builds.md](performance-and-builds.md).
3. The engine CLI. The Hub ships it, installs it on first launch at `~/.unity/bin/unity` and adds it to the shell path. It is a beta with weekly releases, so read `unity --help` and `unity version` for the installed release rather than trusting memory or this file ([agent-control.md](agent-control.md)).
4. Add modules later from the Hub (Installs, the editor's gear menu, Add modules), or through the CLI's `install-modules` command once the user agrees.

**Watch for.**
- A target with no module: it is missing from the Build Profiles window and its command-line build fails. Check the editor's `PlaybackEngines/` folder.
- Intel Macs: Intel support for the macOS editor and players is deprecated in 6.6. Target Apple silicon unless the brief says otherwise.

**Start here** (adjust to the goal): the Mac (Mono), Web and Documentation modules, and nothing else until a brief names another platform.

**API facts** (check the installed version):
- Intel (x86_64) support for the macOS editor and macOS players is deprecated in 6.6, and Apple silicon is unaffected (verified on 6000.6).

## License and sign-in

**Goal.** The editor opens licensed, every automated route reuses that license, and no credential ever reaches a command line or a log.

**Build.**
1. Unity Personal is free for individuals and hobbyists who earn less than $200K from their use of Unity, and for small businesses with less than $200K of revenue and funding. Point the user to Unity's plan page for the current terms; never decide eligibility for them.
2. Personal activates by signing in to the Hub, and only that way: the serial and manual-activation routes on the command line are for paid plans. Signing out of the Hub returns the seat.
3. The engine CLI keeps its own session. The user signs it in once through its browser flow (`unity auth login`) before an agent drives an open Editor; `unity auth status` reports the state.
4. A batch run on the same machine should pick up the Hub's activation. Confirm it on the first batch run by reading the licensing lines in that run's log; a license failure is a human step, never something to retry in a loop.
5. Keep Unity AI and Unity Cloud off unless the user asks: leave Use AI Assistant unticked when creating a project, and create projects with no cloud link. Nothing in Forge needs either.

**Watch for.** The `-username`, `-password` and `-serial` arguments exist for paid plans and build servers; Forge never uses them. When licensing fails, the licensing client's own log is `~/Library/Logs/Unity/Unity.Licensing.Client.log`.

**API facts** (check the installed version):
- The command-line license procedures don't apply to Unity Personal, which activates by signing in to the Hub and returns its license by signing out (verified on 6000.6).
- Batch-mode use of Unity falls under Unity's Terms of Service and their additional terms (verified on 6000.6).

## Probe without launching anything

**Goal.** Rule 0 learns the Unity facts from files and harmless version queries, without starting the Editor or the Hub.

**Build.** Read these and record them in `BRIEF.md` (Stack) and in the tools table of `PLAN.md`:
1. **Editors and modules:** each editor folder, its version and changeset, and its modules (`modules.json`, `PlaybackEngines/`).
2. **License:** that a license file exists and the Hub shows a signed-in user. Never print the license file.
3. **Engine CLI:** whether `unity` is on the path, its version, and whether it is signed in. Both queries are read-only.
4. **Project, once one exists:** `ProjectVersion.txt`; `Packages/manifest.json` and `packages-lock.json` (the render pipeline, the Input System, the test framework, the CLI's editor package `com.unity.pipeline`, and any community bridge); and in `ProjectSettings/`, the input handling, color space, run-in-background and window mode (`ProjectSettings.asset`), the serialization and Enter Play Mode values (`EditorSettings.asset`), the render pipeline asset on each quality level (`QualitySettings.asset`, `GraphicsSettings.asset`) and the meta-file mode (`VersionControlSettings.asset`).
5. **Bridges:** the names of any community editor bridge configured in the harness or listed in the manifest. Names only, never their keys, ports or tokens.
6. **Toolchain:** git, Git LFS, a .NET SDK and a C# editor extension (Recommended installs).

**Watch for.** In a Force Text project these settings files are readable text. Read them freely, but change them through the Editor, an editor script or the Package Manager, never by hand-editing ([project-hygiene.md](project-hygiene.md)).

## Template and render pipeline

**Goal.** The project starts on the right render pipeline, because switching pipelines later means reworking every material and light.

**Choose.**
- **Universal 3D** for any 3D game or scene: URP with its 3D renderer. The default.
- **Universal 2D** for sprite and tile games: URP with its 2D renderer, which 2D lights and shadows require ([2d.md](2d.md)).
- **HDRP** only as a short route the user approves, for a Mac-only showcase; it doesn't run on the Web target ([foundation.md](foundation.md)).
- **Never** the Built-in render pipeline for a new project: it is deprecated.
- Sample and learning templates are for study. Their content comes under Unity's own terms, so check those terms before anything from them enters a public repository ([assets-and-import.md](assets-and-import.md)).

**Build.** Name the template in `PLAN.md`; what URP gives up, and how each topic file works around it, is in [foundation.md](foundation.md). Then add what the template lacks, each package with the user's yes ([project-hygiene.md](project-hygiene.md), Packages and the lock file):
- The bundled 3D URP template (the Hub's Universal 3D) lists AI Navigation, the Input System, Timeline, uGUI and the Test Framework, but not Cinemachine: add that core package for follow cameras ([camera-and-animation.md](camera-and-animation.md)).
- No glTF importer ships with the editor: add glTFast when the plan imports `.gltf` or `.glb` files ([assets-and-import.md](assets-and-import.md)).
- Universal 2D already includes URP's Pixel Perfect Camera: never add the standalone 2D Pixel Perfect package, a Built-in-only component ([2d.md](2d.md)).
- Asset Store content, Unity's Starter Assets included, follows the policy in [assets-and-import.md](assets-and-import.md) (Asset Store and Mixamo files).

**Watch for.**
- A new quality level added later with no pipeline asset assigned. The templates set the pipeline per quality level and leave the Graphics default empty, so such a level falls back to the Built-in pipeline and every material turns pink ([foundation.md](foundation.md) has the rule; [performance-and-builds.md](performance-and-builds.md) owns the tiers).
- The 3D URP template already uses post-processing: its camera has Post Processing on and no anti-aliasing, and both URP assets apply a profile with Neutral tone mapping, bloom and a vignette to every scene. [final-image.md](final-image.md) decides what to keep, and the no-post still applies ([validation.md](validation.md)).

**API facts** (check the installed version):
- The Hub's URP templates are Universal 2D, Universal 3D and Universal 3D sample, and a URP project isn't compatible with HDRP or the Built-in pipeline (verified on 6000.6).
- The bundled 3D URP template ships PC and Mobile quality levels, each pointing at its own URP asset, and its dependencies include URP 17.6.0, the Input System, Test Framework, Timeline, uGUI and AI Navigation (verified on 6000.6).

## Create the project

**Goal.** A local project in a plain folder, linked to no cloud service, that already holds the CLI's editor package when the plan uses the live route.

**Choose.**
- **The Hub**, by default for a new user: Unity documents this route, and its New project page can add the CLI's editor package at creation.
- **The engine CLI**, with the user's yes: it creates projects with or without a Unity Cloud link; always pass the no-cloud option, and check `unity projects --help` for the installed release.
- **The Editor command line** (`-createProject` with `-cloneFromTemplate`) for a scripted setup only.

**Build.**
1. Choose a local folder that no cloud service syncs: not iCloud Drive, not a Desktop or Documents folder synced to iCloud, and not a Dropbox-style folder. Unity doesn't support projects stored in cloud-synced folders.
2. Keep the path short and free of spaces; a path with spaces needs quotes in every command.
3. In the Hub: Projects, New project, the 6.6 editor, Universal 3D (or Universal 2D), a name and a location. Tick Use Unity CLI when the plan uses the live route, leave Use AI Assistant unticked, pick the local option if the Hub offers a cloud-connected one, then Create project.
4. Keep one Unity project at the repository root. Forge's files (`BRIEF.md`, `art/`, `artifacts/`) then sit beside `Assets/`, outside what Unity imports ([project-hygiene.md](project-hygiene.md)).

**API facts** (check the installed version):
- `-createProject <path>` combined with `-cloneFromTemplate <template archive or folder>` creates a new project from a template on the command line (verified on 6000.6).
- Unity doesn't support storing a project in cloud-based storage, which can corrupt it through sync conflicts (verified on 6000.6).

## The first open

**Goal.** The project imports once and cleanly, and the agent confirms that from files, not from the user's eyes.

**Build.**
1. The first open imports every asset and compiles every script, which takes a few minutes. Tell the user the Editor shows a progress bar and may look frozen until it closes.
2. The template may open a readme or a welcome panel. It is safe to close.
3. Then check, without asking the user: the project's `Logs/Editor.log` shows no compile errors; `.meta` files exist next to every asset; `Packages/packages-lock.json` exists; `ProjectVersion.txt` names 6000.6.
4. If a dialog appears, name the window and the button to press (Coaching a first-time user). The Enter Safe Mode dialog means compile errors: the user presses Enter Safe Mode, and the agent reads the errors from the log and fixes them ([agent-control.md](agent-control.md)).
5. Make the first commit only after this open, once the `.meta` files exist ([project-hygiene.md](project-hygiene.md)).

**Watch for.**
- The wrong log: the Editor writes a log per project, inside the project, by default. The global log in `~/Library/Logs/Unity/` is used only when the global-log option is on, so an empty or stale global log proves nothing.
- A pink scene after the first open: the pipeline asset didn't load, often because of compile errors ([foundation.md](foundation.md)).

**API facts** (check the installed version):
- By default the Editor writes its log to `Logs/Editor.log` inside the open project; `~/Library/Logs/Unity/Editor.log` is used only with the Use Global Editor Log preference or `-useGlobalLog` (verified on 6000.6).
- A project with compile errors opens with the Enter Safe Mode dialog, which offers Enter Safe Mode, Ignore and Quit (verified on 6000.6).

## The settings floor

**Goal.** Every new project starts from settings that agents can diff, merge and reason about. The templates already set most of them; the agent checks each one after the first open and records any change in `PLAN.md`.

**Build.** Check each row, and change a setting only through the Editor or an editor script.

| Setting | Floor | Where it is stored | Owner |
| --- | --- | --- | --- |
| Asset serialization | Force Text | `EditorSettings.asset` | [project-hygiene.md](project-hygiene.md) |
| Meta files | Visible Meta Files | `VersionControlSettings.asset` | [project-hygiene.md](project-hygiene.md) |
| Active Input Handling | Input System Package (New) | `ProjectSettings.asset` | [input-ui-and-audio.md](input-ui-and-audio.md) |
| Color space | Linear | `ProjectSettings.asset` | [foundation.md](foundation.md) |
| Enter Play Mode | the template's value, with statics reset in code | `EditorSettings.asset` | [foundation.md](foundation.md) |
| Render pipeline | a URP asset on every quality level | `QualitySettings.asset` | [performance-and-builds.md](performance-and-builds.md) |
| Run In Background | on, for capture and smoke-test builds | `ProjectSettings.asset` | [validation.md](validation.md) |
| Window mode | windowed, at the capture size, for capture builds | `ProjectSettings.asset` | [validation.md](validation.md) |

**Watch for.**
- Enter Play Mode: the bundled 3D URP template skips both the domain reload and the scene reload when entering Play mode, and the 2D template skips only the domain reload, which is the Editor's default. Either way, static state survives from one Play session to the next, so two sessions in one Editor aren't independent ([foundation.md](foundation.md) has the rules, [validation.md](validation.md) the capture consequence).
- Both templates turn Run In Background off and open players as a full-screen window: a capture build launched from the command line then takes over the screen, and pauses whenever another window has focus.

**API facts** (check the installed version):
- Force Text is the default asset serialization mode, and Visible Meta Files the default version control mode (verified on 6000.6).
- Entering Play mode defaults to Reload Scene only, without a domain reload, so static fields and static event subscribers keep their values between Play sessions (verified on 6000.6).
- `EnterPlayModeOptions` is a flags enum in which `DisableDomainReload` is 1 and `DisableSceneReload` is 2, so the 3D URP template's stored value of 3 skips both reloads (verified on 6000.6).
- With Run In Background off, a desktop player pauses when it loses focus (verified on 6000.6).

## Recommended installs

**Goal.** Agents can check C# outside the Editor and keep large binaries out of plain git, with the user deciding each install.

**Build.** Probe for each one first (Probe without launching anything). Ask before each install, in one sentence saying what it is for, and never install anything without a yes.
- **Git LFS**, before the first commit of textures, models, audio or video. What goes into LFS is in [project-hygiene.md](project-hygiene.md).
- **A .NET SDK**, so command-line tools and the editor extension can analyze the code. Unity compiles with its own bundled toolchain, so builds never depend on it.
- **A C# editor extension** for the user's code editor, plus the matching Unity editor package (the templates already include the Visual Studio and Rider packages). Then set the external script editor under Unity > Settings > External Tools.

**Watch for.** An editor extension shows errors only once the IDE project files exist, and Unity generates those (they are git-ignored). The authority for compile errors is still the Editor log or the CLI's recompile report ([agent-control.md](agent-control.md)).

## Coaching a first-time user

**Goal.** A user new to Unity gets each human step right the first time, and is never asked to judge a log, an error or a picture.

**Build.**
1. Give one step per message: the window, the exact button or menu text as it appears on screen, and what they will see when it worked, such as "the progress bar closes and the sample scene appears".
2. Say how long it takes, especially for imports, module downloads and the first build.
3. Confirm through evidence you read yourself: the Editor log, a file that should now exist, a capture. Never ask "does it look right?" or "do you see an error?".
4. Ask the user to stop at any dialog and tell you its title, or paste a screenshot, before clicking. Then name the button.
5. Explain a Unity word once, in plain terms, the first time it comes up: scene, prefab, package, Play mode.
6. Do yourself what files and scripts can do. Only sign-ins, approvals, operating-system permissions and dialogs need the user.

**Watch for.** Beginners click through dialogs quickly, and some answers change the project: the API Updater rewrites scripts, Ignore on the Safe Mode dialog imports a broken project, and an upgrade prompt moves the project to another version.

## The human steps, fewest clicks

**Goal.** The user does only what needs a person, in an order that never blocks an agent.

**Build.** When the probe finds the Hub signed in with a license, and the 6.6 editor with Mac and Web support, already installed:
1. Confirm the targets: Mac and Web by default, which need no new modules.
2. Approve the control routes for this build ([agent-control.md](agent-control.md)). Files and batch mode need nothing more; the live route needs the next step.
3. For the live route only: sign in the CLI once. `unity auth login` opens a browser, and the user finishes the sign-in there.
4. Create the project in the Hub, about six clicks (Create the project).
5. Wait out the first open, and answer any dialog the way the agent says.
6. Approve or decline the recommended installs.
7. Keep the Editor open or closed as the agent asks for each phase: batch runs refuse a project the Editor has open, and the live route needs it open.

After setup the user is asked only to approve a one-off code run through the CLI, answer a dialog, approve an install or a new package, grade the visual criteria when no image-capable critic exists, and unlock publishing.

## Symptom → cause

| Symptom | Likely cause | First check |
| --- | --- | --- |
| The Hub can't create a project | not signed in, or no active license | the Hub's account and Licenses pages |
| A batch run stops at once with a license error | no activation on this machine, or it expired | the licensing lines in that run's log, then the Hub's Licenses page |
| The Web or Mac target is missing | its module isn't installed | the editor's `PlaybackEngines/` folder and `modules.json` |
| `unity` isn't found | the shell never loaded the CLI's path file, or the CLI isn't installed | a new terminal, then the Hub's Tools menu |
| The CLI exits with 3 or 7 when driving the Editor | not signed in, or the Editor or its package isn't running | `unity auth status` and `unity status` ([agent-control.md](agent-control.md)) |
| The project opens in Safe Mode | compile errors | the project's `Logs/Editor.log` |
| Everything renders pink | no pipeline asset on the active quality level, or compile errors stopped the pipeline loading | the quality level's pipeline asset ([foundation.md](foundation.md)) |
| An exception at the first read of `UnityEngine.Input` | old input calls under Input System Package (New) | Active Input Handling ([input-ui-and-audio.md](input-ui-and-audio.md)) |
| Values from the last Play session leak into the next | domain reload off and statics never reset | the Enter Play Mode setting ([foundation.md](foundation.md)) |
| Missing references or reimports after a sync | the project sits in a cloud-synced folder | the project path |
| A captured player stalls when another window has focus | Run In Background is off | the Player setting ([validation.md](validation.md)) |
| The log the agent reads never changes | reading the global log while the Editor writes the project log | `Logs/Editor.log` inside the project |
