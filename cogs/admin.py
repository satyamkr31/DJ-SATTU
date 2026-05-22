"""
Admin Cog — DJ roles, content filters, moderation
"""

import discord
from discord.ext import commands
from discord import app_commands
from utils.embeds import MusicEmbed


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dj_roles: dict[int, int] = {}        # guild_id → role_id
        self.blocked_words: dict[int, list] = {}   # guild_id → [words]

    def is_dj_or_admin(self, interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator:
            return True
        dj_role_id = self.dj_roles.get(interaction.guild_id)
        if dj_role_id:
            return any(r.id == dj_role_id for r in interaction.user.roles)
        return False

    @app_commands.command(name="djrole", description="Set the DJ role (admins only)")
    @app_commands.describe(role="The role to set as DJ")
    async def djrole(self, interaction: discord.Interaction, role: discord.Role):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                embed=MusicEmbed.error("Administrator permission required."), ephemeral=True
            )
        self.dj_roles[interaction.guild_id] = role.id
        await self.bot.db.set_setting(interaction.guild_id, "dj_role", str(role.id))
        await interaction.response.send_message(
            embed=MusicEmbed.success(f"🎧 DJ role set to **{role.name}**")
        )

    @app_commands.command(name="block", description="Block a word/artist from being queued")
    @app_commands.describe(word="Word or artist name to block")
    async def block(self, interaction: discord.Interaction, word: str):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message(
                embed=MusicEmbed.error("Manage Server permission required."), ephemeral=True
            )
        guild_id = interaction.guild_id
        if guild_id not in self.blocked_words:
            self.blocked_words[guild_id] = []
        self.blocked_words[guild_id].append(word.lower())
        await interaction.response.send_message(
            embed=MusicEmbed.success(f"🚫 Blocked: **{word}**")
        )

    @app_commands.command(name="setup", description="Setup a dedicated music channel")
    async def setup_channel(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                embed=MusicEmbed.error("Administrator permission required."), ephemeral=True
            )

        # Create dedicated music channel
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(
                send_messages=True, read_messages=True
            )
        }
        channel = await interaction.guild.create_text_channel(
            "🎵-music", overwrites=overwrites
        )

        embed = discord.Embed(
            title="🎵 Music Bot Ready!",
            description=(
                "**Type song names or URLs here to play music!**\n\n"
                "**Commands:**\n"
                "`/play <song>` — Play a song\n"
                "`/queue` — View queue\n"
                "`/skip` — Skip song\n"
                "`/stop` — Stop music\n"
                "`/mood <mood>` — Play by mood\n"
                "`/recommend` — AI recommendations\n"
                "`/autodj` — Let AI DJ take control\n"
                "`/lyrics` — Show lyrics\n"
                "`/filter` — Audio filters\n"
                "`/radio` — Internet radio\n"
                "`/playlist` — Manage playlists\n"
                "`/leaderboard` — Music leaderboard\n"
                "`/stats` — Your listening stats"
            ),
            color=discord.Color.purple()
        )

        await channel.send(embed=embed)
        await self.bot.db.set_setting(interaction.guild_id, "music_channel", str(channel.id))

        await interaction.response.send_message(
            embed=MusicEmbed.success(f"✅ Music channel created: {channel.mention}"),
            ephemeral=True
        )

    @app_commands.command(name="help", description="Show all bot commands")
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎵 Music Bot — Command Reference",
            color=discord.Color.purple()
        )

        sections = {
            "▶️ Playback": ["/play", "/pause", "/resume", "/skip", "/stop", "/volume", "/nowplaying", "/loop", "/shuffle", "/247"],
            "📋 Queue":    ["/queue", "/remove", "/move", "/jump", "/clear", "/history"],
            "🤖 AI DJ":    ["/recommend", "/mood", "/autodj", "/ask", "/autoplay"],
            "🎚️ Filters":  ["/filter", "/eq", "/filters"],
            "📂 Playlists":["/playlist create", "/playlist add", "/playlist play", "/playlist show", "/playlist list"],
            "🎤 Lyrics":   ["/lyrics"],
            "📻 Radio":    ["/radio", "/radiolist"],
            "🏆 Social":   ["/leaderboard", "/stats", "/serverstats", "/react"],
            "⚙️ Admin":    ["/setup", "/djrole", "/block"],
        }

        for section, cmds in sections.items():
            embed.add_field(
                name=section,
                value=" • ".join(f"`{c}`" for c in cmds),
                inline=False
            )

        embed.set_footer(text="Tip: Use /ask for natural language commands! e.g. /ask play something relaxing")
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Admin(bot))
