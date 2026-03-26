"""
Wikipedia pageview data fetcher.

Uses the Wikimedia REST API to download daily page-view counts for
any English Wikipedia article.  No API key is required.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

import pandas as pd


_BASE_URL = (
    "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"
    "/{project}/all-access/all-agents/{article}/daily/{start}/{end}"
)

_HEADERS = {
    "User-Agent": (
        "seasonal-spirals/0.1 "
        "(https://github.com/; python package demo)"
    )
}

# Wikimedia allows at most ~2 years per request; chunk if needed.
_MAX_DAYS_PER_REQUEST = 730


def fetch_pageviews(
    article: str,
    start: str,
    end: str,
    project: str = "en.wikipedia",
    retry: int = 3,
    retry_delay: float = 2.0,
) -> pd.Series:
    """
    Fetch daily Wikipedia page views for a single article.

    Parameters
    ----------
    article : str
        Article title as it appears in the URL (spaces as underscores,
        e.g. ``"Game_of_Thrones"``).  The function will URL-encode the
        title automatically, so plain spaces are also accepted.
    start : str
        Start date, inclusive, in ``"YYYY-MM-DD"`` or ``"YYYYMMDD"``
        format.
    end : str
        End date, inclusive, in ``"YYYY-MM-DD"`` or ``"YYYYMMDD"``
        format.
    project : str, optional
        Wikimedia project identifier. Default ``"en.wikipedia"``.
    retry : int, optional
        Number of retry attempts on HTTP errors. Default ``3``.
    retry_delay : float, optional
        Seconds to wait between retries. Default ``2.0``.

    Returns
    -------
    pd.Series
        Daily view counts with a DatetimeIndex, named after *article*.

    Raises
    ------
    urllib.error.HTTPError
        If the API returns an error that persists after all retries.

    Examples
    --------
    >>> from seasonal_spirals.wikipedia import fetch_pageviews
    >>> data = fetch_pageviews("Influenza", "2015-01-01", "2022-12-31")
    >>> data.head()
    """
    # Normalise date strings to YYYYMMDD
    start_dt = pd.Timestamp(start)
    end_dt = pd.Timestamp(end)

    # Encode article title (spaces → underscores, then URL-encode)
    encoded = urllib.parse.quote(article.replace(" ", "_"), safe="")

    all_records: list[tuple[str, int]] = []

    # Chunk the request into ≤ _MAX_DAYS_PER_REQUEST windows
    chunk_start = start_dt
    while chunk_start <= end_dt:
        chunk_end = min(
            chunk_start + pd.Timedelta(days=_MAX_DAYS_PER_REQUEST - 1), end_dt
        )
        url = _BASE_URL.format(
            project=project,
            article=encoded,
            start=chunk_start.strftime("%Y%m%d") + "00",
            end=chunk_end.strftime("%Y%m%d") + "00",
        )

        data = _get_json(url, retry=retry, delay=retry_delay)
        for item in data.get("items", []):
            all_records.append((item["timestamp"][:8], int(item["views"])))

        chunk_start = chunk_end + pd.Timedelta(days=1)

    if not all_records:
        return pd.Series([], dtype=float, name=article)

    dates = pd.to_datetime([r[0] for r in all_records], format="%Y%m%d")
    views = [r[1] for r in all_records]
    series = pd.Series(views, index=dates, name=article, dtype=float)
    return series.sort_index()


def fetch_multiple(
    articles: list[str],
    start: str,
    end: str,
    project: str = "en.wikipedia",
    retry: int = 3,
    retry_delay: float = 2.0,
) -> dict[str, pd.Series]:
    """
    Fetch daily Wikipedia page views for multiple articles.

    Parameters
    ----------
    articles : list of str
        Article titles (see :func:`fetch_pageviews` for formatting).
    start, end : str
        Date range (inclusive) in ``"YYYY-MM-DD"`` or ``"YYYYMMDD"``.
    project : str, optional
        Wikimedia project. Default ``"en.wikipedia"``.
    retry, retry_delay
        Passed through to :func:`fetch_pageviews`.

    Returns
    -------
    dict mapping article title → pd.Series
    """
    result: dict[str, pd.Series] = {}
    for article in articles:
        result[article] = fetch_pageviews(
            article,
            start=start,
            end=end,
            project=project,
            retry=retry,
            retry_delay=retry_delay,
        )
        # Be polite to the API
        time.sleep(0.3)
    return result


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _get_json(url: str, retry: int, delay: float) -> dict:
    req = urllib.request.Request(url, headers=_HEADERS)
    last_err: Optional[Exception] = None
    for attempt in range(retry):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                # Article not found  - return empty rather than retrying
                return {}
            last_err = exc
        except Exception as exc:  # noqa: BLE001
            last_err = exc
        if attempt < retry - 1:
            time.sleep(delay)
    raise RuntimeError(f"Failed to fetch {url}") from last_err
