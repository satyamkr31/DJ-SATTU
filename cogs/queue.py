"""
Queue Cog — Full queue management: view, remove, move, jump, clear
"""

import discord
from discord.ext import commands
from discord import app_commands
from utils.embeds import MusicEmbed


class Queue(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_player(self, guild_id):
        music_cog = self.bot.get_cog("Music")
        return music_cog.get_player(guild_id) if music_cog else None

    # ── /queue ─────────────────────────────────────────────────────────────────
    @app_commands.command(name="queue", description="Show the current queue")
    @app_commands.describe(page="Page number")
    async def queue(self, interaction: discord.Interaction, page: int = 1):
        player = self.get_player(interaction.guild_id)
        if not player:
            return await interaction.response.send_message(
                embed=MusicEmbed.error("No active player."), ephemeral=True
            )

        items = list(player.queue._queue)
        if not items and not player.current:
            return await interaction.response.send_message(
                embed=MusicEmbed.error("The queue is empty!"), ephemeral=True
            )

        per_page = 10
        pages = max(1, (len(items) + per_page - 1) // per_page)
        page = max(1, min(page, pages))
        start = (page - 1) * per_page
        chunk = items[start:start + per_page]

        embed = discord.Embed(
            title="🎵 Music Queue",
            color=discord.Color.purple()
        )

        if player.current:
            embed.add_field(
                name="▶️ Now Playing",
                value=f"[{player.current.title}]({player.current.url}) — {player.current.duration_str}",
                inline=False
            )

        if chunk:
            queue_text = "\n".join(
                f"`{start + i + 1}.` [{s.title}]({s.url}) — {s.duration_str} | {s.requester.mention}"
                for i, s in enumerate(chunk)
            )
            embed.add_field(name=f"📋 Up Next (Page {page}/{pages})", value=queue_text, inline=False)

        embed.set_footer(text=f"{len(items)} songs in queue | Loop: {player.loop_mode} | Vol: {int(player.volume * 100)}%")
        await interaction.response.send_message(embed=embed)

    # ── /remove ────────────────────────────────────────────────────────────────
    @app_commands.command(name="remove", description="Remove a song from the queue")
    @app_commands.describe(position="Position in queue (1-based)")
    async def remove(self, interaction: discord.Interaction, position: int):
        player = self.get_player(interaction.guild_id)
        items = list(player.queue._queue)

        if not 1 <= position <= len(items):
            return await interaction.response.send_message(
                embed=MusicEmbed.error(f"Invalid position. Queue has {len(items)} songs."),
                ephemeral=True
            )

        removed = items.pop(position - 1)
        player.queue._queue.clear()
        player.queue._queue.extend(items)

        await interaction.response.send_message(
            embed=MusicEmbed.success(f"🗑️ Removed: **{removed.title}**")
        )

    # ── /move ──────────────────────────────────────────────────────────────────
    @app_commands.command(name="move", description="Move a song to a new position")
    @app_commands.describe(from_pos="Current position", to_pos="New position")
    async def move(self, interaction: discord.Interaction, from_pos: int, to_pos: int):
        player = self.get_player(interaction.guild_id)
        items = list(player.queue._queue)

        if not (1 <= from_pos <= len(items) and 1 <= to_pos <= len(items)):
            return await interaction.response.send_message(
                embed=MusicEmbed.error("Invalid position(s)."), ephemeral=True
            )

        song = items.pop(from_pos - 1)
        items.insert(to_pos - 1, song)
        player.queue._queue.clear()
        player.queue._queue.extend(items)

        await interaction.response.send_message(
            embed=MusicEmbed.success(f"↕️ Moved **{song.title}** to position **{to_pos}**")
        )

    # ── /jump ──────────────────────────────────────────────────────────────────
    @app_commands.command(name="jump", description="Jump to a specific song in queue")
    @app_commands.describe(position="Position to jump to")
    async def jump(self, interaction: discord.Interaction, position: int):
        player = self.get_player(interaction.guild_id)
        items = list(player.queue._queue)

        if not 1 <= position <= len(items):
            return await interaction.response.send_message(
                embed=MusicEmbed.error("Invalid position."), ephemeral=True
            )

        # Remove everything before the target
        items = items[position - 1:]
        player.queue._queue.clear()
        player.queue._queue.extend(items)

        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.stop()  # triggers after_play → _play_next

        await interaction.response.send_message(
            embed=MusicEmbed.success(f"⏩ Jumped to position **{position}**: **{items[0].title}**")
        )

    # ── /clear ─────────────────────────────────────────────────────────────────
    @app_commands.command(name="clear", description="Clear the entire queue")
    async def clear(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild_id)
        size = player.queue.qsize()
        player.queue._queue.clear()
        await interaction.response.send_message(
            embed=MusicEmbed.success(f"🧹 Cleared **{size}** songs from the queue.")
        )

    # ── /history ───────────────────────────────────────────────────────────────
    @app_commands.command(name="history", description="Show recently played songs")
    async def history(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild_id)
        if not player or not player.history:
            return await interaction.response.send_message(
                embed=MusicEmbed.error("No play history yet."), ephemeral=True
            )

        recent = list(reversed(player.history[-10:]))
        embed = discord.Embed(title="📜 Recent History", color=discord.Color.blue())
        text = "\n".join(
            f"`{i + 1}.` [{s.title}]({s.url}) — {s.requester.mention}"
            for i, s in enumerate(recent)
        )
        embed.description = text
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Queue(bot))
