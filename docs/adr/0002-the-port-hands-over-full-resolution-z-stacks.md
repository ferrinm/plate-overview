# The render port hands over one full-resolution Z stack per well

`WellSource.read_well` returns a `(C, Z, Y, X)` array at acquisition resolution.
The package then max-projects it, downsamples it, and discards it before it reads
the next well.

Two other splits were possible, and both are worse.

**A pure function over already-gathered pixels.** The consumer gathers every
thumbnail and hands the whole plate over at once. This is ruled out on memory. A
large mosaic well reaches about 268 MB against a 1 MB thumbnail, so 96 of them
reach about 26 GB. The loop has to live on the package side of the seam, because
only the loop can discard a well.

**The adapter projects and downsamples.** The port would then take one small
`(C, Y, X)` thumbnail per well. This is ruled out on calibration. The overview
supports two eyeball judgements, and both are calibrated against plate-wide
per-channel contrast. Contrast is measured on the downsampled pixels
(ADR-0001), so an adapter that resamples first sets the contrast itself. Two
adapters that resample differently then produce two figures that both look like
plausible plate overviews and are not comparable. That is the exact failure this
package exists to prevent.

The consequence is that an adapter must read on demand. It must not pre-load the
plate, and it must not resample. The one thing it does own is the read: which
files a well maps to, how fields are stitched, and whether flat-field correction
is available.
