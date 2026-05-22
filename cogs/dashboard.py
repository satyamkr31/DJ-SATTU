"""
Dashboard Cog — Web dashboard bridge (launches FastAPI server)
"""

import discord
from discord.ext import commands
from discord import app_commands
from utils.embeds import MusicEmbed
import os


class Dashboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="dashboard", description="Get the link to the web dashboard")
    async def dashboard(self, interaction: discord.Interaction):
        port = os.getenv("DASHBOARD_PORT", "8080")
        host = os.getenv("DASHBOARD_HOST", "localhost")
        url = f"http://{host}:{port}"

        embed = discord.Embed(
            title="🌐 Web Dashboard",
            description=(
                f"**Control your music from the browser!**\n\n"
                f"🔗 [Open Dashboard]({url})\n\n"
                f"**Features:**\n"
                f"• Live queue management\n"
                f"• Playlist editing\n"
                f"• Listening analytics\n"
                f"• Server settings\n"
                f"• Premium management\n\n"
                f"*Start the dashboard with:* `python web/app.py`"
            ),
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Dashboard(bot))
