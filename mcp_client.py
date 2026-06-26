"""
Minimal MCP HTTP client — calls tools on a Zoho MCP server.
Handles JSON-RPC 2.0 over HTTP with Bearer token auth.
"""

import json
import urllib.request
import urllib.error


class MCPClient:
    def __init__(self, mcp_url: str, access_token: str):
        self.url = mcp_url
        self.token = access_token
        self._session_id = None
        self._msg_id = 0

    def _next_id(self) -> int:
        self._msg_id += 1
        return self._msg_id

    def _post(self, payload: dict) -> dict:
        body = json.dumps(payload).encode()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
        }
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id

        req = urllib.request.Request(self.url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req) as r:
                if "Mcp-Session-Id" in r.headers:
                    self._session_id = r.headers["Mcp-Session-Id"]
                raw = r.read()
                if not raw.strip():
                    return {}
                # Handle SSE response (text/event-stream)
                ct = r.headers.get("Content-Type", "")
                if "event-stream" in ct:
                    return self._parse_sse(raw)
                return json.loads(raw)
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            raise RuntimeError(f"MCP HTTP {e.code}: {body}")

    def _parse_sse(self, raw: bytes) -> dict:
        for line in raw.decode().splitlines():
            if line.startswith("data:"):
                data = line[5:].strip()
                if data and data != "[DONE]":
                    try:
                        return json.loads(data)
                    except Exception:
                        pass
        return {}

    def initialize(self):
        resp = self._post({
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "growisto-ebr-skill", "version": "1.0"},
            },
            "id": self._next_id(),
        })
        # Send initialized notification
        self._post({
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        })
        return resp

    def list_tools(self) -> list:
        resp = self._post({
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": self._next_id(),
        })
        return resp.get("result", {}).get("tools", [])

    def call_tool(self, tool_name: str, arguments: dict) -> dict:
        resp = self._post({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
            "id": self._next_id(),
        })
        if "error" in resp:
            raise RuntimeError(f"MCP tool error: {resp['error']}")
        return resp.get("result", {})
