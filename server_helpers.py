import json
import os
import threading
from datetime import datetime

from app_logging import log_info


CACHE_SAVE_EVERY = 500

games_cache = {}

library_status = {
    "loading": False,
    "last_loaded": None,
    "game_count": 0,
    "message": "Not loaded yet",
    "paused": False,
    "processed_count": 0,
    "total_count": 0
}

# Set to True by /pause-library-refresh. The scanning loop checks this
# between games, saves the partial cache, and stops cleanly.
library_control = {
    "pause_requested": False
}

cache_lock = threading.Lock()
_progress_counter = 0


def status(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")
    log_info(message)


def progress_bar(message, percent):
    bar_length = 40
    filled = int(bar_length * percent / 100)
    bar = "#" * filled + "-" * (bar_length - filled)

    print(
        f"\r[{bar}] {percent:3d}%  {message}",
        end="",
        flush=True
    )

    if percent >= 100:
        print()

    log_info(message)


def get_library_status_text():
    if library_status.get("loading"):
        return "Loading"

    if library_status.get("paused"):
        return "Paused"

    if library_status["game_count"] > 0:
        return "Complete"

    return "Not Loaded"


def save_cache(cache_file, games):
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(games, f, indent=4)


def load_cache_from_file(cache_file):
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                loaded_cache = json.load(f)

            games_cache.clear()
            games_cache.update(loaded_cache)

            library_status["last_loaded"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            library_status["game_count"] = len(games_cache)
            library_status["message"] = "Loaded from cache"

            status(f"Loaded {len(games_cache)} games from cache")

        except Exception as e:
            status(f"Cache load failed: {e}")
            library_status["message"] = f"Cache load failed: {e}"


def cache_progress_update(cache_file, games, message, force=False):
    global _progress_counter

    with cache_lock:
        games_cache.clear()
        games_cache.update(games)

        library_status["game_count"] = len(games_cache)
        library_status["message"] = message

        if "Loading LaunchBox Library" in message and "/" in message and "games" in message:
            try:
                count_text = message.split("Loading LaunchBox Library...")[-1].split("games")[0].strip()
                processed_text, total_text = count_text.split("/")
                library_status["processed_count"] = int(processed_text.strip())
                library_status["total_count"] = int(total_text.strip())
            except Exception:
                pass

        _progress_counter += 1

        should_save = (
            force
            or _progress_counter >= CACHE_SAVE_EVERY
        )

        if should_save:
            _progress_counter = 0
            cache_snapshot = dict(games_cache)
        else:
            cache_snapshot = None

    # Only use the single-line progress bar for percent messages.
    # This prevents one terminal line per game.
    if (
        "Loading LaunchBox Library" in message
        and "(" in message
        and "%)" in message
    ):
        try:
            percent_text = (
                message.split("(")[-1]
                .replace("%)", "")
                .strip()
            )

            percent = int(percent_text)

            progress_bar(message, percent)

        except Exception:
            pass

    # Only print important non-progress messages.
    elif (
        message.startswith("Found ")
        or "complete" in message.lower()
        or "failed" in message.lower()
        or "error" in message.lower()
    ):
        status(message)

    if should_save and cache_snapshot is not None:
        save_cache(cache_file, cache_snapshot)


def get_games():
    return games_cache


def load_favorites():
    try:
        from cache_db import load_favorites as db_load_favorites
        return db_load_favorites()
    except Exception:
        return set()


def toggle_favorite(game_id):
    from cache_db import toggle_favorite as db_toggle_favorite
    db_toggle_favorite(game_id)
