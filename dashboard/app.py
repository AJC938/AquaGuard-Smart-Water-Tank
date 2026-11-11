from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from serial_reader import SerialReader, available_ports


st.set_page_config(page_title="AquaGuard | Tank Monitoring", page_icon="💧", layout="wide")

st.markdown("""
<style>
:root { --bg:#0b1117; --panel:#111b24; --panel2:#14212c; --line:#243744; --cyan:#37d6cf; --mint:#77f0d5; --text:#edf5f7; --muted:#8da2ad; --red:#ff647c; }
.stApp { background:radial-gradient(ellipse at 85% -15%,#12333c 0,transparent 35%),var(--bg); color:var(--text); font-family:'Segoe UI',sans-serif; }
[data-testid="stHeader"] { background:transparent; }
[data-testid="stSidebar"] { background:#0d151c; border-right:1px solid var(--line); }
.block-container { padding-top:2.2rem; max-width:1500px; }
.brand { display:flex; align-items:center; gap:15px; margin-bottom:20px; }
.brand-mark { width:48px;height:48px;border-radius:15px;display:grid;place-items:center;background:linear-gradient(145deg,#1a4b55,#102a35);border:1px solid #28616a;color:var(--mint);font-size:25px;box-shadow:0 0 28px #36d6cf16; }
.brand-name { font-size:26px;line-height:1.1;letter-spacing:.13em;font-weight:800;color:#f3fbfc; }
.brand-sub { color:var(--muted);font-size:10px;letter-spacing:.2em;margin-top:5px;font-weight:700; }
.topline { color:var(--muted);font-size:12px;margin:0 0 24px; }
.section-kicker { color:#76909c;font-size:10px;letter-spacing:.18em;font-weight:800;text-transform:uppercase;margin:12px 0 12px; }
.metric-card { min-height:174px;background:linear-gradient(150deg,#14232d,#101920 72%);border:1px solid #253944;border-radius:18px;padding:20px 22px;position:relative;overflow:hidden; }
.metric-card:after { content:''; position:absolute;right:-34px;top:-50px;width:110px;height:110px;border-radius:50%;background:#31d5cb0d; }
.metric-title { color:#9ab0ba;font-weight:800;letter-spacing:.12em;font-size:10px; }
.metric-value { color:#f4fbfc;font-size:34px;font-weight:700;letter-spacing:-.04em;margin-top:18px;line-height:1; }
.metric-unit { color:#8ea5af;font-size:14px;font-weight:500;letter-spacing:0; }
.metric-foot { color:#8197a2;font-size:11px;margin-top:16px; }
.metric-icon { float:right;color:#49d6ce;font-size:18px; }
.panel { background:linear-gradient(145deg,#111c25,#101820);border:1px solid #243843;border-radius:17px;padding:20px 22px;margin:12px 0; }
.panel-title { font-size:13px;font-weight:800;letter-spacing:.06em;color:#e5f0f3;margin-bottom:3px; }
.panel-caption { color:#8197a2;font-size:11px; }
.pill { border-radius:30px;padding:7px 12px;font-size:10px;font-weight:800;letter-spacing:.12em;display:inline-block; }
.pill-live { color:#80f5d8;background:#123a34;border:1px solid #1f665b; }
.pill-off { color:#a7b5bb;background:#1b2830;border:1px solid #34434b; }
.pill-alert { color:#ff8292;background:#3b1e28;border:1px solid #723440; }
.small-label { color:#8299a3;font-size:10px;letter-spacing:.12em;font-weight:800;text-transform:uppercase; }
.small-value { color:#edf5f7;font-family:'Cascadia Mono','Consolas',monospace;font-size:13px;margin-top:6px; }
div[data-testid="stButton"] button { border-radius:10px;border:1px solid #28646a;background:#16363d;color:#a8faf0;font-weight:800; }
div[data-testid="stButton"] button:hover { border-color:#53e3d6;color:white;background:#1a4a4f; }
div[data-testid="stSelectbox"] label, div[data-testid="stSlider"] label { color:#91a8b2; }
div[data-testid="stAlert"] { border-radius:12px; }
footer { visibility:hidden; }
</style>
""", unsafe_allow_html=True)

if "serial_reader" not in st.session_state:
    st.session_state.serial_reader = SerialReader()
reader: SerialReader = st.session_state.serial_reader

state = reader.snapshot()
st.markdown(f"""
<div class="brand"><div class="brand-mark">◈</div><div><div class="brand-name">AQUAGUARD</div>
<div class="brand-sub">SMART WATER TANK MONITORING SYSTEM</div></div></div>
<div class="topline">Local monitoring console &nbsp;·&nbsp; Arduino Uno R3 &nbsp;·&nbsp; 9600 baud</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown('<div class="section-kicker">Device connection</div>', unsafe_allow_html=True)
    ports = available_ports()
    port_options = [p["device"] for p in ports]
    if not port_options:
        st.caption("No serial ports detected. Connect the Uno by USB, then refresh this page.")
        selected_port = st.selectbox("Arduino COM port", ["No ports found"], disabled=True)
    else:
        selected_port = st.selectbox("Arduino COM port", port_options,
                                     format_func=lambda p: next((f"{p} · {x['description']}" for x in ports if x["device"] == p), p))
    if st.button("↻  Refresh available ports", width="stretch"):
        st.rerun()
    st.caption("Baud rate · 9600")
    active = state["connected"]
    left, right = st.columns(2)
    with left:
        connect_clicked = st.button("Connect", disabled=active or not port_options, width="stretch")
    with right:
        disconnect_clicked = st.button("Disconnect", disabled=not active, width="stretch")
    if connect_clicked and port_options:
        try:
            reader.connect(selected_port, 9600)
            st.rerun()
        except Exception as exc:
            st.error(f"Could not open {selected_port}: {exc}")
    if disconnect_clicked:
        reader.disconnect()
        st.rerun()
    st.markdown('<div class="section-kicker" style="margin-top:28px">Session</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="small-label">Selected port</div><div class="small-value">{state["port"] or "—"}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="small-label" style="margin-top:18px">Serial status</div><div class="small-value">{"CONNECTED" if active else "DISCONNECTED"}</div>', unsafe_allow_html=True)
    if state["error"]:
        st.error(state["error"])
    st.markdown('<div class="section-kicker" style="margin-top:28px">Protocol</div><div class="panel-caption">Temperature · Distance · Water Sensor · Status · Buzzer</div>', unsafe_allow_html=True)


@st.fragment(run_every="1s")
def live_dashboard() -> None:
    state = reader.snapshot()
    reading = state["last_reading"]
    connected = state["connected"]
    # Fade values to an explicit waiting state until real hardware sends a full message.
    waiting = reading is None
    temp = f'{reading["temperature_c"]:.1f}' if reading and reading["temperature_c"] is not None else ("SENSOR ERROR" if reading else "—")
    temp_note = (reading["temperature_error"] if reading and reading["temperature_error"] else "Live probe reading") if reading else "Waiting for Arduino data"
    distance = f'{reading["distance_cm"]:.1f}' if reading and reading["distance_cm"] is not None else (reading["distance_status"] if reading else "—")
    distance_note = "Ultrasonic sensor" if reading else "Waiting for Arduino data"
    water = reading["water_status"] if reading else "—"
    water_note = f'Raw analog value · {reading["water_raw"]}' if reading else "Waiting for Arduino data"
    buzzer = reading["buzzer"] if reading else "—"
    buzzer_active = buzzer == "ON"
    conn_pill = '<span class="pill pill-live">●&nbsp; LIVE LINK</span>' if connected else '<span class="pill pill-off">●&nbsp; DISCONNECTED</span>'
    st.markdown(f'<div style="display:flex;justify-content:space-between;align-items:center;margin:8px 0 14px"><div><div class="section-kicker" style="margin:0">Tank overview</div><div style="color:#78909b;font-size:11px;margin-top:5px">Live sensor telemetry and recent operating history</div></div>{conn_pill}</div>', unsafe_allow_html=True)
    cols = st.columns(4, gap="medium")
    cards = [
        ("WATER TEMPERATURE", temp, "°C", temp_note, "◉"),
        ("ULTRASONIC DISTANCE", distance, "cm" if reading and reading["distance_cm"] is not None else "", distance_note, "⌁"),
        ("WATER SENSOR", water, "", water_note, "◈"),
        ("BUZZER / ALARM", buzzer, "", "Alarm active" if buzzer_active else ("Normal operation" if reading else "Waiting for Arduino data"), "⚠"),
    ]
    for col, (title, value, unit, note, icon) in zip(cols, cards):
        value_color = "#ff7388" if title == "BUZZER / ALARM" and buzzer_active else "#f4fbfc"
        if title == "WATER SENSOR" and water == "WET": value_color = "#4ce1d4"
        if title == "WATER SENSOR" and water == "DRY": value_color = "#f5cc71"
        col.markdown(f'<div class="metric-card"><span class="metric-icon">{icon}</span><div class="metric-title">{title}</div><div class="metric-value" style="color:{value_color};font-size:{"28px" if len(str(value))>10 else "34px"}">{value} <span class="metric-unit">{unit}</span></div><div class="metric-foot">{note}</div></div>', unsafe_allow_html=True)

    if not connected:
        st.info("Connect the Arduino to begin. No simulated readings are shown.")
    elif waiting:
        st.info("Connected. Waiting for the first complete sensor message from the Arduino…")

    st.markdown('<div class="section-kicker" style="margin-top:25px">Live trend · recent readings</div>', unsafe_allow_html=True)
    history = state["history"]
    cutoff = datetime.now().astimezone() - timedelta(minutes=15)
    recent = [x for x in history if x["timestamp"] >= cutoff]
    chart_left, chart_right = st.columns(2, gap="medium")
    with chart_left:
        st.markdown('<div class="panel-title">TEMPERATURE HISTORY</div><div class="panel-caption">Recent readings · °C</div>', unsafe_allow_html=True)
        valid = [{"Time": x["timestamp"], "Temperature (°C)": x["temperature_c"]} for x in recent if x["temperature_c"] is not None]
        if valid:
            frame = pd.DataFrame(valid).set_index("Time")
            st.line_chart(frame, color="#37d6cf", height=230, width="stretch", alt="Temperature readings over time")
        else:
            st.markdown('<div class="panel-caption" style="padding:40px 0;text-align:center">Chart will populate when valid temperature readings arrive.</div>', unsafe_allow_html=True)
    with chart_right:
        st.markdown('<div class="panel-title">DISTANCE HISTORY</div><div class="panel-caption">Recent readings · cm</div>', unsafe_allow_html=True)
        valid = [{"Time": x["timestamp"], "Distance (cm)": x["distance_cm"]} for x in recent if x["distance_cm"] is not None]
        if valid:
            frame = pd.DataFrame(valid).set_index("Time")
            st.line_chart(frame, color="#8b9dff", height=230, width="stretch", alt="Distance readings over time")
        else:
            st.markdown('<div class="panel-caption" style="padding:40px 0;text-align:center">Chart will populate when distance readings arrive.</div>', unsafe_allow_html=True)

    last = reading["timestamp"].strftime("%Y-%m-%d %H:%M:%S %Z") if reading else "No complete reading received"
    update_status = "Receiving complete messages" if reading and connected else ("Waiting for complete message" if connected else "No active serial session")
    st.markdown('<div class="section-kicker" style="margin-top:20px">System information</div>', unsafe_allow_html=True)
    info_cols = st.columns(4)
    info = [("CONNECTION", "Connected" if connected else "Disconnected"), ("LAST SUCCESSFUL READING", last), ("READING UPDATE", update_status), ("SERIAL INPUT", f'{state["lines_received"]} lines received')]
    for col, (label, value) in zip(info_cols, info):
        col.markdown(f'<div class="panel"><div class="small-label">{label}</div><div class="small-value">{value}</div></div>', unsafe_allow_html=True)


live_dashboard()
st.markdown('<div style="text-align:center;color:#526973;font-size:10px;margin:25px 0 4px;letter-spacing:.08em">AQUAGUARD · LOCAL USB SERIAL MONITORING</div>', unsafe_allow_html=True)
