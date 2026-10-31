"""Channel colors for merge compositing.

Single-channel PNGs always use viridis. A merge adds one black-to-color
ramp per channel, so the colors must stay additive and distinct.

This module also decides which color each channel gets. A channel takes
the color of the first rule that answers:

1. An explicit entry in ``PlateFacts["channel_colors"]``.
2. :data:`FLUOROPHORE_COLORS`, the fluorophore name table.
3. An excitation wavelength parsed out of the channel name and placed
   on :data:`COLOR_LADDER_NM`, the color ladder.
4. The positional :data:`DEFAULT_CHANNEL_COLORS` cycle.

Rules 2 and 3 read the name, so the module owns a name parser and a
slot search as well as the colormaps. See
``docs/adr/0004-a-channel-takes-its-color-from-its-name.md``.
"""

from __future__ import annotations

import bisect
import itertools
import re
from typing import NamedTuple

from matplotlib.colors import LinearSegmentedColormap

__all__ = [
    "BASE_LADDER_SLOTS",
    "COLOR_LADDER_NM",
    "COLOR_RGB",
    "DEFAULT_CHANNEL_COLORS",
    "FLUOROPHORE_COLORS",
    "MAX_WAVELENGTH_NM",
    "MIN_WAVELENGTH_NM",
    "WHOLE_WORD_FLUOROPHORES",
    "assign_ladder_slots",
    "base_boundaries_nm",
    "fluorophore_color",
    "named_cmap",
    "parse_wavelength_nm",
    "resolve_channel_colors",
    "rgb_for",
]

# Color name → (R, G, B) for additive merge compositing. Single-color
# colormaps go from black to the named tip. The names match napari's, so
# a consumer that already colors channels for a viewer reuses them.
COLOR_RGB: dict[str, tuple[float, float, float]] = {
    "gray": (1.0, 1.0, 1.0),
    "grey": (1.0, 1.0, 1.0),
    "red": (1.0, 0.0, 0.0),
    "green": (0.0, 1.0, 0.0),
    "blue": (0.0, 0.0, 1.0),
    "cyan": (0.0, 1.0, 1.0),
    "magenta": (1.0, 0.0, 1.0),
    "yellow": (1.0, 1.0, 0.0),
}

# Fallback assignment, by channel order, when a consumer supplies no
# colors of its own.
DEFAULT_CHANNEL_COLORS = (
    "cyan",
    "magenta",
    "yellow",
    "green",
    "red",
    "blue",
)


# The canonical fluorophore name → color table. There must be exactly
# one such table in the codebase. It moved here from
# `pyphenix._colormaps` with the renderer, because a second copy agrees
# today and drifts tomorrow, and the drift breaks the calibration
# invisibly. Add a fluorophore here and it propagates everywhere a
# channel is colored.
#
# Order matters. Lookup is first-match on a case-insensitive substring,
# so a specific name must come before any broader name that
# substring-matches it.
FLUOROPHORE_COLORS: dict[str, str] = {
    "Brightfield": "gray",
    "BF": "gray",
    "TL": "gray",
    "Trans": "gray",
    "DAPI": "cyan",
    "Hoechst": "cyan",
    "Alexa 488": "green",
    "GFP": "green",
    "EGFP": "green",
    "Alexa 555": "yellow",
    "Alexa 568": "yellow",
    "Cy3": "yellow",
    "mCherry": "magenta",
    "mStrawberry": "magenta",
    "Alexa 647": "magenta",
    "Cy5": "magenta",
}

# These keys match as a whole word, not as a substring. Two letters
# appear inside too many other strings: "BF" sits inside "subfield",
# and "TL" sits inside "Thunder Light".
WHOLE_WORD_FLUOROPHORES = frozenset({"BF", "TL"})

_WHOLE_WORD_PATTERNS = {
    key: re.compile(rf"\b{re.escape(key)}\b", re.IGNORECASE)
    for key in WHOLE_WORD_FLUOROPHORES
}


# The color ladder. Each slot owns one representative excitation
# wavelength, and a channel takes the slot with the nearest one. The
# ladder runs on excitation, not emission, because that is what these
# channel names carry. The colors already account for the emission
# shift: "Ex 390" excites DAPI, which emits near 460 nm, and cyan reads
# better than blue against black.
#
# This one table governs everything downstream. The boundaries are
# derived from it, never written down a second time.
class LadderSlot(NamedTuple):
    """One rung of the color ladder."""

    color: str
    representative_nm: int


COLOR_LADDER_NM: tuple[LadderSlot, ...] = (
    LadderSlot("blue", 365),
    LadderSlot("cyan", 405),
    LadderSlot("green", 480),
    LadderSlot("yellow", 555),
    LadderSlot("red", 600),
    LadderSlot("magenta", 650),
)

# Indices into COLOR_LADDER_NM for the four slots a plate uses when no
# two channels collide. "blue" and "red" are spares. Only a collision
# opens them. See docs/adr/0004.
BASE_LADDER_SLOTS: tuple[int, ...] = (1, 2, 3, 5)

# A parsed number counts as a wavelength only inside this range. The
# range is what rejects the numbers that are not wavelengths: "Ch2"
# gives 2, "w1" gives 1 and "20x" gives 20, and all three fall outside.
MIN_WAVELENGTH_NM = 340
MAX_WAVELENGTH_NM = 800

# "Ex 475", "Ex475", "ex: 475". The lookbehind stops the "ex" inside a
# longer word, such as "Alexa", from tagging the number after it.
_EX_TAGGED_NM = re.compile(r"(?<![a-z])ex[\s:=_-]*(\d+)", re.IGNORECASE)
_ANY_NUMBER = re.compile(r"\d+")


def _in_range_wavelengths(texts: list[str]) -> list[int]:
    """Parse each match, and keep the ones inside the wavelength range."""
    return [
        value
        for value in (int(text) for text in texts)
        if MIN_WAVELENGTH_NM <= value <= MAX_WAVELENGTH_NM
    ]


def parse_wavelength_nm(channel_name: str) -> int | None:
    """Read an excitation wavelength out of a channel name.

    An ``Ex`` tag selects its own number. Without a tag, the lowest
    in-range number wins, because the excitation line of one
    fluorophore is always shorter than its emission line. ``Ex 475 /
    Em 509`` and ``475/509`` therefore both give 475.

    Returns ``None`` when the name carries no in-range number.
    """
    tagged = _in_range_wavelengths(_EX_TAGGED_NM.findall(channel_name))
    if tagged:
        return tagged[0]
    untagged = _in_range_wavelengths(_ANY_NUMBER.findall(channel_name))
    return min(untagged) if untagged else None


def fluorophore_color(channel_name: str) -> str | None:
    """Look a channel name up in :data:`FLUOROPHORE_COLORS`.

    The match is case-insensitive, on a substring, and the first entry
    that matches wins. A key in :data:`WHOLE_WORD_FLUOROPHORES` matches
    as a whole word instead.

    Returns ``None`` when no entry matches.
    """
    lowered = channel_name.lower()
    for key, color in FLUOROPHORE_COLORS.items():
        pattern = _WHOLE_WORD_PATTERNS.get(key)
        if pattern is not None:
            if pattern.search(channel_name):
                return color
        elif key.lower() in lowered:
            return color
    return None


def base_boundaries_nm() -> list[float]:
    """Wavelengths where the base set changes color.

    Each boundary is the midpoint between two neighboring
    representatives in :data:`COLOR_LADDER_NM`. Every boundary lands in
    an empty gap between the common LED excitation clusters, so no
    hardware line sits near one.
    """
    reps = [
        COLOR_LADDER_NM[slot].representative_nm for slot in BASE_LADDER_SLOTS
    ]
    return [(low + high) / 2 for low, high in itertools.pairwise(reps)]


_BASE_BOUNDARIES_NM = base_boundaries_nm()


def _base_slot(wavelength_nm: int) -> int:
    """The base ladder slot that owns *wavelength_nm*.

    The boundaries are half-integers, so an integer wavelength never
    lands on one and the choice is never a tie.
    """
    return BASE_LADDER_SLOTS[
        bisect.bisect_left(_BASE_BOUNDARIES_NM, wavelength_nm)
    ]


def _slot_cost(sorted_nm: list[int], slots: tuple[int, ...]) -> int:
    """Total distance from each wavelength to its slot representative."""
    return sum(
        abs(nm - COLOR_LADDER_NM[slot].representative_nm)
        for nm, slot in zip(sorted_nm, slots, strict=True)
    )


def assign_ladder_slots(sorted_nm: list[int]) -> list[int] | None:
    """One ladder slot per wavelength, for wavelengths sorted ascending.

    Each channel keeps its base slot while the base slots stay
    distinct. A collision opens the two spares, ``blue`` and ``red``,
    and the whole plate is re-seated across the full ladder under two
    constraints:

    - The slot indices strictly increase, so a longer wavelength never
      takes a color earlier in the ladder.
    - The sum of the distances to the representatives is the minimum.

    The ladder holds six slots, so the search enumerates every strictly
    increasing assignment and takes the cheapest. The result is exact,
    which a single greedy pass is not: a greedy pass that only moves
    upward fails when the upward slot is taken and the downward slot is
    free.

    Returns ``None`` when there are more wavelengths than ladder slots.
    """
    if len(sorted_nm) > len(COLOR_LADDER_NM):
        return None
    base = [_base_slot(nm) for nm in sorted_nm]
    if len(set(base)) == len(base):
        return base
    best = min(
        itertools.combinations(range(len(COLOR_LADDER_NM)), len(sorted_nm)),
        key=lambda slots: (
            _slot_cost(sorted_nm, slots),
            # On an equal cost, prefer the base set. A spare slot opens
            # only when it is strictly cheaper. `blue` in particular
            # reads dim against black.
            sum(1 for slot in slots if slot not in BASE_LADDER_SLOTS),
            slots,
        ),
    )
    return list(best)


def rgb_for(color_name: str) -> tuple[float, float, float]:
    """Look up a color name. An unknown name renders as white."""
    return COLOR_RGB.get(color_name.lower(), (1.0, 1.0, 1.0))


def named_cmap(color_name: str) -> LinearSegmentedColormap:
    """Black → named-color linear colormap, for the colorbars."""
    return LinearSegmentedColormap.from_list(
        f"plate_overview_{color_name}", [(0, 0, 0), rgb_for(color_name)]
    )


def _positional_colors(
    channel_ids: list[int],
    provided: dict[int, str],
) -> dict[int, str]:
    """The original rule: one color per channel, by channel position."""
    return {
        ch_id: provided.get(
            ch_id, DEFAULT_CHANNEL_COLORS[idx % len(DEFAULT_CHANNEL_COLORS)]
        )
        for idx, ch_id in enumerate(channel_ids)
    }


def resolve_channel_colors(
    channel_ids: list[int],
    provided: dict[int, str] | None,
    channel_names: dict[int, str] | None = None,
) -> dict[int, str]:
    """Assign one color to each channel.

    A channel takes the color of the first rule that answers:

    1. An explicit entry in *provided*.
    2. :data:`FLUOROPHORE_COLORS`, the fluorophore name table.
    3. A wavelength parsed out of *channel_names*, placed on
       :data:`COLOR_LADDER_NM`.
    4. The :data:`DEFAULT_CHANNEL_COLORS` cycle, by channel position.

    The table wins over the parse because a name encodes the
    fluorophore identity, and a number in the same name does not.

    A channel that resolves by name does not consume a position in the
    cycle, so an explicit entry never shifts the colors of its
    neighbors.
    """
    provided = provided or {}
    names = channel_names or {}

    tabled = {
        ch_id: color
        for ch_id in channel_ids
        if ch_id not in provided
        and (color := fluorophore_color(names.get(ch_id, ""))) is not None
    }
    parsed = {
        ch_id: nm
        for ch_id in channel_ids
        if ch_id not in provided
        and ch_id not in tabled
        and (nm := parse_wavelength_nm(names.get(ch_id, ""))) is not None
    }
    if not parsed and not tabled:
        return _positional_colors(channel_ids, provided)

    order = sorted(parsed, key=lambda ch_id: (parsed[ch_id], ch_id))
    slots = assign_ladder_slots([parsed[ch_id] for ch_id in order])
    if slots is None:
        # More channels than the ladder can seat. One coherent rule
        # beats a mixed one, so every parsed channel falls back to the
        # cycle together.
        if not tabled:
            return _positional_colors(channel_ids, provided)
        order, slots = [], []

    colors = {
        ch_id: COLOR_LADDER_NM[slot].color
        for ch_id, slot in zip(order, slots, strict=True)
    }
    colors.update(tabled)
    colors.update(
        {ch_id: provided[ch_id] for ch_id in channel_ids if ch_id in provided}
    )

    # Whatever is left took no color from a name. Walk the cycle, and
    # skip the colors the named channels already hold.
    taken = set(colors.values())
    pool = [c for c in DEFAULT_CHANNEL_COLORS if c not in taken] or list(
        DEFAULT_CHANNEL_COLORS
    )
    unnamed = [ch_id for ch_id in channel_ids if ch_id not in colors]
    for idx, ch_id in enumerate(unnamed):
        colors[ch_id] = pool[idx % len(pool)]

    return {ch_id: colors[ch_id] for ch_id in channel_ids}
