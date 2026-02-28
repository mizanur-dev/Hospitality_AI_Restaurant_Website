"""HR CSV Data Processor.

This processor backs CSV upload endpoints. It is intentionally optimized for
predictable response time:

- Detect analysis type from the CSV header.
- Read only the columns required for that analysis.
- Compute a single aggregate analysis (no per-row processing).

If AI is configured (OPENAI_API_KEY), we generate AI-based strategic
recommendations from the *aggregate metrics only* (no per-row detail) with a
strict timeout and caching.
"""

from __future__ import annotations

import csv
import io
import os
import re
from typing import Any, Dict, List, Optional

import pandas as pd

from backend.consulting_services.kpi.kpi_utils import format_business_report
from backend.shared.ai.strategic_recommendations import generate_ai_strategic_recommendations


def _ai_timeout_s() -> float:
    try:
        return float(os.getenv("HR_UPLOAD_AI_TIMEOUT_S", os.getenv("OPENAI_TIMEOUT_S", "4.0")))
    except Exception:
        return 4.0


def _maybe_ai_recommendations(
    *,
    analysis_type: str,
    metrics: dict[str, Any],
    performance: dict[str, Any] | None,
    benchmarks: dict[str, Any] | None,
    additional_data: dict[str, Any] | None,
    existing: list[str],
    max_items: int = 6,
) -> list[str]:
    # Only attempt AI when configured; helper returns None otherwise.
    ai_recs = generate_ai_strategic_recommendations(
        analysis_type=analysis_type,
        metrics=metrics or {},
        performance=performance or {},
        benchmarks=benchmarks or {},
        additional_data=additional_data or {},
        existing_recommendations=existing or [],
        max_items=max_items,
        timeout_s=_ai_timeout_s(),
    )
    if ai_recs and isinstance(ai_recs, list):
        cleaned = [str(x).strip() for x in ai_recs if str(x).strip()]
        return cleaned[:max_items] if cleaned else existing
    return existing


def _normalize_col_name(name: str) -> str:
    value = str(name or "").strip().lower()
    value = value.replace("%", " percent ")
    value = re.sub(r"[^a-z0-9_]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value


def _read_upload_bytes(csv_file) -> bytes:
    try:
        pos = csv_file.tell()
    except Exception:
        pos = None

    raw = csv_file.read()
    raw_bytes = raw.encode("utf-8") if isinstance(raw, str) else (raw or b"")

    try:
        csv_file.seek(0 if pos is None else pos)
    except Exception:
        pass

    return raw_bytes


def _sniff_header_columns(raw_bytes: bytes) -> List[str]:
    try:
        text = raw_bytes.decode("utf-8", errors="replace")
        reader = csv.reader(io.StringIO(text))
        header = next(reader, [])
        return [str(c).strip() for c in header if str(c).strip()]
    except Exception:
        return []


def _find_column(norm_to_original: dict[str, str], variations: List[str]) -> Optional[str]:
    for var in variations:
        key = _normalize_col_name(var)
        if key in norm_to_original:
            return norm_to_original[key]
    return None


def _map_columns(norm_to_original: dict[str, str], column_def: Dict[str, List[str]]) -> dict[str, str]:
    mapped: dict[str, str] = {}
    for target, variations in column_def.items():
        found = _find_column(norm_to_original, variations)
        if found:
            mapped[target] = found
    return mapped


def _detect_analysis_type_from_header(norm_to_original: dict[str, str]) -> Optional[str]:
    has_turnover = _find_column(norm_to_original, ["turnover_rate", "turnover", "attrition_rate"]) is not None
    has_sched = all(
        _find_column(norm_to_original, vars) is not None
        for vars in [
            ["total_sales", "sales", "revenue"],
            ["labor_hours", "hours_worked", "hours"],
            ["hourly_rate", "pay_rate", "avg_hourly_rate", "wage"],
        ]
    )
    has_perf = any(
        _find_column(norm_to_original, vars) is not None
        for vars in [
            ["customer_satisfaction", "csat", "satisfaction"],
            ["sales_performance", "sales_score", "sales_target"],
            ["efficiency_score", "efficiency", "productivity_score"],
            ["attendance_rate", "attendance", "attendance_pct"],
        ]
    )

    if has_sched:
        return "scheduling"
    if has_turnover:
        return "retention"
    if has_perf:
        return "performance"
    return None


def _clean_numeric_series(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()
    s = s.str.replace("$", "", regex=False)
    s = s.str.replace(",", "", regex=False)
    s = s.str.replace("%", "", regex=False)
    s = s.replace({"": None, "nan": None, "NaN": None})
    return pd.to_numeric(s, errors="coerce")


def _maybe_scale_ratio_to_percent(series: pd.Series) -> pd.Series:
    if series is None or series.empty:
        return series
    s = series.dropna()
    if s.empty:
        return series
    try:
        if float(s.max()) <= 1.0:
            return series * 100.0
    except Exception:
        return series
    return series


def _wrap_text_report_html(title: str, report_text: str) -> str:
    safe_text = report_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    safe_text = safe_text.replace("\n", "<br>")
    return (
        '<section class="report" style="border:1px solid #e5e7eb;border-radius:16px;overflow:hidden;background:#fff;box-shadow:0 10px 30px rgba(0,0,0,0.06);">'
        f'<header class="report__header" style="background:linear-gradient(135deg,#0ea5e9,#6366f1);color:#fff;padding:20px;">'
        f'<h2 style="margin:0 0 6px 0;">{title}</h2>'
        f'<div class="report__meta" style="opacity:0.9;">Generated: {__import__("datetime").datetime.now().strftime("%B %d, %Y")}</div>'
        '</header>'
        f'<article class="report__body" style="padding:20px;line-height:1.6;">{safe_text}</article>'
        '</section>'
    )


def process_hr_csv_data(csv_file, analysis_type: str = "auto", *, fast: bool = True) -> Dict[str, Any]:
    """Process uploaded CSV file for HR analysis.

    analysis_type: "retention", "scheduling", "performance", or "auto".
    fast: kept for backwards-compatibility; uploads always use fast aggregate mode.
    """

    try:
        raw_bytes = _read_upload_bytes(csv_file)
        header_cols = _sniff_header_columns(raw_bytes)
        if not header_cols:
            return {"status": "error", "message": "The CSV file is empty or has no valid header"}

        norm_to_original = {_normalize_col_name(c): c for c in header_cols}

        retention_columns = {
            "turnover_rate": ["turnover_rate", "turnover", "turnover_percent", "turnover%", "attrition_rate"],
            "industry_average": ["industry_average", "industry_avg", "benchmark", "industry_benchmark"],
            "department": ["department", "dept", "team", "division"],
            "employee_count": ["employee_count", "employees", "headcount", "staff_count"],
        }
        scheduling_columns = {
            "total_sales": ["total_sales", "sales", "revenue", "daily_sales"],
            "labor_hours": ["labor_hours", "hours_worked", "hours", "staff_hours", "work_hours"],
            "hourly_rate": ["hourly_rate", "rate", "wage", "pay_rate", "avg_hourly_rate"],
            "peak_hours": ["peak_hours", "peak_hours_worked", "busy_hours"],
            "date": ["date", "period", "week", "day"],
        }
        performance_columns = {
            "customer_satisfaction": ["customer_satisfaction", "csat", "satisfaction", "customer_score"],
            "sales_performance": ["sales_performance", "sales_score", "sales_target", "sales_pct"],
            "efficiency_score": ["efficiency_score", "efficiency", "productivity", "productivity_score"],
            "attendance_rate": ["attendance_rate", "attendance", "attendance_pct"],
            "employee_name": ["employee_name", "name", "employee", "staff_name"],
            "department": ["department", "dept", "team"],
        }

        if analysis_type == "auto":
            detected = _detect_analysis_type_from_header(norm_to_original)
            if not detected:
                return {
                    "status": "error",
                    "message": "Could not determine HR analysis type from CSV columns",
                    "found_columns": header_cols,
                    "help": """HR Analysis requires specific columns based on analysis type:

Staff Retention:
- Required: turnover_rate
- Optional: industry_average, department, employee_count

Labor Scheduling:
- Required: total_sales, labor_hours (or hours_worked), hourly_rate
- Optional: peak_hours, date

Training Programs:
- Required: at least one of customer_satisfaction, sales_performance, efficiency_score, attendance_rate
- Optional: employee_name, department""",
                }
            analysis_type = detected

        if analysis_type == "retention":
            mapped = _map_columns(norm_to_original, retention_columns)
            if "turnover_rate" not in mapped:
                return {
                    "status": "error",
                    "message": "Missing required column: turnover_rate",
                    "found_columns": header_cols,
                }
            usecols = sorted(set(mapped.values()))
            df = pd.read_csv(io.BytesIO(raw_bytes), usecols=usecols)
            return _fast_retention_aggregate(df, mapped, header_cols)

        if analysis_type == "scheduling":
            mapped = _map_columns(norm_to_original, scheduling_columns)
            missing = [k for k in ["total_sales", "labor_hours", "hourly_rate"] if k not in mapped]
            if missing:
                return {
                    "status": "error",
                    "message": f"Missing required columns: {', '.join(missing)}",
                    "found_columns": header_cols,
                }
            usecols = sorted(set(mapped.values()))
            df = pd.read_csv(io.BytesIO(raw_bytes), usecols=usecols)
            return _fast_scheduling_aggregate(df, mapped, header_cols)

        if analysis_type == "performance":
            mapped = _map_columns(norm_to_original, performance_columns)
            metric_keys = ["customer_satisfaction", "sales_performance", "efficiency_score", "attendance_rate"]
            if not any(k in mapped for k in metric_keys):
                return {
                    "status": "error",
                    "message": "At least one performance metric column is required",
                    "found_columns": header_cols,
                }
            usecols = sorted(set(mapped.values()))
            df = pd.read_csv(io.BytesIO(raw_bytes), usecols=usecols)
            return _fast_performance_aggregate(df, mapped, header_cols)

        return {
            "status": "error",
            "message": f"Unknown analysis type: {analysis_type}",
            "supported_types": ["retention", "scheduling", "performance", "auto"],
        }

    except pd.errors.EmptyDataError:
        return {"status": "error", "message": "The CSV file is empty or has no valid data"}
    except Exception as exc:
        return {
            "status": "error",
            "message": f"Error processing HR CSV: {str(exc)}",
            "error_type": type(exc).__name__,
        }


def _fast_retention_aggregate(df: pd.DataFrame, mapped: dict[str, str], header_cols: List[str]) -> Dict[str, Any]:
    turnover = _maybe_scale_ratio_to_percent(_clean_numeric_series(df[mapped["turnover_rate"]]))
    industry_col = mapped.get("industry_average")
    industry = _maybe_scale_ratio_to_percent(_clean_numeric_series(df[industry_col])) if industry_col else None
    dept_col = mapped.get("department")
    headcount_col = mapped.get("employee_count")

    avg_turnover = float(turnover.mean(skipna=True)) if turnover.notna().any() else 0.0
    avg_industry = float(industry.mean(skipna=True)) if (industry is not None and industry.notna().any()) else 70.0
    retention_rate = 100.0 - avg_turnover
    vs_industry = avg_turnover - avg_industry

    avg_annual_salary = 30000.0
    replacement_cost_per_employee = avg_annual_salary * 1.5
    if headcount_col:
        headcount = _clean_numeric_series(df[headcount_col])
        employees = float(headcount.mean(skipna=True)) if headcount.notna().any() else 25.0
        employees = max(1.0, employees)
    else:
        employees = 25.0
    estimated_annual_turnover_cost = (avg_turnover / 100.0) * employees * replacement_cost_per_employee

    if avg_turnover <= 30:
        rating, risk_level = "Excellent", "Low"
    elif avg_turnover <= 50:
        rating, risk_level = "Good", ("Low" if avg_turnover <= avg_industry else "Moderate")
    elif avg_turnover <= 70:
        rating, risk_level = "Acceptable", ("Moderate" if avg_turnover <= avg_industry + 20 else "High")
    else:
        rating, risk_level = "Needs Improvement", "High"

    recommendations: list[str] = []
    if avg_turnover > avg_industry:
        gap = max(0.0, vs_industry)
        recommendations.append(
            f"Reduce turnover by ~{gap:.1f} points to reach the industry average ({avg_industry:.1f}%). Focus on scheduling fairness, manager practices, workload, and role clarity."
        )
        recommendations.append("Run stay interviews with high performers this month; fix the top 2 recurring drivers.")
        recommendations.append("Improve first-30/60/90-day onboarding with checklists, buddy system, and manager check-ins.")
    else:
        recommendations.append("Maintain current retention practices; turnover is at/under the benchmark.")
        recommendations.append("Track turnover monthly by department and tenure to catch drift early.")

    metrics = {
        "turnover_rate": round(avg_turnover, 2),
        "retention_rate": round(retention_rate, 2),
        "industry_average": round(avg_industry, 2),
        "vs_industry": round(vs_industry, 2),
        "estimated_annual_turnover_cost": round(estimated_annual_turnover_cost, 2),
    }
    performance = {"rating": rating, "risk_level": risk_level}
    benchmarks = {"industry_average": round(avg_industry, 2)}
    additional_data = {"records_analyzed": len(df), "employees_estimate": round(employees, 1)}

    # AI-based recommendations (aggregate metrics only, strict timeout).
    recommendations = _maybe_ai_recommendations(
        analysis_type="HR Staff Retention (CSV Upload)",
        metrics=metrics,
        performance=performance,
        benchmarks=benchmarks,
        additional_data=additional_data,
        existing=recommendations,
        max_items=6,
    )

    dept_lines: list[str] = []
    if dept_col and dept_col in df.columns:
        try:
            tmp = pd.DataFrame({"dept": df[dept_col].astype(str), "turnover": turnover})
            tmp = tmp[(tmp["dept"].str.strip() != "") & tmp["turnover"].notna()]
            if not tmp.empty:
                dept_avgs = tmp.groupby("dept")["turnover"].mean().sort_values(ascending=False).head(8)
                dept_lines = [f"• {d}: {v:.1f}%" for d, v in dept_avgs.items()]
        except Exception:
            dept_lines = []

    report_lines = [
        "RESTAURANT CONSULTING REPORT — STAFF RETENTION (CSV)",
        "====================================================",
        f"Records analyzed: {len(df):,}",
        "",
        "KEY METRICS:",
        f"• Average Turnover Rate: {avg_turnover:.1f}%",
        f"• Average Retention Rate: {retention_rate:.1f}%",
        f"• Industry Average: {avg_industry:.1f}%",
        f"• vs Industry: {vs_industry:+.1f}%",
        f"• Estimated Annual Turnover Cost: ${estimated_annual_turnover_cost:,.0f}",
        "",
        f"PERFORMANCE RATING: {rating.upper()} (Risk: {risk_level})",
    ]
    if dept_lines:
        report_lines.extend(["", "TURNOVER BY DEPARTMENT (top):", *dept_lines])
    report_lines.append("")
    report_lines.append("RECOMMENDATIONS:")
    for i, rec in enumerate(recommendations[:6], 1):
        report_lines.append(f"{i}. {rec}")

    report_text = "\n".join(report_lines).strip()
    report_html = _wrap_text_report_html("Staff Retention Summary", report_text)

    return {
        "status": "success",
        "analysis_type": "staff_retention",
        "data": {
            "turnover_rate": round(avg_turnover, 2),
            "retention_rate": round(retention_rate, 2),
            "industry_average": round(avg_industry, 2),
            "vs_industry": round(vs_industry, 2),
            "risk_level": risk_level,
            "estimated_annual_cost": round(estimated_annual_turnover_cost, 2),
            "strategic_recommendations": recommendations[:6],
            "business_report": report_text,
            "business_report_html": report_html,
        },
        "business_report": report_text,
        "business_report_html": report_html,
        "found_columns": header_cols,
    }


def _fast_scheduling_aggregate(df: pd.DataFrame, mapped: dict[str, str], header_cols: List[str]) -> Dict[str, Any]:
    sales = _clean_numeric_series(df[mapped["total_sales"]])
    hours = _clean_numeric_series(df[mapped["labor_hours"]])
    rate = _clean_numeric_series(df[mapped["hourly_rate"]])
    peak_col = mapped.get("peak_hours")
    peak = _clean_numeric_series(df[peak_col]) if peak_col and peak_col in df.columns else None

    total_sales = float(sales.sum(skipna=True))
    labor_hours = float(hours.sum(skipna=True))
    labor_hours = max(0.0, labor_hours)

    if labor_hours > 0 and hours.notna().any() and rate.notna().any():
        weighted = (hours.fillna(0.0) * rate.fillna(0.0)).sum(skipna=True)
        hourly_rate = float(weighted / labor_hours) if labor_hours else float(rate.mean(skipna=True) or 0.0)
    else:
        hourly_rate = float(rate.mean(skipna=True) or 0.0)

    peak_hours = float(peak.sum(skipna=True)) if (peak is not None and peak.notna().any()) else labor_hours * 0.3
    total_labor_cost = labor_hours * hourly_rate
    sales_per_hour = (total_sales / labor_hours) if labor_hours > 0 else 0.0
    labor_percent = (total_labor_cost / total_sales * 100.0) if total_sales > 0 else 0.0
    off_peak_hours = max(0.0, labor_hours - peak_hours)
    peak_efficiency = (peak_hours / labor_hours * 100.0) if labor_hours > 0 else 0.0

    if labor_percent <= 25:
        rating = "Excellent"
    elif labor_percent <= 30:
        rating = "Good"
    elif labor_percent <= 35:
        rating = "Acceptable"
    else:
        rating = "Needs Improvement"

    scheduling_efficiency = "High" if peak_efficiency >= 40 else "Medium" if peak_efficiency >= 25 else "Low"

    recs: list[str] = []
    target_labor_percent = 30.0
    if labor_percent > target_labor_percent and total_sales > 0:
        target_labor_cost = (target_labor_percent / 100.0) * total_sales
        potential_savings = max(0.0, total_labor_cost - target_labor_cost)
        hours_to_cut = (potential_savings / hourly_rate) if hourly_rate > 0 else 0.0
        recs.append(
            f"Labor is {labor_percent:.1f}% vs {target_labor_percent:.0f}% target. Reduce labor by ~${potential_savings:,.0f} (≈ {hours_to_cut:,.1f} hours) or grow sales while holding hours flat."
        )
        recs.append(f"Tighten off-peak coverage ({off_peak_hours:.1f} hrs) and rebuild schedules from hourly sales patterns.")
    if peak_efficiency < 30:
        recs.append(f"Peak coverage is low ({peak_efficiency:.1f}% of hours). Shift some off-peak hours into peak windows and validate with service metrics.")
    recs.append("Update schedules weekly and re-check labor % trend monthly.")

    metrics = {
        "total_sales": total_sales,
        "labor_hours": labor_hours,
        "hourly_rate": hourly_rate,
        "total_labor_cost": total_labor_cost,
        "sales_per_hour": round(sales_per_hour, 2),
        "labor_percent": round(labor_percent, 2),
        "peak_hours": peak_hours,
        "off_peak_hours": off_peak_hours,
    }
    performance = {"rating": rating, "scheduling_efficiency": scheduling_efficiency}
    benchmarks = {"target_labor_percent": target_labor_percent, "optimal_peak_percent": 40.0}

    recs = _maybe_ai_recommendations(
        analysis_type="HR Labor Scheduling (CSV Upload)",
        metrics={
            **metrics,
            "peak_efficiency_percent": round(peak_efficiency, 1),
        },
        performance=performance,
        benchmarks=benchmarks,
        additional_data={"records_analyzed": len(df)},
        existing=recs,
        max_items=6,
    )

    formatted = format_business_report(
        analysis_type="Labor Scheduling Analysis",
        metrics=metrics,
        performance=performance,
        recommendations=tuple(recs),  # tuple skips formatter's internal AI rewrite
        benchmarks=benchmarks,
        additional_data={"peak_efficiency_percent": round(peak_efficiency, 1), "records_analyzed": len(df)},
    )

    return {
        "status": "success",
        "analysis_type": "labor_scheduling",
        "data": {
            **metrics,
            "strategic_recommendations": recs[:6],
            "business_report": formatted.get("business_report"),
            "business_report_html": formatted.get("business_report_html"),
        },
        "business_report": formatted.get("business_report"),
        "business_report_html": formatted.get("business_report_html"),
        "found_columns": header_cols,
    }


def _fast_performance_aggregate(df: pd.DataFrame, mapped: dict[str, str], header_cols: List[str]) -> Dict[str, Any]:
    def mean_or_default(key: str, default: float) -> float:
        col = mapped.get(key)
        if not col or col not in df.columns:
            return default
        s = _maybe_scale_ratio_to_percent(_clean_numeric_series(df[col]))
        val = float(s.mean(skipna=True)) if s.notna().any() else default
        return default if pd.isna(val) else val

    csat = max(0.0, min(100.0, mean_or_default("customer_satisfaction", 85.0)))
    sales_perf = max(0.0, min(100.0, mean_or_default("sales_performance", 100.0)))
    efficiency = max(0.0, min(100.0, mean_or_default("efficiency_score", 80.0)))
    attendance = max(0.0, min(100.0, mean_or_default("attendance_rate", 95.0)))

    weights = {"customer_satisfaction": 0.3, "sales_performance": 0.3, "efficiency_score": 0.25, "attendance_rate": 0.15}
    overall_score = (
        csat * weights["customer_satisfaction"]
        + sales_perf * weights["sales_performance"]
        + efficiency * weights["efficiency_score"]
        + attendance * weights["attendance_rate"]
    )

    if overall_score >= 90:
        rating = "Excellent"
    elif overall_score >= 80:
        rating = "Good"
    elif overall_score >= 70:
        rating = "Acceptable"
    else:
        rating = "Needs Improvement"

    recs: list[str] = []
    if csat < 90:
        recs.append("Lift CSAT with service standards refresh + weekly coaching during peak shifts.")
    if sales_perf < 100:
        recs.append("Improve sales performance with upsell scripts, product knowledge refreshers, and a simple margin-focused incentive.")
    if efficiency < 85:
        recs.append("Boost efficiency with station setup standards, prep sequencing, and time-management coaching.")
    if attendance < 98:
        recs.append("Raise attendance with earlier schedules, clearer expectations, and manager follow-up on repeat absences.")
    recs.append("Standardize monthly performance check-ins and create individual development plans by role.")

    metrics = {
        "overall_score": round(float(overall_score), 1),
        "customer_satisfaction": round(csat, 1),
        "sales_performance": round(sales_perf, 1),
        "efficiency_score": round(efficiency, 1),
        "attendance_rate": round(attendance, 1),
        "performance_rating": rating,
    }
    performance = {"rating": rating, "overall_score": round(float(overall_score), 1)}
    benchmarks = {"excellent_threshold": 90.0, "good_threshold": 80.0, "acceptable_threshold": 70.0}

    recs = _maybe_ai_recommendations(
        analysis_type="HR Training Programs (CSV Upload)",
        metrics=metrics,
        performance=performance,
        benchmarks=benchmarks,
        additional_data={"records_analyzed": len(df)},
        existing=recs,
        max_items=6,
    )

    formatted = format_business_report(
        analysis_type="Training Programs Analysis",
        metrics=metrics,
        performance=performance,
        recommendations=tuple(recs),  # tuple skips formatter's internal AI rewrite
        benchmarks=benchmarks,
        additional_data={"records_analyzed": len(df)},
    )

    return {
        "status": "success",
        "analysis_type": "performance_management",
        "data": {
            **metrics,
            "strategic_recommendations": recs[:6],
            "business_report": formatted.get("business_report"),
            "business_report_html": formatted.get("business_report_html"),
        },
        "business_report": formatted.get("business_report"),
        "business_report_html": formatted.get("business_report_html"),
        "found_columns": header_cols,
    }
