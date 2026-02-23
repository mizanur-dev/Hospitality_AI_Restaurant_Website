"""
CSV Pricing Strategy Processor
Parses uploaded CSV to analyze pricing opportunities and return a business report.
"""
from typing import Any, Dict, List
import pandas as pd
from backend.consulting_services.kpi.kpi_utils import format_business_report


def _clean_numeric(value) -> float:
    if value is None:
        return 0.0
    try:
        if isinstance(value, float) and pd.isna(value):
            return 0.0
    except Exception:
        pass
    if isinstance(value, str):
        s = value.strip().replace("$", "").replace("%", "").replace(",", "")
        if s == "" or s.lower() == "nan":
            return 0.0
        try:
            return float(s)
        except ValueError:
            return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _map_columns(actual_columns: List[str]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for col in actual_columns:
        l = col.lower()
        if l in mapping:
            continue
        if l in ("item_name", "menu item", "product_name", "product name"):
            mapping[col] = "item_name"
        elif l in ("item_price", "price", "unit_price", "unit price"):
            mapping[col] = "item_price"
        elif l in ("item_cost", "cost"):
            mapping[col] = "item_cost"
        elif "competitor" in l and "price" in l:
            mapping[col] = "competitor_price"
        elif "target_food_cost" in l or "target food cost" in l:
            mapping[col] = "target_food_cost_percent"
        elif "category" in l:
            mapping[col] = "category"
    return mapping


def process_pricing_csv_data(csv_file) -> Dict[str, Any]:
    try:
        df = pd.read_csv(csv_file)
        actual_cols = [c.strip() for c in df.columns]
        df.columns = actual_cols
        mapping = _map_columns(actual_cols)
        df = df.rename(columns=mapping)

        required = ["item_name", "item_price", "item_cost", "competitor_price"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            return {
                "status": "error",
                "message": f"Missing required columns: {', '.join(missing)}",
                "your_columns": actual_cols,
                "help": "CSV must include: item_name, item_price, item_cost, competitor_price"
            }

        # Clean numeric fields
        for c in ["item_price", "item_cost", "competitor_price", "target_food_cost_percent"]:
            if c in df.columns:
                df[c] = df[c].apply(_clean_numeric)

        # Drop invalid rows
        df = df.dropna(subset=["item_name"]).copy()
        df = df[(df["item_price"] > 0) & (df["item_cost"] >= 0)]
        if len(df) == 0:
            return {"status": "error", "message": "No valid data rows found after cleaning"}

        target_food_cost = df["target_food_cost_percent"].dropna().iloc[0] if "target_food_cost_percent" in df.columns and df["target_food_cost_percent"].dropna().size else 32.0

        items = []
        for _, row in df.iterrows():
            name = str(row.get("item_name"))
            price = float(row.get("item_price", 0.0))
            cost = float(row.get("item_cost", 0.0))
            competitor = float(row.get("competitor_price", 0.0))
            items.append({
                "name": name,
                "price": price,
                "cost": cost,
                "competitor": competitor
            })

        # Compute metrics
        underpriced: List[Dict[str, Any]] = []
        overpriced: List[Dict[str, Any]] = []
        well_priced: List[Dict[str, Any]] = []
        for it in items:
            food_cost_pct = (it["cost"] / it["price"] * 100) if it["price"] > 0 else 0.0
            competitor_gap = ((it["price"] - it["competitor"]) / it["competitor"] * 100) if it["competitor"] > 0 else 0.0
            rec = {**it, "food_cost_pct": food_cost_pct, "competitor_gap": competitor_gap}
            if food_cost_pct > target_food_cost:
                underpriced.append(rec)
            elif it["competitor"] > 0 and competitor_gap > 10:
                overpriced.append(rec)
            else:
                well_priced.append(rec)

        metrics = {
            "Underpriced Items": len(underpriced),
            "Overpriced Items": len(overpriced),
            "Well-Priced Items": len(well_priced),
            "Avg Price": sum(i["price"] for i in items) / len(items) if items else 0.0,
            "Min Price": min(i["price"] for i in items) if items else 0.0,
            "Max Price": max(i["price"] for i in items) if items else 0.0,
            "Target Food Cost %": target_food_cost,
        }

        # Performance rating
        underpriced_pct = (len(underpriced) / len(items) * 100) if items else 0.0
        if underpriced_pct > 30:
            performance = "Significant Opportunity"
        elif underpriced_pct > 20:
            performance = "Moderate Opportunity"
        elif underpriced_pct > 10:
            performance = "Minor Adjustments Needed"
        else:
            performance = "Well-Optimized"

        # Recommendations
        recommendations: List[str] = []
        if underpriced:
            top = sorted(
                underpriced,
                key=lambda x: (x["food_cost_pct"] - target_food_cost, x["food_cost_pct"]),
                reverse=True,
            )[:3]
            examples: List[str] = []
            for t in top:
                target_price = (t["cost"] / (target_food_cost / 100.0)) if target_food_cost > 0 else t["price"]
                price_increase = target_price - t["price"]
                target_cost = t["price"] * (target_food_cost / 100.0)
                cost_reduction = t["cost"] - target_cost
                examples.append(
                    f"{t['name']} (food cost {t['food_cost_pct']:.1f}% vs {target_food_cost:.0f}%; "
                    f"raise ~${price_increase:.2f} to ~${target_price:.2f} OR cut cost ~${max(cost_reduction, 0):.2f})"
                )
            recommendations.append(
                "Underpriced vs target food cost — fix the biggest gaps first: " + "; ".join(examples)
            )
        if overpriced:
            top = sorted(overpriced, key=lambda x: x["competitor_gap"], reverse=True)[:3]
            examples: List[str] = []
            for t in top:
                suggested_price = (t["competitor"] * 1.05) if t.get("competitor", 0) > 0 else t["price"]
                delta = t["price"] - suggested_price
                examples.append(
                    f"{t['name']} ({t['competitor_gap']:+.0f}% vs competitor; consider -${max(delta, 0):.2f} to ~${suggested_price:.2f})"
                )
            recommendations.append(
                "Overpriced vs competitor — bring high outliers closer to market (or clearly justify the premium): " + "; ".join(examples)
            )
        if not recommendations:
            recommendations.append("Pricing appears aligned with targets. Maintain and monitor.")

        benchmarks = {
            "Target Food Cost %": f"{target_food_cost}%",
            "Pricing Variance Threshold": "±10% from optimal",
            "Psychological Pricing": ".99 endings (<$10), .95 endings ($10-20)",
            "Minimum Markup": "1.5x cost (33% max food cost)",
        }

        # Build tracking sections for comprehensive UI
        # Food cost percent across all items
        avg_food_cost_pct = (
            sum(((i["cost"] / i["price"] * 100.0) if i["price"] > 0 else 0.0) for i in items) / len(items)
        ) if items else 0.0
        within_target_count = sum(
            1 for i in items if (i["price"] > 0 and (i["cost"] / i["price"] * 100.0) <= target_food_cost)
        )

        # Competitor gap stats
        comp_gaps: List[float] = [
            (((i["price"] - i["competitor"]) / i["competitor"] * 100.0) if i["competitor"] > 0 else 0.0)
            for i in items
        ]
        avg_comp_gap = (sum(comp_gaps) / len(comp_gaps)) if comp_gaps else 0.0
        above_10 = sum(1 for g in comp_gaps if g > 10.0)
        near_10 = sum(1 for g in comp_gaps if abs(g) <= 10.0)
        below_0 = sum(1 for g in comp_gaps if g < 0.0)

        pricing_alignment = {
            "Underpriced": len(underpriced),
            "Overpriced": len(overpriced),
            "Well-Priced": len(well_priced),
            "Underpriced %": (len(underpriced) / len(items) * 100.0) if items else 0.0,
            "Rating": performance,
            "data_source": "Actual",
        }

        food_cost_compliance = {
            "Target %": target_food_cost,
            "Avg Food Cost %": avg_food_cost_pct,
            "Items Within Target": within_target_count,
            "Compliance %": (within_target_count / len(items) * 100.0) if items else 0.0,
            "data_source": "Actual",
        }

        competitive_position = {
            "Avg Competitor Gap %": avg_comp_gap,
            "Above Competitor (>10%)": above_10,
            "Near Competitor (±10%)": near_10,
            "Below Competitor": below_0,
            "data_source": "Actual",
        }

        additional_sections = {
            "Pricing Alignment": pricing_alignment,
            "Food Cost Compliance": food_cost_compliance,
            "Competitive Position": competitive_position,
        }

        business_report = format_business_report(
            analysis_type="Menu Pricing Strategy Analysis",
            metrics=metrics,
            performance={"rating": performance, "color": "green"},
            recommendations=recommendations,
            benchmarks=benchmarks,
            additional_data=additional_sections
        )

        return {
            "status": "success",
            "analysis_type": business_report["analysis_type"],
            "business_report": business_report["business_report"],
            "business_report_html": business_report["business_report_html"],
            "metrics": metrics,
            "performance": performance,
            "recommendations": recommendations,
            "underpriced_items": underpriced,
            "overpriced_items": overpriced,
            "well_priced_items": well_priced,
            "target_food_cost_percent": target_food_cost,
        }
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "message": f"CSV processing error: {str(e)}",
            "traceback": traceback.format_exc() if hasattr(traceback, "format_exc") else None,
        }
