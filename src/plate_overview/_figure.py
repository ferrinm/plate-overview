"""The figure itself: one PNG for one channel combo.

The figure is built against the Agg canvas, not through ``pyplot``. A
plate is rendered on a cluster, where a backend that looks for a display
either fails or drags in a GUI toolkit. Agg does neither, and it holds
no global figure registry to leak.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.colorbar import ColorbarBase
from matplotlib.colors import Normalize
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle

from ._colors import named_cmap, rgb_for
from ._labels import (
    combo_label,
    nice_scalebar_length_um,
    options_label,
    row_letter,
)
from ._thumbnails import normalize

__all__ = ["render_cell", "render_combo_png"]


def render_cell(
    thumb: np.ndarray,
    combo_channel_indices: list[int],
    contrast: list[tuple[float, float]],
    combo_colors: list[str],
    is_singleton: bool,
) -> np.ndarray:
    """Render a single well's thumbnail for one channel combo.

    Returns an ``(h, w, 3)`` RGB float32 array in ``[0, 1]``.
    """
    h, w = thumb.shape[1:]
    if is_singleton:
        ch_idx = combo_channel_indices[0]
        lo, hi = contrast[0]
        norm = normalize(thumb[ch_idx], lo, hi)
        viridis = matplotlib.colormaps["viridis"]
        return viridis(norm)[..., :3].astype(np.float32)

    rgb = np.zeros((h, w, 3), dtype=np.float32)
    for ch_idx, (lo, hi), color in zip(
        combo_channel_indices, contrast, combo_colors, strict=True
    ):
        norm = normalize(thumb[ch_idx], lo, hi)
        r, g, b = rgb_for(color)
        rgb[..., 0] += norm * r
        rgb[..., 1] += norm * g
        rgb[..., 2] += norm * b
    return np.clip(rgb, 0.0, 1.0)


def render_combo_png(
    *,
    combo: tuple[int, ...],
    combo_channel_indices: list[int],
    well_thumbs: dict[tuple[int, int], np.ndarray],
    contrast_for_combo: list[tuple[float, float]],
    combo_colors: list[str],
    channel_names: dict[int, str],
    plate_rows: int,
    plate_cols: int,
    cell_h: int,
    cell_w: int,
    plate_id: str,
    objective_mag: str | None,
    field_label: str,
    timepoint_label: str,
    z_label: str,
    ffc_label: str,
    stitch_fields: bool,
    um_per_thumb_pixel: float,
    scalebar_um: float | None,
    outpath: Path,
) -> None:
    """Render and save one PNG for one channel combo."""
    is_singleton = len(combo) == 1

    # Stitch all wells into one big RGB image.
    H = plate_rows * cell_h
    W = plate_cols * cell_w
    canvas = np.zeros((H, W, 3), dtype=np.float32)
    for (row, col), thumb in well_thumbs.items():
        if row < 1 or row > plate_rows or col < 1 or col > plate_cols:
            continue
        rgb = render_cell(
            thumb,
            combo_channel_indices,
            contrast_for_combo,
            combo_colors,
            is_singleton,
        )
        h, w = rgb.shape[:2]
        h = min(h, cell_h)
        w = min(w, cell_w)
        y0 = (row - 1) * cell_h
        x0 = (col - 1) * cell_w
        canvas[y0 : y0 + h, x0 : x0 + w] = rgb[:h, :w]

    # Figure layout in inches → fig fractions. The plate-image axis is
    # sized so its pixel dimensions at the chosen dpi match the canvas,
    # i.e. well_px actually controls the output PNG resolution. All
    # layout and font sizes scale uniformly with the canvas so a large
    # plate produces a proportionally bigger image (not a small-text one).
    # Baseline = 7" canvas → scale 1, matching prior 8"-figure look.
    n_combo = len(combo)
    dpi = 150
    axis_w_in = (plate_cols * cell_w) / dpi
    axis_h_in = (plate_rows * cell_h) / dpi
    scale = max(1.0, axis_w_in / 7.0)

    margin_left = 0.7 * scale
    # margin_right has to fit the colorbar tick labels and rotated channel
    # label that hang off the right side of each cb axis.
    margin_right = 0.7 * scale
    margin_top = 0.95 * scale
    margin_bottom = 0.5 * scale
    colorbar_w = 0.18 * scale
    scalebar_h = 0.55 * scale
    hgap = 0.2 * scale
    vgap = 0.2 * scale
    title_fs = 11 * scale
    subtitle_fs = 9 * scale
    tick_fs = 7 * scale
    cb_tick_fs = 6 * scale
    cb_label_fs = 7 * scale
    scalebar_fs = 7 * scale
    fig_w = max(
        8.0, margin_left + axis_w_in + hgap + colorbar_w + margin_right
    )
    fig_h = max(
        6.0, margin_top + axis_h_in + vgap + scalebar_h + margin_bottom
    )
    # When the minimums kicked in, expand the axis up to whatever the
    # canvas aspect ratio allows so wells stay visually square.
    avail_w = fig_w - (margin_left + hgap + colorbar_w + margin_right)
    avail_h = fig_h - (margin_top + vgap + scalebar_h + margin_bottom)
    canvas_aspect = (plate_rows * cell_h) / (plate_cols * cell_w)
    if avail_w * canvas_aspect <= avail_h:
        real_axis_w, real_axis_h = avail_w, avail_w * canvas_aspect
    else:
        real_axis_w, real_axis_h = avail_h / canvas_aspect, avail_h

    fig = Figure(figsize=(fig_w, fig_h), dpi=dpi)
    FigureCanvasAgg(fig)

    ax_left = margin_left / fig_w
    ax_bottom = (margin_bottom + scalebar_h + vgap) / fig_h
    ax_w_frac = real_axis_w / fig_w
    ax_h_frac = real_axis_h / fig_h
    ax = fig.add_axes([ax_left, ax_bottom, ax_w_frac, ax_h_frac])
    ax.imshow(canvas, interpolation="nearest", origin="upper", aspect="auto")

    # Column ticks on top: 1..plate_cols at cell centers.
    col_positions = [(c - 0.5) * cell_w for c in range(1, plate_cols + 1)]
    ax.set_xticks(col_positions)
    ax.set_xticklabels(
        [str(c) for c in range(1, plate_cols + 1)], fontsize=tick_fs
    )
    ax.xaxis.set_ticks_position("top")
    ax.xaxis.set_label_position("top")

    # Row ticks on left: A..letter(plate_rows).
    row_positions = [(r - 0.5) * cell_h for r in range(1, plate_rows + 1)]
    ax.set_yticks(row_positions)
    ax.set_yticklabels(
        [row_letter(r) for r in range(1, plate_rows + 1)], fontsize=tick_fs
    )
    ax.tick_params(axis="both", length=0)

    # Subtle gridlines between cells.
    for c in range(plate_cols + 1):
        ax.axvline(c * cell_w - 0.5, color="white", linewidth=0.3, alpha=0.3)
    for r in range(plate_rows + 1):
        ax.axhline(r * cell_h - 0.5, color="white", linewidth=0.3, alpha=0.3)
    ax.set_xlim(-0.5, plate_cols * cell_w - 0.5)
    ax.set_ylim(plate_rows * cell_h - 0.5, -0.5)
    ax.set_facecolor("black")
    for spine in ax.spines.values():
        spine.set_visible(False)

    # Single-line subtitle: channel combo + all user-controllable
    # rendering options, separated by middle dots. Inch-based y-positions
    # keep the gap to the plate axis constant across figure sizes.
    title_combo = combo_label(combo, channel_names, len({*channel_names}))
    options_line = options_label(
        objective_mag=objective_mag,
        field_label=field_label,
        timepoint_label=timepoint_label,
        z_label=z_label,
        ffc_label=ffc_label,
    )
    subtitle = f"{title_combo}  ·  {options_line}"
    fig.text(
        0.5,
        1 - (0.3 * scale) / fig_h,
        plate_id,
        ha="center",
        fontsize=title_fs,
        fontweight="bold",
    )
    fig.text(
        0.5,
        1 - (0.62 * scale) / fig_h,
        subtitle,
        ha="center",
        fontsize=subtitle_fs,
        color="gray",
    )

    # Colorbar column on the right: one per channel in combo, top → bottom.
    cb_x = (margin_left + real_axis_w + hgap) / fig_w
    cb_w_frac = colorbar_w / fig_w
    cb_gap_in = 0.35 * scale
    sub_h_in = (real_axis_h - (n_combo - 1) * cb_gap_in) / n_combo
    ax_top_in = margin_bottom + scalebar_h + vgap + real_axis_h
    for i, ch_id in enumerate(combo):
        sub_top_in = ax_top_in - i * (sub_h_in + cb_gap_in)
        sub_bottom_in = sub_top_in - sub_h_in
        cax = fig.add_axes(
            [cb_x, sub_bottom_in / fig_h, cb_w_frac, sub_h_in / fig_h]
        )
        lo, hi = contrast_for_combo[i]
        if is_singleton:
            cmap = matplotlib.colormaps["viridis"]
        else:
            cmap = named_cmap(combo_colors[i])
        norm = Normalize(vmin=lo, vmax=hi)
        cb = ColorbarBase(cax, cmap=cmap, norm=norm, orientation="vertical")
        cb.ax.tick_params(labelsize=cb_tick_fs)
        cb.set_label(
            f"Ch{ch_id}: {channel_names.get(ch_id, '?')}",
            fontsize=cb_label_fs,
        )

    # Scale bar below the plate (in µm). Length: nice 1/2/5×10^k value
    # covering ~20 % of one well's visible width.
    sb_ax = fig.add_axes(
        [ax_left, margin_bottom / fig_h, ax_w_frac, scalebar_h / fig_h]
    )
    # xlim spans the full plate width so 1 thumb pixel here = 1 thumb pixel
    # on the plate axis above; the drawn bar length is then proportionally
    # correct against the cells.
    sb_ax.set_xlim(0, plate_cols * cell_w)
    sb_ax.set_ylim(0, 1)
    sb_ax.axis("off")
    # Each grid cell shows one field (single-field mode) or one well's
    # fields stitched together (stitched mode).
    cell_visible_um = cell_w * um_per_thumb_pixel
    bar_um = (
        scalebar_um
        if scalebar_um is not None
        else nice_scalebar_length_um(cell_visible_um)
    )
    bar_thumb_px = bar_um / um_per_thumb_pixel if um_per_thumb_pixel > 0 else 0
    sb_ax.add_patch(Rectangle((0, 0.78), bar_thumb_px, 0.12, color="black"))
    cell_descriptor = (
        "one fully stitched well" if stitch_fields else "one field"
    )
    # Bar length centered under the bar; spatial reference below it, also
    # centered under the bar (will overflow when bar is much shorter than
    # the descriptor text — acceptable since the scalebar axis spans the
    # whole plate width).
    sb_ax.text(
        bar_thumb_px / 2,
        0.55,
        f"{bar_um:g} µm",
        ha="center",
        va="center",
        fontsize=scalebar_fs,
    )
    sb_ax.text(
        bar_thumb_px / 2,
        0.20,
        f"{cell_descriptor} ≈ {cell_visible_um:.0f} µm",
        ha="center",
        va="center",
        fontsize=scalebar_fs,
        color="gray",
    )

    fig.savefig(outpath, dpi=dpi, facecolor="white")
