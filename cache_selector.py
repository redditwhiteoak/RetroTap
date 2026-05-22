import json
import os

# -----------------------------
# Cache file names
# -----------------------------

DEBUG_GAME_CACHE = "game_cache_debug.json"
NORMAL_GAME_CACHE = "game_cache.json"

DEBUG_LIBRARY_CACHE = "library_cache_debug.db"
NORMAL_LIBRARY_CACHE = "library_cache.db"


def _here(filename):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)


def _debug_cache_requested():
    """Debug cache is opt-in so a packaged debug cache cannot hide the full library."""
    if os.environ.get("RETROTAP_DEBUG_CACHE", "").strip().lower() in {"1", "true", "yes", "on"}:
        return True

    config_path = _here("config.json")
    try:
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            return bool(config.get("debug_cache_enabled", False))
    except Exception:
        pass

    return False


def get_game_cache_file():
    """Use the full game cache by default. Use debug cache only when explicitly enabled."""
    debug_path = _here(DEBUG_GAME_CACHE)
    normal_path = _here(NORMAL_GAME_CACHE)

    if _debug_cache_requested() and os.path.exists(debug_path):
        return debug_path

    return normal_path


def get_library_db_file():
    """Use the full SQLite cache by default. Use debug cache only when explicitly enabled."""
    debug_path = _here(DEBUG_LIBRARY_CACHE)
    normal_path = _here(NORMAL_LIBRARY_CACHE)

    if _debug_cache_requested() and os.path.exists(debug_path):
        return debug_path

    return normal_path


def debug_mode_enabled():
    return _debug_cache_requested()


def print_cache_mode():
    if debug_mode_enabled():
        print("[DEBUG MODE] Debug cache explicitly enabled")
    else:
        print("[NORMAL MODE] Using full library cache")

    print(f"[CACHE] Game cache: {get_game_cache_file()}")
    print(f"[CACHE] Library DB:  {get_library_db_file()}")
