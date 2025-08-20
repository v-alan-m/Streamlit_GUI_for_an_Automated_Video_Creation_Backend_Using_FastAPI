# workflow_monitor_streamlit.py
import streamlit as st
import time

# State
if "running" not in st.session_state:
    st.session_state.running = False
    st.session_state.logs = []
    st.session_state.progress = 0

st.title("Python Workflow Monitor")

# Controls
col1, col2, col3 = st.columns(3)
if col1.button("▶️ Start", disabled=st.session_state.running):
    st.session_state.running = True
    st.session_state.logs = ["Workflow started"]
    st.session_state.progress = 0
if col2.button("🛑 Stop", disabled=not st.session_state.running):
    st.session_state.running = False
    st.session_state.logs.append("Workflow stopped")
if col3.button("🔄 Reset"):
    st.session_state.running = False
    st.session_state.logs = []
    st.session_state.progress = 0

# Progress
progress_bar = st.progress(st.session_state.progress)

# Logs
log_area = st.empty()
for log in st.session_state.logs:
    log_area.text("\n".join(st.session_state.logs))

# Fake workflow
if st.session_state.running:
    for i in range(st.session_state.progress, 101, 10):
        time.sleep(0.2)
        st.session_state.progress = i
        progress_bar.progress(i)
        st.session_state.logs.append(f"Progress {i}%")
        log_area.text("\n".join(st.session_state.logs))
    st.session_state.running = False
    st.session_state.logs.append("Workflow complete ✅")
