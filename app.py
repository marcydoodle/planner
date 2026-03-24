import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta

# --- CONFIG ---
DATA_FILE = "sync_data.json"
CATEGORIES = ["Mexican", "Asian", "Pasta", "Roast", "Caribbean", "Pizza", "Scrounge", "Starve"]
UTC_OFFSET = -4 

def get_local_now():
    return datetime.utcnow() + timedelta(hours=UTC_OFFSET)

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            try:
                d = json.load(f)
                for k in ["history", "multipliers", "other_multipliers", "groceries", "appointments"]:
                    if k not in d: d[k] = {} if "multipliers" in k or "history" in k else []
                return d
            except: pass
    return {"multipliers": {c: 1.0 for c in CATEGORIES}, "other_multipliers": {}, "groceries": [], "appointments": [], "history": {}}

def save_data(d):
    with open(DATA_FILE, "w") as f:
        json.dump(d, f)

# --- INITIALIZE DATA ---
data = load_data()
now_dt = get_local_now()
today_str = "2026-03-24" # HARDCODED FOR TODAY
tomorrow_str = "2026-03-25"

# --- HARDCODING YOUR SPECIFIC DATA FROM SCREENSHOTS ---
if today_str not in data["history"]:
    data["history"][today_str] = {
        "Joy": {
            "energy": 9,
            "work": "9-5pm",
            "intensity": 7,
            "mtg": "None",
            "after": "Visit the storage unit to gain access and take a view boxes. Put together the dresser if it gets delivered and there is time/desire.",
            "reminders": "None",
            "need": "Help me move stuff around to preview where the table will be."
        },
        "Marcy": {
            "energy": 10,
            "gym": "Light, high volume leg day around 8-9",
            "cycle": "20 miles moderate biking with some climbs but not intense, 1 hour",
            "tasks": "Organize transcripts, reach out for letters of recommendation, tryhackme, code academy, newsletter",
            "after": "Mario 64",
            "reminders": "Swag",
            "need": "One new thought or memory that I don't know and a head rub"
        }
    }
    save_data(data)

# --- APP UI ---
st.set_page_config(page_title="Joy & Marcy Sync", layout="wide")
st.title("🌙 The Daily Sync")

tabs = st.tabs(["📅 Today", "📋 Tomorrow", "📝 Input", "🗓 Planner", "🛒 Groceries"])

def render_rundown(date_key, label):
    day_data = data["history"].get(date_key, {})
    day_appts = [a for a in data["appointments"] if a["date"] == date_key]
    
    st.header(f"{label}: {date_key}")
    
    if not day_data and not day_appts:
        st.warning(f"No sync data found.")
        return

    c1, c2 = st.columns(2)
    for name, col in zip(["Joy", "Marcy"], [c1, c2]):
        with col:
            st.subheader(f"{'🌸' if name == 'Joy' else '⚡'} {name}")
            u = day_data.get(name, {})
            
            with st.expander("🌅 Morning & Daytime", expanded=True):
                if name == "Joy":
                    st.write(f"**Work Schedule:** {u.get('work')}")
                    st.write(f"**Intensity:** {u.get('intensity')}/10")
                    st.info(f"**Meetings:** {u.get('mtg')}")
                else:
                    st.write(f"**Gym Plan:** {u.get('gym')}")
                    st.write(f"**Cycling:** {u.get('cycle')}")
                    st.info(f"**Daily Tasks:** {u.get('tasks')}")

            with st.expander("🌆 After Work & Evening", expanded=True):
                st.write(f"**Plan:** {u.get('after')}")
                st.write(f"**Don't Forget:** {u.get('reminders')}")

            with st.container(border=True):
                st.write("**🤝 Partnership & Needs**")
                st.write(f"**Energy Level:** {u.get('energy')}/10")
                if u.get("need"):
                    st.chat_message("user").write(u.get("need"))

# --- TABS ---
with tabs[0]:
    render_rundown(today_str, "Today")

with tabs[1]:
    render_rundown(tomorrow_str, "Tomorrow")

with tabs[2]:
    st.header("Nightly Sync")
    # Date picker now defaults to actual Tomorrow
    target_date = st.date_input("Planning Date", value=now_dt + timedelta(days=1))
    t_key = target_date.strftime("%Y-%m-%d")
    user = st.radio("User", ["Joy", "Marcy"], horizontal=True)
    
    with st.form("input_f"):
        # Input fields (same as previous logic)
        # ... [Rest of form logic here]
        if st.form_submit_button("Submit"):
            # Save logic
            st.success(f"Saved for {t_key}")

with tabs[4]:
    st.header("🛒 Groceries")
    # Grocery logic
    # ...
