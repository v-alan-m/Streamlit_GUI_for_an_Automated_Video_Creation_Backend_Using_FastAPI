# workflow_monitor.py
# Python-only GUI that mirrors your screenshots using Dear PyGui.
# - Start -> disables itself (grey "Running…"), enables Stop (red)
# - Stop   -> halts the worker, re-enables Start (green)
# - Reset  -> clears progress + logs
# - Simulated 3-step workflow with live logs and overall progress

import time
import threading
from datetime import datetime, timedelta
import dearpygui.dearpygui as dpg

# ----------------------------
# App State
# ----------------------------
state = {
    "running": False,
    "stop_flag": False,
    "start_time": None,
    "completed_steps": 0,
    "overall_progress": 0.0,
    "total_steps": 3
}


# ----------------------------
# THEMES (dark + button states)
# ----------------------------
def make_button_theme(name, color, hovered=None, active=None, text=(230, 230, 230, 255), disabled=False):
    with dpg.theme(tag=name):
        with dpg.theme_component(dpg.mvButton, enabled_state=not disabled):
            dpg.add_theme_color(dpg.mvThemeCol_Button, color)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, hovered or color)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, active or color)
            dpg.add_theme_color(dpg.mvThemeCol_Text, text)


# base dark theme for whole app
with dpg.theme() as DARK:
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (15, 21, 29, 255))
        dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (28, 36, 48, 255))
        dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, (18, 25, 34, 255))
        dpg.add_theme_color(dpg.mvThemeCol_Header, (30, 39, 52, 255))
        dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, (40, 52, 68, 255))
        dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, (40, 52, 68, 255))
        dpg.add_theme_color(dpg.mvThemeCol_Text, (220, 226, 235, 255))
        dpg.add_theme_color(dpg.mvThemeCol_Separator, (55, 66, 82, 255))

# buttons
make_button_theme("THEME_START_ENABLED", color=(24, 151, 78, 255), hovered=(27, 173, 88, 255),
                  active=(20, 133, 69, 255))
make_button_theme("THEME_START_DISABLED", color=(60, 70, 84, 255), disabled=True)

make_button_theme("THEME_STOP_ENABLED", color=(180, 56, 56, 255), hovered=(205, 64, 64, 255), active=(150, 45, 45, 255))
make_button_theme("THEME_STOP_DISABLED", color=(60, 70, 84, 255), disabled=True)

make_button_theme("THEME_RESET", color=(60, 70, 84, 255), hovered=(70, 84, 100, 255), active=(50, 60, 72, 255))


# ----------------------------
# Helpers
# ----------------------------
def log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    dpg.add_text(f"{timestamp}  {msg}", parent="log_scroller")
    dpg.set_y_scroll("log_region", 10_000_000)


def set_status(text):
    dpg.set_value("status_label", text)


def set_timing():
    if not state["start_time"]:
        dpg.set_value("started_at", "--:--:--")
        dpg.set_value("duration_val", "—")
        return
    dpg.set_value("started_at", state["start_time"].strftime("%H:%M:%S"))
    delta = datetime.now() - state["start_time"]
    if delta < timedelta(minutes=1):
        dpg.set_value("duration_val", "less than a minute")
    else:
        mins = int(delta.total_seconds() // 60)
        dpg.set_value("duration_val", f"{mins} min")


def update_progress():
    pct = state["overall_progress"]
    dpg.set_value("overall_progress_bar", pct)
    dpg.set_value("overall_progress_label", f"{int(pct * 100)}%")
    dpg.set_value("steps_counter", f"{state['completed_steps']}/{state['total_steps']}")


def set_step_state(step_tag, done: bool):
    # step status dot (green when done)
    dpg.configure_item(f"{step_tag}_dot", show=True)
    dpg.bind_item_theme(f"{step_tag}_dot", "THEME_START_ENABLED" if done else "THEME_START_DISABLED")


def set_controls(running: bool):
    if running:
        dpg.configure_item("btn_start", enabled=False)
        dpg.bind_item_theme("btn_start", "THEME_START_DISABLED")
        dpg.configure_item("btn_stop", enabled=True)
        dpg.bind_item_theme("btn_stop", "THEME_STOP_ENABLED")
    else:
        dpg.configure_item("btn_start", enabled=True)
        dpg.bind_item_theme("btn_start", "THEME_START_ENABLED")
        dpg.configure_item("btn_stop", enabled=False)
        dpg.bind_item_theme("btn_stop", "THEME_STOP_DISABLED")


# ----------------------------
# Worker (simulated 3-step pipeline)
# ----------------------------
def run_pipeline():
    steps = [
        ("story_creation", "Generating story using ChatGPT API…"),
        ("video_generation", "Automating 3rd-party web app with Playwright…"),
        ("file_download", "Downloading completed video file…"),
    ]
    total_ticks = 100
    per_step = total_ticks // len(steps)

    for idx, (tag, message) in enumerate(steps, start=1):
        if state["stop_flag"]:
            log("INFO  | Pipeline stopped by user.")
            return
        log(f"INFO  | Step {idx}/{len(steps)}: {message}")
        # simulate step work
        for _ in range(per_step):
            if state["stop_flag"]:
                log("INFO  | Pipeline stopping…")
                return
            time.sleep(0.03)  # simulate work
            state["overall_progress"] += 1 / total_ticks
            update_progress()
            set_timing()
        state["completed_steps"] += 1
        set_step_state(tag, True)

    log("SUCCESS | Workflow completed.")
    # flip back to idle
    state["running"] = False
    dpg.set_value("status_badge", "Idle")
    set_status("Idle")
    set_controls(False)


def start_clicked():
    if state["running"]:
        return
    state.update(running=True, stop_flag=False, start_time=datetime.now(),
                 completed_steps=0, overall_progress=0.0)
    dpg.set_value("status_badge", "Running")
    set_status("Running")
    set_step_state("story_creation", False)
    set_step_state("video_generation", False)
    set_step_state("file_download", False)
    update_progress()
    set_timing()
    set_controls(True)
    log("INFO  | Initializing ChatGPT API connection")
    log("INFO  | Sending story generation prompt")
    threading.Thread(target=run_pipeline, daemon=True).start()


def stop_clicked():
    if not state["running"]:
        return
    state["stop_flag"] = True
    state["running"] = False
    dpg.set_value("status_badge", "Idle")
    set_status("Idle")
    set_controls(False)


def reset_clicked():
    state.update(running=False, stop_flag=False, start_time=None,
                 completed_steps=0, overall_progress=0.0)
    set_status("Idle")
    dpg.set_value("status_badge", "Idle")
    dpg.delete_item("log_scroller", children_only=True)
    dpg.add_text("", parent="log_scroller")  # keep widget alive
    set_step_state("story_creation", False)
    set_step_state("video_generation", False)
    set_step_state("file_download", False)
    update_progress()
    set_timing()
    set_controls(False)
    log("INFO  | Reset complete.")


# ----------------------------
# UI
# ----------------------------
dpg.create_context()
dpg.create_viewport(title="Python Workflow Monitor", width=1200, height=780)

with dpg.window(label="Python Workflow Monitor", tag="main", no_move=True, no_resize=True, no_collapse=True, width=1180,
                height=760):
    dpg.add_spacer(height=4)

    # Top: Status / Timing / Progress cards
    with dpg.group(horizontal=True):
        with dpg.child_window(width=300, height=120, border=True):
            dpg.add_text("Status")
            dpg.add_text(" ")
            with dpg.group(horizontal=True):
                dpg.add_text("●")
                dpg.add_text("Idle", tag="status_label")
            dpg.add_text("", tag="status_badge")  # small status text if needed

        with dpg.child_window(width=480, height=120, border=True):
            dpg.add_text("Timing")
            with dpg.group(horizontal=True):
                dpg.add_text("Started")
                dpg.add_spacer(width=10)
                dpg.add_text("--:--:--", tag="started_at")
            with dpg.group(horizontal=True):
                dpg.add_text("Duration")
                dpg.add_spacer(width=10)
                dpg.add_text("—", tag="duration_val")

        with dpg.child_window(width=360, height=120, border=True):
            dpg.add_text("Progress")
            with dpg.group(horizontal=True):
                dpg.add_text("0/3", tag="steps_counter")
                dpg.add_spacer(width=8)
                dpg.add_text("Steps Completed")

    dpg.add_spacer(height=8)

    # Controls
    dpg.add_text("Workflow Controls")
    with dpg.group(horizontal=True):
        dpg.add_button(label="Start Workflow", width=150, callback=start_clicked, tag="btn_start")
        dpg.add_button(label="Stop", width=100, callback=stop_clicked, tag="btn_stop")
        dpg.add_button(label="Reset", width=100, callback=reset_clicked, tag="btn_reset")

    dpg.add_spacer(height=8)

    # Progress Tracker
    dpg.add_text("Progress Tracker")
    with dpg.group():
        with dpg.group(horizontal=True):
            dpg.add_progress_bar(default_value=0.0, overlay="", width=800, tag="overall_progress_bar")
            dpg.add_spacer(width=10)
            dpg.add_text("0%", tag="overall_progress_label")

        dpg.add_spacer(height=4)
        dpg.add_text("WORKFLOW STEPS")
        with dpg.group(horizontal=True):
            for step_tag, title, subtitle in [
                ("story_creation", "Story Creation", "Generating story using ChatGPT API"),
                ("video_generation", "Video Generation", "Automating 3rd party web app with Playwright"),
                ("file_download", "File Download", "Downloading completed video file"),
            ]:
                with dpg.child_window(width=360, height=110, border=True):
                    with dpg.group(horizontal=True):
                        dpg.add_text("■", tag=f"{step_tag}_dot")
                        dpg.add_text(title)
                    dpg.add_text(subtitle)

    dpg.add_spacer(height=8)

    # Live Logs
    dpg.add_text("Live Logs")
    with dpg.child_window(height=260, border=True, tag="log_region"):
        with dpg.group(tag="log_scroller"):
            dpg.add_text("")

# Bind themes
dpg.bind_item_theme("main", DARK)
set_controls(False)  # initial state
set_step_state("story_creation", False)
set_step_state("video_generation", False)
set_step_state("file_download", False)
update_progress()
set_timing()

dpg.setup_dearpygui()
dpg.show_viewport()
dpg.set_primary_window("main", True)
dpg.start_dearpygui()
dpg.destroy_context()
