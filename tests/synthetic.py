"""Synthetic plate data.

No fixture in this repository derives from a real acquisition. Every
array here comes from a seeded random generator, and every identifier is
invented.
"""

from __future__ import annotations

import numpy as np

# A small synthetic plate. The numbers are deliberately tiny so the
# whole suite renders in seconds.
PLATE_ROWS = 2
PLATE_COLUMNS = 3
CHANNEL_IDS = [1, 2]
CHANNEL_NAMES = {1: "ChannelOne", 2: "ChannelTwo"}
FIELDS = [1, 2]
TIMEPOINTS = [0, 1]
FULL_HEIGHT = 48
FULL_WIDTH = 64
Z_PLANES = 3
PIXEL_SIZE_M = (3.0e-07, 3.0e-07)


class FakeWellSource:
    """A :class:`plate_overview.WellSource` over arrays held in memory.

    It records every call, so a test can assert on what the gathering
    loop asked for.
    """

    def __init__(
        self,
        wells: dict[tuple[int, int], np.ndarray],
        channel_ids: list[int] | None = None,
    ) -> None:
        self.wells = wells
        self.channel_ids = list(channel_ids or CHANNEL_IDS)
        self.calls: list[dict] = []

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
        self.calls.append(
            {
                "row": row,
                "column": column,
                "field": field,
                "stitch_fields": stitch_fields,
                "timepoint": timepoint,
                "channels": list(channels),
                "z_slices": z_slices,
                "apply_ffc": apply_ffc,
            }
        )
        data = self.wells[(row, column)]
        picked = [self.channel_ids.index(c) for c in channels]
        data = data[picked]
        if z_slices is not None:
            data = data[:, list(z_slices)]
        return data


def make_well(seed: int, channels: int = 2) -> np.ndarray:
    """One synthetic well, shape ``(C, Z, Y, X)``, uint16."""
    rng = np.random.default_rng(seed)
    return rng.integers(
        0,
        4000,
        size=(channels, Z_PLANES, FULL_HEIGHT, FULL_WIDTH),
        dtype=np.uint16,
    )
