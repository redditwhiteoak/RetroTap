# Setup guide

## 1. Install Python

Install Python 3.10 or newer from python.org. During install, enable **Add Python to PATH**.

Check it:

```bash
python --version
```

## 2. Download RetroTap

Download the repo as a ZIP from GitHub or clone it:

```bash
git clone https://github.com/YOUR_USERNAME/RetroTap.git
cd RetroTap
```

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

## 4. Configure LaunchBox path

Open `user_settings.py` and change this line:

```python
LAUNCHBOX_FOLDER = r"D:\LaunchBox"
```

Set it to your actual LaunchBox folder.

## 5. Start the GUI

Double-click:

```text
Start_RetroTap_GUI.bat
```

Or run:

```bash
python retrotap_control_panel.py
```

The GUI shows the local URL and network URL. Use the network URL from your phone.

## 6. Build/load the library

Open RetroTap in a browser. The first library load may take longer while it reads LaunchBox metadata, images, and game paths. After the cache is created, later loads should be faster.

## 7. Optional phone/NFC setup

For phone play, configure MacroDroid and RetroArch as described in `docs/PHONE_PLAY.md`.
