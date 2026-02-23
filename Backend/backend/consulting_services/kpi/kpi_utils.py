"""
Performance Management Module
Handles KPI tracking, analytics, and performance reporting
"""

from typing import Any, Dict, List, Optional
import os
import json

import pandas as pd
from datetime import datetime
from backend.shared.utils.business_report import format_comprehensive_analysis


def generate_ai_kpi_analysis(
    total_sales: float,
    avg_labor_percent: float,
    avg_food_percent: float,
    avg_prime_percent: float,
    avg_sales_per_hour: float,
    trend: str,
    num_days: int,
    daily_data: List[Dict] = None
) -> Optional[str]:
    """
    Generate AI-powered KPI analysis using OpenAI GPT-4.
    
    Args:
        total_sales: Total sales for the period
        avg_labor_percent: Average labor cost percentage
        avg_food_percent: Average food cost percentage
        avg_prime_percent: Average prime cost percentage
        avg_sales_per_hour: Average sales per labor hour
        trend: Performance trend (improving, declining, stable)
        num_days: Number of days analyzed
        daily_data: Sample of daily KPI data for pattern analysis
        
    Returns:
        AI-generated analysis string or None if unavailable
    """
    try:
        from openai import OpenAI
        from dotenv import load_dotenv
        load_dotenv()
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None
            
        client = OpenAI(api_key=api_key)
        
        # Build context for AI analysis
        daily_summary = ""
        if daily_data:
            daily_summary = "\nDaily Data Sample:\n"
            for day in daily_data[:5]:
                daily_summary += f"- {day.get('date', 'N/A')}: Sales ${day.get('sales', 0):,.0f}, Labor {day.get('labor_percent', 0):.1f}%, Food {day.get('food_percent', 0):.1f}%\n"
        
        prompt = f"""As a restaurant business consultant, analyze these KPIs and provide strategic insights:

Period Analyzed: {num_days} days
Total Sales: ${total_sales:,.2f}
Average Labor Cost: {avg_labor_percent:.1f}% (industry benchmark is 25-30%)
Average Food Cost: {avg_food_percent:.1f}% (industry benchmark is 28-32%)
Average Prime Cost: {avg_prime_percent:.1f}% (industry benchmark is 55-60%)
Sales per Labor Hour: ${avg_sales_per_hour:.2f} (industry benchmark is $50+)
Performance Trend: {trend}
{daily_summary}

IMPORTANT FORMATTING RULES:
- Write in plain, natural English without any markdown or special formatting
- Do NOT use asterisks, bold markers, or hash symbols
- Do NOT use LaTeX or mathematical notation like backslash commands
- Write formulas in plain words: "Labor Cost Percentage equals Labor Cost divided by Total Sales, times 100"
- Use simple numbered lists (1. 2. 3.) or dashes (-) for lists
- Write like you're having a friendly conversation with a restaurant owner

Provide a helpful analysis including:
1. Executive Summary - overall performance and key findings
2. Critical Issues - metrics outside industry benchmarks
3. Quick Wins - immediate actions to improve performance
4. Strategic Recommendations - longer term improvements
5. Projected Impact - estimated savings if recommendations are implemented

Keep the response practical and conversational for restaurant operators."""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": """You are an expert restaurant consultant with 20+ years of experience in hospitality operations. You specialize in KPI analysis, cost control, operational efficiency, and strategic business optimization.

CRITICAL FORMATTING RULES - YOU MUST FOLLOW THESE:
1. NEVER use markdown formatting (no asterisks, no bold markers like **, no hash symbols like ##)
2. NEVER use LaTeX or mathematical notation (no \\text{}, no \\frac{}, no \\left, no \\right, no backslash commands)
3. Write in plain, natural English like a friendly conversation
4. For formulas, write them as plain words: "Labor Cost Percentage equals Labor Cost divided by Sales, times 100"
5. Use simple numbered lists (1. 2. 3.) or dashes (-) for lists

Your Response Style:
- Write like you're having a conversation with a restaurant owner
- Break down complex metrics into easy-to-understand explanations
- Show your calculations in plain English with actual numbers
- Compare results to industry benchmarks naturally in the text
- Provide specific dollar amounts and percentages

When Analyzing Data:
- Acknowledge the specific numbers provided
- Explain calculations conversationally with actual values
- Mention industry benchmarks in a natural way
- Explain if performance is above or below standard
- Provide 3-5 specific action items
- Quantify potential impact when possible

Industry Benchmarks to Reference:
- Food Cost: 28-32% (ideal around 30%)
- Labor Cost: 25-30% (ideal around 28%)
- Prime Cost: 55-65% (ideal around 60%)
- Beverage Cost: 18-24% (ideal around 20%)
- Sales Per Labor Hour: $35-50 or higher

Write naturally and conversationally. No special formatting or markup."""
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000,
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return f"AI analysis unavailable: {str(e)}"


def format_business_report(analysis_type, metrics, performance, recommendations, benchmarks=None, additional_data=None):
    current_date = datetime.now().strftime("%B %d, %Y")

    def _dedupe_preserve_order(values):
        if not isinstance(values, list):
            return values
        seen = set()
        out = []
        for v in values:
            try:
                if isinstance(v, (dict, list, tuple)):
                    key = json.dumps(v, sort_keys=True, default=str)
                else:
                    key = str(v)
            except Exception:
                key = str(v)
            norm = key.strip()
            norm = norm.rstrip(" \t\n\r")
            norm = norm.rstrip(".,;:")
            norm_key = norm.lower()
            if not norm_key:
                continue
            if norm_key in seen:
                continue
            seen.add(norm_key)
            out.append(v if isinstance(v, (dict, list, tuple)) else norm)
        return out

    rating = performance['rating']
    tone = (
        "excellent" if rating == "Excellent"
        else "good" if rating == "Good"
        else "acceptable" if rating == "Acceptable"
        else "concerning"
    )
    comp = (
        "exceed" if rating in ["Excellent", "Good"]
        else "meet" if rating == "Acceptable"
        else "fall below"
    )

    # Text (keep for file export)
    exec_summary_text = (
        f"PERFORMANCE RATING: {rating.upper()}\n\n"
        f"This {analysis_type.lower()} reveals {tone} performance metrics that {comp} industry standards."
    )
    key_metrics_lines = []
    for k, v in metrics.items():
        label = k.replace('_', ' ').title()
        key_lower = k.lower()
        if isinstance(v, float):
            if 'percent' in key_lower or '%' in k:
                key_metrics_lines.append(f"{label}: {v:.1f}%")
            elif any(w in key_lower for w in ['cost', 'sales', 'revenue', 'profit', 'savings', 'price']):
                key_metrics_lines.append(f"{label}: ${v:,.2f}")
            else:
                key_metrics_lines.append(f"{label}: {v:.2f}")
        else:
            # Only apply numeric grouping if value is an int
            if isinstance(v, int):
                key_metrics_lines.append(f"{label}: {v:,}")
            else:
                key_metrics_lines.append(f"{label}: {v}")

    bench_lines = []
    if benchmarks:
        for k, v in benchmarks.items():
            if isinstance(v, (int, float)):
                bench_lines.append(f"{k.replace('_', ' ').title()}: {v:.1f}%")
            else:
                bench_lines.append(f"{k.replace('_', ' ').title()}: {v}")

    recommendations = _dedupe_preserve_order(recommendations)
    rec_lines = [f"{i}. {r}" for i, r in enumerate(recommendations, 1)]

    add_lines = []
    if additional_data:
        for k, v in additional_data.items():
            if isinstance(v, dict):
                add_lines.append(f"{k.replace('_',' ').title()}:")
                for sk, sv in v.items():
                    add_lines.append(f"  {sk.replace('_',' ').title()}: {sv}")
            else:
                add_lines.append(f"{k.replace('_',' ').title()}: {v}")

    # Add bullets back for text version
    key_metrics_text = ["• " + line for line in key_metrics_lines]
    bench_text = ["• " + line for line in bench_lines] if bench_lines else []
    add_text = []
    for line in add_lines:
        if line.startswith("  "):  # Indented sub-item
            add_text.append("  • " + line.strip())
        else:
            add_text.append("• " + line)
    
    business_report_text = (
        f"RESTAURANT CONSULTING REPORT — {analysis_type.upper()}\n"
        f"Generated: {current_date}\n\n"
        f"{exec_summary_text}\n\n"
        "KEY PERFORMANCE METRICS\n"
        + "\n".join(key_metrics_text) + ("\n\nINDUSTRY BENCHMARKS\n" + "\n".join(bench_text) if bench_text else "")
        + ("\n\nADDITIONAL INSIGHTS\n" + "\n".join(add_text) if add_text else "")
        + "\n\nSTRATEGIC RECOMMENDATIONS\n"
        + "\n".join(rec_lines)
        + "\n\nEND OF REPORT"
    ).strip()

    # HTML (for on-screen display)
    def li_items(lines):  # helper for <ul>
        return "".join(f"<li>{line}</li>" for line in lines)
    
    # Choose tracking header theme based on performance color
    perf_color = performance.get('color', 'blue') if isinstance(performance, dict) else 'blue'
    tracking_gradient = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
    if perf_color == 'green':
        tracking_gradient = "linear-gradient(135deg, #10b981 0%, #059669 100%)"
    elif perf_color == 'orange':
        tracking_gradient = "linear-gradient(135deg, #f59e0b 0%, #f97316 100%)"
    elif perf_color == 'red':
        tracking_gradient = "linear-gradient(135deg, #ef4444 0%, #dc2626 100%)"

    def format_tracking_section(title, data, icon="📊"):
        """Format a tracking section with proper HTML styling"""
        if not data or not isinstance(data, dict):
            return ""
        
        # Determine status color based on data_source or status
        data_source = data.get('data_source', data.get('Data Source', 'Estimated'))
        status = data.get('status', data.get('Status', ''))
        
        if data_source == 'Actual':
            source_badge = '<span class="badge badge--excellent" style="font-size: 0.7rem; padding: 2px 8px;">✓ Actual Data</span>'
        else:
            source_badge = '<span class="badge badge--needs-improvement" style="font-size: 0.7rem; padding: 2px 8px;">⚠ Estimated</span>'
        
        # Build metric items
        metric_items = []
        for k, v in data.items():
            if k.lower() in ['data_source', 'status', 'rating']:
                continue  # Skip meta fields, we'll show them separately
            label = k.replace('_', ' ').title()
            if isinstance(v, float):
                if 'percent' in k.lower():
                    formatted_value = f"{v:.1f}%"
                elif any(w in k.lower() for w in ['cost', 'check', 'price']):
                    formatted_value = f"${v:,.2f}"
                elif 'ratio' in k.lower():
                    formatted_value = f"{v:.2f}"
                else:
                    formatted_value = f"{v:,.1f}"
            elif isinstance(v, int):
                formatted_value = f"{v:,}"
            else:
                formatted_value = str(v)
            metric_items.append(f'<div class="tracking-metric"><span class="tracking-label">{label}</span><span class="tracking-value">{formatted_value}</span></div>')
        
        # Add rating if present
        rating = data.get('rating', data.get('Rating', ''))
        if rating:
            rating_class = rating.lower().replace(' ', '-')
            metric_items.append(f'<div class="tracking-metric"><span class="tracking-label">Rating</span><span class="badge badge--{rating_class}" style="font-size: 0.75rem;">{rating}</span></div>')
        
        return f'''
        <div class="tracking-card">
            <div class="tracking-header">
                <span class="tracking-icon">{icon}</span>
                <span class="tracking-title">{title}</span>
                {source_badge}
            </div>
            <div class="tracking-body">
                {''.join(metric_items)}
            </div>
        </div>'''

    # (Removed temporary KPI grid; reverting to original design)
    
    # Build tracking sections HTML
    tracking_html = ""
    other_insights = []
    
    if additional_data:
        for k, v in additional_data.items():
            if isinstance(v, dict):
                # This is a tracking section
                if 'savings' in k.lower():
                    tracking_html += format_tracking_section("💰 Savings Opportunities", v, "💵")
                elif 'overtime' in k.lower():
                    tracking_html += format_tracking_section("Overtime Tracking", v, "⏰")
                elif 'productivity' in k.lower():
                    tracking_html += format_tracking_section("Productivity Metrics", v, "📈")
                elif 'efficiency' in k.lower():
                    tracking_html += format_tracking_section("Efficiency Metrics", v, "⚡")
                elif 'revenue' in k.lower():
                    tracking_html += format_tracking_section("Revenue Analysis", v, "💰")
                elif 'waste' in k.lower():
                    tracking_html += format_tracking_section("Waste Tracking", v, "🗑️")
                elif 'inventory' in k.lower():
                    tracking_html += format_tracking_section("Inventory Analysis", v, "📦")
                elif 'growth' in k.lower():
                    tracking_html += format_tracking_section("Growth Analysis", v, "🚀")
                elif 'benchmark' in k.lower():
                    tracking_html += format_tracking_section("Benchmark Comparison", v, "🎯")
                elif 'cover' in k.lower():
                    tracking_html += format_tracking_section("Per-Cover Metrics", v, "👥")
                elif 'menu' in k.lower():
                    tracking_html += format_tracking_section("Menu Costing", v, "📋")
                elif 'cost_breakdown' in k.lower():
                    tracking_html += format_tracking_section("Cost Breakdown", v, "📊")
                elif 'trend' in k.lower():
                    tracking_html += format_tracking_section("Trend Analysis", v, "📉")
                else:
                    tracking_html += format_tracking_section(k.replace('_', ' ').title(), v, "📊")
            else:
                # Regular insight item
                label = k.replace('_', ' ').title()
                if isinstance(v, float):
                    if 'percent' in k.lower():
                        other_insights.append(f"{label}: {v:.1f}%")
                    elif any(w in k.lower() for w in ['cost', 'savings', 'price']):
                        other_insights.append(f"{label}: ${v:,.2f}")
                    else:
                        other_insights.append(f"{label}: {v:.2f}")
                else:
                    other_insights.append(f"{label}: {v}")
    
    # Wrap tracking sections if any exist
    if tracking_html:
        tracking_html = f'<div class="tracking-section"><h3>📊 Detailed Tracking & Analytics</h3><div class="tracking-grid">{tracking_html}</div></div>'
    
    # Other insights section
    other_insights_html = ""
    if other_insights:
        other_insights_html = f"<h3>Additional Insights</h3><ul>{li_items(other_insights)}</ul>"

    # Normalize badge class name
    badge_class = rating.lower().replace(' ', '-').replace('_', '-')

    # Add CSS styles for tracking sections
    tracking_styles = f'''<style>
    .tracking-section {{ margin: 1.5rem 0; }}
    .tracking-section h3 {{ color: #1e293b; margin-bottom: 1rem; font-size: 1.1rem; }}
    .tracking-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem; }}
    .tracking-card {{ background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); border-radius: 12px; border: 1px solid rgba(102, 126, 234, 0.15); overflow: hidden; }}
    .tracking-header {{ display: flex; align-items: center; gap: 0.5rem; padding: 0.75rem 1rem; background: {tracking_gradient}; color: white; }}
    .tracking-icon {{ font-size: 1.2rem; }}
    .tracking-title {{ font-weight: 600; flex: 1; }}
    .tracking-body {{ padding: 1rem; display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.5rem; }}
    .tracking-metric {{ display: flex; flex-direction: column; padding: 0.5rem; background: white; border-radius: 8px; border: 1px solid #e2e8f0; }}
    .tracking-label {{ font-size: 0.75rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; }}
    .tracking-value {{ font-size: 1.1rem; font-weight: 600; color: #1e293b; }}
    </style>'''

    business_report_html = f"""{tracking_styles}<section class="report"><header class="report__header"><h2>{analysis_type}</h2><div class="report__meta">Generated: {current_date}</div><div class="badge badge--{badge_class}">{rating}</div></header><article class="report__body"><p class="lead">This {analysis_type.lower()} reveals <strong>{tone}</strong> performance metrics that <strong>{comp}</strong> industry standards.</p><h3>Key Performance Metrics</h3><ul>{li_items(key_metrics_lines)}</ul>{f"<h3>Industry Benchmarks</h3><ul>{li_items(bench_lines)}</ul>" if bench_lines else ""}{tracking_html}{other_insights_html}<h3>Strategic Recommendations</h3><ol>{''.join(f'<li>{r}</li>' for r in recommendations)}</ol></article></section>"""

    return {
        "status": "success",
        "analysis_type": analysis_type,
        "report_date": current_date,
        "performance_rating": rating,
        "performance_color": performance.get('color', 'blue'),
        "business_report": business_report_text,          # keep for downloads
        "business_report_html": business_report_html,     # render this in UI
        "executive_summary": exec_summary_text,
        "key_metrics": metrics,
        "benchmarks": benchmarks or {},
        "recommendations": recommendations,
        "additional_insights": additional_data or {},
    }


def calculate_labor_cost_analysis(total_sales, labor_cost, hours_worked, target_labor_percent=30.0, overtime_hours=None, covers=None):
    """
    Comprehensive Labor Cost Analysis with industry benchmarks and recommendations

    Args:
        total_sales (float): Total sales revenue
        labor_cost (float): Total labor costs
        hours_worked (float): Total hours worked
        target_labor_percent (float): Target labor percentage (default 30%)
        overtime_hours (float, optional): Actual overtime hours worked
        covers (int, optional): Number of guests served

    Returns:
        dict: Labor cost analysis with recommendations
    """
    # Input validation
    if not all(isinstance(x, (int, float)) and x > 0 for x in [total_sales, labor_cost, hours_worked]):
        return {"status": "error", "message": "All inputs must be positive numbers"}

    # Calculate key metrics - Labor Cost Percentage
    labor_percent = (labor_cost / total_sales) * 100
    sales_per_labor_hour = total_sales / hours_worked
    cost_per_labor_hour = labor_cost / hours_worked
    
    # Overtime Tracking - use provided value or estimate
    if overtime_hours is not None and overtime_hours >= 0:
        # Use actual overtime hours provided by user
        actual_overtime_hours = float(overtime_hours)
        regular_hours = hours_worked - actual_overtime_hours
        overtime_source = "Actual"
    else:
        # Estimate overtime (assume overtime kicks in at 40hrs/week for monthly data)
        regular_hours = min(hours_worked, 160)  # 40 hrs/week * 4 weeks
        actual_overtime_hours = max(0, hours_worked - 160)
        overtime_source = "Estimated"
    
    overtime_percent = (actual_overtime_hours / hours_worked * 100) if hours_worked > 0 else 0
    overtime_premium_cost = actual_overtime_hours * (labor_cost / hours_worked) * 0.5  # OT is 1.5x regular rate
    
    # Productivity Metrics - use provided covers or estimate
    if covers is not None and covers > 0:
        actual_covers = int(covers)
        covers_source = "Actual"
        covers_per_labor_hour = actual_covers / hours_worked
        avg_check = total_sales / actual_covers
    else:
        # Estimate covers assuming $25 average check
        avg_check = 25
        actual_covers = int(total_sales / avg_check)
        covers_source = "Estimated"
        covers_per_labor_hour = sales_per_labor_hour / avg_check
    
    productivity_score = sales_per_labor_hour / 50 * 100  # Benchmark: $50/hour = 100%
    productivity_score = min(productivity_score, 150)  # Cap at 150%
    labor_efficiency_ratio = total_sales / labor_cost if labor_cost > 0 else 0
    labor_cost_per_cover = labor_cost / actual_covers if actual_covers > 0 else 0

    # Industry benchmarks
    excellent_labor_percent = 25.0
    good_labor_percent = 30.0
    acceptable_labor_percent = 35.0

    # Performance assessment
    if labor_percent <= excellent_labor_percent:
        performance = "Excellent"
        performance_color = "green"
    elif labor_percent <= good_labor_percent:
        performance = "Good"
        performance_color = "blue"
    elif labor_percent <= acceptable_labor_percent:
        performance = "Acceptable"
        performance_color = "yellow"
    else:
        performance = "Needs Improvement"
        performance_color = "red"

    # Calculate potential savings
    target_labor_cost = (target_labor_percent / 100) * total_sales
    potential_savings = labor_cost - target_labor_cost

    # Generate recommendations
    recommendations = []
    
    # Labor Cost Percentage recommendations
    if labor_percent > target_labor_percent:
        labor_gap_pts = labor_percent - target_labor_percent
        est_hours_to_cut = (potential_savings / cost_per_labor_hour) if cost_per_labor_hour > 0 else 0
        recommendations.append(
            f"Labor is {labor_percent:.1f}% vs {target_labor_percent:.1f}% target (+{labor_gap_pts:.1f} pts). "
            f"To hit target on current sales (${total_sales:,.0f}), reduce labor spend by ${potential_savings:,.0f} "
            f"(~{est_hours_to_cut:.0f} labor-hours at ${cost_per_labor_hour:,.0f}/hr)."
        )
        recommendations.append(
            "Start with schedule-to-sales: trim coverage in low-demand dayparts, align breaks/clock-ins to forecasted volume, "
            "and protect peak staffing to avoid sales loss."
        )
    else:
        recommendations.append(
            f"Labor is {labor_percent:.1f}% at/under the {target_labor_percent:.1f}% target. "
            "Maintain weekly schedule-to-sales reviews and monitor overtime creep."
        )
    
    # Overtime Tracking recommendations
    if overtime_percent > 10:
        target_overtime_percent = 5.0
        target_overtime_hours = hours_worked * (target_overtime_percent / 100)
        overtime_hours_to_reduce = max(actual_overtime_hours - target_overtime_hours, 0)
        recommendations.append(
            f"Overtime is {overtime_percent:.1f}% ({actual_overtime_hours:.0f} hrs). "
            f"Bring it toward ~{target_overtime_percent:.0f}% by reducing ~{overtime_hours_to_reduce:.0f} overtime hours; "
            f"estimated premium cost is ${overtime_premium_cost:,.0f} ({overtime_source})."
        )
        recommendations.append(
            "Fix root cause: tighten forecast-based schedules, require shift-extension approvals, and rebalance staffing via cross-training "
            "before adding extra hours."
        )
    elif overtime_percent > 5:
        recommendations.append(
            f"Overtime is {overtime_percent:.1f}% ({actual_overtime_hours:.0f} hrs). "
            "Set a guardrail (e.g., keep overtime near 5%) and review the top overtime roles/shifts weekly."
        )
    else:
        recommendations.append(
            f"Overtime is controlled at {overtime_percent:.1f}% ({actual_overtime_hours:.0f} hrs). "
            "Keep the approval workflow and watch for spikes around peak events."
        )
    
    # Productivity recommendations
    if sales_per_labor_hour < 50:
        splh_gap = 50 - sales_per_labor_hour
        est_sales_uplift = splh_gap * hours_worked if splh_gap > 0 else 0
        recommendations.append(
            f"Sales per labor hour is ${sales_per_labor_hour:.2f} (target ≥ $50). "
            f"Closing the gap by ${splh_gap:.0f}/labor-hr could add ~${est_sales_uplift:,.0f} in sales at current hours."
        )
        recommendations.append(
            "Prioritize 2–3 high-margin add-ons for suggestive selling, tighten speed-of-service (prep/line bottlenecks), "
            "and cross-train so you can flex labor without sacrificing guest experience."
        )
    elif sales_per_labor_hour > 100:
        recommendations.append(
            f"Excellent productivity at ${sales_per_labor_hour:.2f}/labor-hr. "
            "Ensure peak staffing matches demand and consider extending peak capacity (covers/throughput) without increasing labor %."
        )
    else:
        recommendations.append(
            f"Productivity is ${sales_per_labor_hour:.2f}/labor-hr (around industry standard). "
            "Next step: push toward $100+ by improving check average and tightening staffing during slow periods."
        )

    # Prepare data for business report
    metrics = {
        "labor_percent": round(labor_percent, 2),
        "sales_per_labor_hour": round(sales_per_labor_hour, 2),
        "cost_per_labor_hour": round(cost_per_labor_hour, 2),
        "total_labor_cost": labor_cost,
        "total_sales": total_sales,
        "hours_worked": hours_worked,
        "overtime_hours": round(actual_overtime_hours, 1),
        "overtime_percent": round(overtime_percent, 1),
        "productivity_score": round(productivity_score, 1),
        "covers": actual_covers,
        "labor_cost_per_cover": round(labor_cost_per_cover, 2)
    }

    performance_data = {
        "rating": performance,
        "color": performance_color,
        "vs_target": round(labor_percent - target_labor_percent, 2)
    }

    benchmarks = {
        "excellent_threshold": excellent_labor_percent,
        "good_threshold": good_labor_percent,
        "acceptable_threshold": acceptable_labor_percent,
        "target_percent": target_labor_percent
    }
    
    # Calculate total savings opportunities (combine all sources)
    savings_from_target = round(potential_savings, 2) if potential_savings > 0 else 0
    savings_from_overtime = round(overtime_premium_cost, 2) if overtime_percent > 5 else 0
    savings_from_efficiency = round(labor_cost * 0.05, 2) if sales_per_labor_hour < 50 else 0
    total_savings_opportunity = savings_from_target + savings_from_overtime + savings_from_efficiency

    additional_insights = {
        "savings_summary": {
            "total_savings_opportunity": total_savings_opportunity,
            "savings_from_cost_reduction": savings_from_target,
            "savings_from_overtime_reduction": savings_from_overtime,
            "savings_from_efficiency": savings_from_efficiency,
            "status": "On Target" if total_savings_opportunity == 0 else "Savings Available",
            "data_source": "Calculated"
        },
        "efficiency_rating": "High" if sales_per_labor_hour > 80 else "Medium" if sales_per_labor_hour > 50 else "Low",
        "cost_control": "Excellent" if labor_percent <= 25 else "Good" if labor_percent <= 30 else "Needs Improvement",
        "overtime_tracking": {
            "overtime_hours": round(actual_overtime_hours, 1),
            "regular_hours": round(regular_hours, 1),
            "overtime_percent": round(overtime_percent, 1),
            "overtime_premium_cost": round(overtime_premium_cost, 2),
            "data_source": overtime_source,
            "status": "Low" if overtime_percent < 5 else "Moderate" if overtime_percent < 10 else "High"
        },
        "productivity_metrics": {
            "productivity_score": round(productivity_score, 1),
            "labor_efficiency_ratio": round(labor_efficiency_ratio, 2),
            "covers_per_labor_hour": round(covers_per_labor_hour, 1),
            "labor_cost_per_cover": round(labor_cost_per_cover, 2),
            "total_covers": actual_covers,
            "avg_check": round(avg_check, 2),
            "data_source": covers_source,
            "rating": "Excellent" if productivity_score > 120 else "Good" if productivity_score > 100 else "Needs Improvement"
        }
    }

    return format_business_report(
        analysis_type="Labor Cost Analysis",
        metrics=metrics,
        performance=performance_data,
        recommendations=recommendations,
        benchmarks=benchmarks,
        additional_data=additional_insights
    )


def calculate_food_cost_analysis(total_sales, food_cost, target_food_percent=30.0, waste_cost=None, covers=None, beginning_inventory=None, ending_inventory=None):
    """
    Comprehensive Food Cost Analysis with industry benchmarks and recommendations

    Args:
        total_sales (float): Total sales revenue
        food_cost (float): Total food costs
        target_food_percent (float): Target food cost percentage (default 30%)
        waste_cost (float, optional): Actual recorded waste value
        covers (int, optional): Number of guests served
        beginning_inventory (float, optional): Starting inventory value
        ending_inventory (float, optional): Ending inventory value

    Returns:
        dict: Food cost analysis with recommendations
    """
    # Input validation
    if not all(isinstance(x, (int, float)) and x > 0 for x in [total_sales, food_cost]):
        return {"status": "error", "message": "All inputs must be positive numbers"}

    # Calculate key metrics - Food Cost Percentage
    food_percent = (food_cost / total_sales) * 100
    gross_profit = total_sales - food_cost
    gross_profit_margin = (gross_profit / total_sales) * 100
    
    # Waste Tracking - use provided value or estimate
    if waste_cost is not None and waste_cost >= 0:
        actual_waste_cost = float(waste_cost)
        actual_waste_percent = (actual_waste_cost / food_cost * 100) if food_cost > 0 else 0
        waste_source = "Actual"
    else:
        # Estimate waste based on industry averages (4-10% of food purchases)
        actual_waste_percent = 6.0 if food_percent > 32 else 4.0 if food_percent > 28 else 3.0
        actual_waste_cost = food_cost * (actual_waste_percent / 100)
        waste_source = "Estimated"
    
    waste_per_day = actual_waste_cost / 30  # Monthly estimate
    potential_waste_savings = actual_waste_cost * 0.5  # Can typically reduce waste by 50%
    
    # Inventory analysis if provided
    if beginning_inventory is not None and ending_inventory is not None:
        inventory_change = beginning_inventory - ending_inventory
        inventory_turnover = food_cost / ((beginning_inventory + ending_inventory) / 2) if (beginning_inventory + ending_inventory) > 0 else 0
        inventory_source = "Actual"
    else:
        inventory_change = None
        inventory_turnover = None
        inventory_source = "Not Provided"
    
    # Menu Costing Metrics - use provided covers or estimate
    if covers is not None and covers > 0:
        actual_covers = int(covers)
        covers_source = "Actual"
        avg_check = total_sales / actual_covers
    else:
        avg_check = 25  # Default assumption
        actual_covers = int(total_sales / avg_check)
        covers_source = "Estimated"
    
    ideal_food_cost = total_sales * 0.28  # Industry ideal is 28%
    menu_cost_variance = food_cost - ideal_food_cost
    cost_per_cover = food_cost / actual_covers if actual_covers > 0 else 0
    contribution_margin = gross_profit / actual_covers if actual_covers > 0 else 0  # Per cover

    # Industry benchmarks
    excellent_food_percent = 25.0
    good_food_percent = 30.0
    acceptable_food_percent = 35.0

    # Performance assessment
    if food_percent <= excellent_food_percent:
        performance = "Excellent"
        performance_color = "green"
    elif food_percent <= good_food_percent:
        performance = "Good"
        performance_color = "blue"
    elif food_percent <= acceptable_food_percent:
        performance = "Acceptable"
        performance_color = "yellow"
    else:
        performance = "Needs Improvement"
        performance_color = "red"

    # Calculate potential savings
    target_food_cost = (target_food_percent / 100) * total_sales
    potential_savings = food_cost - target_food_cost

    # Generate recommendations
    recommendations = []
    
    # Food Cost Percentage recommendations
    if food_percent > target_food_percent:
        food_gap_pts = food_percent - target_food_percent
        recommendations.append(
            f"Food cost is {food_percent:.1f}% vs {target_food_percent:.1f}% target (+{food_gap_pts:.1f} pts). "
            f"On current sales (${total_sales:,.0f}), that's ~${potential_savings:,.0f} above target — prioritize portion control and recipe adherence."
        )
        recommendations.append(
            "Audit the top-selling recipes for portion drift, refresh recipe cards with current ingredient prices, and re-price or re-engineer low-margin items."
        )
    else:
        recommendations.append(
            f"Food cost is {food_percent:.1f}% at/under the {target_food_percent:.1f}% target. "
            "Maintain weekly recipe-cost updates and spot-check portioning on high-volume items."
        )
    
    # Waste Tracking recommendations
    if actual_waste_percent > 5:
        recommendations.append(
            f"{waste_source} waste is {actual_waste_percent:.1f}% (~${actual_waste_cost:,.0f}/month). "
            f"Reducing waste toward target could save about ${potential_waste_savings:,.0f}/month."
        )
        recommendations.append(
            "Run a daily waste log by station, enforce FIFO rotation, and adjust par levels/ordering for the top waste categories."
        )
    else:
        recommendations.append(
            f"{waste_source} waste is controlled at {actual_waste_percent:.1f}% (~${actual_waste_cost:,.0f}/month). "
            "Continue FIFO discipline and monitor spikes after menu changes or events."
        )
    
    # Menu Costing recommendations
    if menu_cost_variance > 0:
        recommendations.append(
            f"Menu cost variance is ${menu_cost_variance:,.0f} above the ideal (28% model). "
            "Re-cost key recipes, verify yields, and promote high-margin items to shift mix."
        )
        recommendations.append(
            "Use menu engineering: highlight high-margin/high-popularity items, and fix low-margin best-sellers via portion/cost/price adjustments."
        )
    else:
        recommendations.append(
            "Menu costing is on track versus the ideal model. Maintain pricing discipline and re-cost after supplier price changes."
        )
    
    if food_percent > 35:
        recommendations.append(
            "CRITICAL: Food cost is materially above standard. Start with top-10 ingredients by spend: renegotiate pricing, "
            "swap equivalent SKUs, and tighten receiving/portion controls immediately."
        )
    
    if gross_profit_margin < 65:
        gp_gap_pts = 65 - gross_profit_margin
        est_gp_uplift = (gp_gap_pts / 100) * total_sales if gp_gap_pts > 0 else 0
        recommendations.append(
            f"Gross profit margin is {gross_profit_margin:.1f}% (goal ~65%+). "
            f"Closing the {gp_gap_pts:.1f}-pt gap adds ~${est_gp_uplift:,.0f} gross profit on current sales — use pricing + cost control together."
        )

    # Prepare data for business report
    metrics = {
        "food_percent": round(food_percent, 2),
        "total_food_cost": food_cost,
        "total_sales": total_sales,
        "gross_profit": round(gross_profit, 2),
        "gross_profit_margin": round(gross_profit_margin, 2),
        "waste_cost": round(actual_waste_cost, 2),
        "waste_percent": round(actual_waste_percent, 1),
        "cost_per_cover": round(cost_per_cover, 2),
        "contribution_margin": round(contribution_margin, 2),
        "covers": actual_covers
    }

    performance_data = {
        "rating": performance,
        "color": performance_color,
        "vs_target": round(food_percent - target_food_percent, 2)
    }

    benchmarks = {
        "excellent_threshold": excellent_food_percent,
        "good_threshold": good_food_percent,
        "acceptable_threshold": acceptable_food_percent,
        "target_percent": target_food_percent
    }
    
    # Calculate total savings opportunities
    savings_from_target = round(potential_savings, 2) if potential_savings > 0 else 0
    savings_from_waste = round(potential_waste_savings, 2) if actual_waste_percent > 3 else 0
    savings_from_menu = round(menu_cost_variance, 2) if menu_cost_variance > 0 else 0
    total_savings_opportunity = savings_from_target + savings_from_waste

    additional_insights = {
        "savings_summary": {
            "total_savings_opportunity": total_savings_opportunity,
            "savings_from_cost_reduction": savings_from_target,
            "savings_from_waste_reduction": savings_from_waste,
            "savings_from_menu_optimization": savings_from_menu,
            "status": "On Target" if total_savings_opportunity == 0 else "Savings Available",
            "data_source": "Calculated"
        },
        "cost_control_rating": "Excellent" if food_percent <= 25 else "Good" if food_percent <= 30 else "Needs Improvement",
        "menu_engineering_priority": "Low" if food_percent <= 28 else "Medium" if food_percent <= 32 else "High",
        "waste_tracking": {
            "waste_percent": round(actual_waste_percent, 1),
            "waste_cost": round(actual_waste_cost, 2),
            "waste_per_day": round(waste_per_day, 2),
            "potential_savings": round(potential_waste_savings, 2),
            "data_source": waste_source,
            "status": "Low" if actual_waste_percent < 4 else "Moderate" if actual_waste_percent < 6 else "High"
        },
        "menu_costing": {
            "cost_per_cover": round(cost_per_cover, 2),
            "ideal_food_cost": round(ideal_food_cost, 2),
            "menu_variance": round(menu_cost_variance, 2),
            "contribution_margin": round(contribution_margin, 2),
            "total_covers": actual_covers,
            "avg_check": round(avg_check, 2),
            "data_source": covers_source,
            "pricing_status": "Optimized" if menu_cost_variance <= 0 else "Needs Review" if menu_cost_variance < 1000 else "Critical"
        },
        "inventory_analysis": {
            "beginning_inventory": beginning_inventory,
            "ending_inventory": ending_inventory,
            "inventory_change": round(inventory_change, 2) if inventory_change is not None else None,
            "inventory_turnover": round(inventory_turnover, 2) if inventory_turnover is not None else None,
            "data_source": inventory_source
        }
    }

    return format_business_report(
        analysis_type="Food Cost Analysis",
        metrics=metrics,
        performance=performance_data,
        recommendations=recommendations,
        benchmarks=benchmarks,
        additional_data=additional_insights
    )


def calculate_prime_cost_analysis(total_sales, labor_cost, food_cost, target_prime_percent=60.0, covers=None):
    """
    Comprehensive Prime Cost Analysis (Labor + Food costs)

    Args:
        total_sales (float): Total sales revenue
        labor_cost (float): Total labor costs
        food_cost (float): Total food costs
        target_prime_percent (float): Target prime cost percentage (default 60%)
        covers (int, optional): Number of guests served

    Returns:
        dict: Prime cost analysis with recommendations
    """
    # Input validation
    if not all(isinstance(x, (int, float)) and x > 0 for x in [total_sales, labor_cost, food_cost]):
        return {"status": "error", "message": "All inputs must be positive numbers"}

    # Calculate key metrics - Prime Cost Percentage
    prime_cost = labor_cost + food_cost
    prime_percent = (prime_cost / total_sales) * 100
    labor_percent = (labor_cost / total_sales) * 100
    food_percent = (food_cost / total_sales) * 100
    gross_profit = total_sales - prime_cost
    gross_profit_margin = (gross_profit / total_sales) * 100
    
    # Calculate per-cover metrics
    if covers is not None and covers > 0:
        actual_covers = int(covers)
        covers_source = "Actual"
        avg_check = total_sales / actual_covers
    else:
        avg_check = 25  # Default assumption
        actual_covers = int(total_sales / avg_check)
        covers_source = "Estimated"
    
    prime_cost_per_cover = prime_cost / actual_covers if actual_covers > 0 else 0
    profit_per_cover = gross_profit / actual_covers if actual_covers > 0 else 0

    # Industry benchmarks
    excellent_prime_percent = 55.0
    good_prime_percent = 60.0
    acceptable_prime_percent = 65.0

    # Performance assessment
    if prime_percent <= excellent_prime_percent:
        performance = "Excellent"
        performance_color = "green"
    elif prime_percent <= good_prime_percent:
        performance = "Good"
        performance_color = "blue"
    elif prime_percent <= acceptable_prime_percent:
        performance = "Acceptable"
        performance_color = "yellow"
    else:
        performance = "Needs Improvement"
        performance_color = "red"

    # Calculate potential savings
    target_prime_cost = (target_prime_percent / 100) * total_sales
    potential_savings = prime_cost - target_prime_cost

    # Cost breakdown analysis
    cost_breakdown = {
        "labor_portion": round((labor_cost / prime_cost) * 100, 1),
        "food_portion": round((food_cost / prime_cost) * 100, 1)
    }
    
    # Target Benchmarking
    industry_benchmarks = {
        "fine_dining": {"target": 65, "labor": 35, "food": 30},
        "casual_dining": {"target": 60, "labor": 30, "food": 30},
        "fast_casual": {"target": 55, "labor": 25, "food": 30},
        "quick_service": {"target": 50, "labor": 22, "food": 28}
    }
    
    # Determine best fit segment based on labor/food ratio
    if labor_percent > food_percent + 5:
        segment_fit = "fine_dining"
    elif labor_percent > food_percent:
        segment_fit = "casual_dining"
    elif food_percent > labor_percent + 5:
        segment_fit = "quick_service"
    else:
        segment_fit = "fast_casual"
    
    segment_benchmark = industry_benchmarks[segment_fit]
    vs_segment_target = prime_percent - segment_benchmark["target"]
    labor_vs_benchmark = labor_percent - segment_benchmark["labor"]
    food_vs_benchmark = food_percent - segment_benchmark["food"]
    
    # Trend Analysis (simulated based on current performance)
    # In production, this would use historical data
    trend_direction = "Improving" if prime_percent < 60 else "Stable" if prime_percent < 65 else "Declining"
    projected_savings_monthly = potential_savings if potential_savings > 0 else 0
    projected_savings_annual = projected_savings_monthly * 12
    
    # Calculate efficiency scores
    labor_efficiency_score = max(0, 100 - (labor_percent - 25) * 5)  # 25% = 100 score
    food_efficiency_score = max(0, 100 - (food_percent - 28) * 5)   # 28% = 100 score
    overall_efficiency_score = (labor_efficiency_score + food_efficiency_score) / 2

    # Generate recommendations
    recommendations = []
    
    # Prime Cost Percentage recommendations
    if prime_percent > target_prime_percent:
        prime_gap_pts = prime_percent - target_prime_percent
        recommendations.append(
            f"Prime cost is {prime_percent:.1f}% vs {target_prime_percent:.1f}% target (+{prime_gap_pts:.1f} pts). "
            f"To hit target on current sales (${total_sales:,.0f}), reduce combined labor+food spend by ${potential_savings:,.0f}."
        )
        if labor_percent > 30:
            recommendations.append(
                f"Labor is {labor_percent:.1f}% — tighten schedules and overtime first to move toward the segment benchmark (~{segment_benchmark['labor']}%)."
            )
        if food_percent > 30:
            recommendations.append(
                f"Food is {food_percent:.1f}% — focus on portioning, waste, and menu mix to move toward the segment benchmark (~{segment_benchmark['food']}%)."
            )
    else:
        recommendations.append(
            f"Prime cost is {prime_percent:.1f}% at/under the {target_prime_percent:.1f}% target. "
            "Maintain weekly labor scheduling and recipe-cost discipline."
        )
    
    # Target Benchmarking recommendations
    if vs_segment_target > 5:
        recommendations.append(f"Prime cost is {vs_segment_target:.1f}% above {segment_fit.replace('_', ' ')} benchmark ({segment_benchmark['target']}%)")
    elif vs_segment_target < -5:
        recommendations.append(f"Outperforming {segment_fit.replace('_', ' ')} benchmark by {abs(vs_segment_target):.1f}% - excellent cost control")
    else:
        recommendations.append(f"Performing at {segment_fit.replace('_', ' ')} industry standard")
    
    if labor_vs_benchmark > 3:
        recommendations.append(f"Labor cost {labor_vs_benchmark:.1f}% above segment benchmark - prioritize labor optimization")
    if food_vs_benchmark > 3:
        recommendations.append(f"Food cost {food_vs_benchmark:.1f}% above segment benchmark - prioritize food cost control")
    
    # Trend Analysis recommendations
    if trend_direction == "Declining":
        recommendations.append(
            "Cost trend is unfavorable. Implement a 2-week cost reset: daily labor vs forecast, daily waste log, and recipe-cost refresh on top movers."
        )
        recommendations.append(f"Potential annual savings if target achieved (at current run rate): ${projected_savings_annual:,.0f}")
    elif trend_direction == "Improving":
        recommendations.append("Cost trend is improving — keep the current controls and formalize them into weekly routines.")
    
    if cost_breakdown["labor_portion"] > 60:
        recommendations.append("Labor costs dominate - focus on labor efficiency and scheduling")
    elif cost_breakdown["food_portion"] > 60:
        recommendations.append("Food costs dominate - focus on menu engineering and portion control")

    # Prepare data for business report
    metrics = {
        "prime_cost": round(prime_cost, 2),
        "prime_percent": round(prime_percent, 2),
        "labor_percent": round(labor_percent, 2),
        "food_percent": round(food_percent, 2),
        "total_sales": total_sales,
        "gross_profit": round(gross_profit, 2),
        "gross_profit_margin": round(gross_profit_margin, 2),
        "efficiency_score": round(overall_efficiency_score, 1),
        "covers": actual_covers,
        "prime_cost_per_cover": round(prime_cost_per_cover, 2),
        "profit_per_cover": round(profit_per_cover, 2)
    }

    performance_data = {
        "rating": performance,
        "color": performance_color,
        "vs_target": round(prime_percent - target_prime_percent, 2)
    }

    benchmarks = {
        "excellent_threshold": excellent_prime_percent,
        "good_threshold": good_prime_percent,
        "acceptable_threshold": acceptable_prime_percent,
        "target_percent": target_prime_percent
    }
    
    # Calculate total savings opportunities
    savings_from_target = round(potential_savings, 2) if potential_savings > 0 else 0
    savings_from_labor_opt = round(labor_cost * 0.05, 2) if labor_percent > 30 else 0
    savings_from_food_opt = round(food_cost * 0.05, 2) if food_percent > 30 else 0
    total_savings_opportunity = savings_from_target + savings_from_labor_opt + savings_from_food_opt

    additional_insights = {
        "savings_summary": {
            "total_savings_opportunity": total_savings_opportunity,
            "savings_from_cost_reduction": savings_from_target,
            "savings_from_labor_optimization": savings_from_labor_opt,
            "savings_from_food_optimization": savings_from_food_opt,
            "projected_annual_savings": round(total_savings_opportunity * 12, 2),
            "status": "On Target" if total_savings_opportunity == 0 else "Savings Available",
            "data_source": "Calculated"
        },
        "cost_breakdown": cost_breakdown,
        "cost_control_rating": "Excellent" if prime_percent <= 55 else "Good" if prime_percent <= 60 else "Needs Improvement",
        "primary_cost_driver": (
            "Labor" if cost_breakdown["labor_portion"] > 60
            else "Food" if cost_breakdown["food_portion"] > 60
            else "Balanced"
        ),
        "cover_metrics": {
            "total_covers": actual_covers,
            "avg_check": round(avg_check, 2),
            "prime_cost_per_cover": round(prime_cost_per_cover, 2),
            "profit_per_cover": round(profit_per_cover, 2),
            "data_source": covers_source
        },
        "target_benchmarking": {
            "segment_fit": segment_fit.replace('_', ' ').title(),
            "segment_target": segment_benchmark["target"],
            "vs_segment_target": round(vs_segment_target, 1),
            "labor_vs_benchmark": round(labor_vs_benchmark, 1),
            "food_vs_benchmark": round(food_vs_benchmark, 1),
            "benchmark_status": "Above Target" if vs_segment_target > 3 else "At Target" if vs_segment_target > -3 else "Below Target"
        },
        "trend_analysis": {
            "trend_direction": trend_direction,
            "labor_efficiency_score": round(labor_efficiency_score, 1),
            "food_efficiency_score": round(food_efficiency_score, 1),
            "overall_efficiency_score": round(overall_efficiency_score, 1),
            "projected_monthly_savings": round(projected_savings_monthly, 2),
            "projected_annual_savings": round(projected_savings_annual, 2)
        }
    }

    return format_business_report(
        analysis_type="Prime Cost Analysis",
        metrics=metrics,
        performance=performance_data,
        recommendations=recommendations,
        benchmarks=benchmarks,
        additional_data=additional_insights
    )


def calculate_sales_performance_analysis(total_sales, labor_cost, food_cost, hours_worked, previous_sales=None, covers=None, avg_check=None):
    """
    Comprehensive Sales Performance Analysis

    Args:
        total_sales (float): Current period sales revenue
        labor_cost (float): Total labor costs
        food_cost (float): Total food costs
        hours_worked (float): Total hours worked
        previous_sales (float, optional): Previous period sales for comparison
        covers (int, optional): Number of guests served
        avg_check (float, optional): Average check amount

    Returns:
        dict: Sales performance analysis with insights
    """
    # Input validation
    if not all(isinstance(x, (int, float)) and x > 0 for x in [total_sales, labor_cost, food_cost, hours_worked]):
        return {"status": "error", "message": "All inputs must be positive numbers"}

    # Calculate key metrics - Sales Per Labor Hour
    sales_per_labor_hour = total_sales / hours_worked
    labor_percent = (labor_cost / total_sales) * 100
    food_percent = (food_cost / total_sales) * 100
    prime_percent = labor_percent + food_percent
    gross_profit = total_sales - (labor_cost + food_cost)
    gross_profit_margin = (gross_profit / total_sales) * 100
    
    # Calculate per-cover metrics - use provided values or estimate
    if covers is not None and covers > 0:
        actual_covers = int(covers)
        covers_source = "Actual"
        if avg_check is not None and avg_check > 0:
            actual_avg_check = float(avg_check)
        else:
            actual_avg_check = total_sales / actual_covers
    else:
        if avg_check is not None and avg_check > 0:
            actual_avg_check = float(avg_check)
            actual_covers = int(total_sales / actual_avg_check)
        else:
            actual_avg_check = 25  # Default assumption
            actual_covers = int(total_sales / actual_avg_check)
        covers_source = "Estimated"
    
    covers_per_labor_hour = actual_covers / hours_worked
    labor_cost_per_cover = labor_cost / actual_covers if actual_covers > 0 else 0
    food_cost_per_cover = food_cost / actual_covers if actual_covers > 0 else 0
    profit_per_cover = gross_profit / actual_covers if actual_covers > 0 else 0

    # Performance benchmarks
    excellent_sales_per_hour = 80.0
    good_sales_per_hour = 60.0
    acceptable_sales_per_hour = 40.0

    # Sales performance assessment
    if sales_per_labor_hour >= excellent_sales_per_hour:
        sales_performance = "Excellent"
        sales_color = "green"
    elif sales_per_labor_hour >= good_sales_per_hour:
        sales_performance = "Good"
        sales_color = "blue"
    elif sales_per_labor_hour >= acceptable_sales_per_hour:
        sales_performance = "Acceptable"
        sales_color = "yellow"
    else:
        sales_performance = "Needs Improvement"
        sales_color = "red"

    # Revenue Trends Analysis
    # Calculate daily/weekly projections
    daily_sales = total_sales / 30  # Assuming monthly data
    weekly_sales = daily_sales * 7
    annual_projection = total_sales * 12
    
    # Revenue per labor hour trends
    revenue_velocity = sales_per_labor_hour / 60  # Sales per minute
    peak_hour_potential = sales_per_labor_hour * 1.5  # Estimated peak hour revenue
    off_peak_potential = sales_per_labor_hour * 0.6  # Estimated off-peak revenue
    
    # Revenue mix analysis
    revenue_after_labor = total_sales - labor_cost
    revenue_after_food = total_sales - food_cost
    net_revenue = total_sales - (labor_cost + food_cost)
    revenue_retention_rate = (net_revenue / total_sales) * 100

    # Growth Analysis
    # If no previous sales, estimate based on industry standards
    if previous_sales and previous_sales > 0:
        sales_growth_percent = ((total_sales - previous_sales) / previous_sales) * 100
        sales_growth_amount = total_sales - previous_sales
        growth_trend = "Growing" if sales_growth_percent > 0 else "Declining"
    else:
        # Simulate growth metrics based on performance
        if sales_per_labor_hour >= excellent_sales_per_hour:
            sales_growth_percent = 8.5  # Strong performers typically grow 5-10%
            growth_trend = "Growing"
        elif sales_per_labor_hour >= good_sales_per_hour:
            sales_growth_percent = 4.2
            growth_trend = "Growing"
        elif sales_per_labor_hour >= acceptable_sales_per_hour:
            sales_growth_percent = 1.5
            growth_trend = "Stable"
        else:
            sales_growth_percent = -2.0
            growth_trend = "Declining"
        sales_growth_amount = total_sales * (sales_growth_percent / 100)
    
    # Growth potential analysis
    if sales_per_labor_hour < 50:
        growth_potential = "High"  # Lots of room for improvement
        potential_increase = (50 - sales_per_labor_hour) * hours_worked
    elif sales_per_labor_hour < 80:
        growth_potential = "Medium"
        potential_increase = (80 - sales_per_labor_hour) * hours_worked
    else:
        growth_potential = "Limited"  # Already performing well
        potential_increase = (100 - sales_per_labor_hour) * hours_worked
    
    # Calculate growth opportunities
    upselling_potential = total_sales * 0.10  # 10% potential from upselling
    efficiency_gains = (hours_worked * 0.1) * sales_per_labor_hour  # 10% efficiency improvement
    total_growth_opportunity = potential_increase + upselling_potential

    # Generate recommendations
    recommendations = []
    
    # Sales Per Labor Hour recommendations
    if sales_per_labor_hour < acceptable_sales_per_hour:
        splh_gap = acceptable_sales_per_hour - sales_per_labor_hour
        est_revenue_uplift = splh_gap * hours_worked if splh_gap > 0 else 0
        recommendations.append(
            f"Sales per labor hour is ${sales_per_labor_hour:.2f} vs acceptable target ${acceptable_sales_per_hour:.0f} (-${splh_gap:.0f}/hr). "
            f"At current hours, that's ~${est_revenue_uplift:,.0f} in unrealized sales capacity."
        )
        recommendations.append(
            "Run 2-week upsell + speed-of-service sprint: pre-shift prompts for add-ons, table touch cadence, and line/prep bottleneck fixes."
        )
    elif sales_per_labor_hour >= excellent_sales_per_hour:
        recommendations.append(f"Excellent SPLH of ${sales_per_labor_hour:.2f} - you're in the top performance tier")
        recommendations.append("Consider expanding capacity during peak hours to capture more revenue")
    else:
        to_excellent = excellent_sales_per_hour - sales_per_labor_hour
        recommendations.append(
            f"SPLH is ${sales_per_labor_hour:.2f} (good). Closing the remaining ${to_excellent:.0f}/hr gap to ${excellent_sales_per_hour:.0f} is the path to excellence."
        )
    
    # Revenue Trends recommendations
    if revenue_retention_rate < 40:
        recommendations.append(f"Revenue retention at {revenue_retention_rate:.1f}% - focus on cost control to improve margins")
    else:
        recommendations.append(f"Revenue retention at {revenue_retention_rate:.1f}% - healthy profit margins")
    
    recommendations.append(f"Estimated annual revenue: ${annual_projection:,.2f}")
    
    if peak_hour_potential > 100:
        recommendations.append(f"Peak hour potential: ${peak_hour_potential:.2f}/hour - maximize staffing during rush")
    
    # Growth Analysis recommendations
    if growth_trend == "Growing":
        recommendations.append(f"Revenue trending up {sales_growth_percent:.1f}% - continue growth strategies")
        if sales_growth_percent > 10:
            recommendations.append("Strong growth - consider capacity planning and staff expansion")
    elif growth_trend == "Declining":
        recommendations.append(f"Revenue trending down {abs(sales_growth_percent):.1f}% - implement recovery plan")
        recommendations.append("Analyze market trends, customer feedback, and competitive landscape")
    else:
        recommendations.append("Revenue stable - implement growth initiatives to increase market share")
    
    recommendations.append(f"Growth opportunity identified: ${total_growth_opportunity:,.2f} potential additional revenue")
    
    if labor_percent > 35:
        recommendations.append("High labor percentage - optimize scheduling and reduce overtime")
    if food_percent > 35:
        recommendations.append("High food cost percentage - review menu pricing and portion control")

    # Prepare data for business report
    metrics = {
        "total_sales": total_sales,
        "sales_per_labor_hour": round(sales_per_labor_hour, 2),
        "labor_percent": round(labor_percent, 2),
        "food_percent": round(food_percent, 2),
        "prime_percent": round(prime_percent, 2),
        "hours_worked": hours_worked,
        "gross_profit": round(gross_profit, 2),
        "gross_profit_margin": round(gross_profit_margin, 2),
        "covers": actual_covers,
        "avg_check": round(actual_avg_check, 2),
        "covers_per_labor_hour": round(covers_per_labor_hour, 1),
        "revenue_retention_rate": round(revenue_retention_rate, 1)
    }

    performance_data = {
        "rating": sales_performance,
        "color": sales_color
    }

    benchmarks = {
        "excellent_threshold": excellent_sales_per_hour,
        "good_threshold": good_sales_per_hour,
        "acceptable_threshold": acceptable_sales_per_hour
    }

    additional_insights = {
        "revenue_efficiency": {
            "sales_per_labor_hour": round(sales_per_labor_hour, 2),
            "covers_per_labor_hour": round(covers_per_labor_hour, 1),
            "labor_cost_per_cover": round(labor_cost_per_cover, 2),
            "profit_per_cover": round(profit_per_cover, 2),
            "total_covers": actual_covers,
            "avg_check": round(actual_avg_check, 2),
            "data_source": covers_source,
            "efficiency_rating": "High" if sales_per_labor_hour > 80 else "Medium" if sales_per_labor_hour > 50 else "Low"
        },
        "revenue_trends": {
            "daily_sales": round(daily_sales, 2),
            "weekly_sales": round(weekly_sales, 2),
            "annual_projection": round(annual_projection, 2),
            "revenue_retention_rate": round(revenue_retention_rate, 1),
            "peak_hour_potential": round(peak_hour_potential, 2),
            "off_peak_potential": round(off_peak_potential, 2),
            "trend_direction": growth_trend
        },
        "growth_analysis": {
            "growth_percent": round(sales_growth_percent, 1),
            "growth_amount": round(sales_growth_amount, 2),
            "growth_trend": growth_trend,
            "growth_potential": growth_potential,
            "potential_increase": round(potential_increase, 2),
            "upselling_potential": round(upselling_potential, 2),
            "total_opportunity": round(total_growth_opportunity, 2)
        },
        "performance_trend": growth_trend
    }

    return format_business_report(
        analysis_type="Sales Performance Analysis",
        metrics=metrics,
        performance=performance_data,
        recommendations=recommendations,
        benchmarks=benchmarks,
        additional_data=additional_insights
    )


def calculate_kpi_summary(total_sales, labor_cost, food_cost, hours_worked):
    """
    Calculate comprehensive KPI summary with input validation

    Args:
        total_sales (float): Total sales revenue
        labor_cost (float): Total labor costs
        food_cost (float): Total food costs
        hours_worked (float): Total hours worked

    Returns:
        dict: KPI calculations or error response
    """
    # Input validation
    inputs = {"total_sales": total_sales, "labor_cost": labor_cost, "food_cost": food_cost, "hours_worked": hours_worked}

    # Check for None values
    for name, value in inputs.items():
        if value is None:
            return {"status": "error", "message": f"{name} cannot be null"}

    # Check for numeric types
    for name, value in inputs.items():
        if not isinstance(value, (int, float)):
            return {"status": "error", "message": f"{name} must be a number, got {type(value).__name__}"}

    # Check for negative values
    for name, value in inputs.items():
        if value < 0:
            return {"status": "error", "message": f"{name} cannot be negative"}

    # Check for zero values where division occurs
    if total_sales == 0:
        return {"status": "error", "message": "total_sales cannot be zero"}

    if hours_worked == 0:
        return {"status": "error", "message": "hours_worked cannot be zero"}

    # Perform calculations
    prime_cost = labor_cost + food_cost
    labor_percent = (labor_cost / total_sales) * 100
    food_percent = (food_cost / total_sales) * 100
    prime_percent = (prime_cost / total_sales) * 100
    sales_per_labor_hour = total_sales / hours_worked

    # Industry benchmarks for comparison
    industry_benchmarks = {
        "labor_percent": {"excellent": 25, "good": 30, "needs_improvement": 35},
        "food_percent": {"excellent": 28, "good": 32, "needs_improvement": 38},
        "prime_percent": {"excellent": 55, "good": 60, "needs_improvement": 65},
    }

    # Performance assessment
    def assess_performance(value, benchmarks):
        if value <= benchmarks["excellent"]:
            return "excellent", "🟢"
        elif value <= benchmarks["good"]:
            return "good", "🟡"
        else:
            return "needs_improvement", "🔴"

    labor_assessment, labor_icon = assess_performance(labor_percent, industry_benchmarks["labor_percent"])
    food_assessment, food_icon = assess_performance(food_percent, industry_benchmarks["food_percent"])
    prime_assessment, prime_icon = assess_performance(prime_percent, industry_benchmarks["prime_percent"])

    # Generate recommendations
    recommendations = []
    if labor_percent > 30:
        labor_gap_pts = labor_percent - 30
        est_over_target = (labor_gap_pts / 100) * total_sales
        recommendations.append(
            f"Labor is {labor_percent:.1f}% (benchmark ≤30%, +{labor_gap_pts:.1f} pts). "
            f"Each 1-pt is about ${total_sales/100:,.0f} at current sales; target savings ~${est_over_target:,.0f} by tightening schedules and overtime."
        )
    if food_percent > 32:
        food_gap_pts = food_percent - 32
        est_over_target = (food_gap_pts / 100) * total_sales
        recommendations.append(
            f"Food cost is {food_percent:.1f}% (benchmark ≤32%, +{food_gap_pts:.1f} pts). "
            f"That's ~${est_over_target:,.0f} above benchmark on current sales; prioritize portion control, waste tracking, and re-costing top items."
        )
    if prime_percent > 60:
        prime_gap_pts = prime_percent - 60
        est_over_target = (prime_gap_pts / 100) * total_sales
        recommendations.append(
            f"Prime cost is {prime_percent:.1f}% (benchmark ≤60%, +{prime_gap_pts:.1f} pts). "
            f"Closing this gap is worth ~${est_over_target:,.0f} on current sales — run weekly labor and recipe-cost reviews."
        )
    if sales_per_labor_hour < 50:
        splh_gap = 50 - sales_per_labor_hour
        est_revenue_uplift = splh_gap * hours_worked if splh_gap > 0 else 0
        recommendations.append(
            f"Sales per labor hour is ${sales_per_labor_hour:.2f} (goal $50+). "
            f"Improving by ${splh_gap:.0f}/hr could add ~${est_revenue_uplift:,.0f} in sales at current hours."
        )

    if not recommendations:
        recommendations.append("KPIs are within benchmark ranges. Maintain current controls and review these KPIs weekly to catch drift early.")

    # Generate business report using the new formatter
    kpi_data = {
        "labor_percent": {
            "title": "Labor Cost Percentage",
            "calculation": "(Labor Cost / Total Sales) × 100",
            "example": f"(${labor_cost:,.2f} / ${total_sales:,.2f}) × 100 = {labor_percent:.1f}%",
            "interpretation": f"Your labor cost percentage of {labor_percent:.1f}% is {labor_assessment} compared to industry standards of 25-30%.",
            "recommendations": [rec for rec in recommendations if "labor" in rec.lower() or "staff" in rec.lower() or "scheduling" in rec.lower()]
        },
        "food_percent": {
            "title": "Food Cost Percentage",
            "calculation": "(Food Cost / Total Sales) × 100",
            "example": f"(${food_cost:,.2f} / ${total_sales:,.2f}) × 100 = {food_percent:.1f}%",
            "interpretation": f"Your food cost percentage of {food_percent:.1f}% is {food_assessment} compared to industry standards of 28-32%.",
            "recommendations": [rec for rec in recommendations if "food" in rec.lower() or "menu" in rec.lower() or "pricing" in rec.lower()]
        },
        "prime_percent": {
            "title": "Prime Cost Percentage",
            "calculation": "((Labor Cost + Food Cost) / Total Sales) × 100",
            "example": f"(${prime_cost:,.2f} / ${total_sales:,.2f}) × 100 = {prime_percent:.1f}%",
            "interpretation": f"Your prime cost percentage of {prime_percent:.1f}% is {prime_assessment} compared to industry standards of 55-60%.",
            "recommendations": [rec for rec in recommendations if "prime" in rec.lower() or "cost" in rec.lower()]
        },
        "sales_per_labor_hour": {
            "title": "Sales per Labor Hour",
            "calculation": "Total Sales / Labor Hours",
            "example": f"${total_sales:,.2f} / {hours_worked:.0f} hours = ${sales_per_labor_hour:.2f} per hour",
            "interpretation": f"Your sales per labor hour of ${sales_per_labor_hour:.2f} is {'excellent' if sales_per_labor_hour > 50 else 'good' if sales_per_labor_hour > 40 else 'needs improvement'} compared to industry standards of $50+/hour.",
            "recommendations": [rec for rec in recommendations if "productivity" in rec.lower() or "sales" in rec.lower() or "training" in rec.lower()]
        }
    }

    # Generate report (now returns dict with text and html)
    report_result = format_comprehensive_analysis('kpi', kpi_data)
    
    # Extract text and html versions
    business_report_text = report_result.get("text", "") if isinstance(report_result, dict) else report_result
    business_report_html = report_result.get("html", "") if isinstance(report_result, dict) else ""

    return {
        "status": "success",
        "summary": {
            "total_sales": f"${total_sales:,.2f}",
            "prime_cost": f"${prime_cost:,.2f}",
            "prime_percent": f"{prime_percent:.1f}%",
        },
        "kpis": {
            "labor_percent": {
                "value": round(labor_percent, 2),
                "assessment": labor_assessment,
                "icon": labor_icon,
                "benchmark": "25-30%",
            },
            "food_percent": {
                "value": round(food_percent, 2),
                "assessment": food_assessment,
                "icon": food_icon,
                "benchmark": "28-32%",
            },
            "prime_percent": {
                "value": round(prime_percent, 2),
                "assessment": prime_assessment,
                "icon": prime_icon,
                "benchmark": "55-60%",
            },
            "sales_per_labor_hour": {
                "value": round(sales_per_labor_hour, 2),
                "assessment": (
                    "excellent" if sales_per_labor_hour > 50 else "good" if sales_per_labor_hour > 40 else "needs_improvement"
                ),
                "icon": "🟢" if sales_per_labor_hour > 50 else "🟡" if sales_per_labor_hour > 40 else "🔴",
                "benchmark": "$50+/hour",
            },
        },
        "recommendations": recommendations,
        "industry_benchmarks": industry_benchmarks,
        "business_report": business_report_text,
        "business_report_html": business_report_html
    }


def process_kpi_csv_data(csv_file) -> Dict[str, Any]:
    """
    Process uploaded CSV file for comprehensive KPI analysis

    Expected CSV columns: date, sales, labor_cost, food_cost, labor_hours
    """
    try:
        df = pd.read_csv(csv_file)
        
        # Debug: log original columns
        original_columns = list(df.columns)

        # Flexible column mapping
        column_mapping = {
            "sales": ["sales", "revenue", "total_sales", "daily_sales"],
            "labor_cost": ["labor_cost", "labor", "wages", "payroll"],
            "food_cost": ["food_cost", "cogs", "cost_of_goods", "food"],
            "labor_hours": ["labor_hours", "hours", "hours_worked", "staff_hours", "labor_hour"],
        }

        # Find matching columns
        mapped_columns = {}
        for target, variations in column_mapping.items():
            for col in df.columns:
                col_lower = col.lower().strip()
                if any(var.lower() == col_lower or var.lower() in col_lower for var in variations):
                    mapped_columns[target] = col
                    break

        # Check for required columns
        missing_columns = [col for col in column_mapping.keys() if col not in mapped_columns]
        if missing_columns:
            # Check if this looks like a different type of file
            file_type_hint = ""
            col_lower = [c.lower() for c in original_columns]
            if any('recipe' in c for c in col_lower) or any('ingredient' in c for c in col_lower):
                file_type_hint = " This looks like a Recipe Management file - please use the Recipe Builder page for recipe analysis."
            elif any('menu' in c for c in col_lower) or any('item' in c for c in col_lower):
                file_type_hint = " This looks like a Menu Engineering file - please use the Menu Engineering page for product mix analysis."
            elif any('inventory' in c for c in col_lower) or any('stock' in c for c in col_lower):
                file_type_hint = " This looks like an Inventory file - please use the appropriate inventory analysis page."
            
            return {
                "status": "error",
                "message": f"Missing required columns: {', '.join(missing_columns)}.{file_type_hint}",
                "found_columns": original_columns,
                "mapped_columns": mapped_columns,
                "help": "KPI Analysis requires a CSV with columns: date, sales, labor_cost, food_cost, labor_hours. Example: kpi_analysis.csv in the Dataset folder.",
                "expected_format": {
                    "required_columns": ["date", "sales", "labor_cost", "food_cost", "labor_hours"],
                    "example_row": {"date": "2025-01-01", "sales": 7052, "labor_cost": 1647, "food_cost": 2232, "labor_hours": 76}
                }
            }

        # Preserve date column if it exists
        date_col = None
        for col in df.columns:
            if 'date' in col.lower():
                date_col = col
                break

        # Clean and process data - create new columns with standardized names
        df_clean = df.copy()
        for target, source_col in mapped_columns.items():
            df_clean[target] = pd.to_numeric(df_clean[source_col], errors="coerce").fillna(0)

        # Calculate daily KPIs
        daily_kpis = []
        error_count = 0
        for idx, row in df_clean.iterrows():
            try:
                sales_val = float(row["sales"])
                labor_cost_val = float(row["labor_cost"])
                food_cost_val = float(row["food_cost"])
                labor_hours_val = float(row["labor_hours"])
                
                # Skip rows with zero or negative values
                if sales_val <= 0 or labor_hours_val <= 0:
                    continue
                    
                daily_kpi = calculate_kpi_summary(sales_val, labor_cost_val, food_cost_val, labor_hours_val)
                if daily_kpi.get("status") == "success":
                    # Get date from original column or use index
                    date_value = str(row[date_col]) if date_col and date_col in row.index else f"Day {idx + 1}"
                    daily_kpis.append(
                        {
                            "date": date_value,
                            "sales": sales_val,
                            "labor_percent": daily_kpi["kpis"]["labor_percent"]["value"],
                            "food_percent": daily_kpi["kpis"]["food_percent"]["value"],
                            "prime_percent": daily_kpi["kpis"]["prime_percent"]["value"],
                            "sales_per_hour": daily_kpi["kpis"]["sales_per_labor_hour"]["value"],
                        }
                    )
                else:
                    error_count += 1
            except Exception as row_error:
                error_count += 1
                continue

        if not daily_kpis:
            return {
                "status": "error",
                "message": f"No valid data found in CSV. Processed {len(df)} rows, {error_count} had errors.",
                "found_columns": original_columns,
                "mapped_columns": mapped_columns,
                "help": "Please ensure your CSV has positive values for sales and labor_hours. Check that numeric columns don't contain text.",
                "sample_row": df.head(1).to_dict('records')[0] if len(df) > 0 else {}
            }

        # Calculate averages and trends
        avg_labor_percent = sum(kpi["labor_percent"] for kpi in daily_kpis) / len(daily_kpis)
        avg_food_percent = sum(kpi["food_percent"] for kpi in daily_kpis) / len(daily_kpis)
        avg_prime_percent = sum(kpi["prime_percent"] for kpi in daily_kpis) / len(daily_kpis)
        avg_sales_per_hour = sum(kpi["sales_per_hour"] for kpi in daily_kpis) / len(daily_kpis)
        total_sales = sum(kpi["sales"] for kpi in daily_kpis)

        # Calculate trends (comparing first half vs second half)
        mid_point = max(1, len(daily_kpis) // 2)  # Ensure at least 1 to avoid division by zero
        first_half_avg = sum(kpi["prime_percent"] for kpi in daily_kpis[:mid_point]) / mid_point if mid_point > 0 else 0
        second_half_count = len(daily_kpis) - mid_point
        second_half_avg = sum(kpi["prime_percent"] for kpi in daily_kpis[mid_point:]) / second_half_count if second_half_count > 0 else 0
        trend = (
            "improving" if second_half_avg < first_half_avg else "declining" if second_half_avg > first_half_avg else "stable"
        )

        # Generate base recommendations
        recommendations = generate_kpi_recommendations(
            avg_labor_percent, avg_food_percent, avg_prime_percent, avg_sales_per_hour
        )
        
        # Try to get AI-powered analysis
        ai_analysis = None
        try:
            ai_analysis = generate_ai_kpi_analysis(
                total_sales=total_sales,
                avg_labor_percent=avg_labor_percent,
                avg_food_percent=avg_food_percent,
                avg_prime_percent=avg_prime_percent,
                avg_sales_per_hour=avg_sales_per_hour,
                trend=trend,
                num_days=len(daily_kpis),
                daily_data=daily_kpis[:10]  # Send first 10 days for pattern analysis
            )
        except Exception as e:
            ai_analysis = f"AI analysis unavailable: {str(e)}"
        
        # Build KPI business report for consistent frontend rendering
        def _rating_from_kpis(labor_pct, food_pct, prime_pct):
            if labor_pct <= 30 and food_pct <= 32 and prime_pct <= 55:
                return "Excellent", "blue"
            if labor_pct <= 32 and food_pct <= 34 and prime_pct <= 60:
                return "Good", "green"
            if labor_pct <= 35 and food_pct <= 36 and prime_pct <= 65:
                return "Acceptable", "orange"
            return "Needs Improvement", "red"

        perf_rating, perf_color = _rating_from_kpis(avg_labor_percent, avg_food_percent, avg_prime_percent)
        metrics = {
            "Total Sales": total_sales,
            "Average Labor Percent": avg_labor_percent,
            "Average Food Percent": avg_food_percent,
            "Average Prime Percent": avg_prime_percent,
            "Average Sales per Labor Hour": avg_sales_per_hour,
            "Days Analyzed": len(daily_kpis)
        }

        rec_lines = []
        for rec in recommendations:
            if isinstance(rec, dict):
                parts = []
                if rec.get("category"):
                    parts.append(rec["category"])
                if rec.get("action"):
                    parts.append(rec["action"])
                if rec.get("impact"):
                    parts.append(f"Impact: {rec['impact']}")
                rec_lines.append(" - ".join(parts) if parts else str(rec))
            else:
                rec_lines.append(str(rec))

        additional_data = {
            "Trend": trend,
            "AI Analysis": ai_analysis
        }

        business_report = format_business_report(
            analysis_type="KPI Analysis",
            metrics=metrics,
            performance={"rating": perf_rating, "color": perf_color},
            recommendations=rec_lines,
            benchmarks={
                "Labor %": "25-30% (Target Range)",
                "Food %": "28-32% (Target Range)",
                "Prime %": "55-60% (Target Range)",
                "Sales per Labor Hour": "$50+/hour (Target)"
            },
            additional_data=additional_data
        )

        return {
            "status": "success",
            "file_info": csv_file.name,
            "period_analyzed": f"{len(daily_kpis)} days",
            "summary": {
                "total_sales": f"${total_sales:,.2f}",
                "avg_labor_percent": f"{avg_labor_percent:.1f}%",
                "avg_food_percent": f"{avg_food_percent:.1f}%",
                "avg_prime_percent": f"{avg_prime_percent:.1f}%",
                "avg_sales_per_hour": f"${avg_sales_per_hour:.2f}",
                "trend": trend,
            },
            "daily_kpis": daily_kpis[:30],  # Show last 30 days
            "recommendations": recommendations,
            "ai_analysis": ai_analysis,
            "business_report": business_report.get("business_report"),
            "business_report_html": business_report.get("business_report_html"),
            "analysis_type": business_report.get("analysis_type"),
            "performance_rating": business_report.get("performance_rating"),
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"CSV processing error: {str(e)}",
            "help": "Please ensure your CSV has columns: date, sales, labor_cost, food_cost, labor_hours",
        }


def generate_kpi_recommendations(labor_percent, food_percent, prime_percent, sales_per_hour):
    """Generate actionable recommendations based on KPI analysis"""
    recommendations = []

    if labor_percent > 30:
        labor_gap_pts = labor_percent - 30
        recommendations.append(
            {
                "category": "Labor Optimization",
                "priority": "High",
                "action": "Review staff scheduling and reduce overtime",
                "impact": f"Could save about ${labor_gap_pts * 100:.0f} per $10k in sales (each 1-pt ≈ $100)",
            }
        )

    if food_percent > 32:
        food_gap_pts = food_percent - 32
        recommendations.append(
            {
                "category": "Food Cost Control",
                "priority": "High",
                "action": "Audit portion sizes and supplier pricing",
                "impact": f"Could save about ${food_gap_pts * 100:.0f} per $10k in sales (each 1-pt ≈ $100)",
            }
        )

    if sales_per_hour < 50:
        recommendations.append(
            {
                "category": "Sales Performance",
                "priority": "Medium",
                "action": "Improve staff training and upselling techniques",
                "impact": "Could increase revenue by 15-20%",
            }
        )

    if prime_percent > 60:
        prime_gap_pts = prime_percent - 60
        recommendations.append(
            {
                "category": "Overall Efficiency",
                "priority": "Critical",
                "action": "Focus on both labor and food cost optimization",
                "impact": f"Prime cost is +{prime_gap_pts:.1f} pts vs 60% benchmark — prioritize weekly labor + recipe-cost routines",
            }
        )

    if not recommendations:
        recommendations.append(
            {
                "category": "Performance",
                "priority": "Maintain",
                "action": "Keep up the excellent work!",
                "impact": "Your KPIs are within industry standards",
            }
        )

    return recommendations


def calculate_liquor_cost_analysis(expected_oz, actual_oz, liquor_cost, total_sales, bottle_cost=0.0, bottle_size_oz=25.0, target_cost_percentage=20.0):
    """
    Calculate comprehensive liquor cost analysis with business report.

    Args:
        expected_oz: Expected liquor usage in ounces
        actual_oz: Actual liquor usage in ounces
        liquor_cost: Total liquor cost
        total_sales: Total sales revenue
        bottle_cost: Cost per bottle
        bottle_size_oz: Bottle size in ounces
        target_cost_percentage: Target liquor cost percentage

    Returns:
        Dictionary with analysis results and business report
    """
    # Calculate key metrics
    variance_oz = actual_oz - expected_oz
    variance_percent = (variance_oz / expected_oz * 100) if expected_oz > 0 else 0

    cost_per_oz = (liquor_cost / actual_oz) if actual_oz > 0 else 0
    liquor_cost_percentage = (liquor_cost / total_sales * 100) if total_sales > 0 else 0

    # Calculate theoretical usage and waste
    theoretical_cost = expected_oz * cost_per_oz
    waste_cost = liquor_cost - theoretical_cost
    waste_percentage = (waste_cost / liquor_cost * 100) if liquor_cost > 0 else 0

    # Performance assessment
    if abs(variance_percent) <= 5 and liquor_cost_percentage <= target_cost_percentage:
        rating = "Excellent"
    elif abs(variance_percent) <= 10 and liquor_cost_percentage <= target_cost_percentage + 2:
        rating = "Good"
    elif abs(variance_percent) <= 15 and liquor_cost_percentage <= target_cost_percentage + 5:
        rating = "Acceptable"
    else:
        rating = "Needs Improvement"

    # Metrics dictionary
    metrics = {
        "expected_oz": expected_oz,
        "actual_oz": actual_oz,
        "variance_oz": variance_oz,
        "variance_percent": variance_percent,
        "liquor_cost": liquor_cost,
        "cost_per_oz": cost_per_oz,
        "liquor_cost_percentage": liquor_cost_percentage,
        "waste_cost": waste_cost,
        "waste_percentage": waste_percentage
    }

    # Performance dictionary
    performance = {
        "rating": rating,
        "variance_status": "Within Target" if abs(variance_percent) <= 5 else "Needs Attention" if abs(variance_percent) <= 10 else "Critical",
        "cost_status": "Optimal" if liquor_cost_percentage <= target_cost_percentage else "High" if liquor_cost_percentage <= target_cost_percentage + 2 else "Critical"
    }

    # Generate recommendations
    recommendations = []

    if abs(variance_percent) > 10:
        recommendations.append(
            f"Liquor usage variance is {variance_percent:.1f}% ({variance_oz:.0f} oz) vs expected. "
            "Tighten pours to bring variance toward ±5% using jiggers/spouts and shift-by-shift variance review."
        )
        recommendations.append(
            "Implement daily bar inventory (open/close counts) and retrain on standard pours/comp tracking to reduce unexplained variance."
        )

    if liquor_cost_percentage > target_cost_percentage:
        target_liquor_cost = total_sales * (target_cost_percentage / 100) if total_sales > 0 else 0
        over_target_cost = liquor_cost - target_liquor_cost
        recommendations.append(
            f"Liquor cost is {liquor_cost_percentage:.1f}% vs {target_cost_percentage:.1f}% target (+{(liquor_cost_percentage - target_cost_percentage):.1f} pts). "
            f"That's ~${over_target_cost:,.0f} above target on current sales — review pricing, comps, and purchasing."
        )
        recommendations.append("Renegotiate top SKUs, standardize pour costs, and validate menu pricing for low-margin drinks.")

    if waste_percentage > 5:
        recommendations.append(
            f"Waste is {waste_percentage:.1f}% (~${waste_cost:,.0f}). "
            "Track waste by reason (spills, comps, expired, over-pours) and fix the top 2 drivers."
        )
        recommendations.append("Review storage/handling and tighten open-bottle rotation to reduce spoilage and breakage.")

    if variance_percent < -10:
        recommendations.append(
            "Variance is materially below expected. Double-check counts and investigate potential reporting issues (voids/comps not logged) or shrink."
        )
        recommendations.append("Standardize counting procedure and require manager sign-off on daily variances.")

    if not recommendations:
        recommendations.append("Maintain current liquor cost management practices")
        recommendations.append("Continue monitoring variance trends")

    # Industry benchmarks
    benchmarks = {
        "target_cost_percentage": target_cost_percentage,
        "acceptable_variance": "±5%",
        "industry_average_cost_percentage": "18-22%"
    }

    # Additional insights
    additional_data = {
        "cost_efficiency": {
            "theoretical_cost": f"${theoretical_cost:.2f}",
            "actual_cost": f"${liquor_cost:.2f}",
            "efficiency_ratio": f"{(theoretical_cost/liquor_cost*100):.1f}%" if liquor_cost > 0 else "N/A"
        },
        "waste_analysis": {
            "waste_cost": f"${waste_cost:.2f}",
            "waste_percentage": f"{waste_percentage:.1f}%",
            "monthly_waste_impact": f"${waste_cost * 30:.2f}"
        }
    }

    # Generate business report
    business_report_result = format_business_report(
        "Liquor Cost Analysis",
        metrics,
        performance,
        recommendations,
        benchmarks,
        additional_data
    )

    business_report_html = business_report_result.get("business_report_html", "")
    business_report = business_report_result.get("business_report", "")
    analysis_type = business_report_result.get("analysis_type", "Liquor Cost Analysis")

    return {
        "status": "success",
        "analysis_type": analysis_type,
        "metrics": metrics,
        "performance": performance,
        "recommendations": recommendations,
        "industry_benchmarks": benchmarks,
        "business_report_html": business_report_html,
        "business_report": business_report
    }


def calculate_inventory_analysis(current_stock, reorder_point, monthly_usage, inventory_value, lead_time_days=7.0, safety_stock=0.0, item_cost=0.0, target_turnover=12.0):
    """
    Calculate comprehensive inventory analysis with business report.

    Args:
        current_stock: Current inventory level
        reorder_point: Reorder point level
        monthly_usage: Monthly usage rate
        inventory_value: Total inventory value
        lead_time_days: Lead time in days
        safety_stock: Safety stock level
        item_cost: Cost per item
        target_turnover: Target inventory turnover rate

    Returns:
        Dictionary with analysis results and business report
    """
    # Calculate key metrics
    days_of_stock = (current_stock / monthly_usage * 30) if monthly_usage > 0 else 0
    reorder_status = "Order Now" if current_stock <= reorder_point else "Adequate Stock"

    # Calculate optimal reorder point
    daily_usage = monthly_usage / 30
    optimal_reorder_point = (daily_usage * lead_time_days) + safety_stock

    # Calculate turnover rate
    annual_usage = monthly_usage * 12
    turnover_rate = (annual_usage / current_stock) if current_stock > 0 else 0

    # Calculate carrying cost
    carrying_cost_percentage = 25.0  # Industry standard
    annual_carrying_cost = inventory_value * (carrying_cost_percentage / 100)

    # Performance assessment
    if turnover_rate >= target_turnover and current_stock > reorder_point:
        rating = "Excellent"
    elif turnover_rate >= target_turnover * 0.8 and current_stock > reorder_point * 0.8:
        rating = "Good"
    elif turnover_rate >= target_turnover * 0.6 and current_stock > reorder_point * 0.6:
        rating = "Acceptable"
    else:
        rating = "Needs Improvement"

    # Metrics dictionary
    metrics = {
        "current_stock": current_stock,
        "reorder_point": reorder_point,
        "monthly_usage": monthly_usage,
        "inventory_value": inventory_value,
        "days_of_stock": days_of_stock,
        "turnover_rate": turnover_rate,
        "optimal_reorder_point": optimal_reorder_point,
        "carrying_cost": annual_carrying_cost
    }

    # Performance dictionary
    performance = {
        "rating": rating,
        "stock_status": reorder_status,
        "turnover_status": "Optimal" if turnover_rate >= target_turnover else "Low" if turnover_rate >= target_turnover * 0.8 else "Critical"
    }

    # Generate recommendations
    recommendations = []

    if current_stock <= reorder_point:
        recommendations.append(
            f"Stock is at/below reorder point ({current_stock:.0f} ≤ {reorder_point:.0f}). "
            "Place an immediate reorder to prevent stockouts."
        )
        recommendations.append("If this is recurring, increase safety stock or confirm lead time assumptions with suppliers.")

    if turnover_rate < target_turnover * 0.8:
        recommendations.append(
            f"Turnover is low ({turnover_rate:.1f} vs target {target_turnover:.1f}). "
            "Reduce dead stock: slow-mover promos, tighter par levels, and smaller reorder quantities."
        )
        recommendations.append("Focus purchasing on fast movers and consolidate SKUs to reduce holding costs.")

    if days_of_stock > 45:
        recommendations.append(
            f"Days of stock is high ({days_of_stock:.0f} days). "
            "Reduce order quantities to improve cash flow and lower carrying costs."
        )
        recommendations.append("Move toward smaller, more frequent reorders for predictable items.")

    if abs(optimal_reorder_point - reorder_point) > reorder_point * 0.2:
        recommendations.append(
            f"Reorder point may be mis-set (current {reorder_point:.0f} vs optimal {optimal_reorder_point:.0f}). "
            "Update reorder point and revalidate lead times."
        )
        recommendations.append("Re-check usage rates and supplier delivery reliability before locking in new pars.")

    if not recommendations:
        recommendations.append("Maintain current inventory management practices")
        recommendations.append("Continue monitoring turnover trends")

    # Industry benchmarks
    benchmarks = {
        "target_turnover": target_turnover,
        "optimal_days_of_stock": "15-30 days",
        "industry_carrying_cost": "20-30%"
    }

    # Additional insights
    additional_data = {
        "efficiency_metrics": {
            "stockout_risk": "Low" if current_stock > reorder_point * 1.5 else "Medium" if current_stock > reorder_point else "High",
            "cash_flow_impact": f"${inventory_value * 0.25:.2f} annual carrying cost",
            "reorder_frequency": f"{30/days_of_stock:.1f} times per month" if days_of_stock > 0 else "N/A"
        },
        "optimization_potential": {
            "potential_savings": f"${annual_carrying_cost * 0.2:.2f}",
            "improvement_area": "Turnover Rate" if turnover_rate < target_turnover else "Carrying Cost",
            "next_review_date": "30 days"
        }
    }

    # Generate business report
    business_report_result = format_business_report(
        "Bar Inventory Analysis",
        metrics,
        performance,
        recommendations,
        benchmarks,
        additional_data
    )

    business_report_html = business_report_result.get("business_report_html", "")
    business_report = business_report_result.get("business_report", "")
    analysis_type = business_report_result.get("analysis_type", "Bar Inventory Analysis")

    return {
        "status": "success",
        "analysis_type": analysis_type,
        "metrics": metrics,
        "performance": performance,
        "recommendations": recommendations,
        "industry_benchmarks": benchmarks,
        "business_report_html": business_report_html,
        "business_report": business_report
    }


def calculate_pricing_analysis(drink_price, cost_per_drink, sales_volume, competitor_price, target_margin=75.0, market_position="premium", elasticity_factor=1.5):
    """
    Calculate comprehensive pricing analysis with business report.

    Args:
        drink_price: Current drink price
        cost_per_drink: Cost per drink
        sales_volume: Monthly sales volume
        competitor_price: Competitor's price
        target_margin: Target margin percentage
        market_position: Market position (premium, standard, value)
        elasticity_factor: Price elasticity factor

    Returns:
        Dictionary with analysis results and business report
    """
    # Calculate key metrics
    current_margin = ((drink_price - cost_per_drink) / drink_price * 100) if drink_price > 0 else 0
    margin_difference = current_margin - target_margin

    # Calculate optimal price
    optimal_price = cost_per_drink / (1 - target_margin / 100) if target_margin < 100 else cost_per_drink * 2

    # Calculate competitive position
    price_vs_competitor = ((drink_price - competitor_price) / competitor_price * 100) if competitor_price > 0 else 0

    # Calculate revenue impact
    current_revenue = drink_price * sales_volume
    optimal_revenue = optimal_price * sales_volume

    # Calculate elasticity impact
    price_change_percent = ((optimal_price - drink_price) / drink_price * 100) if drink_price > 0 else 0
    volume_change_percent = -price_change_percent * elasticity_factor
    new_volume = sales_volume * (1 + volume_change_percent / 100)
    elasticity_revenue = optimal_price * new_volume

    # Performance assessment
    if current_margin >= target_margin and abs(price_vs_competitor) <= 10:
        rating = "Excellent"
    elif current_margin >= target_margin * 0.9 and abs(price_vs_competitor) <= 20:
        rating = "Good"
    elif current_margin >= target_margin * 0.8 and abs(price_vs_competitor) <= 30:
        rating = "Acceptable"
    else:
        rating = "Needs Improvement"

    # Metrics dictionary
    metrics = {
        "drink_price": drink_price,
        "cost_per_drink": cost_per_drink,
        "current_margin": current_margin,
        "target_margin": target_margin,
        "margin_difference": margin_difference,
        "optimal_price": optimal_price,
        "competitor_price": competitor_price,
        "price_vs_competitor": price_vs_competitor,
        "sales_volume": sales_volume,
        "current_revenue": current_revenue,
        "optimal_revenue": optimal_revenue,
        "elasticity_revenue": elasticity_revenue
    }

    # Performance dictionary
    performance = {
        "rating": rating,
        "margin_status": "Optimal" if current_margin >= target_margin else "Low" if current_margin >= target_margin * 0.8 else "Critical",
        "competitive_status": "Competitive" if abs(price_vs_competitor) <= 10 else "Premium" if price_vs_competitor > 10 else "Value"
    }

    # Generate recommendations
    recommendations = []

    if current_margin < target_margin:
        recommendations.append(
            f"Margin is {current_margin:.1f}% vs {target_margin:.1f}% target (-{abs(margin_difference):.1f} pts). "
            f"A price of ~${optimal_price:.2f} (from ${drink_price:.2f}) would hit the target margin at current costs."
        )
        recommendations.append("If you cannot raise price, reduce cost per drink via supplier renegotiation, batch prep, or portion control.")

    if price_vs_competitor > 20:
        recommendations.append(
            f"Price is {price_vs_competitor:.0f}% above competitor. "
            "Either reprice closer to market or justify the premium with differentiated menu design, service, and presentation."
        )

    if price_vs_competitor < -20:
        recommendations.append(
            f"Price is {abs(price_vs_competitor):.0f}% below competitor. "
            "You likely have room to raise price in small steps while monitoring volume and guest feedback."
        )

    if elasticity_revenue > current_revenue * 1.1:
        uplift = elasticity_revenue - current_revenue
        recommendations.append(
            f"Elasticity model suggests pricing optimization could lift revenue by ~${uplift:,.0f} at current volume assumptions. "
            "Test small increments and track unit mix weekly."
        )

    if market_position == "premium" and price_vs_competitor < 0:
        recommendations.append("Align pricing with premium market positioning")
        recommendations.append("Enhance product presentation and service quality")

    if not recommendations:
        recommendations.append("Maintain current pricing strategy")
        recommendations.append("Continue monitoring competitive landscape")

    # Industry benchmarks
    benchmarks = {
        "target_margin": target_margin,
        "industry_margin_range": "70-80%",
        "competitive_tolerance": "±10%"
    }

    # Additional insights
    additional_data = {
        "pricing_strategy": {
            "market_position": market_position.title(),
            "elasticity_factor": elasticity_factor,
            "recommended_action": "Maintain" if rating == "Excellent" else "Optimize" if rating == "Good" else "Review"
        },
        "revenue_optimization": {
            "current_monthly_revenue": f"${current_revenue:,.2f}",
            "potential_increase": f"${max(optimal_revenue, elasticity_revenue) - current_revenue:,.2f}",
            "roi_timeline": "Immediate"
        }
    }

    # Generate business report
    business_report_result = format_business_report(
        "Beverage Pricing Analysis",
        metrics,
        performance,
        recommendations,
        benchmarks,
        additional_data
    )

    business_report_html = business_report_result.get("business_report_html", "")
    business_report = business_report_result.get("business_report", "")
    analysis_type = business_report_result.get("analysis_type", "Beverage Pricing Analysis")

    return {
        "status": "success",
        "analysis_type": analysis_type,
        "metrics": metrics,
        "performance": performance,
        "recommendations": recommendations,
        "industry_benchmarks": benchmarks,
        "business_report_html": business_report_html,
        "business_report": business_report
    }
