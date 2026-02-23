"""
HR Staff Retention Analysis Task
Analyzes turnover rates and provides retention strategies with comprehensive business report.
"""

from backend.shared.utils.common import success_payload, error_payload, require, validate_positive_numbers


def run(params: dict, file_bytes: bytes | None = None) -> tuple[dict, int]:
    """
    Calculate staff retention analysis with comprehensive business report.

    Args:
        params: Dictionary containing turnover_rate and industry_average
        file_bytes: Optional file data (not used in this task)

    Returns:
        Tuple of (response_dict, status_code)
    """
    service, subtask = "hr", "staff_retention"

    try:
        # Validate required fields
        require(params, ["turnover_rate"])

        # Validate positive numbers
        validate_positive_numbers(params, ["turnover_rate"])

        # Extract and convert values
        turnover_rate = float(params["turnover_rate"])
        industry_average = float(params.get("industry_average", 70.0))

        # Validate turnover rate is reasonable (0-200%)
        if turnover_rate > 200:
            raise ValueError("Turnover rate cannot exceed 200%")

        # Calculate retention metrics
        retention_rate = 100 - turnover_rate
        vs_industry = turnover_rate - industry_average

        # Performance assessment
        if turnover_rate <= 30:
            performance = "Excellent"
            performance_color = "green"
        elif turnover_rate <= 50:
            performance = "Good"
            performance_color = "blue"
        elif turnover_rate <= 70:
            performance = "Acceptable"
            performance_color = "yellow"
        else:
            performance = "Needs Improvement"
            performance_color = "red"

        # Risk assessment
        if turnover_rate > industry_average + 20:
            risk_level = "High"
        elif turnover_rate > industry_average:
            risk_level = "Moderate"
        else:
            risk_level = "Low"

        # Calculate cost impact (estimated)
        # Average cost to replace an employee is 1.5x their annual salary
        # Assuming average restaurant worker makes $30,000 annually
        avg_annual_salary = 30000
        replacement_cost_per_employee = avg_annual_salary * 1.5
        estimated_annual_turnover_cost = (turnover_rate / 100) * 25 * replacement_cost_per_employee  # Assuming 25 employees

        cost_per_turnover_point = (estimated_annual_turnover_cost / turnover_rate) if turnover_rate > 0 else 0.0
        gap_to_industry = max(0.0, vs_industry)
        savings_if_match_industry = gap_to_industry * cost_per_turnover_point

        # Generate recommendations
        recommendations = []
        if turnover_rate > industry_average:
            recommendations.append(
                f"Reduce turnover by about {gap_to_industry:.1f} points to reach the industry average ({industry_average:.1f}%). That could save roughly ${savings_if_match_industry:,.0f}/year using the current cost model."
            )
            recommendations.append(
                "Run 10–15 stay interviews this month (focus on high performers) to identify the top 2 controllable drivers (scheduling, manager issues, pay, workload)."
            )
            recommendations.append(
                "Fix the first-90-days experience: tighten onboarding checklist, assign a buddy, and schedule a 2-week and 6-week manager check-in to reduce early exits."
            )
            recommendations.append(
                "Add a simple recognition loop (weekly shout-outs + small rewards) tied to reliability and guest experience to improve engagement."
            )
        else:
            recommendations.append("Maintain current retention strategies - performance is above industry average")
            recommendations.append("Continue investing in employee development programs")

        if turnover_rate > 50:
            recommendations.append(
                "Turnover is elevated. Standardize exit interviews (same questions every time) and review results monthly to spot repeatable, fixable issues."
            )
            recommendations.append(
                "Check scheduling fairness and manager practices: inconsistent hours and poor management are common drivers in restaurants and are often faster to fix than comp changes."
            )
            recommendations.append(
                "If pay is a driver, prioritize targeted adjustments for the hardest-to-fill roles and tie them to performance and attendance expectations."
            )

        # Prepare data for business report
        metrics = {
            "turnover_rate": round(turnover_rate, 2),
            "retention_rate": round(retention_rate, 2),
            "industry_average": industry_average,
            "vs_industry": round(vs_industry, 2),
            "estimated_annual_cost": round(estimated_annual_turnover_cost, 2)
        }

        performance_data = {
            "rating": performance,
            "color": performance_color,
            "risk_level": risk_level
        }

        benchmarks = {
            "excellent_threshold": 30.0,
            "good_threshold": 50.0,
            "acceptable_threshold": 70.0,
            "industry_average": industry_average
        }

        additional_insights = {
            "replacement_cost_per_employee": replacement_cost_per_employee,
            "cost_savings_potential": round(estimated_annual_turnover_cost * 0.3, 2),  # 30% reduction potential
            "retention_strategy_priority": "High" if turnover_rate > 70 else "Medium" if turnover_rate > 50 else "Low",
            "employee_satisfaction_focus": "Critical" if turnover_rate > industry_average else "Maintain"
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

        # Generate business report HTML
        recs_html = ''.join([f'<li>{rec}</li>' for rec in recommendations])
        business_report_html = (
            f'<section class="report" style="border:1px solid #e5e7eb;border-radius:16px;overflow:hidden;background:#fff;box-shadow:0 10px 30px rgba(0,0,0,0.06);">'
            f'<header class="report__header" style="background:linear-gradient(135deg,#0ea5e9,#6366f1);color:#fff;padding:20px;">'
            f'<h2 style="margin:0 0 6px 0;">Staff Retention Analysis</h2>'
            f'<div class="report__meta" style="opacity:0.9;">Generated: {__import__("datetime").datetime.now().strftime("%B %d, %Y")}</div>'
            f'<div class="badge badge--{performance.lower().replace(" ", "-")}" style="margin-top:8px;display:inline-block;background:rgba(255,255,255,0.2);padding:4px 10px;border-radius:999px;">{performance}</div>'
            f'</header>'
            f'<article class="report__body" style="padding:20px;">'
            f'<p class="lead" style="margin:0 0 14px 0;">Turnover is <strong>{turnover_rate:.1f}%</strong> with a <strong>{risk_level.lower()}</strong> risk level versus industry standards.</p>'
            f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px;">'
            f'<div style="border:1px solid #e5e7eb;border-radius:12px;padding:12px;background:#f8fafc;">'
            f'<div style="font-size:0.85rem;color:#64748b;">Turnover Rate</div>'
            f'<div style="font-size:1.6rem;font-weight:700;">{turnover_rate:.1f}%</div>'
            f'</div>'
            f'<div style="border:1px solid #e5e7eb;border-radius:12px;padding:12px;background:#f8fafc;">'
            f'<div style="font-size:0.85rem;color:#64748b;">Retention Rate</div>'
            f'<div style="font-size:1.6rem;font-weight:700;">{retention_rate:.1f}%</div>'
            f'</div>'
            f'<div style="border:1px solid #e5e7eb;border-radius:12px;padding:12px;background:#f8fafc;">'
            f'<div style="font-size:0.85rem;color:#64748b;">vs Industry</div>'
            f'<div style="font-size:1.6rem;font-weight:700;">{vs_industry:+.1f}%</div>'
            f'</div>'
            f'<div style="border:1px solid #e5e7eb;border-radius:12px;padding:12px;background:#f8fafc;">'
            f'<div style="font-size:0.85rem;color:#64748b;">Annual Turnover Cost</div>'
            f'<div style="font-size:1.6rem;font-weight:700;">${estimated_annual_turnover_cost:,.0f}</div>'
            f'</div>'
            f'</div>'
            f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px;margin-top:16px;">'
            f'<section style="border:1px solid #e5e7eb;border-radius:12px;padding:12px;background:#fff;">'
            f'<h3 style="margin:0 0 8px 0;">Benchmarks</h3>'
            f'<ul style="margin:0;padding-left:18px;">'
            f'<li>Excellent: {benchmarks["excellent_threshold"]:.1f}%</li>'
            f'<li>Good: {benchmarks["good_threshold"]:.1f}%</li>'
            f'<li>Acceptable: {benchmarks["acceptable_threshold"]:.1f}%</li>'
            f'<li>Industry Avg: {benchmarks["industry_average"]:.1f}%</li>'
            f'</ul>'
            f'</section>'
            f'<section style="border:1px solid #e5e7eb;border-radius:12px;padding:12px;background:#fff;">'
            f'<h3 style="margin:0 0 8px 0;">Insights</h3>'
            f'<ul style="margin:0;padding-left:18px;">'
            f'<li>Risk Level: {risk_level}</li>'
            f'<li>Replacement Cost/Employee: ${replacement_cost_per_employee:,.0f}</li>'
            f'<li>Cost Savings Potential: ${additional_insights["cost_savings_potential"]:,.0f}</li>'
            f'<li>Strategy Priority: {additional_insights["retention_strategy_priority"]}</li>'
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
RESTAURANT CONSULTING REPORT — STAFF RETENTION ANALYSIS
Generated: {__import__('datetime').datetime.now().strftime('%B %d, %Y')}

PERFORMANCE RATING: {performance.upper()}

This staff retention analysis reveals {performance.lower()} turnover metrics with {risk_level.lower()} risk level compared to industry standards.

KEY PERFORMANCE METRICS
• Turnover Rate: {turnover_rate:.1f}%
• Retention Rate: {retention_rate:.1f}%
• Industry Average: {industry_average:.1f}%
• vs Industry: {vs_industry:+.1f}%
• Estimated Annual Cost: ${estimated_annual_turnover_cost:,.0f}

INDUSTRY BENCHMARKS
• Excellent Threshold: {benchmarks['excellent_threshold']:.1f}%
• Good Threshold: {benchmarks['good_threshold']:.1f}%
• Acceptable Threshold: {benchmarks['acceptable_threshold']:.1f}%
• Industry Average: {benchmarks['industry_average']:.1f}%

ADDITIONAL INSIGHTS
• Risk Level: {risk_level}
• Replacement Cost per Employee: ${replacement_cost_per_employee:,.0f}
• Cost Savings Potential: ${additional_insights['cost_savings_potential']:,.0f}
• Strategy Priority: {additional_insights['retention_strategy_priority']}

STRATEGIC RECOMMENDATIONS
{chr(10).join([f'{i+1}. {rec}' for i, rec in enumerate(recommendations)])}

END OF REPORT
        """.strip()

        # Prepare response data
        data = {
            "turnover_rate": turnover_rate,
            "retention_rate": retention_rate,
            "industry_average": industry_average,
            "vs_industry": vs_industry,
            "performance_rating": performance,
            "risk_level": risk_level,
            "estimated_annual_cost": estimated_annual_turnover_cost,
            "business_report_html": business_report_html,
            "business_report": business_report
        }

        insights = recommendations

        return success_payload(service, subtask, params, data, insights), 200

    except ValueError as e:
        return error_payload(service, subtask, str(e))
    except Exception as e:
        return error_payload(service, subtask, f"Internal error: {str(e)}", 500)
