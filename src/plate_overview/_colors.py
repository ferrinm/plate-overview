"""Channel colors for merge compositing.

Single-channel PNGs always use viridis. A merge adds one black-to-color
ramp per channel, so the colors must stay additive and distinct.
"""

from __future__ import annotations

from matplotlib.colors import LinearSegmentedColormap

__all__ = [
    "COLOR_RGB",
    "DEFAULT_CHANNEL_COLORS",
    "named_cmap",
    "resolve_channel_colors",
    "rgb_for",
]

# Color name → (R, G, B) for additive merge compositing. Single-color
# colormaps go from black to the named tip. The names match napari's, so
# a consumer that already colors channels for a viewer reuses them.
COLOR_RGB: dict[str, tuple[float, float, float]] = {
    "gray": (1.0, 1.0, 1.0),
    "grey": (1.0, 1.0, 1.0),
    "red": (1.0, 0.0, 0.0),
    "green": (0.0, 1.0, 0.0),
    "blue": (0.0, 0.0, 1.0),
    "cyan": (0.0, 1.0, 1.0),
    "magenta": (1.0, 0.0, 1.0),
    "yellow": (1.0, 1.0, 0.0),
}

# Fallback assignment, by channel order, when a consumer supplies no
# colors of its own.
DEFAULT_CHANNEL_COLORS = (
    "cyan",
    "magenta",
    "yellow",
    "green",
    "red",
    "blue",
)


def rgb_for(color_name: str) -> tuple[float, float, float]:
    """Look up a color name. An unknown name renders as white."""
    return COLOR_RGB.get(color_name.lower(), (1.0, 1.0, 1.0))


def named_cmap(color_name: str) -> LinearSegmentedColormap:
    """Black → named-color linear colormap, for the colorbars."""
    return LinearSegmentedColormap.from_list(
        f"plate_overview_{color_name}", [(0, 0, 0), rgb_for(color_name)]
    )


def resolve_channel_colors(
    channel_ids: list[int],
    provided: dict[int, str] | None,
) -> dict[int, str]:
    """Assign one color to each channel.

    A color from *provided* wins. Every other channel takes the next
    color in :data:`DEFAULT_CHANNEL_COLORS`, by its position in
    *channel_ids*.
    """
    provided = provided or {}
    colors: dict[int, str] = {}
    for idx, ch_id in enumerate(channel_ids):
        colors[ch_id] = provided.get(
            ch_id, DEFAULT_CHANNEL_COLORS[idx % len(DEFAULT_CHANNEL_COLORS)]
        )
    return colors
