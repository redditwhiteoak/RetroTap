"""
NFC Game Launcher - User Settings

Edit this file first.

These are the values most users need to change when setting up the project.
The app also creates config.json at runtime, but this file makes the important
defaults easy to find before first launch.
"""

# --------------------------------------------------
# PC / LAUNCHBOX SETTINGS
# --------------------------------------------------

# Path to your LaunchBox installation folder.
# Example:
# LAUNCHBOX_FOLDER = r"D:\LaunchBox"
LAUNCHBOX_FOLDER = r"D:\LaunchBox"

# Folder where this Flask launcher project is installed.
# Usually:
# PROJECT_FOLDER = r"C:\nfc_game_launcher"
PROJECT_FOLDER = r"C:\nfc_game_launcher"

# Flask server port.
PORT = 5000


# --------------------------------------------------
# PHONE / MACRODROID SETTINGS
# --------------------------------------------------

# Enable/disable phone play support.
PHONE_PLAY_ENABLED = True

# MacroDroid local/webhook trigger URL.
# Change this to your phone IP and MacroDroid server path.
#
# Example:
# MACRODROID_TRIGGER_URL = "http://192.168.1.50:8080/retroarch"
MACRODROID_TRIGGER_URL = ""

# Android folder where ROMs should be downloaded/moved.
#
# Example:
# ANDROID_ROM_FOLDER = "storage/emulated/0/Download"
ANDROID_ROM_FOLDER = "storage/emulated/0/Download"

# Android RetroArch core folder.
#
# Example:
# ANDROID_RETROARCH_CORE_FOLDER = "data/user/0/com.retroarch/cores"
ANDROID_RETROARCH_CORE_FOLDER = "data/user/0/com.retroarch/cores"

# Android RetroArch config path.
#
# This may vary by RetroArch install/version.
ANDROID_RETROARCH_CONFIG = "data/user/0/com.retroarch/files/retroarch.cfg"


# --------------------------------------------------
# ANDROID RETROARCH CORE MAP
# --------------------------------------------------
# These names may vary depending on your installed RetroArch cores.
# If phone play opens the wrong core, edit the value for that platform.

RETROARCH_ANDROID_CORES = {
    "Nintendo Entertainment System": "nestopia_libretro_android.so",
    "Super Nintendo Entertainment System": "snes9x_libretro_android.so",
    "Nintendo Game Boy": "gambatte_libretro_android.so",
    "Nintendo Game Boy Color": "gambatte_libretro_android.so",
    "Nintendo Game Boy Advance": "mgba_libretro_android.so",
    "Sega Genesis": "genesis_plus_gx_libretro_android.so",
    "Sega Mega Drive": "genesis_plus_gx_libretro_android.so",
    "Sega 32X": "picodrive_libretro_android.so",
    "Sony PlayStation": "pcsx_rearmed_libretro_android.so",
    "Nintendo 64": "mupen64plus_next_gles3_libretro_android.so",
    "Atari 2600": "stella_libretro_android.so",
    "Arcade": "fbneo_libretro_android.so",
}


# --------------------------------------------------
# OPTIONAL SERVER SETTINGS
# --------------------------------------------------

# If True, /game/<game_id> immediately launches instead of showing play options.
AUTO_LAUNCH = False

# Allow downloading ROM files from the web UI.
# Only use on your private/local network.
ROM_DOWNLOADS_ENABLED = True

# Optional IP allowlist.
# Leave empty for normal local network use.
# Example:
# ALLOWED_IPS = ["192.168.1.25", "192.168.1.50"]
ALLOWED_IPS = []
