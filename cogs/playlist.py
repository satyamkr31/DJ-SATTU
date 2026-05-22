"""
Playlist Cog — Personal & server playlists saved to DB
"""

import discord
from discord.ext import commands
from discord import app_commands
from utils.embeds import MusicEmbed


class Playlist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_player(self, guild_id):
        music_cog = self.bot.get_cog("Music")
        return music_cog.get_player(guild_id) if music_cog else None

    @app_commands.command(name="playlist", description="Manage your playlists")
    @app_commands.choices(action=[
        app_commands.Choice(name="Create", value="create"),
        app_commands.Choice(name="Add current song", value="add"),
        app_commands.Choice(name="Show", value="show"),
        app_commands.Choice(name="Play", value="play"),
        app_commands.Choice(name="Delete", value="delete"),
        app_commands.Choice(name="List all", value="list"),
    ])
    @app_commands.describe(action="Action to perform", name="Playlist name")
    async def playlist(self, interaction: discord.Interaction, action: str, name: str = None):
        await interaction.response.defer()
        db = self.bot.db

        if action == "list":
            playlists = await db.get_playlists(interaction.user.id)
            if not playlists:
                return await interaction.followup.send(
                    embed=MusicEmbed.info("You have no saved playlists. Create one with `/playlist create <name>`")
                )
            embed = discord.Embed(title="📂 Your Playlists", color=discord.Color.green())
            text = "\n".join(
                f"• **{p['name']}** — {p['song_count']} songs"
                for p in playlists
            )
            embed.description = text
            return await interaction.followup.send(embed=embed)

        if not name:
            return await interaction.followup.send(
                embed=MusicEmbed.error("Please provide a playlist name."), ephemeral=True
            )

        if action == "create":
            await db.create_playlist(interaction.user.id, name)
            await interaction.followup.send(
                embed=MusicEmbed.success(f"✅ Playlist **{name}** created!")
            )

        elif action == "add":
            player = self.get_player(interaction.guild_id)
            if not player or not player.current:
                return await interaction.followup.send(
                    embed=MusicEmbed.error("Nothing is playing!"), ephemeral=True
                )
            await db.add_to_playlist(interaction.user.id, name, player.current)
            await interaction.followup.send(
                embed=MusicEmbed.success(f"➕ Added **{player.current.title}** to **{name}**")
            )

        elif action == "show":
            songs = await db.get_playlist_songs(interaction.user.id, name)
            if not songs:
                return await interaction.followup.send(
                    embed=MusicEmbed.error(f"Playlist **{name}** is empty or doesn't exist.")
                )
            embed = discord.Embed(title=f"📋 Playlist: {name}", color=discord.Color.green())
            text = "\n".join(
                f"`{i+1}.` {s['title']} — {s.get('duration', '?')}"
                for i, s in enumerate(songs[:20])
            )
            embed.description = text
            await interaction.followup.send(embed=embed)

        elif action == "play":
            songs = await db.get_playlist_songs(interaction.user.id, name)
            if not songs:
                return await interaction.followup.send(
                    embed=MusicEmbed.error(f"Playlist **{name}** is empty.")
                )

            music_cog = self.bot.get_cog("Music")
            if not music_cog:
                return

            if not interaction.user.voice:
                return await interaction.followup.send(
                    embed=MusicEmbed.error("Join a voice channel first!"), ephemeral=True
                )

            if not interaction.guild.voice_client:
                await interaction.user.voice.channel.connect()

            from utils.player import Song
            player = self.get_player(interaction.guild_id)

            # Search and queue each song
            queued = 0
            for s in songs[:30]:
                found = await music_cog._search_youtube(s["title"], interaction.user, limit=1)
                for song in found:
                    await player.queue.put(song)
                    queued += 1

            await interaction.followup.send(
                embed=MusicEmbed.success(f"▶️ Playing playlist **{name}** — {queued} songs queued!")
            )

            if not interaction.guild.voice_client.is_playing():
                await music_cog._play_next(interaction.guild)

        elif action == "delete":
            await db.delete_playlist(interaction.user.id, name)
            await interaction.followup.send(
                embed=MusicEmbed.success(f"🗑️ Deleted playlist **{name}**")
            )


async def setup(bot):
    await bot.add_cog(Playlist(bot))
