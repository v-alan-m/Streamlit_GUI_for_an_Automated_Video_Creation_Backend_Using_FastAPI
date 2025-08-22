# app.py — Python Workflow Monitor (Streamlit)
# - Group boxes back (robust): :has(#controls-anchor) and :has(#steps-anchor)
# - Transparent global wrapper (no giant outer box)
# - Buttons with state-aware colors; no hover lightening
# - Step cards centered (no bullets), green on completion
# - Logs as cards: level pill + centered timestamp (no bullets)
# - Even padding in group boxes; sleek darker pastel background

import time
from datetime import datetime, timedelta
from html import escape
import streamlit as st
from streamlit.components.v1 import html as st_html
from streamlit_extras.stylable_container import stylable_container

st.set_page_config(page_title="Python Workflow Monitor", layout="wide")

# =========================
# CSS
# =========================
st.markdown("""
<style>
/* ===== Sleek, darker pastel background ===== */
.stApp {
  background:
    radial-gradient(130% 100% at 0%   0%,   rgba(255,255,255,0.14) 0%, rgba(255,255,255,0.06) 40%, rgba(255,255,255,0.00) 62%),
    radial-gradient(130% 100% at 100% 0%,   rgba(255,255,255,0.14) 0%, rgba(255,255,255,0.06) 40%, rgba(255,255,255,0.00) 62%),
    radial-gradient(120% 80% at 82% 18%,    rgba(186,144,213,0.30), rgba(186,144,213,0.00) 62%),
    radial-gradient(120% 80% at 25% 30%,    rgba(121,181,233,0.28), rgba(121,181,233,0.00) 62%),
    radial-gradient(120% 80% at 30% 78%,    rgba(110,231,183,0.22), rgba(110,231,183,0.00) 62%),
    #141b24;
  background-attachment: fixed;
}

/* ===== Global variables =====
   - Set --page-frame-* to 0 to remove Streamlit's inner frame
   - Use --shell-* to control the faint wrapper that sometimes 'frames' everything */
:root{
  --page-frame-bg: rgba(20,26,36,0.00);   /* background fill of the big outer box */
  --page-frame-br: rgba(85,102,130,0.00); /* border color of the big outer box   */
  --page-frame-radius: 16px;              /* corner radius                       */

  --shell-bg:    rgba(20,26,36,0.00);     /* 0 = invisible, e.g. 0.35 to show    */
  --shell-br:    rgba(85,102,130,0.00);   /* 0 = no border                       */
  --shell-radius: 16px;                   /* corner radius                       */
  --shell-pad:    0px;                    /* extra inner padding if wanted       */

  --btn-height: 80px;
  --btn-font:   16px;
  --btn-radius: 17px;
  --btn-hpad: 18px;

  --pb-height:  35px;
  --pb-radius:  13px;
  --pb-font:    14px;
  
  --step-done-bg: rgba(64,137,238,.62);   /* nice, saturated blue with a little transparency */
  --step-done-br: rgb(64,137,238);        /* solid border color for the edge */
  --step-error-bg: rgba(200,60,60,0.60);   /* nice, saturated blue with a little transparency */
  --step-error-br: rgb(200,60,60,1);        /* solid border color for the edge */
  
  --group-pad-y: 28px;
  --group-pad-x: 32px;
  --group-bottom-extra: 8px; /* 0 to remove */
}

/* ===== Neutralize Streamlit's default frames ===== */
div[data-testid="stAppViewContainer"],
div[data-testid="stMain"]{
  background: transparent !important;
  box-shadow: none !important;
}
.block-container{
  background: var(--page-frame-bg) !important;
  border: 1px solid var(--page-frame-br) !important;
  border-radius: var(--page-frame-radius) !important;
  box-shadow: none !important;
}
section.main, section.main > div{
  background: transparent !important;
  box-shadow: none !important;
  border: 0 !important;
}
/* Reset ALL Streamlit blocks to transparent by default */
div[data-testid="stVerticalBlock"] {
  background: transparent !important;
  border: 0 !important;
  box-shadow: none !important;
}

/* ===== PAGE SHELL — anchored by #page-shell-anchor =====
   Target ONLY the direct child block of .block-container that contains our anchor. */
div[data-testid="stAppViewContainer"] .block-container
  > div[data-testid="stVerticalBlock"]:has(#page-shell-anchor) {
  background: var(--shell-bg) !important;
  border: 1px solid var(--shell-br) !important;
  border-radius: var(--shell-radius) !important;
  padding: var(--shell-pad) !important;
  box-shadow: none !important;
}

/* ===== Base type & titles ===== */
html, body, [class*="css"] { font-family: "Segoe UI", Inter, system-ui, -apple-system, Arial, sans-serif; color: #e9eef7; }
.page-title    { text-align:center; margin: 10px 0 6px 0; font-weight: 900; font-size: 40px; letter-spacing: .2px; color:#ffffff; }
.page-sub      { text-align:center; margin-bottom: 18px; font-weight: 800; font-size: 26px; color:#cfd6df; }
.section-title { margin: 18px 0 8px 0; font-weight: 800; font-size: 22px; color:#ffffff; }
.section-title.center { text-align:center; }

/* ===== Group boxes (ONLY for the two sections we want) =====
   Important: These come AFTER the global reset so they win. */
div[data-testid="stVerticalBlock"]:has(#controls-anchor),
div[data-testid="stVerticalBlock"]:has(#steps-anchor) {
  background: rgba(20,26,36,0.50) !important;
  border: 1px solid rgba(85,102,130,0.40) !important;
  border-radius: 17px !important;
  padding: var(--group-pad-y) var(--group-pad-x) !important;
}
/* Equalize visual padding (kill stray inner margins) */
div[data-testid="stVerticalBlock"]:has(#controls-anchor) > div:first-child,
div[data-testid="stVerticalBlock"]:has(#steps-anchor)    > div:first-child { margin-top: 0 !important; }
div[data-testid="stVerticalBlock"]:has(#controls-anchor) > div:last-child,
div[data-testid="stVerticalBlock"]:has(#steps-anchor)    > div:last-child  { margin-bottom: 0 !important; }
/* Tiny bottom spacer to make bottom match top visually */
div[data-testid="stVerticalBlock"]:has(#controls-anchor)::after,
div[data-testid="stVerticalBlock"]:has(#steps-anchor)::after {
  content: ""; display:block; height: var(--group-bottom-extra);
}

/* ===== Cards ===== */
.card {
  background: rgba(26,34,45,0.78);
  border: 1px solid rgba(95,110,132,0.50);
  border-radius: 14px;
  padding: 18px 20px;
  color: #e8eef7;
}
.card.top { min-height: 120px; display:flex; align-items:center; justify-content:center; text-align:center; }
.card.done{
  background: var(--step-done-bg);
  border-color: var(--step-done-br);
  color:#fff;
  }
.card.error{
  background: var(--step-error-bg);
  border-color: var(--step-error-br);
  color:#fff;
}

/* ===== Step cards (centered, no bullets) ===== */
.step-card  { text-align:center; padding: 17px; }
.step-title { font-weight: 800; letter-spacing: .2px; display:block; margin-bottom:6px; }
.step-desc  { opacity:.53; }

/* ===== Status badge ===== */
.badge { display:inline-block; min-width: 98px; padding: 6px 12px; border-radius: 999px; font-weight: 800; color:#fff; }
.badge.idle    { background:#46505F; }
.badge.running { background: rgb(24,151,78); }
.badge.error   { background: rgb(200,60,60); }

/* ===== Progress bar ===== */
.progress-wrap {
  width: 100%;
  background: rgba(38,46,60,0.62);
  border: 1px solid rgba(85,102,130,0.72);
  border-radius: 10px;
  position: relative;
  overflow: hidden;
  color:#fff;
  margin: 6px 0;
}
.progress-bar   { height:100%; width:0%; background: rgb(24,151,78); transition: width .12s linear; }
.progress-label { position:absolute; inset:0; display:flex; align-items:center; justify-content:center; font-weight:800; }

/* ===== Size knobs ===== */
/* Buttons use the central knobs (IDs are your stylable_container ids) */
#btn-start button,
#btn-stop  button,
#btn-reset button,
#btn-start [data-testid="baseButton-primary"],
#btn-start [data-testid="baseButton-secondary"],
#btn-stop  [data-testid="baseButton-primary"],
#btn-stop  [data-testid="baseButton-secondary"],
#btn-reset [data-testid="baseButton-primary"],
#btn-reset [data-testid="baseButton-secondary"]{
  height: var(--btn-height) !important;
  min-height: var(--btn-height) !important;   /* belt & suspenders */
  padding: 0 var(--btn-hpad) !important;      /* vertical size now driven by height */
  font-size: var(--btn-font) !important;
  border-radius: var(--btn-radius) !important;
  line-height: 1 !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
}

/* Progress bar uses the central knobs */
.progress-wrap  { height: var(--pb-height) !important; border-radius: var(--pb-radius) !important; }
.progress-bar   { border-radius: var(--pb-radius) !important; }
.progress-label { font-size: var(--pb-font) !important; font-weight: 800; }
</style>
""", unsafe_allow_html=True)

# =========================
# Session state
# =========================
if "running" not in st.session_state:
    st.session_state.running = False
    st.session_state.stop_flag = False
    st.session_state.error = False
    st.session_state.start_time = None
    st.session_state.step_index = 0
    st.session_state.step_started = None
    st.session_state.progress = 0.0
    st.session_state.logs = []
    st.session_state.step_states = ["idle", "idle", "idle"]

STEPS = [
    {"title": "Story Creation", "desc": "Generating story using ChatGPT API", "duration": 3.0},
    {"title": "Video Generation", "desc": "Automating 3rd-party web app", "duration": 3.0},
    {"title": "File Download", "desc": "Downloading completed video file", "duration": 3.0},
]


# =========================
# Helpers
# =========================
def add_log(level: str, msg: str):
    st.session_state.logs.append((datetime.now().strftime("%H:%M:%S"), level, msg))


def start():
    if st.session_state.running: return
    st.session_state.running = True
    st.session_state.stop_flag = False
    st.session_state.error = False
    st.session_state.start_time = datetime.now()
    st.session_state.step_index = 0
    st.session_state.step_started = datetime.now()
    st.session_state.progress = 0.0
    st.session_state.step_states = ["idle", "idle", "idle"]
    st.session_state.logs = []
    add_log("INFO", "Initializing ChatGPT API connection")
    add_log("INFO", "Sending story generation prompt")


def stop():
    st.session_state.stop_flag = True
    st.session_state.running = False
    add_log("INFO", "Pipeline stopped by user")


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
    if not st.session_state.running or st.session_state.stop_flag or st.session_state.error:
        return
    idx = st.session_state.step_index
    if idx >= len(STEPS):
        st.session_state.running = False
        add_log("SUCCESS", "Workflow completed.")
        return

    step = STEPS[idx]
    elapsed = (datetime.now() - st.session_state.step_started).total_seconds()
    step_pct = min(1.0, elapsed / step["duration"])
    st.session_state.progress = (idx + step_pct) / len(STEPS)

    if abs(elapsed) < 0.12:
        add_log("INFO", f"Step {idx + 1}/{len(STEPS)}: {step['desc']}")

    if step_pct >= 1.0:
        st.session_state.step_states[idx] = "done"
        add_log("SUCCESS", f"{step['title']} completed.")
        st.session_state.step_index += 1
        if st.session_state.step_index < len(STEPS):
            st.session_state.step_started = datetime.now()
        else:
            st.session_state.running = False
            add_log("SUCCESS", "Workflow completed.")


# =========================
# Title
# =========================
st.markdown('<div class="page-title">StoryMorph: Story Creation + Automated Video Generation</div>',
            unsafe_allow_html=True)
st.markdown('<div class="page-sub">"From Imagination to Animation — Fully Automated -> Ready for Social Media!"</div>',
            unsafe_allow_html=True)

# >>> Shell anchor (controls the subtle outer wrapper via --shell-*) <<<
st.markdown('<div id="page-shell-anchor"></div>', unsafe_allow_html=True)

# =========================
# Top row (Status & Timing)
# =========================
col_status, col_timing = st.columns(2, gap="small")
with col_status:
    st.markdown('<div class="section-title center">Status</div>', unsafe_allow_html=True)
    status_text = "Running" if st.session_state.running else ("Error" if st.session_state.error else "Idle")
    badge_class = "badge running" if st.session_state.running else (
        "badge error" if st.session_state.error else "badge idle")
    st.markdown(f"""
        <div class="card top">
          <div>
            <div style="opacity:.85; margin-bottom:8px;">Current</div>
            <span class="{badge_class}">{status_text}</span>
          </div>
        </div>
    """, unsafe_allow_html=True)

with col_timing:
    st.markdown('<div class="section-title center">Timing</div>', unsafe_allow_html=True)
    started = st.session_state.start_time.strftime("%H:%M:%S") if st.session_state.start_time else "--:--:--"
    if st.session_state.start_time:
        delta = datetime.now() - st.session_state.start_time
        duration_text = "less than a minute" if delta < timedelta(
            minutes=1) else f"{int(delta.total_seconds() // 60)} min"
    else:
        duration_text = "—"
    st.markdown(f"""
        <div class="card top">
          <div>
            <div style="margin-bottom:6px;">Started &nbsp; <span style="opacity:.9">{started}</span></div>
            <div>Duration &nbsp; <span style="opacity:.9">{duration_text}</span></div>
          </div>
        </div>
    """, unsafe_allow_html=True)

# =========================
# Workflow Controls + Progress (group box)
# =========================
st.markdown('<div class="section-title">Workflow Controls</div>', unsafe_allow_html=True)
with st.container():
    st.markdown('<div id="controls-anchor"></div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns([2, 2, 2], gap="small")

    # --- START (green / dim green when disabled) ---
    with c1:
        with stylable_container(
                "btn-start",
                css_styles="""
                button {
                    background: #05472A !important;        /* green */
                    border: 1px solid #158e4e !important;
                    color: #ffffff !important; font-weight: 800;
                    box-shadow: none !important;
                }
                button:disabled {
                    background: #126c3e !important;   /* slightly darker than current #157a46 */
                    border-color: #0f5b33 !important;
                    color: #d9f3e5 !important;
                    opacity: 0.92 !important;
                }
                button:hover { filter: none !important; }
            """,
        ):
            if st.button("Start Workflow", key="btn_start", use_container_width=True,
                         disabled=st.session_state.running):
                start()

    # --- STOP (red / dim red when disabled) ---
    with c2:
        with stylable_container(
                "btn-stop",
                css_styles="""
                button {
                    background: #b43838 !important;         /* red */
                    border: 1px solid #9b3232 !important;
                    color: #ffffff !important; font-weight: 800;
                    box-shadow: none !important;
                }
                button:disabled {
                    background: #5f2020 !important;   /* darker than current #7a2a2a */
                    border-color: #4e1a1a !important;
                    color: #f2dede !important;
                    opacity: 0.92 !important;
                }
                button:hover { filter: none !important; }
            """,
        ):
            if st.button("Stop", key="btn_stop", use_container_width=True,
                         disabled=not st.session_state.running):
                stop()

    # --- RESET (black / dim black when disabled) ---
    with c3:
        with stylable_container(
                "btn-reset",
                css_styles="""
                button {
                    background: #0f141b !important;          /* black */
                    border: 1px solid #323c4a !important;
                    color: #eaeef6 !important; font-weight: 800;
                    box-shadow: none !important;
                }
                button:disabled {
                    background: #0b0f15 !important;          /* dimmed black */
                    border-color: #2a3340 !important;
                    color: #9aa3ad !important;
                    opacity: 0.9 !important;
                }
                button:hover { filter: none !important; }
            """,
        ):
            if st.button("Reset", key="btn_reset", use_container_width=True,
                         disabled=st.session_state.running):
                reset()

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # Progress (unchanged)
    st.markdown('<div class="section-title" style="margin: 2px 0 8px 0;">Progress Tracker</div>',
                unsafe_allow_html=True)
    pct = int(st.session_state.progress * 100)
    st.markdown(f"""
        <div class="progress-wrap">
          <div class="progress-bar" style="width:{pct}%;"></div>
          <div class="progress-label">{pct}%</div>
        </div>
    """, unsafe_allow_html=True)

# =========================
# WORKFLOW STEPS (group box)
# =========================
st.markdown('<div class="section-title">WORKFLOW STEPS</div>', unsafe_allow_html=True)
with st.container():
    st.markdown('<div id="steps-anchor"></div>', unsafe_allow_html=True)

    s1, s2, s3 = st.columns(3, gap="small")
    for i, col in enumerate((s1, s2, s3)):
        step = STEPS[i]
        state = st.session_state.step_states[i]
        card_cls = "card step-card" if state == "idle" else (
            "card step-card done" if state == "done" else "card step-card error")
        with col:
            st.markdown(f"""
                <div class="{card_cls}">
                  <span class="step-title">{step["title"]}</span>
                  <div class="step-desc">{step["desc"]}</div>
                </div>
            """, unsafe_allow_html=True)

# =========================
# Live Logs (iframe; no bullets; timestamp centered under pill)
# =========================
st.markdown('<div class="section-title">Live Logs</div>', unsafe_allow_html=True)

entries = []
for ts, level, msg in st.session_state.logs[-400:]:
    klass = "success" if level == "SUCCESS" else ("error" if level == "ERROR" else "")
    pill = " success" if klass == "success" else (" error" if klass == "error" else "")
    entries.append(
        f'''
        <div class="lg-card {klass}">
          <div class="lg-pod">
            <div class="lg-pill{pill}">{escape(level)}</div>
            <div class="lg-time">{escape(ts)}</div>
          </div>
          <div class="lg-msg">{escape(msg)}</div>
        </div>
        '''
    )

logs_html = f"""
<style>
.lg-panel {{
  background: rgba(20,26,36,0.50);
  border: 1px solid rgba(85,102,130,0.40);
  border-radius: 14px;
  padding: 16px;
}}
.lg-scroll {{ height: 400px; overflow:auto; padding:8px 2px 2px 2px; }}
.lg-grid   {{ display:grid; grid-auto-rows:min-content; row-gap:10px; }}

.lg-card {{
  background: rgba(26,34,45,0.78);
  border: 1px solid rgba(95,110,132,0.50);
  border-radius: 10px;
  padding: 12px 16px;
  display:grid; grid-template-columns: 110px 1fr; gap:12px; align-items:center;
  color:#e8eef7; font-family: "Segoe UI", Inter, system-ui, -apple-system, Arial, sans-serif;
}}
.lg-card.success {{ border-color: rgba(24,151,78,1); }}
.lg-card.error   {{ border-color: rgba(220,70,70,1); }}

/* Pill + centered timestamp below (no bullets anywhere) */
.lg-pod {{ display:flex; flex-direction:column; align-items:center; gap:4px; }}
.lg-pill {{ display:inline-block; text-align:center; padding:3px 12px; border-radius:999px; font-weight:800; font-size:12px; background:#2a3342; color:#a8c1ff; }}
.lg-pill.success {{ background: rgba(24,151,78,.15); color: rgb(24,151,78); }}
.lg-pill.error   {{ background: rgba(220,70,70,.15); color: rgb(220,70,70); }}
.lg-time {{ font-size:12px; opacity:.85; }}

.lg-msg {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace; font-size: 17px; }}
</style>

<div class="lg-panel">
  <div class="lg-scroll">
    <div class="lg-grid">
      {''.join(entries)}
    </div>
  </div>
</div>
"""
st_html(logs_html, height=380, scrolling=False)

# =========================
# Sim loop
# =========================
if st.session_state.running and not st.session_state.stop_flag and not st.session_state.error:
    tick()
    time.sleep(0.06)
    st.rerun()
