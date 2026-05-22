"""
Social Cog — Leaderboards, server stats, listening analytics, song reactions
"""

import discord
from discord.ext import commands
from discord import app_commands
from utils.embeds import MusicEmbed


class Social(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ── /leaderboard ───────────────────────────────────────────────────────────
    @app_commands.command(name="leaderboard", description="Show top music listeners in this server")
    @app_commands.choices(type=[
        app_commands.Choice(name="Top Listeners", value="listeners"),
        app_commands.Choice(name="Top Songs", value="songs"),
        app_commands.Choice(name="Top Artists", value="artists"),
    ])
    async def leaderboard(self, interaction: discord.Interaction, type: str = "listeners"):
        await interaction.response.defer()
        data = await self.bot.db.get_leaderboard(interaction.guild_id, type)

        embed = discord.Embed(
            title=f"🏆 Music Leaderboard — {type.capitalize()}",
            color=discord.Color.gold()
        )

        if not data:
            embed.description = "No data yet! Start listening to build the leaderboard."
            return await interaction.followup.send(embed=embed)

        medals = ["🥇", "🥈", "🥉"] + ["🎵"] * 20

        if type == "listeners":
            lines = []
            for i, entry in enumerate(data[:10]):
                user = interaction.guild.get_member(entry["user_id"])
                name = user.display_name if user else f"User {entry['user_id']}"
                lines.append(f"{medals[i]} **{name}** — {entry['play_count']} songs played")
            embed.description = "\n".join(lines)

        elif type == "songs":
            lines = [
                f"{medals[i]} **{e['title']}** — played {e['count']}x"
                for i, e in enumerate(data[:10])
            ]
            embed.description = "\n".join(lines)

        elif type == "artists":
            lines = [
                f"{medals[i]} **{e['artist']}** — {e['count']} plays"
                for i, e in enumerate(data[:10])
            ]
            embed.description = "\n".join(lines)

        await interaction.followup.send(embed=embed)

    # ── /stats ─────────────────────────────────────────────────────────────────
    @app_commands.command(name="stats", description="View your personal listening stats")
    async def stats(self, interaction: discord.Interaction):
        await interaction.response.defer()
        data = await self.bot.db.get_user_stats(interaction.user.id, interaction.guild_id)

        embed = discord.Embed(
            title=f"📊 Stats for {interaction.user.display_name}",
            color=discord.Color.blue()
        )

        embed.add_field(name="🎵 Songs Played", value=str(data.get("total_plays", 0)), inline=True)
        embed.add_field(name="⏱️ Time Listened", value=data.get("total_time", "0m"), inline=True)
        embed.add_field(name="🎤 Top Artist", value=data.get("top_artist", "N/A"), inline=True)
        embed.add_field(name="🔥 Fav Song", value=data.get("top_song", "N/A"), inline=True)
        embed.add_field(name="🎭 Top Genre", value=data.get("top_genre", "N/A"), inline=True)
        embed.add_field(name="📅 Listening Streak", value=f"{data.get('streak', 0)} days", inline=True)

        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        await interaction.followup.send(embed=embed)

    # ── /serverstats ───────────────────────────────────────────────────────────
    @app_commands.command(name="serverstats", description="View server-wide music analytics")
    async def serverstats(self, interaction: discord.Interaction):
        await interaction.response.defer()
        data = await self.bot.db.get_server_stats(interaction.guild_id)

        embed = discord.Embed(
            title=f"📈 {interaction.guild.name} — Music Analytics",
            color=discord.Color.purple()
        )

        embed.add_field(name="🎵 Total Songs Played", value=str(data.get("total_plays", 0)), inline=True)
        embed.add_field(name="👥 Active Listeners", value=str(data.get("unique_listeners", 0)), inline=True)
        embed.add_field(name="🔥 Most Played Song", value=data.get("top_song", "N/A"), inline=True)
        embed.add_field(name="🎤 Top Artist", value=data.get("top_artist", "N/A"), inline=True)
        embed.add_field(name="⏰ Peak Hour", value=data.get("peak_hour", "N/A"), inline=True)
        embed.add_field(name="🎭 Most Played Genre", value=data.get("top_genre", "N/A"), inline=True)

        if interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)

        await interaction.followup.send(embed=embed)

    # ── /react ─────────────────────────────────────────────────────────────────
    @app_commands.command(name="react", description="React to the current song")
    @app_commands.choices(reaction=[
        app_commands.Choice(name="🔥 Fire", value="fire"),
        app_commands.Choice(name="❌ Dislike", value="dislike"),
        app_commands.Choice(name="🎧 Replay", value="replay"),
        app_commands.Choice(name="⭐ Favorite", value="favorite"),
    ])
    async def react(self, interaction: discord.Interaction, reaction: str):
        music_cog = self.bot.get_cog("Music")
        if not music_cog:
            return
        player = music_cog.get_player(interaction.guild_id)
        if not player or not player.current:
            return await interaction.response.send_message(
                embed=MusicEmbed.error("Nothing is playing!"), ephemeral=True
            )

        icons = {"fire": "🔥", "dislike": "❌", "replay": "🎧", "favorite": "⭐"}
        labels = {"fire": "Fire!", "dislike": "Noted, will skip sooner", "replay": "Added to your favorites", "favorite": "Added to favorites!"}

        await self.bot.db.log_reaction(
            interaction.user.id, interaction.guild_id, player.current, reaction
        )

        await interaction.response.send_message(
            embed=MusicEmbed.success(f"{icons[reaction]} {labels[reaction]} — **{player.current.title}**"),
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Social(bot))
