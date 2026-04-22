from __future__ import annotations

import html
import io
import logging
import re
from datetime import datetime
from uuid import uuid4

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import MenuChatRequestSerializer
from apps.chat_assistant.translation_utils import translate_html_response

from backend.shared.ai.strategic_recommendations import generate_ai_strategic_recommendations

logger = logging.getLogger(__name__)



def _error_payload(*, code: str, message: str, details=None, trace_id: str | None = None):
    payload = {"error": {"code": code, "message": message}}
    if details is not None:
        payload["error"]["details"] = details
    if trace_id:
        payload["error"]["trace_id"] = trace_id
    return payload


def _ensure_html(text_or_html: str) -> str:
    """Return HTML suitable for injecting into responses.

    If the input already contains HTML tags we assume it's ready to go;
    otherwise we wrap the escaped text in a simple ``<div>`` using the
    surrounding font (no ``<pre>``) and preserve whitespace.  The old
    implementation used a ``<pre>`` element which forced a monospace
    font, leading to responses that looked different from the normal
    conversation text.
    """
    if not isinstance(text_or_html, str):
        text_or_html = str(text_or_html)
    candidate = text_or_html.strip()
    if not candidate:
        return "<div>No analysis returned.</div>"
    if "<" in candidate and ">" in candidate:
        return candidate
    # plain text – use div with inherited font and keep line breaks
    return f'<div style="font-family:inherit; white-space:pre-wrap">{html.escape(candidate)}</div>'


def _snake_key(key: str) -> str:
    key = key.strip().lower()
    key = re.sub(r"[^a-z0-9_\s]", "", key)
    key = re.sub(r"\s+", "_", key)
    key = re.sub(r"_+", "_", key)
    return key.strip("_")


def _coerce_scalar(value: str):
    raw = value.strip().rstrip(".;")
    if not raw:
        return ""
    lowered = raw.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    numeric_candidate = raw.replace(",", "")
    numeric_candidate = re.sub(r"^\$", "", numeric_candidate)
    numeric_candidate = numeric_candidate.replace("$", "").replace("%", "")
    try:
        if re.fullmatch(r"-?\d+", numeric_candidate):
            return int(numeric_candidate)
        if re.fullmatch(r"-?\d*\.\d+", numeric_candidate) or re.fullmatch(r"-?\d+\.\d+", numeric_candidate):
            return float(numeric_candidate)
    except Exception:
        pass
    return raw


def _strip_topic_prefix(message: str) -> tuple[str, str]:
    """Return (cleaned_body, detected_prefix_label)."""
    candidate = message.strip()
    first_line, *rest = candidate.splitlines()

    PREFIX_MAP = {
        "analyze my menu analysis": "menu_analysis",
        "analyze my pricing strategy": "pricing_strategy",
        "analyze my item optimization": "item_optimization",
    }

    if ":" in first_line:
        prefix_raw = first_line.split(":", 1)[0].strip().lower()
        # Only treat the first segment as a topic prefix if it actually looks
        # like an instruction (e.g., "Analyze my …:"). Avoid misclassifying
        # valid KV payloads like "Item: …".
        if prefix_raw.startswith("analyze"):
            for pat, tag in PREFIX_MAP.items():
                if pat in prefix_raw:
                    return "\n".join(rest).strip(), tag

    single_match = re.match(
        r"^(analyze\s+my\s+menu\s+analysis|analyze\s+my\s+pricing\s+strategy|analyze\s+my\s+item\s+optimization)\s*[:\-]?\s*(.*)$",
        candidate,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if single_match:
        label_raw = single_match.group(1).strip().lower()
        body = (single_match.group(2) or "").strip()
        for pat, tag in PREFIX_MAP.items():
            if pat in label_raw:
                return body, tag
        return body, ""

    return candidate, ""


def _parse_kv_message(message: str) -> tuple[dict, str]:
    """Return (params_dict, detected_subtask_label)."""
    body, detected_prefix = _strip_topic_prefix(message)

    params: dict = {}
    # Robust KV extraction:
    # - allows '.' and newlines as separators between pairs
    # - does NOT treat ',' as a delimiter so numbers like 2,375.00 stay intact
    # - allows keys like "Food Cost %" and "Contribution Margin %"
    kv_pattern = re.compile(
        r"(?:^|[\n;]|\.)\s*(?P<key>[A-Za-z_][A-Za-z0-9_ %]*?)\s*:\s*(?P<value>.*?)\s*(?=(?:[\n;]|\.)\s*[A-Za-z_][A-Za-z0-9_ %]*?\s*:\s*|$)",
        flags=re.IGNORECASE | re.DOTALL,
    )
    for match in kv_pattern.finditer(body):
        key = _snake_key(match.group("key"))
        value = _coerce_scalar(match.group("value"))
        if key:
            params[key] = value

    return params, detected_prefix


def _detect_subtask(message: str, params: dict, prefix_hint: str) -> str:
    if prefix_hint == "menu_analysis":
        return "menu_analysis"
    if prefix_hint == "pricing_strategy":
        return "pricing_strategy"
    if prefix_hint == "item_optimization":
        return "item_optimization"

    msg = message.lower()
    # Param-key detection
    if any(k in params for k in ["quantity_sold", "contribution_margin", "food_cost", "revenue", "profit", "sales_mix"]):
        return "menu_analysis"
    if any(k in params for k in ["item_price", "competitor_price", "elasticity_index", "target_food_cost_percent"]):
        return "pricing_strategy"
    if any(k in params for k in ["portion_size", "portion_cost", "waste_percent", "recipe_ingredients", "description"]):
        return "item_optimization"

    # Keyword detection
    if any(w in msg for w in ["menu analysis", "sales mix", "contribution margin", "menu matrix"]):
        return "menu_analysis"
    if any(w in msg for w in ["pricing strategy", "competitor price", "elasticity", "price optimiz"]):
        return "pricing_strategy"
    if any(w in msg for w in ["item optimiz", "portion", "waste", "recipe costing", "description"]):
        return "item_optimization"

    return "menu_analysis"



def _now_str() -> str:
    return datetime.now().strftime("%B %d, %Y")


def _badge(rating: str) -> str:
    r = rating.lower().replace(" ", "-")
    return f'<div class="badge badge--{r}" style="display:inline-block;margin-top:8px;padding:4px 14px;border-radius:9999px;font-weight:600;">{html.escape(rating)}</div>'


def _kpi_row(label: str, value: str) -> str:
    return f'<tr><td style="padding:6px 10px;color:#6b7280;font-size:0.875rem;">{html.escape(label)}</td><td style="padding:6px 10px;font-weight:600;">{html.escape(str(value))}</td></tr>'


def _section_header(title: str) -> str:
    return f'<h3 style="color:#667eea;margin:1.4rem 0 0.6rem;font-size:1rem;">{html.escape(title)}</h3>'


def _rec_item(text: str) -> str:
    return f'<li style="margin-bottom:0.4rem;">{html.escape(str(text))}</li>'


# ─── Card 1: Menu Analysis ──────────────────────────────────────────────────

def _generate_menu_analysis_html(params: dict) -> str:
    item_name = str(params.get("item") or params.get("item_name") or "Menu Item")
    category = str(params.get("category") or "Uncategorized")

    def _num(*keys: str) -> float | None:
        for k in keys:
            if k in params and params.get(k) not in (None, ""):
                try:
                    return float(params.get(k))
                except Exception:
                    return None
        return None

    qty_sold = _num("quantity_sold", "qty_sold")
    price = _num("price", "item_price", "selling_price")
    cost = _num("cost", "item_cost")
    revenue = _num("revenue", "total_revenue")
    profit = _num("profit", "total_profit")
    food_cost_pct = _num("food_cost", "food_cost_percent", "food_cost_pct")
    contribution_margin = _num("contribution_margin", "cm", "margin")
    contribution_margin_pct = _num(
        "contribution_margin_percent",
        "contribution_margin_pct",
        "cm_percent",
        "margin_percent",
    )

    # Fill missing fields from what we have (do not override explicit inputs)
    if qty_sold and qty_sold > 0:
        if price is None and revenue is not None:
            price = revenue / qty_sold
        if revenue is None and price is not None:
            revenue = price * qty_sold
        if cost is None and revenue is not None and profit is not None:
            cost = (revenue - profit) / qty_sold
        if profit is None and revenue is not None and cost is not None:
            profit = revenue - cost * qty_sold

    if price is not None and price > 0:
        if cost is None and food_cost_pct is not None:
            cost = price * (food_cost_pct / 100)
        if food_cost_pct is None and cost is not None:
            food_cost_pct = (cost / price) * 100
        if contribution_margin is None and cost is not None:
            contribution_margin = price - cost
        if contribution_margin_pct is None and cost is not None:
            contribution_margin_pct = ((price - cost) / price) * 100
        if cost is None and contribution_margin is not None:
            cost = price - contribution_margin
        if cost is None and contribution_margin_pct is not None:
            cost = price * (1 - (contribution_margin_pct / 100))

    # Final defaults for rendering
    qty_sold = float(qty_sold or 0)
    price = float(price or 0)
    cost = float(cost or 0)
    revenue = float(revenue or (price * qty_sold) or 0)
    profit = float(profit or ((revenue - cost * qty_sold) if qty_sold else 0) or 0)
    food_cost_pct = float(food_cost_pct or ((cost / price * 100) if price > 0 else 0) or 0)
    contribution_margin = float(contribution_margin or ((price - cost) if price > 0 else 0) or 0)
    contribution_margin_pct = float(
        contribution_margin_pct
        or ((contribution_margin / price * 100) if price > 0 else 0)
        or 0
    )

    # Compute derived metrics
    # (already computed above)

    # Menu Engineering Matrix quadrant (single item → relative to theoretical averages)
    # With only one item, we assess vs industry benchmarks:
    # Food cost: ideally ≤28% = star territory, ≤35% = plowhorse, >35% = dog
    # High qty + good margin = star; high qty + poor margin = plowhorse
    # Low qty + good margin = puzzle; low qty + poor margin = dog
    if food_cost_pct > 0 and qty_sold > 0 and price > 0:
        good_margin = food_cost_pct <= 32
        high_volume = qty_sold >= 50  # relative heuristic
        if good_margin and high_volume:
            quadrant, q_icon, q_action = "⭐ Star", "star", "Promote heavily — maintain quality and portion size."
        elif high_volume and not good_margin:
            quadrant, q_icon, q_action = "🐴 Plowhorse", "plowhorse", "Increase price or reduce cost to improve margin."
        elif good_margin and not high_volume:
            quadrant, q_icon, q_action = "🧩 Puzzle", "puzzle", "Feature prominently to boost sales volume."
        else:
            quadrant, q_icon, q_action = "🐕 Dog", "dog", "Consider repricing, repositioning, or removing from menu."
    else:
        quadrant, q_icon, q_action = "—", "unknown", "Insufficient data for full quadrant classification."

    # Performance rating
    if price <= 0 or qty_sold <= 0:
        rating = "Needs Review"
    elif food_cost_pct <= 28:
        rating = "Excellent"
    elif food_cost_pct <= 32:
        rating = "Good"
    elif food_cost_pct <= 37:
        rating = "Acceptable"
    else:
        rating = "Needs Improvement"

    # Recommendations
    recs = []
    if food_cost_pct > 32:
        recs.append(f"Reduce food cost from {food_cost_pct:.1f}% toward 28-32% target by renegotiating supplier costs or adjusting recipe yield.")
    else:
        recs.append(f"Maintain current food cost of {food_cost_pct:.1f}% — within target range of 28-32%.")
    if qty_sold < 50:
        recs.append("Boost visibility through menu placement, server upselling, and promotional specials.")
    if contribution_margin > 0:
        recs.append(f"Contribution margin of ${contribution_margin:.2f}/item is {'strong' if contribution_margin > price * 0.6 else 'moderate'} — consider bundling with beverages to increase check average.")
    recs.append(f"Quadrant action: {q_action}")

    include_text = str(params.get("include") or "")
    if "sales mix" in include_text.lower():
        recs.append("Sales mix: This item contributes to the overall menu mix — track sales trends weekly to detect seasonal demand shifts.")
    if "menu matrix" in include_text.lower():
        recs.append("Menu matrix position confirmed. Use golden triangle placement (top-right of menu page) for Stars and Puzzles.")

    parts = [
        '<section class="report">',
        '<header class="report__header">',
        f'<h2>🍽️ Menu Analysis — {html.escape(item_name)}</h2>',
        f'<div class="report__meta">Generated: {_now_str()} | Category: {html.escape(category)}</div>',
        _badge(rating),
        '</header>',
        '<article class="report__body">',
        f'<p class="lead">This menu analysis reveals <strong>{rating.lower()}</strong> performance for <strong>{html.escape(item_name)}</strong>, classified as a <strong>{html.escape(quadrant)}</strong> in the Menu Engineering Matrix.</p>',
        _section_header("📊 Key Performance Metrics"),
        '<table style="width:100%;border-collapse:collapse;">',
        _kpi_row("Item Name", item_name),
        _kpi_row("Category", category),
        _kpi_row("Selling Price", f"${price:.2f}"),
        _kpi_row("Item Cost", f"${cost:.2f}"),
        _kpi_row("Quantity Sold", f"{qty_sold:,.0f}"),
        _kpi_row("Total Revenue", f"${revenue:,.2f}"),
        _kpi_row("Total Profit", f"${profit:,.2f}"),
        _kpi_row("Food Cost %", f"{food_cost_pct:.1f}%"),
        _kpi_row("Contribution Margin", f"${contribution_margin:.2f}"),
        _kpi_row("Contribution Margin %", f"{contribution_margin_pct:.1f}%"),
        '</table>',
        _section_header("🗂️ Menu Engineering Matrix"),
        f'<div style="background:rgba(102,126,234,0.08);border-radius:0.75rem;padding:1rem;">',
        f'<p><strong>Quadrant:</strong> {html.escape(quadrant)}</p>',
        f'<p><strong>Action:</strong> {html.escape(q_action)}</p>',
        '</div>',
        _section_header("💡 Strategic Recommendations"),
        '<ol style="padding-left:1.25rem;">',
        "".join(_rec_item(r) for r in recs),
        '</ol>',
        '</article>',
        '</section>',
    ]
    return "".join(parts)


# ─── Card 2: Pricing Strategy ───────────────────────────────────────────────

def _generate_pricing_strategy_html(params: dict) -> str:
    item_name = str(params.get("item") or params.get("item_name") or "Menu Item")
    item_price = float(params.get("item_price") or params.get("price") or 0)
    item_cost = float(params.get("item_cost") or params.get("cost") or 0)
    competitor_price = float(params.get("competitor_price") or 0)
    target_food_cost = float(params.get("target_food_cost_percent") or params.get("target_food_cost") or 32.0)
    elasticity = float(params.get("elasticity_index") or params.get("elasticity_factor") or 1.0)
    category = str(params.get("category") or "Uncategorized")

    # Derived metrics
    food_cost_pct = (item_cost / item_price * 100) if item_price > 0 else 0
    contribution_margin = item_price - item_cost if item_price > 0 else 0
    vs_competitor_pct = ((item_price - competitor_price) / competitor_price * 100) if competitor_price > 0 else 0
    optimal_price = (item_cost / (target_food_cost / 100)) if target_food_cost > 0 and item_cost > 0 else item_price
    price_gap = item_price - optimal_price

    # Positioning assessment
    if food_cost_pct <= target_food_cost:
        positioning = "Well-Priced"
    elif food_cost_pct <= target_food_cost + 5:
        positioning = "Slightly Underpriced"
    else:
        positioning = "Underpriced"

    if competitor_price > 0 and vs_competitor_pct > 10:
        positioning = "Overpriced vs. Competitors"

    # Performance rating
    if food_cost_pct <= target_food_cost and abs(vs_competitor_pct) <= 10:
        rating = "Excellent"
    elif food_cost_pct <= target_food_cost + 5:
        rating = "Good"
    elif food_cost_pct <= target_food_cost + 10:
        rating = "Acceptable"
    else:
        rating = "Needs Improvement"

    # Elasticity interpretation
    if elasticity < 1.0:
        elasticity_desc = "Inelastic — customers are price-insensitive; price increases are viable."
    elif elasticity == 1.0:
        elasticity_desc = "Unit elastic — price changes directly proportional to demand changes."
    else:
        elasticity_desc = "Elastic — customers are price-sensitive; price increases may reduce demand."

    # Recommendations
    recs = []
    if food_cost_pct > target_food_cost:
        recs.append(f"Raise price from ${item_price:.2f} toward optimal ${optimal_price:.2f} to hit {target_food_cost:.0f}% food cost target.")
    else:
        recs.append(f"Current price ${item_price:.2f} already meets the {target_food_cost:.0f}% food cost target — maintain pricing.")
    if competitor_price > 0:
        if vs_competitor_pct > 10:
            recs.append(f"Price is {vs_competitor_pct:.1f}% above competitor — consider a reduction or perceived value enhancement.")
        elif vs_competitor_pct < -10:
            recs.append(f"Price is {abs(vs_competitor_pct):.1f}% below competitor — there is room to increase price without losing customers.")
        else:
            recs.append(f"Price is within ±10% of competitor (${competitor_price:.2f}), maintaining competitive parity.")
    if elasticity > 1.0:
        recs.append("High price elasticity — focus on perceived value improvements rather than raw price increases.")
    else:
        recs.append("Low elasticity suggests loyal customer base — a modest price increase should not significantly impact volume.")

    include_text = str(params.get("focus_on") or "")
    if "profit" in include_text.lower():
        recs.append("Profit maximization: Monitor weekly contribution margin trends and test price changes in low-traffic periods.")

    ai_recs = generate_ai_strategic_recommendations(
        analysis_type="Menu Pricing Strategy",
        metrics={
            "item_name": item_name,
            "category": category,
            "current_price": round(item_price, 2),
            "item_cost": round(item_cost, 2),
            "food_cost_percent": round(food_cost_pct, 1),
            "target_food_cost_percent": round(target_food_cost, 1),
            "contribution_margin": round(contribution_margin, 2),
            "optimal_price": round(optimal_price, 2),
            "price_gap_vs_optimal": round(price_gap, 2),
            "competitor_price": round(competitor_price, 2) if competitor_price else None,
            "vs_competitor_percent": round(vs_competitor_pct, 1) if competitor_price else None,
            "price_elasticity_index": elasticity,
        },
        performance={
            "rating": rating,
            "positioning": positioning,
            "elasticity": elasticity_desc,
        },
        benchmarks={
            "target_food_cost_range": "28-32%",
            "competitive_tolerance": "±10%",
        },
        additional_data={"focus_on": include_text},
        existing_recommendations=recs,
        max_items=6,
    )
    if ai_recs:
        recs = ai_recs

    parts = [
        '<section class="report">',
        '<header class="report__header">',
        f'<h2>💰 Pricing Strategy — {html.escape(item_name)}</h2>',
        f'<div class="report__meta">Generated: {_now_str()} | Category: {html.escape(category)}</div>',
        _badge(rating),
        '</header>',
        '<article class="report__body">',
        f'<p class="lead">This pricing analysis reveals <strong>{rating.lower()}</strong> performance for <strong>{html.escape(item_name)}</strong> with a current positioning of <strong>{html.escape(positioning)}</strong>.</p>',
        _section_header("📊 Pricing Metrics"),
        '<table style="width:100%;border-collapse:collapse;">',
        _kpi_row("Item Name", item_name),
        _kpi_row("Category", category),
        _kpi_row("Current Price", f"${item_price:.2f}"),
        _kpi_row("Item Cost", f"${item_cost:.2f}"),
        _kpi_row("Food Cost %", f"{food_cost_pct:.1f}%"),
        _kpi_row("Target Food Cost %", f"{target_food_cost:.0f}%"),
        _kpi_row("Contribution Margin", f"${contribution_margin:.2f}"),
        _kpi_row("Optimal Price (at target cost %)", f"${optimal_price:.2f}"),
        _kpi_row("Price Gap vs. Optimal", f"${price_gap:+.2f}"),
        _kpi_row("Competitor Price", f"${competitor_price:.2f}" if competitor_price else "N/A"),
        _kpi_row("vs. Competitor", f"{vs_competitor_pct:+.1f}%" if competitor_price else "N/A"),
        _kpi_row("Price Elasticity Index", str(elasticity)),
        '</table>',
        _section_header("📐 Industry Benchmarks"),
        '<table style="width:100%;border-collapse:collapse;">',
        _kpi_row("Target Food Cost Range", "28-32%"),
        _kpi_row("Competitive Tolerance", "±10%"),
        _kpi_row("Price Positioning", positioning),
        '</table>',
        _section_header("📈 Elasticity Analysis"),
        f'<p style="margin:0.5rem 0;color:#374151;">{html.escape(elasticity_desc)}</p>',
        _section_header("💡 Strategic Recommendations"),
        '<ol style="padding-left:1.25rem;">',
        "".join(_rec_item(r) for r in recs),
        '</ol>',
        '</article>',
        '</section>',
    ]
    return "".join(parts)


# ─── Card 3: Item Optimization ──────────────────────────────────────────────

def _generate_item_optimization_html(params: dict) -> str:
    item_name = str(params.get("item") or params.get("item_name") or "Menu Item")
    qty_sold = float(params.get("quantity_sold") or params.get("qty_sold") or 0)
    item_cost = float(params.get("item_cost") or params.get("cost") or 0)
    portion_size = str(params.get("portion_size") or "N/A")
    portion_cost = float(params.get("portion_cost") or 0)
    waste_pct = float(params.get("waste_percent") or params.get("waste_percentage") or params.get("waste") or 0)
    recipe_ingredients = str(params.get("recipe_ingredients") or params.get("ingredients") or "")
    description = str(params.get("description") or "")
    category = str(params.get("category") or "Uncategorized")

    # Derived metrics
    effective_cost = item_cost * (1 + waste_pct / 100) if item_cost > 0 else 0
    waste_cost_per_unit = item_cost * (waste_pct / 100) if item_cost > 0 else 0
    total_waste_cost = waste_cost_per_unit * qty_sold if qty_sold > 0 else 0
    cost_savings_potential = total_waste_cost * 0.5  # assume 50% recoverable

    # Rating based on waste %
    if waste_pct <= 3:
        rating = "Excellent"
    elif waste_pct <= 6:
        rating = "Good"
    elif waste_pct <= 10:
        rating = "Acceptable"
    else:
        rating = "Needs Improvement"

    # Description quality check
    desc_len = len(description.strip())
    if desc_len >= 80:
        desc_rating = "Strong"
        desc_tip = "Description length is good. Consider adding sensory/origin language to further entice guests."
    elif desc_len >= 40:
        desc_rating = "Moderate"
        desc_tip = "Consider expanding description with sensory words (crispy, smoky, house-made) and origin details."
    elif desc_len > 0:
        desc_rating = "Weak"
        desc_tip = "Short description. Add flavour-forward language, preparation method, and key ingredients to boost appeal."
    else:
        desc_rating = "Missing"
        desc_tip = "No description provided. A well-crafted description with sensory words can increase item sales by 20-30%."

    # Recommendations
    recs = []
    if waste_pct > 5:
        recs.append(f"Reduce waste from {waste_pct:.0f}% toward ≤5% through FIFO storage, par-level training, and daily waste tracking.")
        recs.append(f"Estimated waste cost: ${waste_cost_per_unit:.2f}/serving × {qty_sold:.0f} sold = ${total_waste_cost:.2f} total. Potential saving: ~${cost_savings_potential:.2f}.")
    else:
        recs.append(f"Waste at {waste_pct:.0f}% is within acceptable range. Continue portion discipline and FIFO protocols.")

    if portion_cost > 0 and item_cost > 0 and portion_cost > item_cost * 0.5:
        recs.append(f"Portion cost (${portion_cost:.2f}) represents a significant share of item cost (${item_cost:.2f}). Review portion size or supplier pricing.")
    if recipe_ingredients:
        recs.append(f"Standardize recipe card for: {recipe_ingredients}. Ensure every serve uses consistent weights/measures.")
    recs.append(f"Description ({desc_rating}): {desc_tip}")

    include_text = str(params.get("include") or "")
    if "recipe costing" in include_text.lower():
        recs.append("Recipe costing: Re-cost recipe quarterly to account for ingredient price fluctuations.")
    if "portion control" in include_text.lower():
        recs.append("Portion control: Use portion scales or pre-portioned containers to eliminate cook-level variation.")

    ai_recs = generate_ai_strategic_recommendations(
        analysis_type="Menu Item Optimization",
        metrics={
            "item_name": item_name,
            "category": category,
            "quantity_sold": round(qty_sold, 2),
            "item_cost": round(item_cost, 2),
            "portion_cost": round(portion_cost, 2) if portion_cost else None,
            "waste_percent": round(waste_pct, 1),
            "effective_cost": round(effective_cost, 2),
            "waste_cost_per_unit": round(waste_cost_per_unit, 2),
            "total_waste_cost": round(total_waste_cost, 2),
            "cost_savings_potential": round(cost_savings_potential, 2),
            "description_rating": desc_rating,
        },
        performance={
            "rating": rating,
            "description_tip": desc_tip,
        },
        benchmarks={
            "target_waste_percent": "≤5%",
        },
        additional_data={
            "portion_size": portion_size,
            "recipe_ingredients": recipe_ingredients,
            "include": include_text,
        },
        existing_recommendations=recs,
        max_items=6,
    )
    if ai_recs:
        recs = ai_recs

    parts = [
        '<section class="report">',
        '<header class="report__header">',
        f'<h2>🥗 Item Optimization — {html.escape(item_name)}</h2>',
        f'<div class="report__meta">Generated: {_now_str()} | Category: {html.escape(category)}</div>',
        _badge(rating),
        '</header>',
        '<article class="report__body">',
        f'<p class="lead">This item optimization reveals <strong>{rating.lower()}</strong> efficiency for <strong>{html.escape(item_name)}</strong> with <strong>{waste_pct:.0f}% waste</strong>.</p>',
        _section_header("📊 Recipe & Portion Metrics"),
        '<table style="width:100%;border-collapse:collapse;">',
        _kpi_row("Item Name", item_name),
        _kpi_row("Quantity Sold", f"{qty_sold:,.0f}"),
        _kpi_row("Item Cost (per serving)", f"${item_cost:.2f}"),
        _kpi_row("Portion Size", portion_size),
        _kpi_row("Portion Cost", f"${portion_cost:.2f}" if portion_cost else "N/A"),
        _kpi_row("Waste %", f"{waste_pct:.1f}%"),
        _kpi_row("Effective Cost (with waste)", f"${effective_cost:.2f}"),
        _kpi_row("Waste Cost per Serving", f"${waste_cost_per_unit:.2f}"),
        _kpi_row("Total Waste Cost (all sales)", f"${total_waste_cost:.2f}"),
        '</table>',
    ]

    if recipe_ingredients:
        parts += [
            _section_header("🧾 Recipe Costing"),
            '<div style="background:rgba(102,126,234,0.07);border-radius:0.75rem;padding:1rem;">',
            f'<p><strong>Ingredients:</strong> {html.escape(recipe_ingredients)}</p>',
            '<p style="font-size:0.875rem;color:#6b7280;">Ensure a standardized recipe card with exact weights/measures for each ingredient to maintain consistent food cost.</p>',
            '</div>',
        ]

    if description:
        parts += [
            _section_header("✍️ Description Analysis"),
            '<div style="background:rgba(102,126,234,0.07);border-radius:0.75rem;padding:1rem;">',
            f'<p><strong>Current:</strong> {html.escape(description)}</p>',
            f'<p><strong>Quality:</strong> {html.escape(desc_rating)}</p>',
            f'<p style="font-size:0.875rem;color:#6b7280;">{html.escape(desc_tip)}</p>',
            '</div>',
        ]

    parts += [
        _section_header("💡 Optimization Recommendations"),
        '<ol style="padding-left:1.25rem;">',
        "".join(_rec_item(r) for r in recs),
        '</ol>',
        '</article>',
        '</section>',
    ]
    return "".join(parts)



def _format_menu_csv_report_html(result: dict) -> str:
    if not isinstance(result, dict):
        return _ensure_html(str(result))

    if result.get("status") == "error":
        message = html.escape(str(result.get("message") or "Unknown error"))
        help_text = result.get("help")
        your_columns = result.get("your_columns")

        parts = [
            '<div class="report">',
            '<div class="report__header" style="background: linear-gradient(135deg, #ef4444, #dc2626);">',
            "<h2>❌ Menu CSV Analysis Error</h2>",
            "</div>",
            '<div class="report__body">',
            f"<p><strong>Error:</strong> {message}</p>",
        ]
        if help_text:
            parts.append(f"<p><strong>Help:</strong> {html.escape(str(help_text))}</p>")
        if your_columns and isinstance(your_columns, list):
            safe_cols = ", ".join(html.escape(str(c)) for c in your_columns)
            parts.append(f"<p><strong>Found columns:</strong> {safe_cols}</p>")
        parts.extend(["</div>", "</div>"])
        return "".join(parts)

    html_report = (
        result.get("business_report_html")
        or result.get("data", {}).get("business_report_html")
        or result.get("business_report")
        or result.get("data", {}).get("business_report")
    )
    return _ensure_html(str(html_report))



@method_decorator(csrf_exempt, name="dispatch")
class MenuChatAPIView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]
    parser_classes = [JSONParser]

    def post(self, request, *args, **kwargs):
        serializer = MenuChatRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                _error_payload(code="VALIDATION_ERROR", message="Invalid request body.", details=serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )

        message: str = serializer.validated_data["message"]
        language = request.data.get("language", "en")

        if language and language != "en":
            from apps.chat_assistant.translation_utils import translate_prompt_to_english
            message = translate_prompt_to_english(message, language)

        try:
            params, prefix_hint = _parse_kv_message(message)
            subtask = _detect_subtask(message, params, prefix_hint)

            if not params:
                return Response(
                    {
                        "html_response": translate_html_response(
                            _ensure_html(
                                "Please provide menu item details as key:value pairs.\n"
                                "Example: Item: Chicken Biryani, Quantity Sold: 125, Price: $19.00, Cost: $6.20"
                            ),
                            language,
                        )
                    },
                    status=status.HTTP_200_OK,
                )

            if subtask == "menu_analysis":
                html_response = _generate_menu_analysis_html(params)
            elif subtask == "pricing_strategy":
                html_response = _generate_pricing_strategy_html(params)
            else:  # item_optimization
                html_response = _generate_item_optimization_html(params)

            return Response({"html_response": translate_html_response(_ensure_html(html_response), language)}, status=status.HTTP_200_OK)

        except Exception as exc:
            trace_id = str(uuid4())
            logger.exception("Menu chat API failed trace_id=%s: %s", trace_id, exc)
            return Response(
                _error_payload(code="INTERNAL_ERROR", message="Server error while generating menu analysis.", trace_id=trace_id),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@method_decorator(csrf_exempt, name="dispatch")
class MenuUploadAPIView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        if "required_csv" not in request.FILES:
            return Response(
                _error_payload(code="VALIDATION_ERROR", message="required_csv file is missing from the upload."),
                status=status.HTTP_400_BAD_REQUEST,
            )

        required_csv = request.FILES["required_csv"]
        file_name = getattr(required_csv, "name", "") or ""
        if not file_name.lower().endswith(".csv"):
            return Response(
                _error_payload(code="VALIDATION_ERROR", message="required_csv must be a .csv file."),
                status=status.HTTP_400_BAD_REQUEST,
            )

        analysis_type = (request.data.get("analysis_type") or "").strip() or None
        if analysis_type in {"auto", ""}:
            analysis_type = None
        
        language = request.data.get("language", "en")

        try:
            from backend.consulting_services.menu.pricing_csv_processor import process_pricing_csv_data
            from backend.consulting_services.menu.optimization_csv_processor import process_optimization_csv_data
            from backend.consulting_services.menu.design_csv_processor import process_design_csv_data

            raw_bytes = required_csv.read()

            def _fresh() -> io.BytesIO:
                return io.BytesIO(raw_bytes)

            def _sniff_columns(data: bytes) -> set[str]:
                try:
                    import csv
                    reader = csv.reader(io.StringIO(data.decode("utf-8", errors="replace")))
                    header = next(reader, [])
                    return {c.strip().lower() for c in header if c.strip()}
                except Exception:
                    return set()

            columns = _sniff_columns(raw_bytes)

            PRICING_COLS = {"item_price", "price", "item_cost", "cost", "competitor_price"}
            OPTIMIZATION_COLS = {"waste_percent", "waste", "portion_size", "portion_cost", "description"}
            DESIGN_COLS = {"quantity_sold", "quantity", "item_name", "menu item"}

            def _normalise(s: str) -> str:
                return re.sub(r"[\s_-]+", "", s.lower())

            normalised_cols = {_normalise(c) for c in columns}

            def _any_match(target_set: set[str]) -> bool:
                return any(_normalise(t) in normalised_cols for t in target_set)

            result: dict | None = None

            if analysis_type == "pricing_strategy":
                result = process_pricing_csv_data(_fresh())
            elif analysis_type == "item_optimization":
                result = process_optimization_csv_data(_fresh())
            elif analysis_type == "menu_analysis":
                result = process_design_csv_data(_fresh())
            else:
                # Smart detection: pricing columns win if present and specific
                if _any_match(PRICING_COLS) and _any_match({"competitor_price"}):
                    result = process_pricing_csv_data(_fresh())
                elif _any_match(OPTIMIZATION_COLS):
                    result = process_optimization_csv_data(_fresh())
                elif _any_match(DESIGN_COLS):
                    result = process_design_csv_data(_fresh())
                else:
                    # Try all three
                    for fn in [process_design_csv_data, process_pricing_csv_data, process_optimization_csv_data]:
                        attempt = fn(_fresh())
                        if isinstance(attempt, dict) and attempt.get("status") == "success":
                            result = attempt
                            break

                if result is None:
                    col_list = sorted(columns) or ["(none detected)"]
                    result = {
                        "status": "error",
                        "message": "CSV columns did not match any known menu analysis type.",
                        "your_columns": col_list,
                        "help": (
                            "Menu Analysis needs: item_name, quantity_sold, price. "
                            "Pricing Strategy needs: item_name, item_price, item_cost, competitor_price. "
                            "Item Optimization needs: item_name, quantity_sold (plus optional waste_percent, portion_cost, description)."
                        ),
                    }

            html_response = _format_menu_csv_report_html(result or {})
            return Response({"html_response": translate_html_response(_ensure_html(str(html_response)), language)}, status=status.HTTP_200_OK)

        except Exception as exc:
            trace_id = str(uuid4())
            logger.exception("Menu upload API failed trace_id=%s: %s", trace_id, exc)
            return Response(
                _error_payload(code="INTERNAL_ERROR", message="Server error while processing menu CSV upload.", trace_id=trace_id),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
