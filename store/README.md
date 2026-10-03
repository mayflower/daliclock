# Google Play release

Package `de.mayflower.daliclock`, version `1.0` / code `1`, Wear OS 6+.
The German and English listing copy is in `de-DE.txt` and `en-US.txt`.
No account, price, support contact, countries or public privacy URL has been
selected yet. No Play Console upload has been performed.

## Upload signing

Use the existing app's upload key if this package is already registered.
For a new app, choose an upload key and enroll in Play App Signing in the Console.
Keep the keystore, its passwords and an independent backup outside Git.
Do not use the Android debug key for uploads.

Set these environment variables locally (for example in ignored `.env.release`):

```sh
export DALICLOCK_UPLOAD_STORE_FILE='/absolute/path/to/daliclock-upload.jks'
export DALICLOCK_UPLOAD_STORE_PASSWORD='your-local-password'
export DALICLOCK_UPLOAD_KEY_ALIAS='daliclock-upload'
export DALICLOCK_UPLOAD_KEY_PASSWORD='your-local-password'
```

Then build with signing required:

```sh
source .env.local.sh
source .env.release
./gradlew :watchface:bundleRelease -PrequireReleaseSigning=true \
  -PpythonExecutable="$PWD/.venv/bin/python"
jarsigner -verify watchface/build/outputs/bundle/release/watchface-release.aab
tools/validate_wff.sh
```

Output: `watchface/build/outputs/bundle/release/watchface-release.aab`.
With no signing variables and no `requireReleaseSigning` flag, local builds
remain unsigned. Partial signing configuration fails instead of silently
producing an unsigned release. Never put passwords in command arguments or Git.

## Listing assets

```sh
.venv/bin/python tools/export_store_artwork.py
```

This renders `build/store/icon.png` (512 × 512 RGBA) and
`build/store/feature-graphic.png` (1024 × 500 RGB) from the shared geometry.
The icon shows the circular watch face touching all four edges. The feature
graphic is promotional artwork, not a device screenshot.

Use unmodified native Wear OS screenshots in the Wear OS screenshot section,
square and at least 384 × 384. Include more than one configuration because Daliclock
is customizable. Do not add device frames, transparent masks or captions.
Suggested alt text: “Daliclock with amber digits, hours, minutes and seconds.”

Prepared native captures in `build/store/`:

- `01-amber-24h.png`: amber, 24-hour format, seconds visible.
- `02-amber-12h.png`: amber, 12-hour format with AM, seconds visible.
- `03-always-on.png`: static ambient time after a natural minute rollover.

These are 454 × 454 emulator captures from the previously validated app at
commit `fae27b8`, with opaque alpha removed without altering RGB pixels.
They are not physical-device captures. Source captures are
`build/emulator-visible.png` and
`build/render-fix-rollovers/12-1159-{active,after}.png`.
These older captures predate the landscape background and ring and must be replaced before
uploading the updated listing.

## Preparation status, 2026-10-03

Daliclock artwork rendered and visually inspected. All twelve Python tests,
APK/AAB builds, official WFF 4 schema validation and both memory checks pass.
The debug APK declares `de.mayflower.daliclock` and the label `Daliclock` in
both languages. The release AAB remains unsigned; the build without upload
credentials succeeds, but signing with a real upload key is still pending.
No Console settings or releases have been changed by this preparation.

## Console setup still required

Create an **app**, enable **Wear OS** under form factors, and choose applicable
watch face category tags. Supply the public support contact, price and countries.
Complete the content rating and target audience forms using the actual product.
Daliclock has no ads, accounts, network permissions, analytics or executable app code.
The current source contains no mechanism for collecting or sharing user data;
complete Data safety consistently with the final uploaded bundle.

Provide a public privacy policy identifying the actual publisher and support
contact. It should explain that Daliclock itself does not collect or transmit data,
that time/date come from Wear OS, and that preferences remain on the device.
Do not publish placeholder publisher details or invent a policy URL.

Upload to an internal test track first, install through Play and check the
watch face picker, customization, active morphing, ambient minute changes and
wake on a physical Wear OS 6 watch. Physical-watch performance and battery use
have not been tested; host-Vulkan emulator results do not establish those.
New personal developer accounts may require a closed test with at least
12 opted-in testers for 14 consecutive days before production access.

Sources checked 2026-10-03:

- [Watch face publishing](https://support.google.com/googleplay/android-developer/answer/13560201)
- [Wear OS quality and watch face icons](https://developer.android.com/develop/adaptive-apps/quality-guidelines/wear-app-quality)
- [Preview asset requirements](https://support.google.com/googleplay/android-developer/answer/9866151)
- [Personal-account testing](https://support.google.com/googleplay/android-developer/answer/14151465)
