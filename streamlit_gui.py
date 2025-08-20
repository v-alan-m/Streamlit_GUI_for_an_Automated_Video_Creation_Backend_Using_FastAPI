# app.py — Streamlit GUI with pastel gradient background, transparent cards,
# step highlighting (green/red), no scrollbars inside cards, centered badge,
# custom green progress bar, Start/Stop/Reset controls, and live logs.

import time
from datetime import datetime, timedelta
import streamlit as st

# -----------------------------
# Page config
# -----------------------------
st.set_page_config(page_title="Workflow Monitor", layout="wide")

# -----------------------------
# Pastel blurred background + component styles
# -----------------------------
st.markdown(
    """
    <style>
    /* ========== Pastel background ========== */
    .stApp {
        background:
          radial-gradient(60% 50% at 10% 10%, rgba(255, 235, 120, 0.55), transparent 60%),
          radial-gradient(60% 50% at 90% 15%, rgba(255, 140, 220, 0.45), transparent 60%),
          radial-gradient(60% 50% at 20% 85%, rgba(120, 255, 200, 0.45), transparent 60%),
          radial-gradient(60% 50% at 85% 85%, rgba(120, 200, 255, 0.45), transparent 60%),
          #0f1420;
    }

    /* ========== Global typography (keeps it clean & readable) ========== */
    html, body, [class*="css"] {
        font-family: "Segoe UI", Inter, system-ui, -apple-system, Arial, sans-serif;
        color: #E1E6EE;
    }

    /* ========== Transparent cards (50% opacity fills) ========== */
    .card {
        background: rgba(30, 38, 50, 0.50);
        border: 1px solid rgba(85, 102, 130, 0.85);
        border-radius: 12px;
        padding: 16px 20px;
        overflow: hidden;            /* no internal scrollbars */
    }
    .card.done  { background: rgba(24,151,78,0.50);  border-color: rgba(24,151,78,1); box-shadow: 0 0 0 2px rgba(24,151,78,0.35) inset; }
    .card.error { background: rgba(200,60,60,0.50); border-color: rgba(200,60,60,1); box-shadow: 0 0 0 2px rgba(200,60,60,0.35) inset; }

    .card-title { font-weight: 600; letter-spacing: .2px; }

    /* status dot */
    .dot { font-weight: 900; margin-right: 6px; color: #828A96; }
    .dot.done { color: rgb(24,151,78); }

    /* Badge: center text inside pill */
    .badge {
        display: inline-block;
        min-width: 90px;
        padding: 6px 12px;
        text-align: center;
        border-radius: 999px;
        font-weight: 600;
        background: #46505F;
        color: #fff;
    }
    .badge.running { background: rgb(24,151,78); }
    .badge.error   { background: rgb(200,60,60); }

    /* ========== Custom progress bar (full width, green) ========== */
    .progress-wrap {
        width: 100%;
        background: rgba(38,46,60,0.65);
        border-radius: 10px;
        height: 28px;
        position: relative;
        overflow: hidden;
        border: 1px solid rgba(85, 102, 130, 0.6);
    }
    .progress-bar {
        height: 100%;
        width: 0%;
        background: rgb(24,151,78);
        transition: width .12s linear;
    }
    .progress-label {
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        display: flex; align-items: center; justify-content: center;
        font-weight: 600; color: #E1E6EE;
        text-shadow: 0 1px 2px rgba(0,0,0,.35);
    }

    /* ========== Logs ========== */
    .logs {
        height: 260px;
        overflow: auto;                     /* keep scrollbar only here */
        background: rgba(30, 38, 50, 0.55);
        border: 1px solid rgba(85, 102, 130, 0.85);
        border-radius: 12px;
        padding: 12px 14px;
        font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
        font-size: 13px;
        line-height: 1.45;
    }
    .log-info {}
    .log-success { color: rgb(24,151,78); }
    .log-error   { color: rgb(220,70,70); }

    /* small section headings */
    .section-title { margin-top: 4px; margin-bottom: 8px; opacity: .95; font-weight: 600; }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# App state (session)
# -----------------------------
if "running" not in st.session_state:
    st.session_state.running = False
    st.session_state.stop_flag = False
    st.session_state.start_time = None
    st.session_state.step_index = 0
    st.session_state.step_started = None
    st.session_state.progress = 0.0
    st.session_state.logs = []
    st.session_state.step_states = ["idle", "idle", "idle"]  # per step: idle/done/error
    st.session_state.error = False

# Steps config
STEPS = [
    {"title": "Story Creation",   "desc": "Generating story using ChatGPT API…",   "duration": 3.0},
    {"title": "Video Generation", "desc": "Automating 3rd-party web app…",        "duration": 3.0},
    {"title": "File Download",    "desc": "Downloading completed video file…",     "duration": 3.0},
]

# -----------------------------
# Helpers
# -----------------------------
def add_log(level: str, msg: str):
    st.session_state.logs.append((level, msg))

def start():
    if st.session_state.running:
        return
    st.session_state.running = True
    st.session_state.stop_flag = False
    st.session_state.error = False
    st.session_state.start_time = datetime.now()
    st.session_state.step_index = 0
    st.session_state.step_started = datetime.now()
    st.session_state.progress = 0.0
    st.session_state.step_states = ["idle", "idle", "idle"]
    st.session_state.logs = []
    add_log("info", "Initializing ChatGPT API connection")
    add_log("info", "Sending story generation prompt")

def stop():
    st.session_state.stop_flag = True
    st.session_state.running = False
    add_log("info", "Pipeline stopped by user")

def reset():
    st.session_state.running = False
    st.session_state.stop_flag = False
    st.session_state.error = False
    st.session_state.start_time = None
    st.session_state.step_index = 0
    st.session_state.step_started = None
    st.session_state.progress = 0.0
    st.session_state.logs = []
    st.session_state.step_states = ["idle", "idle", "idle"]

def tick():
    """Advance simulation one tick while running."""
    if not st.session_state.running or st.session_state.stop_flag or st.session_state.error:
        return

    idx = st.session_state.step_index
    if idx >= len(STEPS):
        st.session_state.running = False
        add_log("success", "Workflow completed.")
        return

    step = STEPS[idx]
    elapsed = (datetime.now() - st.session_state.step_started).total_seconds()
    step_pct = min(1.0, elapsed / step["duration"])

    # overall progress
    st.session_state.progress = (idx + step_pct) / len(STEPS)

    # on first loop of a step, log the step start
    if abs(elapsed - 0.0) < 0.15:
        add_log("info", f'Step {idx+1}/{len(STEPS)}: {step["desc"]}')

    # step finished
    if step_pct >= 1.0:
        st.session_state.step_states[idx] = "done"
        add_log("success", f'{step["title"]} completed.')
        st.session_state.step_index += 1
        if st.session_state.step_index < len(STEPS):
            st.session_state.step_started = datetime.now()
        else:
            st.session_state.running = False
            add_log("success", "Workflow completed.")

# -----------------------------
# Header row (Status / Timing / Progress summary)
# -----------------------------
col_status, col_timing, col_prog = st.columns([3, 4, 3], gap="small")

with col_status:
    st.markdown('<div class="section-title">Status</div>', unsafe_allow_html=True)
    status_text = "Running" if st.session_state.running else ("Error" if st.session_state.error else "Idle")
    badge_class = "badge running" if st.session_state.running else ("badge error" if st.session_state.error else "badge")
    st.markdown(
        f"""
        <div class="card">
          <div style="display:flex;align-items:center;gap:12px;">
            <div style="opacity:.8;">Current:</div>
            <div style="font-weight:600">{status_text}</div>
            <span class="{badge_class}">{status_text}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_timing:
    st.markdown('<div class="section-title">Timing</div>', unsafe_allow_html=True)
    started = st.session_state.start_time.strftime("%H:%M:%S") if st.session_state.start_time else "--:--:--"
    if st.session_state.start_time:
        delta = datetime.now() - st.session_state.start_time
        duration_text = "less than a minute" if delta < timedelta(minutes=1) else f"{int(delta.total_seconds()//60)} min"
    else:
        duration_text = "—"
    st.markdown(
        f"""
        <div class="card">
            <div style="display:flex;gap:10px;">
                <div>Started</div><div>{started}</div>
            </div>
            <div style="display:flex;gap:10px;margin-top:6px;">
                <div>Duration</div><div>{duration_text}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_prog:
    st.markdown('<div class="section-title">Progress</div>', unsafe_allow_html=True)
    steps_str = f'{sum(1 for s in st.session_state.step_states if s=="done")}/{len(STEPS)}'
    st.markdown(
        f"""
        <div class="card">
            <div style="display:flex;gap:8px;">
                <div>{steps_str}</div><div>Steps Completed</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# -----------------------------
# Controls
# -----------------------------
st.markdown('<div class="section-title">Workflow Controls</div>', unsafe_allow_html=True)
c1, c2, c3 = st.columns([2, 1.2, 1.2])
with c1:
    if st.button("Start Workflow", type="primary", use_container_width=True):
        start()
with c2:
    if st.button("Stop", use_container_width=True):
        stop()
with c3:
    if st.button("Reset", use_container_width=True):
        reset()

# -----------------------------
# Progress Tracker (custom progress bar)
# -----------------------------
st.markdown('<div class="section-title">Progress Tracker</div>', unsafe_allow_html=True)
pct = int(st.session_state.progress * 100)
st.markdown(
    f"""
    <div class="progress-wrap">
        <div class="progress-bar" style="width:{pct}%;"></div>
        <div class="progress-label">{pct}%</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Workflow Steps (3 cards, no scrollbars; equal paddings)
# -----------------------------
st.markdown('<div class="section-title" style="margin-top:12px;">WORKFLOW STEPS</div>', unsafe_allow_html=True)
s1, s2, s3 = st.columns(3, gap="small")
cards = [s1, s2, s3]

for i, step in enumerate(STEPS):
    state = st.session_state.step_states[i]
    card_cls = "card" if state == "idle" else ("card done" if state == "done" else "card error")
    dot_cls = "dot" if state == "idle" else "dot done"
    with cards[i]:
        st.markdown(
            f"""
            <div class="{card_cls}">
              <div style="display:flex;align-items:center;gap:8px;">
                <span class="{dot_cls}">●</span>
                <span class="card-title">{step["title"]}</span>
              </div>
              <div style="height:8px;"></div>
              <div>{step["desc"]}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# -----------------------------
# Logs (scrollable)
# -----------------------------
st.markdown('<div class="section-title" style="margin-top:12px;">Live Logs</div>', unsafe_allow_html=True)
log_lines = []
for level, msg in st.session_state.logs[-400:]:
    cls = "log-info" if level == "info" else ("log-success" if level == "success" else "log-error")
    ts = datetime.now().strftime("%H:%M:%S")
    log_lines.append(f'<div class="{cls}">{ts}  {level.upper():7s} | {msg}</div>')

st.markdown(
    f"""<div class="logs">{''.join(log_lines) or '&nbsp;'}</div>""",
    unsafe_allow_html=True,
)

# -----------------------------
# Simulation tick & rerun loop
# -----------------------------
if st.session_state.running and not st.session_state.stop_flag and not st.session_state.error:
    tick()
    # small sleep to create a smooth loop, then rerun
    time.sleep(0.06)
    st.rerun()
