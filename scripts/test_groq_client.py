"""Simple test runner for the Groq client.

This script attempts a live request only if `GROQ_API_KEY` is set in `.env`.
It is safe to run without credentials; it will skip the live call and exit 0.
"""
from __future__ import annotations

import json
from codepilot_review.config import settings
from codepilot_review.llm.groq_client import GroqClient


def main() -> None:
    if not settings.groq_api_key:
        print("GROQ API key not set in .env; skipping live Groq request.")
        return

    client = GroqClient()
    try:
        response = client.generate("Write a one-sentence friendly greeting.")
        print(json.dumps(response, indent=2))
    except Exception as exc:
        # If an HTTP error occurred, try to show the response content.
        import traceback

        print("Request failed:")
        traceback.print_exc()


if __name__ == "__main__":
    main()
