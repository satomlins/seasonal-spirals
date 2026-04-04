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
    "/{project}/all-access/{agent}/{article}/daily/{start}/{end}"
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
    end: Optional[str] = None,
    project: str = "en.wikipedia",
    agent: str = "user",
    retry: int = 3,
    retry_delay: float = 2.0,
    resolve_title: bool = True,
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
    end : str, optional
        End date, inclusive, in ``"YYYY-MM-DD"`` or ``"YYYYMMDD"``
        format.  Defaults to today.
    project : str, optional
        Wikimedia project identifier. Default ``"en.wikipedia"``.
    agent : str, optional
        Agent filter passed to the pageviews API.  ``"user"`` (default)
        returns only human traffic, excluding bots and web scrapers.
        Other valid values are ``"spider"``, ``"automated"``, and
        ``"all-agents"`` (human + bot + spider combined).
    retry : int, optional
        Number of retry attempts on HTTP errors. Default ``3``.
    retry_delay : float, optional
        Seconds to wait between retries. Default ``2.0``.
    resolve_title : bool, optional
        If ``True`` (default), resolve *article* to its canonical
        Wikipedia title via the MediaWiki API before fetching data.
        This handles redirects (e.g. ``"Covid"`` → ``"COVID-19"``) and
        case normalisation.  The returned Series is named after the
        resolved title.  Set to ``False`` to skip the extra API call.

    Returns
    -------
    pd.Series
        Daily view counts with a DatetimeIndex, named after the
        (resolved) article title.

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
    # Resolve to canonical title (follows redirects, normalises case)
    if resolve_title:
        article = _resolve_title(article, project, retry=retry, delay=retry_delay)

    # Normalise date strings to YYYYMMDD
    start_dt = pd.Timestamp(start)
    end_dt = pd.Timestamp(end) if end is not None else pd.Timestamp.today().normalize()

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
            agent=agent,
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
    end: Optional[str] = None,
    project: str = "en.wikipedia",
    agent: str = "user",
    retry: int = 3,
    retry_delay: float = 2.0,
    resolve_title: bool = True,
) -> dict[str, pd.Series]:
    """
    Fetch daily Wikipedia page views for multiple articles.

    Parameters
    ----------
    articles : list of str
        Article titles (see :func:`fetch_pageviews` for formatting).
    start : str
        Start date (inclusive) in ``"YYYY-MM-DD"`` or ``"YYYYMMDD"``.
    end : str, optional
        End date (inclusive). Defaults to today.
    project : str, optional
        Wikimedia project. Default ``"en.wikipedia"``.
    agent : str, optional
        Agent filter (``"user"`` by default — human traffic only).
        See :func:`fetch_pageviews` for all valid values.
    retry, retry_delay
        Passed through to :func:`fetch_pageviews`.
    resolve_title : bool, optional
        Passed through to :func:`fetch_pageviews`.

    Returns
    -------
    dict mapping article title → pd.Series
        Keys are the *input* titles (not the resolved canonical titles),
        so callers can look up results by the name they supplied.
    """
    result: dict[str, pd.Series] = {}
    for article in articles:
        result[article] = fetch_pageviews(
            article,
            start=start,
            end=end,
            project=project,
            agent=agent,
            retry=retry,
            retry_delay=retry_delay,
            resolve_title=resolve_title,
        )
        # Be polite to the API
        time.sleep(0.3)
    return result


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _resolve_title(article: str, project: str, retry: int, delay: float) -> str:
    """Return the canonical Wikipedia title for *article*.

    Uses the MediaWiki ``action=query`` API with ``redirects=1`` to
    follow redirects and normalise capitalisation in one round-trip.
    Returns *article* unchanged if the lookup fails or the article is
    not found (the pageviews call will then 404 gracefully).

    Parameters
    ----------
    article:
        Raw article name supplied by the caller (may be a redirect,
        mis-capitalised, or contain spaces).
    project:
        Wikimedia project identifier, e.g. ``"en.wikipedia"``.  The
        MediaWiki API lives at ``https://{project}.org/w/api.php``.
    retry, delay:
        Forwarded to :func:`_get_json`.
    """
    title = article.replace("_", " ")
    encoded = urllib.parse.quote(title, safe="")
    url = (
        f"https://{project}.org/w/api.php"
        f"?action=query&titles={encoded}&redirects=1&format=json"
    )
    try:
        data = _get_json(url, retry=retry, delay=delay)
    except Exception:  # noqa: BLE001
        return article

    pages = data.get("query", {}).get("pages", {})
    if not pages:
        return article

    # pages is a dict keyed by page ID (string); -1 means not found
    page = next(iter(pages.values()))
    if page.get("pageid", -1) == -1:
        return article

    return page.get("title", article)


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
