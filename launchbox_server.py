from flask import Flask, render_template, send_file, redirect, request, jsonify
import subprocess
import psutil
import os
import threading
import json
from urllib.parse import unquote, quote, urlencode
from datetime import datetime

import user_settings

from app_config import (
    get_launchbox_folder,
    set_launchbox_folder,
    auto_launch_enabled,
    set_auto_launch,
    rom_downloads_enabled,
    logging_enabled,
    set_logging_enabled,
    get_allowed_ips,
    phone_play_enabled,
    get_macrodroid_trigger_url,
    set_macrodroid_trigger_url,
    get_android_rom_folder,
    set_android_rom_folder,
    get_android_retroarch_config,
    set_android_retroarch_config,
    get_android_retroarch_core_folder,
    set_android_retroarch_core_folder,
    get_retroarch_android_core,
    build_android_core_path,
)
from app_logging import log_error, log_info, get_log_file
from launchbox_library import load_launchbox_games
from server_helpers import (
    games_cache,
    library_status,
    library_control,
    cache_lock,
    status,
    get_library_status_text,
    save_cache,
    load_cache_from_file,
    cache_progress_update,
    get_games,
    load_favorites,
    toggle_favorite,
)
from cache_selector import get_game_cache_file, get_library_db_file, print_cache_mode
from cache_db import (
    init_db,
    upsert_games,
    load_all_games,
    search_games,
    get_distinct_values,
    get_random_game,
    record_recent_play,
    get_recent_plays,
    get_platform_summaries,
    clear_favorites,
    clear_recent_plays,
)


app = Flask(__name__, static_folder="static", template_folder="templates")

@app.context_processor
def inject_logging_state():
    enabled = logging_enabled()
    return {
        "logging_enabled": enabled,
        "logging_state": "Enabled" if enabled else "Disabled",
        "logging_toggle_label": "Disable Debug Logging" if enabled else "Enable Debug Logging",
    }

APP_FOLDER = os.path.dirname(os.path.abspath(__file__))

PORT = getattr(user_settings, "PORT", 5000)
CACHE_FILE = get_game_cache_file()
DB_FILE = get_library_db_file()
print_cache_mode()

PLATFORM_ICON_FOLDER = r"D:\LaunchBox\Images\Media Packs\Platform Clear Logos\Nostalgic Platform Clear Logos\Platforms"
REFRESH_PROGRESS_FILE = os.path.join(APP_FOLDER, "library_refresh_progress.json")


def debug_status(message, terminal=False):
    """Save detailed RetroTap debugging messages to the log file only.

    This keeps the terminal readable. Use terminal=True only for rare
    critical messages that should also appear in the console.
    """
    text = f"[DEBUG] {message}"

    try:
        log_info(text)
    except Exception:
        pass

    if terminal:
        try:
            status(text)
        except Exception:
            try:
                print(text)
            except Exception:
                pass


def describe_game_for_log(game_id, game):
    if not game:
        return f"game_id={game_id} game=None"

    return (
        f"game_id={game_id} | "
        f"title={game.get('title')} | "
        f"system={game.get('system')} | "
        f"platform={game.get('platform')} | "
        f"emulator={game.get('emulator')} | "
        f"emulator_app={game.get('emulator_app')} | "
        f"rom={game.get('rom')} | "
        f"core={game.get('retroarch_core')} | "
        f"box_front={game.get('box_front')} | "
        f"clear_logo={game.get('clear_logo')} | "
        f"background={game.get('background')} | "
        f"music={game.get('music')}"
    )


def resolve_game_for_route(game_id):
    """Get a game for route handling and log where it was found."""
    games = get_games()

    if game_id in games:
        game = dict(games[game_id])
        debug_status("Game found in memory cache: " + describe_game_for_log(game_id, game))
        return game

    debug_status(
        f"Game not found in memory cache: {game_id}. "
        f"Current memory cache size={len(games)}. Trying SQLite search fallback."
    )

    try:
        # Exact title/id fallback is intentionally broad because old cached links can survive
        # while a refresh is paused or after cache files have been cleared.
        matches = search_games(query=game_id, limit=25)
        for found_id, found_game in matches:
            if found_id == game_id:
                game = dict(found_game)
                debug_status("Game found in SQLite search fallback: " + describe_game_for_log(game_id, game))
                return game

        debug_status(
            f"SQLite fallback did not find exact game_id={game_id}. "
            f"Closest matches={[m[0] for m in matches[:5]]}"
        )
    except Exception as e:
        debug_status(f"SQLite fallback failed for game_id={game_id}: {type(e).__name__}: {e}")

    return None



@app.before_request
def log_request_start():
    try:
        debug_status(f"HTTP {request.method} {request.path} args={dict(request.args)} remote={request.remote_addr}")
    except Exception:
        pass


@app.template_filter("rating_2dp")
def rating_2dp(value):
    try:
        if value is None or value == "":
            return ""

        return f"{float(value):.2f}"

    except Exception:
        return str(value)


@app.before_request
def restrict_ips():
    allowed_ips = get_allowed_ips()

    if not allowed_ips:
        return

    remote = request.remote_addr

    if remote not in allowed_ips:
        return render_template(
            "error.html",
            title="Access blocked",
            message="This device is not allowed to access the launcher.",
            detail=remote
        ), 403


def _read_refresh_progress():
    if not os.path.exists(REFRESH_PROGRESS_FILE):
        return {}

    try:
        with open(REFRESH_PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _write_refresh_progress(info):
    try:
        with open(REFRESH_PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(info, f, indent=4)
    except Exception as e:
        status(f"Could not save refresh progress: {e}")


def _clear_refresh_progress():
    try:
        if os.path.exists(REFRESH_PROGRESS_FILE):
            os.remove(REFRESH_PROGRESS_FILE)
    except Exception as e:
        status(f"Could not clear refresh progress: {e}")




def clear_library_cache_files():
    """Clear all RetroTap library cache files and reset in-memory scan status."""
    deleted = []
    candidates = [
        CACHE_FILE,
        get_library_db_file(),
        os.path.join(APP_FOLDER, "game_cache.json"),
        os.path.join(APP_FOLDER, "game_cache_debug.json"),
        os.path.join(APP_FOLDER, "library_cache.db"),
        os.path.join(APP_FOLDER, "library_cache_debug.db"),
        REFRESH_PROGRESS_FILE,
    ]

    for filename in dict.fromkeys(candidates):
        try:
            if filename and os.path.exists(filename):
                os.remove(filename)
                deleted.append(os.path.basename(filename))
        except Exception as e:
            status(f"Could not delete cache file {filename}: {e}")

    with cache_lock:
        games_cache.clear()
        library_control["pause_requested"] = False
        library_status["loading"] = False
        library_status["paused"] = False
        library_status["game_count"] = 0
        library_status["processed_count"] = 0
        library_status["total_count"] = 0
        library_status["last_loaded"] = "Never"
        library_status["message"] = "Cache cleared. Refresh the library to rebuild it."

    try:
        init_db()
    except Exception as e:
        status(f"Cache cleared, but SQLite could not be reinitialized: {e}")

    if deleted:
        status("Cleared cache files: " + ", ".join(deleted))
    else:
        status("No cache files were found to clear.")

    return deleted


def refresh_button_html(button_class="btn-secondary"):
    if library_status.get("loading"):
        return f'<a class="{button_class}" href="/pause-library-refresh">Pause Refresh</a>'
    if library_status.get("paused"):
        return f'<a class="btn-primary" href="/restart-library-refresh">Resume Refresh</a>'
    return f'<a class="{button_class}" href="/refresh-library">Refresh Library</a>'


def cache_control_html(next_url=None, include_status=True):
    next_qs = ""
    if next_url:
        next_qs = "?next=" + quote(next_url, safe="/")

    clear_link = (
        f'<a class="btn-secondary" href="/clear-library-cache{next_qs}" '
        'onclick="return confirm(\'Clear all RetroTap library cache files? You can rebuild them by refreshing the library.\');">Clear Cache</a>'
    )
    start_fresh = '<a class="btn-secondary" href="/refresh-library">Start Fresh Scan</a>'
    status_link = '<a class="btn-secondary" href="/status">Status</a>' if include_status else ''
    pieces = [refresh_button_html(), start_fresh, clear_link]
    if status_link:
        pieces.append(status_link)
    return " ".join(pieces)


def retro_nav_html():
    logging_label = "Disable Debug Logging" if logging_enabled() else "Enable Debug Logging"
    logging_state = "ON" if logging_enabled() else "OFF"

    return f"""
        <div class="retro-banner">
            <div class="retro-banner-left">
                <button class="menu-toggle" type="button" onclick="toggleRetroMenu()">☰ Menu</button>
                <a href="/" aria-label="RetroTap Home"><img class="retro-banner-logo" src="/static/retrotap_logo.png" alt="RetroTap"></a>
                <div class="retro-banner-title">RetroTap</div>
            </div>
            <div class="retro-banner-actions">
                <a class="btn-secondary" href="/toggle-logging?next=/status">{logging_label}</a>
                <a class="btn-secondary" href="/debug-log">View Log</a>
                <a class="btn-secondary" href="/status">Status</a>
            </div>
        </div>
        <nav id="retroSidebar" class="retro-sidebar" aria-label="RetroTap menu">
            <a href="/">Platforms</a>
            <a href="/favorites">Favorites</a>
            <a href="/recent">Recent</a>
            <a href="/genres">Genres</a>
            <a href="/random">Random Game</a>
            <a href="/settings">Settings</a>
            <a href="/status">Server Status</a>
            <a href="/toggle-logging?next=/status">{logging_label} ({logging_state})</a>
            <a href="/debug-log">View Debug Log</a>
            <a href="/refresh-library">Refresh Library</a>
            <a href="/pause-library-refresh">Pause Refresh</a>
            <a href="/restart-library-refresh">Resume Refresh</a>
            <a class="danger-link" href="/clear-library-cache?next=/status" onclick="return confirm('Clear all RetroTap library cache files? You can rebuild them by refreshing the library.');">Clear Cache</a>
        </nav>
        <div id="retroMenuBackdrop" class="retro-menu-backdrop" onclick="toggleRetroMenu(false)"></div>
        <script>
            function toggleRetroMenu(forceOpen) {{
                const menu = document.getElementById('retroSidebar');
                const backdrop = document.getElementById('retroMenuBackdrop');
                if (!menu || !backdrop) return;
                const open = typeof forceOpen === 'boolean' ? forceOpen : !menu.classList.contains('open');
                menu.classList.toggle('open', open);
                backdrop.classList.toggle('open', open);
            }}
        </script>
    """


def refresh_library(resume=False):
    progress_info = _read_refresh_progress() if resume else {}
    resume_after = int(progress_info.get("processed_count", 0) or 0)

    with cache_lock:
        if library_status["loading"]:
            status("Library refresh already running. Skipping duplicate refresh.")
            return

        library_control["pause_requested"] = False
        library_status["loading"] = True
        library_status["paused"] = False
        library_status["message"] = (
            f"Resuming LaunchBox library scan after {resume_after} games..."
            if resume_after
            else "Scanning LaunchBox library..."
        )

        starting_games = dict(games_cache) if resume_after else {}

    try:
        status(library_status["message"])

        last_sqlite_update_percent = -10

        def should_stop():
            return bool(library_control.get("pause_requested"))

        def progress(games, message):
            nonlocal last_sqlite_update_percent

            force_save = "paused" in message.lower()
            debug_status(f"Refresh progress callback: {message} | games_cached={len(games)}")
            cache_progress_update(CACHE_FILE, games, message, force=force_save)

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
                    rounded_percent = (percent // 10) * 10

                    if rounded_percent >= last_sqlite_update_percent + 10:
                        upsert_games(games)
                        last_sqlite_update_percent = rounded_percent

                        status(
                            f"Saving cache at {rounded_percent}% "
                            f"({len(games)} games)"
                        )

                except Exception as e:
                    status(f"Live SQLite update skipped: {e}")

        games, scan_info = load_launchbox_games(
            progress_callback=progress,
            should_stop=should_stop,
            resume_after=resume_after,
            existing_games=starting_games,
            return_status=True,
        )

        with cache_lock:
            games_cache.clear()
            games_cache.update(games)

            library_status["loading"] = False
            library_status["last_loaded"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            library_status["game_count"] = len(games_cache)
            library_status["processed_count"] = scan_info.get("processed_count", 0)
            library_status["total_count"] = scan_info.get("total_count", 0)

            if scan_info.get("paused"):
                library_status["paused"] = True
                library_status["message"] = (
                    f"Library refresh paused at "
                    f"{library_status['processed_count']}/{library_status['total_count']} games. "
                    f"Partial cache saved."
                )
            else:
                library_status["paused"] = False
                library_status["message"] = "Library loaded successfully"

        save_cache(CACHE_FILE, games_cache)
        upsert_games(games_cache)

        if scan_info.get("paused"):
            _write_refresh_progress({
                "paused": True,
                "processed_count": scan_info.get("processed_count", 0),
                "total_count": scan_info.get("total_count", 0),
                "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
            status(library_status["message"])
        else:
            _clear_refresh_progress()
            status(f"Library refresh complete: {len(games_cache)} games")

    except Exception as e:
        with cache_lock:
            library_status["loading"] = False
            library_status["message"] = f"Library scan failed: {e}"

        status(f"Library scan failed: {e}")
        log_error(f"Library scan failed: {e}")


def refresh_library_background(resume=False):
    thread = threading.Thread(target=refresh_library, kwargs={"resume": resume})
    thread.daemon = True
    thread.start()


def load_cache_from_sqlite_or_json():
    init_db()

    db_games = load_all_games()

    if db_games:
        games_cache.clear()
        games_cache.update(db_games)

        library_status["last_loaded"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        library_status["game_count"] = len(games_cache)
        library_status["message"] = "Loaded from SQLite cache"

        status(f"Loaded {len(games_cache)} games from SQLite cache")
        return

    load_cache_from_file(CACHE_FILE)

    if games_cache:
        upsert_games(games_cache)

    progress_info = _read_refresh_progress()
    if progress_info.get("paused"):
        library_status["paused"] = True
        library_status["processed_count"] = int(progress_info.get("processed_count", 0) or 0)
        library_status["total_count"] = int(progress_info.get("total_count", 0) or 0)
        library_status["message"] = (
            f"Library refresh paused at "
            f"{library_status['processed_count']}/{library_status['total_count']} games. "
            f"Use Restart / Resume Refresh to continue."
        )


def normalize_name(name):
    return (
        name.lower()
        .replace(" ", "")
        .replace("-", "")
        .replace("_", "")
        .replace("&", "and")
        .replace(".", "")
        .replace(":", "")
        .replace("'", "")
    )


def find_platform_icon(platform_name):
    if not os.path.exists(PLATFORM_ICON_FOLDER):
        return ""

    possible_extensions = [".png", ".jpg", ".jpeg", ".webp"]
    target = normalize_name(platform_name)

    for file in os.listdir(PLATFORM_ICON_FOLDER):
        name, ext = os.path.splitext(file)

        if ext.lower() not in possible_extensions:
            continue

        if normalize_name(name) == target:
            full_path = os.path.join(PLATFORM_ICON_FOLDER, file)
            return "/platform-icon/" + quote(full_path.replace("\\", "/"))

    return ""


def get_selected_regions():
    regions = []

    for region in request.args.getlist("region"):
        region = region.strip()

        if region and region not in regions:
            regions.append(region)

    return regions


def build_region_query(selected_regions=None):
    if selected_regions is None:
        selected_regions = get_selected_regions()

    if not selected_regions:
        return ""

    return urlencode([("region", region) for region in selected_regions])



def get_platform_summaries_for_homepage(selected_regions=None):
    selected_regions = selected_regions or []

    platforms = {}

    for item in get_platform_summaries(selected_regions):
        platform = item.get("system", "Unknown")

        platforms[platform] = {
            "game_count": item.get("game_count", 0),
            "icon": find_platform_icon(platform),
            "phone_play_available": item.get("phone_play_available", False),
            "game_titles": item.get("game_titles", ""),
        }

    return platforms


def sorted_games_list(game_items):
    return sorted(game_items, key=lambda item: item[1].get("title", "").lower())


def get_platforms(selected_regions=None):
    selected_regions = selected_regions or []
    platforms = {}

    for game_id, game in search_games(region_filters=selected_regions, limit=100000):
        platform = game.get("system", "Unknown")

        if platform not in platforms:
            platforms[platform] = {
                "games": [],
                "icon": find_platform_icon(platform),
                "phone_play_available": False
            }

        if phone_play_available(game):
            platforms[platform]["phone_play_available"] = True

        platforms[platform]["games"].append((game_id, game))

    for platform in platforms:
        platforms[platform]["games"] = sorted_games_list(platforms[platform]["games"])

    return dict(sorted(platforms.items()))


def get_available_regions():
    return get_distinct_values("region")


def add_favorite_flags_to_games(game_items):
    favorites = load_favorites()
    output = []

    for game_id, game in game_items:
        game_copy = dict(game)
        game_copy["is_favorite"] = game_id in favorites
        output.append((game_id, game_copy))

    return output



def is_mobile_request():
    user_agent = request.headers.get("User-Agent", "").lower()

    mobile_keywords = ["android", "iphone", "ipad", "ipod", "mobile", "windows phone"]

    return any(keyword in user_agent for keyword in mobile_keywords)


def get_platform_info(platform_name):
    games = get_games()

    for game in games.values():
        if game.get("system") == platform_name:
            return {
                "name": platform_name,
                "notes": game.get("platform_notes", ""),
                "manufacturer": game.get("platform_manufacturer", ""),
                "developer": game.get("platform_developer", ""),
                "release_date": game.get("platform_release_date", ""),
                "icon": find_platform_icon(platform_name),
            }

    return {
        "name": platform_name,
        "notes": "",
        "manufacturer": "",
        "developer": "",
        "release_date": "",
        "icon": find_platform_icon(platform_name),
    }


def phone_play_available(game):
    if not phone_play_enabled():
        return False

    if bool(game.get("phone_play_available")):
        return True

    emulator_text = (
        str(game.get("emulator", ""))
        + " "
        + str(game.get("emulator_app", ""))
        + " "
        + str(game.get("launch_command", ""))
        + " "
        + str(game.get("cmd", ""))
    ).lower()

    return "retroarch" in emulator_text


def build_macro_url(game_id, game):
    base_url = get_macrodroid_trigger_url().strip()

    if not base_url:
        return ""

    if not base_url.startswith(("http://", "https://")):
        base_url = "http://" + base_url

    rom_name = os.path.basename(game.get("rom", ""))

    android_rom_path = (
        get_android_rom_folder().rstrip("/")
        + "/"
        + rom_name
    )

    android_core_name = get_retroarch_android_core(
        game.get("system", "")
    )

    android_core = build_android_core_path(
        game.get("system", "")
    )

    if not android_core:
        android_core = game.get("retroarch_core", "")

    if not android_core_name:
        android_core_name = os.path.basename(android_core)

    callback = request.host_url.rstrip("/") + f"/phone-confirm/{game_id}"

    params = {
        "core": android_core,
        "rom": android_rom_path,

        # MacroDroid sometimes handles simple names better than names with underscores.
        # Send both so either one can be used.
        "callback": callback,
        "callback_url": callback,
    }

    separator = "&" if "?" in base_url else "?"

    return base_url + separator + urlencode(params)




def launchbox_folder_is_valid(path):
    required_paths = [
        os.path.join(path, "Data"),
        os.path.join(path, "Data", "Platforms"),
        os.path.join(path, "Data", "Emulators.xml"),
    ]

    return all(os.path.exists(item) for item in required_paths)


def close_existing_emulator(emulator_app):
    if not emulator_app:
        status("No emulator app found. Skipping close check.")
        return

    emulator_process_name = os.path.basename(emulator_app).lower()
    found = False

    for proc in psutil.process_iter(["name"]):
        try:
            process_name = proc.info["name"]

            if process_name and process_name.lower() == emulator_process_name:
                found = True
                status(f"Closing existing emulator: {process_name}")
                proc.terminate()

        except Exception as e:
            status(f"Emulator close error: {e}")

    if not found:
        status(f"{os.path.basename(emulator_app)} was not already running. Continuing launch.")


def launch_game(game_id):
    debug_status(f"Play on PC requested for game_id={game_id}")
    game = resolve_game_for_route(game_id)

    if not game:
        status(f"Game not found: {game_id}")
        debug_status(f"Launch aborted because game lookup failed for game_id={game_id}")
        return False, "Game not found"

    launch_command = game.get("launch_command") or game.get("cmd")
    emulator_app = game.get("emulator_app")
    rom_path = game.get("rom")

    status("------------------------------------")
    status(f"Launching: {game.get('title')}")
    status(f"System: {game.get('system')}")
    status(f"Emulator: {game.get('emulator')}")
    status(f"Emulator EXE: {emulator_app}")
    status(f"ROM: {rom_path}")
    status(f"Command: {launch_command}")

    if not launch_command:
        return False, "No launch command found for this game/platform"

    # Keep the emulator check because it gives a useful error if RetroArch/Dolphin/etc. moved.
    if emulator_app and not os.path.exists(emulator_app):
        msg = f"Emulator EXE not found: {emulator_app}"
        status(msg)
        return False, msg

    # Do NOT block launch only because the ROM path check fails.
    # Some libraries use mapped/network drives or emulator-managed paths that Python cannot verify reliably.
    if rom_path and not os.path.exists(rom_path):
        status(f"WARNING: ROM path was not verified by Python, but launch will still be attempted: {rom_path}")

    close_existing_emulator(emulator_app)

    try:
        cwd = os.path.dirname(emulator_app) if emulator_app else None
        creationflags = subprocess.CREATE_NEW_CONSOLE if hasattr(subprocess, "CREATE_NEW_CONSOLE") else 0

        # launch_command is already a full command string from LaunchBox, often with quotes.
        # shell=True is required on Windows for these quoted command strings to launch correctly.
        debug_status(f"Popen starting | cwd={cwd} | shell=True | creationflags={creationflags}")
        subprocess.Popen(
            launch_command,
            cwd=cwd,
            shell=True,
            creationflags=creationflags
        )

        record_recent_play(game_id, game.get("title", ""), game.get("system", ""))

        status("Launch command sent")
        return True, "Launch command sent"

    except Exception as e:
        import traceback
        detail = f"{type(e).__name__}: {e}\nCommand: {launch_command}\nCWD: {os.path.dirname(emulator_app) if emulator_app else ''}\n{traceback.format_exc()}"
        debug_status(f"Launch error: {detail}")
        log_error(f"Launch error: {detail}")
        return False, detail


def render_launched_page_safe(game, game_id, closed, selected_regions, region_query):
    try:
        return render_template(
            "launched.html",
            game=game,
            game_id=game_id,
            closed=closed,
            is_mobile=is_mobile_request(),
            selected_regions=selected_regions,
            region_query=region_query,
            rom_downloads_enabled=rom_downloads_enabled(),
            phone_available=phone_play_available(game),
            macrodroid_url=build_macro_url(game_id, game)
        )

    except Exception as e:
        log_error(f"Launched page render failed for {game_id}: {e}")

        title = game.get("title", "Game")

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{title} Launched</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link rel="stylesheet" href="/static/style.css">
        </head>
        <body class="center-page">
            <div class="simple-card">
                <h1>{title}</h1>
                <p>The game launch command was sent successfully.</p>
                <p>The full launched page had a template error, but the game should still be running.</p>
                <p>
                    <a class="btn-primary" href="/">Back to Library</a>
                    <a class="btn-secondary" href="/game/{game_id}?manual=1">Play Options</a>
                </p>
            </div>
        </body>
        </html>
        """



@app.route("/favicon.ico")
def favicon():
    icon_path = os.path.join(APP_FOLDER, "static", "retrotap_favicon.png")
    if os.path.exists(icon_path):
        return send_file(icon_path, mimetype="image/png")
    return "", 204


@app.route("/manifest.json")
def manifest_json():
    return jsonify({
        "name": "RetroTap",
        "short_name": "RetroTap",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#03040a",
        "theme_color": "#111827",
        "icons": [
            {"src": "/static/retrotap_icon_192.png", "sizes": "192x192", "type": "image/png"}
        ]
    })


@app.route("/service-worker.js")
def service_worker():
    js = """
const CACHE_NAME = 'retrotap-shell-v1';
const SHELL = ['/', '/static/style.css', '/static/retrotap_logo.png', '/static/retrotap_icon_192.png'];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(SHELL)).catch(() => null));
  self.skipWaiting();
});
self.addEventListener('activate', event => {
  event.waitUntil(self.clients.claim());
});
self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;
  event.respondWith(
    fetch(req).then(resp => {
      const copy = resp.clone();
      if (req.url.includes('/static/')) {
        caches.open(CACHE_NAME).then(cache => cache.put(req, copy)).catch(() => null);
      }
      return resp;
    }).catch(() => caches.match(req))
  );
});
"""
    return app.response_class(js, mimetype="application/javascript")


@app.route("/setup-help")
def setup_help():
    return render_template(
        "setup_help.html"
    )


@app.route("/")
def index():
    games = get_games()

    if library_status["loading"] and len(games) == 0:
        return redirect("/loading")

    selected_regions = get_selected_regions()
    region_query = build_region_query(selected_regions)

    platforms = get_platform_summaries_for_homepage(selected_regions)
    favorites = load_favorites()
    recent_games = get_recent_plays(limit=12)

    return render_template(
        "platforms.html",
        platforms=platforms,
        library_status=library_status,
        favorite_count=len(favorites),
        available_regions=get_available_regions(),
        selected_regions=selected_regions,
        region_query=region_query,
        recent_games=recent_games,
        auto_launch=auto_launch_enabled()
    )


@app.route("/platform/<path:platform_name>")
def platform_page(platform_name):
    debug_status(f"Platform selected: {platform_name}")
    selected_regions = get_selected_regions()
    region_query = build_region_query(selected_regions)
    debug_status(f"Platform region filters: {selected_regions} | query={region_query}")

    all_games = search_games(platform=platform_name, limit=100000)
    debug_status(f"Platform total games before region filter: {platform_name} = {len(all_games)}")

    if not all_games:
        return render_template(
            "error.html",
            title="Platform not found",
            message="No games were found for this platform.",
            detail=platform_name
        ), 404

    filtered_games = search_games(
        platform=platform_name,
        region_filters=selected_regions,
        limit=100000
    )
    debug_status(f"Platform games after region filter: {platform_name} = {len(filtered_games)}")

    if filtered_games:
        sample = [f"{gid}:{g.get('title')}" for gid, g in filtered_games[:5]]
        debug_status(f"Platform sample games: {sample}")

    filtered_games = add_favorite_flags_to_games(filtered_games)

    return render_template(
        "platform_games.html",
        platform_name=platform_name,
        games=filtered_games,
        all_game_count=len(all_games),
        available_regions=get_available_regions(),
        selected_regions=selected_regions,
        region_query=region_query,
        library_status=library_status,
        is_mobile=is_mobile_request(),
        platform_info=get_platform_info(platform_name)
    )


@app.route("/game/<game_id>")
def game_choice(game_id):
    debug_status(f"Game page requested: game_id={game_id} | manual={request.args.get('manual')}")
    game = resolve_game_for_route(game_id)

    if not game:
        debug_status(f"Game page failed: game_id={game_id} was not found")
        return render_template(
            "error.html",
            title="Game not found",
            message="Try refreshing the library.",
            detail=game_id
        ), 404

    if auto_launch_enabled() and request.args.get("manual") != "1":
        debug_status(f"Auto-launch enabled. Redirecting game page to /play/{game_id}")
        return redirect(f"/play/{game_id}")

    selected_regions = get_selected_regions()
    region_query = build_region_query(selected_regions)

    game = dict(game)
    game["is_favorite"] = game_id in load_favorites()

    return render_template(
        "play_choice.html",
        game=game,
        game_id=game_id,
        selected_regions=selected_regions,
        region_query=region_query,
        rom_downloads_enabled=rom_downloads_enabled(),
        phone_available=phone_play_available(game),
        macrodroid_url=build_macro_url(game_id, game),
        is_mobile=is_mobile_request()
    )


@app.route("/play/<game_id>")
@app.route("/launch/<game_id>")
def play(game_id):
    debug_status(f"/play route entered for game_id={game_id}")
    game = resolve_game_for_route(game_id)

    if not game:
        debug_status(f"/play failed before launch because game was not found: {game_id}")
        return render_template("error.html", title="Game not found", message="Try refreshing the library.", detail=game_id), 404

    selected_regions = get_selected_regions()
    region_query = build_region_query(selected_regions)

    success, message = launch_game(game_id)

    game = dict(game)
    game["is_favorite"] = game_id in load_favorites()

    if not success:
        return render_template("error.html", title="Launch failed", message=message, detail=game.get("title", "")), 500

    return render_launched_page_safe(
        game=game,
        game_id=game_id,
        closed=False,
        selected_regions=selected_regions,
        region_query=region_query
    )


@app.route("/download-rom/<game_id>")
def download_rom(game_id):
    if not rom_downloads_enabled():
        return render_template("error.html", title="Downloads disabled", message="ROM downloads are disabled in config.json.", detail="rom_downloads_enabled = false"), 403

    debug_status(f"Download ROM requested for game_id={game_id}")
    game = resolve_game_for_route(game_id)

    if not game:
        return render_template("error.html", title="Game not found", message="Cannot download ROM because the game was not found.", detail=game_id), 404
    rom_path = game.get("rom")

    if not rom_path or not os.path.exists(rom_path):
        return render_template("error.html", title="ROM not found", message="The ROM path in LaunchBox does not exist.", detail=rom_path), 404

    status(f"Downloading ROM: {game.get('title')} - {rom_path}")

    return send_file(
        rom_path,
        as_attachment=True,
        download_name=os.path.basename(rom_path)
    )


@app.route("/close-game/<game_id>")
def close_game(game_id):
    games = get_games()

    if game_id not in games:
        return "Game not found.", 404

    selected_regions = get_selected_regions()
    region_query = build_region_query(selected_regions)

    game = dict(games[game_id])
    game["is_favorite"] = game_id in load_favorites()
    emulator_app = game.get("emulator_app")

    close_existing_emulator(emulator_app)

    return render_launched_page_safe(
        game=game,
        game_id=game_id,
        closed=True,
        selected_regions=selected_regions,
        region_query=region_query
    )


@app.route("/favorites")
def favorites_page():
    selected_regions = get_selected_regions()
    region_query = build_region_query(selected_regions)

    favorite_games = search_games(
        region_filters=selected_regions,
        favorites_only=True,
        limit=100000
    )

    favorite_games = add_favorite_flags_to_games(favorite_games)

    return render_template(
        "favorites.html",
        games=favorite_games,
        available_regions=get_available_regions(),
        selected_regions=selected_regions,
        region_query=region_query,
        library_status=library_status,
        is_mobile=is_mobile_request()
    )


@app.route("/clear-favorites")
def clear_favorites_route():
    clear_favorites()

    status("All favorites cleared")

    return redirect("/favorites")


@app.route("/clear-recent")
def clear_recent_route():
    clear_recent_plays()

    status("Recently played list cleared")

    return redirect("/recent")


@app.route("/recent")
def recent_page():
    recent_games = get_recent_plays(limit=100)

    return render_template(
        "game_list.html",
        title="Recently Played",
        subtitle=f"{len(recent_games)} recent launches",
        games=add_favorite_flags_to_games(recent_games),
        selected_regions=get_selected_regions(),
        region_query=build_region_query(),
        is_mobile=is_mobile_request()
    )


@app.route("/genres")
def genres_page():
    genres = get_distinct_values("genre")

    return render_template(
        "genres.html",
        genres=genres
    )


@app.route("/genre/<path:genre_name>")
def genre_page(genre_name):
    games = search_games(
        genre=genre_name,
        region_filters=get_selected_regions(),
        limit=100000
    )

    return render_template(
        "game_list.html",
        title=genre_name,
        subtitle=f"{len(games)} games",
        games=add_favorite_flags_to_games(games),
        selected_regions=get_selected_regions(),
        region_query=build_region_query(),
        is_mobile=is_mobile_request()
    )


@app.route("/random")
def random_game_route():
    platform = request.args.get("platform", "")
    genre = request.args.get("genre", "")
    favorites_only = request.args.get("favorites") == "1"

    game_id, game = get_random_game(
        platform=platform,
        region_filters=get_selected_regions(),
        genre=genre,
        favorites_only=favorites_only
    )

    if not game_id:
        return render_template("error.html", title="No random game found", message="Try changing your filters.", detail=""), 404

    return redirect(f"/game/{game_id}")


@app.route("/favorite/<game_id>", endpoint="toggle_favorite")
@app.route("/toggle-favorite/<game_id>")
def toggle_favorite_route(game_id):
    games = get_games()

    if game_id not in games:
        return "Game not found.", 404

    toggle_favorite(game_id)

    return_url = request.args.get("return", "")

    if return_url:
        return redirect(return_url)

    return redirect(f"/game/{game_id}")


@app.route("/settings", methods=["GET", "POST"])
def settings_page():
    message = ""

    if request.method == "POST":
        new_folder = request.form.get("launchbox_folder", "").strip()
        auto_launch = request.form.get("auto_launch") == "on"
        macrodroid_url = request.form.get("macrodroid_trigger_url", "").strip()
        android_rom_folder = request.form.get("android_rom_folder", "").strip()
        android_config = request.form.get("android_retroarch_config", "").strip()
        android_core_folder = request.form.get("android_retroarch_core_folder", "").strip()
        enable_logging = request.form.get("logging_enabled") == "on"

        if new_folder:
            set_launchbox_folder(new_folder)
            message = "Settings updated. Refresh the library if the LaunchBox folder changed."
            status(f"LaunchBox folder changed to: {new_folder}")

        set_auto_launch(auto_launch)
        set_logging_enabled(enable_logging)
        debug_status(f"Debug file logging {'enabled' if enable_logging else 'disabled'} from settings page")

        set_macrodroid_trigger_url(macrodroid_url)

        if android_rom_folder:
            set_android_rom_folder(android_rom_folder)

        if android_config:
            set_android_retroarch_config(android_config)

        if android_core_folder:
            set_android_retroarch_core_folder(android_core_folder)

    current_folder = get_launchbox_folder()
    folder_valid = launchbox_folder_is_valid(current_folder)

    return render_template(
        "settings.html",
        launchbox_folder=current_folder,
        folder_valid=folder_valid,
        message=message,
        auto_launch=auto_launch_enabled(),
        rom_downloads_enabled=rom_downloads_enabled(),
        logging_enabled=logging_enabled(),
        log_file=get_log_file(),
        phone_play_enabled=phone_play_enabled(),
        macrodroid_trigger_url=get_macrodroid_trigger_url(),
        android_rom_folder=get_android_rom_folder(),
        android_retroarch_config=get_android_retroarch_config(),
        android_retroarch_core_folder=get_android_retroarch_core_folder(),
        library_status=library_status,
        cache_controls=cache_control_html()
    )


@app.route("/api/games")
def api_games():
    query = request.args.get("q", "")
    platform = request.args.get("platform", "")
    genre = request.args.get("genre", "")

    games = search_games(
        query=query,
        platform=platform,
        genre=genre,
        region_filters=get_selected_regions(),
        limit=int(request.args.get("limit", 100))
    )

    results = []
    root = request.host_url.rstrip("/")

    for game_id, game in games:
        icon = find_platform_icon(game.get("system", ""))
        phone_ok = phone_play_available(game)
        results.append({
            "game_id": game_id,
            **game,
            "platform_icon_url": root + icon if icon else "",
            "phone_play_available": phone_ok,
            "phone_launch_available": phone_ok,
            "rom_download_available": rom_downloads_enabled(),
            "rom_download_url": root + f"/download-rom/{quote(game_id)}" if rom_downloads_enabled() else "",
            "game_page_url": root + f"/game/{quote(game_id)}?manual=1",
            "pc_launch_url": root + f"/play/{quote(game_id)}",
        })

    return jsonify(results)


@app.route("/api/platforms")
def api_platforms():
    platforms = []

    for platform in get_distinct_values("system"):
        icon = find_platform_icon(platform)
        platforms.append({
            "name": platform,
            "platform": platform,
            "icon_url": request.host_url.rstrip("/") + icon if icon else "",
        })

    return jsonify(platforms)


@app.route("/api/genres")
def api_genres():
    return jsonify(get_distinct_values("genre"))


@app.route("/phone/<game_id>")
def phone_game_page(game_id):
    games = get_games()

    if game_id not in games:
        return render_template(
            "error.html",
            title="Game not found",
            message="Cannot use phone play because the game was not found.",
            detail=game_id
        ), 404

    game = dict(games[game_id])

    if not is_mobile_request():
        return render_template(
            "error.html",
            title="Phone play is mobile only",
            message="Phone play is only available when opened from a mobile browser.",
            detail=game.get("title", "")
        ), 403

    if not phone_play_available(game):
        return render_template(
            "error.html",
            title="Phone play unavailable",
            message="Phone play is only available for RetroArch games.",
            detail=game.get("title", "")
        ), 403

    macro_url = build_macro_url(game_id, game)

    return render_template(
        "phone_play.html",
        game=game,
        game_id=game_id,
        macrodroid_url=macro_url,
        android_rom_folder=get_android_rom_folder(),
        android_config=get_android_retroarch_config(),
        android_core=build_android_core_path(game.get("system", "")) or game.get("retroarch_core", ""),
        android_core_name=get_retroarch_android_core(game.get("system", "")) or os.path.basename(game.get("retroarch_core", "")),
        android_core_folder=get_android_retroarch_core_folder(),
        region_query=build_region_query(get_selected_regions()),
        rom_downloads_enabled=rom_downloads_enabled()
    )





@app.route("/phone-confirm/<game_id>")
def phone_confirm(game_id):
    games = get_games()

    if game_id not in games:
        return render_template(
            "error.html",
            title="Game not found",
            message="Phone launch confirmation was received, but the game was not found in the library.",
            detail=game_id
        ), 404

    game = dict(games[game_id])
    game["is_favorite"] = game_id in load_favorites()
    game["phone_launched"] = True

    selected_regions = get_selected_regions()
    region_query = build_region_query(selected_regions)

    record_recent_play(
        game_id,
        game.get("title", ""),
        game.get("system", "")
    )

    status(f"Phone launch confirmed by MacroDroid callback: {game.get('title')}")

    return render_launched_page_safe(
        game=game,
        game_id=game_id,
        closed=False,
        selected_regions=selected_regions,
        region_query=region_query
    )


@app.route("/api/phone-play/<game_id>")
def api_phone_play(game_id):
    games = get_games()

    if game_id not in games:
        return jsonify({"error": "Game not found"}), 404

    game = dict(games[game_id])

    if not phone_play_available(game):
        return jsonify({"error": "Phone play unavailable"}), 403

    rom_name = os.path.basename(game.get("rom", ""))

    callback = request.host_url.rstrip("/") + f"/phone-confirm/{game_id}"

    return jsonify({
        "core": build_android_core_path(game.get("system", "")) or game.get("retroarch_core", ""),
        "rom": get_android_rom_folder().rstrip("/") + "/" + rom_name,
        "callback": callback,
        "callback_url": callback,
        "macrodroid_url": build_macro_url(game_id, game),
        "phone_play_available": True,
        "rom_download_available": rom_downloads_enabled(),
        "rom_download_url": request.host_url.rstrip("/") + f"/download-rom/{quote(game_id)}" if rom_downloads_enabled() else ""
    })


@app.route("/loading")
def loading():
    refresh_controls = cache_control_html()

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Loading Library</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta http-equiv="refresh" content="3">
        <link rel="stylesheet" href="/static/style.css">
    </head>

    <body class="center-page has-retro-banner">
        {retro_nav_html()}
        <div class="simple-card">
            <div class="spinner"></div>
            <h1>Loading LaunchBox Library</h1>
            <p>{library_status["message"]}</p>
            <p>Games loaded: {library_status["game_count"]}</p>
            <p>Progress: {library_status.get("processed_count", 0)}/{library_status.get("total_count", 0)}</p>
            <p>This page refreshes automatically.</p>
            <p>
                <a class="btn-primary" href="/">Open Current Library</a>
                <a class="btn-secondary" href="/status">Status</a>
                {refresh_controls}
            </p>
        </div>
    </body>
    </html>
    """


@app.route("/refresh-library")
def refresh_library_route():
    if not library_status["loading"]:
        _clear_refresh_progress()
        with cache_lock:
            library_status["paused"] = False
            library_status["processed_count"] = 0
            library_status["total_count"] = 0
        refresh_library_background(resume=False)
    else:
        status("Refresh requested, but library is already loading.")

    return redirect("/loading")


@app.route("/pause-library-refresh")
def pause_library_refresh_route():
    if library_status.get("loading"):
        library_control["pause_requested"] = True
        status("Pause requested. Saving partial library cache after the current game.")
    else:
        status("Pause requested, but no library refresh is running.")

    return redirect("/loading")


@app.route("/restart-library-refresh")
def restart_library_refresh_route():
    if library_status.get("loading"):
        status("Restart requested, but library refresh is already running.")
    else:
        refresh_library_background(resume=True)

    return redirect("/loading")


@app.route("/clear-library-cache")
def clear_library_cache_route():
    if library_status.get("loading"):
        status("Clear cache requested, but a library refresh is currently running. Pause or wait for it to finish first.")
        return redirect("/loading")

    clear_library_cache_files()
    next_url = request.args.get("next") or request.referrer or "/settings"
    return redirect(next_url)


@app.route("/toggle-logging")
def toggle_logging_route():
    new_value = not logging_enabled()
    set_logging_enabled(new_value)
    message = f"Debug file logging {'enabled' if new_value else 'disabled'}"
    debug_status(message)

    next_url = request.args.get("next") or request.referrer or "/status"
    return redirect(next_url)


@app.route("/diagnostics")
def diagnostics():
    data = {
        "library_status": dict(library_status),
        "cache_file": CACHE_FILE,
        "db_file": DB_FILE,
        "log_file": get_log_file(),
        "logging_enabled": logging_enabled(),
        "launchbox_folder": get_launchbox_folder(),
        "macrodroid_trigger_url": get_macrodroid_trigger_url(),
        "phone_play_enabled": phone_play_enabled(),
        "rom_downloads_enabled": rom_downloads_enabled(),
    }
    return jsonify(data)


@app.route("/debug-log")
def debug_log_file_route():
    log_path = get_log_file()

    if not os.path.exists(log_path):
        return render_template(
            "error.html",
            title="Debug log not found",
            message="No debug log file exists yet. Turn on Debug Logging and reproduce the issue.",
            detail=log_path
        ), 404

    return send_file(log_path, as_attachment=False, download_name="retrotap_debug.log")


@app.route("/status")
def server_status():
    debug_status("Status page opened")
    library_status_text = get_library_status_text()
    refresh_controls = cache_control_html(next_url="/status", include_status=False)
    processed = int(library_status.get("processed_count", 0) or 0)
    total = int(library_status.get("total_count", 0) or 0)
    percent = int((processed / total) * 100) if total else 0
    logging_state = "Enabled" if logging_enabled() else "Disabled"
    logging_button = "Disable Debug Logging" if logging_enabled() else "Enable Debug Logging"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>RetroTap Server Status</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta http-equiv="refresh" content="10">
        <link rel="stylesheet" href="/static/style.css">
    </head>

    <body class="status-page has-retro-banner">
        {retro_nav_html()}
        <div class="simple-card clean-status-card">
            <h1>Game Server Status</h1>
            <p class="good">SERVER ONLINE</p>

            <div class="status-metrics">
                <div class="status-metric"><strong>Library Status</strong>{library_status_text}</div>
                <div class="status-metric"><strong>Games Loaded</strong>{library_status["game_count"]}</div>
                <div class="status-metric"><strong>Progress</strong>{processed}/{total} ({percent}%)</div>
                <div class="status-metric"><strong>Debug Logging</strong>{logging_state}</div>
            </div>

            <div class="progress-track"><div class="progress-fill" style="width:{percent}%;"></div></div>

            <p><b>Last Loaded:</b> {library_status["last_loaded"]}</p>
            <p><b>Status:</b> {library_status["message"]}</p>
            <p><b>Log File:</b> {get_log_file()}</p>

            <div class="button-row">
                <a class="btn-secondary" href="/">Open Platforms</a>
                <a class="btn-secondary" href="/settings">Settings</a>
                <a class="btn-secondary" href="/toggle-logging?next=/status">{logging_button}</a>
                <a class="btn-secondary" href="/debug-log">View Debug Log</a>
                {refresh_controls}
                <a class="btn-secondary" href="/recent">Recent</a>
                <a class="btn-secondary" href="/genres">Genres</a>
            </div>

            <p class="subtitle">This status page refreshes every 10 seconds.</p>
        </div>
    </body>
    </html>
    """


@app.route("/launchbox-image/<path:image_path>")
def launchbox_image(image_path):
    image_path = unquote(image_path)
    debug_status(f"Image requested: {image_path}")

    if not os.path.exists(image_path):
        debug_status(f"Image not found on disk: {image_path}")
        return "Image not found", 404

    debug_status(f"Sending image: {image_path}")
    return send_file(image_path)


@app.route("/launchbox-media/<path:media_path>")
def launchbox_media(media_path):
    media_path = unquote(media_path)
    debug_status(f"Media requested: {media_path}")

    if not os.path.exists(media_path):
        debug_status(f"Media not found on disk: {media_path}")
        return "Media not found", 404

    debug_status(f"Sending media: {media_path}")
    return send_file(media_path)



@app.route("/platform-icon/<path:image_path>")
def platform_icon(image_path):
    image_path = unquote(image_path)
    debug_status(f"Platform icon requested: {image_path}")

    if not os.path.exists(image_path):
        debug_status(f"Platform icon not found on disk: {image_path}")
        return "Platform icon not found", 404

    debug_status(f"Sending platform icon: {image_path}")
    return send_file(image_path)


@app.errorhandler(404)
def not_found(error):
    return render_template(
        "error.html",
        title="Page not found",
        message="The page or item could not be found.",
        detail=str(error)
    ), 404


@app.errorhandler(500)
def server_error(error):
    return render_template(
        "error.html",
        title="Server error",
        message="The server hit an error.",
        detail=str(error)
    ), 500


if __name__ == "__main__":
    status("Starting LaunchBox Game Server")

    init_db()
    load_cache_from_sqlite_or_json()

    if len(games_cache) == 0:
        status("No cache found. Starting first LaunchBox scan.")
        refresh_library_background()
    else:
        status("Using cached library. Refresh manually at /refresh-library")

        status("===================================")
        status("READY TO LOAD GAMES")
        status(f"Cached Games Available: {len(games_cache)}")
        status("Open: http://localhost:5000")
        status("Settings: http://localhost:5000/settings")
        status("===================================")

    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False
    )
