"""
Lyrics Cog — Fetch and display lyrics with syncedlyrics / lyricsgenius
"""

import discord
from discord.ext import commands
from discord import app_commands
import os
from utils.embeds import MusicEmbed
from utils.logger import setup_logger

logger = setup_logger()


class Lyrics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Optional: LyricsGenius API (https://genius.com/api-clients)
        genius_token = os.getenv("GENIUS_API_KEY")
        if genius_token:
            try:
                import lyricsgenius
                self.genius = lyricsgenius.Genius(genius_token, verbose=False)
            except ImportError:
                self.genius = None
        else:
            self.genius = None

    @app_commands.command(name="lyrics", description="Show lyrics for the current or any song")
    @app_commands.describe(song="Song name (leave blank for current song)")
    async def lyrics(self, interaction: discord.Interaction, song: str = None):
        await interaction.response.defer()

        if not song:
            music_cog = self.bot.get_cog("Music")
            player = music_cog.get_player(interaction.guild_id) if music_cog else None
            if not player or not player.current:
                return await interaction.followup.send(
                    embed=MusicEmbed.error("Nothing is playing! Provide a song name."),
                    ephemeral=True
                )
            song = player.current.title

        if not self.genius:
            # Fallback: link to Google search
            query = song.replace(" ", "+")
            embed = discord.Embed(
                title="🎤 Lyrics",
                description=(
                    f"Searching for: **{song}**\n\n"
                    f"[Search lyrics on Google](https://www.google.com/search?q={query}+lyrics)\n"
                    f"[Search on Genius](https://genius.com/search?q={query})\n\n"
                    f"*Tip: Add a `GENIUS_API_KEY` to your .env for in-Discord lyrics!*"
                ),
                color=discord.Color.yellow()
            )
            return await interaction.followup.send(embed=embed)

        try:
            result = self.genius.search_song(song)
            if not result:
                return await interaction.followup.send(
                    embed=MusicEmbed.error(f"No lyrics found for: **{song}**")
                )

            # Discord has 4096 char embed limit
            lyric_text = result.lyrics[:3800] + "..." if len(result.lyrics) > 3800 else result.lyrics

            embed = discord.Embed(
                title=f"🎤 {result.title} — {result.artist}",
                description=lyric_text,
                color=discord.Color.purple(),
                url=result.url
            )
            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Lyrics error: {e}")
            await interaction.followup.send(
                embed=MusicEmbed.error("Failed to fetch lyrics. Try again later.")
            )


async def setup(bot):
    await bot.add_cog(Lyrics(bot))
