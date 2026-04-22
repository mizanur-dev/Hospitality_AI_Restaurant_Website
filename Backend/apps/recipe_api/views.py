from __future__ import annotations

import html
import io
import logging
import re
from uuid import uuid4

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import RecipeChatRequestSerializer
from apps.chat_assistant.translation_utils import translate_html_response

logger = logging.getLogger(__name__)



def _error_payload(*, code: str, message: str, details=None, trace_id: str | None = None):
    payload = {"error": {"code": code, "message": message}}
    if details is not None:
        payload["error"]["details"] = details
    if trace_id:
        payload["error"]["trace_id"] = trace_id
    return payload


def _ensure_html(value) -> str:
    text = str(value) if not isinstance(value, str) else value
    text = text.strip()
    if not text:
        return "<div>No analysis returned.</div>"
    if "<" in text and ">" in text:
        return text
    return f'<div style="font-family:inherit; white-space:pre-wrap">{html.escape(text)}</div>'


def _extract_report_html(result_tuple) -> str | None:
    """Pull business_report_html from a (dict, int) tuple returned by run()."""
    if not isinstance(result_tuple, tuple) or len(result_tuple) < 1:
        return None
    result_dict = result_tuple[0]
    if not isinstance(result_dict, dict):
        return None
    # success_payload wraps data inside 'data'
    html_report = (
        result_dict.get("data", {}).get("business_report_html")
        or result_dict.get("business_report_html")
        or result_dict.get("data", {}).get("business_report")
        or result_dict.get("business_report")
    )
    return html_report or None


def _is_error_result(result_tuple) -> tuple[bool, str]:
    if not isinstance(result_tuple, tuple) or len(result_tuple) < 1:
        return True, "No result returned."
    d = result_tuple[0]
    if isinstance(d, dict) and d.get("status") == "error":
        err = d.get("error") or d.get("message") or "Unknown error."
        # error_payload stores message as a plain string in d["error"]
        if isinstance(err, dict):
            err = err.get("message") or "Unknown error."
        return True, str(err)
    return False, ""



def _coerce(value: str):
    raw = value.strip().rstrip(".,;")
    if not raw:
        return ""
    num = re.sub(r"[$,%]", "", raw).replace(",", "")
    try:
        if re.fullmatch(r"-?\d+", num):
            return int(num)
        if re.fullmatch(r"-?\d*\.\d+", num):
            return float(num)
    except Exception:
        pass
    return raw


def _extract_quoted(text: str) -> tuple[str, str]:
    """Return (first_quoted_value, text_with_that_quote_removed)."""
    m = re.search(r'"([^"]+)"', text)
    if m:
        return m.group(1).strip(), text[:m.start()] + text[m.end():]
    return "", text


def _extract_ingredients_block(text: str) -> tuple[str, str]:
    """
    Pull 'ingredients: <...>' block from text.
    Returns (ingredients_string, remaining_text).
    The block ends at the next recognised keyword.
    """
    STOP_WORDS = (
        r"ingredient_cost|labor_cost|recipe_price|recipe_name|servings?"
        r"|prep_time|cook_time|target_margin|portion_cost|total_cost"
        r"|include|calculate|focus|note"
    )
    m = re.search(
        rf"ingredients?\s*:\s*((?:(?!(?:{STOP_WORDS})\s*[:\d]).){{1,500}})",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if m:
        ingredients_str = m.group(1).strip().rstrip(",. ")
        remaining = text[: m.start()] + text[m.end() :]
        return ingredients_str, remaining
    return "", text


def _parse_kv(text: str) -> dict:
    """Simple key:value / key value parser."""
    params: dict = {}
    # key: value  (colon-separated)
    for m in re.finditer(
        r"(?P<key>[A-Za-z_][A-Za-z0-9_ ]*?)\s*:\s*(?P<value>[^,\n]+)",
        text,
    ):
        key = re.sub(r"\s+", "_", m.group("key").strip().lower()).strip("_")
        if key:
            params[key] = _coerce(m.group("value"))

    # key value  (space-separated, numeric only)
    for m in re.finditer(
        r"\b(?P<key>[a-z_][a-z0-9_]{2,})\s+(?P<value>[$]?\d+(?:[.,]\d+)?%?)\b",
        text,
        re.IGNORECASE,
    ):
        key = m.group("key").lower()
        if key not in params:
            params[key] = _coerce(m.group("value"))

    return params


def _strip_prefix(message: str) -> tuple[str, str]:
    """Strip opening instruction line, return (body, hint_label)."""
    PREFIXES = {
        "create a recipe": "create_recipe",
        "analyze recipe cost": "cost_analysis",
        "analyse recipe cost": "cost_analysis",
        "scale ": "scale_recipe",
    }
    first_line = message.split("\n")[0].lower()
    for pat, label in PREFIXES.items():
        if pat in first_line:
            body = re.sub(re.escape(first_line), "", message, count=1, flags=re.IGNORECASE).strip()
            return body or message, label
    return message, ""


def _detect_subtask(message: str, params: dict, hint: str) -> str:
    if hint in ("create_recipe", "cost_analysis", "scale_recipe"):
        return hint
    msg = message.lower()
    if any(k in params for k in ["prep_time", "cook_time"]):
        return "create_recipe"
    if any(k in params for k in ["portion_cost"]):
        return "cost_analysis"
    if any(w in msg for w in ["scale ", "scaling", "serves ", "to 48", "to 24", "to 96"]):
        return "scale_recipe"
    if any(w in msg for w in ["create a recipe", "recipe named", "create recipe"]):
        return "create_recipe"
    if any(w in msg for w in ["analyze recipe cost", "cost analysis", "food cost", "margin"]):
        return "cost_analysis"
    return "create_recipe"


def _parse_scale_servings(message: str) -> tuple[float, float]:
    """Extract (current_servings, target_servings) from 'serves X to Y' patterns."""
    patterns = [
        r"serves?\s+(\d+(?:\.\d+)?)\s+to\s+(\d+(?:\.\d+)?)",
        r"(\d+(?:\.\d+)?)\s+to\s+(\d+(?:\.\d+)?)\s+servings?",
        r"serving\s+(\d+(?:\.\d+)?)\s+to\s+(\d+(?:\.\d+)?)",
    ]
    for pat in patterns:
        m = re.search(pat, message, re.IGNORECASE)
        if m:
            return float(m.group(1)), float(m.group(2))
    return 0.0, 0.0



def _re_parse_ingredients(raw: str) -> list[dict]:
    """Parse ingredient string into list of {name, amount, unit}."""
    items = []
    parts = [p.strip() for p in re.split(r"[;,]+", raw) if p.strip()]
    for p in parts:
        m = re.match(
            r"^([A-Za-z][A-Za-z0-9 \-]*?)\s+([0-9]+(?:\.[0-9]+)?)\s*([A-Za-z]+)?$",
            p.strip(),
        )
        if m:
            items.append({
                "name": m.group(1).strip(),
                "amount": float(m.group(2)),
                "unit": (m.group(3) or "").strip(),
            })
        else:
            items.append({"name": p, "amount": 0.0, "unit": ""})
    return items


def _recipe_steps(recipe_name: str, ingredients: list[dict], method: str,
                  prep: float, cook: float) -> list[str]:
    """Return 6-8 concise preparation steps tailored to the recipe."""
    rn = recipe_name.lower()
    ing_names = [i["name"].lower() for i in ingredients]

    def _has(*words):
        return any(w in rn or any(w in n for n in ing_names) for w in words)

    # Step templates by method / main protein
    if _has("salmon", "fish", "tuna", "cod", "sea bass", "halibut"):
        return [
            f"Remove {recipe_name} portions from the refrigerator 15 minutes before cooking to bring to room temperature.",
            "Pat fish dry with paper towels. Season generously with salt, cracked black pepper, and fresh lemon juice.",
            "Combine butter and minced garlic in a small bowl; set aside for basting.",
            f"Preheat grill / pan to medium-high heat (375–400 °F | 190–200 °C). Lightly oil the grates.",
            "Place fish skin-side down. Grill for 4–5 minutes until skin is crisp and releases easily.",
            "Flip gently, brush with garlic butter. Cook 3–4 minutes until internal temperature reaches 145 °F (63 °C).",
            "Rest on a warm plate for 2 minutes before plating. Garnish with lemon wedges and fresh herbs.",
            "Plate over your chosen side (rice, asparagus, or a light salad) and drizzle with remaining pan juices.",
        ]
    if _has("chicken"):
        return [
            f"Trim and pat {recipe_name} dry. Score thicker portions for even cooking.",
            "Marinate with olive oil, lemon, garlic, and chosen herbs for at minimum 30 minutes.",
            f"Preheat {method.lower()} surface to medium-high heat. Season with salt and pepper just before cooking.",
            "Sear skin-side down 5–6 minutes until golden. Flip and cook a further 6–8 minutes.",
            "Baste with pan juices every 2 minutes. Internal temperature must reach 165 °F (74 °C).",
            "Rest 5 minutes before slicing to retain juices.",
            "Deglaze pan with stock or white wine; reduce 2 minutes and spoon sauce over plated chicken.",
        ]
    if _has("beef", "steak", "sirloin", "tenderloin"):
        return [
            "Bring beef to room temperature; 30 minutes on the counter ensures even cooking.",
            "Season liberally with coarse salt and cracked pepper on all sides.",
            "Heat a cast-iron pan or grill to smoking-hot. Add a high-smoke-point oil.",
            "Sear 2–3 minutes per side for medium-rare (internal 130 °F | 54 °C). Adjust to desired doneness.",
            "Add butter, garlic, and rosemary; baste continuously for 1 minute.",
            "Rest on a rack for at least 5 minutes before slicing against the grain.",
        ]
    if _has("pasta", "spaghetti", "fettuccine", "linguine", "penne"):
        return [
            "Bring a large pot of generously salted water to a rolling boil.",
            f"Cook pasta 1–2 minutes less than package directions (it will finish in the sauce).",
            "While pasta cooks, prepare your sauce: sauté aromatics in olive oil, add liquid, and simmer.",
            "Reserve 1 cup pasta water before draining — this starch thickens the sauce.",
            "Toss drained pasta directly in the sauce pan over medium heat; add pasta water gradually to reach desired consistency.",
            "Fold in proteins or vegetables. Taste and adjust seasoning.",
            f"Plate immediately with fresh herbs, grated cheese, and a drizzle of extra-virgin olive oil.",
        ]
    if _has("soup", "bisque", "chowder", "broth"):
        return [
            "Sweat aromatics (onion, celery, carrot) in butter or oil over medium-low heat until translucent (8–10 min).",
            "Add dry spices and toast 60 seconds to bloom their flavour.",
            "Add stock and main ingredients. Bring to a gentle boil, then reduce to a simmer.",
            f"Simmer uncovered for {int(cook) or 25} minutes, stirring occasionally.",
            "Taste at the halfway point and adjust salt, acid (lemon/vinegar), and seasoning.",
            "For a smooth texture, blend in batches using an immersion blender. Strain through a fine sieve for bisque.",
            "Adjust consistency with extra stock or cream. Serve with crusty bread or a garnish of herbs and croutons.",
        ]
    # Generic fallback
    return [
        f"Gather and prep all mise-en-place: wash, peel, and measure every ingredient before cooking.",
        f"Season the main components of {recipe_name} and allow to rest for {int(prep) or 15} minutes if marinating.",
        "Heat your cooking surface (pan, grill, or oven) to the target temperature before adding food.",
        "Add ingredients in order of longest cooking time first to ensure everything is done simultaneously.",
        f"Cook for {int(cook) or 20} minutes, checking at the halfway mark and adjusting heat as needed.",
        "Taste frequently; season in layers — salt early, acid (lemon/vinegar) at the end.",
        "Rest protein components before cutting. Assemble on warm plates and garnish with fresh herbs.",
    ]


def _ingredient_suggestions(recipe_name: str, ing_names: list[str]) -> list[dict]:
    """Return a list of {name, reason} complementary ingredient suggestions."""
    rn = recipe_name.lower()

    def _has(*words):
        return any(w in rn or any(w in n for n in ing_names) for w in words)

    if _has("salmon", "fish", "tuna", "cod", "sea bass"):
        return [
            {"name": "Fresh Dill", "reason": "Classic pairing with salmon — brightens the dish and adds grassy freshness."},
            {"name": "Capers", "reason": "Briny punch that cuts through the richness of the butter sauce."},
            {"name": "Dijon Mustard", "reason": "Emulsifies beautifully into a glaze; adds pleasant heat and depth."},
            {"name": "Cherry Tomatoes", "reason": "Roast alongside the fish for natural acidity and colour."},
            {"name": "Asparagus", "reason": "Premium restaurant pairing; roasts in same time as salmon."},
        ]
    if _has("chicken"):
        return [
            {"name": "Fresh Rosemary", "reason": "Woody herb that complements chicken beautifully when roasted."},
            {"name": "Sundried Tomatoes", "reason": "Concentrated sweetness and umami; great in pan sauces."},
            {"name": "Smoked Paprika", "reason": "Adds a subtle smokiness and gorgeous deep-red colour."},
            {"name": "White Wine", "reason": "Deglazes the pan and builds a bright, acidic sauce base."},
            {"name": "Tarragon", "reason": "Anise-forward herb traditional in French chicken dishes."},
        ]
    if _has("beef", "steak"):
        return [
            {"name": "Shallots", "reason": "Sweeter than onion; creates a refined pan sauce."},
            {"name": "Mushrooms", "reason": "Earthy umami that amplifies the richness of beef."},
            {"name": "Red Wine (Cabernet)", "reason": "Classic reduction sauce base — tannins complement beef."},
            {"name": "Horseradish Cream", "reason": "Sharp condiment that cuts through fat and enriches every bite."},
            {"name": "Blue Cheese Butter", "reason": "Compound butter that melts over hot steak for a luxurious finish."},
        ]
    if _has("pasta"):
        return [
            {"name": "Fresh Basil", "reason": "Essential Italian herb — add off the heat to preserve bright flavour."},
            {"name": "Pecorino Romano", "reason": "Sharper alternative to Parmesan; elevates simple pasta sauces."},
            {"name": "Chilli Flakes", "reason": "Small amount adds background heat without overpowering."},
            {"name": "Pine Nuts (toasted)", "reason": "Buttery crunch and flavour contrast in finished pasta dishes."},
        ]
    if _has("soup"):
        return [
            {"name": "Crème Fraîche", "reason": "Swirled in at service for richness and a slight tang."},
            {"name": "Sourdough Croutons", "reason": "Texture contrast; can be baked with herbs and olive oil."},
            {"name": "Smoked Paprika Oil", "reason": "Drizzle for visual appeal and a smoky finish note."},
            {"name": "Parmesan Rind", "reason": "Simmered in the broth adds deep umami to any soup."},
        ]
    # Generic
    return [
        {"name": "Fresh Herbs (Parsley, Chives)", "reason": "Finishing herbs brighten any savoury dish instantly."},
        {"name": "Good Olive Oil", "reason": "A high-quality finishing drizzle adds flavour complexity."},
        {"name": "Lemon Zest", "reason": "Adds aromatic citrus oils without extra liquid."},
        {"name": "Toasted Seeds/Nuts", "reason": "Textural contrast and healthy fats in the final dish."},
    ]


def _estimate_nutrition(recipe_name: str, ing_names: list[str], servings: float) -> dict:
    """Rough per-serving nutrition estimates based on recipe category."""
    rn = recipe_name.lower()

    def _has(*words):
        return any(w in rn or any(w in n for n in ing_names) for w in words)

    if _has("salmon", "fish", "tuna", "cod", "sea bass", "halibut"):
        return {"Calories": "285 kcal", "Protein": "34 g", "Total Fat": "14 g",
                "Saturated Fat": "5 g", "Carbohydrates": "2 g", "Sodium": "320 mg", "Omega-3": "~2.5 g"}
    if _has("chicken"):
        return {"Calories": "265 kcal", "Protein": "31 g", "Total Fat": "12 g",
                "Saturated Fat": "4 g", "Carbohydrates": "5 g", "Sodium": "350 mg", "Iron": "1.2 mg"}
    if _has("beef", "steak"):
        return {"Calories": "385 kcal", "Protein": "29 g", "Total Fat": "24 g",
                "Saturated Fat": "10 g", "Carbohydrates": "4 g", "Sodium": "420 mg", "Iron": "3.1 mg"}
    if _has("pasta"):
        return {"Calories": "430 kcal", "Protein": "15 g", "Total Fat": "14 g",
                "Saturated Fat": "5 g", "Carbohydrates": "60 g", "Sodium": "280 mg", "Fibre": "3 g"}
    if _has("soup"):
        return {"Calories": "180 kcal", "Protein": "8 g", "Total Fat": "6 g",
                "Saturated Fat": "2 g", "Carbohydrates": "22 g", "Sodium": "580 mg", "Fibre": "4 g"}
    if _has("salad", "slaw"):
        return {"Calories": "145 kcal", "Protein": "5 g", "Total Fat": "9 g",
                "Saturated Fat": "2 g", "Carbohydrates": "14 g", "Sodium": "190 mg", "Fibre": "5 g"}
    return {"Calories": "320 kcal", "Protein": "20 g", "Total Fat": "14 g",
            "Saturated Fat": "5 g", "Carbohydrates": "28 g", "Sodium": "380 mg", "Fibre": "2 g"}


def _call_openai_for_recipe(
    recipe_name: str,
    servings: int,
    prep_time: int,
    cook_time: int,
    ingredients_raw: str,
    ingredient_cost: float,
    labor_cost: float,
    recipe_price: float,
    total_cost: float,
    cost_per_serving: float,
    food_cost_pct: float,
    margin_pct: float,
) -> dict | None:
    """
    Call OpenAI gpt-4o with response_format=json_object to generate:
      - steps: list[str]
      - suggestions: list[{name, reason}]
      - nutrition: {label: value_str, ...}
      - nutrition_note: str
      - method: str
      - chef_note: str  (one-sentence flavour tip)
    Returns the parsed dict, or None if the API key is absent / call fails.
    """
    import json as _json
    import os

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        system_prompt = (
            "You are an expert chef and culinary consultant for a restaurant management platform. "
            "Respond ONLY with a valid JSON object (no markdown, no prose outside the JSON). "
            "The JSON must have exactly these keys:\n"
            '  "method": string — cooking method (e.g. "Grilling", "Baking / Roasting", "Pan-Frying", "Simmering")\n'
            '  "steps": array of 6-8 strings — professional preparation steps, written like a culinary instructor\n'
            '  "suggestions": array of 4-5 objects with keys "name" (string) and "reason" (string) — '
            "complementary ingredients with a chef's rationale for each\n"
            '  "nutrition": object with string keys (e.g. "Calories", "Protein", "Total Fat", "Saturated Fat", '
            '"Carbohydrates", "Sodium", "Fibre") and string values (e.g. "285 kcal", "34 g")\n'
            '  "nutrition_note": string — one or two sentences explaining what drives the key nutrition numbers\n'
            '  "chef_note": string — one memorable tip that elevates this dish'
        )

        user_prompt = (
            f"Recipe Name: {recipe_name}\n"
            f"Servings: {servings}\n"
            f"Prep Time: {prep_time} min | Cook Time: {cook_time} min\n"
            f"Ingredients: {ingredients_raw or 'not specified'}\n"
            f"Batch Ingredient Cost: ${ingredient_cost:.2f} | Labor Cost: ${labor_cost:.2f}\n"
            f"Total Batch Cost: ${total_cost:.2f} | Cost per Serving: ${cost_per_serving:.2f}\n"
            f"Sale Price per Serving: ${recipe_price:.2f} | Food Cost %: {food_cost_pct:.1f}% | "
            f"Profit Margin: {margin_pct:.1f}%\n\n"
            "Generate the JSON recipe analysis now."
        )

        response = client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=1600,
        )
        raw = response.choices[0].message.content or "{}"
        return _json.loads(raw)
    except Exception as exc:
        logger.warning("OpenAI call failed in _generate_create_recipe_html: %s", exc)
        return None


def _generate_create_recipe_html(params: dict) -> str:
    """Build a rich, fully AI-generated HTML response for Card 1 (Create Recipe)."""
    from datetime import datetime as _dt

    recipe_name = str(params.get("recipe_name") or "New Recipe").strip()
    servings = float(params.get("servings") or 1)
    prep_time = float(params.get("prep_time") or 0)
    cook_time = float(params.get("cook_time") or 0)
    ingredient_cost = float(params.get("ingredient_cost") or 0)
    labor_cost = float(params.get("labor_cost") or 0)
    recipe_price = float(params.get("recipe_price") or 0)
    ingredients_raw = str(params.get("ingredients") or "")

    total_cost = ingredient_cost + labor_cost
    cost_per_serving = total_cost / servings if servings else 0
    food_cost_pct = (cost_per_serving / recipe_price * 100) if recipe_price else 0
    margin_pct = 100 - food_cost_pct if recipe_price else 0
    optimal_price_70 = cost_per_serving / 0.30 if cost_per_serving else 0
    total_time = prep_time + cook_time

    # Rating
    if margin_pct >= 70:
        rating, badge_cls = "Excellent", "badge--excellent"
    elif margin_pct >= 60:
        rating, badge_cls = "Good", "badge--good"
    elif margin_pct >= 45:
        rating, badge_cls = "Acceptable", "badge--acceptable"
    else:
        rating, badge_cls = "Needs Improvement", "badge--needs-improvement"

    # Parse ingredients list for the HTML table
    ingredients = _re_parse_ingredients(ingredients_raw)
    ing_names = [i["name"].lower() for i in ingredients]

    # ── AI-generated content ─────────────────────────────────────────────────
    ai = _call_openai_for_recipe(
        recipe_name=recipe_name,
        servings=int(servings),
        prep_time=int(prep_time),
        cook_time=int(cook_time),
        ingredients_raw=ingredients_raw,
        ingredient_cost=ingredient_cost,
        labor_cost=labor_cost,
        recipe_price=recipe_price,
        total_cost=total_cost,
        cost_per_serving=cost_per_serving,
        food_cost_pct=food_cost_pct,
        margin_pct=margin_pct,
    )

    # Fallback to rule-based helpers when AI is unavailable
    if ai:
        method = str(ai.get("method") or "Cooking")
        steps = [str(s) for s in (ai.get("steps") or [])] or _recipe_steps(
            recipe_name, ingredients, method, prep_time, cook_time)
        suggestions = [
            {"name": str(s.get("name") or ""), "reason": str(s.get("reason") or "")}
            for s in (ai.get("suggestions") or [])
            if s.get("name")
        ] or _ingredient_suggestions(recipe_name, ing_names)
        nutrition = {str(k): str(v) for k, v in (ai.get("nutrition") or {}).items()} \
            or _estimate_nutrition(recipe_name, ing_names, servings)
        nutrition_note = str(ai.get("nutrition_note") or "")
        chef_note = str(ai.get("chef_note") or "")
    else:
        rn = recipe_name.lower()
        if any(w in rn for w in ["grill", "bbq", "barbecue"]):
            method = "Grilling"
        elif any(w in rn for w in ["bake", "baked", "roast"]):
            method = "Baking / Roasting"
        elif any(w in rn for w in ["fry", "fried", "sauté", "pan"]):
            method = "Pan-Frying / Sautéing"
        elif any(w in rn for w in ["soup", "bisque", "chowder"]):
            method = "Simmering"
        else:
            method = "Cooking"
        steps = _recipe_steps(recipe_name, ingredients, method, prep_time, cook_time)
        suggestions = _ingredient_suggestions(recipe_name, ing_names)
        nutrition = _estimate_nutrition(recipe_name, ing_names, servings)
        nutrition_note = ""
        chef_note = ""

    now = _dt.now().strftime("%B %d, %Y")

    # ── HTML assembly ────────────────────────────────────────────────────────

    def _row(label, value, highlight=False):
        td_style = "padding:7px 12px;color:#6b7280;font-size:0.875rem;"
        vd_style = f"padding:7px 12px;font-weight:600;{'color:#059669;' if highlight else ''}"
        return f"<tr><td style='{td_style}'>{html.escape(label)}</td><td style='{vd_style}'>{html.escape(str(value))}</td></tr>"

    def _section(icon, title):
        return (
            f'<h3 style="color:#667eea;margin:1.6rem 0 0.7rem;font-size:1.05rem;'
            f'border-bottom:1px solid rgba(102,126,234,0.15);padding-bottom:0.4rem;">'
            f"{icon} {html.escape(title)}</h3>"
        )

    # Ingredients table rows
    ing_rows = ""
    for i, ing in enumerate(ingredients):
        bg = "rgba(102,126,234,0.04)" if i % 2 == 0 else "transparent"
        amt = f"{ing['amount']:.0f} {ing['unit']}" if ing["amount"] else ing["unit"]
        ing_rows += (
            f"<tr style='background:{bg};'>"
            f"<td style='padding:6px 12px;'>{html.escape(ing['name'])}</td>"
            f"<td style='padding:6px 12px;text-align:right;font-weight:600;'>{html.escape(amt)}</td>"
            f"</tr>"
        )

    # Steps
    steps_html = "".join(
        f"<li style='margin-bottom:0.6rem;line-height:1.6;'>{html.escape(s)}</li>"
        for s in steps
    )

    # Suggestions
    sugg_html = "".join(
        f"<li style='margin-bottom:0.5rem;'>"
        f"<strong>{html.escape(s['name'])}</strong> — "
        f"<span style='color:#6b7280;'>{html.escape(s['reason'])}</span></li>"
        for s in suggestions
    )

    # Nutrition table
    nutri_rows = "".join(
        f"<tr><td style='padding:5px 12px;color:#6b7280;font-size:0.875rem;'>{html.escape(k)}</td>"
        f"<td style='padding:5px 12px;font-weight:600;text-align:right;'>{html.escape(v)}</td></tr>"
        for k, v in nutrition.items()
    )

    source_badge = (
        '<span style="font-size:0.7rem;background:linear-gradient(135deg,#667eea,#764ba2);'
        'color:#fff;padding:2px 8px;border-radius:999px;margin-left:8px;vertical-align:middle;">'
        'AI Generated</span>'
        if ai else
        '<span style="font-size:0.7rem;background:#9ca3af;color:#fff;padding:2px 8px;'
        'border-radius:999px;margin-left:8px;vertical-align:middle;">Template</span>'
    )

    parts = [
        '<section class="report">',
        '<header class="report__header">',
        f'<h2>👨‍🍳 {html.escape(recipe_name)}{source_badge}</h2>',
        f'<div class="report__meta">Generated: {now} &nbsp;|&nbsp; Method: {html.escape(method)}'
        f' &nbsp;|&nbsp; Serves: {int(servings)}</div>',
        f'<div class="{badge_cls} badge" style="margin-top:8px;">{rating}</div>',
        '</header>',
        '<article class="report__body">',

        # Lead paragraph
        f'<p class="lead" style="margin:0 0 1rem;color:#374151;line-height:1.7;">'
        f'AI-generated recipe card for <strong>{html.escape(recipe_name)}</strong>. '
        f'Yields <strong>{int(servings)} servings</strong> — total time '
        f'<strong>{int(total_time)} min</strong> ({int(prep_time)} min prep + {int(cook_time)} min cook). '
        f'Profit margin <strong style="color:#059669;">{margin_pct:.1f}%</strong> — '
        f'<strong>{rating}</strong>.</p>',
    ]

    if chef_note:
        parts.append(
            f'<div style="background:linear-gradient(135deg,rgba(102,126,234,0.08),rgba(118,75,162,0.08));'
            f'border-left:3px solid #667eea;border-radius:0 0.5rem 0.5rem 0;padding:10px 14px;margin-bottom:1rem;">'
            f'<span style="font-weight:600;color:#667eea;">Chef\'s Tip:</span> '
            f'{html.escape(chef_note)}</div>'
        )

    # Auto-Costing
    parts += [
        _section("💰", "Auto-Costing Breakdown"),
        '<table style="width:100%;border-collapse:collapse;">',
        _row("Ingredient Cost (total batch)", f"${ingredient_cost:.2f}"),
        _row("Labor Cost", f"${labor_cost:.2f}"),
        _row("Total Batch Cost", f"${total_cost:.2f}"),
        _row("Cost per Serving", f"${cost_per_serving:.2f}"),
        _row("Menu / Sale Price per Serving", f"${recipe_price:.2f}"),
        _row("Food Cost %", f"{food_cost_pct:.1f}%"),
        _row("Profit Margin", f"{margin_pct:.1f}%", highlight=True),
        _row("Optimal Price for 70% Margin", f"${optimal_price_70:.2f}"),
        '</table>',
    ]

    # Ingredients
    parts += [
        _section("🧂", "Ingredients"),
        ('<table style="width:100%;border-collapse:collapse;">'
         '<thead><tr>'
         '<th style="text-align:left;padding:6px 12px;color:#374151;font-size:0.8rem;text-transform:uppercase;'
         'letter-spacing:0.05em;border-bottom:1px solid rgba(102,126,234,0.2);">Ingredient</th>'
         '<th style="text-align:right;padding:6px 12px;color:#374151;font-size:0.8rem;text-transform:uppercase;'
         'letter-spacing:0.05em;border-bottom:1px solid rgba(102,126,234,0.2);">Quantity</th>'
         '</tr></thead><tbody>'),
        ing_rows,
        '</tbody></table>',
    ]

    # Preparation Steps
    parts += [
        _section("📋", "Preparation Steps"),
        f'<ol style="padding-left:1.4rem;margin:0;">{steps_html}</ol>',
    ]

    # Nutrition
    parts += [
        _section("🥗", "Estimated Nutrition (per serving)"),
        '<div style="background:rgba(102,126,234,0.06);border-radius:0.75rem;padding:4px 0 4px;">',
        '<table style="width:100%;border-collapse:collapse;">',
        nutri_rows,
        '</table>',
    ]
    if nutrition_note:
        parts.append(
            f'<p style="font-size:0.8rem;color:#6b7280;padding:4px 12px 6px;font-style:italic;">'
            f'{html.escape(nutrition_note)}</p>'
        )
    parts.append(
        '<p style="font-size:0.75rem;color:#9ca3af;padding:4px 12px 8px;">'
        '* Estimates only. Actual values vary by ingredient brands, preparation methods, and portion sizes.</p>'
    )
    parts.append('</div>')

    # Ingredient Suggestions
    parts += [
        _section("✨", "Suggested Complementary Ingredients"),
        f'<ul style="padding-left:1.25rem;margin:0;">{sugg_html}</ul>',
        '</article>',
        '</section>',
    ]

    return "".join(parts)



def _format_csv_report_html(result: dict) -> str:
    if not isinstance(result, dict):
        return _ensure_html(str(result))
    if result.get("status") == "error":
        msg = html.escape(str(result.get("message") or "Unknown error"))
        parts = [
            '<div class="report">',
            '<div class="report__header" style="background:linear-gradient(135deg,#ef4444,#dc2626);">',
            "<h2>❌ Recipe CSV Error</h2></div>",
            f'<div class="report__body"><p><strong>Error:</strong> {msg}</p>',
        ]
        if result.get("help"):
            parts.append(f'<p><strong>Help:</strong> {html.escape(str(result["help"]))}</p>')
        if result.get("your_columns"):
            cols = ", ".join(html.escape(str(c)) for c in result["your_columns"])
            parts.append(f"<p><strong>Found columns:</strong> {cols}</p>")
        parts += ["</div></div>"]
        return "".join(parts)

    html_report = (
        result.get("business_report_html")
        or result.get("data", {}).get("business_report_html")
        or result.get("business_report")
        or result.get("data", {}).get("business_report")
    )
    return _ensure_html(str(html_report))



@method_decorator(csrf_exempt, name="dispatch")
class RecipeChatAPIView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]
    parser_classes = [JSONParser]

    def post(self, request, *args, **kwargs):
        serializer = RecipeChatRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                _error_payload(code="VALIDATION_ERROR", message="Invalid request.", details=serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )

        message: str = serializer.validated_data["message"]
        language = request.data.get("language", "en")

        if language and language != "en":
            from apps.chat_assistant.translation_utils import translate_prompt_to_english
            message = translate_prompt_to_english(message, language)

        try:
            # ── Strip opening instruction prefix ─────────────────────────────
            body, hint = _strip_prefix(message)

            # ── Extract ingredients block before generic KV parsing ──────────
            ingredients_str, body_no_ing = _extract_ingredients_block(body)

            # ── Extract quoted recipe name ───────────────────────────────────
            recipe_name, body_no_name = _extract_quoted(body_no_ing)

            # ── Parse remaining key-value params ─────────────────────────────
            params = _parse_kv(body_no_name)

            if recipe_name:
                params["recipe_name"] = recipe_name
            if ingredients_str:
                params["ingredients"] = ingredients_str

            # ── Target margin from trailing instruction ───────────────────────
            margin_match = re.search(r"(\d+(?:\.\d+)?)\s*%\s*margin", message, re.IGNORECASE)
            if margin_match and "target_margin" not in params:
                params["target_margin"] = float(margin_match.group(1))

            # ── Detect which card ────────────────────────────────────────────
            subtask = _detect_subtask(message, params, hint)

            if not params and not recipe_name:
                return Response(
                    {"html_response": translate_html_response(
                        _ensure_html(
                            "Please provide recipe details, e.g.:\n"
                            'recipe_name "Grilled Salmon", servings 6, ingredient_cost 18.00, recipe_price 28.00'
                        ),
                        language,
                    )},
                    status=status.HTTP_200_OK,
                )

            # ── Route to backend service ─────────────────────────────────────
            html_response: str

            if subtask == "create_recipe":
                html_response = _generate_create_recipe_html(params)

            elif subtask == "cost_analysis":
                from backend.consulting_services.recipe.costing import run
                result_tuple = run(params)
                is_err, err_msg = _is_error_result(result_tuple)
                if is_err:
                    html_response = _ensure_html(f"Cost analysis error: {err_msg}")
                else:
                    html_response = _ensure_html(_extract_report_html(result_tuple) or "No report generated.")

            else:  # scale_recipe
                current_batch, target_batch = _parse_scale_servings(message)

                # Fall back to params if pattern not found
                if current_batch == 0:
                    current_batch = float(params.get("current_batch") or params.get("servings") or params.get("current_servings") or 0)
                if target_batch == 0:
                    target_batch = float(params.get("target_batch") or params.get("target_servings") or 0)

                if current_batch == 0 or target_batch == 0:
                    html_response = _ensure_html(
                        'Please specify current and target servings, e.g.:\n'
                        '"Scale My Soup which serves 6 to 48 servings."'
                    )
                else:
                    from backend.consulting_services.recipe.analysis_functions import calculate_recipe_scaling_analysis
                    scaling_factor = target_batch / current_batch if current_batch > 0 else 1.0
                    scaling_result = calculate_recipe_scaling_analysis(
                        current_batch=current_batch,
                        target_batch=target_batch,
                        yield_percentage=float(params.get("yield_percentage") or 90.0),
                        consistency_score=float(params.get("consistency_score") or 8.0),
                        base_recipe_cost=float(params.get("base_recipe_cost") or params.get("ingredient_cost") or 0.0),
                        scaling_factor=scaling_factor,
                        quality_threshold=float(params.get("quality_threshold") or 85.0),
                        efficiency_score=float(params.get("efficiency_score") or 8.0),
                    )
                    rhtml = (
                        scaling_result.get("business_report_html")
                        or scaling_result.get("business_report")
                        or ""
                    )
                    html_response = _ensure_html(rhtml or "No scaling report generated.")

            return Response({"html_response": translate_html_response(html_response, language)}, status=status.HTTP_200_OK)

        except Exception as exc:
            trace_id = str(uuid4())
            logger.exception("Recipe chat API error trace_id=%s: %s", trace_id, exc)
            return Response(
                _error_payload(code="INTERNAL_ERROR", message="Server error during recipe analysis.", trace_id=trace_id),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@method_decorator(csrf_exempt, name="dispatch")
class RecipeUploadAPIView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        if "required_csv" not in request.FILES:
            return Response(
                _error_payload(code="VALIDATION_ERROR", message="required_csv file is missing."),
                status=status.HTTP_400_BAD_REQUEST,
            )

        required_csv = request.FILES["required_csv"]
        if not getattr(required_csv, "name", "").lower().endswith(".csv"):
            return Response(
                _error_payload(code="VALIDATION_ERROR", message="required_csv must be a .csv file."),
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            language = request.data.get("language", "en")
            from backend.consulting_services.recipe.analysis_functions import process_recipe_csv_data

            raw_bytes = required_csv.read()

            def _fresh() -> io.BytesIO:
                return io.BytesIO(raw_bytes)

            result = process_recipe_csv_data(_fresh())
            html_response = _format_csv_report_html(result if isinstance(result, dict) else {})
            return Response({"html_response": translate_html_response(_ensure_html(html_response), language)}, status=status.HTTP_200_OK)

        except Exception as exc:
            trace_id = str(uuid4())
            logger.exception("Recipe upload API error trace_id=%s: %s", trace_id, exc)
            return Response(
                _error_payload(code="INTERNAL_ERROR", message="Server error during recipe CSV processing.", trace_id=trace_id),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
