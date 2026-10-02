# XDaliClock digit outlines

Original artwork: Jamie Zawinski's XDaliClock, `font/dalifont.ai`.
Source mirror revision: `8d3cfc1061dd74db644f9c57fadc707bed69abde`.
https://github.com/dylex/xdaliclock/blob/8d3cfc1061dd74db644f9c57fadc707bed69abde/font/dalifont.ai

`dalifont.ai` is the original source. The ten SVGs contain its digit paths,
converted with Poppler's `pdftocairo -svg`, translated and uniformly scaled
into a 100 × 160 box with digit height 140. No horizontal font distortion is
applied. These outlines are the visual reference used by the raster tests.

`../melt.json` stores connected medial-axis routes derived from these outlines,
not a substitute system font. Coordinates are x, y, and stroke radius.
Upper bowl/flag, lower bowl/base, and waist routes have shared endpoints and
common sample positions across all ten digits. Local serif branches are
traversed out and back. Linear cubic spans store the sampled routes; short,
round-capped lines reproduce the original tapered shapes approximately.
The preview and active WFF output interpolate both coordinates and thickness.
Always-on images are rendered from the same derived geometry at build time.

Authoring used 4× rasterization, scikit-image 0.25.2 medial_axis with rng=0,
and manual semantic route correspondence. The derived data is checked in;
builds use only the normal Python dependencies and never fetch fonts.

## Upstream permission notice

xdaliclock, Copyright © 1991-2022 Jamie Zawinski.

Permission to use, copy, modify, distribute, and sell this software and its
documentation for any purpose is hereby granted without fee, provided that
the above copyright notice appear in all copies and that both that
copyright notice and this permission notice appear in supporting
documentation. No representations are made about the suitability of this
software for any purpose. It is provided "as is" without express or
implied warranty.

Notice reproduced from the same revision's X11/xdaliclock.c.
