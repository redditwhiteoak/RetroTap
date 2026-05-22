# Configuration reference

RetroTap has two configuration layers:

1. `user_settings.py` contains first-run defaults and easy-to-edit values.
2. `config.json` is created at runtime and stores values changed in the web Settings page.

`config.json` is ignored by Git so your local paths and network settings are not uploaded.

## Common settings

### `LAUNCHBOX_FOLDER`

Path to your LaunchBox install folder.

```python
LAUNCHBOX_FOLDER = r"D:\LaunchBox"
```

### `PORT`

The Flask server port. Default is `5000`.

```python
PORT = 5000
```

### `AUTO_LAUNCH`

If `True`, game URLs launch immediately instead of showing the choice page.

```python
AUTO_LAUNCH = False
```

### `ROM_DOWNLOADS_ENABLED`

Shows/hides ROM download options in the web UI.

```python
ROM_DOWNLOADS_ENABLED = True
```

### `PHONE_PLAY_ENABLED`

Enables Android/MacroDroid phone play links.

```python
PHONE_PLAY_ENABLED = True
```

### `MACRODROID_TRIGGER_URL`

Your phone's MacroDroid HTTP trigger URL.

```python
MACRODROID_TRIGGER_URL = "http://192.168.1.50:8080/retroarch"
```

Leave it blank until you configure MacroDroid.

### `ANDROID_ROM_FOLDER`

Android path where RetroArch can find downloaded ROMs.

```python
ANDROID_ROM_FOLDER = "storage/emulated/0/Download"
```

### `RETROARCH_ANDROID_CORES`

Maps LaunchBox platform names to Android RetroArch core filenames. Edit these if your installed core names differ.
