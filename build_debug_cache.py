import json
import sqlite3
from collections import defaultdict
from pathlib import Path

# -----------------------------
# SETTINGS
# -----------------------------

SOURCE_GAME_CACHE = "game_cache.json"
DEBUG_GAME_CACHE = "game_cache_debug.json"
DEBUG_LIBRARY_DB = "library_cache_debug.db"
MAX_GAMES_PER_PLATFORM = 5

# -----------------------------
# BUILD DEBUG GAME CACHE
# -----------------------------

source_path = Path(SOURCE_GAME_CACHE)

if not source_path.exists():
    raise FileNotFoundError(f"Could not find {SOURCE_GAME_CACHE}")

with source_path.open("r", encoding="utf-8") as f:
    full_cache = json.load(f)

platform_counts = defaultdict(int)
debug_cache = {}

for game_id, game_data in full_cache.items():
    platform = game_data.get("system", "Unknown")

    if platform_counts[platform] < MAX_GAMES_PER_PLATFORM:
        debug_cache[game_id] = game_data
        platform_counts[platform] += 1

with open(DEBUG_GAME_CACHE, "w", encoding="utf-8") as f:
    json.dump(debug_cache, f, indent=2, ensure_ascii=False)

print()
print("Created debug JSON cache")
print(f"File: {DEBUG_GAME_CACHE}")
print(f"Games: {len(debug_cache)}")
print(f"Platforms: {len(platform_counts)}")

# -----------------------------
# BUILD DEBUG SQLITE CACHE
# -----------------------------
# This creates a clean library_cache_debug.db from the debug JSON.
# It does not need to copy or trim the big production database.

GAME_FIELDS = [
    "game_id", "title", "system", "rom", "image", "box_art", "screenshot", "music",
    "genre", "developer", "publisher", "release_date", "notes", "favorite",
    "star_rating", "play_count", "play_time", "last_played", "region", "version",
    "play_mode", "max_players", "series", "source", "status", "completed", "broken",
    "portable", "hide", "database_id", "community_star_rating", "platform_notes",
    "platform_manufacturer", "platform_developer", "platform_release_date", "emulator",
    "emulator_id", "emulator_app", "command_line", "launch_command", "cmd",
    "phone_play_available", "retroarch_core", "retroarch_config"
]

db_path = Path(DEBUG_LIBRARY_DB)
if db_path.exists():
    db_path.unlink()

conn = sqlite3.connect(DEBUG_LIBRARY_DB)
cur = conn.cursor()

cur.execute("""
    CREATE TABLE games (
        game_id TEXT PRIMARY KEY,
        title TEXT,
        system TEXT,
        rom TEXT,
        image TEXT,
        box_art TEXT,
        screenshot TEXT,
        music TEXT,
        genre TEXT,
        developer TEXT,
        publisher TEXT,
        release_date TEXT,
        notes TEXT,
        favorite TEXT,
        star_rating TEXT,
        play_count TEXT,
        play_time TEXT,
        last_played TEXT,
        region TEXT,
        version TEXT,
        play_mode TEXT,
        max_players TEXT,
        series TEXT,
        source TEXT,
        status TEXT,
        completed TEXT,
        broken TEXT,
        portable TEXT,
        hide TEXT,
        database_id TEXT,
        community_star_rating TEXT,
        platform_notes TEXT,
        platform_manufacturer TEXT,
        platform_developer TEXT,
        platform_release_date TEXT,
        emulator TEXT,
        emulator_id TEXT,
        emulator_app TEXT,
        command_line TEXT,
        launch_command TEXT,
        cmd TEXT,
        phone_play_available INTEGER,
        retroarch_core TEXT,
        retroarch_config TEXT
    )
""")

cur.execute("CREATE TABLE favorites (game_id TEXT PRIMARY KEY)")
cur.execute("""
    CREATE TABLE recent_plays (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        game_id TEXT,
        title TEXT,
        system TEXT,
        played_at TEXT
    )
""")

placeholders = ",".join(["?"] * len(GAME_FIELDS))
columns = ",".join(GAME_FIELDS)

for game_id, game in debug_cache.items():
    row = []

    for field in GAME_FIELDS:
        if field == "game_id":
            row.append(game_id)
        elif field == "phone_play_available":
            row.append(1 if game.get(field) else 0)
        else:
            value = game.get(field, "")
            row.append("" if value is None else str(value))

    cur.execute(
        f"INSERT INTO games ({columns}) VALUES ({placeholders})",
        row
    )

cur.execute("CREATE INDEX idx_games_title ON games(title)")
cur.execute("CREATE INDEX idx_games_system ON games(system)")
cur.execute("CREATE INDEX idx_games_region ON games(region)")
cur.execute("CREATE INDEX idx_games_genre ON games(genre)")

conn.commit()
conn.close()

print()
print("Created debug SQLite cache")
print(f"File: {DEBUG_LIBRARY_DB}")
print()
print("Platform counts:")
for platform, count in sorted(platform_counts.items()):
    print(f"- {platform}: {count}")

print()
print("DONE")
print("Start the server normally. It will automatically use debug caches when these files exist.")
