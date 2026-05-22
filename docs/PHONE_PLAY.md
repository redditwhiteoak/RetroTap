# Phone play with MacroDroid and RetroArch

Phone play is optional. It is designed for Android phones running RetroArch and MacroDroid.

## Overview

RetroTap builds a MacroDroid URL that includes:

- Android RetroArch core path
- Android ROM path
- Optional callback URL back to the RetroTap server

MacroDroid receives the URL and uses the parameters to launch RetroArch.

## Basic setup

1. Install RetroArch on Android.
2. Install the RetroArch cores you want to use.
3. Install MacroDroid.
4. Create a MacroDroid HTTP/webhook trigger such as:

```text
http://PHONE_IP:8080/retroarch
```

5. In RetroTap Settings, enter that URL as the MacroDroid trigger URL.
6. Confirm the Android ROM folder and core folder paths match your phone.

## URL parameters sent by RetroTap

RetroTap sends values such as:

```text
core=...
rom=...
callback=...
callback_url=...
```

Your MacroDroid macro should read those query parameters and use them in a **Send Intent** or app-launch action for RetroArch.

## Notes

- Your phone and PC usually need to be on the same local network.
- The phone IP may change unless you reserve it in your router.
- Core filenames can vary by RetroArch version. Edit `RETROARCH_ANDROID_CORES` if a platform opens with the wrong core.
- If a game cannot be played on phone, RetroTap can still show download options while hiding the phone launch button.
