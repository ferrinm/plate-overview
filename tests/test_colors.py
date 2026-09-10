"""Tests for channel colors and cell compositing."""

from __future__ import annotations

import matplotlib
import numpy as np

from plate_overview._colors import (
    DEFAULT_CHANNEL_COLORS,
    named_cmap,
    resolve_channel_colors,
    rgb_for,
)
from plate_overview._figure import render_cell


def test_a_known_color_name_maps_to_its_tip():
    assert rgb_for("Magenta") == (1.0, 0.0, 1.0)


def test_an_unknown_color_name_falls_back_to_white():
    assert rgb_for("chartreuse") == (1.0, 1.0, 1.0)


def test_named_cmap_runs_from_black_to_the_named_tip():
    cmap = named_cmap("green")
    assert cmap(0.0)[:3] == (0.0, 0.0, 0.0)
    np.testing.assert_allclose(cmap(1.0)[:3], (0.0, 1.0, 0.0))


def test_supplied_colors_win_over_the_default_order():
    colors = resolve_channel_colors([1, 2, 3], {2: "red"})
    assert colors[2] == "red"
    assert colors[1] == DEFAULT_CHANNEL_COLORS[0]
    assert colors[3] == DEFAULT_CHANNEL_COLORS[2]


def test_default_colors_cycle_for_a_long_channel_list():
    ids = list(range(len(DEFAULT_CHANNEL_COLORS) + 2))
    colors = resolve_channel_colors(ids, None)
    assert colors[0] == colors[len(DEFAULT_CHANNEL_COLORS)]


def test_a_single_channel_cell_is_rendered_with_viridis():
    """Viridis, not the channel color.

    A single-channel PNG exists to show intensity. Viridis separates
    intensity levels that a black-to-color ramp compresses.
    """
    thumb = np.zeros((1, 2, 2), dtype=np.float32)
    rgb = render_cell(thumb, [0], [(0.0, 1.0)], ["green"], True)
    expected = matplotlib.colormaps["viridis"](0.0)[:3]
    np.testing.assert_allclose(rgb[0, 0], expected, atol=1e-6)
    # A black-to-green ramp would have rendered this cell black.
    assert rgb.max() > 0.0


def test_a_merged_cell_adds_one_ramp_per_channel():
    thumb = np.zeros((2, 1, 1), dtype=np.float32)
    thumb[0, 0, 0] = 1.0
    thumb[1, 0, 0] = 1.0
    rgb = render_cell(
        thumb, [0, 1], [(0.0, 1.0), (0.0, 1.0)], ["red", "green"], False
    )
    np.testing.assert_allclose(rgb[0, 0], (1.0, 1.0, 0.0))


def test_a_merged_cell_clips_at_white():
    thumb = np.ones((2, 1, 1), dtype=np.float32)
    rgb = render_cell(
        thumb, [0, 1], [(0.0, 1.0), (0.0, 1.0)], ["red", "red"], False
    )
    np.testing.assert_allclose(rgb[0, 0], (1.0, 0.0, 0.0))
