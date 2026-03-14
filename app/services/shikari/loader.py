"""
loader.py — Data loading and session discovery for sensor EDA.

Functions:
    list_sessions(data_dir) -> list of session directory paths (sorted chronologically)
    load_session(session_dir) -> dict[str, pd.DataFrame] of all sensor CSVs
    load_meta(session_dir)   -> dict with device info and timing events
"""

from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from app.services.shikari.constants import EVENT_START, META_DEVICE_KEY, META_TIME_KEY, XYZ_SENSORS


TIME_COL = "time_s"
PRESSURE_COL = "pressure_hpa"
LAT_COL = "latitude_deg"
LON_COL = "longitude_deg"
HEIGHT_COL = "height_m"
VELOCITY_COL = "velocity_mps"
DIRECTION_COL = "direction_deg"
H_ACC_COL = "horizontal_accuracy_m"
V_ACC_COL = "vertical_accuracy_m"
X_COL = "x"
Y_COL = "y"
Z_COL = "z"
META_CSV_KEY_MAP = {
    "device": META_DEVICE_KEY,
    "time": META_TIME_KEY,
}


def _format_utc_offset(td: timedelta) -> str:
    total_seconds = int(td.total_seconds())
    sign = "+" if total_seconds >= 0 else "-"
    total_seconds = abs(total_seconds)
    hours, rem = divmod(total_seconds, 3600)
    minutes = rem // 60
    return f"{sign}{hours:02d}:{minutes:02d}"


def _session_name_start_event(session_name: str) -> dict | None:
    """Build a synthetic START event from the session directory timestamp."""
    try:
        naive = datetime.strptime(session_name, "%Y-%m-%d-%H:%M:%S")
    except ValueError:
        return None

    local_dt = naive.replace(tzinfo=datetime.now().astimezone().tzinfo)
    offset = local_dt.utcoffset() or timedelta(0)
    return {
        "event": EVENT_START,
        "experiment_time": 0.0,
        "system_time": float(local_dt.timestamp()),
        "system_time_text": (
            f"{local_dt.strftime('%Y-%m-%d %H:%M:%S')}.000 UTC{_format_utc_offset(offset)}"
        ),
    }


def _infer_duration_from_sensors(session_data: dict[str, pd.DataFrame] | None) -> float:
    """Infer session duration from the max time in normalized sensor frames."""
    if not session_data:
        return 0.0

    max_times: list[float] = []
    for key, df in session_data.items():
        if key.startswith("meta/") or TIME_COL not in df.columns or df.empty:
            continue
        try:
            max_times.append(float(pd.to_numeric(df[TIME_COL], errors="coerce").max()))
        except Exception:
            continue

    if not max_times:
        return 0.0
    return float(np.nanmax(max_times))


# ---------------------------------------------------------------------------
# Session discovery
# ---------------------------------------------------------------------------

def list_sessions(data_dir: str | Path) -> list[Path]:
    """Return a sorted list of session directory paths inside *data_dir*.

    All immediate subdirectories are considered candidate sessions.
    The list is sorted by directory name (typically chronological for
    timestamp-based names).
    """
    data_dir = Path(data_dir)
    sessions = [
        d for d in data_dir.iterdir()
        if d.is_dir()
    ]
    sessions.sort(key=lambda p: p.name)
    return sessions


# ---------------------------------------------------------------------------
# Session loading
# ---------------------------------------------------------------------------


def _norm_col(col_name: str) -> str:
    return "".join(ch.lower() for ch in str(col_name) if ch.isalnum())


def _extract_unit(col_name: str) -> str:
    if "(" in col_name and ")" in col_name:
        return str(col_name).split("(")[-1].rstrip(")")
    return ""


def _rename_by_aliases(
    df: pd.DataFrame,
    alias_map: dict[str, tuple[str, ...]],
    *,
    csv_name: str,
) -> pd.DataFrame:
    """Rename columns to canonical names using exact/normalized aliases and validate."""
    cols = [str(c) for c in df.columns]
    norm_to_col = {_norm_col(col): col for col in cols}
    rename_map: dict[str, str] = {}
    missing: list[str] = []

    for canonical, aliases in alias_map.items():
        found = None
        for alias in aliases:
            if alias in cols:
                found = alias
                break
        if found is None:
            for alias in aliases:
                found = norm_to_col.get(_norm_col(alias))
                if found is not None:
                    break
        if found is None:
            missing.append(canonical)
            continue
        rename_map[found] = canonical

    if missing:
        raise ValueError(
            f"{csv_name}: missing required columns {missing}; found {cols}"
        )

    out = df.rename(columns=rename_map).copy()
    # Ensure no duplicate canonical names after normalization.
    if out.columns.duplicated().any():
        dupes = out.columns[out.columns.duplicated()].tolist()
        raise ValueError(f"{csv_name}: duplicate columns after normalization: {dupes}")
    return out


def _normalize_xyz_sensor(df: pd.DataFrame, *, csv_name: str) -> pd.DataFrame:
    cols = [str(c) for c in df.columns]
    time_col = None
    for candidate in ("Time (s)", "Time"):
        if candidate in cols:
            time_col = candidate
            break
    if time_col is None:
        norm_to_col = {_norm_col(col): col for col in cols}
        for candidate in ("Time (s)", "Time"):
            time_col = norm_to_col.get(_norm_col(candidate))
            if time_col is not None:
                break
    if time_col is None:
        raise ValueError(f"{csv_name}: missing time column; found {cols}")

    lowered = {str(col): str(col).lower() for col in df.columns}

    def axis_col(axis: str) -> str:
        patterns = (f" {axis} (", f" {axis}_", f" {axis}-")
        for col, low in lowered.items():
            if any(p in low for p in patterns):
                return col
        raise ValueError(f"{csv_name}: missing {axis}-axis column; found {cols}")

    x_col = axis_col("x")
    y_col = axis_col("y")
    z_col = axis_col("z")
    xyz_unit = _extract_unit(x_col)
    out = df.rename(columns={
        time_col: TIME_COL,
        x_col: X_COL,
        y_col: Y_COL,
        z_col: Z_COL,
    }).copy()
    if out.columns.duplicated().any():
        dupes = out.columns[out.columns.duplicated()].tolist()
        raise ValueError(f"{csv_name}: duplicate columns after normalization: {dupes}")
    out.attrs["xyz_unit"] = xyz_unit
    return out


def _normalize_sensor_frame(sensor_name: str, df: pd.DataFrame, *, csv_name: str) -> pd.DataFrame:
    """Normalize known sensor schemas to canonical column names and validate required columns."""
    if sensor_name in XYZ_SENSORS:
        return _normalize_xyz_sensor(df, csv_name=csv_name)

    if sensor_name == "Pressure":
        return _rename_by_aliases(
            df,
            {
                TIME_COL: ("Time (s)", "Time"),
                PRESSURE_COL: ("Pressure (hPa)", "Pressure"),
            },
            csv_name=csv_name,
        )

    if sensor_name == "Location":
        return _rename_by_aliases(
            df,
            {
                TIME_COL: ("Time (s)", "Time"),
                LAT_COL: ("Latitude (°)", "Latitude"),
                LON_COL: ("Longitude (°)", "Longitude"),
                HEIGHT_COL: ("Height (m)", "Height"),
                VELOCITY_COL: ("Velocity (m/s)", "Velocity"),
                DIRECTION_COL: ("Direction (°)", "Direction"),
                H_ACC_COL: ("Horizontal Accuracy (m)", "Horizontal Accuracy"),
                V_ACC_COL: ("Vertical Accuracy (m)", "Vertical Accuracy"),
            },
            csv_name=csv_name,
        )

    return df

def load_session(session_dir: str | Path) -> dict[str, pd.DataFrame]:
    """Load every CSV in *session_dir* (and its ``meta/`` subfolder) into a dict.

    Keys are the file stems, e.g. ``"Accelerometer"``, ``"Location"``.
    Meta files are keyed as ``meta/device`` and ``meta/time``.
    """
    session_dir = Path(session_dir)
    data: dict[str, pd.DataFrame] = {}

    # Top-level sensor CSVs
    for csv_file in sorted(session_dir.glob("*.csv")):
        df = pd.read_csv(csv_file)
        data[csv_file.stem] = _normalize_sensor_frame(
            csv_file.stem,
            df,
            csv_name=str(csv_file),
        )

    # Meta CSVs
    meta_dir = session_dir / "meta"
    if meta_dir.is_dir():
        for csv_file in sorted(meta_dir.glob("*.csv")):
            key = META_CSV_KEY_MAP.get(csv_file.stem, f"meta/{csv_file.stem}")
            data[key] = pd.read_csv(csv_file)

    return data


# ---------------------------------------------------------------------------
# Meta helpers
# ---------------------------------------------------------------------------

def load_meta(
    session_dir: str | Path,
    session_data: dict[str, pd.DataFrame] | None = None,
) -> dict:
    """Parse ``meta/device.csv`` and ``meta/time.csv`` into a structured dict.

    Parameters
    ----------
    session_dir : str | Path
        Path to the session directory (used for the session name and as a
        fallback for reading CSVs from disk).
    session_data : dict[str, pd.DataFrame], optional
        If provided (e.g. the return value of :func:`load_session`), the
        meta DataFrames are taken from here instead of re-reading from disk.

    Returns a dict with keys:
        - ``"device"``: dict of device properties (model, brand, manufacturer, …)
        - ``"sensors"``: dict keyed by sensor name, each a dict of properties
        - ``"events"``: list of dicts with keys ``event``, ``experiment_time``,
          ``system_time``, ``system_time_text``
        - ``"duration_s"``: total experiment duration in seconds
        - ``"session_name"``: directory name (timestamp string)
    """
    session_dir = Path(session_dir)
    meta: dict = {
        "device": {},
        "sensors": {},
        "events": [],
        "duration_s": 0.0,
        "session_name": session_dir.name,
        "time_inferred": False,
    }

    # --- device.csv ----------------------------------------------------------
    device_df = (session_data or {}).get(META_DEVICE_KEY)
    if device_df is None:
        device_csv = session_dir / "meta" / "device.csv"
        if device_csv.exists():
            device_df = pd.read_csv(device_csv)

    if device_df is not None and not device_df.empty:
        # Vectorised: split into device-level vs sensor-level rows
        props = device_df[["property", "value"]].astype(str)
        has_space = props["property"].str.contains(" ", regex=False)

        # Device-level properties (no space in key)
        dev_rows = props.loc[~has_space]
        meta["device"] = dict(zip(dev_rows["property"], dev_rows["value"]))

        # Sensor-level properties ("sensorKey Attr")
        sen_rows = props.loc[has_space].copy()
        splits = sen_rows["property"].str.split(" ", n=1)
        sen_rows = sen_rows.assign(
            sensor_key=splits.str[0],
            attr=splits.str[1],
        )
        sensor_props: dict[str, dict[str, str]] = {}
        for sensor_key, grp in sen_rows.groupby("sensor_key"):
            sensor_props[sensor_key] = dict(zip(grp["attr"], grp["value"]))
        meta["sensors"] = sensor_props

    # --- time.csv ------------------------------------------------------------
    time_df = (session_data or {}).get(META_TIME_KEY)
    if time_df is None:
        time_csv = session_dir / "meta" / "time.csv"
        if time_csv.exists():
            time_df = pd.read_csv(time_csv)

    if time_df is not None and not time_df.empty:
        events = time_df.rename(columns={
            "experiment time": "experiment_time",
            "system time": "system_time",
            "system time text": "system_time_text",
        }).to_dict(orient="records")
        # Ensure numeric types
        for ev in events:
            ev["experiment_time"] = float(ev["experiment_time"])
            ev["system_time"] = float(ev["system_time"])
        meta["events"] = events

        # Duration = last recorded experiment time
        meta["duration_s"] = float(time_df["experiment time"].max())
    else:
        # Fallback: infer duration from sensor CSV time columns and map wall-clock
        # to the session directory name timestamp (to second precision).
        meta["duration_s"] = _infer_duration_from_sensors(session_data)
        synthetic_start = _session_name_start_event(session_dir.name)
        if synthetic_start is not None:
            meta["events"] = [synthetic_start]
            meta["time_inferred"] = True

    return meta


# ---------------------------------------------------------------------------
# Time mapping: experiment time → wall-clock
# ---------------------------------------------------------------------------

def _parse_utc_offset(time_text: str) -> timedelta:
    """Extract UTC offset from a string like ``'2026-02-24 11:12:51.682 UTC+05:30'``."""
    parts = time_text.split("UTC")
    if len(parts) < 2:
        return timedelta(0)
    offset_str = parts[1].strip()  # e.g. "+05:30"
    sign = 1 if offset_str[0] == "+" else -1
    h, m = offset_str[1:].split(":")
    return timedelta(hours=sign * int(h), minutes=sign * int(m))


def experiment_to_wall_clock(
    experiment_times: pd.Series | np.ndarray,
    events: list[dict],
    fmt: str = "%H:%M:%S",
) -> list[str]:
    """Map experiment-elapsed times to wall-clock time strings.

    Uses the START events in *events* to build a piecewise mapping from
    experiment time to system (Unix) time, then formats each result using
    the timezone parsed from the first event's ``system_time_text``.

    Parameters
    ----------
    experiment_times : array-like of float
        Experiment elapsed times in seconds.
    events : list[dict]
        Events list from ``load_meta()["events"]``.
    fmt : str
        ``strftime`` format for the output strings.

    Returns
    -------
    list[str]
        One formatted wall-clock string per input time.
    """
    if not events:
        return [""] * len(experiment_times)

    # Build sorted arrays of START-event breakpoints
    starts = sorted(
        [e for e in events if e["event"] == EVENT_START],
        key=lambda e: e["experiment_time"],
    )
    if not starts:
        return [""] * len(experiment_times)

    start_exp = np.array([s["experiment_time"] for s in starts])
    start_sys = np.array([s["system_time"] for s in starts])

    # Determine timezone from the first event
    first_text = events[0].get("system_time_text", "")
    tz = timezone(_parse_utc_offset(first_text)) if "UTC" in first_text else timezone.utc

    # Vectorised lookup: for each t find the last START with exp_time <= t
    exp_arr = np.asarray(experiment_times, dtype=float)
    idx = np.searchsorted(start_exp, exp_arr, side="right") - 1
    idx = np.clip(idx, 0, len(starts) - 1)

    sys_times = start_sys[idx] + (exp_arr - start_exp[idx])

    return [
        datetime.fromtimestamp(float(st), tz=tz).strftime(fmt)
        for st in sys_times
    ]
