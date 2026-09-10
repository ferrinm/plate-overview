"""The render port.

A consumer supplies two things:

- :class:`PlateFacts`, a normalized dict of plate-level facts.
- :class:`WellSource`, one method that reads the pixels of one well.

The port is narrow on purpose. It is not a reader interface. It carries
render-time facts only, and it leaves out the analysis-time members that
a reader carries. A single merged interface would be satisfied honestly
by neither side.
"""

from __future__ import annotations

from typing import Protocol, TypedDict, runtime_checkable

import numpy as np

__all__ = ["PlateFacts", "WellSource"]


class _RequiredPlateFacts(TypedDict):
    """The plate facts that every consumer must supply."""

    plate_id: str
    plate_rows: int
    plate_columns: int
    channel_ids: list[int]
    channel_names: dict[int, str]
    timepoints: list[int]
    fields: list[int]
    well_field_map: dict[tuple[int, int], list[int]]
    image_size: tuple[int, int]
    pixel_size_m: tuple[float, float]


class PlateFacts(_RequiredPlateFacts, total=False):
    """Plate-level facts, normalized away from any acquisition format.

    Required keys
    -------------
    plate_id : str
        Plate name. It titles every PNG and prefixes every filename.
        Keep operator names and real specimen identifiers out of it.
    plate_rows : int
        Number of rows in the plate geometry, for example 8.
    plate_columns : int
        Number of columns in the plate geometry, for example 12.
    channel_ids : list of int
        Every acquired channel id, in ascending order.
    channel_names : dict
        ``{channel_id: name}`` for every id in *channel_ids*.
    timepoints : list of int
        Every acquired timepoint id, in ascending order.
    fields : list of int
        Every acquired field id, in ascending order. This is the
        plate-wide set. A single well can hold a subset of it.
    well_field_map : dict
        ``{(row, column): [field_id, ...]}`` with 1-based row and column
        numbers. The keys of this map are the wells that hold data, so
        the renderer visits exactly these wells.
    image_size : tuple of int
        Full-resolution size of one field, as ``(height, width)`` in
        pixels. The renderer divides it by the thumbnail size to derive
        the scale bar.
    pixel_size_m : tuple of float
        Physical pixel pitch as ``(height, width)`` in meters.

    Optional keys
    -------------
    objective_magnification : str or None
        Objective magnification, for example ``"20"``. It appears in the
        subtitle. Omit it and the subtitle omits the field.
    channel_colors : dict
        ``{channel_id: color_name}`` for merge compositing. See
        :data:`plate_overview._colors.COLOR_RGB` for the accepted names.
        Omit it and the renderer assigns colors by channel order.
    source_name : str
        Name of the acquisition the pixels come from. The JSON sidecar
        records the basename of this value, never a directory path.
    """

    objective_magnification: str | None
    channel_colors: dict[int, str]
    source_name: str


@runtime_checkable
class WellSource(Protocol):
    """One well of pixels, read on demand.

    The renderer calls :meth:`read_well` once per well, downsamples the
    result, and then discards it. A large mosaic well reaches about
    268 MB against a 1 MB thumbnail, so the renderer never holds two
    full-resolution wells at once. An adapter must therefore read on
    demand. It must not pre-load the plate.
    """

    def read_well(
        self,
        *,
        row: int,
        column: int,
        field: int | None,
        stitch_fields: bool,
        timepoint: int,
        channels: list[int],
        z_slices: list[int] | None,
        apply_ffc: bool,
    ) -> np.ndarray:
        """Read the pixels of one well.

        Parameters
        ----------
        row : int
            1-based plate row.
        column : int
            1-based plate column.
        field : int or None
            Field to read. ``None`` means every field, and the renderer
            passes it only together with ``stitch_fields=True``.
        stitch_fields : bool
            If true, stitch every field of the well into one image.
        timepoint : int
            Single timepoint to read.
        channels : list of int
            Channel ids to read, in the order the renderer expects them
            on the returned C axis.
        z_slices : list of int or None
            Z planes to read. ``None`` means every plane.
        apply_ffc : bool
            If true, apply flat-field correction. An adapter without
            correction profiles ignores this flag.

        Returns
        -------
        np.ndarray
            Shape ``(C, Z, Y, X)``, any numeric dtype. C matches
            *channels*. An adapter without a Z axis returns ``Z == 1``.
            Return the pixels at full resolution. The renderer
            downsamples them. An adapter that resamples first shifts the
            plate contrast, which is the divergence this package exists
            to prevent.
        """
        ...
