# Troubleshooting

## Server will not start

- Run `pip install -r requirements.txt`.
- Make sure another app is not already using port `5000`.
- Try running `python launchbox_server.py` in a terminal to see the error.

## LaunchBox games do not appear

- Confirm `LAUNCHBOX_FOLDER` points to the correct folder.
- Use the Settings page to update the path.
- Rebuild/refresh the library cache.
- Check debug logs if enabled.

## Game launch gives a server error

- Confirm the ROM path still exists.
- Confirm the emulator path still exists.
- Confirm LaunchBox metadata has the correct emulator/application command.
- Enable debug logging and retry so the log captures the failing command.

## Phone launch button is missing

- Phone play may be disabled.
- MacroDroid URL may be blank.
- The selected game's emulator/platform may not be mapped to an Android RetroArch core.
- The game may be downloadable but not phone-playable.

## Phone launch opens the wrong core

Edit `RETROARCH_ANDROID_CORES` in `user_settings.py` or update the phone settings in RetroTap.

## NFC tag opens the wrong address

Use your PC network IP, not `127.0.0.1`. Example:

```text
http://192.168.1.100:5000/game/example_game_id
```

`127.0.0.1` means the current device, so on a phone it points to the phone, not the PC.
