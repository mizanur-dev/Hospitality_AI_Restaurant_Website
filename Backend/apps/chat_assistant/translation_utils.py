"""
Utility for translating HTML responses to the requested language.
Used by all domain API views when language != 'en'.
"""
import logging
import os

logger = logging.getLogger(__name__)


def translate_html_response(html_content: str, language: str) -> str:
    """Translate HTML content to the specified language using OpenAI.
    
    If language is 'en' or translation fails, returns the original content unchanged.
    """
    if not html_content or not language or language.lower() == "en":
        return html_content

    try:
        from openai import OpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return html_content

        lang_map = {
            "es": "Spanish (Español)",
        }
        target_lang = lang_map.get(language.lower())
        if not target_lang:
            return html_content

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You are a professional translator. Translate the following HTML content to {target_lang}. "
                        "Keep ALL HTML tags, CSS styles, class attributes, and formatting exactly as-is. "
                        "Only translate the visible text content. Do not add any extra text, explanations, or markdown fences. "
                        "Return ONLY the raw translated HTML. DO NOT wrap the output in ```html codeblocks."
                    ),
                },
                {"role": "user", "content": html_content},
            ],
            temperature=0.3,
            max_tokens=4000,
        )
        translated = response.choices[0].message.content
        if translated and translated.strip():
            return translated
    except Exception as exc:
        logger.warning("Translation to %s failed: %s", language, exc)

    return html_content

def translate_prompt_to_english(prompt: str, language: str) -> str:
    """Translate user prompt to English so legacy systems can parse it.
    
    If language is 'en' or translation fails, returns the original prompt.
    """
    if not prompt or not language or language.lower() == "en":
        return prompt

    try:
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return prompt

        client = OpenAI(api_key=api_key)
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
                {"role": "user", "content": prompt},
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
