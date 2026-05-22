# RetroTap

RetroTap is a local-network LaunchBox companion app for launching games from a browser, phone, or NFC workflow. It reads your LaunchBox library, builds searchable platform/game pages, and can launch games on the PC or hand off playable games to an Android phone through MacroDroid + RetroArch.

> RetroTap is intended for personal libraries on your own private network. Only use ROM download/launch features with games and files you are legally allowed to use.

## Features

- **LaunchBox library browser**: Browse platforms, genres, favorites, and recent plays.
- **PC game launching**: Start LaunchBox/RetroArch games from a web page.
- **Phone play support**: Generate MacroDroid URLs that can open RetroArch on Android with the selected core and ROM path.
- **NFC-friendly URLs**: Write a game URL to an NFC tag and open the RetroTap choice page after scanning.
- **ROM download button**: Download the ROM from the local web UI when enabled.
- **Favorites and recent plays**: Track commonly used games locally.
- **Cache/database support**: Builds a local cache from LaunchBox metadata for faster browsing.
- **Desktop control panel**: Tkinter GUI for starting/stopping the server and opening common pages.
- **Debug logging toggle**: Enable logs when troubleshooting, then disable for normal use.
- **Responsive templates**: Web pages are designed for desktop and phone browsers.

## Project layout

```text
RetroTap/
├─ launchbox_server.py          # Main Flask server
├─ retrotap_control_panel.py    # Desktop GUI control panel
├─ launchbox_library.py         # LaunchBox XML/library parsing
├─ cache_db.py                  # SQLite cache helpers
├─ server_helpers.py            # Shared state/cache helpers
├─ app_config.py                # Runtime config loader/saver
├─ user_settings.py             # Easy first-run defaults
├─ templates/                   # Flask HTML templates
├─ static/                      # CSS and RetroTap images
├─ docs/                        # Setup and usage docs
└─ *.bat                        # Windows launch helpers
```

## Requirements

- Windows PC running LaunchBox
- Python 3.10+
- Local network access between your PC and phone if using phone/NFC features
- Optional for phone play: Android phone, RetroArch, and MacroDroid

Install Python packages:

```bash
pip install -r requirements.txt
```

## Quick start

1. Download or clone this repo.
2. Edit `user_settings.py` and set `LAUNCHBOX_FOLDER` to your LaunchBox folder.
3. Install dependencies with `pip install -r requirements.txt`.
4. Start RetroTap with `Start_RetroTap_GUI.bat` or run:

   ```bash
   python retrotap_control_panel.py
   ```

5. Click **Start Server** in the GUI.
6. Open the local or network URL shown in the GUI.
7. Use the Settings page to confirm your LaunchBox path and optional phone settings.

See [docs/SETUP.md](docs/SETUP.md) for full setup instructions.

## NFC usage

Write a RetroTap game URL to an NFC tag, such as:

```text
http://YOUR_PC_IP:5000/game/tmnt_nes
```

When scanned, the phone opens the game page and can show PC launch, phone launch, and download options depending on the game and settings.

## Documentation

- [Setup guide](docs/SETUP.md)
- [Configuration reference](docs/CONFIGURATION.md)
- [Phone play with MacroDroid](docs/PHONE_PLAY.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Security notes](docs/SECURITY.md)
- [Contributing](CONTRIBUTING.md)

## Important notes

- Keep RetroTap on your private home network unless you understand the security risks.
- Do not expose this server directly to the public internet.
- The ROM download feature is powerful and should only be used for your own legal files.
- `config.json`, caches, logs, and database files are intentionally ignored by Git.

## License

This project is released under the MIT License. See [LICENSE](LICENSE).
