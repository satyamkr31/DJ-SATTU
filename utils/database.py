"""
Database — SQLite async wrapper for playlists, history, stats, settings
Uses aiosqlite for non-blocking I/O
"""

import aiosqlite
import os
from datetime import datetime
from utils.logger import setup_logger

logger = setup_logger()
DB_PATH = os.getenv("DB_PATH", "data/musicbot.db")


class Database:
    def __init__(self):
        os.makedirs("data", exist_ok=True)

    async def init(self):
        """Create tables on startup"""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.executescript("""
                CREATE TABLE IF NOT EXISTS play_history (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER NOT NULL,
                    guild_id    INTEGER NOT NULL,
                    title       TEXT,
                    url         TEXT,
                    artist      TEXT,
                    duration    INTEGER,
                    played_at   TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS playlists (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER NOT NULL,
                    name        TEXT NOT NULL,
                    created_at  TEXT DEFAULT (datetime('now')),
                    UNIQUE(user_id, name)
                );

                CREATE TABLE IF NOT EXISTS playlist_songs (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    playlist_id INTEGER REFERENCES playlists(id) ON DELETE CASCADE,
                    title       TEXT,
                    url         TEXT,
                    artist      TEXT,
                    duration    INTEGER,
                    added_at    TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS reactions (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER,
                    guild_id    INTEGER,
                    title       TEXT,
                    reaction    TEXT,
                    reacted_at  TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS settings (
                    guild_id    INTEGER NOT NULL,
                    key         TEXT NOT NULL,
                    value       TEXT,
                    PRIMARY KEY (guild_id, key)
                );

                CREATE INDEX IF NOT EXISTS idx_history_user ON play_history(user_id);
                CREATE INDEX IF NOT EXISTS idx_history_guild ON play_history(guild_id);
            """)
            await db.commit()
        logger.info("✅ Database initialized")

    # ── Play history ───────────────────────────────────────────────────────────
    async def log_play(self, user_id: int, guild_id: int, song):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO play_history (user_id, guild_id, title, url, artist, duration) VALUES (?,?,?,?,?,?)",
                (user_id, guild_id, song.title, song.url, song.artist, song.duration)
            )
            await db.commit()

    async def get_user_history(self, user_id: int, limit: int = 20) -> list:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM play_history WHERE user_id=? ORDER BY played_at DESC LIMIT ?",
                (user_id, limit)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    # ── Leaderboard ────────────────────────────────────────────────────────────
    async def get_leaderboard(self, guild_id: int, type: str) -> list:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            if type == "listeners":
                query = """
                    SELECT user_id, COUNT(*) as play_count
                    FROM play_history WHERE guild_id=?
                    GROUP BY user_id ORDER BY play_count DESC LIMIT 10
                """
            elif type == "songs":
                query = """
                    SELECT title, COUNT(*) as count
                    FROM play_history WHERE guild_id=?
                    GROUP BY title ORDER BY count DESC LIMIT 10
                """
            elif type == "artists":
                query = """
                    SELECT artist, COUNT(*) as count
                    FROM play_history WHERE guild_id=?
                    GROUP BY artist ORDER BY count DESC LIMIT 10
                """
            else:
                return []

            async with db.execute(query, (guild_id,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    # ── User stats ─────────────────────────────────────────────────────────────
    async def get_user_stats(self, user_id: int, guild_id: int) -> dict:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT COUNT(*) as total, SUM(duration) as total_secs FROM play_history WHERE user_id=? AND guild_id=?",
                (user_id, guild_id)
            ) as cur:
                row = dict(await cur.fetchone())

            async with db.execute(
                "SELECT artist, COUNT(*) as c FROM play_history WHERE user_id=? GROUP BY artist ORDER BY c DESC LIMIT 1",
                (user_id,)
            ) as cur:
                top_artist_row = await cur.fetchone()

            async with db.execute(
                "SELECT title, COUNT(*) as c FROM play_history WHERE user_id=? GROUP BY title ORDER BY c DESC LIMIT 1",
                (user_id,)
            ) as cur:
                top_song_row = await cur.fetchone()

            total_secs = row.get("total_secs") or 0
            hours, rem = divmod(int(total_secs), 3600)
            mins = rem // 60
            time_str = f"{hours}h {mins}m" if hours else f"{mins}m"

            return {
                "total_plays": row.get("total", 0),
                "total_time": time_str,
                "top_artist": top_artist_row[0] if top_artist_row else "N/A",
                "top_song": top_song_row[0] if top_song_row else "N/A",
                "top_genre": "N/A",
                "streak": 0,
            }

    async def get_server_stats(self, guild_id: int) -> dict:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT COUNT(*) as total, COUNT(DISTINCT user_id) as users FROM play_history WHERE guild_id=?",
                (guild_id,)
            ) as cur:
                row = dict(await cur.fetchone())

            async with db.execute(
                "SELECT title, COUNT(*) as c FROM play_history WHERE guild_id=? GROUP BY title ORDER BY c DESC LIMIT 1",
                (guild_id,)
            ) as cur:
                top_song = await cur.fetchone()

            async with db.execute(
                "SELECT artist, COUNT(*) as c FROM play_history WHERE guild_id=? GROUP BY artist ORDER BY c DESC LIMIT 1",
                (guild_id,)
            ) as cur:
                top_artist = await cur.fetchone()

            return {
                "total_plays": row.get("total", 0),
                "unique_listeners": row.get("users", 0),
                "top_song": top_song[0] if top_song else "N/A",
                "top_artist": top_artist[0] if top_artist else "N/A",
                "peak_hour": "N/A",
                "top_genre": "N/A",
            }

    # ── Playlists ──────────────────────────────────────────────────────────────
    async def create_playlist(self, user_id: int, name: str):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR IGNORE INTO playlists (user_id, name) VALUES (?,?)",
                (user_id, name)
            )
            await db.commit()

    async def get_playlists(self, user_id: int) -> list:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT p.name, COUNT(ps.id) as song_count
                FROM playlists p
                LEFT JOIN playlist_songs ps ON p.id = ps.playlist_id
                WHERE p.user_id = ?
                GROUP BY p.id
            """, (user_id,)) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def add_to_playlist(self, user_id: int, name: str, song):
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT id FROM playlists WHERE user_id=? AND name=?", (user_id, name)
            ) as cur:
                row = await cur.fetchone()
            if not row:
                await db.execute("INSERT INTO playlists (user_id, name) VALUES (?,?)", (user_id, name))
                await db.commit()
                async with db.execute(
                    "SELECT id FROM playlists WHERE user_id=? AND name=?", (user_id, name)
                ) as cur:
                    row = await cur.fetchone()

            await db.execute(
                "INSERT INTO playlist_songs (playlist_id, title, url, artist, duration) VALUES (?,?,?,?,?)",
                (row[0], song.title, song.url, song.artist, song.duration)
            )
            await db.commit()

    async def get_playlist_songs(self, user_id: int, name: str) -> list:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT ps.* FROM playlist_songs ps
                JOIN playlists p ON p.id = ps.playlist_id
                WHERE p.user_id=? AND p.name=?
                ORDER BY ps.added_at
            """, (user_id, name)) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def delete_playlist(self, user_id: int, name: str):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "DELETE FROM playlists WHERE user_id=? AND name=?", (user_id, name)
            )
            await db.commit()

    # ── Reactions ──────────────────────────────────────────────────────────────
    async def log_reaction(self, user_id: int, guild_id: int, song, reaction: str):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO reactions (user_id, guild_id, title, reaction) VALUES (?,?,?,?)",
                (user_id, guild_id, song.title, reaction)
            )
            await db.commit()

    # ── Settings ───────────────────────────────────────────────────────────────
    async def set_setting(self, guild_id: int, key: str, value: str):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR REPLACE INTO settings (guild_id, key, value) VALUES (?,?,?)",
                (guild_id, key, value)
            )
            await db.commit()

    async def get_setting(self, guild_id: int, key: str) -> str | None:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT value FROM settings WHERE guild_id=? AND key=?", (guild_id, key)
            ) as cur:
                row = await cur.fetchone()
                return row[0] if row else None
