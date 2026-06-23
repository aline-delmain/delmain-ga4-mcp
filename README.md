# :Delmain GA4 MCP

A small [MCP](https://modelcontextprotocol.io) server that lets any MCP client
(Claude Desktop, Claude Code, Cursor, ...) query **Google Analytics 4**.

It is intentionally **neutral**: tools take a property ID plus free-form
dimensions and metrics, so it works for PPC, SEO, content, leadership, anyone.
Each person authenticates with **their own Google account** (per-user OAuth), so
everyone only sees the GA4 properties they already have access to.

## Tools

| Tool | What it does |
|---|---|
| `list_properties` | List every GA4 account + property your account can read |
| `get_property` | Metadata for one property (name, timezone, currency) |
| `run_report` | Report with any dimensions/metrics over a date range |
| `run_realtime_report` | Active users / events in the last ~30 minutes |

`run_report` is the workhorse. Example dimensions: `sessionSource`,
`sessionMedium`, `landingPage`, `date`, `country`, `deviceCategory`,
`eventName`. Example metrics: `sessions`, `totalUsers`, `newUsers`,
`screenPageViews`, `bounceRate`, `averageSessionDuration`, `conversions`,
`eventCount`.

---

## Installing with Claude Code

The fastest path. Open **Claude Code** (or the **Code** tab in the Claude Desktop
App) and paste:

> Install the MCP server from https://github.com/aline-delmain/delmain-ga4-mcp —
> `pip install` it and add it to my MCP config as "delmain-ga4".

Claude will clone the repo, install the package, and wire up your MCP client
config. Then **you** finish the two steps Claude can't do for you (by design,
since every person authenticates as themselves):

1. Paste the OAuth `client_id` / `client_secret` (from the team vault) into
   `~/.delmain-ga4-mcp/.env`.
2. Run `delmain-ga4-mcp-setup` and authorize in the browser with your own
   Google account.

Restart your MCP client and the GA4 tools show up.

> Note: a plain chat at claude.ai cannot install software, only **Claude Code**
> or the Desktop **Code** tab can. And the admin setup below must be done once
> first, otherwise authorization fails with `org_internal` / `SERVICE_DISABLED`.

---

## One-time setup by an admin (do this once for the whole team)

1. **OAuth client** — in the Google Cloud project that owns the ":Delmain GA4"
   app, create (or reuse) an OAuth client of type **Desktop app**. Note its
   client ID and client secret.
2. **Consent screen** — so teammates don't each need to be added as test users:
   - If everyone authorizes with an **@delmain.co** account, set the consent
     screen to **Internal** (org-only) and you're done.
   - If people will use other Google accounts, set it to **External** and
     **Publish** the app (status: *In production*). While in *Testing*, only
     listed test users can authorize.
3. **Enable APIs** in that project:
   - Google Analytics Data API (`analyticsdata.googleapis.com`)
   - Google Analytics Admin API (`analyticsadmin.googleapis.com`)
4. Put the client ID + secret in the **team vault** (1Password / Bitwarden).
   They are shared by everyone; only each person's refresh token is personal.

---

## Per-user install

### Quick install (one script)

There is a one-shot installer for each OS. It finds Python, installs the
package, registers the MCP with Claude Code using the full executable path (so a
missing PATH entry doesn't break it), writes your `.env`, and runs the browser
authorization.

**Windows** ([`install-delmain-ga4-mcp.ps1`](install-delmain-ga4-mcp.ps1)):

```powershell
powershell -ExecutionPolicy Bypass -File .\install-delmain-ga4-mcp.ps1
```

**macOS / Linux** ([`install-delmain-ga4-mcp.sh`](install-delmain-ga4-mcp.sh)):

```bash
bash install-delmain-ga4-mcp.sh
```

It will ask you to paste the OAuth `client_id` / `client_secret` from the team
vault. That's the only manual input. Then restart your MCP client.

> **Claude Desktop users:** the script auto-registers only with **Claude Code**
> (via the `claude` CLI). If you use the Desktop app, the script prints a
> `"mcpServers"` JSON block with the full executable path. Copy that block into
> your `claude_desktop_config.json` (Settings → Developer → Edit Config), then
> restart the app. Same block works for Cursor's `~/.cursor/mcp.json`.

### Manual install

Requires Python 3.10+.

```bash
# 1. Install (from the repo, or once published, from GitHub)
pip install git+https://github.com/<org>/delmain-ga4-mcp.git
#   or, working in a clone:
pip install -e .

# 2. Configure credentials
mkdir -p ~/.delmain-ga4-mcp
cp .env.example ~/.delmain-ga4-mcp/.env
#   edit it and paste DELMAIN_GA4_CLIENT_ID + DELMAIN_GA4_CLIENT_SECRET
#   (from the team vault). Leave the refresh token blank.

# 3. Generate YOUR personal refresh token (opens the browser)
delmain-ga4-mcp-setup
#   sign in with the Google account that has your GA4 access, then authorize.
```

That writes your refresh token to `~/.delmain-ga4-mcp/.env`. Done.

---

## Connect it to your MCP client

The server runs over **stdio** via the `delmain-ga4-mcp` command.

### Claude Desktop / Claude Code

Add to your MCP config (`claude_desktop_config.json`, or `.mcp.json` /
`~/.claude.json` for Claude Code):

```json
{
  "mcpServers": {
    "delmain-ga4": {
      "command": "delmain-ga4-mcp"
    }
  }
}
```

### Cursor

`~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "delmain-ga4": { "command": "delmain-ga4-mcp" }
  }
}
```

Restart the client. You should see the GA4 tools available.

---

## Example prompts

- "List my GA4 properties."
- "For property 463688888, sessions and conversions by sessionSource/sessionMedium, last 30 days."
- "Top 10 landing pages by sessions for property 463688888 this month."
- "How many active users are on property 463688888 right now?"

---

## Optional: the `delmain-ga4` skill (Claude only)

The MCP gives you the raw GA4 access. The optional **skill** in
[`skills/delmain-ga4/`](skills/delmain-ga4/) adds a neutral playbook on top: how
to resolve a property, which dimensions/metrics to use for common questions, and
how to read the numbers honestly (event-count inflation, attribution buckets,
realtime caveats). It works in Claude Code and the Claude Desktop app (not
Cursor, which has no skills).

To install it, copy the folder into your skills directory:

```bash
# global (all projects)
cp -r skills/delmain-ga4 ~/.claude/skills/
```

```powershell
# Windows
Copy-Item -Recurse skills\delmain-ga4 "$env:USERPROFILE\.claude\skills\"
```

It needs the MCP connected to do anything; it calls the same tools.

---

## Notes

- **Read-only.** The server only requests `analytics.readonly`; it cannot
  change anything in GA4.
- **No secrets in git.** `.env`, `*.json` credentials are gitignored. Share the
  OAuth client via the vault, never by committing it.
- **Access scope.** You can only query properties your own Google account can
  see. `list_properties` shows exactly that set.
