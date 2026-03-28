"""Tests for the Wikipedia pageview fetcher (network calls mocked)."""

import json
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from seasonal_spirals import fetch_pageviews, fetch_multiple


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


class TestFetchPageviews:
    @patch("urllib.request.urlopen")
    def test_returns_series(self, mock_urlopen):
        mock_urlopen.return_value = _make_response([
            ("20220101", 100),
            ("20220102", 200),
        ])
        result = fetch_pageviews("Python", "2022-01-01", "2022-01-02")
        assert isinstance(result, pd.Series)

    @patch("urllib.request.urlopen")
    def test_series_has_datetime_index(self, mock_urlopen):
        mock_urlopen.return_value = _make_response([
            ("20220101", 100),
            ("20220102", 200),
        ])
        result = fetch_pageviews("Python", "2022-01-01", "2022-01-02")
        assert isinstance(result.index, pd.DatetimeIndex)

    @patch("urllib.request.urlopen")
    def test_series_name_is_article(self, mock_urlopen):
        mock_urlopen.return_value = _make_response([("20220101", 50)])
        result = fetch_pageviews("Influenza", "2022-01-01", "2022-01-01")
        assert result.name == "Influenza"

    @patch("urllib.request.urlopen")
    def test_values_correct(self, mock_urlopen):
        mock_urlopen.return_value = _make_response([
            ("20220101", 123),
            ("20220102", 456),
        ])
        result = fetch_pageviews("Python", "2022-01-01", "2022-01-02")
        assert result["2022-01-01"] == 123.0
        assert result["2022-01-02"] == 456.0

    @patch("urllib.request.urlopen")
    def test_empty_response_returns_empty_series(self, mock_urlopen):
        empty = MagicMock()
        empty.read.return_value = json.dumps({}).encode()
        empty.__enter__ = lambda s: s
        empty.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = empty
        result = fetch_pageviews("Nonexistent", "2022-01-01", "2022-01-02")
        assert isinstance(result, pd.Series)
        assert len(result) == 0

    @patch("urllib.request.urlopen")
    def test_result_is_sorted(self, mock_urlopen):
        # Return records out of order
        mock_urlopen.return_value = _make_response([
            ("20220103", 300),
            ("20220101", 100),
            ("20220102", 200),
        ])
        result = fetch_pageviews("Python", "2022-01-01", "2022-01-03")
        assert result.index.is_monotonic_increasing

    @patch("urllib.request.urlopen")
    def test_spaces_in_article_name(self, mock_urlopen):
        mock_urlopen.return_value = _make_response([("20220101", 50)])
        # Should not raise
        fetch_pageviews("Game of Thrones", "2022-01-01", "2022-01-01")
        call_url = mock_urlopen.call_args[0][0].full_url
        assert " " not in call_url

    @patch("urllib.request.urlopen")
    def test_long_range_chunks_requests(self, mock_urlopen):
        mock_urlopen.return_value = _make_response([("20200101", 1)])
        # 3-year range exceeds the 730-day chunk limit, so should make >1 call
        fetch_pageviews("Python", "2020-01-01", "2022-12-31")
        assert mock_urlopen.call_count > 1


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
