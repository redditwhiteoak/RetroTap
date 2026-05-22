import os
import sqlite3
from datetime import datetime


DB_FILE = "library_cache.db"

from cache_selector import get_library_db_file


def resolve_db_file(db_file=None):
    return db_file or get_library_db_file()


GAME_FIELDS = [
    "game_id", "title", "system", "rom", "image", "box_art", "screenshot","music", "genre", "developer", "publisher", "release_date",
    "notes", "favorite", "star_rating", "play_count", "play_time",
    "last_played", "region", "version", "play_mode", "max_players",
    "series", "source", "status", "completed", "broken", "portable", "hide",
    "database_id", "community_star_rating", "platform_notes",
    "platform_manufacturer", "platform_developer", "platform_release_date",
    "emulator", "emulator_id", "emulator_app", "command_line",
    "launch_command", "cmd", "phone_play_available",
    "retroarch_core", "retroarch_config"
]


def connect(db_file=None):
    db_file = resolve_db_file(db_file)
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_file=None):
    conn = connect(db_file)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS games (
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

    cur.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            game_id TEXT PRIMARY KEY
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS recent_plays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT,
            title TEXT,
            system TEXT,
            played_at TEXT
        )
    """)

    existing_columns = [
        row[1]
        for row in cur.execute("PRAGMA table_info(games)").fetchall()
    ]

    if "retroarch_core" not in existing_columns:
        cur.execute("ALTER TABLE games ADD COLUMN retroarch_core TEXT")

    if "retroarch_config" not in existing_columns:
        cur.execute("ALTER TABLE games ADD COLUMN retroarch_config TEXT")

    extra_columns = [
        "series",
        "source",
        "status",
        "completed",
        "broken",
        "portable",
        "hide",
        "database_id",
        "community_star_rating",
        "platform_notes",
        "platform_manufacturer",
        "platform_developer",
        "platform_release_date",
    ]

    for column in extra_columns:
        if column not in existing_columns:
            cur.execute(f"ALTER TABLE games ADD COLUMN {column} TEXT")

    cur.execute("CREATE INDEX IF NOT EXISTS idx_games_title ON games(title)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_games_system ON games(system)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_games_region ON games(region)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_games_genre ON games(genre)")

    conn.commit()
    conn.close()


def dict_to_db_row(game_id, game):
    row = {}

    for field in GAME_FIELDS:
        if field == "game_id":
            row[field] = game_id
        elif field == "phone_play_available":
            row[field] = 1 if game.get(field) else 0
        else:
            value = game.get(field, "")
            if value is None:
                value = ""
            row[field] = str(value)

    return row


def upsert_games(games, db_file=None):
    init_db(db_file)

    conn = connect(db_file)
    cur = conn.cursor()

    placeholders = ",".join(["?"] * len(GAME_FIELDS))
    columns = ",".join(GAME_FIELDS)
    update = ",".join(
        f"{field}=excluded.{field}"
        for field in GAME_FIELDS
        if field != "game_id"
    )

    sql = f"""
        INSERT INTO games ({columns})
        VALUES ({placeholders})
        ON CONFLICT(game_id) DO UPDATE SET {update}
    """

    rows = []

    for game_id, game in games.items():
        row = dict_to_db_row(game_id, game)
        rows.append([row[field] for field in GAME_FIELDS])

    cur.executemany(sql, rows)
    conn.commit()
    conn.close()


def load_all_games(db_file=None):
    init_db(db_file)

    conn = connect(db_file)
    rows = conn.execute(
        "SELECT * FROM games ORDER BY title COLLATE NOCASE"
    ).fetchall()
    conn.close()

    games = {}

    for row in rows:
        game = dict(row)
        game_id = game.pop("game_id")
        game["phone_play_available"] = bool(game.get("phone_play_available"))
        games[game_id] = game

    return games


def search_games(query="", platform="", region_filters=None, genre="", favorites_only=False, limit=500, db_file=None):
    init_db(db_file)

    region_filters = region_filters or []

    sql = "SELECT g.* FROM games g"
    params = []

    if favorites_only:
        sql += " JOIN favorites f ON f.game_id = g.game_id"

    where = []

    if query:
        where.append("g.title LIKE ?")
        params.append(f"%{query}%")

    if platform:
        where.append("g.system = ?")
        params.append(platform)

    if genre:
        where.append("g.genre = ?")
        params.append(genre)

    if region_filters:
        marks = ",".join(["?"] * len(region_filters))
        where.append(f"g.region IN ({marks})")
        params.extend(region_filters)

    if where:
        sql += " WHERE " + " AND ".join(where)

    sql += " ORDER BY g.title COLLATE NOCASE LIMIT ?"
    params.append(limit)

    conn = connect(db_file)
    rows = conn.execute(sql, params).fetchall()
    conn.close()

    output = []

    for row in rows:
        game = dict(row)
        game_id = game.pop("game_id")
        game["phone_play_available"] = bool(game.get("phone_play_available"))
        output.append((game_id, game))

    return output


def load_favorites(db_file=None):
    init_db(db_file)

    conn = connect(db_file)
    rows = conn.execute("SELECT game_id FROM favorites").fetchall()
    conn.close()

    return set(row["game_id"] for row in rows)


def toggle_favorite(game_id, db_file=None):
    init_db(db_file)

    conn = connect(db_file)
    existing = conn.execute(
        "SELECT game_id FROM favorites WHERE game_id = ?",
        (game_id,)
    ).fetchone()

    if existing:
        conn.execute("DELETE FROM favorites WHERE game_id = ?", (game_id,))
    else:
        conn.execute("INSERT OR IGNORE INTO favorites(game_id) VALUES (?)", (game_id,))

    conn.commit()
    conn.close()


def record_recent_play(game_id, title, system, db_file=None):
    init_db(db_file)

    conn = connect(db_file)

    # Keep recently played unique by game. Re-launching moves it to the top.
    conn.execute(
        "DELETE FROM recent_plays WHERE game_id = ?",
        (game_id,)
    )

    conn.execute(
        """
        INSERT INTO recent_plays(game_id, title, system, played_at)
        VALUES (?, ?, ?, ?)
        """,
        (game_id, title, system, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()


def get_recent_plays(limit=25, db_file=None):
    init_db(db_file)

    conn = connect(db_file)
    rows = conn.execute(
        """
        SELECT g.*, latest.played_at
        FROM (
            SELECT game_id, MAX(id) AS max_id, MAX(played_at) AS played_at
            FROM recent_plays
            GROUP BY game_id
            ORDER BY max_id DESC
            LIMIT ?
        ) latest
        JOIN games g ON g.game_id = latest.game_id
        ORDER BY latest.max_id DESC
        """,
        (limit,)
    ).fetchall()
    conn.close()

    output = []

    for row in rows:
        game = dict(row)
        game_id = game.pop("game_id")
        game["phone_play_available"] = bool(game.get("phone_play_available"))
        output.append((game_id, game))

    return output



def get_distinct_values(field, db_file=None):
    allowed = {"system", "region", "genre", "developer", "publisher", "emulator"}

    if field not in allowed:
        return []

    init_db(db_file)

    conn = connect(db_file)
    rows = conn.execute(
        f"""
        SELECT DISTINCT {field} AS value
        FROM games
        WHERE {field} IS NOT NULL AND {field} != ''
        ORDER BY {field} COLLATE NOCASE
        """
    ).fetchall()
    conn.close()

    return [row["value"] for row in rows]


def get_random_game(platform="", region_filters=None, genre="", favorites_only=False, db_file=None):
    init_db(db_file)

    region_filters = region_filters or []

    sql = "SELECT g.* FROM games g"
    params = []

    if favorites_only:
        sql += " JOIN favorites f ON f.game_id = g.game_id"

    where = []

    if platform:
        where.append("g.system = ?")
        params.append(platform)

    if genre:
        where.append("g.genre = ?")
        params.append(genre)

    if region_filters:
        marks = ",".join(["?"] * len(region_filters))
        where.append(f"g.region IN ({marks})")
        params.extend(region_filters)

    if where:
        sql += " WHERE " + " AND ".join(where)

    sql += " ORDER BY RANDOM() LIMIT 1"

    conn = connect(db_file)
    row = conn.execute(sql, params).fetchone()
    conn.close()

    if not row:
        return None, None

    game = dict(row)
    game_id = game.pop("game_id")
    game["phone_play_available"] = bool(game.get("phone_play_available"))

    return game_id, game



def clear_favorites(db_file=None):
    init_db(db_file)

    conn = connect(db_file)
    conn.execute("DELETE FROM favorites")
    conn.commit()
    conn.close()


def clear_recent_plays(db_file=None):
    init_db(db_file)

    conn = connect(db_file)
    conn.execute("DELETE FROM recent_plays")
    conn.commit()
    conn.close()



def get_platform_summaries(region_filters=None, db_file=None):
    init_db(db_file)

    region_filters = region_filters or []

    params = []

    where = ""

    if region_filters:
        marks = ",".join(["?"] * len(region_filters))
        where = f"WHERE region IN ({marks})"
        params.extend(region_filters)

    sql = f"""
        SELECT
            system,
            COUNT(*) AS game_count,
            MAX(phone_play_available) AS phone_play_available,
            GROUP_CONCAT(title, ' ') AS game_titles
        FROM games
        {where}
        GROUP BY system
        ORDER BY system COLLATE NOCASE
    """

    conn = connect(db_file)
    rows = conn.execute(sql, params).fetchall()
    conn.close()

    output = []

    for row in rows:
        output.append({
            "system": row["system"],
            "game_count": row["game_count"],
            "phone_play_available": bool(row["phone_play_available"]),
            "game_titles": row["game_titles"] or ""
        })

    return output
