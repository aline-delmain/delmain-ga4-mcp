"""delmain-ga4-mcp — FastMCP server exposing neutral GA4 tools over stdio."""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from . import ga4

mcp = FastMCP("delmain-ga4")


def _json(obj) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, default=str)


@mcp.tool()
def list_properties() -> str:
    """List every GA4 account and property the authenticated user can read.

    Use this first to discover property IDs. Returns account name, property
    name, and the numeric property_id needed by every other tool.
    """
    return _json(ga4.list_properties())


@mcp.tool()
def get_property(property_id: str = "") -> str:
    """Get metadata for one GA4 property: display name, time zone, currency.

    property_id: numeric GA4 property ID (e.g. "463688888"). If omitted, uses
    DELMAIN_GA4_PROPERTY_ID from the environment when set.
    """
    return _json(ga4.get_property(property_id or None))


@mcp.tool()
def run_report(
    property_id: str = "",
    dimensions: list[str] | None = None,
    metrics: list[str] | None = None,
    start_date: str = "30daysAgo",
    end_date: str = "today",
    limit: int = 50,
    order_by_metric: str = "",
    order_desc: bool = True,
) -> str:
    """Run a GA4 report with arbitrary dimensions and metrics.

    property_id: numeric GA4 property ID. Call list_properties() to find it.
    dimensions: GA4 dimension API names, e.g. ["sessionSource", "sessionMedium"],
        ["landingPage"], ["date"], ["country"], ["deviceCategory"], ["eventName"].
        Pass [] for a single totals row.
    metrics: GA4 metric API names, e.g. ["sessions", "totalUsers", "newUsers",
        "screenPageViews", "bounceRate", "averageSessionDuration", "conversions",
        "eventCount"]. Defaults to ["sessions"].
    start_date / end_date: either "YYYY-MM-DD" or relative like "7daysAgo",
        "28daysAgo", "today", "yesterday".
    limit: max rows (default 50).
    order_by_metric: metric name to sort by (e.g. "sessions"). Empty = API default.
    order_desc: sort descending when order_by_metric is set.
    """
    return _json(
        ga4.run_report(
            property_id=property_id or None,
            dimensions=dimensions,
            metrics=metrics,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            order_by_metric=order_by_metric or None,
            order_desc=order_desc,
        )
    )


@mcp.tool()
def run_realtime_report(
    property_id: str = "",
    dimensions: list[str] | None = None,
    metrics: list[str] | None = None,
    limit: int = 50,
) -> str:
    """Run a GA4 realtime report (active users in roughly the last 30 minutes).

    property_id: numeric GA4 property ID.
    dimensions: e.g. ["unifiedScreenName"], ["country"], ["deviceCategory"].
    metrics: e.g. ["activeUsers"], ["screenPageViews"]. Defaults to ["activeUsers"].
    """
    return _json(
        ga4.run_realtime_report(
            property_id=property_id or None,
            dimensions=dimensions,
            metrics=metrics,
            limit=limit,
        )
    )


def main() -> None:
    """Console entry point: run the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
