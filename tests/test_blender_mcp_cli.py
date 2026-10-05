import json
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path

from helpers import run_script

SCENE_NAME = "Kocka ünïcødé ✓ " * 400


class MockAddon:
    """Speaks the blender-mcp addon protocol: one JSON object in, one JSON object out, socket kept open."""

    def __init__(self, mode="normal", polyhaven=False):
        self.mode = mode
        self.polyhaven = polyhaven
        self.received = []
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen()
        self.port = self.sock.getsockname()[1]
        self.thread = threading.Thread(target=self.serve, daemon=True)
        self.thread.start()

    def close(self):
        self.sock.close()

    def serve(self):
        while True:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            threading.Thread(target=self.handle, args=(conn,), daemon=True).start()

    def handle(self, conn):
        buf = b""
        with conn:
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    return
                buf += chunk
                try:
                    cmd = json.loads(buf)
                except ValueError:
                    continue
                buf = b""
                self.received.append(cmd)
                reply = self.reply(cmd)
                if self.mode == "silent":
                    time.sleep(3)
                    return
                data = json.dumps(reply, ensure_ascii=False).encode("utf-8")
                if self.mode == "close_mid":
                    conn.sendall(data[: len(data) // 2])
                    return
                for i in range(0, len(data), 7):
                    conn.sendall(data[i:i + 7])

    def reply(self, cmd):
        kind, params = cmd.get("type"), cmd.get("params", {})
        if kind == "get_addon_info":
            if self.mode == "old_addon":
                return {"status": "error", "message": "Unknown command type: get_addon_info"}
            return {"status": "success", "result": {"name": "Blender MCP", "addon_version": [1, 5],
                                                    "protocol_version": 4, "blender_version": "5.2.0 LTS"}}
        if kind == "get_polyhaven_status":
            return {"status": "success", "result": {"enabled": self.polyhaven, "message": "state"}}
        if kind == "get_scene_info":
            return {"status": "success", "result": {"name": SCENE_NAME, "object_count": 3}}
        if kind == "execute_code":
            if "raise" in params.get("code", ""):
                return {"status": "error", "message": "Code execution error: boom"}
            if "blendermcp_use_polyhaven = True" in params.get("code", ""):
                self.polyhaven = True
            return {"status": "success", "result": {"executed": True, "result": "ok\n"}}
        if kind == "get_viewport_screenshot":
            if self.mode == "tool_error":
                return {"status": "success", "result": {"error": "No 3D viewport found"}}
            Path(params["filepath"]).write_bytes(b"\x89PNG fake")
            return {"status": "success", "result": {"success": True, "filepath": params["filepath"]}}
        if kind in ("search_polyhaven_assets", "download_polyhaven_asset") and not self.polyhaven:
            return {"status": "error", "message": f"Unknown command type: {kind}"}
        if kind == "search_polyhaven_assets":
            return {"status": "success", "result": {"assets": {}, "total_count": 0, "returned_count": 0}}
        return {"status": "error", "message": f"Unknown command type: {kind}"}


def cli(port, *args, timeout="5"):
    res = run_script("blender_mcp_cli.py", "--port", str(port), "--timeout", timeout, *args)
    try:
        payload = json.loads(res.stdout)
    except ValueError:
        payload = None
    return res.returncode, payload, res


class BlenderCliTests(unittest.TestCase):
    def setUp(self):
        self.servers = []

    def tearDown(self):
        for server in self.servers:
            server.close()

    def server(self, **kw):
        server = MockAddon(**kw)
        self.servers.append(server)
        return server

    def test_status_reports_versions(self):
        server = self.server()
        code, out, res = cli(server.port, "status")
        self.assertEqual(code, 0, res.stdout + res.stderr)
        self.assertEqual(out["addon"]["protocol_version"], 4)
        self.assertEqual(out["blender_version"], "5.2.0 LTS")
        self.assertEqual(out["polyhaven"]["enabled"], False)

    def test_status_falls_back_for_older_addons(self):
        server = self.server(mode="old_addon")
        code, out, _ = cli(server.port, "status")
        self.assertEqual(code, 0)
        self.assertIn("predates", out["addon"]["note"])

    def test_chunked_utf8_response_is_reassembled(self):
        server = self.server()
        code, out, res = cli(server.port, "scene")
        self.assertEqual(code, 0, res.stdout + res.stderr)
        self.assertEqual(out["result"]["name"], SCENE_NAME)

    def test_connection_refused(self):
        probe = socket.socket()
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
        probe.close()
        code, out, _ = cli(port, "status")
        self.assertEqual(code, 3)
        self.assertEqual(out["status"], "error")
        self.assertIn("hint", out)

    def test_timeout_and_truncated_response(self):
        code, out, _ = cli(self.server(mode="silent").port, "status", timeout="0.5")
        self.assertEqual(code, 4)
        self.assertIn("no complete response", out["message"])
        code, out, _ = cli(self.server(mode="close_mid").port, "scene")
        self.assertEqual(code, 4)
        self.assertIn("mid-response", out["message"])

    def test_exec_file_code_and_errors(self):
        server = self.server()
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "build.py"
            script.write_text("import bpy\nprint('hi')\n")
            code, out, _ = cli(server.port, "exec", "--file", str(script))
            self.assertEqual(code, 0)
            self.assertEqual(server.received[-1]["params"]["code"], script.read_text())
            code, out, _ = cli(server.port, "exec", "--file", str(Path(tmp) / "missing.py"))
            self.assertEqual(code, 2)
        code, out, _ = cli(server.port, "exec", "--code", "raise RuntimeError()")
        self.assertEqual(code, 1)
        self.assertIn("boom", out["message"])

    def test_polyhaven_disabled_hint_then_enable(self):
        server = self.server()
        code, out, _ = cli(server.port, "polyhaven-search", "--type", "textures")
        self.assertEqual(code, 1)
        self.assertIn("enable-polyhaven", out["hint"])
        self.assertEqual(cli(server.port, "enable-polyhaven")[0], 0)
        code, out, _ = cli(server.port, "polyhaven-search", "--type", "textures", "--categories", "rock")
        self.assertEqual(code, 0)
        self.assertEqual(server.received[-1]["params"], {"asset_type": "textures", "categories": "rock"})

    def test_screenshot_success_and_tool_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "shots" / "view.png"
            server = self.server()
            code, out, _ = cli(server.port, "screenshot", "--output", str(target), "--max-size", "800")
            self.assertEqual(code, 0)
            self.assertTrue(target.is_file())
            self.assertEqual(server.received[-1]["params"]["max_size"], 800)
            code, out, _ = cli(self.server(mode="tool_error").port, "screenshot", "--output", str(target))
            self.assertEqual(code, 1)
            self.assertIn("No 3D viewport", out["message"])

    def test_remote_hosts_need_opt_in(self):
        res = run_script("blender_mcp_cli.py", "--host", "192.0.2.10", "status")
        self.assertEqual(res.returncode, 2)
        self.assertIn("non-loopback", json.loads(res.stdout)["message"])

    def test_help(self):
        self.assertEqual(run_script("blender_mcp_cli.py", "--help").returncode, 0)


if __name__ == "__main__":
    unittest.main()
