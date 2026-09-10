"""The gathering loop and the JSON sidecar.

This module owns the pass over the plate. It reads one well, projects
it, downsamples it, and discards the full-resolution array before it
reads the next well. A large mosaic well reaches about 268 MB against a
1 MB thumbnail, so a design that gathers first and renders later needs
tens of gigabytes for a 96-well plate.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
from tqdm import tqdm

from ._colors import resolve_channel_colors
from ._figure import render_combo_png
from ._labels import resolve_field_label, resolve_z_label
from ._port import PlateFacts, WellSource
from ._thumbnails import (
    compute_plate_contrast,
    downsample,
    max_project,
    pad_to_cell,
)

try:
    from ._version import version as __version__
except ImportError:  # pragma: no cover - source tree without metadata
    __version__ = "unknown"

__all__ = ["render_plate_overview"]


def _basename(value: str) -> str:
    """Strip every directory component from *value*.

    The sidecar records a filename, never a path. A sidecar pasted into
    a public issue must not leak a filesystem layout.
    """
    cleaned = str(value).replace("\\", "/").rstrip("/")
    return cleaned.rsplit("/", 1)[-1]


def render_plate_overview(
    source: WellSource,
    plate: PlateFacts,
    output_dir: str | Path,
    *,
    field: int | str | None = None,
    channels: list[int] | None = None,
    timepoint: int | None = None,
    z_slices: int | list[int] | None = None,
    well_px: int = 300,
    contrast_limits: dict[int, tuple[float, float]] | None = None,
    apply_ffc: bool = True,
    scalebar_um: float | None = None,
    verbose: bool = True,
    provenance: Mapping[str, Any] | None = None,
) -> list[Path]:
    """Render plate overview PNGs and a JSON sidecar.

    Writes one PNG per non-empty channel combo (``2**N - 1`` for N
    selected channels) plus a single JSON provenance sidecar. Every PNG
    shares one set of plate-wide per-channel contrast limits, so wells
    are visually comparable.

    Parameters
    ----------
    source : WellSource
        Reads the pixels of one well on demand. See
        :class:`~plate_overview._port.WellSource`.
    plate : PlateFacts
        Plate-level facts. See
        :class:`~plate_overview._port.PlateFacts`.
    output_dir : str or Path
        Directory for the PNGs and the sidecar. Created if it is absent.
    field : int, ``'stitched'``, or None, optional
        Per-well field-choice rule, applied uniformly to every well.
        ``None`` (default) uses each well's first available field.
        ``'stitched'`` stitches all fields. An integer selects that field
        from each well, and skips a well that lacks it.
    channels : list of int, optional
        Channel ids to consider. The combo set comes from this subset.
        ``None`` uses every acquired channel.
    timepoint : int, optional
        Single timepoint to render. ``None`` uses the first timepoint.
    z_slices : int, list of int, or None, optional
        Z planes to read before the max projection. ``None`` reads all.
    well_px : int, default 300
        Per-well render size on the longest side, in pixels.
    contrast_limits : dict, optional
        Optional ``{channel_id: (lo, hi)}`` override. Channels that are
        absent from it fall back to the computed plate-wide value.
        Passing it saves no work — the limits are still computed for the
        sidecar — but the override is applied for rendering.
    apply_ffc : bool, default True
        Ask the source for flat-field correction. A source without
        correction profiles ignores this flag.
    scalebar_um : float, optional
        Scale-bar length in µm. ``None`` (default) picks a nice
        1/2/5×10^k value covering ~25-50 % of one displayed cell. Must
        be positive.
    verbose : bool, default True
        Show a ``tqdm`` progress bar for reading and for rendering.
    provenance : mapping, optional
        Extra keys for the sidecar, for example a consumer's version.
        The keys of this package win on a collision. Do not put a
        filesystem path in it.

    Returns
    -------
    list of Path
        Every file written: the PNGs, then the JSON sidecar.

    Raises
    ------
    ValueError
        If no selected channel was acquired, if *timepoint* was not
        acquired, if *scalebar_um* is not positive, or if the source
        returns an array that is not ``(C, Z, Y, X)``.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if scalebar_um is not None and scalebar_um <= 0:
        raise ValueError(f"scalebar_um must be positive, got {scalebar_um}")

    # Resolve selection.
    all_channels = list(plate["channel_ids"])
    if channels is None:
        sel_channels = all_channels
    else:
        sel_channels = [c for c in channels if c in all_channels]
    if not sel_channels:
        raise ValueError(
            "No selected channels overlap with acquired channels."
        )

    timepoints = list(plate["timepoints"])
    if timepoint is None:
        timepoint = timepoints[0]
    elif timepoint not in timepoints:
        raise ValueError(
            f"timepoint={timepoint} not in acquired timepoints {timepoints}"
        )

    stitch_fields = field == "stitched"
    fixed_field: int | None = None
    if not stitch_fields and field is not None:
        fixed_field = int(field)

    if isinstance(z_slices, int):
        z_arg: list[int] | None = [z_slices]
    else:
        z_arg = z_slices

    plate_fields = list(plate["fields"])
    well_field_map = plate["well_field_map"]

    # Single pass over wells: read → max-project Z → downsample → store.
    available_wells = sorted(well_field_map)
    well_thumbs: dict[tuple[int, int], np.ndarray] = {}

    iterator = available_wells
    if verbose:
        iterator = tqdm(available_wells, desc="Reading wells")

    for row, col in iterator:
        if stitch_fields:
            use_field = None
            use_stitch = True
        else:
            wfields = well_field_map.get((row, col), plate_fields)
            if fixed_field is not None:
                if fixed_field not in wfields:
                    continue
                use_field = fixed_field
            else:
                use_field = wfields[0] if wfields else plate_fields[0]
            use_stitch = False

        arr = source.read_well(
            row=row,
            column=col,
            field=use_field,
            stitch_fields=use_stitch,
            timepoint=timepoint,
            channels=sel_channels,
            z_slices=z_arg,
            apply_ffc=apply_ffc,
        )
        arr = np.asarray(arr)
        if arr.ndim != 4:
            raise ValueError(
                "WellSource.read_well must return a (C, Z, Y, X) array; "
                f"well {(row, col)} returned shape {arr.shape}"
            )
        thumb = downsample(max_project(arr), well_px)
        well_thumbs[(row, col)] = thumb

    # Cell size = largest thumb we got (cells get zero-padded to this).
    if well_thumbs:
        cell_h = max(t.shape[1] for t in well_thumbs.values())
        cell_w = max(t.shape[2] for t in well_thumbs.values())
    else:
        cell_h = cell_w = well_px
    pad_to_cell(well_thumbs, cell_h, cell_w)

    # Plate-wide contrast limits — always computed for the sidecar.
    computed_contrast = compute_plate_contrast(well_thumbs, sel_channels)
    rendering_contrast: dict[int, tuple[float, float]] = dict(
        computed_contrast
    )
    if contrast_limits:
        for ch_id, lh in contrast_limits.items():
            if ch_id in rendering_contrast:
                rendering_contrast[ch_id] = (float(lh[0]), float(lh[1]))

    # Channel colors for merges; singletons always use viridis.
    all_names = plate["channel_names"]
    channel_names = {
        ch_id: all_names.get(ch_id, "?") for ch_id in sel_channels
    }
    ch_colors = resolve_channel_colors(
        sel_channels, plate.get("channel_colors")
    )

    # Effective µm per thumb pixel — derived from one well's downsample.
    image_size = plate["image_size"]
    if image_size and well_thumbs:
        any_thumb = next(iter(well_thumbs.values()))
        # In first-field mode the thumb matches the single-field
        # downsample; in stitched mode this underestimates effective
        # µm/pixel slightly (still adequate for a diagnostic scale bar).
        thumb_long = max(any_thumb.shape[1], any_thumb.shape[2])
        full_long = max(image_size[0], image_size[1])
        downsample_factor = full_long / thumb_long if thumb_long else 1.0
    else:
        downsample_factor = 1.0
    pixel_size_m = plate["pixel_size_m"]
    um_per_full_px = pixel_size_m[1] * 1e6
    um_per_thumb_pixel = um_per_full_px * downsample_factor

    objective_mag = plate.get("objective_magnification")
    field_label = resolve_field_label(field, stitch_fields, fixed_field)
    timepoint_label = str(timepoint)
    z_label = resolve_z_label(z_slices)
    ffc_label = "on" if apply_ffc else "off"

    plate_id = plate["plate_id"]
    written: list[Path] = []
    n = len(sel_channels)

    combos_iter = []
    for k in range(1, n + 1):
        for combo in combinations(sel_channels, k):
            combos_iter.append(combo)

    if verbose:
        combos_iter_display = tqdm(combos_iter, desc="Rendering combos")
    else:
        combos_iter_display = combos_iter

    for combo in combos_iter_display:
        is_all = len(combo) == n
        if len(combo) == 1:
            fname = f"{plate_id}_overview_ch{combo[0]}.png"
        elif is_all:
            fname = f"{plate_id}_overview_merge_all.png"
        else:
            fname = (
                f"{plate_id}_overview_"
                + "+".join(f"ch{c}" for c in combo)
                + ".png"
            )
        outpath = output_dir / fname
        combo_channel_indices = [sel_channels.index(c) for c in combo]
        contrast_for_combo = [rendering_contrast[c] for c in combo]
        combo_colors = [ch_colors[c] for c in combo]
        render_combo_png(
            combo=combo,
            combo_channel_indices=combo_channel_indices,
            well_thumbs=well_thumbs,
            contrast_for_combo=contrast_for_combo,
            combo_colors=combo_colors,
            channel_names=channel_names,
            plate_rows=plate["plate_rows"],
            plate_cols=plate["plate_columns"],
            cell_h=cell_h,
            cell_w=cell_w,
            plate_id=plate_id,
            objective_mag=objective_mag,
            field_label=field_label,
            timepoint_label=timepoint_label,
            z_label=z_label,
            ffc_label=ffc_label,
            stitch_fields=stitch_fields,
            um_per_thumb_pixel=um_per_thumb_pixel,
            scalebar_um=scalebar_um,
            outpath=outpath,
        )
        written.append(outpath)

    # JSON sidecar. The keys below win over anything in *provenance*.
    sidecar: dict[str, Any] = dict(provenance or {})
    sidecar.update(
        {
            "plate_overview_version": __version__,
            "plate_id": plate_id,
            "source_name": _basename(plate.get("source_name", "")),
            "parameters": {
                "field": field,
                "channels": sel_channels,
                "timepoint": timepoint,
                "z_slices": z_slices,
                "well_px": well_px,
                "apply_ffc": apply_ffc,
                "scalebar_um": scalebar_um,
                "contrast_limits_override": (
                    {str(k): list(v) for k, v in contrast_limits.items()}
                    if contrast_limits
                    else None
                ),
            },
            "plate_layout": {
                "rows": plate["plate_rows"],
                "columns": plate["plate_columns"],
            },
            "plate_contrast_limits": {
                str(k): [float(v[0]), float(v[1])]
                for k, v in computed_contrast.items()
            },
            "rendering_contrast_limits": {
                str(k): [float(v[0]), float(v[1])]
                for k, v in rendering_contrast.items()
            },
            "channel_colormaps": {str(k): v for k, v in ch_colors.items()},
            "channel_names": {str(k): v for k, v in channel_names.items()},
            "pixel_size_m": [
                float(pixel_size_m[0]),
                float(pixel_size_m[1]),
            ],
            "um_per_thumb_pixel": float(um_per_thumb_pixel),
            "objective_magnification": objective_mag,
            "output_files": [p.name for p in written],
        }
    )
    json_path = output_dir / f"{plate_id}_overview.json"
    json_path.write_text(json.dumps(sidecar, indent=2))
    written.append(json_path)

    return written
