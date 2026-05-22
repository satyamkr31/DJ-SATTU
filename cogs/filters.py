"""
Filters Cog — Audio filters via FFmpeg: bass boost, nightcore, 8D, vaporwave, EQ
"""

import discord
from discord.ext import commands
from discord import app_commands
from utils.embeds import MusicEmbed

# ── FFmpeg filter chains ───────────────────────────────────────────────────────
FILTERS = {
    "bassboost":  "bass=g=20,dynaudnorm=f=200",
    "nightcore":  "aresample=48000,asetrate=48000*1.25",
    "vaporwave":  "aresample=48000,asetrate=48000*0.8",
    "8d":         "apulsator=hz=0.125",
    "karaoke":    "stereotools=mlev=0.1",
    "echo":       "aecho=0.8:0.9:1000:0.3",
    "tremolo":    "tremolo",
    "vibrato":    "vibrato=f=6.5",
    "reverb":     "aecho=0.8:0.88:60:0.4",
    "loud":       "dynaudnorm=f=200",
    "earrape":    "acrusher=.1:1:64:0:log",  # capped for safety
    "clear":      None,  # remove all filters
}

# EQ presets (bass / mid / treble via equalizer)
EQ_PRESETS = {
    "gaming":   "equalizer=f=60:width_type=o:width=2:g=4,equalizer=f=2500:width_type=o:width=2:g=3",
    "edm":      "equalizer=f=60:width_type=o:width=2:g=8,equalizer=f=200:width_type=o:width=2:g=-2",
    "bass":     "equalizer=f=80:width_type=o:width=2:g=12",
    "vocal":    "equalizer=f=1000:width_type=o:width=2:g=5,equalizer=f=3000:width_type=o:width=2:g=3",
    "classical": "equalizer=f=100:width_type=o:width=2:g=-2,equalizer=f=4000:width_type=o:width=2:g=4",
    "flat":     None,
}


class Filters(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_filters: dict[int, str] = {}  # guild_id → filter name

    def get_player(self, guild_id):
        music_cog = self.bot.get_cog("Music")
        return music_cog.get_player(guild_id) if music_cog else None

    async def _restart_with_filter(self, guild: discord.Guild, filter_chain: str | None):
        """Restart current song with a new FFmpeg filter"""
        vc = guild.voice_client
        player = self.get_player(guild.id)
        if not vc or not player or not player.current:
            return False

        # Build FFmpeg options with filter
        options = "-vn"
        if filter_chain:
            options += f" -af \"{filter_chain}\""

        ffmpeg_opts = {
            "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            "options": options,
        }

        vc.stop()
        import asyncio
        await asyncio.sleep(0.3)

        source = discord.FFmpegPCMAudio(player.current.stream_url, **ffmpeg_opts)
        source = discord.PCMVolumeTransformer(source, volume=player.volume)

        def after(error):
            if error:
                return
            music_cog = self.bot.get_cog("Music")
            if music_cog:
                import asyncio
                asyncio.run_coroutine_threadsafe(
                    music_cog._play_next(guild), self.bot.loop
                )

        vc.play(source, after=after)
        return True

    # ── /filter ────────────────────────────────────────────────────────────────
    @app_commands.command(name="filter", description="Apply an audio filter")
    @app_commands.choices(name=[
        app_commands.Choice(name=k.capitalize(), value=k) for k in FILTERS
    ])
    async def apply_filter(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer()

        if not interaction.guild.voice_client:
            return await interaction.followup.send(
                embed=MusicEmbed.error("Bot is not in a voice channel."), ephemeral=True
            )

        filter_chain = FILTERS.get(name)
        success = await self._restart_with_filter(interaction.guild, filter_chain)

        if success:
            self.active_filters[interaction.guild_id] = name if name != "clear" else "none"
            icon = "✨" if name != "clear" else "🔄"
            label = name.capitalize() if name != "clear" else "Filters cleared"
            await interaction.followup.send(
                embed=MusicEmbed.success(f"{icon} Filter applied: **{label}**")
            )
        else:
            await interaction.followup.send(
                embed=MusicEmbed.error("Nothing is playing. Start a song first."), ephemeral=True
            )

    # ── /eq ────────────────────────────────────────────────────────────────────
    @app_commands.command(name="eq", description="Apply an equalizer preset")
    @app_commands.choices(preset=[
        app_commands.Choice(name=k.capitalize(), value=k) for k in EQ_PRESETS
    ])
    async def eq(self, interaction: discord.Interaction, preset: str):
        await interaction.response.defer()

        filter_chain = EQ_PRESETS.get(preset)
        success = await self._restart_with_filter(interaction.guild, filter_chain)

        if success:
            await interaction.followup.send(
                embed=MusicEmbed.success(f"🎛️ EQ preset: **{preset.capitalize()}**")
            )
        else:
            await interaction.followup.send(
                embed=MusicEmbed.error("Nothing is playing."), ephemeral=True
            )

    # ── /filters list ──────────────────────────────────────────────────────────
    @app_commands.command(name="filters", description="List all available filters")
    async def filters_list(self, interaction: discord.Interaction):
        active = self.active_filters.get(interaction.guild_id, "none")

        filter_text = "\n".join(
            f"{'→ ' if k == active else '  '}`{k}` — {_describe_filter(k)}"
            for k in FILTERS if k != "clear"
        )
        eq_text = "\n".join(
            f"  `{k}` — {_describe_eq(k)}"
            for k in EQ_PRESETS if k != "flat"
        )

        embed = discord.Embed(title="🎚️ Available Filters", color=discord.Color.teal())
        embed.add_field(name="Audio Effects", value=filter_text, inline=False)
        embed.add_field(name="EQ Presets", value=eq_text, inline=False)
        embed.set_footer(text=f"Active filter: {active} | Use /filter or /eq to apply")
        await interaction.response.send_message(embed=embed)


def _describe_filter(name: str) -> str:
    descriptions = {
        "bassboost": "Boost low frequencies",
        "nightcore": "Speed up + raise pitch",
        "vaporwave": "Slow down + lower pitch",
        "8d":        "Spatial 3D panning effect",
        "karaoke":   "Remove vocals",
        "echo":      "Add echo/delay",
        "tremolo":   "Volume tremolo effect",
        "vibrato":   "Pitch vibrato effect",
        "reverb":    "Add reverb/room sound",
        "loud":      "Normalize to loud",
        "earrape":   "Extreme distortion",
    }
    return descriptions.get(name, "")


def _describe_eq(name: str) -> str:
    descriptions = {
        "gaming":    "Boosted mids + highs",
        "edm":       "Heavy bass + sub",
        "bass":      "Maximum bass",
        "vocal":     "Boosted mids for vocals",
        "classical": "Balanced, bright highs",
    }
    return descriptions.get(name, "")


async def setup(bot):
    await bot.add_cog(Filters(bot))
