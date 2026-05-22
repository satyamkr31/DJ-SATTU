# 🎵 Advanced Discord Music Bot

A full-featured Discord music bot with **AI DJ**, personalized recommendations, audio filters, playlists, lyrics, internet radio, leaderboards, and a web dashboard.

---

## ✨ Features

| Category | Features |
|---|---|
| **Playback** | YouTube, Spotify, SoundCloud, direct URLs, playlists |
| **AI DJ** | Smart recommendations, mood detection, natural language commands |
| **Filters** | Bass boost, nightcore, 8D, vaporwave, echo, karaoke + EQ presets |
| **Playlists** | Personal playlists, save/load/share |
| **Lyrics** | In-Discord lyrics via Genius API |
| **Radio** | 9 internet radio stations (Lofi, Jazz, Anime, EDM...) |
| **Social** | Leaderboards, listening stats, song reactions |
| **Dashboard** | Web UI at `localhost:8080` |
| **Queue** | Full management: remove, move, jump, shuffle, loop, history |

---

## 🚀 Quick Setup

### 1. Prerequisites

- Python 3.10+
- `ffmpeg` installed and in PATH

**Install ffmpeg:**
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows — download from https://ffmpeg.org/download.html
```

### 2. Install Dependencies

```bash
git clone <your-repo>
cd discord-music-bot
pip install -r requirements.txt
```

### 3. Create Discord Bot

1. Go to https://discord.com/developers/applications
2. Click **New Application** → name it
3. Go to **Bot** → click **Add Bot**
4. Under **Privileged Gateway Intents**, enable:
   - ✅ Server Members Intent
   - ✅ Message Content Intent
5. Copy your **Bot Token**
6. Go to **OAuth2 → URL Generator**:
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: `Connect`, `Speak`, `Send Messages`, `Embed Links`, `Read Message History`
7. Use the generated URL to invite the bot to your server

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your DISCORD_TOKEN
```

**Required:**
```
DISCORD_TOKEN=your_token_here
```

**Optional (unlock more features):**
```
SPOTIFY_CLIENT_ID=...     # Spotify URL support
SPOTIFY_CLIENT_SECRET=...
OPENAI_API_KEY=...         # /recommend, /ask, AI DJ
GENIUS_API_KEY=...         # In-Discord lyrics
```

### 5. Run the Bot

```bash
python bot.py
```

### 6. Run the Web Dashboard (optional)

```bash
python web/app.py
# Open http://localhost:8080
```

---

## 📋 Commands

### ▶️ Playback
| Command | Description |
|---|---|
| `/play <song>` | Play song, URL, or Spotify link |
| `/pause` / `/resume` | Pause or resume |
| `/skip` | Skip current song |
| `/stop` | Stop and disconnect |
| `/volume <0-200>` | Set volume |
| `/nowplaying` | Show current song |
| `/loop <off/song/queue>` | Set loop mode |
| `/shuffle` | Shuffle queue |
| `/autoplay` | Toggle AI autoplay |
| `/247` | Toggle 24/7 mode |

### 📋 Queue
| Command | Description |
|---|---|
| `/queue [page]` | View queue |
| `/remove <pos>` | Remove song |
| `/move <from> <to>` | Reorder queue |
| `/jump <pos>` | Jump to position |
| `/clear` | Clear queue |
| `/history` | Recently played |

### 🤖 AI DJ
| Command | Description |
|---|---|
| `/recommend` | AI-powered song recommendations |
| `/mood <mood>` | Play music for a mood |
| `/autodj` | Let AI take control |
| `/ask <request>` | Natural language (e.g. "play something chill") |

### 🎚️ Filters
| Command | Description |
|---|---|
| `/filter <name>` | Apply audio filter |
| `/eq <preset>` | Apply EQ preset |
| `/filters` | List all filters |

**Available filters:** `bassboost`, `nightcore`, `vaporwave`, `8d`, `karaoke`, `echo`, `tremolo`, `vibrato`, `reverb`, `clear`

**EQ presets:** `gaming`, `edm`, `bass`, `vocal`, `classical`

### 📂 Playlists
```
/playlist create <name>
/playlist add <name>         (adds current song)
/playlist play <name>
/playlist show <name>
/playlist list
/playlist delete <name>
```

### 🏆 Social
| Command | Description |
|---|---|
| `/leaderboard` | Top listeners / songs / artists |
| `/stats` | Your personal stats |
| `/serverstats` | Server-wide analytics |
| `/react <reaction>` | React to current song |

### ⚙️ Admin
| Command | Description |
|---|---|
| `/setup` | Create dedicated music channel |
| `/djrole <role>` | Set DJ role |
| `/block <word>` | Block a song/artist |

---

## 🔧 Architecture

```
discord-music-bot/
├── bot.py              # Main entry point
├── cogs/
│   ├── music.py        # Core playback (yt-dlp + FFmpeg)
│   ├── queue.py        # Queue management
│   ├── ai_dj.py        # AI recommendations & mood
│   ├── filters.py      # Audio filters & EQ
│   ├── playlist.py     # Playlist system
│   ├── lyrics.py       # Lyrics via Genius
│   ├── radio.py        # Internet radio
│   ├── social.py       # Leaderboards & stats
│   ├── admin.py        # Moderation
│   └── dashboard.py    # Web dashboard bridge
├── utils/
│   ├── player.py       # Song & MusicPlayer models
│   ├── embeds.py       # Discord embed helpers
│   ├── database.py     # SQLite async DB
│   └── logger.py       # Logging
├── web/
│   └── app.py          # FastAPI dashboard
├── data/               # Auto-created: DB + logs
├── .env.example
└── requirements.txt
```

---

## 🌐 Adding More Music Sources

To add Apple Music / Deezer / Bandcamp — yt-dlp already supports most of these. Just pass the URL to `/play` and it will work automatically.

## 🤖 AI Features Without OpenAI

If you don't have an OpenAI key:
- `/recommend` falls back to most-played-artist suggestions
- `/ask` will not work (tells user to use slash commands instead)
- `/autodj` still works using time-based mood detection

---

## 🛠️ Troubleshooting

**"opus not found" error:**
```bash
pip install PyNaCl
# or on Linux: sudo apt install libopus-dev
```

**No audio plays:**
- Ensure `ffmpeg` is installed: `ffmpeg -version`
- Check bot has `Connect` + `Speak` permissions in the VC

**Slash commands not showing:**
- Wait up to 1 hour for global sync, or use guild-specific sync for instant results
- Ensure `applications.commands` scope was granted when inviting

**Spotify not working:**
- Verify `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` are set in `.env`
- Bot falls back to YouTube search if Spotify credentials are missing
