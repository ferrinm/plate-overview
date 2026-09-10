# plate-overview

Whole-plate overview images for multiwell fluorescence microscopy: one
thumbnail per well, laid out in plate geometry, with each channel's
contrast normalized **across the whole plate** so wells are comparable
to each other by eye.

Vendor-neutral. This package knows nothing about acquisition formats —
you hand it pixels through a small typed port and it draws.

> **Status: pre-alpha.** The renderer landed in #2. The API can still
> change.

## Why this exists as its own package

There is exactly one renderer. Every acquisition format reaches it
through an adapter, so overviews from different instruments stay
comparable. `pyphenix` (Opera Phenix) is the first consumer. A Leica
Thunder `.lif` adapter is the second.

## Install

```bash
pip install plate-overview
```

## Use it

Write an adapter with one method, describe the plate in one dict, and
call the renderer.

```python
from plate_overview import render_plate_overview


class MySource:
    """Adapter over one acquisition format."""

    def read_well(
        self,
        *,
        row,
        column,
        field,
        stitch_fields,
        timepoint,
        channels,
        z_slices,
        apply_ffc,
    ):
        # Read the well from your format. Return a (C, Z, Y, X) array at
        # acquisition resolution, with C in the order of *channels*.
        # Do not project it and do not resample it.
        return my_format.read(row, column, field, ...)


plate = {
    "plate_id": "PLATE-001",
    "plate_rows": 8,
    "plate_columns": 12,
    "channel_ids": [1, 2],
    "channel_names": {1: "Nuclei", 2: "Marker"},
    "timepoints": [0],
    "fields": [1, 2, 3, 4],
    "well_field_map": {(1, 1): [1, 2, 3, 4], (1, 2): [1, 2, 3, 4]},
    "image_size": (1080, 1080),
    "pixel_size_m": (2.97e-07, 2.97e-07),
}

written = render_plate_overview(MySource(), plate, "overviews/")
```

`render_plate_overview` writes one PNG per non-empty channel combo
(`2**N - 1` PNGs for N channels) plus one JSON sidecar, and returns
every path it wrote. Every PNG shares one set of plate-wide per-channel
contrast limits, so the wells are comparable by eye.

Three rules bind an adapter:

- Return full-resolution pixels. The package projects and downsamples
  once, and an adapter that resamples first shifts the plate contrast.
- Read on demand. The package discards each well before it reads the
  next one, so a plate never has to fit in memory.
- Keep paths out of `source_name`. The package records a basename.

`help(plate_overview.PlateFacts)` documents every key, required and
optional.

## Design notes

[CONTEXT.md](CONTEXT.md) covers the render port, the gathering loop, and
the resampling rule. [docs/adr/](docs/adr) records the decisions behind
them.

## Contributing

Two house rules beyond the usual:

- **No real acquisition data, anywhere.** No fixture, example, sidecar
  or docstring may derive from a real acquisition. No plate
  identifiers, no operator-bearing paths, no source filenames. Test
  fixtures are synthetic. This repository is public and the upstream
  acquisitions are not.
- **Output paths are basenames.** The JSON sidecar records a filename,
  never an absolute path, so a sidecar pasted into an issue does not
  leak a filesystem layout.

## License

BSD 3-Clause. See [LICENSE](LICENSE).
