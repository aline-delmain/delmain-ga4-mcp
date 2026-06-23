---
name: delmain-ga4
description: Query Google Analytics 4 through the delmain-ga4 MCP server and turn the result into a clear, correct answer. Neutral, works for any team (SEO, content, paid, leadership). Use when the user asks about GA4, Google Analytics, website sessions, users, pageviews, bounce rate, traffic sources, channels, landing pages, UTM campaigns, conversions or key events, devices, geography, or realtime / active users. Also triggers when the user names a property and asks "how is the site doing", "where does traffic come from", or "what is converting".
---

# delmain-ga4

Answer Google Analytics 4 questions using the **delmain-ga4 MCP server**. This
skill is the playbook; the MCP is the data access. Keep it neutral: no
vertical-specific assumptions, benchmarks, or naming.

## Prerequisite

The `delmain-ga4` MCP must be connected (tools `list_properties`,
`get_property`, `run_report`, `run_realtime_report`). If the tools are missing,
tell the user to install it (see the delmain-ga4-mcp README) instead of guessing
numbers.

## Workflow

1. **Resolve the property.** If the user gave a numeric property ID, use it. If
   they named a site/brand instead, call `list_properties` and match by name,
   then confirm the ID you picked. Never invent a property ID.
2. **Pick dimensions + metrics** for the question (recipes below) and call
   `run_report` (or `run_realtime_report` for "right now").
3. **Present the answer**, not the raw JSON. State the property and the date
   range you used. Use plain language; a small table or bullets is fine.

## Tools

| Tool | Use for |
|---|---|
| `list_properties` | Discover which properties the user can read + their IDs |
| `get_property` | Name, time zone, currency of one property |
| `run_report` | Any historical report (dimensions + metrics + date range) |
| `run_realtime_report` | Active users / events in roughly the last 30 minutes |

Dates accept `YYYY-MM-DD` or relative values like `7daysAgo`, `28daysAgo`,
`yesterday`, `today`.

## Common recipes (neutral)

- **Overview:** dimensions `[]`, metrics `["sessions","totalUsers","newUsers","screenPageViews","bounceRate","averageSessionDuration","conversions"]`.
- **Where traffic comes from:** dimensions `["sessionDefaultChannelGroup"]` (or `["sessionSource","sessionMedium"]` for detail), metrics `["sessions","conversions"]`, `order_by_metric="sessions"`.
- **Top landing pages:** dimensions `["landingPage"]`, metrics `["sessions","bounceRate","conversions"]`, `order_by_metric="sessions"`, limit 10-20.
- **UTM campaigns:** dimensions `["sessionCampaignName","sessionSource","sessionMedium"]`, metrics `["sessions","conversions"]`.
- **Conversions by event:** dimensions `["eventName"]`, metrics `["conversions","eventCount","totalUsers"]`, `order_by_metric="conversions"`.
- **Devices:** dimensions `["deviceCategory"]`. **Geography:** `["country"]` or `["city"]`.
- **Daily trend:** dimensions `["date"]`, metrics you care about, start/end dates set.
- **Right now:** `run_realtime_report` with metrics `["activeUsers"]`, optional dimensions `["unifiedScreenName"]` or `["country"]`.

## Reading the numbers honestly

- **Always say the window and property.** "Last 30 days for property X" beats a
  bare number.
- **Channels:** when asked "where does traffic come from", break it down; do not
  answer from the totals row.
- **Event count vs users:** a single click event can fire many times per user,
  so `eventCount` can be much larger than the people behind it. When a count
  looks inflated, also report `totalUsers` for that event.
- **Attribution buckets:** rows like `(direct)/(none)`, `(not set)`, or
  `(data not available)` are normal. Call them out rather than folding them into
  a channel they don't belong to.
- **Bounce rate / engagement:** report them, but pair with context (a high
  bounce on direct traffic reads differently than on paid).
- **Realtime is approximate** (~last 30 min) and not comparable to historical
  reports.

## Rules

- **Read-only.** This never changes anything in GA4.
- **Never fabricate** property IDs, metrics, or numbers. If a tool errors (no
  access, property not found), report it plainly.
- **Don't dump JSON** at the user; summarize. Offer the raw rows only if asked.
