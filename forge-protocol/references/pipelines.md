# Pipelines: stacks, Blender, web and Unity

The loop only needs captures of the running build, so any stack works. Pick one at plan time from the goal and from what the Rule 0 probe found. This file covers the routes most visual builds use; adapt freely.

## Picking a stack

| Stack | Good for | Assets | Capture |
| :--- | :--- | :--- | :--- |
| **Web**: Three.js / WebGPU, canvas, DOM | instant browser demos, shareable links, shader showcases, UI and data viz | code, Blender exporting `.glb`, licensed or CC0 assets | a browser capture ([capture-and-tools.md](capture-and-tools.md)) |
| **Unity** | standalone builds, heavy physics, terrain tools, node-based shaders | Blender exporting `.fbx` (or `.glb` through Unity's glTF importer package) into the project | an engine render per view (below) |
| **Other**: native, other engines, notebooks, video | whatever the goal needs | any | any route that writes stills from the live build |

Only go 3D when the goal needs it. A 2D, canvas or DOM build that meets the bar beats a 3D one that doesn't.

## Blender

### Live session over MCP

- Blender can run a small server inside the app (the open-source [blender-mcp](https://github.com/ahujasid/blender-mcp) addon) that an MCP server relays to. Connect it using whatever MCP setup your agent supports.
- Use the live session for look-dev, scene inspection, viewport screenshots and quick material or lighting passes the user can watch.
- Probe it with a read-only request such as scene info. If that fails, Blender or the addon server is not running; say so in the plan and fall back to headless workers.
- The addon can fetch PolyHaven assets (CC0) once that feature is enabled in Blender.
- Safety: code sent this way runs inside the user's open Blender with their permissions, and the addon's socket has no authentication. Tell the user before running code in a session they have open, keep the connection on the local machine, and prefer headless workers for generation.
- No MCP in your environment but the addon is running? A small client that sends one JSON command and reads one JSON reply is enough. Verify it with a read-only command before sending any code.

### Headless workers (parallel-safe)

- Each asset builder runs its own background Blender process with a short Blender Python script that builds the asset and exports `.glb` (or `.fbx` for Unity). The command shape is `blender -b --factory-startup --python-exit-code 1 -P <script> -- <your arguments>`.
- Keep `--python-exit-code 1`: without it Blender exits 0 even when the script fails. Verify once by running a script that raises on purpose.
- One asset per worker. Hero objects are authored multi-part shapes, never primitive stand-ins.

### Turnaround gate for hero assets

Before a hero asset enters the scene, render a turnaround and open it yourself.
- Write, if you need one, a background Blender script that imports the asset, frames it from its bounding box, renders a few evenly spaced views at a slight elevation with one consistent light and a shadow-catching ground, joins them into one strip in `artifacts/turnarounds/`, and records stats next to it: triangle count, materials, textures, and size in meters.
- Verify it on a plain cube and on a dense built-in test mesh: every view shows the whole object, the stats differ the way they should, and a missing input makes Blender exit non-zero.
- Reject primitive stand-ins, flat shading, broken normals and wrong scale. A very low triangle count for a hero object is a quick tell. Gate each asset yourself; never delegate the call.

## Web: Three.js, WebGPU, canvas and DOM

- Three.js builds: read [threejs/router.md](threejs/router.md) first. It routes the plan and each builder to the topic files its piece needs, and sets the version policy.
- At plan time, probe the installed three.js revision and the backend each target device and the capture route actually land on (WebGPU or the WebGL 2 fallback, on a hardware or software adapter), and record both in `BRIEF.md` under Stack.
- Load Blender exports as `.glb`; keep texel density and scale consistent across assets (one unit is one meter unless the project says otherwise).
- Expose small hooks for capture when they help: a ready flag the page sets once assets and the first frames are in, and a set-view function for camera presets or UI states. Three.js builds also expose a debug-mode switch and a quality-tier switch that change real pipeline output, reset, pause and step controls, and a metrics readout ([threejs/foundation.md](threejs/foundation.md)).
- Prefer a fixed device pixel ratio and deterministic animation time during capture, so rounds compare cleanly.

## Unity

- Unity builds: read [unity/router.md](unity/router.md) first. It routes the plan and each builder to the topic files its piece needs, and sets the version policy.
- Agents act on a Unity project through files they write, through batch mode with the Editor closed, or, once the user approves, through Unity's engine CLI and its editor package (`com.unity.pipeline`), which drive an open Editor. Tell the user and get a yes before running one-off code through the CLI. Routes, sign-in, exit codes and logs are in [unity/agent-control.md](unity/agent-control.md).
- Don't set up the MCP server that shipped inside Unity's AI Assistant package: Unity has deprecated it in favor of the CLI. A community editor bridge is an option only when the user approves one.
- Read the Editor log (the project's `Logs/Editor.log`, or the batch run's `-logFile`) or the CLI's recompile report after every script or shader change, and capture only when it shows zero errors and no deprecation warnings.
- Capture with a script inside the build that saves each view at the `BRIEF.md` size to `artifacts/stills/`, preferably from a freshly launched player, and prove the route on a known answer before round 1. Rendering needs a GPU, so never pass `-nographics`. Then write `MANIFEST.md` with the Unity provenance line ([unity/validation.md](unity/validation.md)).
- From Blender, export `.fbx`, Unity's own import format. `.glb` needs Unity's glTF importer package, which the editor doesn't bundle, so the agent adds it to the project once the user agrees. Don't rely on Unity importing `.blend` files directly, which works only where Blender is installed. Check scale and orientation on import ([unity/assets-and-import.md](unity/assets-and-import.md)).
