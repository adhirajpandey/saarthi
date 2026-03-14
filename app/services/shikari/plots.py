"""
plots.py — Plotly visualization functions for sensor data.

Every public function returns a ``plotly.graph_objects.Figure`` so callers can
``.show()``, ``.write_html()``, or compose figures further.

Functions:
    plot_xyz_sensor(df, title)          -> 3-axis subplot (x/y/z)
    plot_pressure(df)                   -> single-trace pressure time series
    plot_location_trace(df)             -> lat/lon scatter colored by velocity
    plot_velocity(df)                   -> velocity over time
    plot_session_dashboard(data, meta)  -> combined multi-panel dashboard
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from app.services.shikari.constants import (
    AXIS_COLORS,
    DEFAULT_DEVICE_NAME,
    EVENT_PAUSE,
    EVENT_START,
    MS_TO_KMPH,
    PLOT_THEMES,
    STANDALONE_PLOT_TEMPLATE,
    VELOCITY_COLORSCALE,
    XYZ_SENSORS,
)
from app.services.shikari.loader import (
    LAT_COL,
    LON_COL,
    PRESSURE_COL,
    TIME_COL,
    VELOCITY_COL,
    X_COL,
    Y_COL,
    Z_COL,
    experiment_to_wall_clock,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _filter_events(events: list[dict], min_gap: float = 5.0) -> list[dict]:
    """Return events keeping only those at least *min_gap* seconds apart.

    This avoids overlapping vertical lines when START and PAUSE happen almost
    simultaneously (e.g. the initial brief pause at t ≈ 0).
    """
    if not events:
        return []
    filtered: list[dict] = [events[0]]
    for ev in events[1:]:
        if abs(ev["experiment_time"] - filtered[-1]["experiment_time"]) >= min_gap:
            filtered.append(ev)
    return filtered


def _add_pause_annotations(
    fig: go.Figure,
    events: list[dict],
    *,
    row_count: int = 1,
    col_count: int = 1,
    min_gap: float = 0.0,
    opacity: float = 0.5,
) -> None:
    """Draw vertical lines for START/PAUSE events across subplot rows/cols.

    Parameters
    ----------
    fig : go.Figure
        Target figure.
    events : list[dict]
        Event list from ``load_meta``.
    row_count, col_count : int
        Number of subplot rows/columns to annotate (1-based).
    min_gap : float
        If > 0, events closer than this many seconds are filtered out via
        :func:`_filter_events`.
    opacity : float
        Line opacity.
    """
    to_draw = _filter_events(events, min_gap=min_gap) if min_gap > 0 else events
    for ev in to_draw:
        t = ev["experiment_time"]
        if ev["event"] == EVENT_START:
            color = "green"
        elif ev["event"] == EVENT_PAUSE:
            color = "red"
        else:
            color = "gray"
        for row in range(1, row_count + 1):
            for col in range(1, col_count + 1):
                fig.add_vline(
                    x=t, line_dash="dash", line_color=color, opacity=opacity,
                    row=row, col=col,
                )


def _build_customdata(
    time_series: pd.Series,
    events: list[dict] | None,
    *extra: list,
) -> list[list[str]] | None:
    """Build a customdata array with wall-clock time and optional extra columns.

    ``customdata[i][0]`` is always the wall-clock string (or ``""`` if no
    events).  ``customdata[i][1..]`` are values from *extra* lists.

    Returns *None* only when there are no events AND no extra columns —
    meaning there is nothing useful to show in the tooltip.
    """
    has_extra = bool(extra)
    if not events and not has_extra:
        return None
    clock_strs = (
        experiment_to_wall_clock(time_series, events)
        if events else [""] * len(time_series)
    )
    if not has_extra:
        return [[c] for c in clock_strs]
    return [[c] + [col[i] for col in extra] for i, c in enumerate(clock_strs)]


def _decimate_df(df: pd.DataFrame, max_points: int) -> pd.DataFrame:
    """Downsample dataframe to at most ``max_points`` rows while preserving order."""
    if len(df) <= max_points:
        return df
    step = int(np.ceil(len(df) / max_points))
    out = df.iloc[::step].copy()
    out.attrs = dict(df.attrs)
    return out


# ---------------------------------------------------------------------------
# Shared trace-kwargs builders (used by standalone plots AND dashboard)
# ---------------------------------------------------------------------------

def _make_pressure_kwargs(
    df: pd.DataFrame,
    events: list[dict] | None,
) -> dict:
    """Return ``go.Scattergl`` kwargs for a pressure trace."""
    cdata = _build_customdata(df[TIME_COL], events)
    kwargs: dict = dict(
        x=df[TIME_COL],
        y=df[PRESSURE_COL],
        mode="lines",
        line=dict(width=1, color="#9b59b6"),
        name="Pressure",
    )
    if cdata is not None:
        kwargs["customdata"] = cdata
        kwargs["hovertemplate"] = (
            "%{y:.2f} hPa"
            "<br>Clock: %{customdata[0]}"
            "<extra>Pressure</extra>"
        )
    return kwargs


def _make_velocity_kwargs(
    df: pd.DataFrame,
    events: list[dict] | None,
    *,
    unit: str = "km/h",
    marker_size: int = 2,
    hover_fmt: str | None = None,
) -> dict:
    """Return ``go.Scattergl`` kwargs for a velocity trace.

    *unit* selects ``"km/h"`` or ``"m/s"``.  *hover_fmt* overrides the
    default number format in the tooltip (``".1f"`` for km/h, ``".2f"``
    for m/s).
    """
    if unit == "km/h":
        vel = df[VELOCITY_COL] * MS_TO_KMPH
        fmt = hover_fmt or ".1f"
    else:
        vel = df[VELOCITY_COL]
        fmt = hover_fmt or ".2f"
    cdata = _build_customdata(df[TIME_COL], events)
    kwargs: dict = dict(
        x=df[TIME_COL],
        y=vel,
        mode="lines+markers",
        marker=dict(size=marker_size),
        line=dict(width=1, color="#e67e22"),
        name=f"Velocity ({unit})",
    )
    if cdata is not None:
        kwargs["customdata"] = cdata
        kwargs["hovertemplate"] = (
            f"%{{y:{fmt}}} {unit}"
            "<br>Clock: %{customdata[0]}"
            "<extra>Velocity</extra>"
        )
    return kwargs


def _make_gps_kwargs(
    df: pd.DataFrame,
    events: list[dict] | None,
    *,
    name: str = "GPS trace",
    colorbar_kw: dict | None = None,
) -> dict:
    """Return ``go.Scattergl`` kwargs for a GPS trace coloured by velocity."""
    vel_kmph = df[VELOCITY_COL] * MS_TO_KMPH

    vel_strs = [f"{v:.1f}" for v in vel_kmph]
    cdata = _build_customdata(df[TIME_COL], events, vel_strs)

    cb = colorbar_kw or dict(title="Velocity (km/h)")
    return dict(
        x=df[LON_COL],
        y=df[LAT_COL],
        mode="markers+lines",
        marker=dict(
            size=5,
            color=vel_kmph,
            colorscale=VELOCITY_COLORSCALE,
            colorbar=cb,
        ),
        line=dict(width=0.5, color="rgba(0,0,0,0.15)"),
        name=name,
        customdata=cdata,
        hovertemplate=(
            "Lon: %{x:.6f}°<br>Lat: %{y:.6f}°"
            "<br>Velocity: %{customdata[1]} km/h"
            "<br>Clock: %{customdata[0]}"
            f"<extra>{name}</extra>"
        ),
    )


# ---------------------------------------------------------------------------
# 3-axis sensor plot (Accelerometer / Gravity / Gyroscope / Linear Accel)
# ---------------------------------------------------------------------------

def plot_xyz_sensor(
    df: pd.DataFrame,
    title: str = "Sensor",
    events: list[dict] | None = None,
) -> go.Figure:
    """Plot a 3-axis sensor as three vertically stacked subplots sharing the time axis.

    Parameters
    ----------
    df : pd.DataFrame
        Must be a normalized 3-axis sensor DataFrame from ``loader.load_session()``
        with canonical columns ``time_s``, ``x``, ``y``, ``z``.
    title : str
        Figure title.
    events : list[dict], optional
        START/PAUSE events from ``load_meta`` to annotate on the plot.
    """
    unit = str(df.attrs.get("xyz_unit", ""))
    cdata = _build_customdata(df[TIME_COL], events)

    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        subplot_titles=("X axis", "Y axis", "Z axis"),
    )

    for i, (col, axis_label) in enumerate(
        [(X_COL, "x"), (Y_COL, "y"), (Z_COL, "z")], start=1
    ):
        trace_kwargs: dict = dict(
            x=df[TIME_COL],
            y=df[col],
            mode="lines",
            line=dict(width=1, color=AXIS_COLORS[axis_label]),
            name=f"{axis_label} ({unit})" if unit else axis_label,
            showlegend=True,
        )
        if cdata is not None:
            trace_kwargs["customdata"] = cdata
            trace_kwargs["hovertemplate"] = (
                "%{y:.4f} " + (unit or "") +
                "<br>Clock: %{customdata[0]}"
                "<extra>%{fullData.name}</extra>"
            )
        fig.add_trace(go.Scattergl(**trace_kwargs), row=i, col=1)
        fig.update_yaxes(title_text=unit if unit else col, row=i, col=1)

    fig.update_xaxes(title_text="Time (s)", row=3, col=1)
    fig.update_layout(
        title_text=title,
        height=700,
        template=STANDALONE_PLOT_TEMPLATE,
        hovermode="x unified",
    )

    if events:
        _add_pause_annotations(fig, events, row_count=3)

    return fig


# ---------------------------------------------------------------------------
# Pressure
# ---------------------------------------------------------------------------

def plot_pressure(
    df: pd.DataFrame,
    events: list[dict] | None = None,
) -> go.Figure:
    """Single-trace time series for barometric pressure."""
    fig = go.Figure()
    fig.add_trace(go.Scattergl(**_make_pressure_kwargs(df, events)))
    fig.update_layout(
        title_text="Barometric Pressure",
        xaxis_title="Time (s)",
        yaxis_title="Pressure (hPa)",
        height=400,
        template=STANDALONE_PLOT_TEMPLATE,
        hovermode="x unified",
    )

    if events:
        _add_pause_annotations(fig, events)

    return fig


# ---------------------------------------------------------------------------
# Location: trace
# ---------------------------------------------------------------------------

def plot_location_trace(
    df: pd.DataFrame,
    events: list[dict] | None = None,
) -> go.Figure:
    """Scatter of Latitude vs Longitude, coloured by velocity."""
    fig = go.Figure()
    fig.add_trace(go.Scattergl(**_make_gps_kwargs(df, events)))
    fig.update_layout(
        title_text="GPS Trace",
        xaxis_title="Longitude (°)",
        yaxis_title="Latitude (°)",
        height=550,
        template=STANDALONE_PLOT_TEMPLATE,
        yaxis_scaleanchor="x",  # keep aspect ratio
    )
    return fig


# ---------------------------------------------------------------------------
# Location: velocity
# ---------------------------------------------------------------------------

def plot_velocity(
    df: pd.DataFrame,
    events: list[dict] | None = None,
) -> go.Figure:
    """Velocity over time from the Location CSV, with m/s ↔ km/h toggle."""
    fig = go.Figure()

    trace_ms = _make_velocity_kwargs(df, events, unit="m/s", marker_size=3)
    trace_ms["visible"] = True
    fig.add_trace(go.Scattergl(**trace_ms))

    trace_kmph = _make_velocity_kwargs(
        df, events, unit="km/h", marker_size=3, hover_fmt=".2f",
    )
    trace_kmph["visible"] = False
    fig.add_trace(go.Scattergl(**trace_kmph))

    fig.update_layout(
        title_text="Velocity Profile",
        xaxis_title="Time (s)",
        yaxis_title="Velocity (m/s)",
        height=400,
        template=STANDALONE_PLOT_TEMPLATE,
        hovermode="x unified",
        updatemenus=[
            dict(
                type="buttons",
                direction="left",
                x=1.0,
                xanchor="right",
                y=1.15,
                yanchor="top",
                buttons=[
                    dict(
                        label="m/s",
                        method="update",
                        args=[
                            {"visible": [True, False]},
                            {"yaxis.title.text": "Velocity (m/s)"},
                        ],
                    ),
                    dict(
                        label="km/h",
                        method="update",
                        args=[
                            {"visible": [False, True]},
                            {"yaxis.title.text": "Velocity (km/h)"},
                        ],
                    ),
                ],
            )
        ],
    )

    if events:
        _add_pause_annotations(fig, events)

    return fig


# ---------------------------------------------------------------------------
# Combined dashboard
# ---------------------------------------------------------------------------

# Layout:  Row 1: Accelerometer | Gravity
#          Row 2: Gyroscope     | Linear Acceleration
#          Row 3: Pressure      | Velocity
#          Row 4: GPS Trace (colspan=2)


def _add_xyz_overlay(
    fig: go.Figure,
    df: pd.DataFrame,
    row: int,
    col: int,
    sensor_name: str,
    events: list[dict] | None = None,
) -> None:
    """Add x/y/z traces overlaid on a single subplot cell."""
    cdata = _build_customdata(df[TIME_COL], events)
    unit = str(df.attrs.get("xyz_unit", ""))
    xyz_cols = [X_COL, Y_COL, Z_COL]

    for i, axis_label in enumerate(["x", "y", "z"]):
        col_name = xyz_cols[i]
        trace_kwargs: dict = dict(
            x=df[TIME_COL],
            y=df[col_name],
            mode="lines",
            line=dict(width=1, color=AXIS_COLORS[axis_label]),
            name=f"{sensor_name} {axis_label}",
            legendgroup=sensor_name,
            showlegend=False,  # subplot titles + color key in subtitle suffice
        )
        if cdata is not None:
            trace_kwargs["customdata"] = cdata
            trace_kwargs["hovertemplate"] = (
                "%{y:.4f} " + (unit or "") +
                "<br>Clock: %{customdata[0]}"
                "<extra>" + axis_label + "</extra>"
            )
        fig.add_trace(go.Scattergl(**trace_kwargs), row=row, col=col)

    fig.update_yaxes(title_text=unit, row=row, col=col)


def plot_session_dashboard(
    session_data: dict[str, pd.DataFrame],
    meta: dict,
    theme: str = "light",
) -> go.Figure:
    """Build a single combined dashboard figure for a session.

    Parameters
    ----------
    session_data : dict[str, pd.DataFrame]
        Output of ``loader.load_session()``.
    meta : dict
        Output of ``loader.load_meta()``.

    Returns
    -------
    go.Figure
        A single Plotly figure with all sensors in a grid layout.
    """
    events = meta.get("events", [])
    device_model = meta.get("device", {}).get("deviceModel") or DEFAULT_DEVICE_NAME
    session_name = meta.get("session_name", "")
    theme_cfg = PLOT_THEMES.get(theme, PLOT_THEMES["light"])

    # Cap trace sizes to avoid static-export timeout on very high-frequency sessions.
    session_for_plot = {
        name: _decimate_df(df, 8000 if name != "Location" else 3000)
        for name, df in session_data.items()
    }

    has_location = "Location" in session_for_plot

    fig = make_subplots(
        rows=4, cols=2,
        row_heights=[0.22, 0.22, 0.22, 0.34],
        vertical_spacing=0.06,
        horizontal_spacing=0.08,
        subplot_titles=(
            "Accelerometer", "Gravity",
            "Gyroscope", "Linear Acceleration",
            "Pressure", "Velocity",
            "GPS Trace",
        ),
        specs=[
            [{}, {}],
            [{}, {}],
            [{}, {}],
            [{"colspan": 2}, None],
        ],
    )

    # --- Row 1–2: 3-axis sensors (x/y/z overlaid) ---------------------------
    grid_positions = [(1, 1), (1, 2), (2, 1), (2, 2)]
    for sensor, (r, c) in zip(XYZ_SENSORS, grid_positions):
        if sensor in session_for_plot:
            _add_xyz_overlay(fig, session_for_plot[sensor], r, c, sensor, events)

    # --- Row 3, Col 1: Pressure ----------------------------------------------
    if "Pressure" in session_for_plot:
        kwargs = _make_pressure_kwargs(session_for_plot["Pressure"], events)
        kwargs.update(legendgroup="Pressure", showlegend=True)
        fig.add_trace(go.Scattergl(**kwargs), row=3, col=1)
        fig.update_yaxes(title_text="hPa", row=3, col=1)

    # --- Row 3, Col 2: Velocity (km/h) --------------------------------------
    if has_location:
        kwargs = _make_velocity_kwargs(session_data["Location"], events, unit="km/h")
        kwargs.update(name="Velocity", legendgroup="Velocity", showlegend=True)
        fig.add_trace(go.Scattergl(**kwargs), row=3, col=2)
        fig.update_yaxes(title_text="km/h", row=3, col=2)

    # --- Row 4: GPS Trace (full width) ---------------------------------------
    if has_location:
        df = session_data["Location"]
        kwargs = _make_gps_kwargs(
            df, events,
            name="GPS",
            colorbar_kw=dict(title="km/h", x=1.01, len=0.3, y=0.15),
        )
        kwargs.update(legendgroup="GPS", showlegend=True)
        fig.add_trace(go.Scattergl(**kwargs), row=4, col=1)

        fig.update_xaxes(title_text="Longitude (°)", row=4, col=1)
        fig.update_yaxes(title_text="Latitude (°)", row=4, col=1)

    # --- Link time x-axes across rows 1–3 for synced zoom/pan ---------------
    # The first subplot (row=1, col=1) uses xaxis "x".  All other time-series
    # subplots are told to match it so zoom/pan stays in sync.
    for r in range(1, 4):
        for c in [1, 2]:
            fig.update_xaxes(title_text="Time (s)", matches="x", row=r, col=c)

    # --- Fix column alignment: consistent y-axis tick width ------------------
    # Set a fixed tick label width so left/right columns line up evenly.
    for r in range(1, 4):
        for c in [1, 2]:
            fig.update_yaxes(tickformat=".1f", row=r, col=c)

    # --- Global layout -------------------------------------------------------
    fig.update_layout(
        title_text=(
            f"{device_model} — {session_name}"
            f'<br><span style="font-size:12px; color:{theme_cfg["subtitle_color"]}">'
            'Axes: <span style="color:#e74c3c">x</span> · '
            '<span style="color:#2ecc71">y</span> · '
            '<span style="color:#3498db">z</span></span>'
        ),
        height=1500,
        template=theme_cfg["template"],
        hovermode="closest",
        showlegend=False,
    )

    # Add START/PAUSE vlines to time-series subplots (rows 1–3),
    # skipping events that are less than 5 s apart (avoids the blob at t≈0).
    if events:
        _add_pause_annotations(
            fig, events, row_count=3, col_count=2, min_gap=5.0, opacity=0.4,
        )

    return fig
