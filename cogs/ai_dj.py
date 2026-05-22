"""
AI DJ Cog — Personalized recommendations, mood detection, smart autoplay
Uses OpenAI for NLP + music intelligence
"""

import discord
from discord.ext import commands
from discord import app_commands
import openai
import os
import json
from utils.embeds import MusicEmbed
from utils.logger import setup_logger

logger = setup_logger()

# Mood → search query mappings
MOOD_QUERIES = {
    "happy":    ["happy pop hits", "feel good songs", "upbeat playlist"],
    "sad":      ["sad songs", "melancholic music", "heartbreak songs"],
    "chill":    ["lofi hip hop", "chill vibes", "relaxing music"],
    "workout":  ["gym motivation", "workout playlist", "pump up songs"],
    "study":    ["study music", "focus playlist", "lo-fi study beats"],
    "party":    ["party hits", "dance music", "club bangers"],
    "sleep":    ["sleep music", "ambient relaxation", "calm piano"],
    "gaming":   ["gaming music", "epic gaming playlist", "intense gaming"],
    "romantic": ["romantic songs", "love songs", "date night music"],
    "angry":    ["hard rock", "metal playlist", "rage music"],
}

# Time-based auto mood
def get_time_mood() -> str:
    from datetime import datetime
    hour = datetime.now().hour
    if 0 <= hour < 6:   return "sleep"
    if 6 <= hour < 10:  return "chill"
    if 10 <= hour < 14: return "happy"
    if 14 <= hour < 18: return "study"
    if 18 <= hour < 21: return "chill"
    return "happy"


class AIDJ(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            self.openai_client = openai.AsyncOpenAI(api_key=openai_key)
        else:
            self.openai_client = None
            logger.warning("OPENAI_API_KEY not set — AI features limited")

    def get_player(self, guild_id):
        music_cog = self.bot.get_cog("Music")
        return music_cog.get_player(guild_id) if music_cog else None

    # ── /recommend ─────────────────────────────────────────────────────────────
    @app_commands.command(name="recommend", description="Get AI-powered song recommendations")
    async def recommend(self, interaction: discord.Interaction):
        await interaction.response.defer()

        # Pull user history from DB
        history = await self.bot.db.get_user_history(interaction.user.id, limit=20)

        if not history:
            await interaction.followup.send(
                embed=MusicEmbed.info(
                    "🎵 No listening history yet!\nPlay some songs first, then I'll learn your taste."
                )
            )
            return

        if self.openai_client:
            recs = await self._ai_recommendations(history, interaction.user)
        else:
            recs = await self._simple_recommendations(history)

        embed = discord.Embed(
            title=f"🤖 AI Recommendations for {interaction.user.display_name}",
            description="\n".join(f"• {r}" for r in recs),
            color=discord.Color.purple()
        )
        embed.set_footer(text="Use /play <song name> to play any of these!")
        await interaction.followup.send(embed=embed)

    async def _ai_recommendations(self, history: list, user) -> list[str]:
        """Use GPT to generate personalized recommendations"""
        titles = [h["title"] for h in history[:15]]
        prompt = f"""The user has been listening to these songs: {', '.join(titles)}

Based on this listening history, recommend exactly 8 new songs they would enjoy.
Respond with ONLY a JSON array of strings like: ["Song - Artist", "Song2 - Artist2", ...]
No explanation, just the JSON array."""

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.8
            )
            text = response.choices[0].message.content.strip()
            recs = json.loads(text)
            return recs[:8]
        except Exception as e:
            logger.error(f"OpenAI recommendation error: {e}")
            return await self._simple_recommendations(history)

    async def _simple_recommendations(self, history: list) -> list[str]:
        """Fallback: suggest based on most played artists"""
        from collections import Counter
        artists = [h.get("artist", "Unknown") for h in history]
        top_artists = [a for a, _ in Counter(artists).most_common(3)]
        suggestions = []
        for artist in top_artists:
            suggestions.append(f"More by {artist}")
        suggestions += ["Top 50 Global", "Trending Music 2024", "Discover Weekly Mix"]
        return suggestions[:8]

    # ── /mood ──────────────────────────────────────────────────────────────────
    @app_commands.command(name="mood", description="Play music matching a mood")
    @app_commands.choices(mood=[
        app_commands.Choice(name=m.capitalize(), value=m)
        for m in MOOD_QUERIES
    ])
    async def mood(self, interaction: discord.Interaction, mood: str):
        await interaction.response.defer()

        import random
        query = random.choice(MOOD_QUERIES[mood])

        music_cog = self.bot.get_cog("Music")
        if not music_cog:
            return

        # Ensure in VC
        if not interaction.user.voice:
            await interaction.followup.send(
                embed=MusicEmbed.error("You must be in a voice channel!"), ephemeral=True
            )
            return

        if not interaction.guild.voice_client:
            await interaction.user.voice.channel.connect()

        songs = await music_cog._search_youtube(query, interaction.user, limit=10)
        player = self.get_player(interaction.guild_id)

        for song in songs:
            await player.queue.put(song)

        embed = discord.Embed(
            title=f"🎭 Mood: {mood.capitalize()}",
            description=f"Queued **{len(songs)} songs** for your `{mood}` mood!\n*(Query: {query})*",
            color=discord.Color.purple()
        )
        await interaction.followup.send(embed=embed)

        if not interaction.guild.voice_client.is_playing():
            await music_cog._play_next(interaction.guild)

    # ── /autodj ────────────────────────────────────────────────────────────────
    @app_commands.command(name="autodj", description="Let the AI DJ take control!")
    async def autodj(self, interaction: discord.Interaction):
        await interaction.response.defer()

        player = self.get_player(interaction.guild_id)
        if not player:
            return

        player.autoplay = True
        mood = get_time_mood()

        embed = discord.Embed(
            title="🤖 AI DJ Activated!",
            description=(
                f"I've taken control of the queue!\n\n"
                f"**Current vibe:** `{mood.capitalize()}`\n"
                f"I'll keep the music flowing and adapt to your server's energy.\n\n"
                f"Use `/autodj` again to stop."
            ),
            color=discord.Color.gold()
        )

        await interaction.followup.send(embed=embed)

        # Seed initial songs based on time mood
        import random
        music_cog = self.bot.get_cog("Music")
        if music_cog and interaction.user.voice:
            if not interaction.guild.voice_client:
                await interaction.user.voice.channel.connect()

            query = random.choice(MOOD_QUERIES[mood])
            songs = await music_cog._search_youtube(query, self.bot.user, limit=10)
            for song in songs:
                await player.queue.put(song)

            if not interaction.guild.voice_client.is_playing():
                await music_cog._play_next(interaction.guild)

    # ── /ask ───────────────────────────────────────────────────────────────────
    @app_commands.command(name="ask", description="Ask the AI DJ anything (natural language)")
    @app_commands.describe(request="e.g. 'play something relaxing', 'skip to faster songs'")
    async def ask(self, interaction: discord.Interaction, request: str):
        await interaction.response.defer()

        if not self.openai_client:
            await interaction.followup.send(
                embed=MusicEmbed.error("OpenAI API key not configured for natural language commands.")
            )
            return

        prompt = f"""You are a Discord music bot assistant. The user said: "{request}"

Determine what music action they want and respond with a JSON object:
{{
  "action": "play" | "skip" | "stop" | "mood" | "recommend",
  "query": "search query if action is play or mood",
  "mood": "mood name if applicable"
}}

Only output the JSON, nothing else."""

        try:
            resp = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100
            )
            data = json.loads(resp.choices[0].message.content.strip())
            action = data.get("action")

            if action == "play" and data.get("query"):
                music_cog = self.bot.get_cog("Music")
                if music_cog and interaction.user.voice:
                    if not interaction.guild.voice_client:
                        await interaction.user.voice.channel.connect()
                    songs = await music_cog._search_youtube(data["query"], interaction.user, limit=5)
                    player = self.get_player(interaction.guild_id)
                    for song in songs:
                        await player.queue.put(song)
                    if not interaction.guild.voice_client.is_playing():
                        await music_cog._play_next(interaction.guild)
                    await interaction.followup.send(
                        embed=MusicEmbed.success(f"🤖 Got it! Queuing: **{data['query']}**")
                    )
                    return

            elif action == "skip":
                vc = interaction.guild.voice_client
                if vc and vc.is_playing():
                    vc.stop()
                await interaction.followup.send(embed=MusicEmbed.success("⏭️ Skipped!"))
                return

            elif action == "stop":
                vc = interaction.guild.voice_client
                if vc:
                    vc.stop()
                    await vc.disconnect()
                await interaction.followup.send(embed=MusicEmbed.success("⏹️ Stopped!"))
                return

        except Exception as e:
            logger.error(f"AI ask error: {e}")

        await interaction.followup.send(
            embed=MusicEmbed.error("I couldn't understand that. Try `/play`, `/skip`, or `/mood`.")
        )

    # ── Autoplay hook (called by Music cog) ───────────────────────────────────
    async def autoplay_next(self, guild: discord.Guild):
        """Called when queue ends and autoplay is on"""
        player = self.get_player(guild.id)
        if not player or not player.autoplay:
            return

        music_cog = self.bot.get_cog("Music")
        if not music_cog:
            return

        # Pick next song based on history
        if player.history:
            last = player.history[-1]
            query = f"{last.title} similar songs"
        else:
            mood = get_time_mood()
            import random
            query = random.choice(MOOD_QUERIES[mood])

        songs = await music_cog._search_youtube(query, guild.me, limit=5)
        for song in songs:
            await player.queue.put(song)

        await music_cog._play_next(guild)
        logger.info(f"Autoplay: queued {len(songs)} songs in {guild.name}")


async def setup(bot):
    await bot.add_cog(AIDJ(bot))
