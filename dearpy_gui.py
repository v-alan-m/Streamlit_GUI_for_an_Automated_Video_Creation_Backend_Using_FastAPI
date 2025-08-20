# workflow_monitor.py — Dear PyGui v2.x
# Gradient background (viewport), transparent main window (no_background),
# vertically centered status badge, aligned layout, step card states, v2-safe.

import math, time, threading, os
from queue import Queue, Empty
from datetime import datetime
import dearpygui.dearpygui as dpg

# ---------------- App state ----------------
state = {
    "running": False,
    "stop_flag": False,
    "start_time": None,
    "overall_progress": 0.0,
    "completed_steps": 0,
    "total_steps": 3,
    "fail_step": None,  # set to "video_generation" to simulate failure
}

# Layout
H_MARGIN = 30
COL_GAP = 10
TOP_COL_RATIOS = (0.30, 0.40, 0.30)

# ---------------- UI queue (v2-safe) ----------------
_UIQ: Queue = Queue()
def ui(fn, *a, **k): _UIQ.put((fn, a, k))
def _drain_ui(n=128):
    i=0
    while i<n:
        try: fn,a,k=_UIQ.get_nowait()
        except Empty: break
        try: fn(*a, **k)
        except Exception: pass
        i+=1

# ---------------- Gaussian gradient ----------------
def gen_soft_gradient_rgba(width=1024, height=640):
    width = int(width); height = int(height)
    seeds = [
        (0.20, 0.25, (1.00, 0.83, 0.35)),  # yellow
        (0.80, 0.25, (1.00, 0.60, 0.85)),  # pink
        (0.75, 0.70, (0.40, 0.80, 1.00)),  # aqua
        (0.35, 0.75, (0.40, 1.00, 0.70)),  # mint
        (0.10, 0.65, (1.00, 0.90, 0.70)),  # peach
    ]
    sigma = 0.35
    data=[]
    for y in range(height):
        fy = y/(height-1)
        for x in range(width):
            fx = x/(width-1)
            r=g=b=0.0; wsum=0.0
            for cx,cy,(cr,cg,cb) in seeds:
                dx=fx-cx; dy=fy-cy
                weight = math.exp(-(dx*dx+dy*dy)/(2*sigma*sigma))
                r+=cr*weight; g+=cg*weight; b+=cb*weight; wsum+=weight
            if wsum>0:
                inv=1.0/wsum; r*=inv; g*=inv; b*=inv
            # soft vignette
            d = math.hypot(fx-0.5, fy-0.5)
            v = (1 - 0.25*d)
            r*=v; g*=v; b*=v
            data.extend((r,g,b,1.0))
    return width, height, data

# ---------------- Logs + helpers ----------------
def _log_with_theme(msg, theme=None):
    ts = datetime.now().strftime("%H:%M:%S")
    def _do():
        item = dpg.add_text(f"{ts}  {msg}", parent="log_scroller")
        if theme: dpg.bind_item_theme(item, theme)
        try: dpg.set_y_scroll("log_region", dpg.get_y_scroll_max("log_region"))
        except Exception: pass
    ui(_do)

def log_info(msg):    _log_with_theme(msg, None)
def log_success(msg): _log_with_theme(msg, "THEME_LOG_SUCCESS")
def log_error(msg):   _log_with_theme(msg, "THEME_LOG_ERROR")

def set_status(x): ui(dpg.set_value, "status_label", x)  # hidden text (we use the badge)
def set_badge(text, running):
    def _do():
        dpg.configure_item("status_badge_btn", label=text)
        dpg.bind_item_theme("status_badge_btn", "THEME_BADGE_RUNNING_BTN" if running else "THEME_BADGE_IDLE_BTN")
    ui(_do)
def set_steps(): ui(dpg.set_value, "steps_counter", f"{state['completed_steps']}/{state['total_steps']}")
def set_progress():
    def _do():
        dpg.set_value("overall_progress_bar", state["overall_progress"])
        dpg.configure_item("overall_progress_bar", overlay=f"{int(state['overall_progress']*100)}%")
    ui(_do)
def set_controls(running):
    def _do():
        dpg.configure_item("btn_start", enabled=not running)
        dpg.configure_item("btn_stop",  enabled=running)
        dpg.bind_item_theme("btn_start", "THEME_START_DISABLED" if running else "THEME_START_ENABLED")
        dpg.bind_item_theme("btn_stop",  "THEME_STOP_ENABLED"  if running else "THEME_STOP_DISABLED")
    ui(_do)
def set_dot(tag, done): ui(dpg.bind_item_theme, f"{tag}_dot", "THEME_DOT_DONE" if done else "THEME_DOT_IDLE")
def set_card_state(tag, name):
    ui(dpg.bind_item_theme, f"{tag}_card",
       {"idle":"THEME_CARD_IDLE","done":"THEME_CARD_DONE","error":"THEME_CARD_ERROR"}.get(name,"THEME_CARD_IDLE"))
def set_timing():
    def _do():
        if not state["start_time"]:
            dpg.set_value("started_at","--:--:--"); dpg.set_value("duration_val","—"); return
        dpg.set_value("started_at", state["start_time"].strftime("%H:%M:%S"))
        delta = datetime.now() - state["start_time"]
        dpg.set_value("duration_val", "less than a minute" if delta.total_seconds()<60 else f"{int(delta.total_seconds()//60)} min")
    ui(_do)
def clear_logs():
    def _do():
        dpg.delete_item("log_scroller", children_only=True)
        dpg.add_text("", parent="log_scroller")
    ui(_do)
def mark_step_failed(tag, title, reason="Step failed"):
    set_card_state(tag,"error"); log_error(f"ERROR | {title}: {reason}")
    state["running"]=False; set_status("Error"); set_badge("Error", False); set_controls(False)

# ---------------- Worker ----------------
def run_pipeline():
    steps = [
        ("story_creation",   "Story Creation",   "Generating story using ChatGPT API…"),
        ("video_generation", "Video Generation", "Automating 3rd-party web app with Playwright…"),
        ("file_download",    "File Download",    "Downloading completed video file…"),
    ]
    total_ticks=120; per_step=total_ticks//len(steps)
    for i,(tag,title,desc) in enumerate(steps, start=1):
        if state["stop_flag"]: log_info("INFO  | Pipeline stopped by user."); return
        log_info(f"INFO  | Step {i}/{len(steps)}: {desc}")
        set_dot(tag, False); set_card_state(tag,"idle")
        for _ in range(per_step):
            if state["stop_flag"]: log_info("INFO  | Pipeline stopping…"); return
            if state.get("fail_step")==tag: mark_step_failed(tag,title,"Simulated failure"); return
            time.sleep(0.03)
            state["overall_progress"]=min(1.0, state["overall_progress"]+1/total_ticks)
            set_progress(); set_timing()
        state["completed_steps"]+=1; set_steps(); set_dot(tag, True)
        set_card_state(tag,"done"); log_success(f"SUCCESS | {title} completed.")
    log_success("SUCCESS | Workflow completed.")
    state["running"]=False; set_status("Idle"); set_badge("Idle",False); set_controls(False)

# ---------------- Callbacks ----------------
def start_clicked():
    if state["running"]: return
    state.update(running=True, stop_flag=False, start_time=datetime.now(), overall_progress=0.0, completed_steps=0)
    set_status("Running"); set_badge("Running", True)
    for t in ("story_creation","video_generation","file_download"): set_dot(t, False); set_card_state(t,"idle")
    set_steps(); set_progress(); set_timing(); set_controls(True)
    log_info("INFO  | Initializing ChatGPT API connection")
    log_info("INFO  | Sending story generation prompt")
    threading.Thread(target=run_pipeline, daemon=True).start()

def stop_clicked():
    if not state["running"]: return
    state["stop_flag"]=True; state["running"]=False
    set_status("Idle"); set_badge("Idle", False); set_controls(False); log_info("INFO  | Stop clicked")

def reset_clicked():
    state.update(running=False, stop_flag=False, start_time=None, overall_progress=0.0, completed_steps=0, fail_step=None)
    set_status("Idle"); set_badge("Idle", False); set_controls(False)
    clear_logs(); set_steps(); set_progress(); set_timing()
    for t in ("story_creation","video_generation","file_download"): set_dot(t, False); set_card_state(t,"idle")
    log_info("INFO  | Reset complete")

# ---------------- UI / Themes ----------------
dpg.create_context()

with dpg.theme(tag="APP_DARK"):
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (16,20,28,255))
        dpg.add_theme_color(dpg.mvThemeCol_FrameBg,  (30,38,50,255))
        dpg.add_theme_color(dpg.mvThemeCol_Border,   (55,66,82,255))
        dpg.add_theme_color(dpg.mvThemeCol_Text,     (225,230,238,255))
        dpg.add_theme_color(dpg.mvThemeCol_Separator,(55,66,82,255))
        dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 10)
        dpg.add_theme_style(dpg.mvStyleVar_FrameRounding,  10)
        dpg.add_theme_style(dpg.mvStyleVar_ChildRounding,  12)
        dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 14,10)
        dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing,  COL_GAP,10)
        dpg.add_theme_style(dpg.mvStyleVar_WindowPadding,16,16)
        dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize,1)
        dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize,1)

# Transparent theme for main (safety net)
with dpg.theme(tag="THEME_MAIN_TRANSPARENT_BG"):
    with dpg.theme_component(dpg.mvWindowAppItem):
        dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (0,0,0,0))

# Buttons (incl. badge with tuned vertical padding)
def make_btn_theme(name, color, hov=None, act=None, text=(235,235,235,255), disabled=False, pad_y=10):
    with dpg.theme(tag=name):
        with dpg.theme_component(dpg.mvButton, enabled_state=not disabled):
            dpg.add_theme_color(dpg.mvThemeCol_Button,        color)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, hov or color)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive,  act or color)
            dpg.add_theme_color(dpg.mvThemeCol_Text,          text)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 14)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding,  16, pad_y)

make_btn_theme("THEME_START_ENABLED",  (24,151,78,255), (27,173,88,255), (20,133,69,255))
make_btn_theme("THEME_START_DISABLED", (70,78,92,255),  disabled=True)
make_btn_theme("THEME_STOP_ENABLED",   (180,56,56,255), (205,64,64,255), (150,45,45,255))
make_btn_theme("THEME_STOP_DISABLED",  (70,78,92,255),  disabled=True)
make_btn_theme("THEME_RESET",          (62,72,86,255),  (72,86,104,255), (50,60,72,255))

# Badge themes: centered look -> pad_y=6 + height=30 on the button
make_btn_theme("THEME_BADGE_RUNNING_BTN", (24,151,78,255), text=(255,255,255,255), pad_y=6)
make_btn_theme("THEME_BADGE_IDLE_BTN",    (70,78,92,255),  text=(235,235,235,255), pad_y=6)

with dpg.theme(tag="THEME_DOT_DONE"):
    with dpg.theme_component(dpg.mvText): dpg.add_theme_color(dpg.mvThemeCol_Text, (24,151,78,255))
with dpg.theme(tag="THEME_DOT_IDLE"):
    with dpg.theme_component(dpg.mvText): dpg.add_theme_color(dpg.mvThemeCol_Text, (130,138,150,255))

# 50% transparent cards
with dpg.theme(tag="THEME_CARD_IDLE"):
    with dpg.theme_component(dpg.mvChildWindow):
        dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (30,38,50,128))
        dpg.add_theme_color(dpg.mvThemeCol_Border,  (55,66,82,200))
        dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize,1)
with dpg.theme(tag="THEME_CARD_DONE"):
    with dpg.theme_component(dpg.mvChildWindow):
        dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (24,151,78,128))
        dpg.add_theme_color(dpg.mvThemeCol_Border,  (24,151,78,255))
        dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize,2)
with dpg.theme(tag="THEME_CARD_ERROR"):
    with dpg.theme_component(dpg.mvChildWindow):
        dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (200,60,60,128))
        dpg.add_theme_color(dpg.mvThemeCol_Border,  (200,60,60,255))
        dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize,2)

with dpg.theme(tag="THEME_LOG_SUCCESS"):
    with dpg.theme_component(dpg.mvText): dpg.add_theme_color(dpg.mvThemeCol_Text, (24,151,78,255))
with dpg.theme(tag="THEME_LOG_ERROR"):
    with dpg.theme_component(dpg.mvText): dpg.add_theme_color(dpg.mvThemeCol_Text, (220,70,70,255))

with dpg.theme(tag="THEME_PROGRESS"):
    with dpg.theme_component(dpg.mvProgressBar):
        dpg.add_theme_color(dpg.mvThemeCol_PlotHistogram, (24,151,78,255))
        if hasattr(dpg, "mvThemeCol_PlotHistogramHovered"):
            dpg.add_theme_color(dpg.mvThemeCol_PlotHistogramHovered, (27,173,88,255))
        dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (38,46,60,200))

# Fonts (optional pleasant defaults)
def _first_font(paths, size):
    for p in paths:
        if p and os.path.exists(p):
            try: return dpg.add_font(p, size)
            except Exception: pass
    return None
with dpg.font_registry():
    BODY = _first_font([r"C:\Windows\Fonts\Inter.ttf",
                        r"C:\Windows\Fonts\Inter-Regular.ttf",
                        r"C:\Windows\Fonts\segoeui.ttf"], 16)
if BODY: dpg.bind_font(BODY)

# ---------------- Build UI ----------------
dpg.create_viewport(title="Workflow Monitor", width=1240, height=820)

# Create gradient texture
with dpg.texture_registry():
    gw, gh, gdata = gen_soft_gradient_rgba(1024, 640)
    dpg.add_static_texture(gw, gh, gdata, tag="bg_texture")

# Draw gradient BEHIND everything on the viewport drawlist
bg_draw = dpg.add_viewport_drawlist(front=False, tag="bg_draw")
bg_img  = dpg.draw_image("bg_texture", (0,0), (1240,820), parent=bg_draw)

with dpg.window(
    label="Workflow Monitor",
    tag="main",
    width=1220,
    height=800,
    no_collapse=True,
    no_resize=True,
    no_background=True,   # <— lets the gradient show through for sure
):
    dpg.add_spacer(height=6)

    # Top row (no scrollbars)
    with dpg.group(horizontal=True, tag="top_row"):
        with dpg.child_window(height=130, border=True, no_scrollbar=True, tag="card_status"):
            dpg.add_text("Status"); dpg.add_spacer(height=6)
            with dpg.group(horizontal=True):
                dpg.add_text("Current:"); dpg.add_spacer(width=6)
                dpg.add_text("", tag="status_label", show=False)   # hide duplicate text
                dpg.add_button(label="Idle", width=96, height=30, tag="status_badge_btn")  # centered badge
        with dpg.child_window(height=130, border=True, no_scrollbar=True, tag="card_timing"):
            dpg.add_text("Timing"); dpg.add_spacer(height=6)
            with dpg.group(horizontal=True):
                dpg.add_text("Started"); dpg.add_spacer(width=8)
                dpg.add_text("--:--:--", tag="started_at")
            with dpg.group(horizontal=True):
                dpg.add_text("Duration"); dpg.add_spacer(width=8)
                dpg.add_text("—", tag="duration_val")
        with dpg.child_window(height=130, border=True, no_scrollbar=True, tag="card_progsummary"):
            dpg.add_text("Progress"); dpg.add_spacer(height=6)
            with dpg.group(horizontal=True):
                dpg.add_text("0/3", tag="steps_counter"); dpg.add_spacer(width=6)
                dpg.add_text("Steps Completed")

    dpg.add_spacer(height=12)
    dpg.add_text("Workflow Controls")
    with dpg.group(horizontal=True):
        dpg.add_button(label="Start Workflow", width=170, height=38, tag="btn_start", callback=start_clicked)
        dpg.add_button(label="Stop",           width=110, height=38, tag="btn_stop",  callback=stop_clicked)
        dpg.add_button(label="Reset",          width=110, height=38, tag="btn_reset", callback=reset_clicked)
        dpg.bind_item_theme("btn_reset", "THEME_RESET")

    dpg.add_spacer(height=12)
    dpg.add_text("Progress Tracker")
    with dpg.group(tag="progress_container"):
        dpg.add_progress_bar(default_value=0.0, width=10, overlay="0%", tag="overall_progress_bar")
        dpg.bind_item_theme("overall_progress_bar", "THEME_PROGRESS")

    dpg.add_spacer(height=6)
    dpg.add_text("WORKFLOW STEPS")
    with dpg.group(horizontal=True, tag="steps_row"):
        for tag, title, sub in [
            ("story_creation", "Story Creation", "Generating story using ChatGPT API"),
            ("video_generation","Video Generation","Automating 3rd party web app with Playwright"),
            ("file_download",   "File Download",   "Downloading completed video file"),
        ]:
            with dpg.child_window(height=110, border=True, no_scrollbar=True, tag=f"{tag}_card"):
                with dpg.group(horizontal=True):
                    dpg.add_text("●", tag=f"{tag}_dot")
                    dpg.add_text(title)
                dpg.add_spacer(height=4)
                dpg.add_text(sub)

    dpg.add_spacer(height=12)
    dpg.add_text("Live Logs")
    with dpg.child_window(height=260, border=True, tag="log_region"):  # keep scrollbar here
        with dpg.group(tag="log_scroller"):
            dpg.add_text("")

# Bind themes
dpg.bind_theme("APP_DARK")
dpg.bind_item_theme("main", "THEME_MAIN_TRANSPARENT_BG")
for t in ("card_status","card_timing","card_progsummary"): dpg.bind_item_theme(t,"THEME_CARD_IDLE")
set_controls(False); set_badge("Idle", False)
for t in ("story_creation","video_generation","file_download"):
    set_dot(t, False); set_card_state(t, "idle")
set_steps(); set_progress(); set_timing()
dpg.bind_item_theme("status_badge_btn", "THEME_BADGE_IDLE_BTN")

# Fonts (optional)
if 'BODY' in locals() and BODY: dpg.bind_font(BODY)

dpg.setup_dearpygui()
dpg.show_viewport()
dpg.set_primary_window("main", True)

# ---------------- Manual render loop ----------------
prev_vw = prev_vh = 0
prev_main_w = 0
while dpg.is_dearpygui_running():
    _drain_ui()

    # Resize gradient to viewport
    vw, vh = dpg.get_viewport_client_width(), dpg.get_viewport_client_height()
    if (vw and vh) and (vw!=prev_vw or vh!=prev_vh):
        dpg.configure_item(bg_img, pmin=(0,0), pmax=(vw, vh))
        prev_vw, prev_vh = vw, vh

    # Align widths to progress bar right edge
    mw, _ = dpg.get_item_rect_size("main")
    if mw and mw != prev_main_w:
        target_w = max(300, mw - 2*H_MARGIN)
        dpg.set_item_width("overall_progress_bar", target_w)
        r1,r2,r3 = TOP_COL_RATIOS
        w1 = int(target_w*r1); w2 = int(target_w*r2); w3 = target_w - w1 - w2 - 2*COL_GAP
        dpg.set_item_width("card_status", w1)
        dpg.set_item_width("card_timing", w2)
        dpg.set_item_width("card_progsummary", w3)
        w_step = int((target_w - 2*COL_GAP)/3)
        dpg.set_item_width("story_creation_card",  w_step)
        dpg.set_item_width("video_generation_card",w_step)
        dpg.set_item_width("file_download_card",   w_step)
        prev_main_w = mw

    dpg.render_dearpygui_frame()

dpg.destroy_context()
