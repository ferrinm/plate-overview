"""Tests for the pixel pipeline: project, downsample, contrast, scale."""

from __future__ import annotations

import numpy as np
import pytest

from plate_overview._thumbnails import (
    compute_plate_contrast,
    downsample,
    max_project,
    normalize,
    pad_to_cell,
)


def test_max_project_takes_the_brightest_plane_per_pixel():
    arr = np.zeros((2, 3, 4, 5), dtype=np.uint16)
    arr[0, 1, 2, 3] = 7
    arr[1, 2, 0, 0] = 9
    projected = max_project(arr)
    assert projected.shape == (2, 4, 5)
    assert projected[0, 2, 3] == 7
    assert projected[1, 0, 0] == 9


def test_downsample_scales_the_longest_side_to_the_target():
    arr = np.ones((2, 40, 80), dtype=np.uint16)
    out = downsample(arr, 20)
    assert out.shape == (2, 10, 20)
    assert out.dtype == np.float32


def test_downsample_leaves_a_small_array_alone():
    arr = np.arange(2 * 4 * 6, dtype=np.uint16).reshape(2, 4, 6)
    out = downsample(arr, 100)
    assert out.shape == arr.shape
    np.testing.assert_array_equal(out, arr.astype(np.float32))


def test_downsample_averages_the_block_it_replaces():
    """Block mean, not nearest neighbor.

    A 2×2 block of 0, 0, 0, 4 must become 1. Nearest neighbor would
    return 0 or 4, and that shifts the plate contrast.
    """
    arr = np.zeros((1, 2, 2), dtype=np.float32)
    arr[0, 1, 1] = 4.0
    out = downsample(arr, 1)
    assert out.shape == (1, 1, 1)
    assert out[0, 0, 0] == pytest.approx(1.0)


def test_pad_to_cell_pads_short_thumbnails_with_zeros():
    thumbs = {
        (1, 1): np.ones((2, 4, 4), dtype=np.float32),
        (1, 2): np.ones((2, 2, 3), dtype=np.float32),
    }
    pad_to_cell(thumbs, 4, 4)
    assert thumbs[(1, 1)].shape == (2, 4, 4)
    assert thumbs[(1, 2)].shape == (2, 4, 4)
    assert thumbs[(1, 2)][0, 3, 3] == 0.0
    assert thumbs[(1, 2)][0, 0, 0] == 1.0


def test_plate_contrast_pools_every_well():
    """One limit per channel, over the whole plate.

    A bright well must raise the limit that a dim well is drawn with.
    Otherwise the two wells are not comparable by eye.
    """
    dim = np.full((1, 10, 10), 10.0, dtype=np.float32)
    bright = np.full((1, 10, 10), 1000.0, dtype=np.float32)
    limits = compute_plate_contrast({(1, 1): dim, (1, 2): bright}, [1])
    lo, hi = limits[1]
    assert lo == 0.0
    assert hi > 900.0


def test_plate_contrast_ignores_zero_pixels():
    """Zero padding must not drag the percentile down."""
    thumb = np.zeros((1, 10, 10), dtype=np.float32)
    thumb[0, :2, :] = 500.0
    limits = compute_plate_contrast({(1, 1): thumb}, [1])
    assert limits[1][1] == pytest.approx(500.0)


def test_plate_contrast_falls_back_when_there_is_nothing_to_measure():
    assert compute_plate_contrast({}, [1, 2]) == {1: (0.0, 1.0), 2: (0.0, 1.0)}
    empty = {(1, 1): np.zeros((1, 4, 4), dtype=np.float32)}
    assert compute_plate_contrast(empty, [1]) == {1: (0.0, 1.0)}


def test_normalize_maps_the_range_and_clips_outside_it():
    arr = np.array([-5.0, 0.0, 5.0, 10.0, 20.0], dtype=np.float32)
    out = normalize(arr, 0.0, 10.0)
    np.testing.assert_allclose(out, [0.0, 0.0, 0.5, 1.0, 1.0])


def test_normalize_returns_zeros_for_an_empty_range():
    arr = np.array([1.0, 2.0], dtype=np.float32)
    np.testing.assert_array_equal(normalize(arr, 5.0, 5.0), [0.0, 0.0])
