"""
Venture Ferret - Gemini AI Service
Provides embeddings (1536-dim) and structured content extraction.
"""
import os
import asyncio
from typing import Optional

from google import genai
from google.genai import types as gtypes


class GeminiService:
    """Wraps Google Gemini for embeddings + structured content reasoning."""

    EMBED_MODEL = "gemini-embedding-001"
    CHAT_MODEL = "gemini-2.5-flash"
    EMBED_DIM = 1536

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise RuntimeError("GOOGLE_API_KEY missing")
        self.client = genai.Client(api_key=self.api_key)

    async def embed(self, text: str) -> list[float]:
        if not text:
            return [0.0] * self.EMBED_DIM
        # Gemini SDK is sync; offload to thread
        def _run() -> list[float]:
            res = self.client.models.embed_content(
                model=self.EMBED_MODEL,
                contents=text[:8000],  # safety truncate
                config=gtypes.EmbedContentConfig(output_dimensionality=self.EMBED_DIM),
            )
            return list(res.embeddings[0].values)
        return await asyncio.to_thread(_run)

    async def extract_signals(self, markdown: str, query: str) -> list[dict]:
        """Extract structured research signals from scraped markdown."""
        prompt = f"""You are Venture Ferret's signal extraction engine.

Given the scraped web content below, extract 2-5 structured research signals
relevant to this analyst query: "{query}"

Each signal MUST be one of these categories:
- market_signal (industry trends, demand indicators, growth signals)
- technical_dependency (tech stack, frameworks, libraries used)
- competitor_analysis (competing products, pricing, positioning)
- infrastructure (deployment, hosting, scaling, architecture)

Return ONLY a valid JSON array with this exact shape:
[
  {{
    "category": "market_signal" | "technical_dependency" | "competitor_analysis" | "infrastructure",
    "entity_name": "Short distinctive name (3-8 words)",
    "summary": "One sentence finding (max 200 chars)",
    "evidence": "Direct quote or paraphrase from source",
    "confidence": 0.0-1.0
  }}
]

No markdown fences, no commentary, just the JSON array.

SOURCE CONTENT:
{markdown[:6000]}
"""

        def _run() -> str:
            res = self.client.models.generate_content(
                model=self.CHAT_MODEL,
                contents=prompt,
                config=gtypes.GenerateContentConfig(
                    temperature=0.2,
                    response_mime_type="application/json",
                ),
            )
            return res.text or "[]"

        raw = await asyncio.to_thread(_run)
        import json
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "signals" in data:
                return data["signals"]
            return []
        except json.JSONDecodeError:
            return []


_gemini: Optional[GeminiService] = None


def gemini() -> GeminiService:
    global _gemini
    if _gemini is None:
        _gemini = GeminiService()
    return _gemini
