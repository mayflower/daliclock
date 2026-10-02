# Melt development environment

Prepared and exercised on 2026-10-02 on this Apple Silicon Mac. This document records the environment setup. See README.md for the current
Melt implementation status and application build commands.

## Use the installed tools

From this directory:

```sh
source .env.local.sh
source .venv/bin/activate
```

The machine-local activation file configures Java, the Android SDK, Gradle,
and the two official WFF tool JAR paths. It does not modify the global shell
configuration. Python graphics dependencies are pinned in `requirements-dev.txt`.

## Tested versions and locations

| Component | Version / location |
| --- | --- |
| JDK | Homebrew OpenJDK 17.0.20.1 |
| Gradle for Melt | 8.13, `$MELT_TOOLS/gradle-8.13` |
| Android Gradle Plugin | 8.13.2, downloaded and tested in the sample build |
| Android SDK | `$ANDROID_HOME` = `/Users/johann/Library/Android/sdk` |
| Android platform | API 36, revision 2 |
| SDK Build Tools | 36.0.0 |
| SDK Command-line Tools | 23.0 |
| Android CLI | 1.0.16486076 |
| Platform Tools / ADB | 37.0.1 |
| Emulator | 37.2.12, hardware acceleration available |
| Wear image | `system-images;android-36;android-wear-signed;arm64-v8a`, revision 1 |
| Python | 3.13.15 in `.venv` |
| SVG / raster support | CairoSVG 2.9.1, Pillow 12.3.0, Homebrew Cairo 1.18.4 |
| Browsers | Chrome and Safari installed |

The JDK/Gradle/AGP combination follows the
[official AGP 8.13 compatibility table](https://developer.android.com/build/releases/agp-8-13-0-release-notes).
The application build pins these versions and SDK Build Tools 36.0.0 and
includes the Gradle 8.13 wrapper.

## Official WFF tools

`$MELT_TOOLS` is `/Users/johann/.local/share/melt-tools`.
The [Google watchface tools](https://github.com/google/watchface) checkout is
`$MELT_TOOLS/watchface`, detached at commit
`b6cdda0acd3e4c5d0be5624fcdc01209380029d1`.
Both JARs were built using the upstream Gradle 8.9 wrappers and JDK 17.
The WFF 4 Line and Stroke XSD blob hashes match those in the prompt set.

```sh
java -jar "$WFF_VALIDATOR_JAR" 4 path/to/watchface.xml
java -jar "$WFF_MEMORY_JAR" --watch-face path/to/watchface.apk \
  --schema-version 4 --ambient-limit-mb 10 --active-limit-mb 100 \
  --apply-v1-offload-limitations --estimate-optimization
```

The memory evaluator also accepts AAB files. These are the upstream documented
invocations, exercised against the sample artifacts below.

## Wear OS emulator

A dedicated round 454 x 454 device named `Melt_Wear_OS_6` is configured.
It booted completely, reported API 36 and the Wear watchface runtime, displayed
its default watchface, and successfully installed the sample APK through ADB.
The original, simpler Melt geometry was tested with software graphics and the
guest Skia Vulkan renderer. The current XDaliClock-derived font stalls on this
backend; OpenGL displays it but still drops unchanged ambient content. See
README.md for the current partial native-validation status.
The initial SwiftShader setup could boot and install packages, but subsequent
Melt and system-UI checks exposed disappearing static content with Skia OpenGL.
The earlier tested combination below uses Lavapipe for Vulkan on this Mac.

```sh
# Run in a separate terminal; remove -no-window to show the emulator window.
emulator -avd Melt_Wear_OS_6 -port 5580 -gpu software \
  -no-window -no-audio -no-snapshot

# Target this emulator explicitly; a physical Android phone may also be attached.
adb -s emulator-5580 shell getprop sys.boot_completed
adb -s emulator-5580 shell setprop debug.hwui.renderer skiavk
adb -s emulator-5580 shell am force-stop com.google.wear.watchface.runtime
adb -s emulator-5580 install -r path/to/watchface.apk
# Select another watchface in the picker, then select Melt.
adb -s emulator-5580 shell dumpsys gfxinfo com.google.wear.watchface.runtime
# Confirm Pipeline=Skia (Vulkan) in that output.
```

Set the renderer after each cold boot, before selecting Melt; the property is
not persistent. If Melt was already selected before stopping the runtime,
switch to a different face and back to recreate its service. Allow initialization
to finish before capturing. Stop the emulator with
`adb -s emulator-5580 emu kill` when finished. A physical Wear OS watch was
not connected. The pre-existing phone AVD has a missing API 36.1 phone image;
that unrelated AVD was left unchanged.

## Setup verification

A copy of Google's sample was built outside this workspace at
`$MELT_TOOLS/build-smoke`, using API 36 and WFF 4. Both builds succeeded:

```sh
gradle -p "$MELT_TOOLS/build-smoke" :app:assembleDebug :app:bundleRelease
```

Artifacts:

- `$MELT_TOOLS/build-smoke/app/build/outputs/apk/debug/app-debug.apk`
- `$MELT_TOOLS/build-smoke/app/build/outputs/bundle/release/app-release.aab`

The APK is debug-signed; the release AAB is unsigned. Both contain no DEX code.
The sample needed `minifyEnabled true` with `shrinkResources false` for both
build types to remove generated classes while preserving watchface resources.
Both artifacts passed the official memory evaluator; the sample XML passed
the version-4 validator. SVG-to-PNG rendering and PNG loading also worked.

These artifacts are environment probes, not Melt. They do not establish Melt's
geometry, animation, editor behavior, ambient behavior, pixel activation, or
hardware performance. See README.md for implementation and runtime-test status.
The default emulator watchface screenshot
is saved at `$MELT_TOOLS/wear-os-6.png`.
