"""Loads settings from environment variables (.env file)."""
import os

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
MONGODB_URI = os.getenv("MONGODB_URI", "").strip()
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "ai_chat_assistant").strip()

# How many previous messages are sent to OpenAI as context
MAX_CONTEXT_MESSAGES = 20
MAX_MESSAGE_LENGTH = 4000


def validate_settings() -> None:
    """Stop the app early with a clear message if something is missing."""
    missing = []
    if not OPENAI_API_KEY or OPENAI_API_KEY.startswith("your-"):
        missing.append("OPENAI_API_KEY")
    if not MONGODB_URI:
        missing.append("MONGODB_URI")
    if missing:
        raise RuntimeError(
            f"Missing environment variable(s): {', '.join(missing)}. "
            "Copy .env.example to .env and fill in the values."
        )
