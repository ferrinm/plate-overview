"""Pixel parity against the implementation this package was moved from.

The renderer was extracted from ``pyphenix._overview``. The move must
change no pixel: the plate overview is a calibrated instrument, and a
drift in contrast or layout breaks the two eyeball judgements it exists
to support.

This module renders the same synthetic plate twice, once through each
implementation, and compares the PNG bytes.

The test skips when ``pyphenix`` is not installed, which is the normal
case in this repository's CI. Install ``pyphenix`` next to this package
to run it:

.. code-block:: bash

   uv run --with pyphenix pytest tests/test_parity_with_pyphenix.py
"""

from __future__ import annotations

import numpy as np
import pytest

legacy = pytest.importorskip(
    "pyphenix._overview",
    reason="parity is checked against pyphenix, which is not installed",
)

from plate_overview._colors import named_cmap  # noqa: E402
from plate_overview._figure import (  # noqa: E402
    render_cell,
    render_combo_png,
)
from plate_overview._labels import (  # noqa: E402
    combo_label,
    nice_scalebar_length_um,
    options_label,
    resolve_field_label,
    resolve_z_label,
    row_letter,
)
from plate_overview._thumbnails import (  # noqa: E402
    compute_plate_contrast,
    downsample,
    normalize,
)

CHANNEL_NAMES = {1: "ChannelOne", 2: "ChannelTwo"}
COMBO_COLORS = ["cyan", "magenta"]


@pytest.fixture
def well_thumbs() -> dict[tuple[int, int], np.ndarray]:
    """Six synthetic thumbnails, shape ``(2, 24, 32)``."""
    rng = np.random.default_rng(20260910)
    return {
        (row, col): rng.random((2, 24, 32)).astype(np.float32) * 3000
        for row in (1, 2)
        for col in (1, 2, 3)
    }


def test_downsample_is_unchanged():
    rng = np.random.default_rng(1)
    arr = rng.integers(0, 4000, size=(2, 48, 64), dtype=np.uint16)
    np.testing.assert_array_equal(
        downsample(arr, 16), legacy._downsample(arr, 16)
    )


def test_plate_contrast_is_unchanged(well_thumbs):
    assert compute_plate_contrast(well_thumbs, [1, 2]) == (
        legacy._compute_plate_contrast(well_thumbs, [1, 2])
    )


def test_normalize_is_unchanged():
    arr = np.linspace(-10, 100, 50, dtype=np.float32)
    np.testing.assert_array_equal(
        normalize(arr, 5.0, 60.0), legacy._normalize(arr, 5.0, 60.0)
    )


@pytest.mark.parametrize("is_singleton", [True, False])
def test_cell_rendering_is_unchanged(well_thumbs, is_singleton):
    thumb = well_thumbs[(1, 1)]
    contrast = [(0.0, 2500.0), (0.0, 2900.0)]
    np.testing.assert_array_equal(
        render_cell(thumb, [0, 1], contrast, COMBO_COLORS, is_singleton),
        legacy._render_cell(
            thumb, [0, 1], contrast, COMBO_COLORS, is_singleton
        ),
    )


def test_the_colorbar_ramp_is_unchanged():
    steps = np.linspace(0.0, 1.0, 17)
    np.testing.assert_array_equal(
        named_cmap("magenta")(steps), legacy._named_cmap("magenta")(steps)
    )


def test_the_labels_are_unchanged():
    assert [row_letter(r) for r in range(1, 17)] == [
        legacy._row_letter(r) for r in range(1, 17)
    ]
    for visible_um in (37.0, 250.0, 1330.0, 9000.0):
        assert nice_scalebar_length_um(visible_um) == (
            legacy._nice_scalebar_length_um(visible_um)
        )
    assert resolve_field_label(None, False, None) == (
        legacy._resolve_field_label(None, False, None)
    )
    assert resolve_z_label([0, 2]) == legacy._resolve_z_label([0, 2])
    assert combo_label((1, 2), CHANNEL_NAMES, 2) == (
        legacy._combo_label((1, 2), CHANNEL_NAMES, 2)
    )
    kwargs = {
        "objective_mag": "20",
        "field_label": "stitched",
        "timepoint_label": "0",
        "z_label": "all",
        "ffc_label": "on",
    }
    assert options_label(**kwargs) == legacy._options_label(**kwargs)


@pytest.mark.parametrize("combo", [(1,), (2,), (1, 2)])
def test_the_png_is_byte_for_byte_unchanged(well_thumbs, combo, tmp_path):
    """The whole point of the move: same PNGs, same contrast."""
    contrast = compute_plate_contrast(well_thumbs, [1, 2])
    kwargs = {
        "combo": combo,
        "combo_channel_indices": [c - 1 for c in combo],
        "well_thumbs": well_thumbs,
        "contrast_for_combo": [contrast[c] for c in combo],
        "combo_colors": [COMBO_COLORS[c - 1] for c in combo],
        "channel_names": CHANNEL_NAMES,
        "plate_rows": 2,
        "plate_cols": 3,
        "cell_h": 24,
        "cell_w": 32,
        "plate_id": "SYNTHETIC-PLATE",
        "objective_mag": "20",
        "field_label": "per-well first",
        "timepoint_label": "0",
        "z_label": "all",
        "ffc_label": "on",
        "stitch_fields": False,
        "um_per_thumb_pixel": 1.2,
        "scalebar_um": None,
    }
    moved = tmp_path / "moved.png"
    original = tmp_path / "original.png"
    render_combo_png(outpath=moved, **kwargs)
    legacy._render_combo_png(outpath=original, **kwargs)
    assert moved.read_bytes() == original.read_bytes()
