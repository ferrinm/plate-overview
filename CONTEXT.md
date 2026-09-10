# CONTEXT

This document holds the domain context for `plate-overview`. It covers
what the overview is for, and the constraints that shape the seam
between this package and its adapters.

## What the overview is for

The overview is a gate, not a picture. It answers two questions before
any analysis runs:

- Does this channel hold the puncta that the staining sheet claims?
- Do the mock wells have a usable noise floor?

Both judgements depend on plate-wide per-channel contrast. That contrast
is what makes the apparent brightness of a well mean something relative
to its neighbors.

## One renderer, not two that match

There is exactly one renderer, and there must stay exactly one. A second
implementation agrees today and drifts tomorrow. The drift breaks the
calibration invisibly, because both figures still look like plausible
plate overviews.

The renderer therefore lives in this package, once. Every acquisition
format reaches it through an adapter. `pyphenix` (Opera Phenix) is the
first consumer. A Leica Thunder `.lif` adapter is the second.

## The seam

A consumer implements a narrow **render port**: a typed Protocol plus a
normalized dict of plate-level facts.

- `WellSource` is the Protocol. It has one method, `read_well`, which
  returns one well as a `(C, Z, Y, X)` array at acquisition resolution.
- `PlateFacts` is the dict: plate geometry, channels, timepoints,
  fields, the well-to-field map, and the physical pixel size.
- `render_plate_overview` takes both and writes the PNGs and the
  sidecar.

The port is deliberately not a general reader interface. The two
contracts cross rather than nest. The port needs render-time facts that
a reader can omit. A reader carries analysis-time members that the
renderer never reads.

## The gathering loop

This package owns the **gathering loop**. The reason is a memory
constraint, not a style choice. A large mosaic well can reach ~268 MB
against a ~1 MB thumbnail. A design that hands over 96 pre-gathered
wells therefore needs tens of gigabytes.

The loop downsamples each well. It then discards the full-resolution
array before it reads the next well.

## Resampling happens once

Resampling happens exactly once, inside this package. An adapter that
downsamples before it hands the pixels over produces different pixel
values. Different pixel values produce different plate contrast. That
divergence is what this package exists to prevent.

The same argument covers the Z projection. The package max-projects, so
an adapter cannot substitute a different projection.

## The sidecar records a basename

Every render writes one JSON sidecar next to the PNGs. It records the
name of the acquisition, never a path to it. The package strips the
directory components itself, because a sidecar is small enough to paste
whole into a public issue.
