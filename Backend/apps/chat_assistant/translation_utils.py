"""
Utilities for translating response content to the requested language.

The HTML translator preserves the exact markup structure and translates only
visible text nodes in manageable batches so long reports do not get truncated.
"""
from __future__ import annotations

import json
import logging
import os
from html.parser import HTMLParser

logger = logging.getLogger(__name__)

_LANGUAGE_MAP = {
    "es": "Spanish (Español)",
}
_HTML_TRANSLATION_BATCH_SIZE = 20
_HTML_TRANSLATION_CHAR_LIMIT = 6000
_PROMPT_TRANSLATION_CHAR_LIMIT = 4000


def _get_target_language(language: str) -> str | None:
    if not language:
        return None
    return _LANGUAGE_MAP.get(language.lower())


def _create_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    from openai import OpenAI

    return OpenAI(api_key=api_key)


def _translate_text_batch(
    client,
    texts: list[str],
    *,
    target_language: str,
) -> list[str] | None:
    if not texts:
        return []

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a professional translator. "
                        f"Translate each string in the provided JSON array to {target_language}. "
                        "Preserve meaning, numbers, punctuation, whitespace, and line breaks. "
                        "Do not summarize or omit content. "
                        'Return a JSON object with one key: "translations", whose value is an array '
                        "with the same number of translated strings in the same order."
                    ),
                },
                {"role": "user", "content": json.dumps({"texts": texts}, ensure_ascii=False)},
            ],
            temperature=0.2,
            max_tokens=8000,
        )
        content = response.choices[0].message.content or ""
        payload = json.loads(content)
        translations = payload.get("translations")
        if (
            isinstance(translations, list)
            and len(translations) == len(texts)
            and all(isinstance(item, str) for item in translations)
        ):
            return translations
    except Exception as exc:
        logger.warning("Batch translation to %s failed: %s", target_language, exc)

    return None


class _HtmlTranslationParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.tokens: list[tuple[str, str]] = []
        self._raw_text_stack: list[str] = []

    def handle_starttag(self, tag: str, attrs):
        self.tokens.append(("raw", self.get_starttag_text()))
        if tag.lower() in {"script", "style"}:
            self._raw_text_stack.append(tag.lower())

    def handle_startendtag(self, tag: str, attrs):
        self.tokens.append(("raw", self.get_starttag_text()))

    def handle_endtag(self, tag: str):
        self.tokens.append(("raw", f"</{tag}>"))
        if self._raw_text_stack and self._raw_text_stack[-1] == tag.lower():
            self._raw_text_stack.pop()

    def handle_data(self, data: str):
        token_type = "raw" if self._raw_text_stack else "text"
        self.tokens.append((token_type, data))

    def handle_comment(self, data: str):
        self.tokens.append(("raw", f"<!--{data}-->"))

    def handle_decl(self, decl: str):
        self.tokens.append(("raw", f"<!{decl}>"))

    def handle_entityref(self, name: str):
        self.tokens.append(("raw", f"&{name};"))

    def handle_charref(self, name: str):
        self.tokens.append(("raw", f"&#{name};"))


def _translate_html_tokens(tokens: list[tuple[str, str]], *, target_language: str) -> str:
    client = _create_openai_client()
    if client is None:
        return "".join(value for _, value in tokens)

    text_indexes = [
        index
        for index, (token_type, value) in enumerate(tokens)
        if token_type == "text" and value.strip()
    ]
    if not text_indexes:
        return "".join(value for _, value in tokens)

    translated_tokens = list(tokens)
    batch_indexes: list[int] = []
    batch_texts: list[str] = []
    batch_chars = 0

    def flush_batch():
        nonlocal batch_indexes, batch_texts, batch_chars
        if not batch_texts:
            return

        translated = _translate_text_batch(
            client,
            batch_texts,
            target_language=target_language,
        )
        if translated:
            for idx, translated_text in zip(batch_indexes, translated):
                translated_tokens[idx] = ("text", translated_text)

        batch_indexes = []
        batch_texts = []
        batch_chars = 0

    for token_index in text_indexes:
        text_value = tokens[token_index][1]
        projected_chars = batch_chars + len(text_value)
        if batch_texts and (
            len(batch_texts) >= _HTML_TRANSLATION_BATCH_SIZE
            or projected_chars > _HTML_TRANSLATION_CHAR_LIMIT
        ):
            flush_batch()

        batch_indexes.append(token_index)
        batch_texts.append(text_value)
        batch_chars += len(text_value)

    flush_batch()
    return "".join(value for _, value in translated_tokens)


def translate_html_response(html_content: str, language: str) -> str:
    """Translate visible HTML text while preserving the exact markup."""
    if not html_content:
        return html_content

    target_language = _get_target_language(language)
    if not target_language:
        return html_content

    try:
        parser = _HtmlTranslationParser()
        parser.feed(html_content)
        parser.close()
        return _translate_html_tokens(parser.tokens, target_language=target_language)
    except Exception as exc:
        logger.warning("HTML translation to %s failed: %s", language, exc)
        return html_content


def translate_prompt_to_english(prompt: str, language: str) -> str:
    """Translate the user's prompt to English for legacy parsers."""
    if not prompt or not language or language.lower() == "en":
        return prompt

    client = _create_openai_client()
    if client is None:
        return prompt

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a professional translator. Translate the following user message to English. "
                        "Preserve the overall meaning, numerical data, and intent exactly. "
                        "Do NOT answer the prompt or add any explanations, just return the translated text."
                    ),
                },
                {"role": "user", "content": prompt[:_PROMPT_TRANSLATION_CHAR_LIMIT]},
            ],
            temperature=0.3,
            max_tokens=1500,
        )
        translated = response.choices[0].message.content
        if translated and translated.strip():
            return translated
    except Exception as exc:
        logger.warning("Translation of prompt from %s to English failed: %s", language, exc)

    return prompt
