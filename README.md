# seasonal-spirals

Turn any daily time series into a seasonal spiral chart.

Each ring is one year. The angle is the time of year. The colour is the value. If your data has a seasonal pattern, it jumps out immediately. You can see it coiling around year after year.

Inspired by [Wikipulse](https://wikipulse.toolforge.org/), which does this for Wikipedia pageview traffic.

## Installation

```bash
uv add seasonal-spirals
```

## Quick start

```python
from seasonal_spirals import plot_spiral

fig = plot_spiral(data, title="My data")
fig.show()          # interactive in a notebook
fig.write_html("spiral.html")   # standalone HTML file
fig.write_image("spiral.png")   # static image (needs kaleido)
```

### Fetch Wikipedia pageview data

The library includes a fetcher for Wikipedia traffic (no API key needed):

```python
from seasonal_spirals import fetch_pageviews, plot_spiral

data = fetch_pageviews("Influenza", start="2015-01-01", end="2023-12-31")
fig = plot_spiral(data, title="Influenza Wikipedia pageviews", log_scale=True)
fig.show()
```

### Static charts with matplotlib

If you want a static output for saving or publication:

```bash
uv add seasonal-spirals[matplotlib]
```

```python
from seasonal_spirals import plot_spiral_static

fig, ax = plot_spiral_static(data, title="My data", cmap="plasma")
fig.savefig("spiral.png", dpi=150, bbox_inches="tight")
```

## API

### `plot_spiral(data, **kwargs)`

Returns a Plotly `Figure` with hover tooltips. Call `.show()`, `.write_html()`, or `.write_image()` on it.

| Parameter | Default | Description |
|---|---|---|
| `colorscale` | auto | Plotly colorscale (string or list). Leave unset to use the default hybrid colour scheme |
| `inner_radius` | `0.1` | Size of the centre hole |
| `ring_width` | `1.0` | Radial growth per year |
| `start_month` | `1` | Month at 12 o'clock (1 = January) |
| `log_scale` | `False` | Logarithmic colour normalisation |
| `vmin`, `vmax` | auto | Colour scale limits |
| `height`, `width` | `700` | Figure dimensions in pixels |
| `cutoff_n` | `2.0` | Multiplier for the colour scheme cutoff (see below) |
| `cutoff_percentile` | `75.0` | Percentile used to anchor the cutoff (see below) |
| `cutoff` | auto | Override the cutoff directly with a raw value |

### `plot_spiral_static(data, **kwargs)` (requires `[matplotlib]`)

Returns a `(fig, ax)` tuple.

| Parameter | Default | Description |
|---|---|---|
| `cmap` | auto | Matplotlib colourmap. Leave unset to use the default hybrid colour scheme |
| `inner_radius` | `0.1` | Size of the centre hole |
| `ring_width` | `1.0` | Radial growth per year |
| `start_month` | `1` | Month at 12 o'clock |
| `log_scale` | `False` | Logarithmic colour normalisation |
| `vmin`, `vmax` | auto | Colour scale limits |
| `show_month_labels` | `True` | Show month names around the edge |
| `show_year_labels` | `True` | Show year numbers in the spiral |
| `cutoff_n` | `2.0` | Multiplier for the colour scheme cutoff (see below) |
| `cutoff_percentile` | `75.0` | Percentile used to anchor the cutoff (see below) |
| `cutoff` | auto | Override the cutoff directly with a raw value |

### `SeasonalSpiral(data, **kwargs)` (requires `[matplotlib]`)

Lower-level class if you want more control. Call `.plot()` to render.

### `fetch_pageviews(article, start, end)`

Fetches daily Wikipedia pageview counts for one article. Returns a `pd.Series` with a `DatetimeIndex`.

### `fetch_multiple(articles, start, end)`

Same, but for a list of articles. Returns a `dict` of `pd.Series`.

## Colour scheme and the cutoff

The default colour scheme uses a hybrid linear-log scale. The data range is split at a threshold called the **cutoff**:

- **Below the cutoff** (ordinary days): linear scale, light green to dark navy. This is where most days sit, and the linear mapping preserves the relative differences between them.
- **Above the cutoff** (extraordinary spikes): log scale, deep blue through magenta to coral red. The log mapping spreads out the spikes so they don't all collapse to the same colour.

Both halves get equal visual weight regardless of where the cutoff falls numerically, so the choice of cutoff controls how much of the colour range is "spent" on ordinary variation versus spikes.

The cutoff is computed automatically as:

```
cutoff = cutoff_n * percentile(data, cutoff_percentile)
```

with defaults `cutoff_n=2.0` and `cutoff_percentile=75`. In plain English: a day has to be twice as high as a typical busy day before it gets classified as a spike. This took some trial and error to land on, and you may want to adjust it for your data:

```python
# More sensitive: classify fewer days as spikes
plot_spiral(data, cutoff_n=2.0)

# Less sensitive: only the most extreme outliers get the spike colours
plot_spiral(data, cutoff_n=5.0)

# Anchor the threshold at a higher percentile
plot_spiral(data, cutoff_n=3.0, cutoff_percentile=90)

# Override the cutoff directly if you know the right value
plot_spiral(data, cutoff=50_000)
```

Pass `cmap` / `colorscale` to use a completely different colour scheme, which bypasses the cutoff logic entirely.

## Licence

MIT
