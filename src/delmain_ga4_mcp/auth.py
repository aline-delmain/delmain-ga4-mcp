"""Authentication and client construction for the GA4 APIs.

Per-user OAuth: every teammate generates their own refresh token (via the
`delmain-ga4-mcp-setup` command) using the shared ":Delmain GA4" OAuth client.
The token grants read-only Analytics access scoped to whatever GA4 properties
that person's Google account can already see.
"""

from __future__ import annotations

import os
from pathlib import Path

SCOPE = "https://www.googleapis.com/auth/analytics.readonly"

CONFIG_DIR = Path(os.path.expanduser("~/.delmain-ga4-mcp"))
# Search order for the .env: project-local first, then the per-user config dir.
_ENV_PATHS = [
    Path.cwd() / ".env",
    CONFIG_DIR / ".env",
]


def load_env() -> None:
    """Load KEY=VALUE pairs from the first .env found, without overriding
    variables already present in the real environment."""
    for env_path in _ENV_PATHS:
        if env_path.is_file():
            _parse_env(env_path)
            return


def _parse_env(env_path: Path) -> None:
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:]
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value and not os.environ.get(key):
            os.environ[key] = value


def get_oauth_config() -> tuple[str, str, str]:
    """Return (client_id, client_secret, refresh_token) from the environment."""
    load_env()
    return (
        os.environ.get("DELMAIN_GA4_CLIENT_ID", "").strip(),
        os.environ.get("DELMAIN_GA4_CLIENT_SECRET", "").strip(),
        os.environ.get("DELMAIN_GA4_REFRESH_TOKEN", "").strip(),
    )


def build_credentials():
    """Build OAuth2 credentials from the configured refresh token."""
    from google.oauth2.credentials import Credentials

    client_id, client_secret, refresh_token = get_oauth_config()
    missing = [
        name
        for name, val in (
            ("DELMAIN_GA4_CLIENT_ID", client_id),
            ("DELMAIN_GA4_CLIENT_SECRET", client_secret),
            ("DELMAIN_GA4_REFRESH_TOKEN", refresh_token),
        )
        if not val
    ]
    if missing:
        raise RuntimeError(
            "Missing credentials: "
            + ", ".join(missing)
            + ". Fill the .env and run `delmain-ga4-mcp-setup` to generate the "
            "refresh token."
        )

    return Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=[SCOPE],
    )


_data_client = None
_admin_client = None


def data_client():
    """Lazily build and cache the GA4 Data API client."""
    global _data_client
    if _data_client is None:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient

        _data_client = BetaAnalyticsDataClient(credentials=build_credentials())
    return _data_client


def admin_client():
    """Lazily build and cache the GA4 Admin API client."""
    global _admin_client
    if _admin_client is None:
        from google.analytics.admin_v1beta import AnalyticsAdminServiceClient

        _admin_client = AnalyticsAdminServiceClient(credentials=build_credentials())
    return _admin_client


def default_property_id() -> str | None:
    load_env()
    pid = os.environ.get("DELMAIN_GA4_PROPERTY_ID", "").strip()
    return pid.replace("properties/", "") if pid else None
