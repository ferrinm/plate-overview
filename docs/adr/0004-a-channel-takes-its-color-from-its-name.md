# A channel takes its color from its name

A merge adds one black-to-color ramp per channel. The overview is a gate, so a
reviewer must be able to read which channel holds the puncta. If the colors do
not match what the channel actually is, the reviewer reads the wrong channel and
the gate fails.

The renderer used to assign colors by channel position only. A four-channel
plate always rendered cyan, magenta, yellow, green. On a plate whose channel
names carry excitation lines — `Ex 390`, `Ex 475`, `Ex 555`, `Ex 635` — that
order is wrong. `Ex 475` excites a green fluorophore and rendered magenta.

The renderer now reads the channel name.

## The resolution order

A channel takes the color of the first rule that answers:

1. An explicit entry in `PlateFacts["channel_colors"]`.
2. `FLUOROPHORE_COLORS`, the fluorophore name table.
3. An excitation wavelength parsed out of the channel name, placed on the color
   ladder.
4. The positional `DEFAULT_CHANNEL_COLORS` cycle.

The table wins over the parse because a name encodes the fluorophore identity,
and a number in the same name does not. `DAPI 647` is cyan. The two rules agree
on every entry in the table today, so the order matters only for entries added
later.

A channel that resolves by name does not consume a position in the cycle. An
explicit entry therefore never shifts the colors of its neighbors.

## The fluorophore name table

The table moved here from `pyphenix._colormaps`. There must be exactly one such
table in the codebase. The argument is the one `CONTEXT.md` gives for the
renderer itself: a second copy agrees today and drifts tomorrow, and the drift
breaks the calibration invisibly. The table colors the renderer's channels, so
it belongs in the package that owns the renderer.

| Name | Color |
| --- | --- |
| `Brightfield`, `BF`, `TL`, `Trans` | gray |
| `DAPI`, `Hoechst` | cyan |
| `Alexa 488`, `GFP`, `EGFP` | green |
| `Alexa 555`, `Alexa 568`, `Cy3` | yellow |
| `mCherry`, `mStrawberry`, `Alexa 647`, `Cy5` | magenta |

The match is case-insensitive, on a substring, and the first entry that matches
wins. Order therefore matters: a specific name must come before any broader name
that substring-matches it. `Alexa 488` comes before any entry that `488` would
match.

`BF` and `TL` match as a whole word instead. Two letters appear inside too many
other strings. `BF` sits inside `subfield`. `TL` sits inside `TLR4-GFP`, a gene
name, and a substring match would gray a GFP channel.

A transmitted-light channel carries no wavelength, so the parse can never reach
it. The brightfield entries are the only way such a channel gets gray.

The table is public. `pyphenix` imports it from here rather than keeping a copy.

## The color ladder

Each slot owns one representative excitation wavelength.

| Slot | Representative (nm) | In the base set |
| --- | --- | --- |
| blue | 365 | no |
| cyan | 405 | yes |
| green | 480 | yes |
| yellow | 555 | yes |
| red | 600 | no |
| magenta | 650 | yes |

A channel takes the slot with the nearest representative. The base set gives
three boundaries, at the midpoints between neighboring representatives:

- 442.5 nm, between cyan and green.
- 517.5 nm, between green and yellow.
- 602.5 nm, between yellow and magenta.

The code derives these from the representatives. One table governs both the
boundaries and the collision rule below, so neither can drift from the other.

### Why these boundaries

Every boundary sits in an empty gap between the common LED excitation clusters.
No common line (365, 385, 390, 395, 405, 470, 475, 488, 514, 550, 555, 561, 590,
594, 630, 635, 640, 647) sits near one. A boundary that falls on a hardware line
flips color when two adapters round the same line differently.

### Why excitation, not emission

The ladder runs on excitation wavelength, because that is what these channel
names carry. The colors already account for the emission shift. `Ex 390` excites
DAPI, which emits near 460 nm, and cyan reads better than blue against black.

## The parse rules

- A number counts as a wavelength only inside 340 to 800 nm.
- The range is what rejects the numbers that are not wavelengths. `Ch2` gives 2,
  `w1` gives 1 and `20x` gives 20. All three fall outside.
- If the name tags a number with `Ex`, that number wins.
- Without a tag, the lowest in-range number wins. The excitation line of one
  fluorophore is always shorter than its emission line, so `Ex 475 / Em 509` and
  `475/509` both give 475.

## Spare slots and collisions

`blue` and `red` are spares. They stay empty unless a collision forces them.
Red appears only when two channels would otherwise share magenta, or when two
channels would otherwise share yellow.

Two channels in one plate can land in the same base slot. A plate with `Ex 470`
and `Ex 488` would render both channels green, and the merge would then hide one
channel inside the other. That defeats the gate.

When the base slots collide, the whole plate is re-seated across all six slots
under two constraints:

- The slot indices strictly increase. A longer wavelength never takes a color
  earlier in the ladder.
- The sum of the distances from each wavelength to its slot representative is
  the minimum.

A single greedy pass does not satisfy both. A greedy pass that always moves
upward fails when the upward slot is taken and the downward slot is free. The
ladder holds six slots, so the code enumerates every strictly increasing
assignment and takes the cheapest. The search space is bounded by the ladder
size, so the result is exact and deterministic.

Two assignments can cost the same. On an equal cost the base set wins, so a
spare slot opens only when it is strictly cheaper. `blue` in particular reads
dim against black.

### Consistency with the base set

A plate with no collision produces exactly the colors it produced before the
spare slots existed. The code checks the base assignment first and keeps it
while the base slots stay distinct.

### Channels the ladder cannot seat

If more channels parse a wavelength than the ladder holds slots, every parsed
channel falls back to the positional cycle together. One coherent rule beats a
mixed one.

A fixed color survives that fallback. The table and the explicit entry sit above
the ladder in the resolution order, so a `Brightfield` channel stays gray on a
plate of eight channels. Only the ladder gives way.

If only some channels parse, the parsed channels claim their slots first. The
rest take the remaining colors by position and skip the taken ones, so a merge
never gives two channels the same ramp.

### A fixed color does not take part

The collision rule governs the ladder alone. A color that comes from an explicit
`channel_colors` entry or from the fluorophore table stands exactly as given,
and the ladder neither moves it nor avoids it.

This follows from the resolution order. Both rules sit above the ladder, so the
ladder cannot overrule them, and an explicit entry must not shift the colors of
its neighbors.

The cost is a case the ladder cannot fix. A plate with a `DAPI` channel and an
`Ex 390` channel renders both cyan, because the table answers the first and the
ladder answers the second with the same color. The same holds for `Alexa 555`
and `Cy3`, which the table maps to yellow twice.

Such a plate images one dye twice, so it is rare. Accept it for now. To resolve
it, the ladder would have to seat the tabled channels too, which means mapping a
table color back to a slot. That is a larger change than this decision covers.

## Consequences

This changes the default render for any plate whose channel names carry
wavelengths or known fluorophore names. That is the intent of the change. A
consumer that needs the old colors passes them explicitly through
`PlateFacts["channel_colors"]`, which still wins over every other rule.
