# Android delivery plan

## Target artifact

The normal Android deliverable is an APK for personal installation. AAB is
used for store distribution. `zpk` is not the normal Android artifact; if it
refers to a specific device platform, its exact platform and signing tool must
be confirmed before release packaging.

## Planned architecture

1. Keep the FastAPI learning engine as a versioned HTTP/SSE service.
2. Build the React frontend as a mobile-first web bundle.
3. Package that bundle with Capacitor into an Android APK.
4. Provide `API_BASE_URL` as a runtime setting so the APK can connect to a
   private server, a LAN computer, or a local tunnel without changing code.
5. Add native Capacitor adapters for microphone recording, ASR, audio playback,
   and TTS only after the model and speech providers are selected.

## Personal offline option

An APK containing the frontend alone still needs a FastAPI process somewhere.
For a fully offline APK, the backend must be ported to an Android-compatible
runtime such as a Chaquopy Python service or replaced with native Kotlin
implementations. That is a separate release target and should be chosen after
the online/mobile API is stable.

## Release checks

- `npm run build` passes.
- Capacitor Android project builds with `assembleDebug`.
- Android device can complete onboarding, start a session, submit a turn, and
  display the cited grammar report.
- API URL, database path, provider keys, and debug logs are not hard-coded into
  the APK.
- A signed release build is tested on the target Android version.
