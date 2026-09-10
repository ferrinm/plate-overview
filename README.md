# plate-overview

Whole-plate overview images for multiwell fluorescence microscopy: one
thumbnail per well, laid out in plate geometry, with each channel's
contrast normalized **across the whole plate** so wells are comparable
to each other by eye.

Vendor-neutral. This package knows nothing about acquisition formats —
you hand it pixels through a small typed port and it draws.

> **Status: pre-alpha, empty.** The renderer has not landed yet. See
> [ferrinm/PyPhenix#32](https://github.com/ferrinm/PyPhenix/issues/32),
> which extracts it, and #1 here.

## Why this exists as its own package

There is exactly one renderer. Every acquisition format reaches it
through an adapter, so overviews from different instruments stay
comparable. `pyphenix` (Opera Phenix) is the first consumer. A Leica
Thunder `.lif` adapter is the second.

## Design notes

[CONTEXT.md](CONTEXT.md) covers the render port, the gathering loop, and
the resampling rule.

## Install

```bash
pip install plate-overview
```

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
