"""
CSV Item Optimization Processor
Analyzes underperforming items using recipe costing, portion control, description optimization, and waste hotspots.
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
        elif l in ("item_cost", "cost", "portion_cost"):
            # prefer item_cost, but map generically
            if "item_cost" not in mapping.values():
                mapping[col] = "item_cost"
        elif l in ("portion_size", "portion"):
            mapping[col] = "portion_size"
        elif l in ("portion_cost",):
            mapping[col] = "portion_cost"
        elif "waste" in l:
            mapping[col] = "waste_percent"
        elif "description" in l:
            mapping[col] = "description"
        elif l in ("price", "item_price", "unit_price", "unit price"):
            mapping[col] = "price"
        elif "category" in l:
            mapping[col] = "category"
    return mapping


def process_optimization_csv_data(csv_file) -> Dict[str, Any]:
    try:
        df = pd.read_csv(csv_file)
        actual_cols = [c.strip() for c in df.columns]
        df.columns = actual_cols
        mapping = _map_columns(actual_cols)
        df = df.rename(columns=mapping)

        required_any_price = ["item_name", "quantity_sold"]
        if not all(c in df.columns for c in required_any_price):
            missing = [c for c in required_any_price if c not in df.columns]
            return {
                "status": "error",
                "message": f"Missing required columns: {', '.join(missing)}",
                "your_columns": actual_cols,
                "help": "CSV must include: item_name, quantity_sold; optional: item_cost, portion_size, portion_cost, description, waste_percent"
            }

        # Clean numeric fields
        for c in ["quantity_sold", "item_cost", "portion_cost", "waste_percent", "price"]:
            if c in df.columns:
                df[c] = df[c].apply(_clean_numeric)

        # Drop invalid rows
        df = df.dropna(subset=["item_name"]).copy()
        df = df[(df["quantity_sold"] > 0)]
        if len(df) == 0:
            return {"status": "error", "message": "No valid data rows found after cleaning"}

        # Derive metrics
        items: List[Dict[str, Any]] = []
        for _, row in df.iterrows():
            items.append({
                "name": str(row.get("item_name")),
                "qty": float(row.get("quantity_sold", 0.0)),
                "cost": float(row.get("item_cost", 0.0)),
                "portion_size": row.get("portion_size"),
                "portion_cost": float(row.get("portion_cost", 0.0)),
                "waste": float(row.get("waste_percent", 0.0)),
                "description": str(row.get("description", "")),
                "price": float(row.get("price", 0.0)),
            })

        avg_cost = (sum(i["cost"] for i in items) / len(items)) if items else 0.0
        avg_qty = (sum(i["qty"] for i in items) / len(items)) if items else 0.0
        high_waste = [i for i in items if i["waste"] >= 5.0]

        # KPIs
        metrics = {
            "Items": len(items),
            "Avg Cost/Item": avg_cost,
            "Avg Units Sold": avg_qty,
            "High Waste (>=5%)": len(high_waste),
        }

        # Performance rating
        if len(high_waste) / len(items) * 100 if items else 0.0 > 20:
            performance = "Significant Optimization Needed"
        elif len(high_waste) / len(items) * 100 if items else 0.0 > 10:
            performance = "Moderate Optimization Needed"
        else:
            performance = "Generally Healthy"

        # Recommendations
        recommendations: List[str] = []
        if high_waste:
            top = sorted(high_waste, key=lambda x: x["waste"], reverse=True)[:3]
            names = "; ".join([f"{i['name']} ({i['waste']:.1f}%)" for i in top])
            recommendations.append(
                f"Waste is elevated on key items — bring each toward <5% with portion control and prep standards: {names}"
            )
        # Recipe costing opportunities: items with high cost and low qty
        high_cost_low_qty = [i for i in items if i["cost"] >= avg_cost * 1.2 and i["qty"] <= avg_qty * 0.8]
        if high_cost_low_qty:
            top = sorted(high_cost_low_qty, key=lambda x: (x["cost"], -x["qty"]), reverse=True)[:3]
            names = "; ".join([f"{i['name']} ($ {i['cost']:.2f} cost, {i['qty']:.0f} units)" for i in top])
            recommendations.append(
                f"High cost + low sales items need re-costing or repositioning: {names}"
            )
        # Description optimization: items with low qty and empty description
        needs_description = [i for i in items if i["qty"] <= avg_qty * 0.8 and not i["description"]]
        if needs_description:
            top = sorted(needs_description, key=lambda x: x["qty"])[:3]
            names = "; ".join([f"{i['name']} ({i['qty']:.0f} units vs avg {avg_qty:.0f})" for i in top])
            recommendations.append(
                f"Low-selling items with missing descriptions — add benefit/sensory copy and a signature ingredient: {names}"
            )
        if not recommendations:
            recommendations.append("Items appear optimized; maintain standards and monitor waste.")

        benchmarks = {
            "Waste Target": "< 5%",
            "Portion Control": "Standardize sizes; use scales/scoops",
            "Recipe Costing": "Update ingredient prices monthly",
            "Menu Descriptions": "Use sensory language and benefits",
        }

        # Build tracking sections for comprehensive UI
        avg_waste = (sum(i["waste"] for i in items) / len(items)) if items else 0.0
        portion_info_count = sum(1 for i in items if (i.get("portion_size") or i.get("portion_cost")))
        standardization_needed = sum(1 for i in items if (i["waste"] >= 5.0 and not i.get("portion_size")))

        waste_tracking = {
            "Avg Waste %": avg_waste,
            "High Waste (>=5%)": len(high_waste),
            "Rating": performance,
            "data_source": "Actual",
        }

        portion_control = {
            "Items With Portion Info": portion_info_count,
            "Standardization Needed": standardization_needed,
            "Targets": "Use scales/scoops; train prep standards",
            "data_source": "Actual",
        }

        recipe_costing = {
            "High Cost & Low Sales": len(high_cost_low_qty),
            "Avg Cost/Item": avg_cost,
            "Action": "Review recipes; update ingredient prices",
            "data_source": "Actual",
        }

        description_opt = {
            "Items Needing Description": len(needs_description),
            "Tip": "Use sensory language and benefits",
            "data_source": "Actual",
        }

        additional_sections = {
            "Waste Tracking": waste_tracking,
            "Portion Control": portion_control,
            "Recipe Costing Opportunities": recipe_costing,
            "Description Optimization": description_opt,
        }

        business_report = format_business_report(
            analysis_type="Item Optimization Analysis",
            metrics=metrics,
            performance={"rating": performance, "color": "blue"},
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
            "high_waste_items": high_waste,
            "avg_cost": avg_cost,
            "avg_qty": avg_qty,
        }
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "message": f"CSV processing error: {str(e)}",
            "traceback": traceback.format_exc() if hasattr(traceback, "format_exc") else None,
        }
