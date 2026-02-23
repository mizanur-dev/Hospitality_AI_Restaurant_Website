"""
Strategic Analysis Functions
Contains the core business logic for strategic planning analysis.
"""

from backend.consulting_services.kpi.kpi_utils import format_business_report


def _fmt_money(value: float) -> str:
    try:
        return f"${float(value):,.2f}"
    except Exception:
        return f"${value}"


def _fmt_pct(value: float) -> str:
    try:
        return f"{float(value):.1f}%"
    except Exception:
        return f"{value}%"


def calculate_sales_forecasting_analysis(historical_sales, current_sales, growth_rate, seasonal_factor, forecast_periods=12.0, trend_strength=0.5, market_growth=5.0, confidence_level=85.0):
    """Calculate comprehensive sales forecasting analysis with business report."""
    # Calculate key metrics
    sales_growth = ((current_sales - historical_sales) / historical_sales * 100) if historical_sales > 0 else 0
    projected_sales = current_sales * (1 + growth_rate / 100) * seasonal_factor
    forecast_accuracy = min(100, confidence_level + (trend_strength * 10))

    # Calculate forecasting metrics
    trend_analysis = growth_rate * trend_strength
    market_alignment = min(100, (growth_rate / market_growth) * 100) if market_growth > 0 else 0
    seasonal_adjustment = abs(seasonal_factor - 1.0) * 100

    # Performance assessment
    if forecast_accuracy >= 90 and market_alignment >= 80 and sales_growth >= market_growth:
        rating = "Excellent"
    elif forecast_accuracy >= 80 and market_alignment >= 70 and sales_growth >= market_growth * 0.8:
        rating = "Good"
    elif forecast_accuracy >= 70 and market_alignment >= 60 and sales_growth >= market_growth * 0.6:
        rating = "Acceptable"
    else:
        rating = "Needs Improvement"

    # Metrics dictionary
    metrics = {
        "historical_sales": historical_sales,
        "current_sales": current_sales,
        "growth_rate": growth_rate,
        "seasonal_factor": seasonal_factor,
        "forecast_periods": forecast_periods,
        "trend_strength": trend_strength,
        "market_growth": market_growth,
        "confidence_level": confidence_level,
        "sales_growth": sales_growth,
        "projected_sales": projected_sales,
        "forecast_accuracy": forecast_accuracy,
        "trend_analysis": trend_analysis,
        "market_alignment": market_alignment,
        "seasonal_adjustment": seasonal_adjustment
    }

    # Performance dictionary
    performance = {
        "rating": rating,
        "forecast_status": "Accurate" if forecast_accuracy >= 85 else "Good" if forecast_accuracy >= 75 else "Needs Review",
        "growth_status": "Strong" if sales_growth >= market_growth else "Moderate" if sales_growth >= market_growth * 0.8 else "Weak"
    }

    # Generate recommendations (make them metric-driven and actionable)
    recommendations = []

    target_accuracy = 85.0
    target_market_alignment = 80.0
    target_seasonal_variance = 15.0

    if forecast_accuracy < target_accuracy:
        recommendations.append(
            f"Increase forecast accuracy from {_fmt_pct(forecast_accuracy)} toward {_fmt_pct(target_accuracy)} by using at least 12 months of weekly sales, tagging promos/holidays, and re-forecasting monthly."
        )
        recommendations.append(
            "Add a simple back-test: compare last month’s forecast vs actuals, then adjust assumptions (growth rate and seasonality) based on the error you see."
        )

    if market_alignment < target_market_alignment:
        recommendations.append(
            f"Your growth assumption ({_fmt_pct(growth_rate)}) is not well aligned to market growth ({_fmt_pct(market_growth)}). Revisit the growth rate or document the specific drivers (new capacity, new channels, pricing) that will close the gap."
        )
        recommendations.append(
            "Pressure-test the plan: list the top 2 competitor moves you expect and define a counter-move (offer, positioning, or channel) for each."
        )

    if seasonal_adjustment > target_seasonal_variance:
        recommendations.append(
            f"Seasonality is a meaningful driver (seasonal variance {_fmt_pct(seasonal_adjustment)}). Build a seasonal playbook: staffing plan, ordering levels, and menu/promo adjustments for peak vs slow periods."
        )
        recommendations.append(
            "Set reorder rules tied to forecasted volume (not just last week’s usage) to prevent over-ordering during slow weeks and stockouts during peaks."
        )

    if sales_growth < market_growth * 0.8:
        recommendations.append(
            f"Sales growth ({_fmt_pct(sales_growth)}) is lagging the market trend. Prioritize 1-2 penetration tactics (local partnerships, delivery platforms, loyalty reactivation) and track weekly conversion and repeat rate."
        )
        recommendations.append(
            "Run a pricing/offer review: test one small price move or bundle on your top sellers and measure volume and margin impact for 2-4 weeks."
        )

    if trend_strength < 0.6:
        recommendations.append(
            f"Trend signal is weak (trend strength {trend_strength:.2f}). Reduce reliance on a single growth rate and use a blended forecast (baseline + seasonal + event-driven adjustments)."
        )
        recommendations.append(
            "Capture a few drivers alongside sales (footfall, reservations, delivery orders, marketing spend) so the forecast is explainable and easier to improve."
        )

    if not recommendations:
        recommendations.append("Maintain current forecasting strategy")
        recommendations.append("Continue monitoring market trends and performance")

    # Industry benchmarks
    benchmarks = {
        "target_accuracy": "85%+ (higher is better; varies by data quality)",
        "market_growth_alignment": "80%+ (assumptions should match market unless you have clear growth drivers)",
        "seasonal_variance": "15% or less is easier to plan; higher requires a seasonal playbook",
    }

    # Additional insights
    additional_data = {
        "forecasting_insights": {
            "next_quarter_projection": f"${projected_sales:,.2f}",
            "confidence_interval": f"±{100 - confidence_level:.0f}%",
            "trend_direction": "Positive" if growth_rate > 0 else "Negative"
        },
        "performance_insights": {
            "forecast_trend": "Improving" if forecast_accuracy >= 85 else "Stable" if forecast_accuracy >= 75 else "Declining",
            "market_position": "Leading" if market_alignment >= 90 else "Competitive" if market_alignment >= 70 else "Lagging",
            "next_review": "30 days"
        }
    }

    # Generate business report
    business_report_result = format_business_report(
        "Sales Forecasting Analysis",
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


def calculate_growth_strategy_analysis(market_size, market_share, competition_level, investment_budget, growth_potential=15.0, competitive_advantage=7.0, market_penetration=5.0, roi_target=20.0):
    """Calculate comprehensive growth strategy analysis with business report."""
    # Calculate key metrics
    market_opportunity = market_size * (100 - market_share) / 100
    competitive_position = (competitive_advantage / 10) * 100
    growth_score = (growth_potential + competitive_advantage + market_penetration) / 3

    # Calculate strategy metrics
    market_penetration_potential = min(100, (market_opportunity / market_size) * 100) if market_size > 0 else 0
    # A more coherent investment metric: budget relative to the remaining market opportunity.
    # (The previous formula mixed % ROI with $ budget, which made the value meaningless.)
    investment_efficiency = (investment_budget / market_opportunity * 100) if market_opportunity > 0 else 0
    required_incremental_profit = investment_budget * (roi_target / 100) if investment_budget > 0 else 0
    # competition_level is expected on a 1–10 scale; map to a 0–100 threat score.
    competitive_threat = max(0, min(100, competition_level * 10))

    # Performance assessment
    if growth_score >= 8 and competitive_position >= 80 and market_penetration_potential >= 70:
        rating = "Excellent"
    elif growth_score >= 6 and competitive_position >= 70 and market_penetration_potential >= 50:
        rating = "Good"
    elif growth_score >= 4 and competitive_position >= 60 and market_penetration_potential >= 30:
        rating = "Acceptable"
    else:
        rating = "Needs Improvement"

    # Metrics dictionary
    metrics = {
        "market_size": market_size,
        "market_share": market_share,
        "competition_level": competition_level,
        "investment_budget": investment_budget,
        "growth_potential": growth_potential,
        "competitive_advantage": competitive_advantage,
        "market_penetration": market_penetration,
        "roi_target": roi_target,
        "market_opportunity": market_opportunity,
        "competitive_position": competitive_position,
        "growth_score": growth_score,
        "market_penetration_potential": market_penetration_potential,
        "investment_efficiency": investment_efficiency,
        "competitive_threat": competitive_threat
    }

    # Performance dictionary
    performance = {
        "rating": rating,
        "growth_status": "High" if growth_score >= 8 else "Medium" if growth_score >= 6 else "Low",
        "competitive_status": "Strong" if competitive_position >= 80 else "Moderate" if competitive_position >= 70 else "Weak"
    }

    # Generate recommendations (tie actions to the computed gaps)
    recommendations = []

    # Translate share points into an intuitive $ value.
    one_point_share_value = (market_size / 100) if market_size and market_size > 0 else 0

    if growth_score < 6:
        recommendations.append(
            f"Clarify the growth plan: pick one primary lever (new channels, higher check size, more visits) and set a 90-day target with leading indicators (traffic, conversion, repeat)."
        )
        recommendations.append(
            "Quantify your funnel: define the weekly lead sources (walk-in, delivery apps, catering, events) and assign an owner to each for consistent execution."
        )

    if competitive_position < 70:
        recommendations.append(
            f"Competitive position is moderate/weak ({_fmt_pct(competitive_position)}). Choose 1-2 differentiators (speed, signature items, experience, convenience) and align menu, pricing, and marketing around them."
        )
        recommendations.append(
            "Audit your top 3 competitors: compare price points, ratings, and key selling points; then adjust your offer where you can win profitably."
        )

    if market_penetration_potential < 50:
        if one_point_share_value > 0:
            recommendations.append(
                f"Market share is {_fmt_pct(market_share)} with remaining opportunity {_fmt_money(market_opportunity)}. As a reference, each +1 share point is roughly {_fmt_money(one_point_share_value)} in revenue at current market size."
            )
        recommendations.append(
            "Pick 1-2 customer segments to win (office lunch, families, late-night, catering) and build a segment-specific offer + channel plan (ads, partnerships, delivery listings, or events)."
        )

    if investment_budget > 0:
        recommendations.append(
            f"With an investment budget of {_fmt_money(investment_budget)} and ROI target {_fmt_pct(roi_target)}, you need about {_fmt_money(required_incremental_profit)} incremental profit to hit the target. Define the exact initiatives that will generate it."
        )
    if investment_efficiency < 1:
        recommendations.append(
            f"Investment intensity is low relative to the opportunity ({_fmt_pct(investment_efficiency)} of the remaining market). If growth expectations are high, either increase budget or narrow focus to the highest-ROI segment/channel."
        )

    if competitive_threat > 70:
        recommendations.append(
            "Competitive pressure is high. Set a monthly cadence to review competitor pricing/promos and protect your top sellers with clear value messaging and consistent execution."
        )
        recommendations.append(
            "Build a defensive plan: lock in 3 core items (quality + speed + availability) and create a simple retention tactic (loyalty offer, SMS reactivation, or subscription)."
        )

    if not recommendations:
        recommendations.append("Maintain current growth strategy")
        recommendations.append("Continue monitoring market opportunities")

    # Industry benchmarks
    benchmarks = {
        "target_growth_score": "8.0+ (strong growth readiness)",
        "competitive_threshold": "80%+ (clear differentiation)",
        "market_penetration_goal": "50–70% (depends on category maturity and competition)",
    }

    # Additional insights
    additional_data = {
        "growth_opportunities": {
            "market_opportunity_value": f"${market_opportunity:,.2f}",
            "penetration_potential": f"{market_penetration_potential:.1f}%",
            "investment_roi": f"{roi_target:.1f}%"
        },
        "performance_insights": {
            "growth_trend": "Accelerating" if growth_score >= 8 else "Stable" if growth_score >= 6 else "Slowing",
            "competitive_trend": "Strengthening" if competitive_position >= 80 else "Stable" if competitive_position >= 70 else "Weakening",
            "next_review": "90 days"
        }
    }

    # Generate business report
    business_report_result = format_business_report(
        "Growth Strategy Analysis",
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


def calculate_operational_excellence_analysis(efficiency_score, process_time, quality_rating, customer_satisfaction, cost_per_unit=0.0, waste_percentage=0.0, employee_productivity=8.0, benchmark_score=85.0):
    """Calculate comprehensive operational excellence analysis with business report."""
    # Calculate key metrics
    operational_score = (efficiency_score + quality_rating + customer_satisfaction) / 3
    process_efficiency = (benchmark_score / process_time) if process_time > 0 else 0
    cost_efficiency = (100 - waste_percentage) * (efficiency_score / 10)

    # Calculate excellence metrics
    productivity_index = (employee_productivity / 10) * 100
    quality_index = (quality_rating / 10) * 100
    customer_index = (customer_satisfaction / 10) * 100
    excellence_score = (operational_score + productivity_index + quality_index + customer_index) / 4

    # Performance assessment
    if excellence_score >= 85 and process_efficiency >= 80 and cost_efficiency >= 75:
        rating = "Excellent"
    elif excellence_score >= 75 and process_efficiency >= 70 and cost_efficiency >= 65:
        rating = "Good"
    elif excellence_score >= 65 and process_efficiency >= 60 and cost_efficiency >= 55:
        rating = "Acceptable"
    else:
        rating = "Needs Improvement"

    # Metrics dictionary
    metrics = {
        "efficiency_score": efficiency_score,
        "process_time": process_time,
        "quality_rating": quality_rating,
        "customer_satisfaction": customer_satisfaction,
        "cost_per_unit": cost_per_unit,
        "waste_percentage": waste_percentage,
        "employee_productivity": employee_productivity,
        "benchmark_score": benchmark_score,
        "operational_score": operational_score,
        "process_efficiency": process_efficiency,
        "cost_efficiency": cost_efficiency,
        "productivity_index": productivity_index,
        "quality_index": quality_index,
        "customer_index": customer_index,
        "excellence_score": excellence_score
    }

    # Performance dictionary
    performance = {
        "rating": rating,
        "efficiency_status": "High" if efficiency_score >= 8 else "Medium" if efficiency_score >= 6 else "Low",
        "quality_status": "High" if quality_rating >= 8 else "Medium" if quality_rating >= 6 else "Low"
    }

    # Generate recommendations (explicit, operations-focused)
    recommendations = []

    excellence_target = 85.0

    if excellence_score < 75:
        recommendations.append(
            f"Excellence score is {excellence_score:.1f} (target ~{excellence_target:.0f}+). Start with a 2-week process audit: map the top 3 bottlenecks and remove one constraint at a time."
        )
        recommendations.append(
            "Create a weekly ops scoreboard (speed of service, waste %, guest satisfaction, rework/comped items) and review it with managers every week."
        )

    if process_efficiency < 70:
        recommendations.append(
            f"Process efficiency is below goal ({process_efficiency:.1f}). Standardize the busiest workflows with checklists and station setup (mise en place) to reduce delays."
        )
        recommendations.append(
            "Measure cycle time for 10 peak orders, remove the slowest step, and retest—repeat weekly until stable."
        )

    if cost_efficiency < 65:
        recommendations.append(
            f"Cost efficiency suggests avoidable loss. With waste at {_fmt_pct(waste_percentage)}, set a weekly waste reduction target and track the top 5 waste reasons (prep errors, spoilage, returns)."
        )
        recommendations.append(
            "Tighten purchasing controls: set par levels, enforce FIFO, and verify vendor price changes monthly."
        )

    if productivity_index < 70:
        recommendations.append(
            f"Productivity index is {_fmt_pct(productivity_index)}. Cross-train for flexible scheduling and reduce handoffs during peak periods."
        )
        recommendations.append(
            "Set clear shift goals (tickets/hour or tasks/hour) and coach to them with short daily pre-shift huddles."
        )

    if quality_index < 80:
        recommendations.append(
            f"Quality index is {_fmt_pct(quality_index)}. Add 2 quality checkpoints (line check + final plate check) during peak hours to reduce rework."
        )
        recommendations.append(
            "Standardize recipes and portioning tools (scales, scoops) to improve consistency and protect margins."
        )

    if customer_index < 85:
        recommendations.append(
            f"Customer satisfaction index is {_fmt_pct(customer_index)}. Fix the top 2 service issues first (speed, accuracy, cleanliness) and verify improvement weekly."
        )
        recommendations.append(
            "Add a lightweight feedback loop: QR survey or receipt link, review comments weekly, and close the loop with 1 visible improvement per month."
        )

    if not recommendations:
        recommendations.append("Maintain current operational excellence standards")
        recommendations.append("Continue monitoring performance metrics")

    # Industry benchmarks
    benchmarks = {
        "excellence_threshold": "~85%+ (healthy operations)",
        "process_efficiency_goal": "70–85+ (depends on concept and service style)",
        "quality_standard": "80–90+ (consistent execution)",
    }

    # Additional insights
    additional_data = {
        "operational_insights": {
            "efficiency_gap": f"{benchmark_score - excellence_score:.1f} points",
            "improvement_potential": f"${cost_per_unit * (100 - cost_efficiency) / 100:.2f}",
            "productivity_trend": "Improving" if productivity_index >= 80 else "Stable" if productivity_index >= 70 else "Declining"
        },
        "performance_insights": {
            "excellence_trend": "Improving" if excellence_score >= 85 else "Stable" if excellence_score >= 75 else "Declining",
            "quality_trend": "High" if quality_index >= 90 else "Medium" if quality_index >= 80 else "Low",
            "next_review": "60 days"
        }
    }

    # Generate business report
    business_report_result = format_business_report(
        "Operational Excellence Analysis",
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
