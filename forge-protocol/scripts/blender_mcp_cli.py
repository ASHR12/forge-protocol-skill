#!/usr/bin/env python3
"""Command-line client for the Blender MCP addon's socket server (blender-mcp, published as mcp-for-blender).

Speaks the addon's protocol directly: one JSON object {"type": ..., "params": {...}} per request and one
JSON object back ({"status": "success", "result": ...} or {"status": "error", "message": ...}), with no
framing and the socket left open. Checked against addon 1.5 (protocol 4); `status` falls back to
get_scene_info on older addons that lack get_addon_info.

  blender_mcp_cli.py status                       reachability, addon and Blender versions, PolyHaven state
  blender_mcp_cli.py scene                        scene summary
  blender_mcp_cli.py exec --file build_rock.py    run bpy code in the live session (see Safety)
  blender_mcp_cli.py exec --code "print(len(bpy.data.objects))"
  blender_mcp_cli.py enable-polyhaven             turn on the addon's PolyHaven tools for this scene
  blender_mcp_cli.py polyhaven-search --type textures --categories rock
  blender_mcp_cli.py polyhaven-download --id rock_ground --type textures --resolution 2k
  blender_mcp_cli.py screenshot --output artifacts/turnarounds/viewport.png [--max-size 1600]

Host and port default to BLENDER_HOST / BLENDER_PORT, then localhost:9876, like the MCP server.
Safety: exec runs arbitrary Python inside Blender with your user's permissions, bypasses the MCP server's
BLENDER_MCP_SAFE_MODE check, and the addon socket has no authentication, so non-loopback hosts are refused
unless --allow-remote is given.

Prints one JSON object on stdout in every case. Exit codes: 0 ok, 1 Blender reported an error,
2 usage error, 3 cannot connect, 4 timeout or malformed response.
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import os
import socket
import sys
import time
from pathlib import Path

DEFAULT_PORT = 9876
MAX_RESPONSE_BYTES = 64 * 1024 * 1024


class CliError(Exception):
    def __init__(self, message: str, code: int, hint: str = ""):
        super().__init__(message)
        self.code = code
        self.hint = hint


def is_loopback(host: str) -> bool:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    addresses = {info[4][0] for info in infos}
    return bool(addresses) and all(ipaddress.ip_address(a.split("%")[0]).is_loopback for a in addresses)


def send(cmd_type: str, params: dict | None, host: str, port: int,
         timeout: float = 60.0, connect_timeout: float = 5.0) -> dict:
    payload = json.dumps({"type": cmd_type, "params": params or {}}).encode("utf-8")
    try:
        sock = socket.create_connection((host, port), timeout=connect_timeout)
    except socket.timeout as exc:
        raise CliError(f"timed out connecting to Blender MCP at {host}:{port}", 3,
                       "Is Blender running with the BlenderMCP addon server started?") from exc
    except OSError as exc:
        raise CliError(f"cannot connect to Blender MCP at {host}:{port} ({exc.strerror or exc})", 3,
                       "Open Blender with the BlenderMCP addon and start its server (View3D sidebar > BlenderMCP), "
                       "or use headless blender -b for batch work.") from exc
    deadline = time.monotonic() + timeout
    buffer = b""
    try:
        sock.sendall(payload)
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise socket.timeout()
            sock.settimeout(remaining)
            chunk = sock.recv(65536)
            if not chunk:
                if not buffer:
                    raise CliError("Blender MCP closed the connection without a response", 4)
                raise CliError("Blender MCP closed the connection mid-response", 4)
            buffer += chunk
            if len(buffer) > MAX_RESPONSE_BYTES:
                raise CliError(f"response larger than {MAX_RESPONSE_BYTES} bytes; aborting", 4)
            try:
                parsed = json.loads(buffer)
            except ValueError:
                continue
            if not isinstance(parsed, dict):
                raise CliError("Blender MCP returned JSON that is not an object", 4)
            return parsed
    except socket.timeout as exc:
        raise CliError(f"no complete response from Blender MCP within {timeout:g}s for '{cmd_type}'", 4,
                       "Long operations (downloads, heavy scripts) may need --timeout.") from exc
    finally:
        sock.close()


def result_error(response: dict) -> str | None:
    if response.get("status") == "error":
        return str(response.get("message") or "unknown error")
    result = response.get("result")
    if isinstance(result, dict) and result.get("error"):
        return str(result["error"])
    return None


def checked(response: dict, cmd_type: str) -> dict:
    error = result_error(response)
    if error:
        hint = ""
        if error.startswith("Unknown command type") and "polyhaven" in cmd_type:
            hint = "PolyHaven tools are disabled in this Blender scene; run: blender_mcp_cli.py enable-polyhaven"
        raise CliError(error, 1, hint)
    return response


def cmd_status(args) -> dict:
    info = send("get_addon_info", None, args.host, args.port, args.timeout)
    out: dict = {"reachable": True, "host": args.host, "port": args.port}
    if result_error(info) and str(info.get("message", "")).startswith("Unknown command type"):
        scene = checked(send("get_scene_info", None, args.host, args.port, args.timeout), "get_scene_info")
        out["addon"] = {"note": "addon predates get_addon_info; version unknown"}
        out["scene"] = (scene.get("result") or {}).get("name")
    else:
        result = checked(info, "get_addon_info").get("result") or {}
        out["addon"] = {k: result.get(k) for k in ("name", "addon_version", "protocol_version")}
        out["blender_version"] = result.get("blender_version")
    ph = send("get_polyhaven_status", None, args.host, args.port, args.timeout)
    out["polyhaven"] = ph.get("result") if not result_error(ph) else {"error": result_error(ph)}
    return out


def cmd_exec(args) -> dict:
    if args.file:
        path = Path(args.file).expanduser()
        if not path.is_file():
            raise CliError(f"script not found: {path}", 2)
        code = path.read_text(encoding="utf-8")
    else:
        code = args.code
    return checked(send("execute_code", {"code": code}, args.host, args.port, args.timeout), "execute_code")


def cmd_enable_polyhaven(args) -> dict:
    code = "import bpy\nbpy.context.scene.blendermcp_use_polyhaven = True\nprint(bpy.context.scene.blendermcp_use_polyhaven)"
    checked(send("execute_code", {"code": code}, args.host, args.port, args.timeout), "execute_code")
    status = checked(send("get_polyhaven_status", None, args.host, args.port, args.timeout), "get_polyhaven_status")
    if not (status.get("result") or {}).get("enabled"):
        raise CliError("PolyHaven still reports disabled after enabling", 1, "Enable it in the BlenderMCP sidebar panel.")
    return status


def cmd_search(args) -> dict:
    params = {"asset_type": args.type}
    if args.categories:
        params["categories"] = args.categories
    return checked(send("search_polyhaven_assets", params, args.host, args.port, args.timeout), "search_polyhaven_assets")


def cmd_download(args) -> dict:
    params = {"asset_id": args.id, "asset_type": args.type, "resolution": args.resolution}
    if args.file_format:
        params["file_format"] = args.file_format
    return checked(send("download_polyhaven_asset", params, args.host, args.port, max(args.timeout, 180.0)),
                   "download_polyhaven_asset")


def cmd_screenshot(args) -> dict:
    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    params = {"filepath": str(out), "max_size": args.max_size, "format": out.suffix.lstrip(".").lower() or "png"}
    response = checked(send("get_viewport_screenshot", params, args.host, args.port, args.timeout), "get_viewport_screenshot")
    if not out.is_file():
        raise CliError(f"Blender reported success but {out} does not exist", 1,
                       "The CLI and Blender must share a filesystem (no remote hosts for screenshots).")
    return response


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="blender_mcp_cli.py", description=__doc__.split("\n\n")[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=__doc__.split("\n\n", 1)[1])
    parser.add_argument("--host", default=os.environ.get("BLENDER_HOST", "localhost"))
    parser.add_argument("--port", type=int, default=None, help=f"default: BLENDER_PORT or {DEFAULT_PORT}")
    parser.add_argument("--timeout", type=float, default=60.0, help="seconds to wait for a response (default 60)")
    parser.add_argument("--allow-remote", action="store_true", help="allow a non-loopback host (unauthenticated socket)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status", help="reachability, versions, PolyHaven state").set_defaults(func=cmd_status)
    sub.add_parser("scene", help="scene summary").set_defaults(
        func=lambda a: checked(send("get_scene_info", None, a.host, a.port, a.timeout), "get_scene_info"))
    p = sub.add_parser("exec", help="run Python in the live Blender session")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="path to a .py file")
    group.add_argument("--code", help="inline Python")
    p.set_defaults(func=cmd_exec)
    sub.add_parser("enable-polyhaven", help="enable the addon's PolyHaven tools").set_defaults(func=cmd_enable_polyhaven)
    p = sub.add_parser("polyhaven-search", help="search PolyHaven assets (first 20 results)")
    p.add_argument("--type", default="all", choices=["hdris", "textures", "models", "all"])
    p.add_argument("--categories", default="", help="comma-separated categories")
    p.set_defaults(func=cmd_search)
    p = sub.add_parser("polyhaven-download", help="download a PolyHaven asset into the scene")
    p.add_argument("--id", required=True)
    p.add_argument("--type", required=True, choices=["hdris", "textures", "models"])
    p.add_argument("--resolution", default="1k", help="e.g. 1k, 2k, 4k")
    p.add_argument("--file-format", help="e.g. hdr, exr, gltf, blend")
    p.set_defaults(func=cmd_download)
    p = sub.add_parser("screenshot", help="save the 3D viewport to an image")
    p.add_argument("--output", required=True)
    p.add_argument("--max-size", type=int, default=1600, help="longest edge in px (default 1600)")
    p.set_defaults(func=cmd_screenshot)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.port is None:
            env_port = os.environ.get("BLENDER_PORT", str(DEFAULT_PORT))
            if not env_port.isdigit():
                raise CliError(f"BLENDER_PORT must be a number, got {env_port!r}", 2)
            args.port = int(env_port)
        if not 0 < args.port < 65536:
            raise CliError(f"--port out of range: {args.port}", 2)
        if args.timeout <= 0:
            raise CliError("--timeout must be positive", 2)
        if not args.allow_remote and not is_loopback(args.host):
            raise CliError(f"refusing non-loopback host {args.host!r}: the addon socket is unauthenticated", 2,
                           "Use an SSH tunnel to reach a remote Blender, or pass --allow-remote on a trusted network.")
        result = args.func(args)
        print(json.dumps(result, indent=2))
        return 0
    except CliError as exc:
        print(json.dumps({"status": "error", "message": str(exc), **({"hint": exc.hint} if exc.hint else {})}, indent=2))
        return exc.code


if __name__ == "__main__":
    sys.exit(main())
