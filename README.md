# Melt

A Wear OS watchface with connected, curve-based digit morphing, inspired by
xdaliclock. Target: Watch Face Format 4 on Wear OS 6 / API 36 or newer.

## Status

The shared geometry, offline morph preview, WFF exporter, native settings,
and Android resource build are implemented. The debug APK installs and runs on
the Wear OS 6 emulator; the release AAB is unsigned.

Fixed: ambient reference consumers could lag behind their owners at minute
changes on Wear OS 6. Static consumers now also subscribe to their owner's time
source, while taking the coordinate exclusively from their own ambient reference.
Native captures passed 20:10 → 20:11 and the four-digit 09:59 → 10:00 rollover.

Native checks covered hour carries, midnight, noon AM/PM, the single-digit
12-hour layout, colors, persisted seconds/date options, ambient and waking,
and timezone changes. A further 110-frame capture spans a minute rollover.
The offline transition overview and native intermediate forms were reviewed.

On this Mac, the emulator's Skia OpenGL backend intermittently omitted unchanged
digits and even content in the system charging screen. Use the tested software
Vulkan configuration in SETUP.md: the subsequent timezone, rollover, editor,
and ambient checks retained the expected content. This is an emulator setup
limitation; other graphics backends have not passed the same checks.

An isolated 16.6-second native-renderer `dumpsys gfxinfo` sample recorded 180
frames with CPU/HWUI histogram p50/p95/p99 of 11/15/20 ms. These are emulator
measurements, not physical-watch performance or proof of sustained 30 fps.
The GPU timing histogram was empty, so no GPU percentiles are reported.
Physical-watch performance, accessibility service behavior, and battery use
are not tested. No battery savings are claimed.

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
The preview is a development tool; it is not proof of native renderer behavior.
The geometry tests include a conservative weighted ambient-pixel activation
bound across all digit combinations: 3.276% at 384 px and 3.281% at 454 px, below
the [15% requirement](https://developer.android.com/docs/quality-guidelines/wear-app-quality#performance-and-functionality).
This uses rasterized gray strokes and RGB intensity, not a count of nonblack
pixels.

The generated scene contains 1,326 lines, 1,504 animated coordinates, and 2,632
references. XML size is 2,439,039 bytes. The official memory evaluator reports
2,371,712 bytes active and 810,000 bytes ambient; both APK and AAB pass its limits.

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
editor labels. Always-on shows the current static hours and minutes.
