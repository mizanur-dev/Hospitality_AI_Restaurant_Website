"""AI-powered strategic recommendations helpers.

These helpers are intentionally narrow in scope: they generate or refine the
text shown under "Strategic Recommendations" sections across backend reports.

Design goals:
- Keep all numeric calculations deterministic (computed elsewhere).
- Use AI only for narrative prioritization and phrasing.
- Fall back to existing rule-based recommendations if AI is unavailable.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from typing import Any, Dict, List, Optional


_REC_CACHE: dict[str, tuple[float, list[str]]] = {}
_REC_CACHE_MAX_ITEMS = 128


def _extract_json_array(text: str) -> Optional[list]:
    """Best-effort extraction of a JSON array from a model response."""
    if not text:
        return None

    stripped = text.strip()
    if stripped.startswith("[") and stripped.endswith("]"):
        try:
            return json.loads(stripped)
        except Exception:
            return None

    # Try to find the first JSON array block
    m = re.search(r"\[.*\]", stripped, flags=re.DOTALL)
    if not m:
        return None

    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def _normalize_bullets_to_list(text: str) -> List[str]:
    """Fallback parser for non-JSON list outputs."""
    if not text:
        return []

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    out: list[str] = []
    for ln in lines:
        ln = re.sub(r"^[-*•]+\s+", "", ln)
        ln = re.sub(r"^\d+[\.)]\s+", "", ln)
        ln = ln.strip()
        if ln:
            out.append(ln)
    return out


def generate_ai_strategic_recommendations(
    *,
    analysis_type: str,
    metrics: Dict[str, Any],
    performance: Optional[Dict[str, Any]] = None,
    benchmarks: Optional[Dict[str, Any]] = None,
    additional_data: Optional[Dict[str, Any]] = None,
    existing_recommendations: Optional[List[str]] = None,
    max_items: int = 6,
    timeout_s: float | None = None,
    cache_ttl_s: int = 3600,
) -> Optional[List[str]]:
    """Return an AI-generated list of strategic recommendation strings.

    Returns None if AI is not configured/available.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        from openai import OpenAI
    except Exception:
        return None

    model = os.getenv("OPENAI_MODEL", "gpt-4o")

    if timeout_s is None:
        try:
            timeout_s = float(os.getenv("OPENAI_TIMEOUT_S", "4.0"))
        except Exception:
            timeout_s = 4.0

    payload = {
        "analysis_type": analysis_type,
        "metrics": metrics or {},
        "performance": performance or {},
        "benchmarks": benchmarks or {},
        "additional_data": additional_data or {},
        "existing_recommendations": existing_recommendations or [],
        "max_items": int(max(1, min(max_items, 10))),
    }

    # In-process cache to keep repeated uploads/snaps fast.
    # Cache key is based on model + the JSON payload (sorted keys).
    try:
        cache_key_src = json.dumps(
            {"model": model, "payload": payload},
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        cache_key = hashlib.sha256(cache_key_src.encode("utf-8")).hexdigest()
    except Exception:
        cache_key = ""

    if cache_key and cache_ttl_s > 0:
        hit = _REC_CACHE.get(cache_key)
        if hit:
            ts, recs = hit
            if (time.time() - ts) <= cache_ttl_s and recs:
                return recs[: payload["max_items"]]

    system = (
        "You are an expert restaurant operator and strategy consultant. "
        "Generate strategic recommendations based ONLY on the provided JSON input. "
        "Do NOT invent numbers, percentages, dollar amounts, timelines, or results. "
        "If a recommendation would normally require missing data, phrase it without fabricating values. "
        "Output MUST be valid JSON: a single JSON array of strings. "
        "Each string should be 1-2 sentences, action-oriented, and prioritized (highest impact first)."
    )

    user = (
        "Create the strategic recommendations for this report. "
        "Use only the numbers and facts present in the JSON. "
        "Return exactly max_items items (or fewer if max_items is small).\n\n"
        + json.dumps(payload, ensure_ascii=False)
    )

    try:
        client = OpenAI(api_key=api_key)
        used_with_options = False
        if timeout_s is not None:
            # OpenAI python v1 supports request options via with_options().
            try:
                client = client.with_options(timeout=float(timeout_s))
                used_with_options = True
            except Exception:
                pass

        create_kwargs = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
            "max_tokens": 700,
        }
        # Fallback for clients that accept timeout directly.
        if timeout_s is not None and not used_with_options:
            create_kwargs["timeout"] = float(timeout_s)

        try:
            resp = client.chat.completions.create(**create_kwargs)
        except TypeError:
            # Some client versions don't accept `timeout` kwarg.
            create_kwargs.pop("timeout", None)
            resp = client.chat.completions.create(**create_kwargs)
        text = (resp.choices[0].message.content or "").strip()
        arr = _extract_json_array(text)
        if isinstance(arr, list) and all(isinstance(x, str) for x in arr):
            cleaned = [x.strip() for x in arr if x and x.strip()]
            result = cleaned[: payload["max_items"]]
            if cache_key and cache_ttl_s > 0 and result:
                if len(_REC_CACHE) >= _REC_CACHE_MAX_ITEMS:
                    # Drop an arbitrary old item to keep memory bounded.
                    try:
                        _REC_CACHE.pop(next(iter(_REC_CACHE)))
                    except Exception:
                        _REC_CACHE.clear()
                _REC_CACHE[cache_key] = (time.time(), result)
            return result

        # Fallback: parse bullet text
        cleaned = _normalize_bullets_to_list(text)
        result = cleaned[: payload["max_items"]] if cleaned else None
        if cache_key and cache_ttl_s > 0 and result:
            if len(_REC_CACHE) >= _REC_CACHE_MAX_ITEMS:
                try:
                    _REC_CACHE.pop(next(iter(_REC_CACHE)))
                except Exception:
                    _REC_CACHE.clear()
            _REC_CACHE[cache_key] = (time.time(), result)
        return result
    except Exception:
        return None


def refine_recommendation_cards(
    *,
    context: Dict[str, Any],
    cards: List[Dict[str, Any]],
    max_items: int = 6,
) -> Optional[List[Dict[str, Any]]]:
    """AI-refine card-style recommendations (category/priority/action), preserving impact.

    The intent here is to make the recommendations AI-powered while keeping all
    numeric impact strings deterministic and unchanged.

    Returns None if AI is not configured/available.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        from openai import OpenAI
    except Exception:
        return None

    model = os.getenv("OPENAI_MODEL", "gpt-4o")

    safe_cards = []
    for idx, c in enumerate(cards):
        if not isinstance(c, dict):
            continue
        safe_cards.append(
            {
                "index": idx,
                "category": str(c.get("category") or ""),
                "priority": str(c.get("priority") or ""),
                "action": str(c.get("action") or ""),
                "impact": str(c.get("impact") or ""),
            }
        )

    if not safe_cards:
        return None

    payload = {
        "context": context or {},
        "cards": safe_cards[: int(max(1, min(max_items, 12)))],
        "rules": {
            "do_not_change": ["impact"],
            "allowed_priorities": ["Critical", "High", "Medium", "Low", "Maintain"],
        },
    }

    system = (
        "You refine restaurant KPI recommendations. "
        "You MUST keep each card's 'impact' field EXACTLY unchanged. "
        "You may rewrite 'category' and 'action' for clarity and specificity, and adjust 'priority' if needed "
        "(choose from allowed_priorities). "
        "Do NOT invent any numbers or claims. "
        "Output MUST be valid JSON: an array of objects with keys index, category, priority, action, impact."
    )

    user = "Refine these recommendation cards.\n\n" + json.dumps(payload, ensure_ascii=False)

    try:
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
            max_tokens=900,
        )
        text = (resp.choices[0].message.content or "").strip()
        arr = _extract_json_array(text)
        if not isinstance(arr, list):
            return None

        by_index: dict[int, dict[str, Any]] = {}
        for item in arr:
            if not isinstance(item, dict):
                continue
            try:
                idx = int(item.get("index"))
            except Exception:
                continue
            by_index[idx] = item

        refined: list[dict[str, Any]] = []
        for idx, orig in enumerate(cards):
            if idx not in by_index or not isinstance(orig, dict):
                refined.append(orig)
                continue
            new = by_index[idx]
            # Preserve impact exactly
            if str(new.get("impact", "")) != str(orig.get("impact", "")):
                refined.append(orig)
                continue
            merged = dict(orig)
            for key in ("category", "priority", "action"):
                if key in new and isinstance(new[key], str) and new[key].strip():
                    merged[key] = new[key].strip()
            refined.append(merged)

        return refined
    except Exception:
        return None
