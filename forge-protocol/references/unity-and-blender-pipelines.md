# Pipelines: Blender, web (Three.js / WebGPU) and Unity

The loop only needs captures of the running build, so any stack works. These are the routes this skill has tools for. Pick one at plan time from the goal and from what the Rule 0 probe found installed.

## Picking a stack

| Stack | Good for | Assets | Capture |
| :--- | :--- | :--- | :--- |
| **Web**: Three.js / WebGPU, canvas, DOM | instant browser demos, shareable links, shader showcases, UI and data viz | code, Blender (headless or MCP) exporting `.glb`, CC0 assets | `templates/capture.mjs` (Playwright) |
| **Unity** via Unity MCP | standalone builds, heavy physics, terrain tools, Shader Graph | Blender exporting `.fbx` / `.glb` into `Assets/` | an Editor capture script (below) |
| **Other**: native, Godot, notebooks, video | whatever the goal needs | any | any route that writes stills, then `forge.py manifest` |

## Blender

### Live session (Blender MCP)

- The [blender-mcp](https://github.com/ahujasid/blender-mcp) addon runs a socket server inside Blender, on `localhost:9876` by default. The MCP server (PyPI package `mcp-for-blender`; `uvx blender-mcp` still works) relays to it, and `scripts/blender_mcp_cli.py` talks to the same socket directly. Host and port follow `BLENDER_HOST` and `BLENDER_PORT`.
- Probe: `python3 scripts/blender_mcp_cli.py status` exits 0 when reachable and 3 when Blender or the addon server is not running. Command names and parameters follow the addon 1.5 source (protocol 4); `status` has been run against a live Blender 5.2 LTS session, the other commands against a mock server.
- PolyHaven tools exist only after `blender_mcp_cli.py enable-polyhaven`. PolyHaven assets are CC0.
- Safety: `exec` runs arbitrary Python inside the user's Blender with the user's permissions and bypasses the MCP server's `BLENDER_MCP_SAFE_MODE` check, and the addon socket has no authentication. The CLI refuses non-loopback hosts unless `--allow-remote` is passed. Tell the user before running code in a session they have open, and prefer headless workers for generation.

### Headless workers (parallel-safe)

- Each asset builder runs its own process and exports `.glb`:
  `blender -b --factory-startup --python-exit-code 1 -P tools/gen_rock.py -- --out public/models/rock.glb`
  Keep `--python-exit-code 1`: without it Blender exits 0 even when the script raises.
- Turnaround gate for every hero asset:
  `blender -b --factory-startup --python-exit-code 1 -P scripts/blender_turnaround.py -- --input public/models/rock.glb --output artifacts/turnarounds/rock.png`
  This writes a strip of views (`--views`, `--angles`, `--elevation`, `--size`, `--engine eevee|cycles|workbench`) plus `rock.json` with triangle, material and texture counts and the asset's size in meters. It was tested on Blender 5.2 LTS with all three engines.
- The orchestrator opens every turnaround and rejects primitive stand-ins, flat shading, broken normals or a wrong scale before the asset enters the scene. A very low triangle count in the json is a quick tell for a primitive.

## Web capture

- `forge.py init --stack web` copies `templates/capture.mjs` to `tools/capture.mjs`. It fixes viewport, device pixel ratio, locale and timezone; it can seed `Math.random` (`--seed`) and pause page time (`--clock fixed`) so animations advance only between captures, which repeats animation timing to within about a millisecond across runs. It waits for `window.__FORGE_READY__ === true` when the page defines it, calls `window.__forgeSetView(name)` through a view's `eval` for camera presets or UI states, saves console errors next to the stills for C3, and writes `MANIFEST.md`.
- Setup: `npm i -D playwright`, then `npx playwright install chromium`, or pass `--channel chrome` to drive an installed Chrome.
- Pass `--build-id "$(python3 <skill-dir>/scripts/forge.py --project . build-id)"` so the manifest records the build.
- Headless Chromium may render WebGL or WebGPU through a software fallback. If stills differ from a real browser, run with a GPU-backed channel or headed, and keep one route for every round.

## Unity (Unity MCP)

Checked against the Unity documentation for `com.unity.ai.assistant` 2.0.0-pre.1, which is a pre-release:

- Requires Unity 6 (6000.0) or later with the `com.unity.ai.assistant` package installed.
- The editor starts the MCP bridge automatically. Confirm it under **Edit > Project Settings > AI > Unity MCP** (Unity Bridge status: Running).
- The relay binary installs to `~/.unity/relay/`, and MCP clients launch it with `--mcp`:
  - macOS (Apple Silicon): `~/.unity/relay/relay_mac_arm64.app/Contents/MacOS/relay_mac_arm64`
  - macOS (Intel): `~/.unity/relay/relay_mac_x64.app/Contents/MacOS/relay_mac_x64`
  - Windows: `%USERPROFILE%\.unity\relay\relay_win.exe`
  - Linux: `~/.unity/relay/relay_linux`
- Approve the client once under **Pending Connections** on the same settings page.
- Built-in tools include `Unity_ManageScene`, `Unity_ManageGameObject` and `Unity_ReadConsole`. Custom tools can be registered through attributes, interfaces or runtime APIs.
- Call `Unity_ReadConsole` after every script or shader change and capture only with zero errors.
- Capture: write an Editor script that renders each view's camera into a `RenderTexture` at the BRIEF size and saves PNGs to `artifacts/stills/`. Run it from the editor, or with `Unity -batchmode -projectPath . -executeMethod <Class.Method> -quit` (rendering needs a GPU, so do not pass `-nographics`), then run `forge.py manifest`.

Example client config for hosts that read `mcpServers` JSON (macOS Apple Silicon):

```json
{
  "mcpServers": {
    "blender": { "command": "uvx", "args": ["mcp-for-blender"] },
    "unity-mcp": {
      "command": "~/.unity/relay/relay_mac_arm64.app/Contents/MacOS/relay_mac_arm64",
      "args": ["--mcp"]
    }
  }
}
```

Clients launched from a GUI may not inherit your shell `PATH`. If `uvx` fails to start, use its full path (`which uvx`).

## When a tool is missing

| Missing | Fallback |
| :--- | :--- |
| Blender | procedural geometry in code or licensed models; say so in the plan |
| Live Blender session | headless workers only |
| Playwright | the host's browser tool or the app's own screenshot route; then `forge.py manifest` |
| ffmpeg | skip composites; the critic grades stills directly and the workbench slider still compares rounds |
| Unity MCP | Unity batch-mode capture, or choose the web stack at plan time |
