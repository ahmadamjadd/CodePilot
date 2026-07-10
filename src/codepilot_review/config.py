from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Optional

from dotenv import load_dotenv


# Load .env into environment, if present
load_dotenv()


@dataclass
class Settings:
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_api_base_url: str = os.getenv("GROQ_API_BASE_URL", "https://api.groq.com/openai/v1")
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    def __post_init__(self) -> None:
        # If model is empty (e.g., GROQ_MODEL= in .env), fallback to a reliable default Groq model
        if not self.groq_model.strip():
            self.groq_model = "llama-3.3-70b-versatile"


settings = Settings()

