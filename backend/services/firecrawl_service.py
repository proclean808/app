"""
Venture Ferret - Firecrawl Service
Wraps Firecrawl v1 /scrape endpoint with async httpx.
"""
import os
from typing import Optional

import httpx


class FirecrawlService:
    BASE_URL = "https://api.firecrawl.dev/v1"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("FIRECRAWL_API_KEY")
        if not self.api_key:
            raise RuntimeError("FIRECRAWL_API_KEY missing")

    async def scrape(self, url: str, wait_ms: int = 2000) -> dict:
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(
                f"{self.BASE_URL}/scrape",
                json={
                    "url": url,
                    "formats": ["markdown"],
                    "actions": [{"type": "wait", "milliseconds": wait_ms}],
                },
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
        if res.status_code != 200:
            raise RuntimeError(f"Firecrawl error {res.status_code}: {res.text[:300]}")
        data = res.json().get("data", {}) or {}
        return {
            "markdown": data.get("markdown", ""),
            "metadata": data.get("metadata", {}),
            "title": (data.get("metadata") or {}).get("title", ""),
            "source_url": url,
        }


_firecrawl: Optional[FirecrawlService] = None


def firecrawl() -> FirecrawlService:
    global _firecrawl
    if _firecrawl is None:
        _firecrawl = FirecrawlService()
    return _firecrawl
