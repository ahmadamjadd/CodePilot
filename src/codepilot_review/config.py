from __future__ import annotations

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Optional

from dotenv import load_dotenv


# Load .env into environment, if present
load_dotenv()


@dataclass
class Settings:
    grok_api_key: str = os.getenv("GROK_API_KEY", "")
    grok_api_base_url: str = os.getenv("GROK_API_BASE_URL", "https://api.x.ai/v1")
    grok_model: Optional[str] = os.getenv("GROK_MODEL") or None
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
