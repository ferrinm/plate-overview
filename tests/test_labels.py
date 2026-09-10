"""Tests for the text on the figure."""

from __future__ import annotations

import pytest

from plate_overview._labels import (
    combo_label,
    nice_scalebar_length_um,
    options_label,
    resolve_field_label,
    resolve_z_label,
    row_letter,
)


@pytest.mark.parametrize(
    ("row", "expected"),
    [(1, "A"), (8, "H"), (9, "I"), (16, "P"), (26, "Z"), (27, "27")],
)
def test_row_letter(row, expected):
    assert row_letter(row) == expected


@pytest.mark.parametrize(
    ("visible_um", "expected"),
    [
        (0.0, 1.0),
        (-1.0, 1.0),
        (1000.0, 500.0),
        (500.0, 200.0),
        (250.0, 100.0),
        (2600.0, 1000.0),
    ],
)
def test_nice_scalebar_length_is_a_round_number(visible_um, expected):
    assert nice_scalebar_length_um(visible_um) == pytest.approx(expected)


def test_nice_scalebar_length_covers_a_readable_fraction():
    visible = 837.0
    bar = nice_scalebar_length_um(visible)
    assert 0.2 * visible <= bar <= 0.6 * visible


def test_field_label_states_the_rule_that_was_applied():
    assert resolve_field_label(None, False, None) == "per-well first"
    assert resolve_field_label("stitched", True, None) == "stitched"
    assert resolve_field_label(3, False, 3) == "3"


def test_z_label_states_the_planes_that_were_read():
    assert resolve_z_label(None) == "all"
    assert resolve_z_label(4) == "[4]"
    assert resolve_z_label([0, 1, 2]) == "[0, 1, 2]"


def test_combo_label_names_one_channel():
    names = {1: "ChannelOne", 2: "ChannelTwo"}
    assert combo_label((1,), names, 2) == "Ch1: ChannelOne"


def test_combo_label_calls_a_full_merge_by_its_name():
    names = {1: "ChannelOne", 2: "ChannelTwo"}
    assert combo_label((1, 2), names, 2) == "Merge: all channels"


def test_combo_label_lists_a_partial_merge():
    names = {1: "ChannelOne", 2: "ChannelTwo", 3: "ChannelThree"}
    assert combo_label((1, 3), names, 3) == "Merge: Ch1 + Ch3"


def test_options_label_lists_every_rendering_choice():
    label = options_label(
        objective_mag="20",
        field_label="stitched",
        timepoint_label="0",
        z_label="all",
        ffc_label="on",
    )
    assert label == (
        "Objective: 20× · Field: stitched · T: 0 · Z: all · FFC: on"
    )


def test_options_label_drops_an_unknown_objective():
    label = options_label(
        objective_mag=None,
        field_label="1",
        timepoint_label="0",
        z_label="all",
        ffc_label="off",
    )
    assert label.startswith("Field: 1")
    assert "Objective" not in label
