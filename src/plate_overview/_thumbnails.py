"""From one well of pixels to one comparable thumbnail.

Every step here runs once, inside this package. A consumer that
projects or resamples first produces different pixel values, and
different pixel values produce different plate contrast.
"""

from __future__ import annotations

import numpy as np
from PIL import Image as PILImage

__all__ = [
    "compute_plate_contrast",
    "downsample",
    "max_project",
    "normalize",
    "pad_to_cell",
]


def max_project(arr: np.ndarray) -> np.ndarray:
    """Max-project the Z axis of a ``(C, Z, Y, X)`` array → ``(C, Y, X)``."""
    return arr.max(axis=1)


def downsample(arr: np.ndarray, target_long: int) -> np.ndarray:
    """Block-mean downsample so the longest side ≤ ``target_long``.

    Parameters
    ----------
    arr : np.ndarray
        Shape ``(C, H, W)``, any numeric dtype.
    target_long : int
        Target pixel count on the longest side.

    Returns
    -------
    np.ndarray
        Shape ``(C, h, w)`` float32 with ``max(h, w) ≈ target_long``.
    """
    C, H, W = arr.shape
    long_side = max(H, W)
    if long_side <= target_long:
        return arr.astype(np.float32)
    scale = target_long / long_side
    new_h = max(1, int(round(H * scale)))
    new_w = max(1, int(round(W * scale)))
    out = np.zeros((C, new_h, new_w), dtype=np.float32)
    for c in range(C):
        img = PILImage.fromarray(arr[c].astype(np.float32), mode="F")
        out[c] = np.asarray(img.resize((new_w, new_h), PILImage.BOX))
    return out


def pad_to_cell(
    well_thumbs: dict[tuple[int, int], np.ndarray],
    cell_h: int,
    cell_w: int,
) -> None:
    """Zero-pad every thumbnail to ``(cell_h, cell_w)``, in place.

    Wells with fewer fields produce smaller thumbnails. The grid places
    every cell at the same pitch, so the short ones need padding.
    """
    for key, thumb in list(well_thumbs.items()):
        C, h, w = thumb.shape
        if h == cell_h and w == cell_w:
            continue
        padded = np.zeros((C, cell_h, cell_w), dtype=thumb.dtype)
        padded[:, :h, :w] = thumb
        well_thumbs[key] = padded


def compute_plate_contrast(
    well_thumbs: dict[tuple[int, int], np.ndarray],
    channels: list[int],
) -> dict[int, tuple[float, float]]:
    """Per-channel ``[0, p99.5]`` over non-zero downsampled pixels.

    One limit per channel, pooled over the whole plate. That is what
    makes the apparent brightness of a well mean something relative to
    its neighbors.

    The percentile runs on the downsampled, max-projected pixels the
    renderer already holds. See
    ``docs/adr/0001-plate-wide-contrast-on-downsampled-pixels.md``.
    """
    limits: dict[int, tuple[float, float]] = {}
    for ch_idx, ch_id in enumerate(channels):
        if not well_thumbs:
            limits[ch_id] = (0.0, 1.0)
            continue
        pooled = np.concatenate(
            [t[ch_idx].ravel() for t in well_thumbs.values()]
        )
        nonzero = pooled[pooled > 0]
        if nonzero.size:
            limits[ch_id] = (0.0, float(np.percentile(nonzero, 99.5)))
        else:
            limits[ch_id] = (0.0, 1.0)
    return limits


def normalize(arr: np.ndarray, lo: float, hi: float) -> np.ndarray:
    """Linearly map ``[lo, hi]`` to ``[0, 1]`` with clipping."""
    span = hi - lo
    if span <= 0:
        return np.zeros_like(arr, dtype=np.float32)
    return np.clip((arr.astype(np.float32) - lo) / span, 0.0, 1.0)
