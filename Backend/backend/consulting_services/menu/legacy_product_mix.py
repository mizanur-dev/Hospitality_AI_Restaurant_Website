"""
Product Mix Analysis Module
Handles menu analysis, item performance, and product optimization
"""

from typing import Any, Dict

import pandas as pd
from backend.consulting_services.kpi.kpi_utils import format_business_report


def run():
    return {"tool": "Product Mix", "status": "OK — logic not implemented yet"}


def process_csv_data(csv_file) -> Dict[str, Any]:
    """
    Process uploaded CSV file for product mix analysis

    Handles multiple CSV formats:
    1. Raw POS data: product_name, quantity, unit_price
    2. Generated analysis format: Menu Item, Units Sold, Price, Revenue, Profit, etc.
    """
    try:
        df = pd.read_csv(csv_file)
        actual_columns = [col.strip() for col in df.columns]  # Clean column names
        df.columns = actual_columns
        
        # Normalize column names (case-insensitive matching)
        column_mapping = {}
        
        # Detect format by looking for key columns
        has_menu_item = any("menu item" in col.lower() for col in actual_columns)
        has_product_name = any("product_name" in col.lower() or "product name" in col.lower() for col in actual_columns)
        
        # Format 1: Generated analysis format (Menu Item, Units Sold, Price, etc.)
        if has_menu_item:
            # Map generated CSV format columns
            for col in actual_columns:
                col_lower = col.lower()
                if "menu item" in col_lower:
                    column_mapping[col] = "item_name"
                elif "units sold" in col_lower:
                    column_mapping[col] = "quantity_sold"
                elif col_lower == "price" and "price" not in [v for v in column_mapping.values()]:
                    column_mapping[col] = "price"
                elif "revenue" in col_lower:
                    column_mapping[col] = "revenue"
                elif col_lower == "profit" and "profit" not in [v for v in column_mapping.values()]:
                    column_mapping[col] = "profit"
                elif "contribution margin" in col_lower or "margin %" in col_lower:
                    column_mapping[col] = "contribution_margin_pct"
                elif "food cost" in col_lower and "%" in col:
                    column_mapping[col] = "food_cost_pct"
                elif "food cost" in col_lower:
                    column_mapping[col] = "food_cost"
                elif "cost" in col_lower and col not in column_mapping:
                    column_mapping[col] = "cost"
        
        # Format 2: Raw POS format (product_name, quantity, unit_price)
        elif has_product_name:
            for col in actual_columns:
                col_lower = col.lower()
                if "product_name" in col_lower or "product name" in col_lower:
                    column_mapping[col] = "item_name"
                elif "quantity" in col_lower:
                    column_mapping[col] = "quantity_sold"
                elif "unit_price" in col_lower or "unit price" in col_lower or "price" in col_lower:
                    column_mapping[col] = "price"
                elif "cost" in col_lower:
                    column_mapping[col] = "cost"
        
        # Try generic matching if format not detected
        else:
            for col in actual_columns:
                col_lower = col.lower()
                if "name" in col_lower and "item_name" not in [v for v in column_mapping.values()]:
                    column_mapping[col] = "item_name"
                elif "quantity" in col_lower or "units" in col_lower:
                    column_mapping[col] = "quantity_sold"
                elif col_lower == "price":
                    column_mapping[col] = "price"
                elif col_lower == "food_cost" and "cost" not in [v for v in column_mapping.values()]:
                    column_mapping[col] = "cost"
                elif "cost" in col_lower and "labor" not in col_lower and "cost" not in [v for v in column_mapping.values()]:
                    column_mapping[col] = "cost"
        
        # Apply column mapping
        df = df.rename(columns=column_mapping)
        
        # Validate required columns
        required_cols = ["item_name", "quantity_sold", "price"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            return {
                "status": "error",
                "message": f"Missing required columns: {', '.join(missing_cols)}",
                "your_columns": actual_columns,
                "help": "Your CSV needs columns for: item name, quantity/units sold, and price",
                "detected_format": "generated" if has_menu_item else "raw" if has_product_name else "unknown"
            }
        
        # Clean numeric values (remove $, %, commas)
        def clean_numeric(value):
            # Handle None, NaN, and empty values
            if value is None:
                return 0
            try:
                # Check for NaN using different method to avoid Series ambiguity
                if isinstance(value, float) and pd.isna(value):
                    return 0
            except (TypeError, ValueError):
                pass
            if isinstance(value, str):
                value = value.strip()
                if value == '' or value.lower() == 'nan':
                    return 0
                # Remove currency symbols, percentage signs, commas
                cleaned = value.replace("$", "").replace("%", "").replace(",", "").strip()
                try:
                    return float(cleaned)
                except (ValueError, AttributeError):
                    return 0
            try:
                return float(value) if value is not None else 0
            except (ValueError, TypeError):
                return 0
        
        # Clean price column
        df["price"] = df["price"].apply(clean_numeric)
        
        # Clean quantity column - already handled by clean_numeric
        df["quantity_sold"] = df["quantity_sold"].apply(lambda x: int(clean_numeric(x)))
        
        # Handle cost column - prioritize most accurate sources first
        has_cost_column = "cost" in df.columns
        has_food_cost_pct = "food_cost_pct" in df.columns
        has_contribution_margin_pct = "contribution_margin_pct" in df.columns
        has_profit_and_revenue = "profit" in df.columns and "revenue" in df.columns
        
        if has_cost_column:
            # Direct cost column (highest priority)
            df["cost"] = df["cost"].apply(clean_numeric)
            cost_source = "from cost column"
        elif has_food_cost_pct:
            # Food Cost % column (very accurate)
            df["food_cost_pct"] = df["food_cost_pct"].apply(clean_numeric)
            df["cost"] = df["price"] * (df["food_cost_pct"] / 100)
            cost_source = "calculated from Food Cost % column"
        elif has_contribution_margin_pct:
            # Contribution Margin % column (accurate)
            df["contribution_margin_pct"] = df["contribution_margin_pct"].apply(clean_numeric)
            df["cost"] = df["price"] * (1 - df["contribution_margin_pct"] / 100)
            cost_source = "calculated from Contribution Margin % column"
        elif has_profit_and_revenue:
            # Revenue and Profit columns (calculated)
            df["revenue"] = df["revenue"].apply(clean_numeric)
            df["profit"] = df["profit"].apply(clean_numeric)
            # cost per unit = (revenue - profit) / quantity_sold
            # If quantity is 0, use price-based estimation
            df["cost"] = df.apply(
                lambda row: (row["revenue"] - row["profit"]) / row["quantity_sold"] 
                if row["quantity_sold"] > 0 else row["price"] * 0.30, 
                axis=1
            )
            cost_source = "calculated from Revenue and Profit columns"
        else:
            # Estimate cost based on price ranges (fallback)
            def estimate_food_cost(price):
                if price <= 10:  # Appetizers, sides
                    return price * 0.25  # 25% food cost
                elif price <= 20:  # Entrees, casual items
                    return price * 0.30  # 30% food cost
                elif price <= 35:  # Premium entrees
                    return price * 0.35  # 35% food cost
                else:  # High-end items
                    return price * 0.40  # 40% food cost
            
            df["cost"] = df["price"].apply(estimate_food_cost)
            cost_source = "estimated using tiered food cost model (25-40% based on price range)"
        
        # Clean data
        df = df.dropna(subset=["item_name", "quantity_sold", "price"])
        df = df[df["quantity_sold"] > 0]  # Remove zero quantity items
        df = df[df["price"] > 0]  # Remove zero price items
        
        if len(df) == 0:
            return {"status": "error", "message": "No valid data rows found after cleaning"}
        
        # Aggregate data by item name (sum quantities, average price/cost)
        aggregated = (
            df.groupby("item_name")
            .agg(
                {
                    "quantity_sold": "sum",  # Total quantity sold
                    "price": "mean",  # Average price
                    "cost": "mean",  # Average cost
                }
            )
            .reset_index()
        )
        
        # Convert to items format for existing function
        items = []
        for _, row in aggregated.iterrows():
            items.append(
                {
                    "name": str(row["item_name"]),
                    "quantity_sold": int(row["quantity_sold"]),
                    "price": round(float(row["price"]), 2),
                    "cost": round(float(row["cost"]), 2),
                }
            )
        
        # Generate product mix analysis report
        analysis_result = generate_pmix_report(items)
        
        # Calculate overall metrics for business report
        total_revenue = sum(item.get("price", 0) * item.get("quantity_sold", 0) for item in analysis_result["pmix_report"])
        total_profit = sum(item.get("total_profit", 0) for item in analysis_result["pmix_report"])
        total_items = len(items)
        avg_margin = sum(item.get("contribution_margin", 0) for item in analysis_result["pmix_report"]) / total_items if total_items > 0 else 0
        avg_food_cost_pct = (sum((item.get("cost", 0) / item.get("price", 1)) * 100 for item in analysis_result["pmix_report"]) / total_items) if total_items > 0 else 0
        
        # Categorize items by quadrant (simplified based on profit and popularity)
        top_items = sorted(analysis_result["pmix_report"], key=lambda x: x.get("total_profit", 0), reverse=True)
        stars = [item for item in top_items[:int(total_items * 0.25)] if item.get("total_profit", 0) > avg_margin * 50]
        plowhorses = [item for item in top_items if item.get("quantity_sold", 0) > sum(i.get("quantity_sold", 0) for i in items) / total_items and item not in stars]
        puzzles = [item for item in analysis_result["pmix_report"] if item.get("contribution_margin", 0) > avg_margin * 1.5 and item.get("quantity_sold", 0) < sum(i.get("quantity_sold", 0) for i in items) / total_items]
        dogs = [item for item in analysis_result["pmix_report"] if item not in stars and item not in plowhorses and item not in puzzles]
        
        # Determine performance rating
        star_percent = (len(stars) / total_items) * 100 if total_items > 0 else 0
        dog_percent = (len(dogs) / total_items) * 100 if total_items > 0 else 0
        
        if star_percent >= 30 and dog_percent <= 15:
            performance_rating = "Excellent"
        elif star_percent >= 20 and dog_percent <= 25:
            performance_rating = "Good"
        elif star_percent >= 10 and dog_percent <= 35:
            performance_rating = "Acceptable"
        else:
            performance_rating = "Needs Improvement"
        
        # Build metrics for business report
        metrics = {
            "Total Menu Items": total_items,
            "Total Revenue": total_revenue,
            "Total Profit": total_profit,
            "Average Contribution Margin": avg_margin,
            "Average Food Cost Percent": avg_food_cost_pct,
            "Stars": len(stars),
            "Plowhorses": len(plowhorses),
            "Puzzles": len(puzzles),
            "Dogs": len(dogs)
        }
        
        # Build recommendations
        recommendations = []
        if len(stars) > 0:
            star_names = ", ".join([item["name"] for item in stars[:3]])
            recommendations.append(f"Promote your {len(stars)} Star items ({star_names}) - they generate high profit and should be highlighted on menu.")
        
        if len(dogs) > 0:
            dog_names = ", ".join([item["name"] for item in dogs[:3]])
            recommendations.append(f"Consider removing or repositioning {len(dogs)} Dog items ({dog_names}) - they have low popularity and profitability.")
        
        if len(puzzles) > 0:
            puzzle_names = ", ".join([item["name"] for item in puzzles[:3]])
            recommendations.append(f"Increase marketing for {len(puzzles)} Puzzle items ({puzzle_names}) - they have high profitability but need better promotion.")
        
        if len(plowhorses) > 0:
            plowhorse_names = ", ".join([item["name"] for item in plowhorses[:3]])
            recommendations.append(
                f"Plowhorses: {len(plowhorses)} items (high popularity, lower margin). Improve contribution margin via portion/cost/price adjustments (e.g., {plowhorse_names})."
            )
        
        if not recommendations:
            recommendations.append(
                f"Menu mix looks balanced (Stars {star_percent:.0f}%, Dogs {dog_percent:.0f}%). Maintain pricing discipline and review quadrant shifts monthly."
            )
        
        # Industry benchmarks
        benchmarks = {
            "Food Cost %": "28-35% (Restaurant Industry Standard)",
            "Contribution Margin": "65-72% (Optimal Range)",
            "Stars Distribution": "25-35% of menu items (Ideal)",
            "Dogs Distribution": "< 15% of menu items (Maximum Acceptable)"
        }
        
        # Additional insights
        top_profit_item = top_items[0]["name"] if top_items else "N/A"
        additional_data = {
            "Top Profit Item": top_profit_item,
            "Items Processed": len(items),
            "Data Source": "CSV Upload",
            "Cost Calculation": cost_source
        }
        
        # Generate business report
        business_report = format_business_report(
            analysis_type="Product Mix Analysis (Menu Engineering Matrix)",
            metrics=metrics,
            performance={"rating": performance_rating, "color": "blue"},
            recommendations=recommendations,
            benchmarks=benchmarks,
            additional_data=additional_data
        )
        
        # Combine results
        result = {
            "status": "success",
            "data_source": "csv_upload",
            "items_processed": len(items),
            "file_info": f"{len(items)} unique menu items",
            "cost_info": cost_source,
            "pmix_report": analysis_result["pmix_report"],
            # Add business report formatting
            "business_report": business_report["business_report"],
            "business_report_html": business_report["business_report_html"],
            "analysis_type": business_report["analysis_type"],
            "performance_rating": business_report["performance_rating"],
            "metrics": metrics,
            "recommendations": recommendations
        }
        
        return result

    except Exception as e:
        import traceback
        return {
            "status": "error",
            "message": f"CSV processing error: {str(e)}",
            "traceback": traceback.format_exc() if hasattr(traceback, "format_exc") else None
        }


def generate_pmix_report(items):
    """Generate Product Mix report and a comprehensive business report.

    Returns data including:
    - pmix_report: per-item margins and total profit
    - business_report_html: detailed report with Sales Mix, Contribution Margins, and Menu Matrix mapping
    """
    report = []

    # Build base per-item metrics
    for item in items:
        name = item.get("name")
        qty = float(item.get("quantity_sold", 0) or 0)
        price = float(item.get("price", 0.0) or 0.0)
        cost = float(item.get("cost", 0.0) or 0.0)
        margin = price - cost
        total_profit = qty * margin

        report.append(
            {
                "name": name,
                "quantity_sold": int(qty),
                "price": price,
                "cost": cost,
                "contribution_margin": round(margin, 2),
                "total_profit": round(total_profit, 2),
            }
        )

    # Sort by profit for top items table
    report.sort(key=lambda x: x["total_profit"], reverse=True)

    # Aggregate totals for Sales Mix and Contribution metrics
    total_revenue = sum((r["price"] * r["quantity_sold"]) for r in report)
    total_cost = sum((r["cost"] * r["quantity_sold"]) for r in report)
    total_profit = sum(r["total_profit"] for r in report)
    total_items = len(report)
    avg_margin = (sum(r.get("contribution_margin", 0.0) for r in report) / total_items) if total_items > 0 else 0.0
    avg_food_cost_pct = (
        sum(((r.get("cost", 0.0) / max(r.get("price", 0.0), 1e-6)) * 100.0) for r in report) / total_items
    ) if total_items > 0 else 0.0

    # Popularity threshold: average quantity sold
    avg_qty = (sum(r.get("quantity_sold", 0) for r in report) / total_items) if total_items > 0 else 0.0

    # Quadrant classification (Menu Engineering Matrix)
    stars = [r for r in report if r["quantity_sold"] >= avg_qty and r["contribution_margin"] >= avg_margin]
    plowhorses = [r for r in report if r["quantity_sold"] >= avg_qty and r["contribution_margin"] < avg_margin]
    puzzles = [r for r in report if r["quantity_sold"] < avg_qty and r["contribution_margin"] >= avg_margin]
    dogs = [r for r in report if r["quantity_sold"] < avg_qty and r["contribution_margin"] < avg_margin]

    # Performance rating
    star_percent = (len(stars) / total_items * 100.0) if total_items > 0 else 0.0
    dog_percent = (len(dogs) / total_items * 100.0) if total_items > 0 else 0.0
    if star_percent >= 30 and dog_percent <= 15:
        performance_rating = "Excellent"
        perf_color = "blue"
    elif star_percent >= 20 and dog_percent <= 25:
        performance_rating = "Good"
        perf_color = "green"
    elif star_percent >= 10 and dog_percent <= 35:
        performance_rating = "Acceptable"
        perf_color = "orange"
    else:
        performance_rating = "Needs Improvement"
        perf_color = "red"

    # Sales Mix details
    # Sort by revenue for share calculations
    by_revenue = sorted(report, key=lambda x: (x["price"] * x["quantity_sold"]), reverse=True)
    top1_rev = (by_revenue[0]["price"] * by_revenue[0]["quantity_sold"]) if by_revenue else 0.0
    top5_rev = sum((r["price"] * r["quantity_sold"]) for r in by_revenue[:5]) if by_revenue else 0.0
    sales_mix = {
        "Total Revenue": total_revenue,
        "Top Item Share %": (top1_rev / total_revenue * 100.0) if total_revenue > 0 else 0.0,
        "Top 5 Items Share %": (top5_rev / total_revenue * 100.0) if total_revenue > 0 else 0.0,
        "Items": total_items,
        "Rating": performance_rating,
        "data_source": "Actual" if total_revenue > 0 else "Estimated",
    }

    # Contribution Margin analysis
    cm_percent_overall = ((total_revenue - total_cost) / total_revenue * 100.0) if total_revenue > 0 else 0.0
    cm_analysis = {
        "Average CM ($)": avg_margin,
        "Average Food Cost %": avg_food_cost_pct,
        "Contribution Margin % (Overall)": cm_percent_overall,
        "Total Profit": total_profit,
        "Items": total_items,
        "data_source": "Actual" if total_revenue > 0 else "Estimated",
    }

    # Menu Matrix mapping summary
    matrix_summary = {
        "Stars": len(stars),
        "Plowhorses": len(plowhorses),
        "Puzzles": len(puzzles),
        "Dogs": len(dogs),
        "Stars %": star_percent,
        "Dogs %": dog_percent,
        "Rating": performance_rating,
        "data_source": "Actual",
    }

    # Metrics for key metrics section
    metrics = {
        "Total Menu Items": total_items,
        "Total Revenue": total_revenue,
        "Total Profit": total_profit,
        "Average Contribution Margin": avg_margin,
        "Average Food Cost Percent": avg_food_cost_pct,
        "Stars": len(stars),
        "Plowhorses": len(plowhorses),
        "Puzzles": len(puzzles),
        "Dogs": len(dogs),
    }

    # Recommendations
    recommendations = []
    if len(stars) > 0:
        star_names = ", ".join([item.get("name") for item in stars[:3] if item.get("name")])
        recommendations.append(
            f"Stars: {len(stars)} items (≈{star_percent:.0f}% of menu). Feature and highlight top Stars (e.g., {star_names}) to protect profit and volume."
        )
    if len(plowhorses) > 0:
        plow_names = ", ".join([item.get("name") for item in plowhorses[:3] if item.get("name")])
        recommendations.append(
            f"Plowhorses: {len(plowhorses)} items. Improve margin without hurting sales by tightening portion specs and re-costing ingredients (e.g., {plow_names})."
        )
    if len(puzzles) > 0:
        puzzle_names = ", ".join([item.get("name") for item in puzzles[:3] if item.get("name")])
        recommendations.append(
            f"Puzzles: {len(puzzles)} items. Boost visibility for high-margin, low-popularity items with placement/callouts (e.g., {puzzle_names})."
        )
    if len(dogs) > 0:
        dog_names = ", ".join([item.get("name") for item in dogs[:3] if item.get("name")])
        recommendations.append(
            f"Dogs: {len(dogs)} items (≈{dog_percent:.0f}% of menu). Minimize/rework/remove the weakest items first (e.g., {dog_names})."
        )
    if not recommendations:
        recommendations.append(
            f"Menu performance looks balanced (Stars {star_percent:.0f}%, Dogs {dog_percent:.0f}%). Maintain pricing and monitor quadrant shifts weekly."
        )

    # Benchmarks
    benchmarks = {
        "Food Cost %": "28-35% (Restaurant Industry Standard)",
        "Contribution Margin": "65-72% (Optimal Range)",
        "Stars Distribution": "25-35% of menu items (Ideal)",
        "Dogs Distribution": "< 15% of menu items (Maximum Acceptable)",
    }

    # Additional sections for tracking cards
    additional_sections = {
        "Revenue Mix": sales_mix,              # renders as Revenue Analysis card
        "Contribution Margin Analysis": cm_analysis,
        "Menu Matrix Mapping": matrix_summary,
    }

    # Build comprehensive business report HTML
    from backend.consulting_services.kpi.kpi_utils import format_business_report
    business_report = format_business_report(
        analysis_type="Comprehensive Menu Performance Review",
        metrics=metrics,
        performance={"rating": performance_rating, "color": perf_color},
        recommendations=recommendations,
        benchmarks=benchmarks,
        additional_data=additional_sections,
    )

    return {
        "status": "success",
        "analysis_type": business_report["analysis_type"],
        "business_report": business_report["business_report"],
        "business_report_html": business_report["business_report_html"],
        "performance_rating": performance_rating,
        "metrics": metrics,
        "recommendations": recommendations,
        "pmix_report": report,
    }
