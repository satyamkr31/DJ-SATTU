# """
# Music Cog — Core playback engine using yt-dlp + discord.py voice
# Supports: YouTube, SoundCloud, direct URLs, Spotify (via search fallback)
# """

# import discord
# from discord.ext import commands
# from discord import app_commands
# import asyncio
# import yt_dlp
# import os
# import re
# from utils.embeds import MusicEmbed
# from utils.player import MusicPlayer, Song
# from utils.logger import setup_logger

# logger = setup_logger()

# # ── YT-DLP Options ─────────────────────────────────────────────────────────────
# COOKIES_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cookies.txt")

# def _build_ytdl_options() -> dict:
#     opts = {
#         "format": "bestaudio/best",
#         "noplaylist": False,
#         "nocheckcertificate": True,
#         "ignoreerrors": True,
#         "logtostderr": False,
#         "quiet": True,
#         "no_warnings": True,
#         "default_search": "ytsearch",
#         "source_address": "0.0.0.0",
#         "http_headers": {
#             "User-Agent": (
#                 "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#                 "AppleWebKit/537.36 (KHTML, like Gecko) "
#                 "Chrome/124.0.0.0 Safari/537.36"
#             ),
#             "Accept-Language": "en-US,en;q=0.9",
#         },
#         # tv_embedded + android bypass age-gate without any cookies
#         "extractor_args": {
#             "youtube": {
#                 "player_client": ["tv_embedded", "android", "web"],
#                 "player_skip": ["webpage", "js"],   # faster — skip JS parsing
#             }
#         },
#         "age_limit": 99,       # don't filter by age on our end
#     }
#     if os.path.isfile(COOKIES_FILE):
#         opts["cookiefile"] = COOKIES_FILE
#         logger.info(f"✅ Using cookies file: {COOKIES_FILE}")
#     return opts

# YTDL_OPTIONS = _build_ytdl_options()
# ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)


# def get_ffmpeg_options(ffmpeg_path: str) -> dict:
#     return {
#         "executable": ffmpeg_path,
#         "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
#         "options": "-vn",
#     }


# class Music(commands.Cog):
#     def __init__(self, bot):
#         self.bot = bot
#         self.players: dict[int, MusicPlayer] = {}

#         # Spotify — optional, safe import
#         self.spotify = None
#         try:
#             import spotipy
#             from spotipy.oauth2 import SpotifyClientCredentials
#             sp_id = os.getenv("SPOTIFY_CLIENT_ID")
#             sp_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
#             if sp_id and sp_secret:
#                 self.spotify = spotipy.Spotify(
#                     auth_manager=SpotifyClientCredentials(
#                         client_id=sp_id,
#                         client_secret=sp_secret
#                     )
#                 )
#                 logger.info("✅ Spotify client ready")
#         except Exception as e:
#             logger.info(f"Spotify not configured (optional): {e}")

#     def get_player(self, guild_id: int) -> MusicPlayer:
#         if guild_id not in self.players:
#             self.players[guild_id] = MusicPlayer(guild_id)
#         return self.players[guild_id]

#     @property
#     def ffmpeg(self) -> str:
#         return getattr(self.bot, "ffmpeg_path", "ffmpeg")

#     async def ensure_voice(self, interaction: discord.Interaction) -> bool:
#         """Ensure user is in a VC and bot has joined it."""
#         if not interaction.user.voice or not interaction.user.voice.channel:
#             await interaction.followup.send(
#                 embed=MusicEmbed.error("You must be in a voice channel first!"),
#                 ephemeral=True
#             )
#             return False

#         user_channel = interaction.user.voice.channel
#         vc = interaction.guild.voice_client

#         if vc is None:
#             try:
#                 await user_channel.connect(timeout=15.0, reconnect=True)
#                 logger.info(f"Joined VC: {user_channel.name} in {interaction.guild.name}")
#             except Exception as e:
#                 await interaction.followup.send(
#                     embed=MusicEmbed.error(f"Could not join voice channel: {e}"),
#                     ephemeral=True
#                 )
#                 return False
#         elif vc.channel != user_channel:
#             await vc.move_to(user_channel)

#         return True

#     # ── /play ──────────────────────────────────────────────────────────────────
#     @app_commands.command(name="play", description="Play a song or playlist")
#     @app_commands.describe(query="Song name, YouTube/Spotify URL, or mood (e.g. 'sad hindi songs')")
#     async def play(self, interaction: discord.Interaction, query: str):
#         await interaction.response.defer()

#         if not await self.ensure_voice(interaction):
#             return

#         player = self.get_player(interaction.guild_id)
#         player.text_channel = interaction.channel

#         songs = await self._resolve_query(query, interaction.user)

#         if not songs:
#             await interaction.followup.send(
#                 embed=MusicEmbed.error(f"No results found for: `{query}`")
#             )
#             return

#         for song in songs:
#             await player.queue.put(song)

#         if len(songs) == 1:
#             embed = MusicEmbed.added_to_queue(songs[0], player.queue.qsize())
#         else:
#             embed = MusicEmbed.playlist_added(songs, query)

#         await interaction.followup.send(embed=embed)

#         vc = interaction.guild.voice_client
#         if vc and not vc.is_playing():
#             await self._play_next(interaction.guild)

#         try:
#             await self.bot.db.log_play(interaction.user.id, interaction.guild_id, songs[0])
#         except Exception:
#             pass

#     async def _resolve_query(self, query: str, requester) -> list:
#         if "open.spotify.com" in query and self.spotify:
#             return await self._resolve_spotify(query, requester)
#         elif re.match(r"https?://", query):
#             return await self._fetch_url(query, requester)
#         else:
#             return await self._search_youtube(query, requester)

#     async def _search_youtube(self, query: str, requester, limit: int = 1) -> list:
#         loop = asyncio.get_event_loop()
#         # Try YouTube first
#         try:
#             data = await loop.run_in_executor(
#                 None,
#                 lambda: ytdl.extract_info(f"ytsearch{limit}:{query}", download=False)
#             )
#             entries = [e for e in data.get("entries", []) if e]
#             if entries:
#                 return [Song.from_ytdl(e, requester) for e in entries]
#         except Exception as e:
#             logger.warning(f"YouTube search failed ({e}), trying SoundCloud...")

#         # Fallback: SoundCloud
#         try:
#             data = await loop.run_in_executor(
#                 None,
#                 lambda: ytdl.extract_info(f"scsearch{limit}:{query}", download=False)
#             )
#             entries = [e for e in data.get("entries", []) if e]
#             if entries:
#                 logger.info(f"SoundCloud fallback succeeded for: {query}")
#                 return [Song.from_ytdl(e, requester) for e in entries]
#         except Exception as e:
#             logger.error(f"SoundCloud fallback also failed: {e}")

#         return []

#     async def _fetch_url(self, url: str, requester) -> list:
#         loop = asyncio.get_event_loop()
#         try:
#             data = await loop.run_in_executor(
#                 None,
#                 lambda: ytdl.extract_info(url, download=False)
#             )
#             if "entries" in data:
#                 return [Song.from_ytdl(e, requester) for e in data["entries"] if e]
#             return [Song.from_ytdl(data, requester)]
#         except Exception as e:
#             logger.error(f"URL fetch error: {e}")
#             return []

#     async def _resolve_spotify(self, url: str, requester) -> list:
#         songs = []
#         try:
#             if "/track/" in url:
#                 track_id = url.split("/track/")[1].split("?")[0]
#                 track = self.spotify.track(track_id)
#                 query = f"{track['name']} {track['artists'][0]['name']}"
#                 songs = await self._search_youtube(query, requester)
#             elif "/playlist/" in url:
#                 playlist_id = url.split("/playlist/")[1].split("?")[0]
#                 results = self.spotify.playlist_tracks(playlist_id)
#                 for item in results["items"][:50]:
#                     t = item.get("track")
#                     if t:
#                         found = await self._search_youtube(f"{t['name']} {t['artists'][0]['name']}", requester)
#                         songs.extend(found)
#             elif "/album/" in url:
#                 album_id = url.split("/album/")[1].split("?")[0]
#                 results = self.spotify.album_tracks(album_id)
#                 for t in results["items"][:30]:
#                     found = await self._search_youtube(f"{t['name']} {t['artists'][0]['name']}", requester)
#                     songs.extend(found)
#         except Exception as e:
#             logger.error(f"Spotify resolve error: {e}")
#         return songs

#     async def _play_next(self, guild: discord.Guild):
#         player = self.get_player(guild.id)
#         vc = guild.voice_client

#         if not vc or not vc.is_connected():
#             player.current = None
#             return

#         if player.queue.empty():
#             player.current = None
#             ai_cog = self.bot.get_cog("AIDJ")
#             if ai_cog and player.autoplay:
#                 await ai_cog.autoplay_next(guild)
#             return

#         song = await player.queue.get()

#         # Re-fetch fresh stream URL (they expire)
#         try:
#             loop = asyncio.get_event_loop()
#             fresh = await loop.run_in_executor(
#                 None,
#                 lambda: ytdl.extract_info(song.url, download=False)
#             )
#             stream_url = self._best_audio_url(fresh)
#             if stream_url:
#                 song.stream_url = stream_url
#         except Exception as e:
#             logger.warning(f"Stream URL refresh failed: {e}")

#         if not song.stream_url:
#             logger.error(f"No stream URL for: {song.title} — skipping")
#             await self._play_next(guild)
#             return

#         player.current = song
#         player.history.append(song)

#         try:
#             ffmpeg_opts = get_ffmpeg_options(self.ffmpeg)
#             source = discord.FFmpegPCMAudio(song.stream_url, **ffmpeg_opts)
#             source = discord.PCMVolumeTransformer(source, volume=player.volume)

#             def after_play(error):
#                 if error:
#                     logger.error(f"Playback error: {error}")
#                 asyncio.run_coroutine_threadsafe(
#                     self._play_next(guild), self.bot.loop
#                 )

#             vc.play(source, after=after_play)

#             if player.text_channel:
#                 await player.text_channel.send(
#                     embed=MusicEmbed.now_playing(song, player)
#                 )

#         except Exception as e:
#             logger.error(f"Play error: {e}")
#             await self._play_next(guild)

#     def _best_audio_url(self, data: dict) -> str:
#         """Extract the best audio stream URL from yt-dlp data."""
#         formats = data.get("formats", [])
#         # Prefer audio-only
#         for fmt in reversed(formats):
#             if (fmt.get("acodec") not in (None, "none")
#                     and fmt.get("vcodec") in (None, "none", "")
#                     and fmt.get("url")):
#                 return fmt["url"]
#         # Fall back to anything with audio
#         for fmt in reversed(formats):
#             if fmt.get("acodec") not in (None, "none") and fmt.get("url"):
#                 return fmt["url"]
#         return data.get("url", "")

#     # ── /skip ──────────────────────────────────────────────────────────────────
#     @app_commands.command(name="skip", description="Skip the current song")
#     async def skip(self, interaction: discord.Interaction):
#         vc = interaction.guild.voice_client
#         if not vc or not vc.is_playing():
#             return await interaction.response.send_message(
#                 embed=MusicEmbed.error("Nothing is playing!"), ephemeral=True
#             )
#         vc.stop()
#         await interaction.response.send_message(embed=MusicEmbed.success("⏭️ Skipped!"))

#     # ── /stop ──────────────────────────────────────────────────────────────────
#     @app_commands.command(name="stop", description="Stop music and clear queue")
#     async def stop(self, interaction: discord.Interaction):
#         player = self.get_player(interaction.guild_id)
#         player.queue = asyncio.Queue()
#         player.current = None
#         vc = interaction.guild.voice_client
#         if vc:
#             vc.stop()
#             await vc.disconnect()
#         self.players.pop(interaction.guild_id, None)
#         await interaction.response.send_message(embed=MusicEmbed.success("⏹️ Stopped and disconnected."))

#     # ── /pause & /resume ───────────────────────────────────────────────────────
#     @app_commands.command(name="pause", description="Pause playback")
#     async def pause(self, interaction: discord.Interaction):
#         vc = interaction.guild.voice_client
#         if vc and vc.is_playing():
#             vc.pause()
#             await interaction.response.send_message(embed=MusicEmbed.success("⏸️ Paused."))
#         else:
#             await interaction.response.send_message(
#                 embed=MusicEmbed.error("Nothing is playing!"), ephemeral=True)

#     @app_commands.command(name="resume", description="Resume playback")
#     async def resume(self, interaction: discord.Interaction):
#         vc = interaction.guild.voice_client
#         if vc and vc.is_paused():
#             vc.resume()
#             await interaction.response.send_message(embed=MusicEmbed.success("▶️ Resumed."))
#         else:
#             await interaction.response.send_message(
#                 embed=MusicEmbed.error("Not paused."), ephemeral=True)

#     # ── /volume ────────────────────────────────────────────────────────────────
#     @app_commands.command(name="volume", description="Set volume (0-200)")
#     @app_commands.describe(level="Volume level 0-200")
#     async def volume(self, interaction: discord.Interaction, level: int):
#         if not 0 <= level <= 200:
#             return await interaction.response.send_message(
#                 embed=MusicEmbed.error("Volume must be 0–200."), ephemeral=True)
#         player = self.get_player(interaction.guild_id)
#         player.volume = level / 100
#         vc = interaction.guild.voice_client
#         if vc and vc.source:
#             vc.source.volume = player.volume
#         await interaction.response.send_message(
#             embed=MusicEmbed.success(f"🔊 Volume set to **{level}%**"))

#     # ── /nowplaying ────────────────────────────────────────────────────────────
#     @app_commands.command(name="nowplaying", description="Show current song info")
#     async def nowplaying(self, interaction: discord.Interaction):
#         player = self.get_player(interaction.guild_id)
#         if not player.current:
#             return await interaction.response.send_message(
#                 embed=MusicEmbed.error("Nothing is playing."), ephemeral=True)
#         await interaction.response.send_message(
#             embed=MusicEmbed.now_playing(player.current, player))

#     # ── /loop ──────────────────────────────────────────────────────────────────
#     @app_commands.command(name="loop", description="Toggle loop mode")
#     @app_commands.choices(mode=[
#         app_commands.Choice(name="Off", value="off"),
#         app_commands.Choice(name="Song", value="song"),
#         app_commands.Choice(name="Queue", value="queue"),
#     ])
#     async def loop(self, interaction: discord.Interaction, mode: str):
#         player = self.get_player(interaction.guild_id)
#         player.loop_mode = mode
#         icons = {"off": "➡️", "song": "🔂", "queue": "🔁"}
#         await interaction.response.send_message(
#             embed=MusicEmbed.success(f"{icons[mode]} Loop: **{mode.capitalize()}**"))

#     # ── /shuffle ───────────────────────────────────────────────────────────────
#     @app_commands.command(name="shuffle", description="Shuffle the queue")
#     async def shuffle(self, interaction: discord.Interaction):
#         import random
#         player = self.get_player(interaction.guild_id)
#         items = list(player.queue._queue)
#         random.shuffle(items)
#         player.queue._queue.clear()
#         player.queue._queue.extend(items)
#         await interaction.response.send_message(
#             embed=MusicEmbed.success(f"🔀 Shuffled **{len(items)}** songs!"))

#     # ── /autoplay ──────────────────────────────────────────────────────────────
#     @app_commands.command(name="autoplay", description="Toggle AI autoplay")
#     async def autoplay(self, interaction: discord.Interaction):
#         player = self.get_player(interaction.guild_id)
#         player.autoplay = not player.autoplay
#         status = "enabled 🤖" if player.autoplay else "disabled"
#         await interaction.response.send_message(
#             embed=MusicEmbed.success(f"AI Autoplay **{status}**"))

#     # ── /247 ───────────────────────────────────────────────────────────────────
#     @app_commands.command(name="247", description="Toggle 24/7 mode (stay in VC)")
#     async def twentyfourseven(self, interaction: discord.Interaction):
#         player = self.get_player(interaction.guild_id)
#         player.always_on = not player.always_on
#         status = "enabled 🕐" if player.always_on else "disabled"
#         await interaction.response.send_message(
#             embed=MusicEmbed.success(f"24/7 mode **{status}**"))


# async def setup(bot):
#     await bot.add_cog(Music(bot))

"""
Music Cog — Core playback engine using yt-dlp + discord.py voice
Optimized for Railway / Linux hosting
"""

import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import yt_dlp
import os
import re
import random

from utils.embeds import MusicEmbed
from utils.player import MusicPlayer, Song
from utils.logger import setup_logger

logger = setup_logger()

# ─────────────────────────────────────────────────────────────
# YT-DLP CONFIG
# ─────────────────────────────────────────────────────────────

COOKIES_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "cookies.txt"
)

def build_ytdl_options():

    opts = {
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "noplaylist": False,
        "nocheckcertificate": True,
        "ignoreerrors": False,
        "logtostderr": False,
        "quiet": True,
        "no_warnings": True,
        "default_search": "ytsearch",
        "source_address": "0.0.0.0",

        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        },

        "extractor_args": {
            "youtube": {
                "player_client": [
                    "android",
                    "web",
                    "tv_embedded"
                ]
            }
        }
    }

    if os.path.isfile(COOKIES_FILE):
        opts["cookiefile"] = COOKIES_FILE
        logger.info(f"Using cookies: {COOKIES_FILE}")

    return opts

YTDL_OPTIONS = build_ytdl_options()
ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

# ─────────────────────────────────────────────────────────────
# FFMPEG OPTIONS
# ─────────────────────────────────────────────────────────────

FFMPEG_OPTIONS = {
    "before_options": (
        "-reconnect 1 "
        "-reconnect_streamed 1 "
        "-reconnect_delay_max 5"
    ),
    "options": (
        "-vn "
        "-bufsize 64k"
    )
}

# ─────────────────────────────────────────────────────────────
# MUSIC COG
# ─────────────────────────────────────────────────────────────

class Music(commands.Cog):

    def __init__(self, bot):

        self.bot = bot
        self.players = {}

        # Spotify
        self.spotify = None

        try:
            import spotipy
            from spotipy.oauth2 import SpotifyClientCredentials

            sp_id = os.getenv("SPOTIFY_CLIENT_ID")
            sp_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

            if sp_id and sp_secret:
                self.spotify = spotipy.Spotify(
                    auth_manager=SpotifyClientCredentials(
                        client_id=sp_id,
                        client_secret=sp_secret
                    )
                )

                logger.info("✅ Spotify Ready")

        except Exception as e:
            logger.warning(f"Spotify unavailable: {e}")

    # ─────────────────────────────────────────────────────────

    def get_player(self, guild_id):

        if guild_id not in self.players:
            self.players[guild_id] = MusicPlayer(guild_id)

        return self.players[guild_id]

    # ─────────────────────────────────────────────────────────

    @property
    def ffmpeg(self):
        return getattr(self.bot, "ffmpeg_path", "ffmpeg")

    # ─────────────────────────────────────────────────────────
    # VOICE
    # ─────────────────────────────────────────────────────────

    async def ensure_voice(self, interaction):

        if not interaction.user.voice:
            await interaction.followup.send(
                embed=MusicEmbed.error(
                    "Join a voice channel first!"
                ),
                ephemeral=True
            )
            return False

        channel = interaction.user.voice.channel
        vc = interaction.guild.voice_client

        try:

            if vc is None:
                await channel.connect(
                    timeout=20,
                    reconnect=True
                )

            elif vc.channel != channel:
                await vc.move_to(channel)

            return True

        except Exception as e:

            logger.error(f"VC connect error: {e}")

            await interaction.followup.send(
                embed=MusicEmbed.error(
                    f"Could not join VC:\n{e}"
                ),
                ephemeral=True
            )

            return False

    # ─────────────────────────────────────────────────────────
    # PLAY
    # ─────────────────────────────────────────────────────────

    @app_commands.command(
        name="play",
        description="Play a song"
    )
    async def play(
        self,
        interaction: discord.Interaction,
        query: str
    ):

        await interaction.response.defer()

        if not await self.ensure_voice(interaction):
            return

        player = self.get_player(interaction.guild_id)
        player.text_channel = interaction.channel

        songs = await self.resolve_query(
            query,
            interaction.user
        )

        if not songs:

            return await interaction.followup.send(
                embed=MusicEmbed.error(
                    f"No results for:\n`{query}`"
                )
            )

        for song in songs:
            await player.queue.put(song)

        await interaction.followup.send(
            embed=MusicEmbed.added_to_queue(
                songs[0],
                player.queue.qsize()
            )
        )

        vc = interaction.guild.voice_client

        if not vc.is_playing():
            await self.play_next(interaction.guild)

    # ─────────────────────────────────────────────────────────
    # QUERY RESOLVER
    # ─────────────────────────────────────────────────────────

    async def resolve_query(self, query, requester):

        if "spotify.com" in query and self.spotify:
            return await self.resolve_spotify(query, requester)

        elif re.match(r"https?://", query):
            return await self.fetch_url(query, requester)

        else:
            return await self.search_youtube(query, requester)

    # ─────────────────────────────────────────────────────────
    # YOUTUBE SEARCH
    # ─────────────────────────────────────────────────────────

    async def search_youtube(
        self,
        query,
        requester,
        limit=1
    ):

        loop = asyncio.get_event_loop()

        try:

            data = await loop.run_in_executor(
                None,
                lambda: ytdl.extract_info(
                    f"ytsearch{limit}:{query}",
                    download=False
                )
            )

            entries = data.get("entries", [])

            songs = []

            for entry in entries:
                if entry:
                    songs.append(
                        Song.from_ytdl(entry, requester)
                    )

            return songs

        except Exception as e:

            logger.error(f"YT Search Error: {e}")

            return []

    # ─────────────────────────────────────────────────────────
    # URL FETCH
    # ─────────────────────────────────────────────────────────

    async def fetch_url(self, url, requester):

        loop = asyncio.get_event_loop()

        try:

            data = await loop.run_in_executor(
                None,
                lambda: ytdl.extract_info(
                    url,
                    download=False
                )
            )

            if "entries" in data:

                songs = []

                for entry in data["entries"]:
                    if entry:
                        songs.append(
                            Song.from_ytdl(entry, requester)
                        )

                return songs

            return [Song.from_ytdl(data, requester)]

        except Exception as e:

            logger.error(f"URL Error: {e}")

            return []

    # ─────────────────────────────────────────────────────────
    # SPOTIFY
    # ─────────────────────────────────────────────────────────

    async def resolve_spotify(self, url, requester):

        songs = []

        try:

            if "/track/" in url:

                track_id = url.split("/track/")[1].split("?")[0]

                track = self.spotify.track(track_id)

                query = (
                    f"{track['name']} "
                    f"{track['artists'][0]['name']}"
                )

                songs.extend(
                    await self.search_youtube(query, requester)
                )

        except Exception as e:

            logger.error(f"Spotify Error: {e}")

        return songs

    # ─────────────────────────────────────────────────────────
    # PLAY NEXT
    # ─────────────────────────────────────────────────────────

    async def play_next(self, guild):

        player = self.get_player(guild.id)
        vc = guild.voice_client

        if not vc or not vc.is_connected():
            return

        if player.queue.empty():

            player.current = None

            return

        song = await player.queue.get()

        try:

            loop = asyncio.get_event_loop()

            data = await loop.run_in_executor(
                None,
                lambda: ytdl.extract_info(
                    song.url,
                    download=False
                )
            )

            stream_url = self.best_audio(data)

            if not stream_url:
                return await self.play_next(guild)

            player.current = song
            player.history.append(song)

            source = discord.FFmpegPCMAudio(
                stream_url,
                executable=self.ffmpeg,
                **FFMPEG_OPTIONS
            )

            source = discord.PCMVolumeTransformer(
                source,
                volume=player.volume
            )

            def after_play(error):

                if error:
                    logger.error(f"Playback Error: {error}")

                fut = asyncio.run_coroutine_threadsafe(
                    self.play_next(guild),
                    self.bot.loop
                )

                try:
                    fut.result()
                except:
                    pass

            vc.play(
                source,
                after=after_play
            )

            if player.text_channel:

                await player.text_channel.send(
                    embed=MusicEmbed.now_playing(
                        song,
                        player
                    )
                )

        except Exception as e:

            logger.error(f"Play Error: {e}")

            await self.play_next(guild)

    # ─────────────────────────────────────────────────────────
    # AUDIO FORMAT
    # ─────────────────────────────────────────────────────────

    def best_audio(self, data):

        formats = data.get("formats", [])

        audio_formats = []

        for fmt in formats:

            if (
                fmt.get("acodec") != "none"
                and fmt.get("url")
            ):
                audio_formats.append(fmt)

        if audio_formats:
            return audio_formats[-1]["url"]

        return data.get("url")

    # ─────────────────────────────────────────────────────────
    # SKIP
    # ─────────────────────────────────────────────────────────

    @app_commands.command(
        name="skip",
        description="Skip current song"
    )
    async def skip(self, interaction):

        vc = interaction.guild.voice_client

        if vc and vc.is_playing():

            vc.stop()

            await interaction.response.send_message(
                embed=MusicEmbed.success(
                    "⏭️ Skipped"
                )
            )

        else:

            await interaction.response.send_message(
                embed=MusicEmbed.error(
                    "Nothing playing"
                ),
                ephemeral=True
            )

    # ─────────────────────────────────────────────────────────
    # STOP
    # ─────────────────────────────────────────────────────────

    @app_commands.command(
        name="stop",
        description="Stop playback"
    )
    async def stop(self, interaction):

        player = self.get_player(interaction.guild_id)

        player.queue = asyncio.Queue()
        player.current = None

        vc = interaction.guild.voice_client

        if vc:
            vc.stop()
            await vc.disconnect()

        await interaction.response.send_message(
            embed=MusicEmbed.success(
                "⏹️ Stopped"
            )
        )

    # ─────────────────────────────────────────────────────────
    # VOLUME
    # ─────────────────────────────────────────────────────────

    @app_commands.command(
        name="volume",
        description="Set volume"
    )
    async def volume(
        self,
        interaction,
        level: int
    ):

        if not 0 <= level <= 200:

            return await interaction.response.send_message(
                embed=MusicEmbed.error(
                    "Volume must be 0-200"
                ),
                ephemeral=True
            )

        player = self.get_player(interaction.guild_id)

        player.volume = level / 100

        vc = interaction.guild.voice_client

        if vc and vc.source:
            vc.source.volume = player.volume

        await interaction.response.send_message(
            embed=MusicEmbed.success(
                f"🔊 Volume: {level}%"
            )
        )

# ─────────────────────────────────────────────────────────────
# SETUP
# ─────────────────────────────────────────────────────────────

async def setup(bot):
    await bot.add_cog(Music(bot))