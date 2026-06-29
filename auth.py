"""
Zoho MCP OAuth2 PKCE flow with dynamic client registration.
No hardcoded credentials — the MCP URL is the only thing needed.
Tokens are saved locally in tokens.json (gitignored).
"""

import base64
import hashlib
import http.server
import json
from typing import Optional, Tuple
import os
import secrets
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

TOKENS_FILE = Path(__file__).parent / "tokens.json"
DISCOVERY_SUFFIX = "/.well-known/oauth-authorization-server"


def _base_url(mcp_url: str) -> str:
    parsed = urllib.parse.urlparse(mcp_url)
    return f"{parsed.scheme}://{parsed.netloc}"


def discover(mcp_url: str) -> dict:
    url = _base_url(mcp_url) + DISCOVERY_SUFFIX
    with urllib.request.urlopen(url) as r:
        return json.loads(r.read())


def dynamic_register(registration_endpoint: str, redirect_uri: str) -> dict:
    payload = json.dumps({
        "client_name": "Growisto Timesheet EBR Skill",
        "redirect_uris": [redirect_uri],
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
    }).encode()
    req = urllib.request.Request(
        registration_endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def _pkce_pair() -> Tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def _wait_for_code(port: int, timeout: int = 120) -> str:
    code_holder = []
    done = threading.Event()

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if "code" in qs:
                code_holder.append(qs["code"][0])
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h2>Authenticated! You can close this tab.</h2>")
            done.set()

        def log_message(self, *args):
            pass  # suppress server logs

    server = http.server.HTTPServer(("localhost", port), Handler)
    t = threading.Thread(target=server.serve_forever)
    t.daemon = True
    t.start()
    done.wait(timeout=timeout)
    server.shutdown()

    if not code_holder:
        raise TimeoutError("OAuth callback not received within timeout")
    return code_holder[0]


def _exchange_code(token_endpoint: str, client_id: str, code: str, redirect_uri: str, verifier: str) -> dict:
    data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "client_id": client_id,
        "code": code,
        "redirect_uri": redirect_uri,
        "code_verifier": verifier,
    }).encode()
    req = urllib.request.Request(token_endpoint, data=data, method="POST")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def _refresh(token_endpoint: str, client_id: str, refresh_token: str) -> dict:
    data = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "client_id": client_id,
        "refresh_token": refresh_token,
    }).encode()
    req = urllib.request.Request(token_endpoint, data=data, method="POST")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def load_tokens() -> Optional[dict]:
    if TOKENS_FILE.exists():
        return json.loads(TOKENS_FILE.read_text())
    return None


def save_tokens(tokens: dict):
    TOKENS_FILE.write_text(json.dumps(tokens, indent=2))


def get_access_token(mcp_url: str, port: int = 8765) -> str:
    meta = discover(mcp_url)
    auth_ep = meta["authorization_endpoint"]
    token_ep = meta["token_endpoint"]
    reg_ep = meta.get("registration_endpoint")
    redirect_uri = f"http://localhost:{port}/callback"

    tokens = load_tokens()

    # Try refresh first
    if tokens and tokens.get("refresh_token") and tokens.get("client_id"):
        try:
            refreshed = _refresh(token_ep, tokens["client_id"], tokens["refresh_token"])
        except Exception:
            refreshed = {}
        if refreshed.get("access_token"):
            tokens.update(refreshed)
            tokens["expires_at"] = time.time() + refreshed.get("expires_in", 3600)
            try:
                save_tokens(tokens)
            except Exception:
                pass  # non-fatal if file is not writable
            return tokens["access_token"]

    # Full OAuth flow
    if not reg_ep:
        raise RuntimeError("MCP server does not support dynamic client registration")

    print("Registering OAuth client with Zoho MCP...")
    client_info = dynamic_register(reg_ep, redirect_uri)
    client_id = client_info["client_id"]

    verifier, challenge = _pkce_pair()
    params = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "scope": "ZohoProjects.timesheets.READ ZohoProjects.projects.READ ZohoProjects.portals.READ ZohoMCP.tool.execute",
    })
    auth_url = f"{auth_ep}?{params}"

    print(f"\nOpening browser for Zoho login...")
    print(f"If browser does not open, visit:\n  {auth_url}\n")
    webbrowser.open(auth_url)

    print(f"Waiting for callback on http://localhost:{port}/callback ...")
    code = _wait_for_code(port)

    print("Exchanging code for tokens...")
    token_data = _exchange_code(token_ep, client_id, code, redirect_uri, verifier)

    if not token_data.get("access_token"):
        raise RuntimeError(f"Token exchange failed: {token_data}")

    token_data["client_id"] = client_id
    token_data["expires_at"] = time.time() + token_data.get("expires_in", 3600)
    save_tokens(token_data)
    print("Authenticated and tokens saved.\n")
    return token_data["access_token"]
