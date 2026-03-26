# seasonal-spirals

A Python library for visualising time series data as seasonal spiral charts.

## Inspiration

This library was born out of admiration for [Wikipulse](https://wikipulse.toolforge.org/), a tool that renders Wikipedia article pageview traffic as beautiful seasonal spirals — coiling outward year by year, with colour encoding the traffic volume. Looking at those charts, the seasonal rhythm of any topic becomes immediately obvious: the annual spike in *Influenza* every winter, the summer surge in *Wimbledon*, the relentless year-on-year growth of certain articles.

We wanted to be able to produce those spirals ourselves — for any time series data, not just Wikipedia traffic — and tweak every aspect of the layout. So we built this library.

## What it does

A seasonal spiral arranges daily data in a clockwise spiral where:

- **Angle** encodes time of year (one full revolution = one calendar year, 12 o'clock = January)
- **Radius** increases with each passing year (oldest data at the centre, most recent at the outside)
- **Colour** encodes the data value

The result makes year-on-year seasonal patterns immediately legible at a glance.

## Installation

```bash
pip install seasonal-spirals
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv add seasonal-spirals
```

## Quick start

```python
import pandas as pd
from seasonal_spirals import plot_spiral

# Any daily pandas Series with a DatetimeIndex works
fig, ax = plot_spiral(data, title="My data", cmap="plasma")
fig.savefig("spiral.png", dpi=150, bbox_inches="tight")
```

### Wikipedia pageviews

The library includes a built-in fetcher for Wikipedia pageview data via the Wikimedia REST API (no API key required):

```python
from seasonal_spirals import fetch_pageviews, plot_spiral

data = fetch_pageviews("Influenza", start="2015-01-01", end="2023-12-31")
fig, ax = plot_spiral(data, title="Influenza — Wikipedia pageviews", cmap="YlOrRd", log_scale=True)
```

### Interactive charts

For an interactive version with hover tooltips, use Plotly:

```python
from seasonal_spirals import fetch_pageviews, plot_spiral_interactive

data = fetch_pageviews("Game_of_Thrones", start="2015-01-01", end="2019-12-31")
fig = plot_spiral_interactive(data, title="Game of Thrones — Wikipedia pageviews")
fig.show()
```

## API

### `plot_spiral(data, **kwargs)`

Convenience function. Returns a `(fig, ax)` tuple from matplotlib.

| Parameter | Default | Description |
|---|---|---|
| `cmap` | `"YlGnBu"` | Matplotlib colourmap |
| `inner_radius` | `0.1` | Size of the centre hole |
| `ring_width` | `1.0` | Radial growth per year |
| `start_month` | `1` | Month at 12 o'clock |
| `log_scale` | `False` | Logarithmic colour normalisation |
| `vmin`, `vmax` | auto | Colour scale limits |
| `show_month_labels` | `True` | Show month names around the edge |
| `show_year_labels` | `True` | Show year numbers in the spiral |

### `SeasonalSpiral(data, **kwargs)`

Lower-level class for more control. Call `.plot()` to render.

### `plot_spiral_interactive(data, **kwargs)`

Returns a Plotly `Figure` with hover tooltips showing date, value, and day of week.

### `fetch_pageviews(article, start, end, project="en.wikipedia")`

Fetches daily Wikipedia pageview counts for a single article. Returns a `pd.Series`.

### `fetch_multiple(articles, start, end)`

Fetches pageviews for a list of articles. Returns a `dict` of `pd.Series`.

## Examples

See [`examples/demo.ipynb`](examples/demo.ipynb) for worked examples including Wikipedia traffic and custom data.

## Licence

MIT
