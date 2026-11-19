"""Everything related to talking to OpenAI."""
import openai
from openai import AsyncOpenAI

import config

client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)

# The tone is passed to OpenAI as a system instruction.
TONE_INSTRUCTIONS = {
    "professional": (
        "You are a helpful AI assistant. Respond in a professional, polished and "
        "well-structured tone. Be accurate, formal and clear."
    ),
    "casual": (
        "You are a helpful AI assistant. Respond in a casual, friendly and "
        "conversational tone, like chatting with a friend. Keep it relaxed and warm."
    ),
    "concise": (
        "You are a helpful AI assistant. Respond as briefly as possible. Give only "
        "the essential information in a few short sentences, with no filler."
    ),
}


def build_messages(history: list[dict], tone: str) -> list[dict]:
    """System instruction first, then the recent conversation."""
    messages = [{"role": "system", "content": TONE_INSTRUCTIONS[tone]}]
    for item in history[-config.MAX_CONTEXT_MESSAGES:]:
        messages.append({"role": item["role"], "content": item["content"]})
    return messages


async def create_stream(history: list[dict], tone: str):
    """Start a streaming completion. Raises OpenAI errors if it fails to start."""
    return await client.chat.completions.create(
        model=config.OPENAI_MODEL,
        messages=build_messages(history, tone),
        stream=True,
    )


def describe_error(exc: Exception) -> tuple[int, str]:
    """Turn an OpenAI exception into (HTTP status, friendly message)."""
    if isinstance(exc, openai.AuthenticationError):
        return 401, "Invalid OpenAI API key. Check OPENAI_API_KEY in your .env file."
    if isinstance(exc, openai.RateLimitError):
        return 429, "OpenAI rate limit or quota reached. Check your OpenAI billing and try again."
    if isinstance(exc, openai.NotFoundError):
        return 404, f"Model '{config.OPENAI_MODEL}' was not found. Check OPENAI_MODEL in your .env file."
    if isinstance(exc, openai.APIConnectionError):
        return 503, "Could not reach OpenAI. Check your internet connection."
    if isinstance(exc, openai.APIStatusError):
        return 502, "OpenAI returned an error. Please try again."
    return 500, "Something went wrong while generating the response."
