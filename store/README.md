# Google Play release

Package `de.mayflower.daliclock`, version `1.0` / code `1`, Wear OS 6+.
The German and English listing copy is in `de-DE.txt` and `en-US.txt`.
Manage account details, pricing, distribution, and releases in Play Console.

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

Capture the current build before submitting a listing. Older local screenshots
predate the landscape background and ring.

## Play Console

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
Follow the testing requirements shown for your developer account in Play Console.

Sources checked 2026-10-03:

- [Watch face publishing](https://support.google.com/googleplay/android-developer/answer/13560201)
- [Wear OS quality and watch face icons](https://developer.android.com/develop/adaptive-apps/quality-guidelines/wear-app-quality)
- [Preview asset requirements](https://support.google.com/googleplay/android-developer/answer/9866151)
- [Personal-account testing](https://support.google.com/googleplay/android-developer/answer/14151465)
