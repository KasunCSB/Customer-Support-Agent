"""Simple message lookup for API responses.

Supports short contextual welcome messages.
"""

from __future__ import annotations

from datetime import datetime
import random

_MESSAGES: dict[str, str] = {
    "error.rate_limited": "Too many requests. Please try again later.",
    "error.pipeline_not_ready": "Service is starting up. Please try again in a moment.",
    "error.backend_timeout": "The request timed out. Please try again.",
    "error.speech_not_configured": "Speech service is not configured.",
    "error.tts_failed": "Text-to-speech conversion failed.",
    "memory.cleared": "Conversation memory cleared.",
}


_WELCOME_MORNING: tuple[str, ...] = (
    "Good morning, how can I help today?",
    "Morning! What can I help you with?",
    "Good morning. Need help with something?",
)

_WELCOME_AFTERNOON: tuple[str, ...] = (
    "Good afternoon, what can I do for you?",
    "Afternoon! How can I support you today?",
    "Good afternoon. What are you looking for?",
)

_WELCOME_EVENING: tuple[str, ...] = (
    "Good evening, how can I assist you?",
    "Evening! What can I help you with?",
    "Good evening. What do you need help with?",
)

_WELCOME_NIGHT: tuple[str, ...] = (
    "Hi, need help with billing or data?",
    "Hello, what can I help you resolve?",
    "Hi there. What can I assist with?",
)

_WELCOME_GENERIC: tuple[str, ...] = (
    "Hi! What can I help you with?",
    "Hello, tell me what you need.",
    "Welcome back. How can I assist?",
    "Hi! Ask me about plans, billing, or support.",
    "Hello! What issue can I help solve?",
)


def _welcome_message(now: datetime) -> str:
    hour = now.hour
    if 5 <= hour < 12:
        pool = _WELCOME_MORNING
    elif 12 <= hour < 17:
        pool = _WELCOME_AFTERNOON
    elif 17 <= hour < 22:
        pool = _WELCOME_EVENING
    else:
        pool = _WELCOME_NIGHT

    # Mix in some generic messages so it doesn't feel repetitive.
    combined = pool + _WELCOME_GENERIC
    return random.choice(combined)


def msg(key: str) -> str:
    """Return a message by key, or the key itself if not found."""
    if key == "welcome.message":
        return _welcome_message(datetime.now())
    return _MESSAGES.get(key, key)
