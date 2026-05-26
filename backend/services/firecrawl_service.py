"""
Venture Ferret - Firecrawl Service
Wraps Firecrawl v1 /scrape endpoint with async httpx.
"""
import os
from typing import Optional

import httpx


class FirecrawlService:
    BASE_URL = "https://api.firecrawl.dev/v1"
    MAX_RETRIES = 3
    BACKOFF_BASE = 1.0

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("FIRECRAWL_API_KEY")
        if not self.api_key:
            raise RuntimeError("FIRECRAWL_API_KEY missing")

    async def scrape(self, url: str, wait_ms: int = 2000) -> dict:
        last_err = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
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
                    last_err = RuntimeError(f"Firecrawl error {res.status_code}: {res.text[:300]}")
                    raise last_err

                data = res.json().get("data", {}) or {}
                return {
                    "markdown": data.get("markdown", ""),
                    "metadata": data.get("metadata", {}),
                    "title": (data.get("metadata") or {}).get("title", ""),
                    "source_url": url,
                }

            except (httpx.RequestError, httpx.HTTPStatusError, RuntimeError) as e:
                last_err = e
                if attempt == self.MAX_RETRIES:
                    raise
                # exponential backoff
                await __import__("asyncio").sleep(self.BACKOFF_BASE * (2 ** (attempt - 1)))



_firecrawl: Optional[FirecrawlService] = None


def firecrawl() -> FirecrawlService:
    global _firecrawl
    if _firecrawl is None:
        _firecrawl = FirecrawlService()
    return _firecrawl
