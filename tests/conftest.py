"""Fixtures over the synthetic plate in ``tests/synthetic.py``."""

from __future__ import annotations

import pytest
from synthetic import (
    CHANNEL_IDS,
    CHANNEL_NAMES,
    FIELDS,
    FULL_HEIGHT,
    FULL_WIDTH,
    PIXEL_SIZE_M,
    PLATE_COLUMNS,
    PLATE_ROWS,
    TIMEPOINTS,
    FakeWellSource,
    make_well,
)

from plate_overview import PlateFacts


@pytest.fixture
def plate_facts() -> PlateFacts:
    """Plate-level facts for the synthetic plate."""
    well_field_map = {
        (row, col): list(FIELDS)
        for row in range(1, PLATE_ROWS + 1)
        for col in range(1, PLATE_COLUMNS + 1)
    }
    return {
        "plate_id": "SYNTHETIC-PLATE",
        "plate_rows": PLATE_ROWS,
        "plate_columns": PLATE_COLUMNS,
        "channel_ids": list(CHANNEL_IDS),
        "channel_names": dict(CHANNEL_NAMES),
        "timepoints": list(TIMEPOINTS),
        "fields": list(FIELDS),
        "well_field_map": well_field_map,
        "image_size": (FULL_HEIGHT, FULL_WIDTH),
        "pixel_size_m": PIXEL_SIZE_M,
        "objective_magnification": "20",
        "channel_colors": {1: "cyan", 2: "magenta"},
        "source_name": "synthetic-run",
    }


@pytest.fixture
def well_source() -> FakeWellSource:
    """A source over six synthetic wells."""
    wells = {
        (row, col): make_well(seed=100 * row + col)
        for row in range(1, PLATE_ROWS + 1)
        for col in range(1, PLATE_COLUMNS + 1)
    }
    return FakeWellSource(wells)
