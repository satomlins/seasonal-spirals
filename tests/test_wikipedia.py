"""Tests for the Wikipedia pageview fetcher (network calls mocked)."""

import json
from unittest.mock import MagicMock, call, patch

import pandas as pd
import pytest

from seasonal_spirals import fetch_pageviews, fetch_multiple
from seasonal_spirals.wikipedia import _resolve_title


def _make_response(records: list[tuple[str, int]]) -> MagicMock:
    """Build a mock urllib response for the given (timestamp, views) pairs."""
    payload = {
        "items": [
            {"timestamp": ts + "00", "views": views}
            for ts, views in records
        ]
    }
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(payload).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def _make_query_response(canonical: str, pageid: int = 1) -> MagicMock:
    """Build a mock MediaWiki action=query response."""
    payload = {"query": {"pages": {str(pageid): {"pageid": pageid, "title": canonical}}}}
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(payload).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def _make_not_found_response() -> MagicMock:
    """Build a mock MediaWiki response for a page that does not exist."""
    payload = {"query": {"pages": {"-1": {"pageid": -1, "title": "Nonexistent"}}}}
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(payload).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


class TestFetchPageviews:
    @patch("urllib.request.urlopen")
    def test_returns_series(self, mock_urlopen):
        mock_urlopen.side_effect = [
            _make_query_response("Python"),
            _make_response([("20220101", 100), ("20220102", 200)]),
        ]
        result = fetch_pageviews("Python", "2022-01-01", "2022-01-02")
        assert isinstance(result, pd.Series)

    @patch("urllib.request.urlopen")
    def test_series_has_datetime_index(self, mock_urlopen):
        mock_urlopen.side_effect = [
            _make_query_response("Python"),
            _make_response([("20220101", 100), ("20220102", 200)]),
        ]
        result = fetch_pageviews("Python", "2022-01-01", "2022-01-02")
        assert isinstance(result.index, pd.DatetimeIndex)

    @patch("urllib.request.urlopen")
    def test_series_name_is_article(self, mock_urlopen):
        mock_urlopen.side_effect = [
            _make_query_response("Influenza"),
            _make_response([("20220101", 50)]),
        ]
        result = fetch_pageviews("Influenza", "2022-01-01", "2022-01-01")
        assert result.name == "Influenza"

    @patch("urllib.request.urlopen")
    def test_values_correct(self, mock_urlopen):
        mock_urlopen.side_effect = [
            _make_query_response("Python"),
            _make_response([("20220101", 123), ("20220102", 456)]),
        ]
        result = fetch_pageviews("Python", "2022-01-01", "2022-01-02")
        assert result["2022-01-01"] == 123.0
        assert result["2022-01-02"] == 456.0

    @patch("urllib.request.urlopen")
    def test_empty_response_returns_empty_series(self, mock_urlopen):
        empty = MagicMock()
        empty.read.return_value = json.dumps({}).encode()
        empty.__enter__ = lambda s: s
        empty.__exit__ = MagicMock(return_value=False)
        mock_urlopen.side_effect = [_make_query_response("Nonexistent"), empty]
        result = fetch_pageviews("Nonexistent", "2022-01-01", "2022-01-02")
        assert isinstance(result, pd.Series)
        assert len(result) == 0

    @patch("urllib.request.urlopen")
    def test_result_is_sorted(self, mock_urlopen):
        mock_urlopen.side_effect = [
            _make_query_response("Python"),
            _make_response([("20220103", 300), ("20220101", 100), ("20220102", 200)]),
        ]
        result = fetch_pageviews("Python", "2022-01-01", "2022-01-03")
        assert result.index.is_monotonic_increasing

    @patch("urllib.request.urlopen")
    def test_spaces_in_article_name(self, mock_urlopen):
        mock_urlopen.side_effect = [
            _make_query_response("Game of Thrones"),
            _make_response([("20220101", 50)]),
        ]
        fetch_pageviews("Game of Thrones", "2022-01-01", "2022-01-01")
        pageview_url = mock_urlopen.call_args_list[1][0][0].full_url
        assert " " not in pageview_url

    @patch("urllib.request.urlopen")
    def test_long_range_chunks_requests(self, mock_urlopen):
        mock_urlopen.side_effect = [
            _make_query_response("Python"),
            _make_response([("20200101", 1)]),
            _make_response([("20210101", 1)]),
        ]
        fetch_pageviews("Python", "2020-01-01", "2022-12-31")
        # First call is title resolution; remaining calls are pageview chunks
        assert mock_urlopen.call_count > 2

    @patch("urllib.request.urlopen")
    def test_resolve_title_false_skips_query(self, mock_urlopen):
        mock_urlopen.return_value = _make_response([("20220101", 10)])
        fetch_pageviews("Python", "2022-01-01", "2022-01-01", resolve_title=False)
        # Only one call: the pageviews request, no title-resolution call
        assert mock_urlopen.call_count == 1

    @patch("urllib.request.urlopen")
    def test_agent_user_in_url(self, mock_urlopen):
        mock_urlopen.side_effect = [
            _make_query_response("Python"),
            _make_response([("20220101", 10)]),
        ]
        fetch_pageviews("Python", "2022-01-01", "2022-01-01")
        pageview_url = mock_urlopen.call_args_list[1][0][0].full_url
        assert "/user/" in pageview_url

    @patch("urllib.request.urlopen")
    def test_agent_all_agents_in_url(self, mock_urlopen):
        mock_urlopen.side_effect = [
            _make_query_response("Python"),
            _make_response([("20220101", 10)]),
        ]
        fetch_pageviews("Python", "2022-01-01", "2022-01-01", agent="all-agents")
        pageview_url = mock_urlopen.call_args_list[1][0][0].full_url
        assert "/all-agents/" in pageview_url


class TestResolveTitle:
    @patch("urllib.request.urlopen")
    def test_returns_canonical_title(self, mock_urlopen):
        mock_urlopen.return_value = _make_query_response("COVID-19")
        result = _resolve_title("covid", "en.wikipedia", retry=1, delay=0)
        assert result == "COVID-19"

    @patch("urllib.request.urlopen")
    def test_follows_redirect(self, mock_urlopen):
        # e.g. "Covid" redirects to "COVID-19"
        mock_urlopen.return_value = _make_query_response("COVID-19")
        result = _resolve_title("Covid", "en.wikipedia", retry=1, delay=0)
        assert result == "COVID-19"

    @patch("urllib.request.urlopen")
    def test_not_found_returns_original(self, mock_urlopen):
        mock_urlopen.return_value = _make_not_found_response()
        result = _resolve_title("Xyzzy_does_not_exist", "en.wikipedia", retry=1, delay=0)
        assert result == "Xyzzy_does_not_exist"

    @patch("urllib.request.urlopen")
    def test_network_error_returns_original(self, mock_urlopen):
        mock_urlopen.side_effect = Exception("network down")
        result = _resolve_title("Python", "en.wikipedia", retry=1, delay=0)
        assert result == "Python"

    @patch("urllib.request.urlopen")
    def test_query_url_uses_project(self, mock_urlopen):
        mock_urlopen.return_value = _make_query_response("Python")
        _resolve_title("Python", "fr.wikipedia", retry=1, delay=0)
        url = mock_urlopen.call_args[0][0].full_url
        assert "fr.wikipedia.org" in url

    @patch("urllib.request.urlopen")
    def test_resolve_updates_series_name(self, mock_urlopen):
        # When a redirect is followed the returned Series should carry the
        # canonical name, not the input alias.
        mock_urlopen.side_effect = [
            _make_query_response("COVID-19"),
            _make_response([("20220101", 500)]),
        ]
        result = fetch_pageviews("Covid", "2022-01-01", "2022-01-01")
        assert result.name == "COVID-19"


class TestFetchMultiple:
    @patch("seasonal_spirals.wikipedia.fetch_pageviews")
    def test_returns_dict(self, mock_fetch):
        mock_fetch.return_value = pd.Series([1, 2], index=pd.date_range("2022-01-01", periods=2))
        result = fetch_multiple(["Python", "Influenza"], "2022-01-01", "2022-01-02")
        assert isinstance(result, dict)
        assert set(result.keys()) == {"Python", "Influenza"}

    @patch("seasonal_spirals.wikipedia.fetch_pageviews")
    def test_each_value_is_series(self, mock_fetch):
        mock_fetch.return_value = pd.Series([1], index=pd.date_range("2022-01-01", periods=1))
        result = fetch_multiple(["Python"], "2022-01-01", "2022-01-01")
        assert isinstance(result["Python"], pd.Series)

    @patch("seasonal_spirals.wikipedia.fetch_pageviews")
    def test_calls_fetch_once_per_article(self, mock_fetch):
        mock_fetch.return_value = pd.Series([], dtype=float)
        fetch_multiple(["A", "B", "C"], "2022-01-01", "2022-01-31")
        assert mock_fetch.call_count == 3

    @patch("seasonal_spirals.wikipedia.fetch_pageviews")
    def test_passes_agent_to_fetch(self, mock_fetch):
        mock_fetch.return_value = pd.Series([], dtype=float)
        fetch_multiple(["Python"], "2022-01-01", "2022-01-01", agent="all-agents")
        _, kwargs = mock_fetch.call_args
        assert kwargs["agent"] == "all-agents"

    @patch("seasonal_spirals.wikipedia.fetch_pageviews")
    def test_passes_resolve_title_to_fetch(self, mock_fetch):
        mock_fetch.return_value = pd.Series([], dtype=float)
        fetch_multiple(["Python"], "2022-01-01", "2022-01-01", resolve_title=False)
        _, kwargs = mock_fetch.call_args
        assert kwargs["resolve_title"] is False
