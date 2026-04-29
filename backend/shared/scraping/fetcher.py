"""URL fetching for job posting pages.

Uses httpx for async HTTP requests.
"""

import httpx

DEFAULT_TIMEOUT = 30.0
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; HouseHelper/1.0)",
}


async def fetch_url(url: str, timeout: float = DEFAULT_TIMEOUT) -> str:
    """Fetch a URL and return the response body as text.

    Raises httpx.HTTPStatusError on non-2xx responses.
    """
    async with httpx.AsyncClient(
        headers=DEFAULT_HEADERS,
        follow_redirects=True,
        timeout=timeout,
    ) as client:
        response = await client.get(url)
        # #region debug log
        try:
            from shared._dbg import dbg
            history_urls = [str(r.url) for r in response.history]
            dbg(
                "fetcher.py:fetch_url",
                "URL fetch resolved",
                {
                    "requested_url": url,
                    "final_url": str(response.url),
                    "redirect_chain": history_urls,
                    "redirect_count": len(history_urls),
                    "status": response.status_code,
                    "validated_before_fetch": False,
                },
                hyp="H2+H3",
            )
        except Exception:
            pass
        # #endregion
        response.raise_for_status()
        return response.text
