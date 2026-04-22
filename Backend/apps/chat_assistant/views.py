from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

from .openai_utils import chat_with_gpt


def chat_ui(request):
    return render(request, "chat_assistant/chat_ui.html")


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def chat_api(request):
    if request.method == "OPTIONS":
        response = JsonResponse({})
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response

    def _extract_message_and_context():
        raw_body = request.body or b""
        content_type = (request.content_type or "").lower()

        body_obj = None
        if raw_body.strip():
            # Try JSON first whenever a body exists (even if Content-Type is wrong).
            if "application/json" in content_type or raw_body.lstrip().startswith((b"{", b"[", b'\"')):
                try:
                    body_obj = json.loads(raw_body)
                except (json.JSONDecodeError, ValueError):
                    body_obj = None

        # Also accept form posts.
        if body_obj is None:
            if request.POST:
                body_obj = request.POST

        def _coerce_text(value):
            if value is None:
                return ""
            if isinstance(value, str):
                return value
            # Common payload shape: {message: {text: "..."}}
            if isinstance(value, dict):
                for k in ("text", "content", "message", "prompt"):
                    if k in value:
                        return _coerce_text(value.get(k))
                return json.dumps(value)
            # Common payload shape: {messages: [{role: "user", content: "..."}, ...]}
            if isinstance(value, list):
                # try to find last user message
                for item in reversed(value):
                    if isinstance(item, dict) and item.get("role") == "user":
                        return _coerce_text(item.get("content") or item.get("text"))
                return ""
            return str(value)

        user_text = ""
        context_val = None
        if isinstance(body_obj, dict):
            # Prefer explicit message keys
            for key in ("message", "prompt", "text", "query"):
                if key in body_obj:
                    user_text = _coerce_text(body_obj.get(key))
                    break
            if not user_text and "messages" in body_obj:
                user_text = _coerce_text(body_obj.get("messages"))
            context_val = body_obj.get("context", None)
            lang_val = body_obj.get("language", "en")
        elif isinstance(body_obj, str):
            user_text = body_obj
        else:
            # Fall back to form-data keys (QueryDict behaves like a dict).
            try:
                user_text = request.POST.get("message", "")
                context_val = request.POST.get("context", None)
                lang_val = request.POST.get("language", "en")
            except Exception:
                user_text = ""
                context_val = None

        return (user_text or ""), context_val, lang_val

    user_input, context, language = _extract_message_and_context()
    if not isinstance(user_input, str):
        user_input = str(user_input)
    if not user_input.strip():
        return JsonResponse(
            {"error": "Message is required", "detail": "Expected a non-empty string in JSON key 'message' (or 'prompt'/'text'/'query')."},
            status=400,
        )

    history = request.session.get("chat_history", [])
    if not isinstance(history, list):
        history = []

    response = chat_with_gpt(user_input, context, history=history, language=language)

    if isinstance(user_input, str) and user_input.strip():
        history.append({"role": "user", "content": user_input.strip()})
    if isinstance(response, str) and response.strip():
        history.append({"role": "assistant", "content": response.strip()})
    history = history[-20:]
    request.session["chat_history"] = history

    return JsonResponse({"response": response})
