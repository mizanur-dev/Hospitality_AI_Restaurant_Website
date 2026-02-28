"""
HR Labor Scheduling Analysis Task
Analyzes scheduling efficiency and provides optimization strategies with comprehensive business report.
"""

from backend.shared.ai.strategic_recommendations import generate_ai_strategic_recommendations
from backend.consulting_services.kpi.kpi_utils import format_business_report
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

        ai_recommendations = generate_ai_strategic_recommendations(
            analysis_type="HR Labor Scheduling Analysis",
            metrics={
                "total_sales": round(total_sales, 2),
                "labor_hours": round(labor_hours, 1),
                "hourly_rate": round(hourly_rate, 2),
                "total_labor_cost": round(total_labor_cost, 2),
                "sales_per_hour": round(sales_per_hour, 2),
                "labor_percent": round(labor_percent, 2),
                "peak_hours": round(peak_hours, 1),
                "off_peak_hours": round(off_peak_hours, 1),
                "peak_efficiency_percent": round(peak_efficiency, 1),
                "target_labor_percent": round(target_labor_percent, 1),
                "potential_savings": round(potential_savings, 2),
                "additional_sales_needed": round(additional_sales_needed, 2),
                "hours_to_cut": round(hours_to_cut, 1),
            },
            performance=performance_data,
            benchmarks=benchmarks,
            additional_data=additional_insights,
            existing_recommendations=recommendations,
            max_items=6,
        )
        if ai_recommendations:
            recommendations = ai_recommendations

        # Use the shared report formatter so HR outputs match KPI layout (tracking cards, header, etc.)
        # Optional inputs (do not require): overtime_hours, covers.
        overtime_hours_param = params.get("overtime_hours")
        covers_param = params.get("covers")

        if overtime_hours_param is not None and float(overtime_hours_param) >= 0:
            actual_overtime_hours = float(overtime_hours_param)
            overtime_source = "Actual"
        else:
            # Estimate overtime similarly to KPI utils (monthly input assumption)
            actual_overtime_hours = max(0.0, labor_hours - 160.0)
            overtime_source = "Estimated"

        regular_hours = max(0.0, labor_hours - actual_overtime_hours)
        overtime_percent = (actual_overtime_hours / labor_hours * 100) if labor_hours > 0 else 0.0
        overtime_premium_cost = actual_overtime_hours * hourly_rate * 0.5

        if covers_param is not None and float(covers_param) > 0:
            actual_covers = int(float(covers_param))
            covers_source = "Actual"
            avg_check = total_sales / actual_covers if actual_covers > 0 else 25.0
            covers_per_labor_hour = actual_covers / labor_hours if labor_hours > 0 else 0.0
        else:
            avg_check = 25.0
            actual_covers = int(total_sales / avg_check) if avg_check > 0 else 0
            covers_source = "Estimated"
            covers_per_labor_hour = (sales_per_hour / avg_check) if avg_check > 0 else 0.0

        productivity_score = min((sales_per_hour / 50.0 * 100.0) if sales_per_hour > 0 else 0.0, 150.0)
        labor_efficiency_ratio = total_sales / total_labor_cost if total_labor_cost > 0 else 0.0
        labor_cost_per_cover = total_labor_cost / actual_covers if actual_covers > 0 else 0.0

        savings_from_target = round(potential_savings, 2) if potential_savings > 0 else 0.0
        savings_from_overtime = round(overtime_premium_cost, 2) if actual_overtime_hours > 0 else 0.0
        savings_from_efficiency = round(total_labor_cost * 0.05, 2) if sales_per_hour < 50 else 0.0
        total_savings_opportunity = savings_from_target + savings_from_overtime + savings_from_efficiency

        formatted = format_business_report(
            analysis_type="Labor Scheduling Analysis",
            metrics=metrics,
            performance=performance_data,
            recommendations=tuple(recommendations),  # tuple skips formatter's AI rewrite
            benchmarks=benchmarks,
            additional_data={
                "savings_summary": {
                    "total_savings_opportunity": round(total_savings_opportunity, 2),
                    "savings_from_cost_reduction": round(savings_from_target, 2),
                    "savings_from_overtime_reduction": round(savings_from_overtime, 2),
                    "savings_from_efficiency": round(savings_from_efficiency, 2),
                    "status": "On Target" if total_savings_opportunity == 0 else "Savings Available",
                    "data_source": "Calculated",
                },
                "overtime_tracking": {
                    "overtime_hours": round(actual_overtime_hours, 1),
                    "regular_hours": round(regular_hours, 1),
                    "overtime_percent": round(overtime_percent, 1),
                    "overtime_premium_cost": round(overtime_premium_cost, 2),
                    "data_source": overtime_source,
                    "status": "Low" if overtime_percent < 5 else "Moderate" if overtime_percent < 10 else "High",
                },
                "productivity_metrics": {
                    "productivity_score": round(productivity_score, 1),
                    "labor_efficiency_ratio": round(labor_efficiency_ratio, 2),
                    "covers_per_labor_hour": round(covers_per_labor_hour, 1),
                    "labor_cost_per_cover": round(labor_cost_per_cover, 2),
                    "total_covers": actual_covers,
                    "avg_check": round(avg_check, 2),
                    "data_source": covers_source,
                    "rating": "Excellent" if productivity_score > 120 else "Good" if productivity_score > 100 else "Needs Improvement",
                },
                "efficiency_metrics": {
                    "peak_efficiency_percent": round(peak_efficiency, 1),
                    "off_peak_hours": round(off_peak_hours, 1),
                    "sales_per_hour": round(sales_per_hour, 2),
                    "data_source": "Calculated",
                },
                "efficiency_rating": "High" if sales_per_hour > 80 else "Medium" if sales_per_hour > 50 else "Low",
                "scheduling_optimization_priority": additional_insights["scheduling_optimization_priority"],
                "overtime_risk": additional_insights["overtime_risk"],
            },
        )

        business_report_html = formatted.get("business_report_html", "")
        business_report = formatted.get("business_report", "")

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
            # Savings are opportunities only when above target; never show negative "savings".
            "potential_savings": savings_from_target,
            "business_report_html": business_report_html,
            "business_report": business_report
        }

        insights = recommendations

        return success_payload(service, subtask, params, data, insights), 200

    except ValueError as e:
        return error_payload(service, subtask, str(e))
    except Exception as e:
        return error_payload(service, subtask, f"Internal error: {str(e)}", 500)
