from __future__ import annotations

import html
import io
import logging
import re
from uuid import uuid4

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import StrategicChatRequestSerializer

logger = logging.getLogger(__name__)


#  helpers 

def _error_payload(*, code: str, message: str, details=None, trace_id: str | None = None):
    payload = {"error": {"code": code, "message": message}}
    if details is not None:
        payload["error"]["details"] = details
    if trace_id:
        payload["error"]["trace_id"] = trace_id
    return payload


def _ensure_html(value) -> str:
    text = str(value) if not isinstance(value, str) else value
    text = text.strip()
    if not text:
        return "<div>No analysis returned.</div>"
    if "<" in text and ">" in text:
        return text
    return f'<div><pre style="white-space:pre-wrap">{html.escape(text)}</pre></div>'


def _dedupe_preserve_order(values: list) -> list:
    """Remove duplicate entries while preserving order (case-insensitive, trims punctuation)."""
    if not isinstance(values, list):
        return values
    seen = set()
    out = []
    for v in values:
        s = str(v).strip()
        s = s.rstrip(".,;:")
        key = s.lower()
        if not key:
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out


#  param parsing 

def _coerce(value: str):
    raw = value.strip().rstrip(".,;")
    if not raw:
        return ""
    num = re.sub(r"[$,%]", "", raw).replace(",", "")
    try:
        if re.fullmatch(r"-?\d+", num):
            return int(num)
        if re.fullmatch(r"-?\d*\.\d+", num):
            return float(num)
    except Exception:
        pass
    return raw


def _parse_kv(text: str) -> dict:
    params: dict = {}
    for m in re.finditer(
        r"(?P<key>[A-Za-z_][A-Za-z0-9_ ]*?)\s*:\s*(?P<value>[^,\n]+)",
        text,
    ):
        key = re.sub(r"\s+", "_", m.group("key").strip().lower()).strip("_")
        if key:
            params[key] = _coerce(m.group("value"))

    for m in re.finditer(
        r"\b(?P<key>[a-z_][a-z0-9_]{2,})\s+(?P<value>[$]?\d+(?:[.,]\d+)?%?)\b",
        text,
        re.IGNORECASE,
    ):
        key = m.group("key").lower()
        if key not in params:
            params[key] = _coerce(m.group("value"))

    return params


def _detect_subtask(message: str, params: dict) -> str:
    msg = message.lower()

    # SWOT detection
    if any(w in msg for w in ["swot", "strength", "weakness", "weaknesses", "opportunities", "threats"]):
        return "swot"

    # Business Goals detection
    if any(w in msg for w in ["business goals", "business goal", "revenue target", "budget total", "marketing spend"]):
        return "business_goals"
    if any(k in params for k in ["revenue_target", "budget_total", "marketing_spend", "timeline"]):
        return "business_goals"

    # Growth Strategy detection
    if any(w in msg for w in ["growth strategy", "market size", "market share", "competition level", "investment budget", "competitive"]):
        return "growth_strategy"
    if any(k in params for k in ["market_size", "market_share", "competition_level", "investment_budget", "competitive_advantage"]):
        return "growth_strategy"

    return "swot"


def _p(val, default=0.0) -> float:
    try:
        return float(val) if val is not None else default
    except Exception:
        return default


#  SWOT helper 

def _parse_swot_sections(text: str) -> dict:
    """Extract Strengths / Weaknesses / Opportunities / Threats from free text."""
    sections: dict = {"strengths": [], "weaknesses": [], "opportunities": [], "threats": []}
    parts = re.split(r"[;\n]+", text)
    for p in parts:
        p = p.strip()
        if not p:
            continue
        m = re.match(r"^(strengths?)[:\s]*(.*)", p, re.IGNORECASE)
        if m:
            sections["strengths"].extend([i.strip() for i in re.split(r",\s*", m.group(2)) if i.strip()])
            continue
        m = re.match(r"^(weaknesses?)[:\s]*(.*)", p, re.IGNORECASE)
        if m:
            sections["weaknesses"].extend([i.strip() for i in re.split(r",\s*", m.group(2)) if i.strip()])
            continue
        m = re.match(r"^(opportunities?)[:\s]*(.*)", p, re.IGNORECASE)
        if m:
            sections["opportunities"].extend([i.strip() for i in re.split(r",\s*", m.group(2)) if i.strip()])
            continue
        m = re.match(r"^(threats?)[:\s]*(.*)", p, re.IGNORECASE)
        if m:
            sections["threats"].extend([i.strip() for i in re.split(r",\s*", m.group(2)) if i.strip()])
            continue

    for k in ("strengths", "weaknesses", "opportunities", "threats"):
        sections[k] = _dedupe_preserve_order(sections.get(k, []))
    return sections


def _generate_swot_html(message: str) -> str:
    """Parse SWOT input and produce a formatted HTML report."""
    sw = _parse_swot_sections(message)

    recs = []
    for s in sw.get("strengths", []):
        recs.append(f"Leverage strength: {s} — build one offer, message, or program that amplifies this advantage.")
    for w in sw.get("weaknesses", []):
        recs.append(f"Address weakness: {w} — prioritize a 30-day quick win via process, training, or scheduling changes.")
    for o in sw.get("opportunities", []):
        recs.append(f"Pursue opportunity: {o} — run a 30–90 day pilot and define success metrics (traffic, conversion, margin).")
    for t in sw.get("threats", []):
        recs.append(f"Mitigate threat: {t} — set a monitoring trigger (weekly/monthly) and a specific contingency action.")
    if not recs:
        recs.append("No recommendations generated — please provide at least one SWOT item.")

    recs = _dedupe_preserve_order(recs)

    try:
        from backend.consulting_services.kpi.kpi_utils import format_business_report
        additional = {
            "Strengths": {str(i + 1): v for i, v in enumerate(sw["strengths"])},
            "Weaknesses": {str(i + 1): v for i, v in enumerate(sw["weaknesses"])},
            "Opportunities": {str(i + 1): v for i, v in enumerate(sw["opportunities"])},
            "Threats": {str(i + 1): v for i, v in enumerate(sw["threats"])},
        }
        metrics = {
            "Strengths Count": len(sw["strengths"]),
            "Weaknesses Count": len(sw["weaknesses"]),
            "Opportunities Count": len(sw["opportunities"]),
            "Threats Count": len(sw["threats"]),
        }
        performance = {
            "rating": "Good" if (sw["strengths"] and sw["opportunities"]) else "Acceptable"
        }
        report = format_business_report(
            "SWOT Analysis", metrics, performance, recs, benchmarks=None, additional_data=additional
        )
        return _ensure_html(
            report.get("business_report_html") or report.get("business_report") or "SWOT analysis generated."
        )
    except Exception as exc:
        logger.warning("SWOT format_business_report fallback: %s", exc)
        return _build_swot_fallback_html(sw, recs)


def _build_swot_fallback_html(sw: dict, recs: list) -> str:
    """Minimal fallback SWOT HTML if the backend utility is unavailable."""
    def _list_items(items):
        if not items:
            return "<li>None provided</li>"
        return "".join(f"<li>{html.escape(i)}</li>" for i in items)

    recs_html = "".join(f"<li>{html.escape(r)}</li>" for r in recs)
    return f"""
<div class="report">
  <div class="report__header">
    <h2>SWOT Analysis</h2>
  </div>
  <div class="report__body">
    <div class="metrics-grid">
      <div class="metric-card">
        <span class="metric-label">Strengths</span>
        <span class="metric-value">{len(sw["strengths"])}</span>
      </div>
      <div class="metric-card">
        <span class="metric-label">Weaknesses</span>
        <span class="metric-value">{len(sw["weaknesses"])}</span>
      </div>
      <div class="metric-card">
        <span class="metric-label">Opportunities</span>
        <span class="metric-value">{len(sw["opportunities"])}</span>
      </div>
      <div class="metric-card">
        <span class="metric-label">Threats</span>
        <span class="metric-value">{len(sw["threats"])}</span>
      </div>
    </div>
    <div class="section">
      <div class="section-title">SWOT Breakdown</div>
      <table>
        <tr><th>Strengths</th><th>Weaknesses</th></tr>
        <tr>
          <td><ul>{_list_items(sw["strengths"])}</ul></td>
          <td><ul>{_list_items(sw["weaknesses"])}</ul></td>
        </tr>
        <tr><th>Opportunities</th><th>Threats</th></tr>
        <tr>
          <td><ul>{_list_items(sw["opportunities"])}</ul></td>
          <td><ul>{_list_items(sw["threats"])}</ul></td>
        </tr>
      </table>
    </div>
    <div class="section">
      <div class="section-title">Strategic Recommendations</div>
      <ul>{recs_html}</ul>
    </div>
  </div>
</div>
""".strip()


#  Business Goals helper 

def _generate_business_goals_html(params: dict) -> str:
    """Compute business goal metrics and produce an HTML report."""
    revenue_target = _p(params.get("revenue_target"))
    budget_total = _p(params.get("budget_total"))
    marketing_spend = _p(params.get("marketing_spend") or params.get("marketing"))
    target_roi = _p(params.get("target_roi") or params.get("roi_target") or params.get("roi"), 20.0) or 20.0
    timeline_months = int(_p(params.get("timeline") or params.get("timeline_months") or params.get("months"), 12) or 12)
    acquisition_cost = _p(params.get("acquisition_cost"))
    conversion_rate = _p(params.get("conversion_rate"))

    total_spend = budget_total + marketing_spend
    projected_net = revenue_target - total_spend
    roi_achieved = (projected_net / total_spend * 100) if total_spend > 0 else 0.0

    # What would it take to hit the target ROI?
    # ROI = (rev - spend)/spend  => rev_required = spend * (1 + target_roi)
    roi_multiplier = 1.0 + (target_roi / 100.0)
    revenue_required = (total_spend * roi_multiplier) if total_spend > 0 else 0.0
    additional_revenue_needed = max(0.0, revenue_required - revenue_target)
    max_spend_for_target = (revenue_target / roi_multiplier) if roi_multiplier > 0 else 0.0
    spend_reduction_needed = max(0.0, total_spend - max_spend_for_target)

    monthly_revenue_target = (revenue_target / timeline_months) if timeline_months > 0 else 0.0
    monthly_spend = (total_spend / timeline_months) if timeline_months > 0 else 0.0

    performance = {
        "rating": "Good" if roi_achieved >= target_roi else "Needs Improvement",
        "color": "green" if roi_achieved >= target_roi else "orange",
    }

    metrics = {
        "Revenue Target": revenue_target,
        "Budget Total": budget_total,
        "Marketing Spend": marketing_spend,
        "Target ROI": target_roi,
        "Timeline (Months)": timeline_months,
        "Projected Net": projected_net,
        "ROI Achieved": roi_achieved,
    }
    if timeline_months > 0:
        metrics["Monthly Revenue Target"] = monthly_revenue_target
        metrics["Monthly Spend"] = monthly_spend
    if acquisition_cost:
        metrics["Acquisition Cost"] = acquisition_cost
    if conversion_rate:
        metrics["Conversion Rate"] = conversion_rate

    recommendations = []
    if roi_achieved < target_roi:
        if additional_revenue_needed > 0:
            recommendations.append(
                f"To reach the target ROI ({target_roi:.1f}%), you need approximately ${additional_revenue_needed:,.0f} more revenue at the current spend level."
            )
        if spend_reduction_needed > 0:
            recommendations.append(
                f"Alternatively, reduce total spend by about ${spend_reduction_needed:,.0f} (or improve margins) to hit the ROI target at the current revenue target."
            )
    if marketing_spend > 0 and total_spend > 0 and (marketing_spend / total_spend) > 0.5:
        marketing_share = (marketing_spend / total_spend * 100) if total_spend > 0 else 0.0
        recommendations.append(
            f"Marketing is {marketing_share:.0f}% of total spend. Rebalance toward operations/product to avoid over-reliance on paid acquisition."
        )
    if revenue_target < total_spend:
        recommendations.append(
            "Revenue target is below total spend. Revisit pricing, volume assumptions, and unit economics before committing budget."
        )
    if not recommendations:
        recommendations.append(
            "Goals look balanced. Track actuals monthly (revenue, spend, margin) and adjust the plan quarterly based on ROI and leading indicators."
        )

    recommendations = _dedupe_preserve_order(recommendations)

    additional_data = {"Total Spend": total_spend, "Timeline": f"{timeline_months} months"}

    try:
        from backend.consulting_services.kpi.kpi_utils import format_business_report
        report = format_business_report(
            "Business Goals Analysis", metrics, performance, recommendations,
            benchmarks=None, additional_data=additional_data
        )
        return _ensure_html(
            report.get("business_report_html") or report.get("business_report") or "Report generated."
        )
    except Exception as exc:
        logger.warning("Business Goals format_business_report fallback: %s", exc)
        return _build_goals_fallback_html(metrics, recommendations, performance)


def _build_goals_fallback_html(metrics: dict, recs: list, performance: dict) -> str:
    recs_html = "".join(f"<li>{html.escape(r)}</li>" for r in recs)
    rows = "".join(
        f"<tr><td><strong>{html.escape(str(k))}</strong></td>"
        f"<td>${v:,.2f}</td></tr>"
        if isinstance(v, (int, float)) else
        f"<tr><td><strong>{html.escape(str(k))}</strong></td>"
        f"<td>{html.escape(str(v))}</td></tr>"
        for k, v in metrics.items()
    )
    rating = performance.get("rating", "")
    return f"""
<div class="report">
  <div class="report__header"><h2>Business Goals Analysis</h2></div>
  <div class="report__body">
    <div class="highlight-box"><strong>Rating:</strong> {html.escape(rating)}</div>
    <div class="section">
      <div class="section-title">Key Metrics</div>
      <table><tbody>{rows}</tbody></table>
    </div>
    <div class="section">
      <div class="section-title">Recommendations</div>
      <ul>{recs_html}</ul>
    </div>
  </div>
</div>
""".strip()


#  CSV report formatter 

def _format_csv_report_html(result: dict) -> str:
    if not isinstance(result, dict):
        return _ensure_html(str(result))
    if result.get("status") == "error":
        msg = html.escape(str(result.get("message") or "Unknown error"))
        parts = [
            '<div class="report">',
            '<div class="report__header" style="background:linear-gradient(135deg,#ef4444,#dc2626);">',
            "<h2>CSV Error</h2></div>",
            f'<div class="report__body"><p><strong>Error:</strong> {msg}</p>',
        ]
        if result.get("help"):
            parts.append(f'<p><strong>Help:</strong> {html.escape(str(result["help"]))}</p>')
        if result.get("your_columns"):
            cols = ", ".join(html.escape(str(c)) for c in result["your_columns"])
            parts.append(f"<p><strong>Found columns:</strong> {cols}</p>")
        parts += ["</div></div>"]
        return "".join(parts)

    report_html = (
        result.get("business_report_html")
        or result.get("data", {}).get("business_report_html")
        or result.get("business_report")
        or result.get("data", {}).get("business_report")
    )
    return _ensure_html(str(report_html or "No report generated."))


#  API views 

@method_decorator(csrf_exempt, name="dispatch")
class StrategicChatAPIView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]
    parser_classes = [JSONParser]

    def post(self, request, *args, **kwargs):
        serializer = StrategicChatRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                _error_payload(code="VALIDATION_ERROR", message="Invalid request.", details=serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )

        message: str = serializer.validated_data["message"]

        try:
            params = _parse_kv(message)
            subtask = _detect_subtask(message, params)

            if subtask == "swot":
                html_response = _generate_swot_html(message)

            elif subtask == "business_goals":
                if not any(k in params for k in ["revenue_target", "budget_total", "marketing_spend", "timeline"]):
                    return Response(
                        {"html_response": _ensure_html(
                            "Please provide business goal metrics. Example:\n"
                            "Revenue target: $1,200,000. Budget total: $250,000. Marketing spend: $60,000. Target ROI: 20%. Timeline: 12 months."
                        )},
                        status=status.HTTP_200_OK,
                    )
                html_response = _generate_business_goals_html(params)

            else:  # growth_strategy
                if not any(k in params for k in ["market_size", "market_share", "competition_level", "investment_budget"]):
                    return Response(
                        {"html_response": _ensure_html(
                            "Please provide growth strategy metrics. Example:\n"
                            "Market size: $5,000,000. Market share: 3%. Competition level: 65%. Investment budget: $150,000. Target ROI: 18%."
                        )},
                        status=status.HTTP_200_OK,
                    )
                from backend.consulting_services.strategy.analysis_functions import (
                    calculate_growth_strategy_analysis,
                )
                result = calculate_growth_strategy_analysis(
                    market_size=_p(params.get("market_size")),
                    market_share=_p(params.get("market_share")),
                    competition_level=_p(params.get("competition_level")),
                    investment_budget=_p(params.get("investment_budget")),
                    growth_potential=_p(params.get("growth_potential"), 15.0) or 15.0,
                    competitive_advantage=_p(params.get("competitive_advantage"), 7.0) or 7.0,
                    market_penetration=_p(params.get("market_penetration"), 5.0) or 5.0,
                    roi_target=_p(params.get("roi_target") or params.get("target_roi"), 20.0) or 20.0,
                )
                html_response = _ensure_html(
                    result.get("business_report_html") or result.get("business_report") or "No report generated."
                )

            return Response({"html_response": html_response}, status=status.HTTP_200_OK)

        except Exception as exc:
            trace_id = str(uuid4())
            logger.exception("Strategic chat API error trace_id=%s: %s", trace_id, exc)
            return Response(
                _error_payload(code="INTERNAL_ERROR", message="Server error during strategic analysis.", trace_id=trace_id),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@method_decorator(csrf_exempt, name="dispatch")
class StrategicUploadAPIView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        if "required_csv" not in request.FILES:
            return Response(
                _error_payload(code="VALIDATION_ERROR", message="required_csv file is missing."),
                status=status.HTTP_400_BAD_REQUEST,
            )

        required_csv = request.FILES["required_csv"]
        if not getattr(required_csv, "name", "").lower().endswith(".csv"):
            return Response(
                _error_payload(code="VALIDATION_ERROR", message="required_csv must be a .csv file."),
                status=status.HTTP_400_BAD_REQUEST,
            )

        analysis_type = request.data.get("analysis_type", "").lower()

        try:
            from backend.consulting_services.strategy.strategic_csv_processor import (
                process_business_goals_csv_data,
                process_growth_strategy_csv_data,
            )

            raw_bytes = required_csv.read()

            def _fresh():
                return io.BytesIO(raw_bytes)

            # Route by analysis_type (card ID matches)
            if "swot" in analysis_type:
                # No CSV processor for SWOT  guide the user
                html_response = _ensure_html(
                    "SWOT analysis works from text input rather than CSV files.\n"
                    "Please type your SWOT data in the chat box:\n\n"
                    "Strengths: loyal customers, prime location; "
                    "Weaknesses: high labor cost, limited seating; "
                    "Opportunities: catering, online ordering; "
                    "Threats: new competitors, rising food costs."
                )

            elif "business_goals" in analysis_type or "performance" in analysis_type:
                result = process_business_goals_csv_data(_fresh())
                html_response = _format_csv_report_html(result if isinstance(result, dict) else {})

            elif "growth" in analysis_type or "scheduling" in analysis_type or "market" in analysis_type:
                result = process_growth_strategy_csv_data(_fresh())
                html_response = _format_csv_report_html(result if isinstance(result, dict) else {})

            else:
                # Auto-detect: try business goals first, then growth strategy
                result = process_business_goals_csv_data(_fresh())
                if isinstance(result, dict) and result.get("status") == "error":
                    result = process_growth_strategy_csv_data(_fresh())
                html_response = _format_csv_report_html(result if isinstance(result, dict) else {})

            return Response({"html_response": _ensure_html(html_response)}, status=status.HTTP_200_OK)

        except Exception as exc:
            trace_id = str(uuid4())
            logger.exception("Strategic upload API error trace_id=%s: %s", trace_id, exc)
            return Response(
                _error_payload(code="INTERNAL_ERROR", message="Server error during strategic CSV processing.", trace_id=trace_id),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
