# plate-overview

Whole-plate QC montages for multiwell microscopy: one thumbnail per
well, laid out in plate geometry, with each channel's contrast
normalized **across the whole plate** so wells are comparable to each
other by eye.

Vendor-neutral. This package knows nothing about acquisition formats —
you hand it pixels through a small typed port and it draws.

> **Status: pre-alpha, empty.** The renderer has not landed yet. See
> [ferrinm/PyPhenix#32](https://github.com/ferrinm/PyPhenix/issues/32),
> which extracts it, and #1 here.

## Why this exists as its own package

The overview is not a picture, it is a gate. It answers two questions
before any analysis runs:

- does this channel hold the puncta the staining sheet claims?
- do the mock wells have a usable noise floor?

Both judgements are calibrated against plate-wide per-channel contrast.
That is what makes a well's apparent brightness mean something relative
to its neighbours, and it is why **there must be exactly one renderer,
not two that match**. A second implementation that agrees today and
drifts tomorrow breaks the calibration invisibly: both figures still
look like plausible plate overviews.

So the renderer lives here, once, and every acquisition format reaches
it through an adapter. `pyphenix` (Opera Phenix) is the first consumer;
a Leica Thunder `.lif` adapter is the second.

## The seam

A consumer implements a narrow **render port**: a typed Protocol plus a
normalized dict of plate-level facts. It is deliberately not a general
reader interface — the two contracts cross rather than nest. The port
needs render-time facts a reader may not expose, and a reader carries
analysis-time members the renderer never reads.

The package owns the **gathering loop**, which is a memory constraint
rather than a style choice: a large mosaic well can be ~268 MB against a
~1 MB thumbnail, so a design that hands over 96 pre-gathered wells needs
tens of gigabytes. The loop downsamples each well and discards the
full-resolution array as it goes.

Resampling happens exactly once, inside this package. An adapter that
downsamples before handing pixels over produces different pixel values
and therefore different plate contrast — the divergence this package
exists to prevent.

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
