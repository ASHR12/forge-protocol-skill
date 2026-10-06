# Unity agent control: routes, readiness, the compile loop, editor scripts, the CLI, batch mode, logs and builds

API facts verified on Unity 6.6 (6000.6.4f1, 2026-10-06). Check the project's Unity version first (ProjectSettings/ProjectVersion.txt); if it differs, confirm in that version's official docs or the installed packages. The installed version wins.

Read when you plan how agents will act on a Unity project (the orchestrator, at Rule 0), and before any builder runs Unity to compile, generate scenes, test, capture or build. Which files agents may write is in [project-hygiene.md](project-hygiene.md), installs and sign-in are in [setup.md](setup.md), and captures are in [validation.md](validation.md).

## Contents

- Four routes, chosen per phase
- One Unity process per project
- Readiness and dialogs
- The compile loop
- Editor scripts are the main lever
- Batch mode: flags and exit codes
- The engine CLI and its editor package
- One-off code needs a yes
- Community editor bridges
- Logs: Editor, player and CLI
- Builds from the command line
- Symptom → cause

## Four routes, chosen per phase

**Goal.** Each action goes through the cheapest route that does it reliably, and `PLAN.md` names the route for every phase.

**Choose.**
- **Files**, always available: C# scripts, assembly definitions, UI and data files, and the Forge files ([project-hygiene.md](project-hygiene.md)). No Unity process is needed, and nothing is checked until Unity compiles.
- **Batch mode, with the Editor closed**, available once the project exists: compile checks, setup scripts that generate and save scenes and prefabs, tests, Project Auditor, and player builds. Each run starts as a fresh process from what is on disk, needs no sign-in beyond the Hub's license, and shows the user nothing.
- **The live Editor, through Unity's engine CLI and its editor package**, once the user approves it, the package is in the project and the CLI is signed in: recompiles with an error report, the console, Play and stop, Game and Scene view captures, tests, menu items, and edits to scenes, objects and prefabs. It is the fastest loop and the user can watch, but state builds up between Play sessions and a dialog can block it.
- **The human**, for sign-ins, the license, approvals, operating-system permission prompts, dialogs, installs the user prefers to click, grading when no image-capable critic exists, and unlocking publishing.
- Community editor bridges are not a default route; see Community editor bridges.

**Build.** Pick per phase and write it into the plan:

| Phase | Route |
| --- | --- |
| Project creation and first open | the human, then files |
| Writing code | files, then the compile loop through batch mode or the live route |
| Generating scenes, prefabs and settings | editor scripts, run in batch mode or as menu items through the live route |
| Look-development iteration | the live route, when approved |
| Capture rounds | the one route proven in [validation.md](validation.md), the same every round |
| Tests and audits | batch mode, in a fresh process |
| Builds and smoke tests | a batch build, then the built player |

**Watch for.** Results that depend on the route: a live Editor carries static state and earlier Play sessions (the 3D URP template skips both the domain and the scene reload on entering Play mode; [foundation.md](foundation.md)), while a batch run starts clean. Never mix routes for the stills of one round.

**Start here** (adjust to the goal): batch mode for everything that must reproduce (scene generation, tests, builds), and the live route only for quick look-development when the user has approved it.

## One Unity process per project

**Goal.** No run fails because another Unity process holds the project.

**Build.**
1. Before a batch run, make sure no Editor has the project open: check the running Unity processes for this project's path, or `unity status`, which lists connected Editors with their project paths.
2. If the Editor is open, either use the live route for this step, or ask the user to save their work and quit the Editor. The CLI's `close` doesn't save, so save through the package before using it.
3. Run every Unity process for a project through one queue ([project-hygiene.md](project-hygiene.md), Parallel builders in one project).
4. Give each batch run a time limit. When it passes, end the process, then read its log before trying again.

**Watch for.** A crashed or hung batch run that is still alive holds the project, and the next run fails for a reason that has nothing to do with its own code.

**API facts** (check the installed version):
- Batch mode refuses to open a project that an open Editor already holds, because only one Unity instance can work on a project at a time (verified on 6000.6).

## Readiness and dialogs

**Goal.** No command reaches an Editor that is importing, compiling, reloading or stuck behind a dialog.

**Build.**
1. **Live route:** before each batch of commands, and after any write that triggers an import or a compile, poll the package's status until it reports ready. It reports a settling state during a cold import and compile, and a blocked-by-dialog state, with the dialog's title and buttons, while a modal is open.
2. **Editor scripts:** wait until `EditorApplication.isCompiling` and `EditorApplication.isUpdating` are both false before acting.
3. **Domain reload:** every successful compile reloads the scripting domain, which ends in-flight async work and clears static state. Afterward, read state back from disk instead of trusting memory.
4. **Batch mode:** the method passed to `-executeMethod` runs after the project has opened and compiled. With compile errors, batch mode quits instead.
5. **Dialogs:** when one is open, stop sending commands. Ask the user for its title, or a screenshot, and name the button to press. Never click dialog buttons blindly through automation. Typical ones: Enter Safe Mode (compile errors when opening), the API Updater's offer to rewrite scripts, a request to restart the Editor, and save prompts.
6. **Safe Mode:** no project or package code runs, so the editor package and any bridge are gone. Read the errors from the log, or compile in a batch run, fix them, and Unity leaves Safe Mode by itself.

**Watch for.**
- The package notices native message boxes and Editor modal windows, but not operating-system file or folder pickers, so keep a timeout as the fallback signal.
- The package warns when the Editor wasn't started for automation: a modal dialog then stalls every command until a person dismisses it.
- A dialog hidden behind other windows looks exactly like a hang.

**Diagnose.** Commands time out with no error → a dialog, or the Editor is still settling; read the status. The CLI exits with 7 → the Editor is closed, the package isn't loaded, or the project is in Safe Mode.

**API facts** (check the installed version):
- `EditorApplication.isCompiling` reports script compilation, and `EditorApplication.isUpdating` reports an asset database refresh (verified on 6000.6).
- Safe Mode runs no managed code from the project or its packages, so editor scripts, asset postprocessors and scripted importers don't run, and Unity exits Safe Mode by itself once no compile errors remain (verified on 6000.6).
- In batch mode, Unity quits when the project has compile errors, unless `-ignoreCompilerErrors` is passed (verified on 6000.6).
- Static constructors marked `[InitializeOnLoad]` run when the project loads and after every recompile, before asset import has finished, so they must not load assets (verified on 6000.6).

## The compile loop

**Goal.** Every code change is compiled, its errors are read from Unity's own report, and they are fixed before anything else runs.

**Build.**
1. Write the change.
2. Recompile. Live route: the CLI's `recompile`, which reports compile errors (`--strict` also fails on warnings). Batch route: a short batch run that opens the project and calls a trivial editor method, then reads the exit code and the log.
3. Wait until the Editor is ready.
4. Read the errors: the log lists each compiler error with its file, line and `CS` code.
5. Fix every error before any capture, test or build. Warnings that say obsolete or deprecated count as failures too ([validation.md](validation.md), Console discipline).
6. After a timeout or a domain reload, never repeat a write blindly. Re-read the file, see whether the edit already landed, and only then decide.

**Watch for.**
- The API Updater runs in batch mode only with `-accept-apiupdate`; without it, old API calls stay compile errors. Fixing the code by hand is clearer; if the updater does run, review its diff.
- One compile error stops every assembly that depends on it, so nothing new from those assemblies runs, including the setup scripts and tests in them.

**API facts** (check the installed version):
- `CompilationPipeline.assemblyCompilationFinished` hands over each assembly's compiler messages, and `compilationFinished` fires after the last one (verified on 6000.6).
- The API Updater doesn't run in batch mode unless `-accept-apiupdate` is passed, which can leave compile errors (verified on 6000.6).

## Editor scripts are the main lever

**Goal.** Scenes, prefabs and settings come from code that anyone can rerun, so the project can be rebuilt from source at any round.

**Build.**
1. Write each setup step as a static method in an `Editor` folder that builds one thing: a scene, a set of prefabs, materials, lighting, settings. Make it idempotent: running it twice gives the same result, because it replaces exactly what it owns.
2. Expose the same method twice: as a menu item for the live route, and as an `-executeMethod` entry for batch mode.
3. Drive layouts from data and a seed, never from hand placement, so a rebuild matches.
4. End every step that builds or changes a lit scene with a lighting bake (`Lightmapping.Bake`): new projects never bake on scene load, so an unbaked scene shows the default sky's ambient light and reflections ([lighting-and-shadows.md](lighting-and-shadows.md)). Baking needs a graphics device, so never run it with `-nographics`.
5. Save explicitly ([project-hygiene.md](project-hygiene.md), Marking dirty and saving), log one line per created asset, and in batch mode fail loudly: throw, or exit with a non-zero code.
6. Read arguments such as an output path, a seed or a view name from `System.Environment.GetCommandLineArgs`.
7. Change Player, quality, tag and layer settings from editor scripts too, so every settings change is reviewable code.
8. Never hand-author scene or prefab YAML ([project-hygiene.md](project-hygiene.md)).

**Start here** (adjust to the goal): one menu root, such as `Tools/Forge`, for every setup, capture and build entry, and a Rebuild All entry that runs the setup steps in order.

**API facts** (check the installed version):
- The `MenuItem` attribute turns a static method into a menu command (verified on 6000.6).
- `-executeMethod` calls a static method whose script sits in an `Editor` folder; an exception exits with code 1, `EditorApplication.Exit` sets any other code, and the method reads extra arguments with `System.Environment.GetCommandLineArgs` (verified on 6000.6).

## Batch mode: flags and exit codes

**Goal.** Every batch run is unattended, bounded in time, logged to its own file, and judged by its exit code and its log together.

**Build.** The usual flags, passed to the editor binary (`Unity.app/Contents/MacOS/Unity` inside the version's folder under `/Applications/Unity/Hub/Editor/`):
- `-batchmode` and `-projectPath <path>` on every run, and `-logFile <path>` with a new file per run (for example under `artifacts/logs/`), so each run's log stands alone.
- `-executeMethod <Class.Method>` for setup, capture and build scripts.
- `-quit` once a synchronous method has finished. Leave it off for test runs and for methods that wait on async work.
- `-buildTarget <target>` or `-activeBuildProfile <path>`, so the project opens on the right platform.
- `-accept-apiupdate` only when the user has agreed to let the updater rewrite scripts.
- `-timestamps`, and `-stackTraceLogType Full` when a stack trace comes out truncated.
- Never `-nographics` for anything that renders, captures or bakes lighting.

**Watch for.**
- Exit code 0 isn't proof: `-quit` can hide errors that still appear in the log. Read the log on every run.
- A project that has never been imported does its full import first, which takes minutes, and opens on the default platform unless a target is given.
- Test runs report through their result file, not their exit code ([validation.md](validation.md), Tests from the command line).

**API facts** (check the installed version):
- `-batchmode` suppresses dialogs, exits with code 1 when script code throws or another operation fails, and prints only a short log to the console while the log file keeps everything (verified on 6000.6).
- `-quit` can hide error messages, quits before tests finish when combined with `-runTests`, can hang with async code, and by default waits 300 seconds for pending async work (`-quitTimeout`) (verified on 6000.6).
- `-nographics` starts without a graphics device, can't bake GI, and turns output logs off unless `-logFile` is given (verified on 6000.6).
- `Application.isBatchMode` is true when Unity was launched with `-batchmode` (verified on 6000.6).

## The engine CLI and its editor package

**Goal.** An approved agent drives an open Editor through shell commands, knowing exactly what the installed CLI release can do.

**Build.**
1. **What it is:** Unity's standalone `unity` binary, free and separate from Unity AI, still experimental, with weekly beta releases (a 1.0.0 beta when this was written, installed by the Hub). On its own it manages editors, modules and projects and runs batch builds and tests. Driving an open Editor also needs the editor package `com.unity.pipeline`, which works with Unity 6.0 and later.
2. **Read the installed release first:** `unity --help`, `unity <command> --help`, `unity commands --format json` for a machine-readable list, and `unity version`. Trust these over memory and over this file.
3. **Sign in:** controlling an Editor needs a signed-in CLI session. The user signs in once with `unity auth login`; `unity auth status` checks it.
4. **Install the package:** tick Use Unity CLI when creating the project in the Hub. Otherwise, with the project open in the Editor, run `unity pipeline install`, wait for the recompile, and confirm with `unity pipeline list`.
5. **Connect:** `unity status` lists the connected Editors (port, project path, version, process ID), `unity command` lists the commands an Editor exposes, `unity list` shows each tool with its parameter schema, and `unity command <name>` runs one. Pass `--format json` when parsing: piped output is tab-separated by default, and errors go to standard error.
6. **What the package covers** (confirm with `unity list`): Play, stop and status; recompile; tests; build targets, profiles and builds; captures and screenshots; console logs; menu items; scenes, objects, components, prefabs and materials; lighting and navigation bakes; packages; project settings, whose state-changing commands take a confirm or dry-run option; performance stats; and a Project Auditor scan. A project can register its own commands from static editor methods.
7. **Security:** the package's server inside the Editor listens on the loopback address only, on a port from a fixed range, and writes a descriptor with a per-session bearer token to `Library/Pipeline/`, readable only by the user. Any process running as that user can read it, so never expose the port, never copy the token into logs or commits, and keep `Library/` ignored. Requests carrying a browser origin are refused by default.
8. **MCP mode** (`unity mcp`) exists for harnesses that can't run shell commands; plain shell commands are faster and cheaper. Its capture tools can return a desktop screenshot instead of a render ([validation.md](validation.md), The screenshot-fallback trap). Configuring a harness for MCP mode edits that harness's settings, sometimes including its network sandbox, so ask the user first.
9. **Exit codes:** 0 success; 1 general error; 2 usage error; 3 authentication; 4 configuration required; 6 the operation failed (for tests: the run didn't finish); 7 a service or the Editor couldn't be reached, safe to retry; 8 tests ran and some failed, never retried; 130 and 143 interrupted.

**Watch for.**
- `unity logs` shows only the CLI's log file. It never shows the Editor's, so a clean result there says nothing about compile errors.
- The MCP server once built into Unity's AI Assistant package is deprecated, and Unity points to this CLI instead. Don't set it up.
- The CLI can install Unity's own agent skills into a harness. Forge doesn't need them, and each installed skill adds text to every session.

## One-off code needs a yes

**Goal.** Arbitrary code runs inside the user's Editor only after the user says yes, and anything worth running twice becomes a named command.

**Build.**
1. The CLI can compile and run a snippet of C# inside the open Editor, or inside a development player that runs the package's runtime server, without a recompile. Unity itself says to handle this as you would remote code execution, and to use it only for local development.
2. Before each run, tell the user in plain words what the code will do, what it touches, and whether it saves anything. Wait for an explicit yes, and note the approval in the handback.
3. That includes read-only inspection, unless the user has approved a named kind of read-only query for the session.
4. Turn anything run twice into an editor script or a registered command: committed, reviewable and reproducible.
5. Never run one-off code against a shipped build. The runtime server is for development builds only and stays off by default.

## Community editor bridges

**Goal.** A community bridge is used only when the user chooses it, knowing what it can do.

**Build.**
1. Open-source packages exist that expose the Editor to agents, through MCP or a local web server. They are not a default route here.
2. Use one only after the user approves it by name for this project, once you have explained what it does: it runs inside the Editor with the user's permissions, many can execute arbitrary C#, some download a server binary at runtime or need a third-party account or paid API keys, and some write their settings into `ProjectSettings/`.
3. If approved: loopback only, one bridge per project, no keys in the repository, the same one-off code rule as the CLI, the same readiness checks, and the same capture proof ([validation.md](validation.md)).

## Logs: Editor, player and CLI

**Goal.** The agent reads the right log for each question, from a file it knows is current.

**Build.**
1. **Editor:** `Logs/Editor.log` inside the project by default. For batch runs, read the file passed with `-logFile`.
2. **Package Manager:** `Logs/upm.log` inside the project.
3. **Player on macOS:** `~/Library/Logs/<company>/<product>/Player.log`, or the path passed with `-logFile` at launch. A Web player logs to the browser's JavaScript console.
4. **CLI:** its own log in the Hub's logs folder, read with `unity logs`.
5. **Hub and licensing:** `~/Library/Application Support/UnityHub/logs/` and `~/Library/Logs/Unity/Unity.Licensing.Client.log`.
6. In every log, look for compiler errors, exceptions with stack traces, shader errors, missing-script warnings, licensing lines, and the game's own ready and provenance lines ([validation.md](validation.md)).

**Watch for.** The Console window can collapse repeated messages and can be cleared, while the log file keeps everything. Treat the file as the record.

**API facts** (check the installed version):
- By default the Editor writes `Logs/Editor.log` inside the open project, and the Package Manager writes `Logs/upm.log` there too (verified on 6000.6).
- A macOS player writes `Player.log` under `~/Library/Logs/<company>/<product>/`, and a Web player logs to the browser's JavaScript console (verified on 6000.6).
- `Application.consoleLogPath` returns the running Editor's or player's log path, or an empty string where the platform keeps no log file (verified on 6000.6).

## Builds from the command line

**Goal.** Each target builds from one documented command, and every build records the profile that made it.

**Build.**
1. Keep one build profile per target and purpose (for example Mac capture, Mac release, Web), created in File > Build Profiles or with the CLI's `build --create-profile`. Profiles are assets, so they are committed and reviewed like code.
2. Build in batch mode with `-activeBuildProfile <project-relative path>` and `-build <output path>`, plus `-quit` and `-logFile`. A macOS output path ends in `.app`.
3. For extra steps, write a build method around `BuildPipeline.BuildPlayer` and call it with `-executeMethod`, still passing `-activeBuildProfile` or `-buildTarget` on the command line.
4. Build one target per process: switching the target from inside a running script doesn't take effect in batch mode.
5. Judge the result from the build report's summary, then the exit code and the log.
6. Record the build profile in the provenance line; profiles can override Player, quality and graphics settings, so check the overrides before blaming the project settings.
7. `unity build` wraps all of this, and `unity build run` launches the latest build; check its flags with `--help`.

**Watch for.** Builds started from the Build Profiles window skip custom build scripts. Target choices, backends, budgets and Web limits belong to [performance-and-builds.md](performance-and-builds.md).

**API facts** (check the installed version):
- `-activeBuildProfile` takes a path relative to the project root, applies the profile's scripting defines before compiling, and with `-executeMethod` compiles with those defines before calling the method (verified on 6000.6).
- A command-line build can target only one platform per invocation, because `BuildProfile.SetActiveBuildProfile`, `EditorUserBuildSettings.SwitchActiveBuildTargetAsync` and `BuildPlayerOptions.target` don't work as expected in batch mode (verified on 6000.6).
- `BuildPipeline.BuildPlayer` returns a `BuildReport` whose summary result says whether the build succeeded (verified on 6000.6).
- Build profile overrides apply both in Play mode and in the player, but Play mode uses the quality level selected in the global Quality settings (verified on 6000.6).

## Symptom → cause

| Symptom | Likely cause | First check |
| --- | --- | --- |
| A batch run can't open the project | an Editor or a stale Unity process has it open | running Unity processes for this path, and `unity status` |
| Live commands hang with no reply | a modal dialog, or the Editor still settling | the package's status, then ask the user what is on screen |
| The CLI exits with 7 | the Editor is closed, the package isn't loaded, or the project is in Safe Mode | `unity status`, then the project's `Logs/Editor.log` |
| The CLI exits with 3 | the CLI isn't signed in | `unity auth status` |
| A batch run exits with 1 and the console shows little | an exception in the method, or compile errors | the run's log file, for exceptions and `CS` errors |
| A batch run never exits | async work under `-quit`, or a method that waits forever | the tail of the run's log |
| A test run ends before the tests finish | `-quit` combined with `-runTests` | the command line ([validation.md](validation.md)) |
| Old-API errors appear only in batch runs | the API Updater is skipped in batch mode | whether `-accept-apiupdate` was agreed and passed |
| The same edit appears twice in a file | a write retried blindly after a reload or timeout | the file's content before the retry |
| A setup script ran, but the next process sees nothing | the scene or asset was never saved | the save calls ([project-hygiene.md](project-hygiene.md)) |
| New C# isn't picked up by the open Editor | no refresh or recompile yet | `unity recompile` and its report |
| A build has the wrong scenes or settings | the wrong profile, or overrides inside the profile | the profile passed, its scene list and its overrides |
| A build fails for only one of two targets | the target was switched inside a running script | one process per target |
| A "capture" shows the whole desktop | the MCP capture fallback after a timeout or a dialog | the note returned with the capture ([validation.md](validation.md)) |
| The log looks clean while the Editor shows errors | reading the CLI log or the global log instead of the project's | `Logs/Editor.log`, or the run's `-logFile` |
