"""
KPI Dashboard Analysis Functions
Contains the core business logic for KPI dashboard analysis.
"""

from backend.consulting_services.kpi.kpi_utils import format_business_report


def calculate_comprehensive_analysis(total_sales, labor_cost, food_cost, prime_cost, hours_worked=0.0, hourly_rate=0.0, previous_sales=0.0, target_margin=70.0):
    """Calculate comprehensive analysis with multi-metric analysis and industry benchmarking."""
    # Calculate key metrics
    total_costs = labor_cost + food_cost
    prime_cost_percentage = (total_costs / total_sales * 100) if total_sales > 0 else 0
    labor_percentage = (labor_cost / total_sales * 100) if total_sales > 0 else 0
    food_percentage = (food_cost / total_sales * 100) if total_sales > 0 else 0

    # Calculate efficiency metrics
    sales_per_hour = total_sales / hours_worked if hours_worked > 0 else 0
    labor_efficiency = (total_sales / labor_cost) if labor_cost > 0 else 0
    cost_efficiency = (total_sales / total_costs) if total_costs > 0 else 0

    # Calculate growth metrics
    sales_growth = ((total_sales - previous_sales) / previous_sales * 100) if previous_sales > 0 else 0
    performance_score = (target_margin - prime_cost_percentage) / target_margin * 100 if target_margin > 0 else 0

    # Performance assessment
    if prime_cost_percentage <= 60 and performance_score >= 80 and sales_growth >= 10:
        rating = "Excellent"
    elif prime_cost_percentage <= 65 and performance_score >= 70 and sales_growth >= 5:
        rating = "Good"
    elif prime_cost_percentage <= 70 and performance_score >= 60 and sales_growth >= 0:
        rating = "Acceptable"
    else:
        rating = "Needs Improvement"

    # Metrics dictionary
    metrics = {
        "total_sales": total_sales,
        "labor_cost": labor_cost,
        "food_cost": food_cost,
        "prime_cost": prime_cost,
        "hours_worked": hours_worked,
        "hourly_rate": hourly_rate,
        "previous_sales": previous_sales,
        "target_margin": target_margin,
        "total_costs": total_costs,
        "prime_cost_percentage": prime_cost_percentage,
        "labor_percentage": labor_percentage,
        "food_percentage": food_percentage,
        "sales_per_hour": sales_per_hour,
        "labor_efficiency": labor_efficiency,
        "cost_efficiency": cost_efficiency,
        "sales_growth": sales_growth,
        "performance_score": performance_score
    }

    # Performance dictionary
    performance = {
        "rating": rating,
        "cost_status": "Optimal" if prime_cost_percentage <= 60 else "Good" if prime_cost_percentage <= 65 else "Needs Review",
        "efficiency_status": "High" if performance_score >= 80 else "Medium" if performance_score >= 70 else "Low"
    }

    # Generate recommendations
    recommendations = []

    if prime_cost_percentage > 65:
        prime_gap_pts = max(prime_cost_percentage - 60, 0)
        est_savings = (prime_gap_pts / 100) * total_sales
        recommendations.append(
            f"Prime cost is {prime_cost_percentage:.1f}% (ideal ≤60%). Closing the {prime_gap_pts:.1f}-pt gap is worth ~${est_savings:,.0f} on current sales."
        )
        recommendations.append(
            f"Prioritize the biggest driver: labor {labor_percentage:.1f}% and food {food_percentage:.1f}%. Set weekly targets and review variances by daypart."
        )

    if labor_percentage > 35:
        labor_gap_pts = max(labor_percentage - 30, 0)
        est_savings = (labor_gap_pts / 100) * total_sales
        recommendations.append(
            f"Labor is {labor_percentage:.1f}% (goal ~30%). That's +{labor_gap_pts:.1f} pts; ~${est_savings:,.0f} opportunity on current sales via schedule-to-sales and overtime control."
        )
        recommendations.append("Use forecast-based schedules, enforce shift-extension approvals, and cross-train to flex coverage without adding hours.")

    if food_percentage > 35:
        food_gap_pts = max(food_percentage - 30, 0)
        est_savings = (food_gap_pts / 100) * total_sales
        recommendations.append(
            f"Food is {food_percentage:.1f}% (goal ~30%). That's +{food_gap_pts:.1f} pts; ~${est_savings:,.0f} opportunity on current sales via portion control, waste reduction, and recipe-cost refresh."
        )
        recommendations.append("Re-cost top-selling items to current ingredient prices and adjust pricing/mix to protect margins.")

    if sales_per_hour < 100:
        if hours_worked > 0:
            sph_gap = 100 - sales_per_hour
            est_sales_uplift = sph_gap * hours_worked if sph_gap > 0 else 0
            recommendations.append(
                f"Sales per hour is ${sales_per_hour:.2f} (target ~$100+). Closing the ${sph_gap:.0f}/hr gap could add ~${est_sales_uplift:,.0f} sales at current hours."
            )
        recommendations.append("Focus on speed-of-service and check-average levers (add-ons, bundles, suggestive selling) before adding labor hours.")

    if sales_growth < 5:
        if previous_sales > 0:
            target_growth = 10.0
            target_sales = previous_sales * (1 + target_growth / 100)
            sales_gap = max(target_sales - total_sales, 0)
            recommendations.append(
                f"Sales growth is {sales_growth:.1f}% (target ~{target_growth:.0f}%). You need about ${sales_gap:,.0f} more sales (vs prior period baseline) to reach target."
            )
        recommendations.append("Build a short growth plan: retention (repeat offers), acquisition (local ads/partners), and peak-time capacity to capture demand.")

    if performance_score < 70:
        recommendations.append(
            f"Overall score is {performance_score:.1f}/100. Set 2–3 weekly targets (prime %, SPLH, waste) and review results on a fixed cadence to prevent drift."
        )
        recommendations.append("Assign owners for labor scheduling, purchasing/recipe costing, and sales training so actions translate into KPI movement.")

    if not recommendations:
        recommendations.append("Maintain current performance levels")
        recommendations.append("Continue monitoring key performance indicators")

    # Industry benchmarks
    benchmarks = {
        "optimal_prime_cost": "≤60%",
        "target_labor_cost": "≤30%",
        "target_food_cost": "≤30%",
        "sales_growth_target": "≥10%"
    }

    # Additional insights
    additional_data = {
        "comprehensive_insights": {
            "overall_score": f"{performance_score:.1f}/100",
            "cost_optimization_potential": f"${total_costs * 0.1:.2f}",
            "efficiency_rating": "High" if performance_score >= 80 else "Medium" if performance_score >= 70 else "Low"
        },
        "performance_insights": {
            "trend_direction": "Improving" if sales_growth >= 10 else "Stable" if sales_growth >= 5 else "Declining",
            "benchmark_comparison": "Above Industry" if performance_score >= 80 else "Industry Average" if performance_score >= 70 else "Below Industry",
            "next_review": "30 days"
        }
    }

    # Generate business report
    business_report_result = format_business_report(
        "Comprehensive Analysis",
        metrics,
        performance,
        recommendations,
        benchmarks,
        additional_data
    )

    business_report_html = business_report_result.get("business_report_html", "")
    business_report = business_report_result.get("business_report", "")

    return {
        "metrics": metrics,
        "performance": performance,
        "recommendations": recommendations,
        "industry_benchmarks": benchmarks,
        "business_report_html": business_report_html,
        "business_report": business_report
    }


def calculate_performance_optimization(current_performance, target_performance, optimization_potential, efficiency_score, baseline_metrics=0.0, improvement_rate=10.0, goal_timeframe=90.0, progress_tracking=8.0):
    """Calculate performance optimization with actionable recommendations and goal setting."""
    # Calculate key metrics
    performance_gap = target_performance - current_performance
    optimization_score = (optimization_potential / 100) * (efficiency_score / 10)
    improvement_potential = (performance_gap / current_performance * 100) if current_performance > 0 else 0

    # Calculate optimization metrics
    goal_achievement_rate = (current_performance / target_performance * 100) if target_performance > 0 else 0
    efficiency_rating = (efficiency_score / 10) * 100
    progress_score = (progress_tracking / 10) * 100
    overall_optimization_score = (optimization_score + efficiency_rating + progress_score) / 3

    # Performance assessment
    if overall_optimization_score >= 85 and goal_achievement_rate >= 90 and improvement_potential >= 15:
        rating = "Excellent"
    elif overall_optimization_score >= 75 and goal_achievement_rate >= 80 and improvement_potential >= 10:
        rating = "Good"
    elif overall_optimization_score >= 65 and goal_achievement_rate >= 70 and improvement_potential >= 5:
        rating = "Acceptable"
    else:
        rating = "Needs Improvement"

    # Metrics dictionary
    metrics = {
        "current_performance": current_performance,
        "target_performance": target_performance,
        "optimization_potential": optimization_potential,
        "efficiency_score": efficiency_score,
        "baseline_metrics": baseline_metrics,
        "improvement_rate": improvement_rate,
        "goal_timeframe": goal_timeframe,
        "progress_tracking": progress_tracking,
        "performance_gap": performance_gap,
        "optimization_score": optimization_score,
        "improvement_potential": improvement_potential,
        "goal_achievement_rate": goal_achievement_rate,
        "efficiency_rating": efficiency_rating,
        "progress_score": progress_score,
        "overall_optimization_score": overall_optimization_score
    }

    # Performance dictionary
    performance = {
        "rating": rating,
        "optimization_status": "High" if overall_optimization_score >= 85 else "Medium" if overall_optimization_score >= 75 else "Low",
        "goal_status": "On Track" if goal_achievement_rate >= 90 else "Behind" if goal_achievement_rate >= 70 else "At Risk"
    }

    # Generate recommendations
    recommendations = []

    if overall_optimization_score < 75:
        recommendations.append(
            f"Optimization score is {overall_optimization_score:.0f}% (target 75%+). Prioritize the lowest levers: efficiency {efficiency_rating:.0f}%, tracking {progress_score:.0f}%, and goal progress {goal_achievement_rate:.0f}%."
        )
        recommendations.append("Pick 3 operational changes for the next 14 days and measure impact weekly (labor %, food %, SPLH, waste).")

    if goal_achievement_rate < 80:
        recommendations.append(
            f"You are at {goal_achievement_rate:.0f}% of target. Close the gap of {performance_gap:,.2f} within ~{goal_timeframe:.0f} days using targeted initiatives tied to KPI owners."
        )
        recommendations.append("Break the target into weekly milestones and review progress every 7 days.")

    if improvement_potential < 10:
        recommendations.append(
            f"Improvement headroom is {improvement_potential:.1f}%. Look for new levers (menu mix, supplier terms, staffing model, throughput constraints) to unlock additional gains."
        )

    if efficiency_rating < 70:
        recommendations.append(
            f"Efficiency rating is {efficiency_rating:.0f}%. Standardize workflows (prep, line, service steps) and run short training cycles to improve consistency and throughput."
        )

    if progress_tracking < 7:
        recommendations.append(
            f"Progress tracking is {progress_tracking:.1f}/10. Set up a weekly KPI dashboard review with owners, actions, and due dates to maintain momentum."
        )

    if performance_gap > current_performance * 0.2:
        recommendations.append(
            f"Performance gap is large relative to current level. Create a milestone plan (every 2 weeks) that closes at least {(performance_gap/goal_timeframe):.2f} units/day on average over the next {goal_timeframe:.0f} days."
        )

    if not recommendations:
        recommendations.append("Maintain current optimization strategies")
        recommendations.append("Continue monitoring performance improvements")

    # Industry benchmarks
    benchmarks = {
        "target_optimization_score": "≥85%",
        "goal_achievement_threshold": "≥90%",
        "improvement_potential_target": "≥15%"
    }

    # Additional insights
    additional_data = {
        "optimization_insights": {
            "improvement_timeline": f"{goal_timeframe:.0f} days",
            "potential_gain": f"{improvement_potential:.1f}%",
            "optimization_priority": "High" if overall_optimization_score < 75 else "Medium" if overall_optimization_score < 85 else "Low"
        },
        "performance_insights": {
            "optimization_trend": "Improving" if overall_optimization_score >= 85 else "Stable" if overall_optimization_score >= 75 else "Declining",
            "goal_progress": "On Track" if goal_achievement_rate >= 90 else "Behind" if goal_achievement_rate >= 70 else "At Risk",
            "next_review": "30 days"
        }
    }

    # Generate business report
    business_report_result = format_business_report(
        "Performance Optimization Analysis",
        metrics,
        performance,
        recommendations,
        benchmarks,
        additional_data
    )

    business_report_html = business_report_result.get("business_report_html", "")
    business_report = business_report_result.get("business_report", "")

    return {
        "metrics": metrics,
        "performance": performance,
        "recommendations": recommendations,
        "industry_benchmarks": benchmarks,
        "business_report_html": business_report_html,
        "business_report": business_report
    }
