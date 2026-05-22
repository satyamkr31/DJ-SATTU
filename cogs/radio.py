"""
Radio Cog — Internet radio stations
"""

import discord
from discord.ext import commands
from discord import app_commands
from utils.embeds import MusicEmbed

RADIO_STATIONS = {
    "lofi":       ("Lofi Hip Hop Radio", "https://play.streamafrica.net/lofiradio"),
    "jazz":       ("Jazz 24", "http://live.wostreaming.net/direct/ppm-jazz24aac-ibc1"),
    "classical":  ("Classical Radio", "https://live.musopen.org:8085/streamvbr0"),
    "edm":        ("EDM Radio", "https://streams.ilovemusic.de/iloveradio17.mp3"),
    "chillhop":   ("Chillhop Radio", "https://streams.ilovemusic.de/iloveradio2.mp3"),
    "anime":      ("Anime Radio", "https://stream.r-a-d.io/main.mp3"),
    "country":    ("Country Hits Radio", "https://streams.ilovemusic.de/iloveradio12.mp3"),
    "80s":        ("80s Radio", "https://streams.ilovemusic.de/iloveradio6.mp3"),
    "90s":        ("90s Radio", "https://streams.ilovemusic.de/iloveradio7.mp3"),
}


class Radio(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="radio", description="Play an internet radio station")
    @app_commands.choices(station=[
        app_commands.Choice(name=v[0], value=k)
        for k, v in RADIO_STATIONS.items()
    ])
    async def radio(self, interaction: discord.Interaction, station: str):
        await interaction.response.defer()

        if not interaction.user.voice:
            return await interaction.followup.send(
                embed=MusicEmbed.error("You must be in a voice channel!"), ephemeral=True
            )

        vc = interaction.guild.voice_client
        if not vc:
            vc = await interaction.user.voice.channel.connect()

        name, url = RADIO_STATIONS[station]

        if vc.is_playing():
            vc.stop()

        import asyncio
        await asyncio.sleep(0.3)

        source = discord.FFmpegPCMAudio(
            url,
            before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
        )
        vc.play(source)

        embed = discord.Embed(
            title="📻 Radio — Now Streaming",
            description=f"**{name}**\nStation: `{station}`",
            color=discord.Color.red()
        )
        embed.set_footer(text="Use /stop to end radio playback")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="radiolist", description="Show all available radio stations")
    async def radiolist(self, interaction: discord.Interaction):
        embed = discord.Embed(title="📻 Available Radio Stations", color=discord.Color.red())
        text = "\n".join(
            f"• `/radio {k}` — **{v[0]}**"
            for k, v in RADIO_STATIONS.items()
        )
        embed.description = text
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Radio(bot))
