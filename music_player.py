import streamlit as st
import os
import base64
import json
from pathlib import Path

# ── Try to import mutagen for metadata ──────────────────────────────────────

try:
from mutagen import File as MutagenFile
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC
from mutagen.flac import FLAC, Picture
from mutagen.mp4 import MP4
HAS_MUTAGEN = True
except ImportError:
HAS_MUTAGEN = False

# ── Page config ─────────────────────────────────────────────────────────────

st.set_page_config(
page_title=“𝄞 Music Player”,
page_icon=“🎵”,
layout=“wide”,
initial_sidebar_state=“expanded”,
)

SUPPORTED_EXT = {”.mp3”, “.flac”, “.wav”, “.ogg”, “.m4a”, “.aac”, “.opus”, “.wma”}

# ── Session state defaults ───────────────────────────────────────────────────

for key, default in {
“playlist”: [],          # list of file paths (str)
“current_index”: 0,
“scan_path”: “”,
}.items():
if key not in st.session_state:
st.session_state[key] = default

# ── Helpers ──────────────────────────────────────────────────────────────────

def scan_folder(folder: str) -> list[str]:
“”“Recursively collect supported audio files.”””
found = []
for root, _, files in os.walk(folder):
for f in sorted(files):
if Path(f).suffix.lower() in SUPPORTED_EXT:
found.append(os.path.join(root, f))
return sorted(found)

def get_metadata(path: str) -> dict:
“”“Return title, artist, album, duration, cover_b64.”””
meta = {
“title”: Path(path).stem,
“artist”: “Unknown Artist”,
“album”: “Unknown Album”,
“duration”: 0,
“cover_b64”: None,
“ext”: Path(path).suffix.lower(),
}
if not HAS_MUTAGEN:
return meta
try:
audio = MutagenFile(path, easy=True)
if audio is None:
return meta
if hasattr(audio, “info”) and hasattr(audio.info, “length”):
meta[“duration”] = int(audio.info.length)
for tag, key in [(“title”, “title”), (“artist”, “artist”), (“album”, “album”)]:
try:
val = audio.get(tag)
if val:
meta[key] = str(val[0])
except Exception:
pass
# Cover art — raw tags
raw = MutagenFile(path)
if raw:
# MP3 ID3
if hasattr(raw, “tags”) and raw.tags:
for k in raw.tags.keys():
if k.startswith(“APIC”):
apic = raw.tags[k]
meta[“cover_b64”] = base64.b64encode(apic.data).decode()
break
# FLAC
if isinstance(raw, FLAC) and raw.pictures:
meta[“cover_b64”] = base64.b64encode(raw.pictures[0].data).decode()
# MP4/M4A
if isinstance(raw, MP4):
covr = raw.tags.get(“covr”) if raw.tags else None
if covr:
meta[“cover_b64”] = base64.b64encode(bytes(covr[0])).decode()
except Exception:
pass
return meta

def fmt_duration(secs: int) -> str:
m, s = divmod(secs, 60)
h, m = divmod(m, 60)
return f”{h}:{m:02d}:{s:02d}” if h else f”{m}:{s:02d}”

def audio_b64(path: str) -> str:
with open(path, “rb”) as f:
return base64.b64encode(f.read()).decode()

def mime(ext: str) -> str:
return {
“.mp3”: “audio/mpeg”,
“.flac”: “audio/flac”,
“.wav”: “audio/wav”,
“.ogg”: “audio/ogg”,
“.m4a”: “audio/mp4”,
“.aac”: “audio/aac”,
“.opus”: “audio/ogg”,
“.wma”: “audio/x-ms-wma”,
}.get(ext, “audio/mpeg”)

# ── CSS ──────────────────────────────────────────────────────────────────────

st.markdown(”””

<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;800&display=swap');

:root {
    --bg:      #0d0d0f;
    --surface: #17171c;
    --card:    #1e1e26;
    --border:  #2a2a38;
    --accent:  #c8f548;
    --accent2: #7b61ff;
    --text:    #e8e8f0;
    --muted:   #6b6b80;
    --radius:  14px;
}

html, body, [data-testid="stApp"] {
    background: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'Syne', sans-serif;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * { color: var(--text) !important; }

/* Inputs */
.stTextInput input, .stSelectbox select, .stFileUploader {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    border-radius: 8px !important;
    font-family: 'Space Mono', monospace !important;
}

/* Buttons */
.stButton > button {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    border-radius: 8px !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 600 !important;
    transition: all .2s !important;
}
.stButton > button:hover {
    border-color: var(--accent) !important;
    color: var(--accent) !important;
    transform: translateY(-1px) !important;
}

/* Player card */
.player-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 28px;
    position: relative;
    overflow: hidden;
}
.player-card::before {
    content: "";
    position: absolute;
    inset: 0;
    background: radial-gradient(ellipse at top left, rgba(200,245,72,.06), transparent 60%);
    pointer-events: none;
}
.cover-img {
    width: 100%;
    aspect-ratio: 1;
    object-fit: cover;
    border-radius: 10px;
    border: 1px solid var(--border);
}
.cover-placeholder {
    width: 100%;
    aspect-ratio: 1;
    background: linear-gradient(135deg, #1e1e26, #2a2a3a);
    border-radius: 10px;
    border: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 64px;
}
.track-title {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 1.35rem;
    color: var(--text);
    margin: 0 0 4px;
    line-height: 1.2;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.track-meta {
    font-family: 'Space Mono', monospace;
    font-size: .75rem;
    color: var(--muted);
}
.track-meta span {
    color: var(--accent);
}
.badge {
    display: inline-block;
    background: var(--accent);
    color: #0d0d0f;
    font-family: 'Space Mono', monospace;
    font-size: .65rem;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 20px;
    letter-spacing: .05em;
    margin-left: 8px;
    vertical-align: middle;
}

/* Playlist items */
.pl-item {
    display: flex;
    align-items: center;
    padding: 10px 14px;
    border-radius: 8px;
    cursor: pointer;
    transition: background .15s;
    border: 1px solid transparent;
    margin-bottom: 4px;
    gap: 10px;
}
.pl-item:hover { background: var(--card); border-color: var(--border); }
.pl-item.active {
    background: rgba(200,245,72,.1);
    border-color: rgba(200,245,72,.3);
}
.pl-num {
    font-family: 'Space Mono', monospace;
    font-size: .7rem;
    color: var(--muted);
    width: 22px;
    text-align: right;
    flex-shrink: 0;
}
.pl-num.active { color: var(--accent); }
.pl-info { overflow: hidden; flex: 1; }
.pl-name {
    font-weight: 600;
    font-size: .85rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.pl-artist {
    font-family: 'Space Mono', monospace;
    font-size: .68rem;
    color: var(--muted);
}
.pl-dur {
    font-family: 'Space Mono', monospace;
    font-size: .68rem;
    color: var(--muted);
    flex-shrink: 0;
}

h1, h2, h3 { font-family: 'Syne', sans-serif !important; }
.section-label {
    font-family: 'Space Mono', monospace;
    font-size: .7rem;
    color: var(--muted);
    letter-spacing: .1em;
    text-transform: uppercase;
    margin-bottom: 12px;
    display: block;
}
hr { border-color: var(--border) !important; margin: 16px 0 !important; }

/* Hide streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 2rem !important; }

/* Audio element hide (we use custom UI) */
audio { display: block; width: 100%; border-radius: 8px; }
</style>

“””, unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
st.markdown(”## 𝄞 Music Player”)
st.markdown(”—”)

```
# ── Folder scan ─────────────────────────────────────────────
st.markdown('<span class="section-label">📁 Cartella Musica</span>', unsafe_allow_html=True)
folder_input = st.text_input(
    "Percorso cartella",
    value=st.session_state.scan_path,
    placeholder="Es. C:/Users/franc/Music",
    label_visibility="collapsed",
)

if st.button("🔍 Scansiona cartella", use_container_width=True):
    folder_input = folder_input.strip()
    if os.path.isdir(folder_input):
        files = scan_folder(folder_input)
        if files:
            st.session_state.playlist = files
            st.session_state.current_index = 0
            st.session_state.scan_path = folder_input
            st.success(f"✅ {len(files)} brani trovati")
        else:
            st.warning("Nessun file audio trovato.")
    else:
        st.error("Cartella non trovata.")

st.markdown("---")

# ── Upload singoli file ──────────────────────────────────────
st.markdown('<span class="section-label">⬆️ Oppure carica file</span>', unsafe_allow_html=True)
uploaded = st.file_uploader(
    "File audio",
    type=["mp3", "flac", "wav", "ogg", "m4a", "aac", "opus"],
    accept_multiple_files=True,
    label_visibility="collapsed",
)

if uploaded:
    # Save uploads to temp dir
    import tempfile, shutil
    tmp_dir = tempfile.mkdtemp(prefix="music_player_")
    saved = []
    for uf in uploaded:
        dest = os.path.join(tmp_dir, uf.name)
        with open(dest, "wb") as f:
            f.write(uf.read())
        saved.append(dest)
    # Merge with existing playlist (avoid duplicates by name)
    existing_names = {Path(p).name for p in st.session_state.playlist}
    new_files = [p for p in saved if Path(p).name not in existing_names]
    st.session_state.playlist = st.session_state.playlist + new_files
    if new_files:
        st.success(f"✅ {len(new_files)} file aggiunti")

st.markdown("---")

# ── Playlist actions ─────────────────────────────────────────
if st.session_state.playlist:
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔀 Shuffle", use_container_width=True):
            import random
            cur = st.session_state.playlist[st.session_state.current_index]
            random.shuffle(st.session_state.playlist)
            st.session_state.current_index = st.session_state.playlist.index(cur)
    with col2:
        if st.button("🗑️ Svuota", use_container_width=True):
            st.session_state.playlist = []
            st.session_state.current_index = 0
            st.rerun()

# ── Stats ────────────────────────────────────────────────────
if st.session_state.playlist:
    st.markdown("---")
    st.markdown(f"""
    <div class="track-meta">
        Playlist: <span>{len(st.session_state.playlist)} brani</span>
    </div>
    """, unsafe_allow_html=True)
    if not HAS_MUTAGEN:
        st.info("💡 Installa `mutagen` per metadata e copertine:\n`pip install mutagen`")
```

# ── Main area ────────────────────────────────────────────────────────────────

playlist = st.session_state.playlist
idx = st.session_state.current_index

if not playlist:
st.markdown(”””
<div style="text-align:center;padding:80px 0;">
<div style="font-size:80px;margin-bottom:24px;">🎵</div>
<h2 style="color:#e8e8f0;font-family:'Syne',sans-serif;">Nessun brano caricato</h2>
<p style="color:#6b6b80;font-family:'Space Mono',monospace;font-size:.85rem;">
Scansiona una cartella o carica file dalla sidebar →
</p>
</div>
“””, unsafe_allow_html=True)
st.stop()

# ── Clamp index ──────────────────────────────────────────────────────────────

idx = max(0, min(idx, len(playlist) - 1))
st.session_state.current_index = idx
current_path = playlist[idx]
meta = get_metadata(current_path)

# ── Layout: player left, playlist right ──────────────────────────────────────

left, right = st.columns([1, 1.6], gap=“large”)

# ──────────────── PLAYER ────────────────────────────────────────────────────

with left:
st.markdown(’<div class="player-card">’, unsafe_allow_html=True)

```
# Cover art
if meta["cover_b64"]:
    st.markdown(
        f'<img class="cover-img" src="data:image/jpeg;base64,{meta["cover_b64"]}"/>',
        unsafe_allow_html=True,
    )
else:
    st.markdown('<div class="cover-placeholder">♪</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Track info
ext_badge = meta["ext"].lstrip(".").upper()
dur_str = fmt_duration(meta["duration"]) if meta["duration"] else "—"
st.markdown(f"""
<p class="track-title">{meta['title']}</p>
<p class="track-meta">
    <span>{meta['artist']}</span> &nbsp;·&nbsp; {meta['album']}
    <span class="badge">{ext_badge}</span>
</p>
<p class="track-meta" style="margin-top:4px;">⏱ {dur_str} &nbsp;|&nbsp; #{idx+1}/{len(playlist)}</p>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Audio player ──────────────────────────────────────────────
try:
    audio_data = audio_b64(current_path)
    audio_mime = mime(meta["ext"])
    audio_html = f"""
    <audio id="mainPlayer" controls autoplay style="width:100%;border-radius:8px;">
        <source src="data:{audio_mime};base64,{audio_data}" type="{audio_mime}">
        Il tuo browser non supporta l'audio.
    </audio>
    """
    st.markdown(audio_html, unsafe_allow_html=True)
except Exception as e:
    st.error(f"Errore caricamento audio: {e}")

st.markdown("<br>", unsafe_allow_html=True)

# ── Controls ──────────────────────────────────────────────────
c1, c2, c3 = st.columns([1, 1, 1])
with c1:
    if st.button("⏮ Prec", use_container_width=True, disabled=(idx == 0)):
        st.session_state.current_index = idx - 1
        st.rerun()
with c2:
    st.markdown(f"""
    <div style="text-align:center;font-family:'Space Mono',monospace;font-size:.7rem;color:#6b6b80;padding-top:8px;">
        {idx+1} / {len(playlist)}
    </div>""", unsafe_allow_html=True)
with c3:
    if st.button("Succ ⏭", use_container_width=True, disabled=(idx == len(playlist) - 1)):
        st.session_state.current_index = idx + 1
        st.rerun()

st.markdown('</div>', unsafe_allow_html=True)
```

# ──────────────── PLAYLIST ───────────────────────────────────────────────────

with right:
st.markdown(’<span class="section-label">📋 Playlist</span>’, unsafe_allow_html=True)

```
# Search
search = st.text_input("🔎 Cerca brano…", placeholder="Titolo o file…", label_visibility="collapsed")

# Build playlist items
items_html = []
for i, path in enumerate(playlist):
    m = get_metadata(path)
    active = "active" if i == idx else ""
    num_cls = "pl-num active" if i == idx else "pl-num"
    dur = fmt_duration(m["duration"]) if m["duration"] else "—"

    if search and search.lower() not in m["title"].lower() and search.lower() not in m["artist"].lower():
        continue

    items_html.append((i, f"""
    <div class="pl-item {active}" id="pl-{i}">
        <div class="{num_cls}">{i+1}</div>
        <div class="pl-info">
            <div class="pl-name">{m['title']}</div>
            <div class="pl-artist">{m['artist']}</div>
        </div>
        <div class="pl-dur">{dur}</div>
    </div>
    """))

# Render playlist with clickable buttons
st.markdown(f"""
<div style="max-height:520px;overflow-y:auto;padding-right:4px;">
    {''.join(h for _, h in items_html)}
</div>
""", unsafe_allow_html=True)

st.markdown("---")
st.markdown('<span class="section-label">🎯 Vai al brano</span>', unsafe_allow_html=True)

visible_indices = [i for i, _ in items_html]
if visible_indices:
    goto = st.selectbox(
        "Seleziona brano",
        options=visible_indices,
        format_func=lambda i: f"{i+1}. {get_metadata(playlist[i])['title']}",
        index=visible_indices.index(idx) if idx in visible_indices else 0,
        label_visibility="collapsed",
    )
    if st.button("▶ Riproduci selezionato", use_container_width=True):
        st.session_state.current_index = goto
        st.rerun()
else:
    st.markdown('<p class="track-meta">Nessun risultato</p>', unsafe_allow_html=True)
```
