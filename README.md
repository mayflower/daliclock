# Daliclock

A Wear OS watchface with connected, curve-based digit morphing, inspired by
xdaliclock. Target: Watch Face Format 4 on Wear OS 6 / API 36 or newer.

## Status

The digits are derived from XDaliClock's original `dalifont.ai` artwork,
including its thick–thin contrast and serifs. The original vectors, permission
notice, and provenance are in [assets/glyphs/xdaliclock](assets/glyphs/xdaliclock/SOURCE.md).
The connected line approximation has 98.3–99.4% silhouette overlap with the
original at 4× resolution; it is not pixel-exact at arbitrarily large sizes.

Active digits interpolate both position and stroke width with native 650 ms
animations with cubic-Bezier easing (`0.65 0 0.25 1`): a slow start,
fast deformation, and a smooth arrival at the exact target. Position and width
share the same easing so connected endpoints remain coordinated. Always-on uses build-rendered static images of the same geometry,
rendered together as a native bitmap-font time field. Updating the whole field
keeps unchanged digits and the colon visible at minute changes. This avoids
duplicating thousands of static expressions: an all-vector ambient version exhausted the emulator's
192 MB Java heap even though the official graphics-memory evaluator passed.

Ten Python tests, Android APK/AAB builds, the official WFF 4 schema validator,
and official APK/AAB memory checks pass. The debug APK is debug-signed;
the release AAB is unsigned unless upload signing is configured as described in
[store/README.md](store/README.md).

The current font renders with Skia Vulkan on the dedicated Wear OS 6 emulator
using the Apple M4 host GPU (MoltenVK). The software Vulkan paths (Lavapipe and
SwiftShader) stall or crash in Skia path tessellation with this detailed font;
use the tested host configuration in SETUP.md. Native captures cover active
morphing, ambient entry, minute updates, and wake. Natural ambient rollovers
08:59 → 09:00 and 11:59 → 12:00 in 12-hour mode, and 23:59 → 00:00 in
24-hour mode retain all required digits and the colon. The original geometry
and animations are unchanged by the renderer fix. The subsequent cubic-Bezier
change was also captured on the native renderer. Overshooting the target
produced persistent bulges in digits 2 and 7 on Wear OS 6; keeping the easing
in the 0–1 range fixes their native silhouettes. After installing it, the
existing renderer stalled in garbage collection; restarting the runtime and
reselecting Daliclock restored rendering without changing the animation.
Physical-watch performance, accessibility-service behavior, and battery use
remain untested; no frame-rate or battery-saving claims are made.

## Start here

- [store/README.md](store/README.md): Google Play listing copy, artwork and upload signing.
- [prompts.md](prompts.md): complete product specification and five implementation steps,
  based on the supplied prompt set, with the requested name and easing updates.
- [AGENTS.md](AGENTS.md): repository working agreements and implementation constraints.
- [SETUP.md](SETUP.md): installed tools, pinned versions, validation commands,
  and the tested Wear OS emulator configuration.

On the prepared machine, from this directory:

```sh
source .env.local.sh
source .venv/bin/activate
```

To recreate the Python environment with Python 3.13:

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
```

The local activation file, SDK, virtual environment, external validation tools,
and sample artifacts are not committed. See SETUP.md for their locations.
Build and check from this directory:

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python tools/preview_morphs.py
./gradlew :watchface:assembleDebug :watchface:bundleRelease \
  -PpythonExecutable="$PWD/.venv/bin/python"
tools/validate_wff.sh
```

The build runs the resource generator automatically. Open `build/preview/index.html`
for the offline player and `build/preview/overview.svg` for all transition samples.
`build/preview/classic-comparison.png` pairs each original digit with Daliclock’s output.
The preview is a development tool; it is not proof of native renderer behavior.
The geometry tests include a conservative weighted ambient-pixel activation
bound across all digit combinations at 384 px and 454 px, below
the [15% requirement](https://developer.android.com/docs/quality-guidelines/wear-app-quality#performance-and-functionality).
This uses rasterized gray strokes and RGB intensity, not a count of nonblack
pixels.

The generated scene contains 3,774 lines, 11,310 native animations (coordinates
and thickness), and 7,536 references. XML size is 8,343,202 bytes. Both APK and
AAB pass the official 100 MB active / 10 MB ambient graphics-memory limits; this check does not
measure renderer Java-heap use or runtime performance.

Artifacts:

- `watchface/build/outputs/apk/debug/watchface-debug.apk` (debug-signed)
- `watchface/build/outputs/bundle/release/watchface-release.aab` (unsigned)

With the dedicated emulator running:

```sh
adb -s emulator-5580 install -r watchface/build/outputs/apk/debug/watchface-debug.apk
adb -s emulator-5580 shell am broadcast \
  -a com.google.android.wearable.app.DEBUG_SURFACE \
  --es operation set-watchface --es watchFaceId de.mayflower.daliclock
```

The selection command follows Google's [WFF codelab](https://developer.android.com/codelabs/watch-face-format).
Alternatively select Daliclock through the watchface picker. No release signing key
or publishing account is needed for these local builds.

## Intended implementation

Locally stored curves for all ten digits feed a small Python geometry library.
The preview and WFF exporter use the same sampled lines. Shared points have one
native animation owner; connected endpoints follow through WFF references.
The installed watchface is a resource-only package rendered by Wear OS.

The product shows HH:MM, optional morphing seconds enabled by default, an
optional date, three color themes, system 12/24-hour time, and German/English
editor labels. Always-on renders the current static hours and minutes in one
native text field using build-rendered glyphs.
