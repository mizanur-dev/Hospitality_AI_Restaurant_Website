"""
HR Labor Scheduling Analysis Task
Analyzes scheduling efficiency and provides optimization strategies with comprehensive business report.
"""

from backend.shared.utils.common import success_payload, error_payload, require, validate_positive_numbers


def run(params: dict, file_bytes: bytes | None = None) -> tuple[dict, int]:
    """
    Calculate labor scheduling analysis with comprehensive business report.

    Args:
        params: Dictionary containing total_sales, labor_hours, hourly_rate, and optional peak_hours
        file_bytes: Optional file data (not used in this task)

    Returns:
        Tuple of (response_dict, status_code)
    """
    service, subtask = "hr", "labor_scheduling"

    try:
        # Validate required fields
        require(params, ["total_sales", "hourly_rate"])

        # Handle both labor_hours and hours_worked
        labor_hours = params.get("labor_hours") or params.get("hours_worked")
        if not labor_hours:
            return error_payload(service, subtask, "Missing required field: labor_hours or hours_worked")

        # Validate positive numbers
        validate_positive_numbers(params, ["total_sales", "hourly_rate"])
        validate_positive_numbers({"labor_hours": labor_hours}, ["labor_hours"])

        # Extract and convert values
        total_sales = float(params["total_sales"])
        labor_hours = float(labor_hours)
        hourly_rate = float(params["hourly_rate"])
        peak_hours = float(params.get("peak_hours", labor_hours * 0.3))  # Assume 30% peak hours if not provided

        # Calculate scheduling metrics
        total_labor_cost = labor_hours * hourly_rate
        sales_per_hour = total_sales / labor_hours
        labor_percent = (total_labor_cost / total_sales) * 100
        cost_per_hour = total_labor_cost / labor_hours

        # Peak efficiency analysis
        peak_efficiency = (peak_hours / labor_hours) * 100
        off_peak_hours = labor_hours - peak_hours

        # Performance assessment
        if labor_percent <= 25:
            performance = "Excellent"
            performance_color = "green"
        elif labor_percent <= 30:
            performance = "Good"
            performance_color = "blue"
        elif labor_percent <= 35:
            performance = "Acceptable"
            performance_color = "yellow"
        else:
            performance = "Needs Improvement"
            performance_color = "red"

        # Scheduling efficiency assessment
        if peak_efficiency >= 40:
            scheduling_efficiency = "High"
        elif peak_efficiency >= 25:
            scheduling_efficiency = "Medium"
        else:
            scheduling_efficiency = "Low"

        # Calculate potential savings
        target_labor_percent = 30.0
        target_labor_cost = (target_labor_percent / 100) * total_sales
        potential_savings = total_labor_cost - target_labor_cost
        hours_to_cut = (potential_savings / hourly_rate) if hourly_rate > 0 else 0.0
        sales_needed_for_current_labor = (total_labor_cost / (target_labor_percent / 100)) if target_labor_percent > 0 else 0.0
        additional_sales_needed = max(0.0, sales_needed_for_current_labor - total_sales)

        # Generate recommendations
        recommendations = []
        if labor_percent > target_labor_percent:
            recommendations.append(
                f"Labor is {labor_percent:.1f}% vs the {target_labor_percent:.0f}% target. Reduce labor cost by about ${potential_savings:,.0f} (≈ {hours_to_cut:,.1f} hours at ${hourly_rate:.2f}/hr) or grow sales by about ${additional_sales_needed:,.0f} at the current labor level."
            )
            recommendations.append(
                f"Reduce off-peak hours ({off_peak_hours:.1f} hrs) by tightening open/close checklists and matching staffing to demand in 30-minute blocks."
            )
            recommendations.append(
                "Cross-train so you can flex staffing without overtime: 1–2 key stations per person is usually enough to reduce coverage gaps."
            )

        if peak_efficiency < 30:
            recommendations.append(
                f"Peak coverage is low ({peak_efficiency:.1f}% of hours). Shift some off-peak hours into peak windows and validate with ticket times, wait times, and guest feedback."
            )
            recommendations.append(
                "Use a simple traffic map: hourly sales by day-of-week for the last 4–8 weeks, then schedule to that curve (and re-check monthly)."
            )
        else:
            recommendations.append("Maintain current peak hour staffing levels")

        if sales_per_hour < 50:
            recommendations.append(
                f"Sales per labor hour is ${sales_per_hour:.2f}. Improve SPLH by tightening deployment (right people at peaks) and by upselling on the top 3 items with the best margin."
            )
            recommendations.append(
                "If certain hours are consistently slow, cut one coverage slot at a time and track service metrics to avoid harming guest experience."
            )
        elif sales_per_hour > 100:
            recommendations.append("Excellent sales per hour - consider expanding during peak times")

        if performance != "Excellent" or scheduling_efficiency != "High":
            recommendations.append("Use predictive scheduling based on historical sales data and update weekly")
            recommendations.append("Consider a lightweight shift swap/bidding policy to improve coverage and satisfaction")

        # Prepare data for business report
        metrics = {
            "total_sales": total_sales,
            "labor_hours": labor_hours,
            "hourly_rate": hourly_rate,
            "total_labor_cost": total_labor_cost,
            "sales_per_hour": round(sales_per_hour, 2),
            "labor_percent": round(labor_percent, 2),
            "cost_per_hour": round(cost_per_hour, 2),
            "peak_hours": peak_hours,
            "off_peak_hours": off_peak_hours
        }

        performance_data = {
            "rating": performance,
            "color": performance_color,
            "scheduling_efficiency": scheduling_efficiency
        }

        benchmarks = {
            "excellent_labor_percent": 25.0,
            "good_labor_percent": 30.0,
            "acceptable_labor_percent": 35.0,
            "target_labor_percent": target_labor_percent,
            "optimal_peak_percent": 40.0
        }

        additional_insights = {
            "peak_efficiency_percent": round(peak_efficiency, 1),
            "potential_savings": round(potential_savings, 2),
            "scheduling_optimization_priority": "High" if labor_percent > 35 else "Medium" if labor_percent > 30 else "Low",
            "overtime_risk": "High" if peak_hours > labor_hours * 0.5 else "Medium" if peak_hours > labor_hours * 0.3 else "Low"
        }

        # Deduplicate recommendations (preserve order)
        if recommendations:
            seen = set()
            deduped = []
            for rec in recommendations:
                s = str(rec).strip().rstrip(".,;:")
                key = s.lower()
                if not key:
                    continue
                if key in seen:
                    continue
                seen.add(key)
                deduped.append(s)
            recommendations = deduped

        # Generate business report HTML (compacted to avoid \n in JSON)
        recs_html = ''.join([f'<li>{rec}</li>' for rec in recommendations])
        business_report_html = (
            f'<section class="report" style="border:1px solid #e5e7eb;border-radius:16px;overflow:hidden;background:#fff;box-shadow:0 10px 30px rgba(0,0,0,0.06);">'
            f'<header class="report__header" style="background:linear-gradient(135deg,#14b8a6,#22c55e);color:#fff;padding:20px;">'
            f'<h2 style="margin:0 0 6px 0;">Labor Scheduling Analysis</h2>'
            f'<div class="report__meta" style="opacity:0.9;">Generated: {__import__("datetime").datetime.now().strftime("%B %d, %Y")}</div>'
            f'<div class="badge badge--{performance.lower().replace(" ", "-")}" style="margin-top:8px;display:inline-block;background:rgba(255,255,255,0.2);padding:4px 10px;border-radius:999px;">{performance}</div>'
            f'</header>'
            f'<article class="report__body" style="padding:20px;">'
            f'<p class="lead" style="margin:0 0 14px 0;">Scheduling efficiency is <strong>{scheduling_efficiency.lower()}</strong> with labor at <strong>{labor_percent:.1f}%</strong> of sales.</p>'
            f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px;">'
            f'<div style="border:1px solid #e5e7eb;border-radius:12px;padding:12px;background:#f8fafc;">'
            f'<div style="font-size:0.85rem;color:#64748b;">Labor Percent</div>'
            f'<div style="font-size:1.6rem;font-weight:700;">{labor_percent:.1f}%</div>'
            f'</div>'
            f'<div style="border:1px solid #e5e7eb;border-radius:12px;padding:12px;background:#f8fafc;">'
            f'<div style="font-size:0.85rem;color:#64748b;">Sales per Hour</div>'
            f'<div style="font-size:1.6rem;font-weight:700;">${sales_per_hour:.2f}</div>'
            f'</div>'
            f'<div style="border:1px solid #e5e7eb;border-radius:12px;padding:12px;background:#f8fafc;">'
            f'<div style="font-size:0.85rem;color:#64748b;">Peak Efficiency</div>'
            f'<div style="font-size:1.6rem;font-weight:700;">{additional_insights["peak_efficiency_percent"]:.1f}%</div>'
            f'</div>'
            f'<div style="border:1px solid #e5e7eb;border-radius:12px;padding:12px;background:#f8fafc;">'
            f'<div style="font-size:0.85rem;color:#64748b;">Potential Savings</div>'
            f'<div style="font-size:1.6rem;font-weight:700;">${additional_insights["potential_savings"]:,.2f}</div>'
            f'</div>'
            f'</div>'
            f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px;margin-top:16px;">'
            f'<section style="border:1px solid #e5e7eb;border-radius:12px;padding:12px;background:#fff;">'
            f'<h3 style="margin:0 0 8px 0;">Core Metrics</h3>'
            f'<ul style="margin:0;padding-left:18px;">'
            f'<li>Total Sales: ${total_sales:,.2f}</li>'
            f'<li>Total Labor Cost: ${total_labor_cost:,.2f}</li>'
            f'<li>Labor Hours: {labor_hours:.1f}</li>'
            f'<li>Peak Hours: {peak_hours:.1f}</li>'
            f'</ul>'
            f'</section>'
            f'<section style="border:1px solid #e5e7eb;border-radius:12px;padding:12px;background:#fff;">'
            f'<h3 style="margin:0 0 8px 0;">Benchmarks</h3>'
            f'<ul style="margin:0;padding-left:18px;">'
            f'<li>Excellent Labor %: {benchmarks["excellent_labor_percent"]:.1f}%</li>'
            f'<li>Good Labor %: {benchmarks["good_labor_percent"]:.1f}%</li>'
            f'<li>Target Labor %: {benchmarks["target_labor_percent"]:.1f}%</li>'
            f'<li>Optimal Peak %: {benchmarks["optimal_peak_percent"]:.1f}%</li>'
            f'</ul>'
            f'</section>'
            f'<section style="border:1px solid #e5e7eb;border-radius:12px;padding:12px;background:#fff;">'
            f'<h3 style="margin:0 0 8px 0;">Insights</h3>'
            f'<ul style="margin:0;padding-left:18px;">'
            f'<li>Scheduling Efficiency: {scheduling_efficiency}</li>'
            f'<li>Optimization Priority: {additional_insights["scheduling_optimization_priority"]}</li>'
            f'<li>Overtime Risk: {additional_insights["overtime_risk"]}</li>'
            f'</ul>'
            f'</section>'
            f'</div>'
            f'<h3 style="margin:16px 0 8px 0;">Strategic Recommendations</h3>'
            f'<ol style="margin:0;padding-left:18px;">{recs_html}</ol>'
            f'</article>'
            f'</section>'
        )

        # Generate text business report
        business_report = f"""
RESTAURANT CONSULTING REPORT — LABOR SCHEDULING ANALYSIS
Generated: {__import__('datetime').datetime.now().strftime('%B %d, %Y')}

PERFORMANCE RATING: {performance.upper()}

This labor scheduling analysis reveals {performance.lower()} scheduling efficiency with {scheduling_efficiency.lower()} peak hour optimization.

KEY PERFORMANCE METRICS
• Total Sales: ${total_sales:,.2f}
• Labor Hours: {labor_hours:.1f}
• Hourly Rate: ${hourly_rate:.2f}
• Total Labor Cost: ${total_labor_cost:,.2f}
• Sales per Hour: ${sales_per_hour:.2f}
• Labor Percent: {labor_percent:.1f}%
• Peak Hours: {peak_hours:.1f}
• Off-Peak Hours: {off_peak_hours:.1f}

INDUSTRY BENCHMARKS
• Excellent Labor %: {benchmarks['excellent_labor_percent']:.1f}%
• Good Labor %: {benchmarks['good_labor_percent']:.1f}%
• Acceptable Labor %: {benchmarks['acceptable_labor_percent']:.1f}%
• Target Labor %: {benchmarks['target_labor_percent']:.1f}%
• Optimal Peak %: {benchmarks['optimal_peak_percent']:.1f}%

ADDITIONAL INSIGHTS
• Peak Efficiency: {additional_insights['peak_efficiency_percent']:.1f}%
• Scheduling Efficiency: {scheduling_efficiency}
• Potential Savings: ${additional_insights['potential_savings']:,.2f}
• Optimization Priority: {additional_insights['scheduling_optimization_priority']}
• Overtime Risk: {additional_insights['overtime_risk']}

STRATEGIC RECOMMENDATIONS
{chr(10).join([f'{i+1}. {rec}' for i, rec in enumerate(recommendations)])}

END OF REPORT
        """.strip()

        # Prepare response data
        data = {
            "total_sales": total_sales,
            "labor_hours": labor_hours,
            "hourly_rate": hourly_rate,
            "total_labor_cost": total_labor_cost,
            "sales_per_hour": sales_per_hour,
            "labor_percent": labor_percent,
            "peak_hours": peak_hours,
            "off_peak_hours": off_peak_hours,
            "performance_rating": performance,
            "scheduling_efficiency": scheduling_efficiency,
            "potential_savings": potential_savings,
            "business_report_html": business_report_html,
            "business_report": business_report
        }

        insights = recommendations

        return success_payload(service, subtask, params, data, insights), 200

    except ValueError as e:
        return error_payload(service, subtask, str(e))
    except Exception as e:
        return error_payload(service, subtask, f"Internal error: {str(e)}", 500)
