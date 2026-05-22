"""
Embed helpers — Consistent, beautiful Discord embeds
"""

import discord
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from utils.player import Song, MusicPlayer


class MusicEmbed:

    @staticmethod
    def now_playing(song: "Song", player: "MusicPlayer") -> discord.Embed:
        embed = discord.Embed(
            title="🎵 Now Playing",
            description=f"**[{song.title}]({song.url})**",
            color=discord.Color.purple()
        )
        embed.add_field(name="Duration",  value=song.duration_str, inline=True)
        embed.add_field(name="Requested", value=song.requester.mention, inline=True)
        embed.add_field(name="Volume",    value=f"{int(player.volume * 100)}%", inline=True)
        embed.add_field(name="Loop",      value=player.loop_mode.capitalize(), inline=True)
        embed.add_field(name="Queue",     value=f"{player.queue.qsize()} songs", inline=True)
        embed.add_field(name="Source",    value=song.source.capitalize(), inline=True)

        if song.thumbnail:
            embed.set_thumbnail(url=song.thumbnail)
        embed.set_footer(text=f"🎤 {song.artist}")
        return embed

    @staticmethod
    def added_to_queue(song: "Song", position: int) -> discord.Embed:
        embed = discord.Embed(
            title="➕ Added to Queue",
            description=f"**[{song.title}]({song.url})**",
            color=discord.Color.green()
        )
        embed.add_field(name="Duration", value=song.duration_str, inline=True)
        embed.add_field(name="Position", value=f"#{position}", inline=True)
        if song.thumbnail:
            embed.set_thumbnail(url=song.thumbnail)
        return embed

    @staticmethod
    def playlist_added(songs: list, name: str) -> discord.Embed:
        embed = discord.Embed(
            title="📋 Playlist Added",
            description=f"Queued **{len(songs)} songs** from `{name}`",
            color=discord.Color.green()
        )
        preview = "\n".join(f"• {s.title}" for s in songs[:5])
        if len(songs) > 5:
            preview += f"\n*...and {len(songs) - 5} more*"
        embed.add_field(name="Tracks", value=preview, inline=False)
        return embed

    @staticmethod
    def success(message: str) -> discord.Embed:
        return discord.Embed(description=f"✅ {message}", color=discord.Color.green())

    @staticmethod
    def error(message: str) -> discord.Embed:
        return discord.Embed(description=f"❌ {message}", color=discord.Color.red())

    @staticmethod
    def info(message: str) -> discord.Embed:
        return discord.Embed(description=f"ℹ️ {message}", color=discord.Color.blue())
