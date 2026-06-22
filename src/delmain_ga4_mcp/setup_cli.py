"""`delmain-ga4-mcp-setup` — generate this user's personal GA4 refresh token.

Runs the OAuth2 installed-app flow in the browser and writes the refresh token
to ~/.delmain-ga4-mcp/.env. The client_id/client_secret come from the .env
(shared via the team vault); only the resulting refresh token is personal.
"""

from __future__ import annotations

import hashlib
import os
import re
import socket
import sys
import webbrowser
from pathlib import Path
from urllib.parse import unquote

from . import auth

SERVER = "127.0.0.1"


def _find_free_port(start: int = 8080, end: int = 8090) -> int | None:
    for port in range(start, end + 1):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind((SERVER, port))
            s.close()
            return port
        except OSError:
            continue
    return None


def _save_refresh_token(token: str) -> Path:
    auth.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    env_path = auth.CONFIG_DIR / ".env"

    client_id, client_secret, _ = auth.get_oauth_config()
    lines = {
        "DELMAIN_GA4_CLIENT_ID": client_id,
        "DELMAIN_GA4_CLIENT_SECRET": client_secret,
        "DELMAIN_GA4_REFRESH_TOKEN": token,
    }

    existing = env_path.read_text(encoding="utf-8") if env_path.is_file() else ""
    content = existing
    for key, value in lines.items():
        if not value:
            continue
        pattern = rf"^#?\s*{key}=.*$"
        new_line = f'{key}="{value}"'
        if re.search(pattern, content, flags=re.MULTILINE):
            content = re.sub(pattern, new_line, content, flags=re.MULTILINE)
        else:
            content = content.rstrip("\n") + f"\n{new_line}\n"

    env_path.write_text(content.lstrip("\n"), encoding="utf-8")
    return env_path


def run_oauth() -> str:
    try:
        from google_auth_oauthlib.flow import Flow
    except ImportError:
        sys.exit("ERROR: google-auth-oauthlib not installed.")

    client_id, client_secret, _ = auth.get_oauth_config()
    if not client_id or not client_secret:
        sys.exit(
            "ERROR: DELMAIN_GA4_CLIENT_ID and DELMAIN_GA4_CLIENT_SECRET must be set "
            "in your .env (get them from the team vault)."
        )

    port = _find_free_port()
    if not port:
        sys.exit("ERROR: no free port between 8080-8090.")
    redirect_uri = f"http://{SERVER}:{port}"

    flow = Flow.from_client_config(
        {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=[auth.SCOPE],
    )
    flow.redirect_uri = redirect_uri

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        state=hashlib.sha256(os.urandom(1024)).hexdigest(),
        prompt="consent",
        include_granted_scopes="false",
    )

    print("\n" + "=" * 60)
    print("  :Delmain GA4 — authorize with YOUR Google account")
    print("=" * 60)
    print("\nOpen this URL (it should open automatically):\n")
    print(f"  {auth_url}\n")
    print(f"Waiting for the callback on {redirect_uri} ...\n")
    webbrowser.open(auth_url)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((SERVER, port))
    sock.listen(1)
    connection, _ = sock.accept()
    data = connection.recv(4096).decode("utf-8")

    match = re.search(r"GET\s/\?(.*?)\s", data)
    params = {}
    if match:
        for pair in match.group(1).split("&"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                params[k] = unquote(v)

    html = (
        "<html><body style='font-family:sans-serif;text-align:center;margin-top:15%'>"
        "<h1 style='color:#4CAF50'>Done!</h1><p>GA4 authorized. You can close this tab.</p>"
        "</body></html>"
    )
    connection.sendall(
        f"HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n\r\n{html}".encode()
    )
    connection.close()
    sock.close()

    if "error" in params or "code" not in params:
        sys.exit(f"ERROR from Google: {params.get('error', 'no authorization code')}")

    flow.fetch_token(code=params["code"])
    refresh_token = flow.credentials.refresh_token
    if not refresh_token:
        sys.exit(
            "ERROR: no refresh token returned. Revoke the app at "
            "https://myaccount.google.com/permissions and retry."
        )
    return refresh_token


def main() -> None:
    token = run_oauth()
    env_path = _save_refresh_token(token)
    print(f"\nSaved refresh token to {env_path}")
    print("You're set. Add the server to your MCP client (see README).")


if __name__ == "__main__":
    main()
