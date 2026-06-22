"""Thin, neutral helpers over the GA4 Data + Admin APIs.

Nothing here is team- or vertical-specific: tools take a property ID plus
free-form dimensions/metrics, so the same server serves PPC, SEO, content,
or anyone else.
"""

from __future__ import annotations

from . import auth


def _resolve(property_id: str | None) -> str:
    pid = property_id or auth.default_property_id()
    if not pid:
        raise ValueError(
            "No property_id given and DELMAIN_GA4_PROPERTY_ID is not set. "
            "Call list_properties() to discover available property IDs."
        )
    return str(pid).replace("properties/", "")


def _format_report(response) -> dict:
    dim_headers = [h.name for h in response.dimension_headers]
    met_headers = [h.name for h in response.metric_headers]
    rows = []
    for row in response.rows:
        r = {}
        for i, dim in enumerate(row.dimension_values):
            r[dim_headers[i]] = dim.value
        for i, met in enumerate(row.metric_values):
            r[met_headers[i]] = met.value
        rows.append(r)
    return {
        "dimensions": dim_headers,
        "metrics": met_headers,
        "row_count": getattr(response, "row_count", len(rows)),
        "rows": rows,
    }


def list_properties() -> dict:
    """List every GA4 account + property the authenticated user can read."""
    client = auth.admin_client()
    out = []
    for account in client.list_account_summaries():
        for prop in account.property_summaries:
            out.append(
                {
                    "account": account.display_name,
                    "property_name": prop.display_name,
                    "property_id": prop.property.replace("properties/", ""),
                }
            )
    return {"properties": out, "total": len(out)}


def get_property(property_id: str | None = None) -> dict:
    """Return metadata for a property (name, timezone, currency)."""
    from google.analytics.admin_v1beta import AnalyticsAdminServiceClient  # noqa: F401

    pid = _resolve(property_id)
    prop = auth.admin_client().get_property(name=f"properties/{pid}")
    return {
        "property_id": pid,
        "display_name": prop.display_name,
        "time_zone": prop.time_zone,
        "currency_code": prop.currency_code,
        "create_time": str(prop.create_time),
    }


def run_report(
    property_id: str | None = None,
    dimensions: list[str] | None = None,
    metrics: list[str] | None = None,
    start_date: str = "30daysAgo",
    end_date: str = "today",
    limit: int = 50,
    order_by_metric: str | None = None,
    order_desc: bool = True,
) -> dict:
    """Run a GA4 report with arbitrary dimensions and metrics."""
    from google.analytics.data_v1beta.types import (
        DateRange,
        Dimension,
        Metric,
        OrderBy,
        RunReportRequest,
    )

    pid = _resolve(property_id)
    metrics = metrics or ["sessions"]
    dimensions = dimensions or []

    order_bys = []
    if order_by_metric:
        order_bys = [
            OrderBy(
                metric=OrderBy.MetricOrderBy(metric_name=order_by_metric),
                desc=order_desc,
            )
        ]

    request = RunReportRequest(
        property=f"properties/{pid}",
        dimensions=[Dimension(name=d) for d in dimensions],
        metrics=[Metric(name=m) for m in metrics],
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        limit=limit,
        order_bys=order_bys,
    )
    return _format_report(auth.data_client().run_report(request))


def run_realtime_report(
    property_id: str | None = None,
    dimensions: list[str] | None = None,
    metrics: list[str] | None = None,
    limit: int = 50,
) -> dict:
    """Run a GA4 realtime report (last ~30 minutes)."""
    from google.analytics.data_v1beta.types import (
        Dimension,
        Metric,
        RunRealtimeReportRequest,
    )

    pid = _resolve(property_id)
    metrics = metrics or ["activeUsers"]
    dimensions = dimensions or []

    request = RunRealtimeReportRequest(
        property=f"properties/{pid}",
        dimensions=[Dimension(name=d) for d in dimensions],
        metrics=[Metric(name=m) for m in metrics],
        limit=limit,
    )
    return _format_report(auth.data_client().run_realtime_report(request))
