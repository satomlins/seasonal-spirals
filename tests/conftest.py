import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def daily_one_year():
    dates = pd.date_range("2022-01-01", "2022-12-31", freq="D")
    rng = np.random.default_rng(42)
    return pd.Series(rng.uniform(10, 100, len(dates)), index=dates, name="test")


@pytest.fixture
def daily_three_years():
    dates = pd.date_range("2020-01-01", "2022-12-31", freq="D")
    rng = np.random.default_rng(42)
    return pd.Series(rng.uniform(10, 100, len(dates)), index=dates, name="test")


@pytest.fixture
def daily_with_nans(daily_three_years):
    s = daily_three_years.copy()
    s.iloc[::30] = np.nan
    return s


@pytest.fixture
def non_datetime_index():
    return pd.Series([1, 2, 3], index=[0, 1, 2])


@pytest.fixture
def non_numeric_data():
    dates = pd.date_range("2022-01-01", periods=3, freq="D")
    return pd.Series(["a", "b", "c"], index=dates)


@pytest.fixture
def all_nan_data():
    dates = pd.date_range("2022-01-01", periods=3, freq="D")
    return pd.Series([np.nan, np.nan, np.nan], index=dates)


@pytest.fixture
def daily_twelve_years():
    dates = pd.date_range("2010-01-01", "2021-12-31", freq="D")
    rng = np.random.default_rng(42)
    return pd.Series(rng.uniform(10, 100, len(dates)), index=dates, name="test")
