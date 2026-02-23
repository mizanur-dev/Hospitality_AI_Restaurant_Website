"""
CSV Menu Design Processor
Parses uploaded CSV to classify items into the Menu Engineering Matrix and return design recommendations.
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
        elif l in ("quantity_sold", "quantity", "units sold"):
            mapping[col] = "quantity_sold"
        elif l in ("price", "unit_price", "unit price", "item_price"):
            mapping[col] = "price"
        elif l in ("cost", "item_cost"):
            mapping[col] = "cost"
        elif "category" in l:
            mapping[col] = "category"
        elif "description" in l:
            mapping[col] = "description"
    return mapping


def process_design_csv_data(csv_file) -> Dict[str, Any]:
    try:
        df = pd.read_csv(csv_file)
        actual_cols = [c.strip() for c in df.columns]
        df.columns = actual_cols
        mapping = _map_columns(actual_cols)
        df = df.rename(columns=mapping)

        required = ["item_name", "quantity_sold", "price"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            return {
                "status": "error",
                "message": f"Missing required columns: {', '.join(missing)}",
                "your_columns": actual_cols,
                "help": "CSV must include: item_name, quantity_sold, price"
            }

        # Clean numeric fields
        for c in ["quantity_sold", "price", "cost"]:
            if c in df.columns:
                df[c] = df[c].apply(_clean_numeric)

        # Drop invalid rows
        df = df.dropna(subset=["item_name"]).copy()
        df = df[(df["quantity_sold"] > 0) & (df["price"] > 0)]
        if len(df) == 0:
            return {"status": "error", "message": "No valid data rows found after cleaning"}

        # Aggregate by item_name to reduce duplicates
        agg = (
            df.groupby("item_name")
              .agg({
                  "quantity_sold": "sum",
                  "price": "mean",
                  "cost": "mean"
              })
              .reset_index()
        )

        # Compute derived fields
        agg["contribution_margin"] = agg.apply(lambda r: max(r["price"] - (r["cost"] if not pd.isna(r["cost"]) else r["price"] * 0.3), 0.0), axis=1)
        total_units = agg["quantity_sold"].sum() or 1.0
        avg_units = agg["quantity_sold"].mean() or 0.0
        avg_margin = agg["contribution_margin"].mean() or 0.0

        # Classify into quadrants (relative to averages)
        def quadrant(row):
            pop_score = (row["quantity_sold"] / avg_units) if avg_units > 0 else 1.0
            prof_score = (row["contribution_margin"] / avg_margin) if avg_margin > 0 else 1.0
            if pop_score >= 1.0 and prof_score >= 1.0:
                return "star"
            elif pop_score >= 1.0 and prof_score < 1.0:
                return "plowhorse"
            elif pop_score < 1.0 and prof_score >= 1.0:
                return "puzzle"
            return "dog"

        agg["quadrant"] = agg.apply(quadrant, axis=1)

        quadrant_counts = {
            "stars": int((agg["quadrant"] == "star").sum()),
            "plowhorses": int((agg["quadrant"] == "plowhorse").sum()),
            "puzzles": int((agg["quadrant"] == "puzzle").sum()),
            "dogs": int((agg["quadrant"] == "dog").sum()),
        }

        # Golden triangle suggestions: pick top margin and top popularity
        top_margin_item = agg.sort_values("contribution_margin", ascending=False).iloc[0]["item_name"] if len(agg) else "N/A"
        top_pop_item = agg.sort_values("quantity_sold", ascending=False).iloc[0]["item_name"] if len(agg) else "N/A"
        golden_triangle = [
            {"menu_item": top_margin_item, "position": "Top Right", "reason": "Highest margin"},
            {"menu_item": top_pop_item, "position": "Top Center", "reason": "Highest popularity"},
        ] if len(agg) else []

        # Metrics
        metrics = {
            "Total Menu Items": int(len(agg)),
            "Stars (High visibility)": quadrant_counts["stars"],
            "Puzzles (Need awareness)": quadrant_counts["puzzles"],
            "Plowhorses (Maintain)": quadrant_counts["plowhorses"],
            "Dogs (Minimize/Remove)": quadrant_counts["dogs"],
            "Golden Triangle Items": len(golden_triangle),
        }

        # Performance
        star_pct = (quadrant_counts["stars"] / len(agg) * 100) if len(agg) else 0.0
        dog_pct = (quadrant_counts["dogs"] / len(agg) * 100) if len(agg) else 0.0
        if star_pct >= 25 and dog_pct <= 15:
            performance = "Well-Structured"
        elif star_pct >= 15 and dog_pct <= 25:
            performance = "Moderate Optimization Needed"
        else:
            performance = "Significant Redesign Recommended"

        # Recommendations
        recommendations: List[str] = []
        if quadrant_counts["dogs"] > 0:
            dog_names = (
                agg[agg["quadrant"] == "dog"]
                .sort_values(["quantity_sold", "contribution_margin"], ascending=[True, True])
                .head(3)["item_name"]
                .tolist()
            )
            recommendations.append(
                f"Dogs: {quadrant_counts['dogs']} items ({dog_pct:.0f}%). Minimize/remove or rework the weakest performers first: {', '.join(dog_names)}"
            )
        if quadrant_counts["puzzles"] > 0:
            puzzle_names = (
                agg[agg["quadrant"] == "puzzle"]
                .sort_values(["contribution_margin"], ascending=[False])
                .head(3)["item_name"]
                .tolist()
            )
            recommendations.append(
                f"Puzzles: {quadrant_counts['puzzles']} items. They have strong margin but low visibility — feature, rename, and add menu callouts for: {', '.join(puzzle_names)}"
            )
        if quadrant_counts["plowhorses"] > 0:
            plow_names = (
                agg[agg["quadrant"] == "plowhorse"]
                .sort_values(["quantity_sold"], ascending=[False])
                .head(3)["item_name"]
                .tolist()
            )
            recommendations.append(
                f"Plowhorses: {quadrant_counts['plowhorses']} items. Protect popularity but improve margin (portion/cost/price) for: {', '.join(plow_names)}"
            )
        if not recommendations:
            recommendations.append("Menu appears well structured; maintain visual hierarchy and monitor.")

        benchmarks = {
            "Golden Triangle": "Top-right, top-center, middle-center positions",
            "Items Per Category": "6-8 items maximum",
            "Star Distribution Target": "25-35% of menu items",
            "Dog Distribution Max": "< 15% of menu items",
        }

        business_report = format_business_report(
            analysis_type="Menu Design Recommendations (Menu Psychology)",
            metrics=metrics,
            performance={"rating": performance, "color": "purple"},
            recommendations=recommendations,
            benchmarks=benchmarks,
            additional_data={"Items Analyzed": int(len(agg))}
        )

        return {
            "status": "success",
            "analysis_type": business_report["analysis_type"],
            "business_report": business_report["business_report"],
            "business_report_html": business_report["business_report_html"],
            "metrics": metrics,
            "performance": performance,
            "recommendations": recommendations,
            "quadrant_counts": quadrant_counts,
            "golden_triangle": golden_triangle,
        }
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "message": f"CSV processing error: {str(e)}",
            "traceback": traceback.format_exc() if hasattr(traceback, "format_exc") else None,
        }
