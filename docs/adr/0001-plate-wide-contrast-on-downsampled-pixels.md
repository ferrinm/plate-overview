# Plate-wide contrast limits are computed on downsampled, max-projected pixels

This decision moved here with the renderer. It was first recorded in `pyphenix`,
where the code lived before the split.

The plate overview needs a per-channel intensity range that is identical across
every well, so wells can be visually compared. The obvious approach — pool every
raw 16-bit pixel from every well and take the 99.5th percentile — roughly doubles
I/O: one streaming pass to compute the limits, a second pass to render. Instead
the percentile runs on the same downsampled, Z-max-projected pixels that the
renderer already holds. That keeps the overview single-pass and bounded in
memory.

The trade-off is that block-mean downsampling attenuates single-pixel hot spots.
The resulting `[0, p99.5]` therefore sits slightly lower than a per-well number
measured on raw pixels in a viewer. For a *diagnostic* overview this is arguably
an improvement, because it suppresses isolated saturation. It does mean that
overview intensities are not directly comparable to live viewer intensities.

If a future use case demands exact parity, switch to a two-pass implementation.
Do not change the percentile or the downsampling kernel. Both of those silently
shift the apparent brightness of every existing overview.
