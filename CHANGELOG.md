# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Versions are derived from git tags by `setuptools_scm` — never hand-edit
a version anywhere in this repo.

## [Unreleased]

## [0.2.0] - 2026-10-30

### Added

- `resolve_channel_colors`, now public. It is the whole color rule for
  a whole plate. A consumer calls this rather than coloring channels
  its own way, because a second rule agrees today and drifts tomorrow.
- `FLUOROPHORE_COLORS` and `fluorophore_color`, the canonical
  fluorophore name → color table, moved out of `pyphenix._colormaps`
  (#6). Both are public, because there must be exactly one such table
  and `pyphenix` must import it rather than keep a copy. The table is
  only one of four rules, so importing it alone still drifts.
- `Brightfield` keeps its gray, and the synonyms `BF`, `TL` and `Trans`
  now reach it too. `BF` and `TL` match as a whole word, because two
  letters appear inside too many other strings.
- ADR-0004, covering the color ladder, the parse rules, the name table
  and the resolution order.

### Changed

- A channel takes its color from its name (#4, #5, #6). The renderer
  reads `channel_names` and tries the fluorophore table, then an
  excitation wavelength parsed out of the name, before it falls back to
  the positional cycle. An explicit `PlateFacts["channel_colors"]`
  entry still wins over all three.
- Two channels whose colors both come from a wavelength never share a
  ramp (#5). The ladder holds two spare slots, `blue` and `red`, and a
  collision spreads the colliding channels across them. A plate with no
  collision renders exactly as before.

  A fixed color does not take part. An explicit `channel_colors` entry
  and a fluorophore table hit both stand as given, so two channels can
  still share a ramp if a fixed color and a ladder color agree. See
  ADR-0004.

**This changes the default render.** Any plate whose channel names carry
a wavelength or a known fluorophore name gets different colors than it
got in 0.1.0. That is the point of the change: `Ex 475` excites a green
fluorophore and used to render magenta, so a reviewer who used the
overview as a gate read the wrong channel. Pass `channel_colors`
explicitly to pin the old colors.

### Follow-up outside this repository

`pyphenix` must now import `FLUOROPHORE_COLORS` from
`plate_overview` and delete `pyphenix/_colormaps.py`. That is a separate
change in a separate repository.

## [0.1.0] - 2026-09-10

### Added

- The renderer, moved out of `pyphenix._overview` (#2). The package now
  exports `render_plate_overview`, the `WellSource` render port, and the
  `PlateFacts` dict. It owns the gathering loop and everything after it:
  max projection, downsampling, plate-wide contrast, cell rendering,
  grid composition, the scale bar, the labels and the JSON sidecar.
- `tqdm` as a dependency, for the progress bars the loop already showed.
- ADR-0001, ADR-0002 and ADR-0003, covering plate-wide contrast, the
  shape the port hands over, and the basename rule for the sidecar.

### Changed

- The JSON sidecar records `source_name`, a basename, in place of the
  absolute `experiment_path` the moved code recorded. A sidecar pasted
  into a public issue no longer leaks a filesystem layout.
- The sidecar records `plate_overview_version`. A consumer adds its own
  version through the new `provenance` argument.

Rendered PNGs are unchanged. `tests/test_parity_with_pyphenix.py`
compares the PNG bytes against the implementation this code was moved
from, and it passes.

## [0.0.1] - 2026-09-10

### Added

- Repository scaffold: packaging, tox, CI, and a headless smoke test.
  No renderer yet; see #1.
