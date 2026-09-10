# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Versions are derived from git tags by `setuptools_scm` — never hand-edit
a version anywhere in this repo.

## [Unreleased]

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
