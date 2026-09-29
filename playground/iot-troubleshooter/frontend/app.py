"""
Streamlit Chat UI — IoT Troubleshooter
"""

from __future__ import annotations

import os
import uuid
from typing import Optional

import requests
import streamlit as st

# ── Config ─────────────────────────────────────────────────────────────────
API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000")

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="IoT Troubleshooter",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS / Animations ─────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Global reset & body ── */
html, body, [data-testid="stAppViewContainer"] {
    background: #030712 !important;
    font-family: 'Inter', sans-serif !important;
}

[data-testid="stAppViewContainer"]::before {
    content: '';
    position: fixed;
    inset: 0;
    background:
        radial-gradient(ellipse 80% 60% at 20% 10%, rgba(99,102,241,0.18) 0%, transparent 60%),
        radial-gradient(ellipse 60% 50% at 80% 80%, rgba(6,182,212,0.14) 0%, transparent 60%),
        radial-gradient(ellipse 50% 40% at 60% 30%, rgba(168,85,247,0.10) 0%, transparent 55%);
    pointer-events: none;
    z-index: 0;
}

/* ── Floating orbs ── */
[data-testid="stAppViewContainer"]::after {
    content: '';
    position: fixed;
    width: 500px; height: 500px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(99,102,241,0.07) 0%, transparent 70%);
    top: -100px; left: -100px;
    animation: orbFloat 12s ease-in-out infinite;
    pointer-events: none;
    z-index: 0;
}

@keyframes orbFloat {
    0%, 100% { transform: translate(0,0) scale(1); }
    33%       { transform: translate(80px, 60px) scale(1.1); }
    66%       { transform: translate(-40px, 100px) scale(0.95); }
}

/* ── Particle canvas overlay ── */
.particle-bg {
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 0;
    overflow: hidden;
}
.particle {
    position: absolute;
    border-radius: 50%;
    opacity: 0;
    animation: particleDrift var(--dur) ease-in-out infinite;
    animation-delay: var(--delay);
}
@keyframes particleDrift {
    0%   { opacity: 0;   transform: translateY(100vh) scale(0); }
    10%  { opacity: 0.6; }
    90%  { opacity: 0.3; }
    100% { opacity: 0;   transform: translateY(-10vh) scale(1.5); }
}

/* ── Sidebar liquid glass ── */
[data-testid="stSidebar"] {
    background: rgba(255,255,255,0.03) !important;
    backdrop-filter: blur(24px) saturate(180%) !important;
    -webkit-backdrop-filter: blur(24px) saturate(180%) !important;
    border-right: 1px solid rgba(255,255,255,0.07) !important;
    box-shadow: inset -1px 0 0 rgba(255,255,255,0.04), 4px 0 32px rgba(0,0,0,0.5) !important;
}

[data-testid="stSidebarContent"] {
    background: transparent !important;
}

/* ── Sidebar title ── */
.sidebar-logo {
    text-align: center;
    padding: 20px 0 8px;
}
.sidebar-logo .icon-ring {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 64px; height: 64px;
    border-radius: 50%;
    background: linear-gradient(135deg, rgba(99,102,241,0.3), rgba(6,182,212,0.3));
    border: 1px solid rgba(99,102,241,0.4);
    font-size: 28px;
    box-shadow: 0 0 24px rgba(99,102,241,0.3), inset 0 0 16px rgba(255,255,255,0.05);
    animation: iconPulse 3s ease-in-out infinite;
    margin-bottom: 10px;
}
@keyframes iconPulse {
    0%, 100% { box-shadow: 0 0 24px rgba(99,102,241,0.3), inset 0 0 16px rgba(255,255,255,0.05); }
    50%       { box-shadow: 0 0 40px rgba(99,102,241,0.55), inset 0 0 24px rgba(255,255,255,0.08); }
}
.sidebar-logo .app-title {
    font-size: 17px;
    font-weight: 700;
    background: linear-gradient(135deg, #818cf8, #22d3ee);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: 0.5px;
}
.sidebar-logo .app-sub {
    font-size: 11px;
    color: rgba(255,255,255,0.35);
    margin-top: 2px;
}

/* ── Glass card (sidebar sections) ── */
.glass-card {
    background: rgba(255,255,255,0.04);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    padding: 14px 16px;
    margin: 10px 0;
    box-shadow: 0 4px 24px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.06);
    transition: border-color 0.3s;
}
.glass-card:hover {
    border-color: rgba(99,102,241,0.3);
}
.glass-card-title {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    color: rgba(255,255,255,0.35);
    margin-bottom: 8px;
}

/* ── Chunk badge ── */
.chunk-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: linear-gradient(135deg, rgba(34,211,238,0.15), rgba(99,102,241,0.15));
    border: 1px solid rgba(34,211,238,0.3);
    border-radius: 20px;
    padding: 4px 12px;
    font-size: 12px;
    color: #22d3ee;
    font-weight: 600;
    animation: badgeGlow 3s ease-in-out infinite;
}
@keyframes badgeGlow {
    0%, 100% { box-shadow: 0 0 8px rgba(34,211,238,0.2); }
    50%       { box-shadow: 0 0 16px rgba(34,211,238,0.45); }
}
.chunk-badge-warn {
    background: rgba(245,158,11,0.12);
    border-color: rgba(245,158,11,0.3);
    color: #fbbf24;
}

/* ── Session info ── */
.session-info {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: rgba(255,255,255,0.3);
    background: rgba(0,0,0,0.2);
    border-radius: 8px;
    padding: 6px 10px;
    margin: 4px 0;
    border: 1px solid rgba(255,255,255,0.05);
}

/* ── Sidebar divider ── */
hr {
    border-color: rgba(255,255,255,0.06) !important;
    margin: 12px 0 !important;
}

/* ── Main area: wipe default white ── */
[data-testid="stMain"], .main, .block-container {
    background: transparent !important;
}

/* ── Page header ── */
.page-header {
    text-align: center;
    padding: 32px 0 24px;
    position: relative;
}
.page-header .header-glow {
    position: absolute;
    top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    width: 400px; height: 100px;
    background: radial-gradient(ellipse, rgba(99,102,241,0.15) 0%, transparent 70%);
    pointer-events: none;
}
.page-header h1 {
    font-size: 36px;
    font-weight: 800;
    background: linear-gradient(135deg, #ffffff 0%, #818cf8 40%, #22d3ee 80%, #a78bfa 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -0.5px;
    margin: 0;
    animation: titleShimmer 4s linear infinite;
    background-size: 200% auto;
}
@keyframes titleShimmer {
    0%   { background-position: 0% center; }
    100% { background-position: 200% center; }
}
.page-header p {
    color: rgba(255,255,255,0.35);
    font-size: 14px;
    margin-top: 6px;
}

/* ── Welcome card ── */
.welcome-card {
    background: rgba(255,255,255,0.03);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 20px;
    padding: 28px 32px;
    margin: 0 0 24px;
    box-shadow: 0 8px 40px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.06);
    position: relative;
    overflow: hidden;
}
.welcome-card::before {
    content: '';
    position: absolute;
    top: -50%; left: -50%;
    width: 200%; height: 200%;
    background: conic-gradient(from 0deg at 50% 50%,
        transparent 0deg, rgba(99,102,241,0.04) 60deg,
        transparent 120deg, rgba(6,182,212,0.04) 180deg,
        transparent 240deg, rgba(168,85,247,0.04) 300deg,
        transparent 360deg);
    animation: cardRotate 20s linear infinite;
    pointer-events: none;
}
@keyframes cardRotate {
    to { transform: rotate(360deg); }
}
.welcome-title {
    font-size: 18px;
    font-weight: 700;
    color: #fff;
    margin-bottom: 6px;
}
.welcome-sub {
    font-size: 13px;
    color: rgba(255,255,255,0.45);
    margin-bottom: 18px;
    line-height: 1.6;
}
.example-chip {
    display: inline-block;
    background: rgba(99,102,241,0.12);
    border: 1px solid rgba(99,102,241,0.25);
    border-radius: 20px;
    padding: 5px 14px;
    font-size: 12px;
    color: rgba(255,255,255,0.7);
    margin: 4px 4px 0 0;
    cursor: default;
    transition: all 0.25s;
}
.example-chip:hover {
    background: rgba(99,102,241,0.25);
    border-color: rgba(99,102,241,0.5);
    color: #fff;
    transform: translateY(-1px);
}

/* ── Chat messages ── */
.msg-row {
    display: flex;
    align-items: flex-end;
    gap: 10px;
    margin: 12px 0;
    animation: msgSlideIn 0.35s cubic-bezier(0.34,1.56,0.64,1);
}
@keyframes msgSlideIn {
    from { opacity: 0; transform: translateY(16px) scale(0.97); }
    to   { opacity: 1; transform: translateY(0) scale(1); }
}
.msg-row.user-row  { flex-direction: row-reverse; }
.msg-row.bot-row   { flex-direction: row; }

.avatar {
    width: 34px; height: 34px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 16px;
    flex-shrink: 0;
}
.avatar.user-av {
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    box-shadow: 0 0 14px rgba(99,102,241,0.5);
}
.avatar.bot-av {
    background: linear-gradient(135deg, #0891b2, #22d3ee);
    box-shadow: 0 0 14px rgba(6,182,212,0.5);
    animation: botAvatarPulse 3s ease-in-out infinite;
}
@keyframes botAvatarPulse {
    0%, 100% { box-shadow: 0 0 14px rgba(6,182,212,0.5); }
    50%       { box-shadow: 0 0 28px rgba(6,182,212,0.8); }
}

/* ── Liquid glass bubble ── */
.user-bubble {
    background: linear-gradient(135deg, rgba(99,102,241,0.35), rgba(139,92,246,0.25));
    backdrop-filter: blur(20px) saturate(180%);
    -webkit-backdrop-filter: blur(20px) saturate(180%);
    border: 1px solid rgba(139,92,246,0.4);
    border-radius: 18px 18px 4px 18px;
    padding: 12px 18px;
    max-width: 78%;
    color: #fff;
    font-size: 14px;
    line-height: 1.65;
    box-shadow: 0 4px 24px rgba(99,102,241,0.25), inset 0 1px 0 rgba(255,255,255,0.15);
    word-wrap: break-word;
    white-space: pre-wrap;
}
.bot-bubble {
    background: rgba(255,255,255,0.05);
    backdrop-filter: blur(20px) saturate(180%);
    -webkit-backdrop-filter: blur(20px) saturate(180%);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 18px 18px 18px 4px;
    padding: 14px 18px;
    max-width: 82%;
    color: rgba(255,255,255,0.9);
    font-size: 14px;
    line-height: 1.7;
    box-shadow: 0 4px 24px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.06);
    word-wrap: break-word;
    white-space: pre-wrap;
    position: relative;
    overflow: hidden;
}
.bot-bubble::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, rgba(34,211,238,0.04) 0%, transparent 50%);
    pointer-events: none;
    border-radius: inherit;
}

/* ── Source tags ── */
.sources-row {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin: 8px 0 4px 44px;
    align-items: center;
}
.source-tag {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: rgba(34,211,238,0.1);
    border: 1px solid rgba(34,211,238,0.25);
    border-radius: 20px;
    padding: 3px 10px;
    font-size: 11px;
    color: #67e8f9;
    font-family: 'JetBrains Mono', monospace;
    transition: all 0.2s;
}
.source-tag:hover {
    background: rgba(34,211,238,0.2);
    border-color: rgba(34,211,238,0.5);
}
.rag-label {
    font-size: 11px;
    color: rgba(255,255,255,0.25);
    margin-right: 4px;
}
.no-rag-badge {
    margin: 4px 0 4px 44px;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    color: rgba(251,191,36,0.7);
    background: rgba(251,191,36,0.06);
    border: 1px solid rgba(251,191,36,0.15);
    border-radius: 20px;
    padding: 3px 12px;
}

/* ── Input area ── */
.input-glass {
    background: rgba(255,255,255,0.04);
    backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 20px;
    padding: 16px 18px;
    margin-top: 16px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.06);
    transition: border-color 0.3s, box-shadow 0.3s;
}
.input-glass:focus-within {
    border-color: rgba(99,102,241,0.5);
    box-shadow: 0 8px 32px rgba(0,0,0,0.4), 0 0 0 1px rgba(99,102,241,0.2), inset 0 1px 0 rgba(255,255,255,0.06);
}

/* ── Streamlit textarea override ── */
textarea {
    background: transparent !important;
    color: rgba(255,255,255,0.85) !important;
    border: none !important;
    outline: none !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
    resize: none !important;
}
textarea::placeholder {
    color: rgba(255,255,255,0.2) !important;
}

/* ── Streamlit button overrides ── */
.stButton > button {
    background: linear-gradient(135deg, rgba(99,102,241,0.8), rgba(139,92,246,0.8)) !important;
    color: #fff !important;
    border: 1px solid rgba(139,92,246,0.4) !important;
    border-radius: 12px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    padding: 8px 16px !important;
    transition: all 0.25s !important;
    backdrop-filter: blur(8px) !important;
    box-shadow: 0 4px 16px rgba(99,102,241,0.25) !important;
    position: relative !important;
    overflow: hidden !important;
}
.stButton > button::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, rgba(255,255,255,0.12), transparent);
    pointer-events: none;
}
.stButton > button:hover {
    background: linear-gradient(135deg, rgba(99,102,241,1), rgba(139,92,246,1)) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 24px rgba(99,102,241,0.45) !important;
}
.stButton > button:active {
    transform: translateY(0) !important;
}

/* ── Form submit button (Send) ── */
[data-testid="stFormSubmitButton"] > button {
    background: linear-gradient(135deg, #6366f1, #22d3ee) !important;
    border: none !important;
    border-radius: 12px !important;
    font-size: 14px !important;
    font-weight: 700 !important;
    box-shadow: 0 4px 20px rgba(99,102,241,0.4) !important;
    animation: sendBtnGlow 3s ease-in-out infinite !important;
}
[data-testid="stFormSubmitButton"] > button:hover {
    box-shadow: 0 6px 28px rgba(99,102,241,0.65) !important;
    transform: translateY(-2px) !important;
}
@keyframes sendBtnGlow {
    0%, 100% { box-shadow: 0 4px 20px rgba(99,102,241,0.4); }
    50%       { box-shadow: 0 4px 32px rgba(34,211,238,0.5); }
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: rgba(255,255,255,0.03) !important;
    border: 1px dashed rgba(255,255,255,0.12) !important;
    border-radius: 12px !important;
}

/* ── Spinner ── */
[data-testid="stSpinner"] > div {
    color: #22d3ee !important;
}

/* ── All text colour fixes ── */
h1, h2, h3, h4, h5, h6, p, span, label,
[data-testid="stMarkdownContainer"] p,
[data-testid="stSidebarContent"] * {
    color: rgba(255,255,255,0.82) !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(99,102,241,0.35); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: rgba(99,102,241,0.6); }

/* ── Status indicator ── */
.status-dot {
    display: inline-block;
    width: 7px; height: 7px;
    border-radius: 50%;
    background: #22c55e;
    box-shadow: 0 0 8px #22c55e;
    animation: dotPulse 2s ease-in-out infinite;
    margin-right: 6px;
    vertical-align: middle;
}
@keyframes dotPulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50%       { opacity: 0.5; transform: scale(0.75); }
}
.status-dot.offline { background: #ef4444; box-shadow: 0 0 8px #ef4444; }

/* ── Typing indicator ── */
.typing-dots span {
    display: inline-block;
    width: 6px; height: 6px;
    border-radius: 50%;
    background: #22d3ee;
    margin: 0 2px;
    animation: typingBounce 1.2s ease-in-out infinite;
}
.typing-dots span:nth-child(2) { animation-delay: 0.2s; }
.typing-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes typingBounce {
    0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
    40%            { transform: translateY(-6px); opacity: 1; }
}
</style>

<!-- Floating particles -->
<div class="particle-bg" id="particles"></div>
<script>
(function(){
    var colours = ['#6366f1','#22d3ee','#a78bfa','#818cf8','#67e8f9'];
    var cont = document.getElementById('particles');
    if (!cont) return;
    for (var i = 0; i < 25; i++) {
        var p = document.createElement('div');
        p.className = 'particle';
        var size = Math.random() * 4 + 2;
        p.style.cssText = [
            'width:' + size + 'px',
            'height:' + size + 'px',
            'left:' + Math.random() * 100 + '%',
            'background:' + colours[Math.floor(Math.random()*colours.length)],
            'box-shadow: 0 0 ' + (size*3) + 'px ' + colours[Math.floor(Math.random()*colours.length)],
            '--dur:' + (Math.random()*12+8) + 's',
            '--delay:' + (Math.random()*10) + 's',
        ].join(';');
        cont.appendChild(p);
    }
})();
</script>
""", unsafe_allow_html=True)


# ── Session state initialisation ───────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id: Optional[str] = None
if "messages" not in st.session_state:
    st.session_state.messages: list[dict] = []
if "turn" not in st.session_state:
    st.session_state.turn = 0


# ── Helper: call backend ───────────────────────────────────────────────────
def send_message(user_text: str) -> dict:
    payload = {
        "message": user_text,
        "session_id": st.session_state.session_id,
    }
    resp = requests.post(f"{API_BASE}/chat", json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()


def reset_session() -> None:
    if st.session_state.session_id:
        try:
            requests.post(
                f"{API_BASE}/chat/reset",
                json={"session_id": st.session_state.session_id},
                timeout=10,
            )
        except Exception:  # noqa: BLE001
            pass
    st.session_state.session_id = None
    st.session_state.messages = []
    st.session_state.turn = 0


def get_docs_status() -> dict:
    try:
        r = requests.get(f"{API_BASE}/docs-status", timeout=5)
        return r.json()
    except Exception:  # noqa: BLE001
        return {"collection_count": 0, "vectorstore_path": "—"}


def trigger_ingest(reset: bool = False) -> dict:
    try:
        r = requests.post(
            f"{API_BASE}/ingest", json={"reset": reset}, timeout=120
        )
        return r.json()
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:

    # Logo / branding
    st.markdown("""
    <div class="sidebar-logo">
        <div class="icon-ring">⚡</div>
        <div class="app-title">IoT Troubleshooter</div>
        <div class="app-sub">Powered by Groq AI + RAG</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ── Knowledge base status ──────────────────────────────────────────
    status = get_docs_status()
    chunks = status.get("collection_count", 0)

    if chunks > 0:
        st.markdown(f"""
        <div class="glass-card">
            <div class="glass-card-title">📚 Knowledge Base</div>
            <div class="chunk-badge">
                <span class="status-dot"></span>
                {chunks} chunks indexed
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="glass-card">
            <div class="glass-card-title">📚 Knowledge Base</div>
            <div class="chunk-badge chunk-badge-warn">
                <span class="status-dot offline"></span>
                No docs indexed yet
            </div>
        </div>
        """, unsafe_allow_html=True)

    col_ingest, col_reset = st.columns(2)
    with col_ingest:
        if st.button("⬆ Ingest", use_container_width=True):
            with st.spinner("Ingesting…"):
                result = trigger_ingest(reset=False)
            if "error" in result:
                st.error(result["error"])
            else:
                st.success(f"✓ {result.get('chunks_indexed','?')} chunks")
                st.rerun()

    with col_reset:
        if st.button("♻ Rebuild", use_container_width=True):
            with st.spinner("Rebuilding…"):
                result = trigger_ingest(reset=True)
            if "error" in result:
                st.error(result["error"])
            else:
                st.success(f"✓ {result.get('chunks_indexed','?')} chunks")
                st.rerun()

    # ── Upload a document ──────────────────────────────────────────────
    st.markdown('<div class="glass-card-title" style="margin-top:14px;font-size:11px;font-weight:600;letter-spacing:1.2px;text-transform:uppercase;color:rgba(255,255,255,0.35);">📤 Upload Document</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader(
        "Upload a manual, guide, or error-code reference",
        type=["pdf", "txt", "md", "html"],
        label_visibility="collapsed",
    )
    if uploaded and st.button("⬆ Upload & Index", use_container_width=True):
        with st.spinner("Uploading & indexing…"):
            files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type)}
            try:
                r = requests.post(
                    f"{API_BASE}/ingest/upload", files=files, timeout=120
                )
                data = r.json()
                if r.ok:
                    st.success(f"✓ {data.get('chunks_indexed','?')} chunks from {data.get('file')}")
                    st.rerun()
                else:
                    st.error(data.get("detail", "Unknown error"))
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))

    st.divider()

    # ── Session controls ───────────────────────────────────────────────
    if st.session_state.session_id:
        st.markdown(f"""
        <div class="glass-card">
            <div class="glass-card-title">💬 Session</div>
            <div class="session-info">ID: {st.session_state.session_id[:8]}…</div>
            <div class="session-info">Turns: {st.session_state.turn}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="glass-card">
            <div class="glass-card-title">💬 Session</div>
            <div class="session-info" style="color:rgba(255,255,255,0.2);">No active session</div>
        </div>
        """, unsafe_allow_html=True)

    if st.button("🗑 New Conversation", use_container_width=True):
        reset_session()
        st.rerun()

    st.divider()
    st.markdown(f"""
    <div style="text-align:center;font-size:11px;color:rgba(255,255,255,0.2);line-height:1.8;">
        IoT Troubleshooter v1.0<br>
        <span style="font-family:'JetBrains Mono',monospace;">{API_BASE}</span>
    </div>
    """, unsafe_allow_html=True)


# ── Main chat area ─────────────────────────────────────────────────────────
st.markdown("""
<div class="page-header">
    <div class="header-glow"></div>
    <h1>⚡ IoT Troubleshooter</h1>
    <p>AI-powered diagnostics grounded in your device documentation</p>
</div>
""", unsafe_allow_html=True)

# Welcome message
if not st.session_state.messages:
    st.markdown("""
    <div class="welcome-card">
        <div class="welcome-title">👋 Welcome — let's fix your device</div>
        <div class="welcome-sub">
            Describe your IoT device and the problem you're experiencing.<br>
            I'll ask clarifying questions and walk you through a diagnosis with step-by-step guidance grounded in your documentation.
        </div>
        <div>
            <span class="example-chip">🔴 Hue bridge solid red light</span>
            <span class="example-chip">📡 Zigbee sensors dropping off</span>
            <span class="example-chip">📶 Smart thermostat WiFi timeout</span>
            <span class="example-chip">🔌 Smart plug disconnects every few minutes</span>
            <span class="example-chip">🔄 Firmware update stuck at 90%</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Render conversation history
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f"""
        <div class="msg-row user-row">
            <div class="avatar user-av">👤</div>
            <div class="user-bubble">{msg["content"]}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="msg-row bot-row">
            <div class="avatar bot-av">🤖</div>
            <div class="bot-bubble">{msg["content"]}</div>
        </div>
        """, unsafe_allow_html=True)

        sources = msg.get("sources", [])
        if sources:
            tags = "".join(
                f'<span class="source-tag">📄 {s}</span>' for s in sources
            )
            st.markdown(
                f'<div class="sources-row"><span class="rag-label">📡 Sources:</span>{tags}</div>',
                unsafe_allow_html=True,
            )
        elif msg.get("retrieval_used") is False:
            st.markdown(
                '<div class="no-rag-badge">⚠ No doc match — reasoning from general knowledge</div>',
                unsafe_allow_html=True,
            )

# ── Input ──────────────────────────────────────────────────────────────────
st.markdown('<div class="input-glass">', unsafe_allow_html=True)
with st.form("chat_form", clear_on_submit=True):
    user_input = st.text_area(
        "Message",
        placeholder="e.g. My smart plug connects but keeps disconnecting every few minutes…",
        height=80,
        label_visibility="collapsed",
    )
    submitted = st.form_submit_button("⚡ Send Message", use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

if submitted and user_input.strip():
    st.session_state.messages.append({"role": "user", "content": user_input.strip()})

    with st.spinner(""):
        st.markdown("""
        <div class="msg-row bot-row" style="margin:8px 0;">
            <div class="avatar bot-av">🤖</div>
            <div class="bot-bubble" style="padding:14px 20px;">
                <div class="typing-dots">
                    <span></span><span></span><span></span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        try:
            data = send_message(user_input.strip())
        except requests.exceptions.ConnectionError:
            st.error(
                f"Cannot reach the backend API. Make sure it's running at `{API_BASE}`."
            )
            st.stop()
        except Exception as exc:  # noqa: BLE001
            st.error(f"Error: {exc}")
            st.stop()

    st.session_state.session_id = data.get("session_id")
    st.session_state.turn = data.get("turn", 0)

    st.session_state.messages.append({
        "role": "assistant",
        "content": data.get("answer", ""),
        "sources": data.get("sources", []),
        "retrieval_used": data.get("retrieval_used", False),
    })

    st.rerun()
