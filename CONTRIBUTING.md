# Contributing

Thanks for helping improve RetroTap.

## Good first contributions

- Add platform mappings or RetroArch core mappings.
- Improve setup instructions for different LaunchBox layouts.
- Improve mobile layout or accessibility.
- Add clearer troubleshooting messages.
- Test with more emulators and platforms.

## Development setup

```bash
git clone https://github.com/YOUR_USERNAME/RetroTap.git
cd RetroTap
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python retrotap_control_panel.py
```

## Pull request checklist

- Do not commit `config.json`, caches, logs, ROMs, or personal paths.
- Keep settings that other users need to change in `user_settings.py` or the web Settings page.
- Test the server starts without a pre-existing cache.
- Test both the GUI startup path and terminal startup path when possible.
