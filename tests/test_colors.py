"""Tests for channel colors and cell compositing."""

from __future__ import annotations

import matplotlib
import numpy as np
import pytest

from plate_overview._colors import (
    COLOR_LADDER_NM,
    DEFAULT_CHANNEL_COLORS,
    FLUOROPHORE_COLORS,
    MAX_WAVELENGTH_NM,
    MIN_WAVELENGTH_NM,
    base_boundaries_nm,
    fluorophore_color,
    named_cmap,
    parse_wavelength_nm,
    resolve_channel_colors,
    rgb_for,
)
from plate_overview._figure import render_cell


def test_a_known_color_name_maps_to_its_tip():
    assert rgb_for("Magenta") == (1.0, 0.0, 1.0)


def test_an_unknown_color_name_falls_back_to_white():
    assert rgb_for("chartreuse") == (1.0, 1.0, 1.0)


def test_named_cmap_runs_from_black_to_the_named_tip():
    cmap = named_cmap("green")
    assert cmap(0.0)[:3] == (0.0, 0.0, 0.0)
    np.testing.assert_allclose(cmap(1.0)[:3], (0.0, 1.0, 0.0))


def test_supplied_colors_win_over_the_default_order():
    colors = resolve_channel_colors([1, 2, 3], {2: "red"})
    assert colors[2] == "red"
    assert colors[1] == DEFAULT_CHANNEL_COLORS[0]
    assert colors[3] == DEFAULT_CHANNEL_COLORS[2]


def test_default_colors_cycle_for_a_long_channel_list():
    ids = list(range(len(DEFAULT_CHANNEL_COLORS) + 2))
    colors = resolve_channel_colors(ids, None)
    assert colors[0] == colors[len(DEFAULT_CHANNEL_COLORS)]


def test_a_single_channel_cell_is_rendered_with_viridis():
    """Viridis, not the channel color.

    A single-channel PNG exists to show intensity. Viridis separates
    intensity levels that a black-to-color ramp compresses.
    """
    thumb = np.zeros((1, 2, 2), dtype=np.float32)
    rgb = render_cell(thumb, [0], [(0.0, 1.0)], ["green"], True)
    expected = matplotlib.colormaps["viridis"](0.0)[:3]
    np.testing.assert_allclose(rgb[0, 0], expected, atol=1e-6)
    # A black-to-green ramp would have rendered this cell black.
    assert rgb.max() > 0.0


def test_a_merged_cell_adds_one_ramp_per_channel():
    thumb = np.zeros((2, 1, 1), dtype=np.float32)
    thumb[0, 0, 0] = 1.0
    thumb[1, 0, 0] = 1.0
    rgb = render_cell(
        thumb, [0, 1], [(0.0, 1.0), (0.0, 1.0)], ["red", "green"], False
    )
    np.testing.assert_allclose(rgb[0, 0], (1.0, 1.0, 0.0))


def test_a_merged_cell_clips_at_white():
    thumb = np.ones((2, 1, 1), dtype=np.float32)
    rgb = render_cell(
        thumb, [0, 1], [(0.0, 1.0), (0.0, 1.0)], ["red", "red"], False
    )
    np.testing.assert_allclose(rgb[0, 0], (1.0, 0.0, 0.0))


# --- the wavelength parse --------------------------------------------


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Ex 390", 390),
        ("Ex475", 475),
        ("ex: 555", 555),
        ("Ex 475 / Em 509", 475),
        ("475/509", 475),
        ("Alexa 488", 488),
        ("HOECHST 33342 405nm", 405),
    ],
)
def test_a_name_that_carries_a_wavelength_parses_to_it(name, expected):
    assert parse_wavelength_nm(name) == expected


@pytest.mark.parametrize("name", ["Ch2", "w1", "20x", "DAPI", "", "Ex 900"])
def test_a_name_that_carries_no_wavelength_parses_to_nothing(name):
    """The 340-800 range rejects the numbers that are not wavelengths."""
    assert parse_wavelength_nm(name) is None


# --- the color ladder, base set --------------------------------------


def test_four_excitation_lines_take_the_base_ladder_in_order():
    """The spread a four-channel plate is expected to produce."""
    names = {1: "Ex 390", 2: "Ex 475", 3: "Ex 555", 4: "Ex 635"}
    colors = resolve_channel_colors([1, 2, 3, 4], None, names)
    assert colors == {1: "cyan", 2: "green", 3: "yellow", 4: "magenta"}


def test_an_explicit_color_wins_and_the_other_names_still_parse():
    names = {1: "Ex 390", 2: "Ex 475", 3: "Ex 555", 4: "Ex 635"}
    colors = resolve_channel_colors([1, 2, 3, 4], {2: "red"}, names)
    assert colors == {1: "cyan", 2: "red", 3: "yellow", 4: "magenta"}


def test_a_name_without_a_wavelength_keeps_its_positional_color():
    names = {1: "ChannelOne", 2: "ChannelTwo"}
    colors = resolve_channel_colors([1, 2], None, names)
    assert colors == {1: "cyan", 2: "magenta"}


def test_the_base_ladder_never_reaches_blue_or_red():
    """`blue` and `red` are spares. One channel cannot open them."""
    for nm in range(MIN_WAVELENGTH_NM, MAX_WAVELENGTH_NM + 1):
        colors = resolve_channel_colors([1], None, {1: f"Ex {nm}"})
        assert colors[1] in {"cyan", "green", "yellow", "magenta"}


def test_the_base_boundaries_sit_in_the_gaps_between_led_lines():
    """Derived from the representatives, not written down twice.

    No common excitation line sits near one of these. A boundary on a
    hardware line flips color when two adapters round differently.
    """
    assert base_boundaries_nm() == [442.5, 517.5, 602.5]


# --- the color ladder, collisions ------------------------------------


@pytest.mark.parametrize(
    ("wavelengths", "expected"),
    [
        # No collision. Nothing moves, and the spares stay shut.
        (
            [390, 475, 555, 635],
            ["cyan", "green", "yellow", "magenta"],
        ),
        # 470 and 488 both sit in the green bin. They split upward.
        (
            [390, 470, 488, 647],
            ["cyan", "green", "yellow", "magenta"],
        ),
        # 635 and 680 both sit in the magenta bin. `red` opens.
        (
            [390, 475, 635, 680],
            ["cyan", "green", "red", "magenta"],
        ),
        # 555 and 594 both sit in the yellow bin. `red` opens.
        (
            [390, 475, 555, 594],
            ["cyan", "green", "yellow", "red"],
        ),
        # Three channels crowd the middle and spread across three slots.
        (
            [390, 514, 555, 594, 647],
            ["cyan", "green", "yellow", "red", "magenta"],
        ),
    ],
)
def test_colliding_channels_spread_across_the_full_ladder(
    wavelengths, expected
):
    ids = list(range(1, len(wavelengths) + 1))
    names = {i: f"Ex {nm}" for i, nm in zip(ids, wavelengths, strict=True)}
    colors = resolve_channel_colors(ids, None, names)
    assert [colors[i] for i in ids] == expected


@pytest.mark.parametrize(
    "wavelengths",
    [
        [390, 475, 555, 635],
        [390, 470, 488, 647],
        [390, 475, 635, 680],
        [390, 475, 555, 594],
        [390, 514, 555, 594, 647],
    ],
)
def test_a_longer_wavelength_never_takes_an_earlier_ladder_color(
    wavelengths,
):
    ladder = [name for name, _ in COLOR_LADDER_NM]
    ids = list(range(1, len(wavelengths) + 1))
    names = {i: f"Ex {nm}" for i, nm in zip(ids, wavelengths, strict=True)}
    colors = resolve_channel_colors(ids, None, names)
    slots = [ladder.index(colors[i]) for i in ids]
    assert slots == sorted(set(slots))


def test_more_channels_than_ladder_slots_fall_back_to_the_cycle():
    """One coherent rule beats a mixed one."""
    wavelengths = [365, 405, 450, 500, 550, 600, 650]
    ids = list(range(1, len(wavelengths) + 1))
    names = {i: f"Ex {nm}" for i, nm in zip(ids, wavelengths, strict=True)}
    colors = resolve_channel_colors(ids, None, names)
    assert [colors[i] for i in ids] == [
        DEFAULT_CHANNEL_COLORS[idx % len(DEFAULT_CHANNEL_COLORS)]
        for idx in range(len(ids))
    ]


def test_an_unparsed_name_never_reuses_a_color_a_parsed_name_took():
    names = {1: "Ex 390", 2: "Ex 475", 3: "Widefield", 4: "Phase"}
    colors = resolve_channel_colors([1, 2, 3, 4], None, names)
    assert colors[1] == "cyan"
    assert colors[2] == "green"
    assert len(set(colors.values())) == 4


# --- the fluorophore name table --------------------------------------


def test_the_four_common_stains_take_the_base_ladder_colors():
    names = {1: "DAPI", 2: "Alexa 488", 3: "Cy3", 4: "Alexa 647"}
    colors = resolve_channel_colors([1, 2, 3, 4], None, names)
    assert colors == {1: "cyan", 2: "green", 3: "yellow", 4: "magenta"}


@pytest.mark.parametrize(
    "name", ["Brightfield", "BF", "TL", "Trans", "bf", "TL 20x"]
)
def test_a_transmitted_light_channel_renders_gray(name):
    """No wavelength reaches a transmitted-light channel."""
    assert fluorophore_color(name) == "gray"


@pytest.mark.parametrize("name", ["subfield", "ABFP", "bfp marker"])
def test_bf_matches_as_a_whole_word_and_not_as_a_substring(name):
    """None of these is a transmitted-light channel."""
    assert fluorophore_color(name) is None


def test_tl_matches_as_a_whole_word_so_a_gene_name_survives():
    """`TLR4-GFP` is a GFP channel. A substring match would gray it."""
    assert fluorophore_color("TLR4-GFP") == "green"


def test_the_table_wins_over_a_wavelength_in_the_same_name():
    """`DAPI 647` is cyan. The name beats the number."""
    colors = resolve_channel_colors([1], None, {1: "DAPI 647"})
    assert colors == {1: "cyan"}


def test_a_name_the_table_misses_still_reaches_the_parse():
    colors = resolve_channel_colors([1], None, {1: "Ex 635"})
    assert colors == {1: "magenta"}


def test_an_explicit_color_still_wins_over_the_table():
    colors = resolve_channel_colors([1, 2], {1: "red"}, {1: "DAPI", 2: "Cy5"})
    assert colors == {1: "red", 2: "magenta"}


def test_the_table_is_ordered_so_a_specific_name_beats_a_broader_one():
    """`Alexa 488` must come before any entry that `488` matches."""
    keys = list(FLUOROPHORE_COLORS)
    for specific in ("Alexa 488", "Alexa 555", "Alexa 568", "Alexa 647"):
        broader = [
            k for k in keys if k != specific and k.lower() in specific.lower()
        ]
        assert not broader, f"{broader} shadow {specific}"


def test_a_name_the_table_misses_returns_nothing():
    assert fluorophore_color("ChannelOne") is None


def test_a_table_color_survives_a_ladder_overflow():
    """The table sits above the ladder, so the ladder cannot undo it."""
    names = {1: "Brightfield"}
    names.update(
        {
            i: f"Ex {nm}"
            for i, nm in enumerate(
                [365, 405, 450, 500, 550, 600, 650], start=2
            )
        }
    )
    colors = resolve_channel_colors(list(names), None, names)
    assert colors[1] == "gray"
