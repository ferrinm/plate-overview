"""Vendor-neutral whole-plate QC montages.

One thumbnail per well, laid out in plate geometry, with each channel's
contrast normalized across the whole plate so wells are comparable to
each other by eye.

This package knows nothing about acquisition formats. A consumer
implements a narrow render port and this package draws:

- :class:`PlateFacts` — plate-level facts, as one normalized dict.
- :class:`WellSource` — one method that reads the pixels of one well.
- :func:`render_plate_overview` — the gathering loop and the renderer.
"""

from ._overview import render_plate_overview
from ._port import PlateFacts, WellSource

try:
    from ._version import version as __version__
except ImportError:  # pragma: no cover - source checkout without metadata
    __version__ = "unknown"

__all__ = [
    "PlateFacts",
    "WellSource",
    "__version__",
    "render_plate_overview",
]
