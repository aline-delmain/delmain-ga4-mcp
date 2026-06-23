#!/usr/bin/env bash
# One-shot installer for the :Delmain GA4 MCP server (macOS / Linux).
#
# Run:  bash install-delmain-ga4-mcp.sh
#
# Finds Python 3, installs the package from GitHub, registers the MCP server
# with Claude Code using the full executable path (so a missing PATH entry
# doesn't break it), prepares ~/.delmain-ga4-mcp/.env, and runs the browser
# authorization. Set SKIP_SETUP=1 to skip the OAuth step.

set -euo pipefail

REPO="${REPO:-https://github.com/aline-delmain/delmain-ga4-mcp.git}"
SKIP_SETUP="${SKIP_SETUP:-0}"

step() { printf "\n==> %s\n" "$1"; }
ok()   { printf "    %s\n" "$1"; }
note() { printf "    %s\n" "$1"; }

# --- 1. Find Python 3 -------------------------------------------------------
step "Looking for Python 3..."
PY=""
for c in python3 python; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info[0] == 3 else 1)' 2>/dev/null; then
        PY="$c"; break
    fi
done
if [ -z "$PY" ]; then
    echo "Python 3 not found. Install it (e.g. 'brew install python') and re-run." >&2
    exit 1
fi
ok "Using: $PY ($("$PY" --version 2>&1))"

# --- 2. Install the package -------------------------------------------------
step "Installing delmain-ga4-mcp from GitHub..."
"$PY" -m pip install --upgrade "git+$REPO"
ok "Package installed."

# --- 3. Locate the executable ----------------------------------------------
step "Locating the installed executable..."
SERVER=""
if command -v delmain-ga4-mcp >/dev/null 2>&1; then
    SERVER="$(command -v delmain-ga4-mcp)"
else
    DIRS="$("$PY" -c 'import sysconfig,site,os;print(sysconfig.get_path("scripts"));print(os.path.join(site.getuserbase(),"bin"))')"
    while IFS= read -r d; do
        [ -n "$d" ] || continue
        if [ -x "$d/delmain-ga4-mcp" ]; then SERVER="$d/delmain-ga4-mcp"; break; fi
    done <<EOF
$DIRS
EOF
fi
if [ -z "$SERVER" ]; then
    echo "Could not find delmain-ga4-mcp after install." >&2
    exit 1
fi
ok "Found: $SERVER"

# --- 4. Register with Claude Code ------------------------------------------
step "Registering the MCP server with Claude Code..."
REGISTERED=0
if command -v claude >/dev/null 2>&1; then
    claude mcp remove delmain-ga4 --scope user >/dev/null 2>&1 || true
    if claude mcp add delmain-ga4 --scope user -- "$SERVER"; then
        ok "Registered as 'delmain-ga4' (user scope)."; REGISTERED=1
    fi
fi
if [ "$REGISTERED" -eq 0 ]; then
    note "Couldn't auto-register (no 'claude' CLI, or you use Claude Desktop)."
    note "Add this to your MCP client config manually:"
    printf '\n      "mcpServers": {\n        "delmain-ga4": { "command": "%s" }\n      }\n\n' "$SERVER"
fi

# --- 5. Prepare the per-user .env ------------------------------------------
step "Preparing your credentials file..."
CFG="$HOME/.delmain-ga4-mcp"; mkdir -p "$CFG"; ENVF="$CFG/.env"
get_val() { grep -E "^$1=" "$ENVF" 2>/dev/null | head -1 | sed -E "s/^$1=\"?//; s/\"?$//"; }
CID=""; CSEC=""; RTOK=""
if [ -f "$ENVF" ]; then CID="$(get_val DELMAIN_GA4_CLIENT_ID)"; CSEC="$(get_val DELMAIN_GA4_CLIENT_SECRET)"; RTOK="$(get_val DELMAIN_GA4_REFRESH_TOKEN)"; fi
if [ -z "$CID" ]; then read -r -p "Paste DELMAIN_GA4_CLIENT_ID (from the team vault): " CID; else ok "DELMAIN_GA4_CLIENT_ID already set."; fi
if [ -z "$CSEC" ]; then read -r -p "Paste DELMAIN_GA4_CLIENT_SECRET (from the team vault): " CSEC; else ok "DELMAIN_GA4_CLIENT_SECRET already set."; fi
cat > "$ENVF" <<EOF
DELMAIN_GA4_CLIENT_ID="$CID"
DELMAIN_GA4_CLIENT_SECRET="$CSEC"
DELMAIN_GA4_REFRESH_TOKEN="$RTOK"
EOF
ok "Wrote $ENVF"

# --- 6. Authorize with Google ----------------------------------------------
if [ "$SKIP_SETUP" = "1" ]; then
    note "Skipping OAuth (SKIP_SETUP=1). Run 'delmain-ga4-mcp-setup' later to authorize."
elif [ -n "$RTOK" ]; then
    ok "Refresh token already present, skipping OAuth."
else
    step "Authorizing with Google (opens your browser)..."
    SETUP="$(dirname "$SERVER")/delmain-ga4-mcp-setup"
    if [ -x "$SETUP" ]; then "$SETUP"; else "$PY" -m delmain_ga4_mcp.setup_cli; fi
fi

step "Done."
ok "Restart your MCP client (Claude Code / Desktop / Cursor) to load the GA4 tools."
