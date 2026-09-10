"""Vendor-neutral whole-plate QC montages.

One thumbnail per well, laid out in plate geometry, with each channel's
contrast normalized across the whole plate so wells are comparable to
each other by eye.

This package knows nothing about acquisition formats. A consumer
implements a narrow render port and this package draws.

Nothing is exported yet — the renderer is extracted in
https://github.com/ferrinm/PyPhenix/issues/32.
"""

try:
    from ._version import version as __version__
except ImportError:  # pragma: no cover - source checkout without metadata
    __version__ = "unknown"

__all__ = ["__version__"]
