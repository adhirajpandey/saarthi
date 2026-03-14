"""Shared constants for Shikari visualization services."""

# Data / schema keys
META_DEVICE_KEY = "meta/device"
META_TIME_KEY = "meta/time"
EVENT_START = "START"
EVENT_PAUSE = "PAUSE"

# CLI defaults
OUTPUT_FORMATS = ["png", "html", "pdf"]
THEMES = ["dark", "light"]

# Plotting
AXIS_COLORS = {
    "x": "#e74c3c",
    "y": "#2ecc71",
    "z": "#3498db",
}

VELOCITY_COLORSCALE = [
    [0.0, "#2ecc71"],
    [0.5, "#f1c40f"],
    [1.0, "#e74c3c"],
]

MS_TO_KMPH = 3.6
DEFAULT_DEVICE_NAME = "Pixel 6a Shikari"
XYZ_SENSORS = ["Accelerometer", "Gravity", "Gyroscope", "Linear Acceleration"]
STANDALONE_PLOT_TEMPLATE = "plotly_white"

PLOT_THEMES = {
    "light": {
        "template": "plotly_white",
        "subtitle_color": "#888",
    },
    "dark": {
        "template": "plotly_dark",
        "subtitle_color": "#bbb",
    },
}
