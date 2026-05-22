"""
Web Dashboard — FastAPI + Jinja2 for queue control and analytics
Run with: python web/app.py
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.database import Database

app = FastAPI(title="Music Bot Dashboard")
db = Database()

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🎵 Music Bot Dashboard</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'Segoe UI', sans-serif; background: #0f0f23; color: #e0e0e0; }
  .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px 40px; display: flex; align-items: center; gap: 15px; }
  .header h1 { color: white; font-size: 1.8rem; }
  .container { max-width: 1200px; margin: 30px auto; padding: 0 20px; display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
  .card { background: #1a1a2e; border-radius: 12px; padding: 24px; border: 1px solid #2d2d44; }
  .card h2 { font-size: 1.1rem; color: #a78bfa; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
  .stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .stat { background: #16213e; border-radius: 8px; padding: 16px; text-align: center; }
  .stat-value { font-size: 2rem; font-weight: 700; color: #a78bfa; }
  .stat-label { font-size: 0.8rem; color: #888; margin-top: 4px; }
  .track { display: flex; align-items: center; gap: 12px; padding: 10px; border-radius: 8px; background: #16213e; margin-bottom: 8px; }
  .track-info { flex: 1; }
  .track-title { font-weight: 600; font-size: 0.95rem; }
  .track-meta { font-size: 0.8rem; color: #888; }
  .badge { background: #667eea; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; }
  .controls { display: flex; gap: 8px; flex-wrap: wrap; }
  .btn { padding: 10px 20px; border-radius: 8px; border: none; cursor: pointer; font-weight: 600; font-size: 0.9rem; transition: opacity 0.2s; }
  .btn:hover { opacity: 0.85; }
  .btn-primary { background: #667eea; color: white; }
  .btn-danger  { background: #ef4444; color: white; }
  .btn-success { background: #22c55e; color: white; }
  .btn-warn    { background: #f59e0b; color: white; }
  .now-playing { background: linear-gradient(135deg, #1a1a2e, #2d1b69); border: 1px solid #667eea; border-radius: 12px; padding: 24px; margin-bottom: 20px; }
  .np-title { font-size: 1.4rem; font-weight: 700; margin-bottom: 4px; }
  .np-artist { color: #a78bfa; margin-bottom: 16px; }
  .progress-bar { background: #2d2d44; border-radius: 4px; height: 6px; overflow: hidden; }
  .progress-fill { background: linear-gradient(90deg, #667eea, #a78bfa); height: 100%; width: 60%; border-radius: 4px; animation: pulse 2s infinite; }
  @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.7; } }
  .full-width { grid-column: 1 / -1; }
  select { background: #2d2d44; color: #e0e0e0; border: 1px solid #444; border-radius: 6px; padding: 8px 12px; }
  .api-note { background: #1e2a1e; border: 1px solid #22c55e; border-radius: 8px; padding: 16px; margin-top: 12px; font-size: 0.85rem; color: #88cc88; }
</style>
</head>
<body>
<div class="header">
  <span style="font-size:2rem">🎵</span>
  <div>
    <h1>Music Bot Dashboard</h1>
    <p style="color:rgba(255,255,255,0.7);font-size:0.85rem">Real-time controls & analytics</p>
  </div>
</div>

<div style="max-width:1200px;margin:30px auto;padding:0 20px">

  <!-- Now Playing -->
  <div class="now-playing" id="now-playing">
    <div style="display:flex;justify-content:space-between;align-items:flex-start">
      <div>
        <p style="color:#a78bfa;font-size:0.85rem;margin-bottom:8px">▶ NOW PLAYING</p>
        <div class="np-title" id="np-title">Fetching...</div>
        <div class="np-artist" id="np-artist">—</div>
      </div>
      <span class="badge" id="np-source">—</span>
    </div>
    <div class="progress-bar" style="margin-top:16px"><div class="progress-fill"></div></div>
  </div>

  <div class="container">

    <!-- Controls -->
    <div class="card">
      <h2>🎛️ Playback Controls</h2>
      <div class="controls">
        <button class="btn btn-warn" onclick="api('pause')">⏸ Pause</button>
        <button class="btn btn-success" onclick="api('resume')">▶ Resume</button>
        <button class="btn btn-primary" onclick="api('skip')">⏭ Skip</button>
        <button class="btn btn-danger" onclick="api('stop')">⏹ Stop</button>
      </div>
      <div style="margin-top:16px">
        <label style="font-size:0.85rem;color:#888;display:block;margin-bottom:6px">Volume</label>
        <input type="range" min="0" max="200" value="50" style="width:100%" oninput="setVolume(this.value)">
      </div>
      <div style="margin-top:16px">
        <label style="font-size:0.85rem;color:#888;display:block;margin-bottom:6px">Loop Mode</label>
        <select onchange="setLoop(this.value)">
          <option value="off">Off</option>
          <option value="song">Song</option>
          <option value="queue">Queue</option>
        </select>
      </div>
    </div>

    <!-- Stats -->
    <div class="card">
      <h2>📊 Server Stats</h2>
      <div class="stat-grid">
        <div class="stat"><div class="stat-value" id="stat-total">—</div><div class="stat-label">Total Plays</div></div>
        <div class="stat"><div class="stat-value" id="stat-listeners">—</div><div class="stat-label">Listeners</div></div>
        <div class="stat"><div class="stat-value" id="stat-queue">—</div><div class="stat-label">Queue Length</div></div>
        <div class="stat"><div class="stat-value" id="stat-playlists">—</div><div class="stat-label">Playlists</div></div>
      </div>
    </div>

    <!-- Queue -->
    <div class="card full-width">
      <h2>📋 Current Queue</h2>
      <div id="queue-list"><p style="color:#888">Loading...</p></div>
    </div>

    <!-- Top Songs -->
    <div class="card">
      <h2>🔥 Top Songs Today</h2>
      <div id="top-songs"><p style="color:#888">Loading...</p></div>
    </div>

    <!-- Top Listeners -->
    <div class="card">
      <h2>🏆 Top Listeners</h2>
      <div id="top-listeners"><p style="color:#888">Loading...</p></div>
    </div>

  </div>

  <div class="api-note">
    💡 <strong>API Endpoints:</strong>
    GET /api/stats • GET /api/queue • POST /api/control/{action} • GET /api/leaderboard/{type}
    <br>The dashboard connects to the bot's SQLite database. For live queue control, run the bot and dashboard together.
  </div>
</div>

<script>
async function api(action, data={}) {
  try {
    const r = await fetch(`/api/control/${action}`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
    const j = await r.json();
    showToast(j.message || 'Done');
  } catch(e) { showToast('Error: ' + e.message, true); }
}

async function loadStats() {
  try {
    const r = await fetch('/api/stats');
    const d = await r.json();
    document.getElementById('stat-total').textContent = d.total_plays ?? '—';
    document.getElementById('stat-listeners').textContent = d.unique_listeners ?? '—';
    document.getElementById('stat-queue').textContent = d.queue_length ?? '—';
    document.getElementById('stat-playlists').textContent = d.total_playlists ?? '—';
    if (d.now_playing) {
      document.getElementById('np-title').textContent = d.now_playing.title;
      document.getElementById('np-artist').textContent = d.now_playing.artist;
      document.getElementById('np-source').textContent = d.now_playing.source;
    }
  } catch(e) {}
}

async function loadLeaderboard() {
  try {
    const songs = await (await fetch('/api/leaderboard/songs')).json();
    document.getElementById('top-songs').innerHTML = (songs.data||[]).slice(0,5).map((s,i) =>
      `<div class="track"><div class="track-info"><div class="track-title">${i+1}. ${s.title||'?'}</div><div class="track-meta">${s.count} plays</div></div></div>`
    ).join('') || '<p style="color:#888">No data yet</p>';

    const listeners = await (await fetch('/api/leaderboard/listeners')).json();
    document.getElementById('top-listeners').innerHTML = (listeners.data||[]).slice(0,5).map((l,i) =>
      `<div class="track"><div class="track-info"><div class="track-title">${i+1}. User ${l.user_id}</div><div class="track-meta">${l.play_count} songs</div></div></div>`
    ).join('') || '<p style="color:#888">No data yet</p>';
  } catch(e) {}
}

function setVolume(val) { api('volume', {level: parseInt(val)}); }
function setLoop(val) { api('loop', {mode: val}); }

function showToast(msg, err=false) {
  const t = document.createElement('div');
  t.textContent = msg;
  t.style.cssText = `position:fixed;bottom:20px;right:20px;background:${err?'#ef4444':'#22c55e'};color:white;padding:12px 20px;border-radius:8px;z-index:999;font-weight:600;box-shadow:0 4px 12px rgba(0,0,0,0.4)`;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3000);
}

// Load on start + poll every 10s
loadStats(); loadLeaderboard();
setInterval(loadStats, 10000);
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def root():
    return DASHBOARD_HTML


@app.get("/api/stats")
async def get_stats(guild_id: int = 0):
    stats = await db.get_server_stats(guild_id)
    stats["queue_length"] = 0
    stats["total_playlists"] = 0
    stats["now_playing"] = None
    return JSONResponse(stats)


@app.get("/api/leaderboard/{type}")
async def leaderboard(type: str, guild_id: int = 0):
    data = await db.get_leaderboard(guild_id, type)
    return JSONResponse({"type": type, "data": data})


@app.post("/api/control/{action}")
async def control(action: str, request: Request):
    """Placeholder — in production, this sends commands to the bot via Redis/websocket"""
    messages = {
        "skip": "⏭ Skip command sent",
        "pause": "⏸ Pause command sent",
        "resume": "▶ Resume command sent",
        "stop": "⏹ Stop command sent",
        "volume": "🔊 Volume updated",
        "loop": "🔁 Loop mode updated",
    }
    return JSONResponse({"status": "ok", "message": messages.get(action, "Command sent")})


if __name__ == "__main__":
    port = int(os.getenv("DASHBOARD_PORT", 8080))
    print(f"🌐 Dashboard starting at http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
