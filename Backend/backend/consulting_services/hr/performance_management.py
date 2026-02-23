"""
HR Performance Management Analysis Task
Analyzes staff performance metrics and provides improvement strategies with comprehensive business report.
"""

from backend.shared.utils.common import success_payload, error_payload, require, validate_positive_numbers


def run(params: dict, file_bytes: bytes | None = None) -> tuple[dict, int]:
    """
    Calculate performance management analysis with comprehensive business report.

    Args:
        params: Dictionary containing performance metrics and optional targets
        file_bytes: Optional file data (not used in this task)

    Returns:
        Tuple of (response_dict, status_code)
    """
    service, subtask = "hr", "performance_management"

    try:
        # Validate required fields - at least one performance metric required
        if not any(key in params for key in ["customer_satisfaction", "sales_performance", "efficiency_score", "attendance_rate"]):
            return error_payload(service, subtask, "At least one performance metric is required")

        # Extract and convert values with defaults
        customer_satisfaction = float(params.get("customer_satisfaction", 85.0))
        sales_performance = float(params.get("sales_performance", 100.0))  # Percentage of target
        efficiency_score = float(params.get("efficiency_score", 80.0))
        attendance_rate = float(params.get("attendance_rate", 95.0))

        # Optional targets
        customer_satisfaction_target = float(params.get("customer_satisfaction_target", 90.0))
        sales_performance_target = float(params.get("sales_performance_target", 100.0))
        efficiency_target = float(params.get("efficiency_target", 85.0))
        attendance_target = float(params.get("attendance_target", 98.0))

        # Validate ranges
        for metric, value in [
            ("customer_satisfaction", customer_satisfaction),
            ("sales_performance", sales_performance),
            ("efficiency_score", efficiency_score),
            ("attendance_rate", attendance_rate)
        ]:
            if not 0 <= value <= 100:
                raise ValueError(f"{metric} must be between 0 and 100")

        # Calculate overall performance score (weighted average)
        weights = {
            "customer_satisfaction": 0.3,
            "sales_performance": 0.3,
            "efficiency_score": 0.25,
            "attendance_rate": 0.15
        }

        overall_score = (
            customer_satisfaction * weights["customer_satisfaction"] +
            sales_performance * weights["sales_performance"] +
            efficiency_score * weights["efficiency_score"] +
            attendance_rate * weights["attendance_rate"]
        )

        # Performance assessment
        if overall_score >= 90:
            performance = "Excellent"
            performance_color = "green"
        elif overall_score >= 80:
            performance = "Good"
            performance_color = "blue"
        elif overall_score >= 70:
            performance = "Acceptable"
            performance_color = "yellow"
        else:
            performance = "Needs Improvement"
            performance_color = "red"

        # Individual metric assessments
        metric_assessments = {}
        for metric, value, target in [
            ("customer_satisfaction", customer_satisfaction, customer_satisfaction_target),
            ("sales_performance", sales_performance, sales_performance_target),
            ("efficiency_score", efficiency_score, efficiency_target),
            ("attendance_rate", attendance_rate, attendance_target)
        ]:
            if value >= target:
                metric_assessments[metric] = "Meets Target"
            elif value >= target * 0.9:
                metric_assessments[metric] = "Close to Target"
            else:
                metric_assessments[metric] = "Below Target"

        # Calculate improvement potential
        improvement_potential = {}
        for metric, value, target in [
            ("customer_satisfaction", customer_satisfaction, customer_satisfaction_target),
            ("sales_performance", sales_performance, sales_performance_target),
            ("efficiency_score", efficiency_score, efficiency_target),
            ("attendance_rate", attendance_rate, attendance_target)
        ]:
            improvement_potential[metric] = max(0, target - value)

        # Generate recommendations
        recommendations = []

        if customer_satisfaction < customer_satisfaction_target:
            recommendations.append(f"Improve customer satisfaction by {improvement_potential['customer_satisfaction']:.1f} points through staff training")
            recommendations.append("Implement customer feedback collection and response system")
            recommendations.append("Focus on service speed and quality during peak hours")

        if sales_performance < sales_performance_target:
            recommendations.append(f"Enhance sales performance by {improvement_potential['sales_performance']:.1f}% through upselling training")
            recommendations.append("Implement sales incentive programs for staff")
            recommendations.append("Provide product knowledge training to improve recommendations")

        if efficiency_score < efficiency_target:
            recommendations.append(f"Boost efficiency score by {improvement_potential['efficiency_score']:.1f} points through process optimization")
            recommendations.append("Implement time management training for staff")
            recommendations.append("Review and streamline operational procedures")

        if attendance_rate < attendance_target:
            recommendations.append(f"Increase attendance rate by {improvement_potential['attendance_rate']:.1f}% through engagement initiatives")
            recommendations.append("Implement flexible scheduling options")
            recommendations.append("Address workplace satisfaction and recognition programs")

        # General recommendations
        if overall_score >= 90:
            recommendations.append("Maintain excellent performance - continue current management practices")
            recommendations.append("Share best practices with other locations or teams")
        elif overall_score < 70:
            recommendations.append("Implement comprehensive performance improvement plan")
            recommendations.append("Consider additional training and development programs")
            recommendations.append("Review management and leadership approaches")

        recommendations.append("Establish regular performance review cycles")
        recommendations.append("Create individual development plans for each team member")

        # Prepare data for business report
        metrics = {
            "overall_score": round(overall_score, 1),
            "customer_satisfaction": customer_satisfaction,
            "sales_performance": sales_performance,
            "efficiency_score": efficiency_score,
            "attendance_rate": attendance_rate
        }

        performance_data = {
            "rating": performance,
            "color": performance_color,
            "overall_score": round(overall_score, 1)
        }

        benchmarks = {
            "excellent_threshold": 90.0,
            "good_threshold": 80.0,
            "acceptable_threshold": 70.0,
            "customer_satisfaction_target": customer_satisfaction_target,
            "sales_performance_target": sales_performance_target,
            "efficiency_target": efficiency_target,
            "attendance_target": attendance_target
        }

        additional_insights = {
            "metric_assessments": metric_assessments,
            "improvement_potential": improvement_potential,
            "performance_trend": "Improving" if overall_score >= 80 else "Stable" if overall_score >= 70 else "Declining",
            "training_priority": "High" if overall_score < 70 else "Medium" if overall_score < 80 else "Low",
            "management_focus": "Critical" if overall_score < 70 else "Important" if overall_score < 80 else "Maintain"
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
        onboarding_items = [
            f'Attendance Rate: {attendance_rate:.1f}% (Target: {attendance_target:.1f}%)',
            f'Customer Satisfaction: {customer_satisfaction:.1f}% (Target: {customer_satisfaction_target:.1f}%)',
            'Focus onboarding on service standards, expectations, and role clarity'
        ]
        if attendance_rate < attendance_target:
            onboarding_items.append('Reduce early absenteeism with tighter onboarding schedules and manager check-ins')
        if customer_satisfaction < customer_satisfaction_target:
            onboarding_items.append('Add service recovery drills to onboarding to lift guest satisfaction')

        skill_dev_items = [
            f'Sales Performance: {sales_performance:.1f}% (Target: {sales_performance_target:.1f}%)',
            f'Efficiency Score: {efficiency_score:.1f}% (Target: {efficiency_target:.1f}%)',
            'Prioritize product knowledge, upselling, and speed of service training'
        ]
        if sales_performance < sales_performance_target:
            skill_dev_items.append('Run weekly upsell coaching and role-play sessions')
        if efficiency_score < efficiency_target:
            skill_dev_items.append('Coach station setup, prep sequencing, and time-management routines')

        performance_tracking_items = [
            f'Overall Score: {overall_score:.1f}% ({performance})',
            f'Performance Trend: {additional_insights["performance_trend"]}',
            f'Training Priority: {additional_insights["training_priority"]}',
            f'Management Focus: {additional_insights["management_focus"]}'
        ]

        onboarding_html = ''.join([f'<li>{item}</li>' for item in onboarding_items])
        skill_dev_html = ''.join([f'<li>{item}</li>' for item in skill_dev_items])
        performance_tracking_html = ''.join([f'<li>{item}</li>' for item in performance_tracking_items])

        business_report_html = (
            f'<section class="report" style="border:1px solid #e5e7eb;border-radius:16px;overflow:hidden;background:#fff;box-shadow:0 10px 30px rgba(0,0,0,0.06);">'
            f'<header class="report__header" style="background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;padding:20px;">'
            f'<h2 style="margin:0 0 6px 0;">Training Programs Analysis</h2>'
            f'<div class="report__meta" style="opacity:0.9;">Generated: {__import__("datetime").datetime.now().strftime("%B %d, %Y")}</div>'
            f'<div class="badge badge--{performance.lower().replace(" ", "-")}" style="margin-top:8px;display:inline-block;background:rgba(255,255,255,0.2);padding:4px 10px;border-radius:999px;">{performance}</div>'
            f'</header>'
            f'<article class="report__body" style="padding:20px;">'
            f'<p class="lead" style="margin:0 0 14px 0;">This training program review summarizes <strong>{performance.lower()}</strong> performance with an overall score of <strong>{overall_score:.1f}%</strong>.</p>'
            f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;">'
            f'<section style="border:1px solid #e5e7eb;border-radius:12px;padding:14px;background:#f9fafb;">'
            f'<h3 style="margin:0 0 8px 0;">Onboarding Optimization</h3>'
            f'<ul style="margin:0;padding-left:18px;">{onboarding_html}</ul>'
            f'</section>'
            f'<section style="border:1px solid #e5e7eb;border-radius:12px;padding:14px;background:#f9fafb;">'
            f'<h3 style="margin:0 0 8px 0;">Skill Development</h3>'
            f'<ul style="margin:0;padding-left:18px;">{skill_dev_html}</ul>'
            f'</section>'
            f'<section style="border:1px solid #e5e7eb;border-radius:12px;padding:14px;background:#f9fafb;">'
            f'<h3 style="margin:0 0 8px 0;">Performance Tracking</h3>'
            f'<ul style="margin:0;padding-left:18px;">{performance_tracking_html}</ul>'
            f'</section>'
            f'</div>'
            f'<h3 style="margin:18px 0 8px 0;">Strategic Recommendations</h3>'
            f'<ol style="margin:0;padding-left:18px;">{recs_html}</ol>'
            f'</article>'
            f'</section>'
        )

        # Generate text business report
        business_report = f"""
RESTAURANT CONSULTING REPORT — PERFORMANCE MANAGEMENT ANALYSIS
Generated: {__import__('datetime').datetime.now().strftime('%B %d, %Y')}

PERFORMANCE RATING: {performance.upper()}

This training programs analysis reveals {performance.lower()} overall performance with a score of {overall_score:.1f}%.

KEY PERFORMANCE METRICS
• Overall Score: {overall_score:.1f}%
• Customer Satisfaction: {customer_satisfaction:.1f}% (Target: {customer_satisfaction_target:.1f}%)
• Sales Performance: {sales_performance:.1f}% (Target: {sales_performance_target:.1f}%)
• Efficiency Score: {efficiency_score:.1f}% (Target: {efficiency_target:.1f}%)
• Attendance Rate: {attendance_rate:.1f}% (Target: {attendance_target:.1f}%)

PERFORMANCE BENCHMARKS
• Excellent Threshold: {benchmarks['excellent_threshold']:.1f}%
• Good Threshold: {benchmarks['good_threshold']:.1f}%
• Acceptable Threshold: {benchmarks['acceptable_threshold']:.1f}%

METRIC ASSESSMENTS
• Customer Satisfaction: {metric_assessments['customer_satisfaction']}
• Sales Performance: {metric_assessments['sales_performance']}
• Efficiency Score: {metric_assessments['efficiency_score']}
• Attendance Rate: {metric_assessments['attendance_rate']}

ADDITIONAL INSIGHTS
• Performance Trend: {additional_insights['performance_trend']}
• Training Priority: {additional_insights['training_priority']}
• Management Focus: {additional_insights['management_focus']}

STRATEGIC RECOMMENDATIONS
{chr(10).join([f'{i+1}. {rec}' for i, rec in enumerate(recommendations)])}

END OF REPORT
        """.strip()

        # Prepare response data
        data = {
            "overall_score": overall_score,
            "customer_satisfaction": customer_satisfaction,
            "sales_performance": sales_performance,
            "efficiency_score": efficiency_score,
            "attendance_rate": attendance_rate,
            "performance_rating": performance,
            "metric_assessments": metric_assessments,
            "improvement_potential": improvement_potential,
            "business_report_html": business_report_html,
            "business_report": business_report
        }

        insights = recommendations

        return success_payload(service, subtask, params, data, insights), 200

    except ValueError as e:
        return error_payload(service, subtask, str(e))
    except Exception as e:
        return error_payload(service, subtask, f"Internal error: {str(e)}", 500)
