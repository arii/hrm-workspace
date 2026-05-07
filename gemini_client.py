#!/usr/bin/env python3
"""
Gemini API client.
Extracts Gemini API interaction logic.
"""

import json
import os
import requests
from typing import Optional, Dict, Any, List

from common_config import setup_logging

logger = setup_logging("gemini_client")


class GeminiClient:
    """Client for interacting with the Gemini API."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.0-flash-lite-preview-02-05"):
        self.api_key = api_key or os.environ.get("GEMINI_KEY")
        self.model = model
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

        if not self.api_key:
            logger.warning("No GEMINI_KEY provided. Gemini API calls will fail.")

    def generate_content(self, prompt: str, response_mime_type: str = "text/plain") -> Optional[str]:
        """Generate content from a prompt."""
        if not self.api_key:
            logger.error("GEMINI_KEY is missing. Cannot generate content.")
            return None

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": response_mime_type}
        }

        try:
            response = requests.post(
                f"{self.url}?key={self.api_key}",
                json=payload,
                timeout=60
            )
            response.raise_for_status()

            result = response.json()
            if "candidates" in result and result["candidates"]:
                return result["candidates"][0]["content"]["parts"][0]["text"]

            logger.warning("Gemini API returned no candidates.")
            return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Gemini API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error calling Gemini API: {e}")
            return None
