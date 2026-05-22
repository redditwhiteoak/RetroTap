import json
import os

try:
    import user_settings
except Exception:
    user_settings = None


CONFIG_FILE = "config.json"


def setting(name, fallback):
    if user_settings and hasattr(user_settings, name):
        return getattr(user_settings, name)

    return fallback


DEFAULT_CONFIG = {
    "launchbox_folder": setting("LAUNCHBOX_FOLDER", r"D:\LaunchBox"),
    "auto_launch": setting("AUTO_LAUNCH", False),
    "rom_downloads_enabled": setting("ROM_DOWNLOADS_ENABLED", True),

    "phone_play_enabled": setting("PHONE_PLAY_ENABLED", True),
    "macrodroid_trigger_url": setting("MACRODROID_TRIGGER_URL", ""),
    "android_rom_folder": setting("ANDROID_ROM_FOLDER", "storage/emulated/0/Download"),
    "android_retroarch_config": setting(
        "ANDROID_RETROARCH_CONFIG",
        "data/user/0/com.retroarch/files/retroarch.cfg"
    ),
    "android_retroarch_core_folder": setting(
        "ANDROID_RETROARCH_CORE_FOLDER",
        "data/user/0/com.retroarch/cores"
    ),
    "retroarch_android_cores": setting("RETROARCH_ANDROID_CORES", {
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
    }),

    "allowed_ips": setting("ALLOWED_IPS", []),
    "logging_enabled": setting("LOGGING_ENABLED", False)
}


def load_config():
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        config = dict(DEFAULT_CONFIG)
        config.update(loaded)

        return config

    except Exception:
        return dict(DEFAULT_CONFIG)


def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)


def get_launchbox_folder():
    return load_config().get("launchbox_folder", DEFAULT_CONFIG["launchbox_folder"])


def set_launchbox_folder(path):
    config = load_config()
    config["launchbox_folder"] = path
    save_config(config)


def auto_launch_enabled():
    return bool(load_config().get("auto_launch", False))


def set_auto_launch(enabled):
    config = load_config()
    config["auto_launch"] = bool(enabled)
    save_config(config)


def rom_downloads_enabled():
    return bool(load_config().get("rom_downloads_enabled", True))


def get_allowed_ips():
    return load_config().get("allowed_ips", [])


def phone_play_enabled():
    return bool(load_config().get("phone_play_enabled", True))


def get_macrodroid_trigger_url():
    return load_config().get("macrodroid_trigger_url", "")


def set_macrodroid_trigger_url(url):
    config = load_config()
    config["macrodroid_trigger_url"] = url
    save_config(config)


def get_android_rom_folder():
    return load_config().get(
        "android_rom_folder",
        DEFAULT_CONFIG["android_rom_folder"]
    )


def set_android_rom_folder(path):
    config = load_config()
    config["android_rom_folder"] = path
    save_config(config)


def get_android_retroarch_config():
    return load_config().get(
        "android_retroarch_config",
        DEFAULT_CONFIG["android_retroarch_config"]
    )


def set_android_retroarch_config(path):
    config = load_config()
    config["android_retroarch_config"] = path
    save_config(config)


def get_android_retroarch_core_folder():
    return load_config().get(
        "android_retroarch_core_folder",
        DEFAULT_CONFIG["android_retroarch_core_folder"]
    )


def set_android_retroarch_core_folder(path):
    config = load_config()
    config["android_retroarch_core_folder"] = path
    save_config(config)


def get_retroarch_android_core(platform):
    config = load_config()
    cores = config.get("retroarch_android_cores", {})

    return cores.get(platform, "")


def build_android_core_path(platform):
    core_folder = get_android_retroarch_core_folder().rstrip("/")
    core_name = get_retroarch_android_core(platform)

    if not core_name:
        return ""

    if "/" in core_name:
        return core_name

    return core_folder + "/" + core_name



def logging_enabled():
    return bool(load_config().get("logging_enabled", False))


def set_logging_enabled(enabled):
    config = load_config()
    config["logging_enabled"] = bool(enabled)
    save_config(config)
