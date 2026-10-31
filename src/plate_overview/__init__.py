"""Vendor-neutral whole-plate QC montages.

One thumbnail per well, laid out in plate geometry, with each channel's
contrast normalized across the whole plate so wells are comparable to
each other by eye.

This package knows nothing about acquisition formats. A consumer
implements a narrow render port and this package draws:

- :class:`PlateFacts` — plate-level facts, as one normalized dict.
- :class:`WellSource` — one method that reads the pixels of one well.
- :func:`render_plate_overview` — the gathering loop and the renderer.

The package also owns the rule that gives each channel its color:

- :func:`resolve_channel_colors` — the whole rule, for a whole plate.
  A consumer that colors channels for a viewer calls this.
- :data:`FLUOROPHORE_COLORS` and :func:`fluorophore_color` — the
  canonical fluorophore name → color table, and its lookup.

There is exactly one such rule and one such table, and both live here
because the renderer lives here. A consumer that keeps a copy agrees
today and drifts tomorrow, and the drift breaks the calibration
invisibly.

The table is only one of four rules, so importing it alone still
drifts on every channel named by wavelength. Import
:func:`resolve_channel_colors` unless you need the table itself.
"""

from ._colors import (
    FLUOROPHORE_COLORS,
    fluorophore_color,
    resolve_channel_colors,
)
from ._overview import render_plate_overview
from ._port import PlateFacts, WellSource

try:
    from ._version import version as __version__
except ImportError:  # pragma: no cover - source checkout without metadata
    __version__ = "unknown"

__all__ = [
    "FLUOROPHORE_COLORS",
    "PlateFacts",
    "WellSource",
    "__version__",
    "fluorophore_color",
    "render_plate_overview",
    "resolve_channel_colors",
]
