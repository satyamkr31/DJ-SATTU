"""
Player utilities — Song dataclass and MusicPlayer state manager
"""

import asyncio
from dataclasses import dataclass, field
from typing import Optional
import discord


@dataclass
class Song:
    """Represents a single track"""
    title: str
    url: str
    stream_url: str
    duration: int          # seconds
    thumbnail: str
    requester: discord.Member
    artist: str = "Unknown"
    source: str = "youtube"

    @property
    def duration_str(self) -> str:
        if not self.duration:
            return "LIVE"
        mins, secs = divmod(self.duration, 60)
        hours, mins = divmod(mins, 60)
        if hours:
            return f"{hours}:{mins:02d}:{secs:02d}"
        return f"{mins}:{secs:02d}"

    @classmethod
    def from_ytdl(cls, data: dict, requester) -> "Song":
        """Build a Song from a yt-dlp info dict"""
        # Prefer audio-only formats, fall back to best available
        stream_url = ""
        formats = data.get("formats", [])
        if formats:
            # Try audio-only first (opus/webm preferred for Discord)
            for fmt in reversed(formats):
                if fmt.get("acodec") not in (None, "none") and fmt.get("vcodec") in (None, "none", "") and fmt.get("url"):
                    stream_url = fmt["url"]
                    break
            # Fall back to any format with audio
            if not stream_url:
                for fmt in reversed(formats):
                    if fmt.get("acodec") not in (None, "none") and fmt.get("url"):
                        stream_url = fmt["url"]
                        break
        # Last resort: top-level url (flat playlist entries use this)
        if not stream_url:
            stream_url = data.get("url", "")

        # Canonical page URL — used to re-fetch a fresh stream URL later
        webpage_url = data.get("webpage_url") or data.get("original_url") or data.get("url", "")

        artist = (
            data.get("artist")
            or data.get("uploader")
            or data.get("channel")
            or "Unknown"
        )

        return cls(
            title=data.get("title", "Unknown Title"),
            url=webpage_url,
            stream_url=stream_url,
            duration=data.get("duration") or 0,
            thumbnail=data.get("thumbnail", ""),
            requester=requester,
            artist=artist,
            source=data.get("extractor_key", "youtube").lower(),
        )

    def to_dict(self) -> dict:
        """Serialize for database storage"""
        return {
            "title": self.title,
            "url": self.url,
            "duration": self.duration,
            "thumbnail": self.thumbnail,
            "artist": self.artist,
            "source": self.source,
        }


class MusicPlayer:
    """Per-guild music state"""

    def __init__(self, guild_id: int):
        self.guild_id = guild_id
        self.queue: asyncio.Queue = asyncio.Queue()
        self.current: Optional[Song] = None
        self.history: list[Song] = []
        self.volume: float = 0.5        # 0.0 – 2.0
        self.loop_mode: str = "off"     # "off" | "song" | "queue"
        self.autoplay: bool = False
        self.always_on: bool = False    # 24/7 mode
        self.text_channel: Optional[discord.TextChannel] = None

    def reset(self):
        self.queue = asyncio.Queue()
        self.current = None
        self.loop_mode = "off"
        self.autoplay = False
