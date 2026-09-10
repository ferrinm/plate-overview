"""Text that goes on the figure.

Every label states a rendering choice. A reader of the PNG must be able
to tell which field, timepoint, Z rule and correction produced it,
without the sidecar.
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "combo_label",
    "nice_scalebar_length_um",
    "options_label",
    "resolve_field_label",
    "resolve_z_label",
    "row_letter",
]


def nice_scalebar_length_um(visible_um: float) -> float:
    """Pick a 1/2/5×10^k value covering ~25-50 % of ``visible_um``."""
    if visible_um <= 0:
        return 1.0
    target = visible_um * 0.4
    exp = np.floor(np.log10(target))
    base = target / (10**exp)
    if base < 1.5:
        nice = 1.0
    elif base < 3.5:
        nice = 2.0
    elif base < 7.5:
        nice = 5.0
    else:
        nice = 10.0
    return nice * (10**exp)


def row_letter(row: int) -> str:
    """1-based row index → ``'A'``, ``'B'``, …, ``'P'`` (with 'I' kept)."""
    if row < 1 or row > 26:
        return str(row)
    return chr(ord("A") + row - 1)


def resolve_field_label(
    field: int | str | None,
    stitch_fields: bool,
    fixed_field: int | None,
) -> str:
    """Human-readable description of the field-selection rule applied."""
    if stitch_fields:
        return "stitched"
    if fixed_field is not None:
        return str(fixed_field)
    return "per-well first"


def resolve_z_label(z_slices: int | list[int] | None) -> str:
    """Human-readable description of the Z-plane selection applied."""
    if z_slices is None:
        return "all"
    if isinstance(z_slices, int):
        return f"[{z_slices}]"
    return str(list(z_slices))


def combo_label(
    combo: tuple[int, ...],
    channel_names: dict[int, str],
    total_channel_count: int,
) -> str:
    """Channel-combo description used in the per-PNG subtitle."""
    if len(combo) == 1:
        ch_id = combo[0]
        return f"Ch{ch_id}: {channel_names.get(ch_id, '?')}"
    if len(combo) == total_channel_count:
        return "Merge: all channels"
    return "Merge: " + " + ".join(f"Ch{c}" for c in combo)


def options_label(
    *,
    objective_mag: str | None,
    field_label: str,
    timepoint_label: str,
    z_label: str,
    ffc_label: str,
) -> str:
    """Single-line summary of the rendering options applied."""
    parts: list[str] = []
    if objective_mag:
        parts.append(f"Objective: {objective_mag}×")
    parts.append(f"Field: {field_label}")
    parts.append(f"T: {timepoint_label}")
    parts.append(f"Z: {z_label}")
    parts.append(f"FFC: {ffc_label}")
    return " · ".join(parts)
