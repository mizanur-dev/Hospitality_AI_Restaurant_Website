"""
Recipe Analysis Functions
Contains the core business logic for recipe management analysis.
"""

from backend.consulting_services.kpi.kpi_utils import format_business_report
import pandas as pd
import io
from typing import Dict, Any, List


def _price_for_margin(cost: float, target_margin_pct: float) -> float:
    """Return the minimum price needed to achieve a target margin given a cost."""
    try:
        m = float(target_margin_pct) / 100.0
        if m >= 1:
            return 0.0
        return float(cost) / (1.0 - m)
    except Exception:
        return 0.0


def calculate_recipe_costing_analysis(ingredient_cost, portion_cost, recipe_price, total_cost, portion_size=1.0, servings=1.0, target_margin=70.0, labor_cost=0.0):
    """Calculate comprehensive recipe costing analysis with business report."""
    # Calculate key metrics
    total_recipe_cost = ingredient_cost + labor_cost
    cost_per_portion = total_recipe_cost / servings if servings > 0 else total_recipe_cost
    profit_margin = ((recipe_price - cost_per_portion) / recipe_price * 100) if recipe_price > 0 else 0
    margin_difference = profit_margin - target_margin

    # Calculate cost efficiency
    ingredient_cost_percentage = (ingredient_cost / total_recipe_cost * 100) if total_recipe_cost > 0 else 0
    labor_cost_percentage = (labor_cost / total_recipe_cost * 100) if total_recipe_cost > 0 else 0

    # Performance assessment
    if profit_margin >= target_margin and ingredient_cost_percentage <= 60:
        rating = "Excellent"
    elif profit_margin >= target_margin * 0.9 and ingredient_cost_percentage <= 70:
        rating = "Good"
    elif profit_margin >= target_margin * 0.8 and ingredient_cost_percentage <= 80:
        rating = "Acceptable"
    else:
        rating = "Needs Improvement"

    # Metrics dictionary
    metrics = {
        "ingredient_cost": ingredient_cost,
        "portion_cost": portion_cost,
        "recipe_price": recipe_price,
        "total_cost": total_cost,
        "portion_size": portion_size,
        "servings": servings,
        "total_recipe_cost": total_recipe_cost,
        "cost_per_portion": cost_per_portion,
        "profit_margin": profit_margin,
        "margin_difference": margin_difference,
        "ingredient_cost_percentage": ingredient_cost_percentage,
        "labor_cost_percentage": labor_cost_percentage
    }

    # Performance dictionary
    performance = {
        "rating": rating,
        "margin_status": "Optimal" if profit_margin >= target_margin else "Low" if profit_margin >= target_margin * 0.8 else "Critical",
        "cost_efficiency": "High" if ingredient_cost_percentage <= 60 else "Medium" if ingredient_cost_percentage <= 70 else "Low"
    }

    # Generate recommendations
    recommendations = []

    price_needed = _price_for_margin(cost_per_portion, target_margin)
    price_delta = max(0.0, price_needed - recipe_price) if recipe_price > 0 else 0.0
    target_cost_at_price = recipe_price * (1.0 - (target_margin / 100.0)) if recipe_price > 0 else 0.0
    cost_reduction_needed = max(0.0, cost_per_portion - target_cost_at_price) if target_cost_at_price > 0 else 0.0

    if profit_margin < target_margin:
        if recipe_price > 0 and price_needed > 0:
            recommendations.append(
                f"To reach a {target_margin:.0f}% target margin at the current cost (${cost_per_portion:.2f}/portion), price needs to be about ${price_needed:.2f} (increase ≈ ${price_delta:.2f})."
            )
        if cost_reduction_needed > 0:
            recommendations.append(
                f"If you prefer not to raise price, reduce cost by about ${cost_reduction_needed:.2f} per portion (portioning, prep yield, or ingredient substitutions)."
            )

    if ingredient_cost_percentage > 70:
        recommendations.append(
            f"Ingredient cost is {ingredient_cost_percentage:.1f}% of total recipe cost. Negotiate pricing on the top 3 cost drivers and tighten portion controls (scales/scoops)."
        )

    if labor_cost_percentage > 30:
        recommendations.append(
            f"Labor cost is {labor_cost_percentage:.1f}% of total recipe cost. Reduce touches: batch prep where possible and standardize steps to shorten prep time."
        )

    if cost_per_portion > recipe_price * 0.4:
        recommendations.append(
            "Cost per portion is high relative to price. Review recipe formulation for cost (trim waste, swap high-cost inputs) without changing guest-perceived value."
        )

    if not recommendations:
        recommendations.append("Maintain current recipe costing strategy")
        recommendations.append("Continue monitoring cost trends and margins")

    # Industry benchmarks
    benchmarks = {
        "target_margin": target_margin,
        "optimal_ingredient_cost": "50-60%",
        "optimal_labor_cost": "20-30%"
    }

    # Additional insights
    additional_data = {
        "cost_optimization": {
            "potential_savings": f"${max(0, (target_margin - profit_margin) * recipe_price / 100):.2f}",
            "cost_per_serving": f"${cost_per_portion:.2f}",
            "margin_improvement": f"{max(0, target_margin - profit_margin):.1f}%"
        },
        "performance_insights": {
            "cost_trend": "Optimized" if profit_margin >= target_margin else "Needs Review",
            "efficiency_rating": "High" if ingredient_cost_percentage <= 60 else "Medium" if ingredient_cost_percentage <= 70 else "Low",
            "next_review": "30 days"
        }
    }

    # Generate business report
    business_report_result = format_business_report(
        "Recipe Costing Analysis",
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


def calculate_ingredient_optimization_analysis(current_cost, supplier_cost, waste_percentage, quality_score, usage_volume=0.0, supplier_count=1.0, consistency_score=8.0, storage_cost=0.0):
    """Calculate comprehensive ingredient optimization analysis with business report."""
    # Calculate key metrics
    cost_savings = current_cost - supplier_cost if supplier_cost > 0 else 0
    savings_percentage = (cost_savings / current_cost * 100) if current_cost > 0 else 0
    total_cost = current_cost + storage_cost
    optimization_score = (quality_score + consistency_score) / 2

    # Calculate efficiency metrics
    waste_cost = (waste_percentage / 100) * current_cost
    effective_cost = current_cost - waste_cost
    cost_per_unit = effective_cost / usage_volume if usage_volume > 0 else effective_cost

    # Performance assessment
    if savings_percentage >= 15 and optimization_score >= 8 and waste_percentage <= 5:
        rating = "Excellent"
    elif savings_percentage >= 10 and optimization_score >= 7 and waste_percentage <= 10:
        rating = "Good"
    elif savings_percentage >= 5 and optimization_score >= 6 and waste_percentage <= 15:
        rating = "Acceptable"
    else:
        rating = "Needs Improvement"

    # Metrics dictionary
    metrics = {
        "current_cost": current_cost,
        "supplier_cost": supplier_cost,
        "waste_percentage": waste_percentage,
        "quality_score": quality_score,
        "usage_volume": usage_volume,
        "supplier_count": supplier_count,
        "consistency_score": consistency_score,
        "storage_cost": storage_cost,
        "cost_savings": cost_savings,
        "savings_percentage": savings_percentage,
        "total_cost": total_cost,
        "optimization_score": optimization_score,
        "waste_cost": waste_cost,
        "effective_cost": effective_cost,
        "cost_per_unit": cost_per_unit
    }

    # Performance dictionary
    performance = {
        "rating": rating,
        "cost_status": "Optimized" if savings_percentage >= 15 else "Good" if savings_percentage >= 10 else "Needs Review",
        "quality_status": "High" if optimization_score >= 8 else "Medium" if optimization_score >= 7 else "Low"
    }

    # Generate recommendations
    recommendations = []

    if savings_percentage < 10:
        recommendations.append(
            f"Supplier savings are {savings_percentage:.1f}% (target 10–15%). Compare quotes and negotiate on the highest-volume items first (current ${current_cost:.2f} vs supplier ${supplier_cost:.2f})."
        )

    if waste_percentage > 10:
        recommendations.append(
            f"Waste is {waste_percentage:.1f}% (target ≤5%). Track waste reasons daily and adjust ordering/par levels; verify FIFO and storage temps to reduce spoilage."
        )

    if optimization_score < 7:
        recommendations.append(
            f"Quality/consistency score is {optimization_score:.1f}/10. Add receiving checks and a simple supplier scorecard (quality, consistency, on-time, price)."
        )

    if storage_cost > current_cost * 0.1:
        recommendations.append("Optimize storage and inventory management")
        recommendations.append("Consider just-in-time ordering")

    if supplier_count < 2:
        recommendations.append("Diversify supplier base to reduce risk")
        recommendations.append("Establish backup supplier relationships")

    if not recommendations:
        recommendations.append("Maintain current ingredient optimization strategy")
        recommendations.append("Continue monitoring supplier performance")

    # Industry benchmarks
    benchmarks = {
        "target_savings": "10-15%",
        "optimal_waste": "≤5%",
        "quality_threshold": "≥8.0"
    }

    # Additional insights
    additional_data = {
        "supplier_optimization": {
            "monthly_savings": f"${cost_savings * 30:.2f}",
            "annual_savings": f"${cost_savings * 365:.2f}",
            "roi_timeline": "Immediate"
        },
        "performance_insights": {
            "optimization_trend": "Improving" if savings_percentage >= 10 else "Stable" if savings_percentage >= 5 else "Declining",
            "quality_trend": "High" if optimization_score >= 8 else "Medium" if optimization_score >= 7 else "Low",
            "next_review": "30 days"
        }
    }

    # Generate business report
    business_report_result = format_business_report(
        "Ingredient Optimization Analysis",
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


def calculate_recipe_scaling_analysis(current_batch, target_batch, yield_percentage, consistency_score, base_recipe_cost=0.0, scaling_factor=1.0, quality_threshold=85.0, efficiency_score=8.0):
    """Calculate comprehensive recipe scaling analysis with business report."""
    # Calculate key metrics
    batch_difference = target_batch - current_batch
    scaling_ratio = target_batch / current_batch if current_batch > 0 else 1.0
    scaled_cost = base_recipe_cost * scaling_ratio
    cost_efficiency = (yield_percentage / 100) * (efficiency_score / 10)

    # Calculate scaling metrics
    yield_efficiency = yield_percentage / 100
    consistency_rating = consistency_score / 10
    scaling_score = (yield_efficiency + consistency_rating + (efficiency_score / 10)) / 3

    # Performance assessment
    if scaling_score >= 0.8 and yield_percentage >= 90 and consistency_score >= 8:
        rating = "Excellent"
    elif scaling_score >= 0.7 and yield_percentage >= 85 and consistency_score >= 7:
        rating = "Good"
    elif scaling_score >= 0.6 and yield_percentage >= 80 and consistency_score >= 6:
        rating = "Acceptable"
    else:
        rating = "Needs Improvement"

    # Metrics dictionary
    metrics = {
        "current_batch": current_batch,
        "target_batch": target_batch,
        "yield_percentage": yield_percentage,
        "consistency_score": consistency_score,
        "base_recipe_cost": base_recipe_cost,
        "scaling_factor": scaling_factor,
        "quality_threshold": quality_threshold,
        "efficiency_score": efficiency_score,
        "batch_difference": batch_difference,
        "scaling_ratio": scaling_ratio,
        "scaled_cost": scaled_cost,
        "cost_efficiency": cost_efficiency,
        "yield_efficiency": yield_efficiency,
        "consistency_rating": consistency_rating,
        "scaling_score": scaling_score
    }

    # Performance dictionary
    performance = {
        "rating": rating,
        "scaling_status": "Optimal" if scaling_score >= 0.8 else "Good" if scaling_score >= 0.7 else "Needs Work",
        "yield_status": "High" if yield_percentage >= 90 else "Medium" if yield_percentage >= 85 else "Low"
    }

    # Generate recommendations
    recommendations = []

    if yield_percentage < 85:
        recommendations.append(
            f"Yield is {yield_percentage:.0f}% (target 90%+). Identify the main loss point (trim, cook loss, holding) and retest with one controlled change at a time."
        )

    if consistency_score < 7:
        recommendations.append(
            f"Consistency score is {consistency_score:.1f}/10. Standardize measurement tools and add 2 checkpoints during peak production (prep and final seasoning/plating)."
        )

    if scaling_score < 0.7:
        recommendations.append(
            "Scaling performance is below target. Scale in smaller increments first and document any adjustments (cook time, seasoning, hydration) before going full batch."
        )

    if cost_efficiency < 0.7:
        recommendations.append(
            "Cost efficiency is low at the target batch size. Re-check the scaled ingredient ratios and consider batch sizing that better matches demand to avoid holding loss and waste."
        )

    if batch_difference > current_batch * 0.5:
        recommendations.append("Consider gradual scaling to maintain quality")
        recommendations.append("Test scaled recipes before full implementation")

    if not recommendations:
        recommendations.append("Maintain current recipe scaling strategy")
        recommendations.append("Continue monitoring scaling performance")

    # Industry benchmarks
    benchmarks = {
        "optimal_yield": "≥90%",
        "consistency_threshold": "≥8.0",
        "scaling_efficiency": "≥0.8"
    }

    # Additional insights
    additional_data = {
        "scaling_optimization": {
            "cost_per_unit": f"${scaled_cost / target_batch:.2f}",
            "efficiency_gain": f"{(scaling_score - 0.6) * 100:.1f}%",
            "quality_maintenance": "High" if consistency_score >= 8 else "Medium" if consistency_score >= 7 else "Low"
        },
        "performance_insights": {
            "scaling_trend": "Improving" if scaling_score >= 0.8 else "Stable" if scaling_score >= 0.7 else "Declining",
            "yield_trend": "High" if yield_percentage >= 90 else "Medium" if yield_percentage >= 85 else "Low",
            "next_review": "30 days"
        }
    }

    # Generate business report
    business_report_result = format_business_report(
        "Recipe Scaling Analysis",
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


def process_recipe_csv_data(csv_file) -> dict:
    """
    Process uploaded CSV file for comprehensive recipe management analysis.

    Expected CSV columns: recipe_name, ingredient_cost, portion_cost, recipe_price, servings, labor_cost
    """
    import pandas as pd
    import os
    from openai import OpenAI

    try:
        df = pd.read_csv(csv_file)

        # Flexible column mapping
        column_mapping = {
            "recipe_name": ["recipe_name", "name", "recipe", "item", "menu_item", "dish"],
            "ingredient_cost": ["ingredient_cost", "ingredients", "food_cost", "cost"],
            "portion_cost": ["portion_cost", "portion", "per_portion"],
            "recipe_price": ["recipe_price", "price", "selling_price", "menu_price", "sell_price"],
            "servings": ["servings", "portions", "yield", "serves", "quantity"],
            "labor_cost": ["labor_cost", "labor", "prep_cost", "preparation_cost"],
        }

        # Find matching columns
        mapped_columns = {}
        for target, variations in column_mapping.items():
            for col in df.columns:
                if any(var.lower() in col.lower() for var in variations):
                    mapped_columns[target] = col
                    break

        # Check for required columns (at least recipe_name and one cost metric)
        required = ["recipe_name"]
        cost_columns = ["ingredient_cost", "portion_cost", "recipe_price"]
        
        missing_required = [col for col in required if col not in mapped_columns]
        has_cost_column = any(col in mapped_columns for col in cost_columns)
        
        if missing_required or not has_cost_column:
            return {
                "status": "error",
                "message": f"Missing required columns. Need: recipe_name and at least one of ingredient_cost, portion_cost, recipe_price",
                "found_columns": list(df.columns),
                "help": "Please ensure your CSV has: recipe_name, ingredient_cost, portion_cost, recipe_price, servings, labor_cost",
            }

        # Clean and process data
        df_clean = df.copy()
        
        # Map columns
        for target, source_col in mapped_columns.items():
            if target == "recipe_name":
                df_clean[target] = df_clean[source_col].astype(str)
            else:
                df_clean[target] = pd.to_numeric(df_clean[source_col], errors="coerce").fillna(0)

        # Set defaults for missing optional columns
        for col in ["ingredient_cost", "portion_cost", "recipe_price", "servings", "labor_cost"]:
            if col not in mapped_columns:
                df_clean[col] = 0.0 if col != "servings" else 1.0

        # Analyze each recipe
        recipe_analyses = []
        total_recipes = 0
        profitable_count = 0
        needs_review_count = 0
        
        for _, row in df_clean.iterrows():
            total_recipes += 1
            recipe_name = row.get("recipe_name", f"Recipe {total_recipes}")
            ingredient_cost = float(row.get("ingredient_cost", 0))
            portion_cost = float(row.get("portion_cost", 0))
            recipe_price = float(row.get("recipe_price", 0))
            servings = float(row.get("servings", 1)) or 1
            labor_cost = float(row.get("labor_cost", 0))
            
            # Calculate metrics
            # Prefer ingredient_cost; if missing/zero and portion_cost provided, derive from portion_cost * servings
            base_cost = ingredient_cost if ingredient_cost > 0 else (portion_cost * servings if portion_cost > 0 and servings > 0 else 0)
            total_cost = base_cost + labor_cost
            cost_per_serving = total_cost / servings if servings > 0 else total_cost
            
            if recipe_price > 0:
                food_cost_percent = (cost_per_serving / recipe_price) * 100
                profit_margin = ((recipe_price - cost_per_serving) / recipe_price) * 100
                profit_per_serving = recipe_price - cost_per_serving
            else:
                food_cost_percent = 0
                profit_margin = 0
                profit_per_serving = 0
            
            # Determine status
            if profit_margin >= 65:
                status = "Excellent"
                profitable_count += 1
            elif profit_margin >= 55:
                status = "Good"
                profitable_count += 1
            elif profit_margin >= 45:
                status = "Acceptable"
            else:
                status = "Needs Review"
                needs_review_count += 1
            
            recipe_analyses.append({
                "recipe_name": recipe_name,
                "ingredient_cost": round(ingredient_cost, 2),
                "labor_cost": round(labor_cost, 2),
                "total_cost": round(total_cost, 2),
                "recipe_price": round(recipe_price, 2),
                "servings": int(servings),
                "cost_per_serving": round(cost_per_serving, 2),
                "food_cost_percent": round(food_cost_percent, 1),
                "profit_margin": round(profit_margin, 1),
                "profit_per_serving": round(profit_per_serving, 2),
                "status": status
            })

        if not recipe_analyses:
            return {
                "status": "error",
                "message": "No valid recipe data found in CSV",
                "help": "Please ensure your CSV has valid recipe data",
            }

        # Calculate summary metrics
        avg_food_cost = sum(r["food_cost_percent"] for r in recipe_analyses) / len(recipe_analyses)
        avg_profit_margin = sum(r["profit_margin"] for r in recipe_analyses) / len(recipe_analyses)
        total_potential_profit = sum(r["profit_per_serving"] for r in recipe_analyses)
        
        # Sort by profit margin for insights
        sorted_by_margin = sorted(recipe_analyses, key=lambda x: x["profit_margin"], reverse=True)
        top_performers = sorted_by_margin[:3] if len(sorted_by_margin) >= 3 else sorted_by_margin
        needs_attention = [r for r in sorted_by_margin if r["status"] == "Needs Review"][:3]

        # Generate recommendations
        recommendations = []
        
        if avg_food_cost > 35:
            recommendations.append(
                f"Average food cost is high ({avg_food_cost:.1f}%). A practical target is 28–35% depending on concept; prioritize reducing waste and adjusting portioning on the highest-cost recipes."
            )
        
        if needs_review_count > 0:
            recommendations.append(
                f"{needs_review_count} recipe(s) have low margins. For each, decide: raise price, reduce portion/cost, or remove/replace if it can’t hit your margin standard."
            )
        
        if avg_profit_margin < 60:
            recommendations.append(
                f"Average profit margin is {avg_profit_margin:.1f}%. Aim for ~60–70% on core items (concept-dependent) by fixing the worst performers first."
            )
        
        target_margin = 65.0
        for recipe in needs_attention:
            current_price = float(recipe.get("recipe_price") or 0)
            cost = float(recipe.get("cost_per_serving") or 0)
            needed_price = _price_for_margin(cost, target_margin) if cost > 0 else 0.0
            price_increase = max(0.0, needed_price - current_price) if current_price > 0 else 0.0
            if current_price > 0 and needed_price > 0 and price_increase > 0.01:
                recommendations.append(
                    f"Review '{recipe['recipe_name']}' ({recipe['profit_margin']}% margin): to reach ~{target_margin:.0f}% margin at ${cost:.2f} cost, price would need to be about ${needed_price:.2f} (≈ +${price_increase:.2f})."
                )
            else:
                recommendations.append(
                    f"Review '{recipe['recipe_name']}' — only {recipe['profit_margin']}% margin. Consider a price change and/or cost reduction."
                )
        
        if not recommendations:
            recommendations.append("All recipes are performing well within target margins")
            recommendations.append("Continue monitoring costs and adjust prices as ingredient costs change")

        # Generate AI-powered analysis
        ai_analysis = None
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                client = OpenAI(api_key=api_key)
                
                # Prepare recipe data for AI
                recipe_summary = "\n".join([
                    f"- {r['recipe_name']}: Cost ${r['cost_per_serving']:.2f}/serving, Price ${r['recipe_price']:.2f}, Margin {r['profit_margin']:.1f}%, Status: {r['status']}"
                    for r in recipe_analyses[:15]  # Limit to 15 for token efficiency
                ])
                
                ai_prompt = f"""Analyze this restaurant recipe portfolio and provide strategic recommendations:

Recipe Portfolio Summary:
- Total Recipes: {total_recipes}
- Average Food Cost: {avg_food_cost:.1f}%
- Average Profit Margin: {avg_profit_margin:.1f}%
- Profitable Recipes: {profitable_count} ({profitable_count/total_recipes*100:.0f}%)
- Recipes Needing Review: {needs_review_count}

Individual Recipe Analysis:
{recipe_summary}

IMPORTANT FORMATTING RULES:
- Write in plain, natural English without any markdown or special formatting
- Do NOT use asterisks or bold markers (no ** symbols)
- Do NOT use hash symbols for headers (no ## symbols)
- Do NOT use LaTeX or mathematical notation
- Use simple numbered lists (1. 2. 3.) or dashes (-) for items
- Write like you're having a conversation with a restaurant owner

Please provide:
1. Portfolio Assessment - overall health of the recipe portfolio
2. Top Performers - which recipes are most profitable and why
3. Improvement Opportunities - specific recipes that need attention
4. Cost Optimization Strategies - how to reduce food costs while maintaining quality
5. Pricing Recommendations - specific price adjustments with rationale
6. Action Plan - prioritized next steps for the kitchen team

Be specific with numbers, percentages, and dollar amounts, but write naturally."""

                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system",
                            "content": """You are an expert restaurant consultant specializing in recipe costing, menu engineering, and kitchen profitability. Analyze recipe data and provide comprehensive, actionable insights.

CRITICAL FORMATTING RULES:
- NEVER use markdown formatting (no asterisks, no bold markers like **, no hash symbols like ##)
- NEVER use LaTeX or mathematical notation (no backslash commands)
- Write in plain, natural English like a friendly conversation
- Use simple numbered lists (1. 2. 3.) or dashes (-) for lists
- Include specific calculations and dollar amounts written conversationally
- Compare to industry benchmarks (Food Cost: 28-32%, Profit Margin: 65-70%)
- Provide prioritized, actionable recommendations
- Be thorough but conversational"""
                        },
                        {"role": "user", "content": ai_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=2000,
                )
                ai_analysis = response.choices[0].message.content
        except Exception as e:
            ai_analysis = f"AI analysis unavailable: {str(e)}"

        # Build business report for consistent UI rendering
        if avg_profit_margin >= 65 and avg_food_cost <= 32:
            performance_rating = "Excellent"
            perf_color = "blue"
        elif avg_profit_margin >= 60 and avg_food_cost <= 35:
            performance_rating = "Good"
            perf_color = "green"
        elif avg_profit_margin >= 50:
            performance_rating = "Acceptable"
            perf_color = "orange"
        else:
            performance_rating = "Needs Improvement"
            perf_color = "red"

        metrics = {
            "Total Recipes": total_recipes,
            "Average Food Cost %": avg_food_cost,
            "Average Profit Margin %": avg_profit_margin,
            "Profitable Recipes": profitable_count,
            "Needs Review": needs_review_count,
            "Total Potential Profit": total_potential_profit,
        }

        additional_data = {
            "Top Performers": [r["recipe_name"] for r in top_performers],
            "Needs Attention": [r["recipe_name"] for r in needs_attention],
            "AI Analysis": ai_analysis,
        }

        business_report = format_business_report(
            analysis_type="Recipe Management Analysis",
            metrics=metrics,
            performance={"rating": performance_rating, "color": perf_color},
            recommendations=recommendations,
            benchmarks={
                "Food Cost %": "28-32% (Target Range)",
                "Profit Margin %": "65-70% (Target Range)",
            },
            additional_data=additional_data,
        )

        return {
            "status": "success",
            "file_info": csv_file.name if hasattr(csv_file, 'name') else "Uploaded CSV",
            "summary": {
                "total_recipes": total_recipes,
                "avg_food_cost_percent": f"{avg_food_cost:.1f}%",
                "avg_profit_margin": f"{avg_profit_margin:.1f}%",
                "profitable_recipes": profitable_count,
                "needs_review": needs_review_count,
                "total_potential_profit": f"${total_potential_profit:.2f}"
            },
            "recipes": recipe_analyses,
            "top_performers": top_performers,
            "needs_attention": needs_attention,
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
            "help": "Please ensure your CSV has columns: recipe_name, ingredient_cost, portion_cost, recipe_price, servings, labor_cost",
        }
