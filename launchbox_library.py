import os
import re
import xml.etree.ElementTree as ET
from urllib.parse import quote

from app_config import get_launchbox_folder
from app_logging import log_info


LAUNCHBOX_FOLDER = get_launchbox_folder()

PLATFORMS_FOLDER = ""
EMULATORS_XML = ""
IMAGES_FOLDER = ""
GAMES_FOLDER = ""
MUSIC_FOLDER = ""


def refresh_launchbox_paths():
    global LAUNCHBOX_FOLDER
    global PLATFORMS_FOLDER
    global EMULATORS_XML
    global IMAGES_FOLDER
    global GAMES_FOLDER
    global MUSIC_FOLDER

    LAUNCHBOX_FOLDER = get_launchbox_folder()

    PLATFORMS_FOLDER = os.path.join(
        LAUNCHBOX_FOLDER,
        "Data",
        "Platforms"
    )

    EMULATORS_XML = os.path.join(
        LAUNCHBOX_FOLDER,
        "Data",
        "Emulators.xml"
    )

    IMAGES_FOLDER = os.path.join(
        LAUNCHBOX_FOLDER,
        "Images"
    )

    GAMES_FOLDER = os.path.join(
        LAUNCHBOX_FOLDER,
        "Games"
    )

    MUSIC_FOLDER = os.path.join(
        LAUNCHBOX_FOLDER,
        "Music"
    )


refresh_launchbox_paths()

# --------------------------------------------------
# SAFE FILESYSTEM HELPERS
# --------------------------------------------------

def safe_exists(path):
    try:
        return bool(path) and os.path.exists(path)
    except Exception as e:
        print(f"[PATH SKIPPED] Invalid path: {path!r} ({e})")
        try:
            log_info(f"[PATH SKIPPED] Invalid path: {path!r} ({e})")
        except Exception:
            pass
        return False


def safe_listdir(path):
    try:
        if safe_exists(path):
            return os.listdir(path)
    except Exception as e:
        print(f"[FOLDER SKIPPED] Could not list folder: {path!r} ({e})")
        try:
            log_info(f"[FOLDER SKIPPED] Could not list folder: {path!r} ({e})")
        except Exception:
            pass
    return []


def safe_walk(path):
    try:
        if safe_exists(path):
            yield from os.walk(path)
    except Exception as e:
        print(f"[FOLDER SKIPPED] Could not walk folder: {path!r} ({e})")
        try:
            log_info(f"[FOLDER SKIPPED] Could not walk folder: {path!r} ({e})")
        except Exception:
            pass
    return


def scan_log(message):
    text = f"[SCAN] {message}"
    print(text)
    try:
        log_info(text)
    except Exception:
        pass


# --------------------------------------------------
# BASIC HELPERS
# --------------------------------------------------

def get_text(node, field_name):
    found = node.find(field_name)

    if found is not None and found.text:
        return found.text.strip()

    return ""


def clean_path(path):
    if not path:
        return ""

    path = path.strip().strip('"').strip("'")
    path = os.path.expandvars(path)
    path = path.replace("/", "\\")

    if path.startswith(".\\"):
        path = os.path.join(LAUNCHBOX_FOLDER, path[2:])

    elif path.startswith("..\\"):
        path = os.path.abspath(os.path.join(LAUNCHBOX_FOLDER, path))

    elif not os.path.isabs(path):
        path = os.path.join(LAUNCHBOX_FOLDER, path)

    return os.path.normpath(path)


def make_game_id(platform, title):
    text = f"{platform}_{title}".lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def image_url(path):
    if path and safe_exists(path):
        return "/launchbox-image/" + quote(path.replace("\\", "/"))

    return ""


def media_url(path):
    if path and safe_exists(path):
        return "/launchbox-media/" + quote(path.replace("\\", "/"))

    return ""


def count_games_in_platform(xml_path):
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        return len(root.findall("Game"))

    except Exception:
        return 0




# --------------------------------------------------
# PLATFORM METADATA
# --------------------------------------------------

def load_platform_metadata():
    platform_data = {}

    metadata_file = os.path.join(
        LAUNCHBOX_FOLDER,
        "Data",
        "Platforms.xml"
    )

    if not safe_exists(metadata_file):
        return platform_data

    try:
        tree = ET.parse(metadata_file)
        root = tree.getroot()

        for platform_node in root.findall("Platform"):
            name = (
                get_text(platform_node, "Name")
                or get_text(platform_node, "Title")
            )

            if not name:
                continue

            platform_data[name] = {
                "name": name,
                "title": get_text(platform_node, "Title") or name,
                "sort_title": get_text(platform_node, "SortTitle"),
                "notes": get_text(platform_node, "Notes"),
                "manufacturer": get_text(platform_node, "Manufacturer"),
                "developer": get_text(platform_node, "Developer"),
                "release_date": get_text(platform_node, "ReleaseDate"),
                "cpu": get_text(platform_node, "Cpu"),
                "memory": get_text(platform_node, "Memory"),
                "graphics": get_text(platform_node, "Graphics"),
                "sound": get_text(platform_node, "Sound"),
                "display": get_text(platform_node, "Display"),
                "max_controllers": get_text(platform_node, "MaxControllers"),
            }

    except Exception as e:
        print("Error reading platform metadata:")
        print(e)

    return platform_data


# --------------------------------------------------
# ROM PATH HELPERS
# --------------------------------------------------

def find_rom_by_filename(filename):
    if not filename:
        return ""

    for root, dirs, files in safe_walk(GAMES_FOLDER):
        for file in files:
            if file.lower() == filename.lower():
                return os.path.join(root, file)

    return ""


def clean_rom_path(path):
    path = clean_path(path)

    if safe_exists(path):
        return path

    filename = os.path.basename(path)
    fallback = find_rom_by_filename(filename)

    if fallback and safe_exists(fallback):
        print("ROM fallback found:", fallback)
        return fallback

    return path


# --------------------------------------------------
# MEDIA HELPERS
# --------------------------------------------------

def find_file_by_title(folder, title, allowed_extensions):
    if not safe_exists(folder):
        return ""

    safe_title = (
        title
        .replace(":", "_")
        .replace("/", "_")
        .replace("\\", "_")
    )

    for file in safe_listdir(folder):
        name, ext = os.path.splitext(file)

        if ext.lower() not in allowed_extensions:
            continue

        if name.lower().startswith(safe_title.lower()):
            return os.path.join(folder, file)

    return ""


def find_box_art(platform, title):
    image_extensions = [".jpg", ".png", ".jpeg", ".webp"]

    box_front_folder = os.path.join(
        IMAGES_FOLDER,
        platform,
        "Box - Front"
    )

    if not safe_exists(box_front_folder):
        return ""

    priority_folders = [
        os.path.join(box_front_folder, "United States"),
        os.path.join(box_front_folder, "North America"),
    ]

    checked_folders = set()

    for folder in priority_folders:
        if safe_exists(folder):
            checked_folders.add(os.path.normpath(folder).lower())

            found = find_file_by_title(
                folder,
                title,
                image_extensions
            )

            if found:
                return found

    for root, dirs, files in safe_walk(box_front_folder):
        normalized_root = os.path.normpath(root).lower()

        if normalized_root in checked_folders:
            continue

        found = find_file_by_title(
            root,
            title,
            image_extensions
        )

        if found:
            return found

    return ""


def find_screenshot(platform, title):
    image_extensions = [".jpg", ".png", ".jpeg", ".webp"]

    screenshot_folder = os.path.join(
        IMAGES_FOLDER,
        platform,
        "Screenshot - Gameplay"
    )

    if not safe_exists(screenshot_folder):
        return ""

    priority_folders = [
        os.path.join(screenshot_folder, "United States"),
        os.path.join(screenshot_folder, "North America"),
    ]

    checked_folders = set()

    for folder in priority_folders:
        if safe_exists(folder):
            checked_folders.add(os.path.normpath(folder).lower())

            found = find_file_by_title(
                folder,
                title,
                image_extensions
            )

            if found:
                return found

    for root, dirs, files in safe_walk(screenshot_folder):
        normalized_root = os.path.normpath(root).lower()

        if normalized_root in checked_folders:
            continue

        found = find_file_by_title(
            root,
            title,
            image_extensions
        )

        if found:
            return found

    return ""


def find_music(platform, title):
    music_extensions = [".mp3", ".wav", ".ogg", ".m4a", ".flac"]

    folders = [
        os.path.join(MUSIC_FOLDER, platform),
        MUSIC_FOLDER,
    ]

    for folder in folders:
        found = find_file_by_title(folder, title, music_extensions)

        if found:
            return found

    return ""


# --------------------------------------------------
# EMULATOR METADATA PARSING
# --------------------------------------------------

def load_launchbox_emulators():
    emulators_by_id = {}
    platform_mappings = {}

    if not safe_exists(EMULATORS_XML):
        print("Emulators.xml not found:", EMULATORS_XML)
        return emulators_by_id, platform_mappings

    try:
        tree = ET.parse(EMULATORS_XML)
        root = tree.getroot()

        for emulator in root.findall("Emulator"):
            emulator_id = get_text(emulator, "ID")

            if not emulator_id:
                continue

            emulators_by_id[emulator_id] = {
                "id": emulator_id,
                "title": get_text(emulator, "Title") or "Unknown Emulator",
                "application_path": clean_path(get_text(emulator, "ApplicationPath")),
                "command_line": get_text(emulator, "CommandLine"),
                "no_quotes": get_text(emulator, "NoQuotes").lower() == "true",
                "no_space": get_text(emulator, "NoSpace").lower() == "true",
                "auto_extract": get_text(emulator, "AutoExtract").lower() == "true",
            }

        for mapping in root.findall("EmulatorPlatform"):
            platform = get_text(mapping, "Platform")
            emulator_id = get_text(mapping, "Emulator")
            is_default = get_text(mapping, "Default").lower() == "true"

            if not platform or not emulator_id:
                continue

            item = {
                "platform": platform,
                "emulator_id": emulator_id,
                "command_line": get_text(mapping, "CommandLine"),
                "default": is_default,
                "auto_extract": get_text(mapping, "AutoExtract").lower() == "true",
                "m3u": get_text(mapping, "M3uDiscLoadEnabled").lower() == "true",
            }

            if platform not in platform_mappings:
                platform_mappings[platform] = []

            platform_mappings[platform].append(item)

    except Exception as e:
        print("Error reading Emulators.xml")
        print(e)

    return emulators_by_id, platform_mappings


def choose_platform_mapping(platform, game_emulator_id, platform_mappings):
    mappings = platform_mappings.get(platform, [])

    if not mappings:
        return {}

    if game_emulator_id:
        for mapping in mappings:
            if mapping.get("emulator_id") == game_emulator_id:
                return mapping

    for mapping in mappings:
        if mapping.get("default"):
            return mapping

    return mappings[0]


def build_launch_command(emulator_info, command_line, rom_path):
    if not emulator_info:
        return ""

    emulator_app = emulator_info.get("application_path", "")

    if not emulator_app:
        return ""

    no_quotes = emulator_info.get("no_quotes", False)
    no_space = emulator_info.get("no_space", False)

    if no_quotes:
        command = emulator_app
        rom_text = rom_path
    else:
        command = f'"{emulator_app}"'
        rom_text = f'"{rom_path}"'

    args = command_line or ""

    placeholders = [
        "{ImagePath}",
        "{RomPath}",
        "{ApplicationPath}",
        "{FilePath}",
        "{rom}",
        "{ROM}",
        "%rom%",
        "%ROM%",
    ]

    replaced = False

    for placeholder in placeholders:
        if placeholder in args:
            args = args.replace(placeholder, rom_text)
            replaced = True

    if args:
        if no_space:
            command += args
        else:
            command += " " + args

    if not replaced:
        if no_space:
            command += rom_text
        else:
            command += " " + rom_text

    return command




def is_retroarch_game(emulator_info):
    title = emulator_info.get("title", "").lower()
    app = emulator_info.get("application_path", "").lower()

    return "retroarch" in title or "retroarch" in app


def extract_retroarch_core_from_command(command_line):
    if not command_line:
        return ""

    parts = command_line.replace("\\", "/").split()

    for index, part in enumerate(parts):
        part_clean = part.strip('"')

        if part.lower() == "-l" and index + 1 < len(parts):
            return parts[index + 1].strip('"')

        if part_clean.lower().endswith("_libretro.dll"):
            return part_clean

        if part_clean.lower().endswith("_libretro.so"):
            return part_clean

    return ""


def extract_retroarch_config_from_command(command_line):
    if not command_line:
        return ""

    parts = command_line.replace("\\", "/").split()

    for index, part in enumerate(parts):
        part_clean = part.strip('"')

        if part.lower() in ["--config", "-c"] and index + 1 < len(parts):
            return parts[index + 1].strip('"')

        if part_clean.lower().endswith(".cfg"):
            return part_clean

    return ""


# --------------------------------------------------
# MAIN LIBRARY LOADER
# --------------------------------------------------

def load_launchbox_games(progress_callback=None, should_stop=None, resume_after=0, existing_games=None, return_status=False):
    refresh_launchbox_paths()

    games = dict(existing_games or {})
    paused = False

    emulators_by_id, platform_mappings = load_launchbox_emulators()
    platform_metadata = load_platform_metadata()

    if not safe_exists(PLATFORMS_FOLDER):
        scan_log(f"LaunchBox platform folder not found: {PLATFORMS_FOLDER}")
        return games

    platform_files = []

    for xml_file in safe_listdir(PLATFORMS_FOLDER):
        if xml_file.lower().endswith(".xml"):
            platform_files.append(
                os.path.join(PLATFORMS_FOLDER, xml_file)
            )

    platform_files = sorted(platform_files)

    total_games = 0
    platform_counts = {}

    for xml_path in platform_files:
        platform_name = os.path.splitext(
            os.path.basename(xml_path)
        )[0]

        count = count_games_in_platform(xml_path)

        platform_counts[platform_name] = count
        total_games += count

        if progress_callback:
            progress_callback(
                games,
                f"Found {count} games for {platform_name}"
            )

    processed_games = 0
    loaded_games = 0
    last_percent = -1

    if progress_callback:
        progress_callback(
            games,
            f"Loading LaunchBox Library... 0/{total_games} games (0%)"
        )

    for xml_path in platform_files:
        platform_from_file = os.path.splitext(
            os.path.basename(xml_path)
        )[0]

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            for game_node in root.findall("Game"):
                title = get_text(game_node, "Title")
                app_path = get_text(game_node, "ApplicationPath")

                if not title or not app_path:
                    continue

                processed_games += 1

                if processed_games <= resume_after:
                    if total_games > 0:
                        percent = int((processed_games / total_games) * 100)
                    else:
                        percent = 100

                    if percent != last_percent:
                        last_percent = percent
                        if progress_callback:
                            progress_callback(
                                games,
                                (
                                    f"Loading LaunchBox Library... "
                                    f"{processed_games}/{total_games} games "
                                    f"({percent}%)"
                                )
                            )
                    continue

                platform = get_text(game_node, "Platform") or platform_from_file
                rom_path = clean_rom_path(app_path)
                game_id = make_game_id(platform, title)

                game_emulator_id = get_text(game_node, "Emulator")

                mapping = choose_platform_mapping(
                    platform,
                    game_emulator_id,
                    platform_mappings
                )

                emulator_id = (
                    game_emulator_id
                    or mapping.get("emulator_id", "")
                )

                emulator_info = emulators_by_id.get(emulator_id, {})

                command_line = (
                    get_text(game_node, "CommandLine")
                    or mapping.get("command_line", "")
                    or emulator_info.get("command_line", "")
                )

                launch_command = build_launch_command(
                    emulator_info,
                    command_line,
                    rom_path
                )

                box_art_path = find_box_art(platform, title)
                screenshot_path = find_screenshot(platform, title)
                music_path = find_music(platform, title)

                phone_play_available = (
                    is_retroarch_game(emulator_info)
                    and safe_exists(rom_path)
                )

                retroarch_core = extract_retroarch_core_from_command(
                    command_line
                )

                retroarch_config = extract_retroarch_config_from_command(
                    command_line
                )

                games[game_id] = {
                    "title": title,
                    "system": platform,
                    "rom": rom_path,

                    "image": image_url(box_art_path) or image_url(screenshot_path),
                    "box_art": image_url(box_art_path),
                    "screenshot": image_url(screenshot_path),
"music": media_url(music_path),

                    "genre": get_text(game_node, "Genre"),
                    "developer": get_text(game_node, "Developer"),
                    "publisher": get_text(game_node, "Publisher"),
                    "release_date": get_text(game_node, "ReleaseDate"),
                    "notes": get_text(game_node, "Notes"),
                    "favorite": get_text(game_node, "Favorite"),
                    "star_rating": get_text(game_node, "CommunityStarRating"),
                    "play_count": get_text(game_node, "PlayCount"),
                    "play_time": get_text(game_node, "PlayTime"),
                    "last_played": get_text(game_node, "LastPlayedDate"),
                    "region": get_text(game_node, "Region"),
                    "version": get_text(game_node, "Version"),
                    "play_mode": get_text(game_node, "PlayMode"),
                    "max_players": get_text(game_node, "MaxPlayers"),
                    "series": get_text(game_node, "Series"),
                    "source": get_text(game_node, "Source"),
                    "status": get_text(game_node, "Status"),
                    "completed": get_text(game_node, "Completed"),
                    "broken": get_text(game_node, "Broken"),
                    "portable": get_text(game_node, "Portable"),
                    "hide": get_text(game_node, "Hide"),
                    "database_id": get_text(game_node, "DatabaseID"),
                    "community_star_rating": get_text(game_node, "CommunityStarRating"),
                    "platform_notes": platform_metadata.get(platform, {}).get("notes", ""),
                    "platform_manufacturer": platform_metadata.get(platform, {}).get("manufacturer", ""),
                    "platform_developer": platform_metadata.get(platform, {}).get("developer", ""),
                    "platform_release_date": platform_metadata.get(platform, {}).get("release_date", ""),

                    "emulator": emulator_info.get("title", ""),
                    "emulator_id": emulator_id,
                    "emulator_app": emulator_info.get("application_path", ""),
                    "command_line": command_line,
                    "launch_command": launch_command,
                    "cmd": launch_command,

                    "phone_play_available": phone_play_available,
                    "retroarch_core": retroarch_core,
                    "retroarch_config": retroarch_config,
                }

                loaded_games += 1

                if total_games > 0:
                    percent = int(
                        (processed_games / total_games) * 100
                    )
                else:
                    percent = 100

                if percent != last_percent:
                    last_percent = percent

                    if progress_callback:
                        progress_callback(
                            games,
                            (
                                f"Loading LaunchBox Library... "
                                f"{processed_games}/{total_games} games "
                                f"({percent}%)"
                            )
                        )

                if should_stop and should_stop():
                    paused = True
                    if progress_callback:
                        progress_callback(
                            games,
                            (
                                f"Library refresh paused at "
                                f"{processed_games}/{total_games} games "
                                f"({len(games)} cached)"
                            )
                        )
                    break

            if paused:
                break

        except Exception as e:
            print("Error reading:", xml_path)
            print(e)

    games = dict(
        sorted(
            games.items(),
            key=lambda item: item[1]["title"].lower()
        )
    )

    if progress_callback and not paused:
        progress_callback(
            games,
            f"Loading LaunchBox Library complete: {len(games)} games (100%)"
        )

    if return_status:
        return games, {
            "paused": paused,
            "processed_count": processed_games,
            "total_count": total_games,
            "loaded_count": loaded_games,
        }

    return games
