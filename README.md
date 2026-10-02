# Melt

A Wear OS watchface with connected, curve-based digit morphing, inspired by
xdaliclock. Target: Watch Face Format 4 on Wear OS 6 / API 36 or newer.

## Status

The digits are derived from XDaliClock's original `dalifont.ai` artwork,
including its thick–thin contrast and serifs. The original vectors, permission
notice, and provenance are in [assets/glyphs/xdaliclock](assets/glyphs/xdaliclock/SOURCE.md).
The connected line approximation has 98.3–99.4% silhouette overlap with the
original at 4× resolution; it is not pixel-exact at arbitrarily large sizes.

Active digits interpolate both position and stroke width with native 650 ms
animations. Always-on uses build-rendered static images of the same geometry,
selected by native current-time conditions. This avoids duplicating thousands
of static expressions: an all-vector ambient version exhausted the emulator's
192 MB Java heap even though the official graphics-memory evaluator passed.

Nine Python tests, Android APK/AAB builds, the official WFF 4 schema validator,
and official APK/AAB memory checks pass. The debug APK is debug-signed;
the release AAB is unsigned.

The current font was rendered on the Wear OS 6 emulator with Skia OpenGL.
Native captures show the active font, seconds, the 09:41 → 09:42 rollover,
always-on, and wake. However, OpenGL drops unchanged ambient content after a
minute update; the previously working software Vulkan backend stalls with
this denser font. The current native rendering check is therefore **partial**.
This build needs further renderer/performance work before release. Physical-watch
performance, accessibility-service behavior, and battery use remain untested;
no frame-rate or battery-saving claims are made.

## Start here

- [prompts.md](prompts.md): complete product specification and five implementation steps,
  copied unchanged from the supplied prompt set.
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
`build/preview/classic-comparison.png` pairs each original digit with Melt’s output.
The preview is a development tool; it is not proof of native renderer behavior.
The geometry tests include a conservative weighted ambient-pixel activation
bound across all digit combinations at 384 px and 454 px, below
the [15% requirement](https://developer.android.com/docs/quality-guidelines/wear-app-quality#performance-and-functionality).
This uses rasterized gray strokes and RGB intensity, not a count of nonblack
pixels.

The generated scene contains 3,774 lines, 11,310 native animations (coordinates
and thickness), and 7,536 references. XML size is 7,955,192 bytes. The official
memory evaluator reports 2,790,064 bytes active and 810,000 bytes ambient;
these figures do not measure renderer Java-heap use or runtime performance.

Artifacts:

- `watchface/build/outputs/apk/debug/watchface-debug.apk` (debug-signed)
- `watchface/build/outputs/bundle/release/watchface-release.aab` (unsigned)

With the dedicated emulator running:

```sh
adb -s emulator-5580 install -r watchface/build/outputs/apk/debug/watchface-debug.apk
adb -s emulator-5580 shell am broadcast \
  -a com.google.android.wearable.app.DEBUG_SURFACE \
  --es operation set-watchface --es watchFaceId de.mayflower.melt
```

The selection command follows Google's [WFF codelab](https://developer.android.com/codelabs/watch-face-format).
Alternatively select Melt through the watchface picker. No release signing key
or publishing account is needed for these local builds.

## Intended implementation

Locally stored curves for all ten digits feed a small Python geometry library.
The preview and WFF exporter use the same sampled lines. Shared points have one
native animation owner; connected endpoints follow through WFF references.
The installed watchface is a resource-only package rendered by Wear OS.

The product shows HH:MM, optional morphing seconds enabled by default, an
optional date, three color themes, system 12/24-hour time, and German/English
editor labels. Always-on selects the current static hours and minutes from build-rendered glyphs.
