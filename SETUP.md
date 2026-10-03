# Daliclock development environment

Tested toolchain and emulator configuration for Apple Silicon macOS.
For build commands, see [README.md](README.md#build).

## Use the installed tools

If you have the local activation file used for this checkout:

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
| Gradle for Daliclock | 8.13, `$DALICLOCK_TOOLS/gradle-8.13` |
| Android Gradle Plugin | 8.13.2 |
| Android SDK | `$ANDROID_HOME` (usually `$HOME/Library/Android/sdk` on macOS) |
| Android platform | API 36, revision 2 |
| SDK Build Tools | 36.0.0 |
| SDK Command-line Tools | 23.0 |
| Android CLI | 1.0.16486076 |
| Platform Tools / ADB | 37.0.1 |
| Emulator | 37.2.12, hardware acceleration available |
| Wear image | `system-images;android-36;android-wear-signed;arm64-v8a`, revision 1 |
| Python | 3.13.15 in `.venv` |
| SVG / raster support | CairoSVG 2.9.1, Pillow 12.3.0, Homebrew Cairo 1.18.4 |

The JDK/Gradle/AGP combination follows the
[official AGP 8.13 compatibility table](https://developer.android.com/build/releases/agp-8-13-0-release-notes).
The application build pins these versions and SDK Build Tools 36.0.0 and
includes the Gradle 8.13 wrapper.

## Official WFF tools

This checkout uses `$DALICLOCK_TOOLS` = `$HOME/.local/share/melt-tools`.
On another machine, choose a local tools directory and set that variable.
The [Google watchface tools](https://github.com/google/watchface) checkout is
`$DALICLOCK_TOOLS/watchface`, detached at commit
`b6cdda0acd3e4c5d0be5624fcdc01209380029d1`.
Build both JARs using the upstream Gradle 8.9 wrappers and JDK 17, then set
`WFF_VALIDATOR_JAR` and `WFF_MEMORY_JAR` to their absolute paths.

```sh
java -jar "$WFF_VALIDATOR_JAR" 4 path/to/watchface.xml
java -jar "$WFF_MEMORY_JAR" --watch-face path/to/watchface.apk \
  --schema-version 4 --ambient-limit-mb 10 --active-limit-mb 100 \
  --apply-v1-offload-limitations --estimate-optimization
```

The memory evaluator also accepts AAB files.

## Wear OS emulator

The existing round 454 x 454 AVD retains its machine-local name
`Melt_Wear_OS_6`; it is used to test Daliclock. The installed tools likewise
retain their existing `melt-tools` directory.
Daliclock's original-font renderer is tested with **host Vulkan** on this Apple M4:
`-gpu host` selects MoltenVK, and `debug.hwui.renderer=skiavk` selects Vulkan
inside Android. The local AVD defaults to host graphics; keep both settings. The software Vulkan backends (Lavapipe and
SwiftShader) stall or crash in Skia path tessellation with the detailed font.
Skia OpenGL also exhibits disappearing static content. Changing HWUI buffer-age
or partial-update properties did not fix that issue.

The watchface separately fixes ambient invalidation by drawing HH:MM as one
bitmap-font text field. The original per-digit PartImages reproduced missing
unchanged digits even with host Vulkan; switching the graphics backend alone
is therefore insufficient.

```sh
# Run in a separate terminal; remove -no-window to show the emulator window.
emulator -avd Melt_Wear_OS_6 -port 5580 -gpu host \
  -no-window -no-audio -no-snapshot

# Target this emulator explicitly; a physical Android phone may also be attached.
adb -s emulator-5580 shell getprop sys.boot_completed
adb -s emulator-5580 shell setprop debug.hwui.renderer skiavk
adb -s emulator-5580 shell am force-stop com.google.wear.watchface.runtime
adb -s emulator-5580 install -r path/to/watchface.apk
# Select another watchface in the picker, then select Daliclock.
adb -s emulator-5580 shell dumpsys gfxinfo com.google.wear.watchface.runtime
# Confirm Pipeline=Skia (Vulkan) in that output.
```

Set the renderer after each cold boot, before selecting Daliclock; the property is
not persistent. The host GLES driver reports only GLES 3.0 on this Mac, so do
not rely on the default OpenGL renderer for this API 36 image. If Daliclock was
already selected before stopping the runtime,
switch to a different face and back to recreate its service. Allow initialization
to finish before capturing. Stop the emulator with
`adb -s emulator-5580 emu kill` when finished.
