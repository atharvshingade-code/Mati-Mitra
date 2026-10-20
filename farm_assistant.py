
"""MatiMitra: Marathi voice utilities and AI provider fallback."""

import asyncio
import os
import tempfile
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()


def get_setting(name, default=None):
    """Read Streamlit Cloud secrets first, then environment variables."""
    try:
        value = st.secrets.get(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    except Exception:
        pass

    return os.getenv(name, default)


def available_ai_providers():
    """Return providers whose API keys are configured."""
    providers = []

    if get_setting("GEMINI_API_KEY"):
        providers.append("Gemini")

    if get_setting("GROQ_API_KEY"):
        providers.append("Groq")

    return providers


def _is_quota_or_rate_limit_error(exc):
    """Identify common quota and rate-limit errors."""
    status = getattr(exc, "status_code", None)
    code = getattr(exc, "code", None)

    details = (
        f"{type(exc).__name__} {status} {code} {exc}"
    ).lower()

    return (
        status == 429
        or str(code) == "429"
        or "resource_exhausted" in details
        or "rate_limit" in details
        or "rate limit" in details
        or "quota exceeded" in details
        or "too many requests" in details
    )


def _call_gemini(prompt):
    api_key = get_setting("GEMINI_API_KEY")
    model = get_setting("GEMINI_MODEL", "")

    if not api_key or not model:
        raise RuntimeError(
            "Gemini requires GEMINI_API_KEY and GEMINI_MODEL."
        )

    from google import genai
    from google.genai import types

    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=30000,
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config={
            "temperature": 0.3,
            "max_output_tokens": 512,
        },
    )

    answer = (response.text or "").strip()
    if not answer:
        raise RuntimeError("Gemini returned an empty response.")

    return answer, f"Gemini ({model})"


def _call_groq(prompt):
    api_key = get_setting("GROQ_API_KEY")
    model = get_setting("GROQ_CHAT_MODEL", "")

    if not api_key or not model:
        raise RuntimeError(
            "Groq requires GROQ_API_KEY and GROQ_CHAT_MODEL."
        )

    from groq import Groq

    client = Groq(api_key=api_key)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are MatiMitra, a careful farming assistant. "
                    "Answer in simple Marathi unless another language "
                    "is requested. Never invent sensor data or prescribe "
                    "exact fertilizer or pesticide doses without "
                    "validated agronomic evidence."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=512,
    )

    answer = (response.choices[0].message.content or "").strip()
    if not answer:
        raise RuntimeError("Groq returned an empty response.")

    return answer, f"Groq ({model})"


def answer_question(
    question,
    readings,
    profile,
    analysis,
    history=None,
    provider=None,
):
    """Answer a farmer using the preferred provider and quota fallback."""

    selected = (
        provider or get_setting("DEFAULT_AI_PROVIDER", "Gemini")
    ).strip().lower()

    if selected not in ("gemini", "groq"):
        return (
            "कृपया Gemini किंवा Groq यापैकी एक AI provider निवडा.",
            "Configuration error",
        )

    recent_history = (history or [])[-4:]

    prompt = f"""
You are MatiMitra, a farming assistant that communicates in Marathi.

Answer in simple Marathi unless another language is requested.
Be concise, practical, and careful about uncertainty.

SAFETY RULES:
- Identify whether readings are simulated, manually entered,
  or sensor-based.
- Never describe simulated readings as real sensor measurements.
- Do not invent missing farm data.
- Do not prescribe exact fertilizer or pesticide doses based only
  on these readings.
- Explain when laboratory soil testing or qualified agricultural
  advice is needed.
- Treat unusual readings as possible issues to investigate,
  not confirmed diagnoses.

FARM PROFILE:
{profile}

CURRENT SOIL READINGS:
{readings}

SOIL INTERPRETATION AND ALERTS:
{analysis}

RECENT CONVERSATION:
{recent_history}

FARMER'S QUESTION:
{question}
"""

    callers = {
        "gemini": _call_gemini,
        "groq": _call_groq,
    }

    # Try the preferred provider first.
    order = [selected]

    # Only retry with the other provider for quota/rate-limit errors.
    fallback = "groq" if selected == "gemini" else "gemini"

    for provider_name in order:
        try:
            return callers[provider_name](prompt)
        except Exception as exc:
            print(
                f"{provider_name.title()} request failed: "
                f"{type(exc).__name__}; "
                f"status={getattr(exc, 'status_code', None)}"
            )

            if not _is_quota_or_rate_limit_error(exc):
                return (
                    "AI सेवा सध्या उपलब्ध नाही. मॉडेलचे नाव, API key, "
                    "इंटरनेट कनेक्शन आणि API quota तपासा.",
                    f"AI error: {type(exc).__name__}",
                )

            if fallback not in available_ai_providers():
                return (
                    "निवडलेल्या AI मॉडेलची मर्यादा संपली आहे आणि "
                    "दुसरा provider कॉन्फिगर केलेला नाही. कृपया "
                    "दुसरी API key किंवा उपलब्ध मॉडेल वापरा.",
                    "Rate limit; no fallback provider",
                )

            try:
                answer, mode = callers[fallback](prompt)
                return answer, f"{mode} (automatic fallback)"
            except Exception as fallback_exc:
                print(
                    f"{fallback.title()} fallback failed: "
                    f"{type(fallback_exc).__name__}; "
                    f"status={getattr(fallback_exc, 'status_code', None)}"
                )
                return (
                    "दोन्ही AI सेवांकडून उत्तर मिळाले नाही. API quota, "
                    "मॉडेलचे नाव आणि सेवा उपलब्धता तपासा.",
                    f"Fallback error: {type(fallback_exc).__name__}",
                )

    return (
        "AI सेवा सध्या उपलब्ध नाही. कृपया पुन्हा प्रयत्न करा.",
        "AI error",
    )


def transcribe_marathi_audio(audio_bytes, filename="question.wav"):
    """Transcribe audio using Groq Whisper."""

    api_key = get_setting("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured.")

    if not audio_bytes:
        raise ValueError("रेकॉर्डिंग रिकामे आहे. कृपया पुन्हा बोला.")

    from groq import Groq

    client = Groq(api_key=api_key)
    result = client.audio.transcriptions.create(
        file=(filename, audio_bytes),
        model=get_setting("GROQ_STT_MODEL", "whisper-large-v3"),
        language="mr",
        response_format="text",
    )

    transcript = str(result).strip()

    if not transcript:
        raise ValueError(
            "आवाजातून मजकूर समजला नाही. कृपया स्पष्टपणे पुन्हा बोला."
        )

    return transcript


def speak_marathi(text, voice=None):
    """Generate Marathi speech and return MP3 bytes."""

    import edge_tts

    selected_voice = voice or get_setting(
        "MARATHI_TTS_VOICE",
        "mr-IN-AarohiNeural",
    )

    async def generate():
        with tempfile.NamedTemporaryFile(
            suffix=".mp3", delete=False
        ) as file:
            output_path = Path(file.name)

        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice=selected_voice,
            )
            await communicate.save(str(output_path))
            return output_path.read_bytes()
        finally:
            output_path.unlink(missing_ok=True)

    return asyncio.run(generate())
