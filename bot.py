# """
# Discord Music Bot - Main Entry Point
# Full-featured bot with AI DJ, recommendations, and web dashboard
# """

# import discord
# from discord.ext import commands
# import asyncio
# import os
# import shutil
# import ctypes
# import ctypes.util
# from dotenv import load_dotenv
# from utils.logger import setup_logger
# from utils.database import Database

# load_dotenv()
# logger = setup_logger()


# # ── FFmpeg Detection ───────────────────────────────────────────────────────────
# def find_ffmpeg() -> str:
#     """Find ffmpeg executable — checks PATH and common Windows locations."""
#     found = shutil.which("ffmpeg")
#     if found:
#         return found

#     windows_paths = [
#         r"C:\ffmpeg\bin\ffmpeg.exe",
#         r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
#         r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
#         os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg.exe"),
#         os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg", "bin", "ffmpeg.exe"),
#     ]
#     for path in windows_paths:
#         if os.path.isfile(path):
#             logger.info(f"Found ffmpeg at: {path}")
#             return path

#     return "ffmpeg"  # will produce a clear error at play time


# FFMPEG_PATH = find_ffmpeg()
# logger.info(f"FFmpeg executable: {FFMPEG_PATH}")


# # ── Opus Detection ─────────────────────────────────────────────────────────────
# def load_opus_library():
#     if discord.opus.is_loaded():
#         return
#     lib = ctypes.util.find_library("opus")
#     if lib:
#         try:
#             discord.opus.load_opus(lib)
#             logger.info(f"✅ Opus loaded: {lib}")
#             return
#         except Exception:
#             pass
#     bot_dir = os.path.dirname(os.path.abspath(__file__))
#     for dll in ["libopus-0.x64.dll", "libopus-0.x86.dll", "opus.dll", "libopus.dll"]:
#         dll_path = os.path.join(bot_dir, dll)
#         if os.path.isfile(dll_path):
#             try:
#                 discord.opus.load_opus(dll_path)
#                 logger.info(f"✅ Opus loaded from file: {dll_path}")
#                 return
#             except Exception:
#                 pass
#     logger.warning("⚠️  Opus not loaded — download libopus-0.x64.dll and place it next to bot.py")

# load_opus_library()


# # ── Bot Setup ──────────────────────────────────────────────────────────────────
# intents = discord.Intents.default()
# intents.message_content = True
# intents.voice_states = True
# intents.members = True

# bot = commands.Bot(
#     command_prefix="!",
#     intents=intents,
#     help_command=None,
#     description="Advanced AI Music Bot"
# )

# bot.db = Database()
# bot.ffmpeg_path = FFMPEG_PATH  # shared with music cog


# # ── Events ─────────────────────────────────────────────────────────────────────
# @bot.event
# async def on_ready():
#     logger.info(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
#     await bot.db.init()
#     await bot.change_presence(
#         activity=discord.Activity(
#             type=discord.ActivityType.listening,
#             name="🎵 /play to start!"
#         )
#     )
#     # Guild sync = instant (global sync takes up to 1 hour)
#     synced_count = 0
#     for guild in bot.guilds:
#         try:
#             bot.tree.copy_global_to(guild=guild)
#             await bot.tree.sync(guild=guild)
#             synced_count += 1
#         except Exception as e:
#             logger.error(f"❌ Sync failed for {guild.name}: {e}")
#     logger.info(f"✅ Slash commands synced to {synced_count} guild(s)")


# @bot.event
# async def on_guild_join(guild):
#     """Sync slash commands when bot joins a new server."""
#     try:
#         bot.tree.copy_global_to(guild=guild)
#         await bot.tree.sync(guild=guild)
#         logger.info(f"✅ Synced commands to new guild: {guild.name}")
#     except Exception as e:
#         logger.error(f"Sync error on join {guild.name}: {e}")


# @bot.event
# async def on_voice_state_update(member, before, after):
#     """Auto-leave when voice channel is empty for 30 seconds."""
#     if member.bot:
#         return
#     guild = member.guild
#     voice_client = guild.voice_client
#     if voice_client and len(voice_client.channel.members) == 1:
#         await asyncio.sleep(30)
#         if voice_client and len(voice_client.channel.members) == 1:
#             await voice_client.disconnect()
#             logger.info(f"Auto-left empty VC in {guild.name}")


# @bot.event
# async def on_command_error(ctx, error):
#     if isinstance(error, commands.CommandNotFound):
#         return
#     logger.error(f"Error: {error}")


# # ── Load Cogs ──────────────────────────────────────────────────────────────────
# async def load_cogs():
#     cogs = [
#         "cogs.music",
#         "cogs.queue",
#         "cogs.ai_dj",
#         "cogs.filters",
#         "cogs.playlist",
#         "cogs.social",
#         "cogs.dashboard",
#         "cogs.lyrics",
#         "cogs.radio",
#         "cogs.admin",
#     ]
#     for cog in cogs:
#         try:
#             await bot.load_extension(cog)
#             logger.info(f"✅ Loaded: {cog}")
#         except Exception as e:
#             logger.error(f"❌ Failed to load {cog}: {e}")


# async def main():
#     async with bot:
#         await load_cogs()
#         token = os.getenv("DISCORD_TOKEN")
#         if not token:
#             raise ValueError("DISCORD_TOKEN not found in .env file!")
#         await bot.start(token)


# if __name__ == "__main__":
#     asyncio.run(main())

import discord
from discord.ext import commands
import asyncio
import os
import shutil
import ctypes
import ctypes.util
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

from utils.logger import setup_logger
from utils.database import Database

load_dotenv()
logger = setup_logger()

# ─────────────────────────────────────────────────────────────
# KEEP ALIVE WEB SERVER (Required for Railway/UptimeRobot)
# ─────────────────────────────────────────────────────────────

app = Flask(__name__)

@app.route("/")
def home():
    return "SattuWave Music Bot is Online!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# ─────────────────────────────────────────────────────────────
# FFmpeg Detection
# ─────────────────────────────────────────────────────────────

def find_ffmpeg():
    found = shutil.which("ffmpeg")
    if found:
        return found

    windows_paths = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg.exe"),
    ]

    for path in windows_paths:
        if os.path.isfile(path):
            logger.info(f"Found ffmpeg: {path}")
            return path

    return "ffmpeg"

FFMPEG_PATH = find_ffmpeg()
logger.info(f"FFmpeg path: {FFMPEG_PATH}")

# ─────────────────────────────────────────────────────────────
# Opus Detection
# ─────────────────────────────────────────────────────────────

def load_opus_library():
    if discord.opus.is_loaded():
        return

    lib = ctypes.util.find_library("opus")

    if lib:
        try:
            discord.opus.load_opus(lib)
            logger.info(f"✅ Opus loaded: {lib}")
            return
        except Exception as e:
            logger.warning(f"Opus load failed: {e}")

    logger.warning("⚠️ Opus library not loaded")

load_opus_library()

# ─────────────────────────────────────────────────────────────
# Discord Bot Setup
# ─────────────────────────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None,
    description="SattuWave AI Music Bot",
)

bot.db = Database()
bot.ffmpeg_path = FFMPEG_PATH

# ─────────────────────────────────────────────────────────────
# EVENTS
# ─────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    logger.info(f"✅ Logged in as {bot.user}")
    logger.info(f"✅ Bot ID: {bot.user.id}")

    await bot.db.init()

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening,
            name="/play 🎵"
        )
    )

    synced = 0

    for guild in bot.guilds:
        try:
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
            synced += 1
        except Exception as e:
            logger.error(f"Sync failed in {guild.name}: {e}")

    logger.info(f"✅ Synced commands in {synced} guilds")

@bot.event
async def on_guild_join(guild):
    try:
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
        logger.info(f"✅ Joined and synced: {guild.name}")
    except Exception as e:
        logger.error(f"Guild join sync error: {e}")

@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return

    voice_client = member.guild.voice_client

    if voice_client:
        if len(voice_client.channel.members) == 1:
            await asyncio.sleep(30)

            if voice_client and len(voice_client.channel.members) == 1:
                await voice_client.disconnect()
                logger.info(f"Disconnected from empty VC")

@bot.event
async def on_command_error(ctx, error):
    logger.error(f"Command Error: {error}")

# ─────────────────────────────────────────────────────────────
# LOAD COGS
# ─────────────────────────────────────────────────────────────

async def load_cogs():

    cogs = [
        "cogs.music",
        "cogs.queue",
        "cogs.ai_dj",
        "cogs.filters",
        "cogs.playlist",
        "cogs.social",
        "cogs.dashboard",
        "cogs.lyrics",
        "cogs.radio",
        "cogs.admin",
    ]

    for cog in cogs:
        try:
            await bot.load_extension(cog)
            logger.info(f"✅ Loaded {cog}")
        except Exception as e:
            logger.error(f"❌ Failed {cog}: {e}")

# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

async def main():

    token = os.getenv("DISCORD_TOKEN")

    if not token:
        raise ValueError("DISCORD_TOKEN missing in .env")

    keep_alive()

    async with bot:
        await load_cogs()
        await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())