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

from .serializers import BeverageChatRequestSerializer
from apps.chat_assistant.translation_utils import translate_html_response

logger = logging.getLogger(__name__)


PERCENT_KEYS = {"target_cost_percentage", "target_margin"}


def _error_payload(*, code: str, message: str, details=None, trace_id: str | None = None):
    payload = {"error": {"code": code, "message": message}}
    if details is not None:
        payload["error"]["details"] = details
    if trace_id:
        payload["error"]["trace_id"] = trace_id
    return payload


def _ensure_html(text_or_html: str) -> str:
    # keep behavior consistent with other apps; avoid monospace <pre>.
    if not isinstance(text_or_html, str):
        text_or_html = str(text_or_html)
    candidate = text_or_html.strip()
    if not candidate:
        return "<div>No analysis returned.</div>"
    if "<" in candidate and ">" in candidate:
        return candidate
    return f'<div style="font-family:inherit; white-space:pre-wrap">{html.escape(candidate)}</div>'


def _snake_key(key: str) -> str:
    key = key.strip().lower()
    key = re.sub(r"[^a-z0-9_\s]", "", key)
    key = re.sub(r"\s+", "_", key)
    key = re.sub(r"_+", "_", key)
    return key.strip("_")


def _coerce_scalar(value: str):
    raw = value.strip()
    if not raw:
        return ""

    # Trim common trailing punctuation from free-form prompts.
    raw = raw.rstrip(".;")

    lowered = raw.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"

    numeric_candidate = raw.replace(",", "")
    numeric_candidate = re.sub(r"^\$", "", numeric_candidate)
    numeric_candidate = numeric_candidate.replace("$", "")
    numeric_candidate = numeric_candidate.replace("%", "")

    try:
        if re.fullmatch(r"-?\d+", numeric_candidate):
            return int(numeric_candidate)
        if re.fullmatch(r"-?\d*\.\d+", numeric_candidate) or re.fullmatch(
            r"-?\d+\.\d+", numeric_candidate
        ):
            return float(numeric_candidate)
    except Exception:
        pass

    return raw


def _strip_topic_prefix(message: str) -> str:
    candidate = message.strip()
    if not candidate:
        return candidate

    # Common dashboard-style prompt prefixes like:
    # "Liquor Cost Analysis:\nExpected oz: ..."
    first_line, *rest = candidate.splitlines()
    if ":" in first_line:
        prefix = first_line.split(":", 1)[0].strip().lower()
        if any(
            p in prefix
            for p in [
                "liquor cost analysis",
                "bar inventory analysis",
                "bar inventory",
                "beverage pricing analysis",
                "beverage pricing",
            ]
        ):
            return "\n".join(rest).strip()

    # Also handle single-line inputs starting with a title prefix:
    # "Liquor Cost Analysis: Expected oz: ..."
    title_match = re.match(
        r"^(liquor\s+cost\s+analysis|bar\s+inventory\s+analysis|bar\s+inventory|beverage\s+pricing\s+analysis|beverage\s+pricing)\s*:\s*(.*)$",
        candidate,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if title_match:
        return (title_match.group(2) or "").strip()

    return candidate


def _parse_kv_message(message: str) -> dict:
    candidate = _strip_topic_prefix(message)
    params: dict = {}

    for match in re.finditer(
        r"(?P<key>[A-Za-z_][A-Za-z0-9_ ]*?)\s*:\s*(?P<value>[^,\n]+)",
        candidate,
    ):
        key = _snake_key(match.group("key"))
        value = _coerce_scalar(match.group("value"))
        if key:
            params[key] = value

    # Convert ratio values (0-1) into percent (0-100) for known percent keys.
    for key in list(params.keys()):
        if key not in PERCENT_KEYS:
            continue
        val = params.get(key)
        if isinstance(val, (int, float)) and 0 <= float(val) <= 1:
            params[key] = float(val) * 100

    return params


def _detect_subtask(message: str, params: dict) -> str:
    msg = message.lower()
    if "liquor cost" in msg or any(k in params for k in ["expected_oz", "actual_oz", "liquor_cost", "total_sales"]):
        return "liquor_cost"
    if "inventory" in msg or any(
        k in params for k in ["current_stock", "reorder_point", "monthly_usage", "inventory_value"]
    ):
        return "inventory"
    if "pricing" in msg or any(
        k in params for k in ["drink_price", "cost_per_drink", "sales_volume", "competitor_price"]
    ):
        return "pricing"
    return "liquor_cost"


def _format_beverage_csv_report_html(result: dict) -> str:
    if not isinstance(result, dict):
        return _ensure_html(str(result))

    if result.get("status") == "error":
        message = html.escape(str(result.get("message") or "Unknown error"))
        help_text = result.get("help")
        your_columns = result.get("your_columns")

        parts = [
            '<div class="report">',
            '<div class="report__header" style="background: linear-gradient(135deg, #ef4444, #dc2626);">',
            "<h2>❌ Beverage CSV Analysis Error</h2>",
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
class BeverageChatAPIView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]
    parser_classes = [JSONParser]

    def post(self, request, *args, **kwargs):
        serializer = BeverageChatRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                _error_payload(
                    code="VALIDATION_ERROR",
                    message="Invalid request body.",
                    details=serializer.errors,
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        message: str = serializer.validated_data["message"]
        language = request.data.get("language", "en")

        if language and language != "en":
            from apps.chat_assistant.translation_utils import translate_prompt_to_english
            message = translate_prompt_to_english(message, language)

        try:
            params = _parse_kv_message(message)
            subtask = _detect_subtask(message, params)

            if not params:
                return Response(
                    {
                        "html_response": translate_html_response(
                            _ensure_html(
                                "Provide beverage inputs as key:value pairs. Example: expected_oz: 1500, actual_oz: 1650"
                            ),
                            language,
                        )
                    },
                    status=status.HTTP_200_OK,
                )

            if subtask == "liquor_cost":
                from backend.consulting_services.beverage.liquor_cost import run as run_liquor

                result, code = run_liquor(params)
            elif subtask == "inventory":
                from backend.consulting_services.beverage.inventory import run as run_inventory

                result, code = run_inventory(params)
            else:
                from backend.consulting_services.beverage.pricing import run as run_pricing

                result, code = run_pricing(params)

            if isinstance(result, dict) and result.get("status") == "success":
                data = result.get("data", {}) if isinstance(result.get("data"), dict) else {}
                html_response = data.get("business_report_html") or data.get("business_report")
                return Response(
                    {"html_response": translate_html_response(_ensure_html(str(html_response)), language)},
                    status=status.HTTP_200_OK,
                )

            error_message = result.get("error") if isinstance(result, dict) else "Beverage analysis failed."
            return Response(
                _error_payload(
                    code="ANALYSIS_ERROR",
                    message=str(error_message or "Beverage analysis failed."),
                    details={"subtask": subtask},
                ),
                status=code if isinstance(code, int) else status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            trace_id = str(uuid4())
            logger.exception("Beverage chat API failed trace_id=%s: %s", trace_id, exc)
            return Response(
                _error_payload(
                    code="INTERNAL_ERROR",
                    message="Server error while generating beverage analysis.",
                    trace_id=trace_id,
                ),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@method_decorator(csrf_exempt, name="dispatch")
class BeverageUploadAPIView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        # Validate file upload (don't use ChoiceField for analysis_type — read it raw
        # from request.data to avoid silent validation drops in multipart forms).
        if "required_csv" not in request.FILES:
            return Response(
                _error_payload(
                    code="VALIDATION_ERROR",
                    message="required_csv file is missing from the upload.",
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        required_csv = request.FILES["required_csv"]
        file_name = getattr(required_csv, "name", "") or ""
        if not file_name.lower().endswith(".csv"):
            return Response(
                _error_payload(
                    code="VALIDATION_ERROR",
                    message="required_csv must be a .csv file.",
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Explicit analysis_type hint from the frontend (can be "auto" or absent).
        analysis_type = (request.data.get("analysis_type") or "").strip() or None
        if analysis_type in {"auto", ""}:
            analysis_type = None
        
        language = request.data.get("language", "en")

        try:
            from backend.consulting_services.beverage.bar_inventory_csv_processor import (
                process_bar_inventory_csv_data,
            )
            from backend.consulting_services.beverage.beverage_pricing_csv_processor import (
                process_beverage_pricing_csv_data,
            )
            from backend.consulting_services.beverage.liquor_cost_csv_processor import (
                process_liquor_cost_csv_data,
            )

            # --- Read raw bytes ONCE so each processor gets a fresh stream ---
            raw_bytes = required_csv.read()

            def _fresh() -> io.BytesIO:
                """Return a fresh BytesIO stream from the uploaded file bytes."""
                return io.BytesIO(raw_bytes)

            def _sniff_columns(data: bytes) -> set[str]:
                """Return the lowercase column names from the CSV header row."""
                try:
                    import csv
                    reader = csv.reader(io.StringIO(data.decode("utf-8", errors="replace")))
                    header = next(reader, [])
                    return {c.strip().lower() for c in header if c.strip()}
                except Exception:
                    return set()

            columns = _sniff_columns(raw_bytes)

            # --- Keyword sets for each analysis type ---
            LIQUOR_COLS = {"expected_oz", "actual_oz", "liquor_cost", "total_sales"}
            INVENTORY_COLS = {"current_stock", "reorder_point", "monthly_usage", "inventory_value"}
            PRICING_COLS = {"drink_price", "cost_per_drink", "sales_volume", "competitor_price"}

            # Map normalised column names (strip spaces/underscores) for fuzzy matching.
            def _normalise(s: str) -> str:
                return re.sub(r"[\s_-]+", "", s.lower())

            normalised_cols = {_normalise(c) for c in columns}

            def _any_match(target_set: set[str]) -> bool:
                return any(_normalise(t) in normalised_cols for t in target_set)

            def _detect_analysis_type() -> str | None:
                if _any_match(LIQUOR_COLS):
                    return "liquor_cost_analysis"
                if _any_match(INVENTORY_COLS):
                    return "bar_inventory_analysis"
                if _any_match(PRICING_COLS):
                    return "beverage_pricing_analysis"
                return None

            detected_type = _detect_analysis_type()

            processors_by_type = {
                "liquor_cost_analysis": process_liquor_cost_csv_data,
                "bar_inventory_analysis": process_bar_inventory_csv_data,
                "beverage_pricing_analysis": process_beverage_pricing_csv_data,
            }

            result: dict | None = None

            # Treat analysis_type as a *hint*. If the frontend sends an incorrect
            # analysis_type (or the user uploads a different CSV than the selected card),
            # fall back to schema detection rather than failing with a misleading error.
            attempted: list[str] = []
            candidate_types: list[str] = []

            if analysis_type in processors_by_type:
                candidate_types.append(str(analysis_type))
            if detected_type and detected_type not in candidate_types:
                candidate_types.append(detected_type)

            # Default fallback order (kept stable for deterministic behavior).
            for t in ["liquor_cost_analysis", "bar_inventory_analysis", "beverage_pricing_analysis"]:
                if t not in candidate_types:
                    candidate_types.append(t)

            first_error: dict | None = None
            for t in candidate_types:
                fn = processors_by_type.get(t)
                if not fn:
                    continue
                attempted.append(t)
                attempt = fn(_fresh())
                if isinstance(attempt, dict) and attempt.get("status") == "success":
                    result = attempt
                    break

                if first_error is None and isinstance(attempt, dict):
                    first_error = attempt

                # If this looks like a schema mismatch, keep trying other processors.
                msg = (attempt or {}).get("message") if isinstance(attempt, dict) else ""
                if isinstance(msg, str) and "Missing required columns" in msg:
                    continue

            if result is None:
                if first_error is not None:
                    # Preserve the most specific error, but add context.
                    first_error = dict(first_error)
                    details = first_error.get("details") if isinstance(first_error.get("details"), dict) else {}
                    details.update(
                        {
                            "attempted_analysis_types": attempted,
                            "detected_analysis_type": detected_type,
                        }
                    )
                    first_error["details"] = details
                    result = first_error
                else:
                    # No processor succeeded — build a helpful combined error.
                    col_list = sorted(columns) or ["(none detected)"]
                    result = {
                        "status": "error",
                        "message": "CSV columns did not match any known beverage analysis type.",
                        "your_columns": col_list,
                        "help": (
                            "Liquor Cost needs: expected_oz, actual_oz, liquor_cost, total_sales. "
                            "Bar Inventory needs: current_stock, reorder_point, monthly_usage, inventory_value. "
                            "Beverage Pricing needs: drink_price, cost_per_drink, sales_volume, competitor_price."
                        ),
                    }

            html_response = _format_beverage_csv_report_html(result or {})
            return Response(
                {"html_response": translate_html_response(_ensure_html(str(html_response)), language)},
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            trace_id = str(uuid4())
            logger.exception("Beverage upload API failed trace_id=%s: %s", trace_id, exc)
            return Response(
                _error_payload(
                    code="INTERNAL_ERROR",
                    message="Server error while processing beverage CSV upload.",
                    trace_id=trace_id,
                ),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
