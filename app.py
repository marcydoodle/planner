import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta

# --- CONFIG & CONSTANTS ---
DATA_FILE = "sync_data.json"
CATEGORIES = ["Mexican", "Asian", "Pasta", "Roast", "Caribbean"]

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {
        "multipliers": {cat: 1.0 for cat in CATEGORIES},
        "other_multipliers": {}, 
        "groceries": [],
        "appointments": [],
        "history": {} # Stores data by date: {"2026-03-23": {...}}
    }

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

data = load_data()

st.set_page_config(page_title="Joy & Marcy Sync", layout="wide")
st.title("🌙 The Daily Sync")

tabs = st.tabs(["📅 Today's Plan", "📋 Tomorrow's Rundown", "📝 Nightly Input", "🗓 Future Planner", "🛒 Groceries"])

def render_rundown(target_date):
    """Reusable function to show Joy and Marcy's day in chronological order."""
    day_data = data["history"].get(target_date, {})
    appts = [a for a in data["appointments"] if a["date"] == target_date]
    
    col_j, col_m = st.columns(2)
    
    for user_name, col in zip(["Joy", "Marcy"], [col_j, col_m]):
        with col:
            st.subheader(f"{'🌸' if user_name == 'Joy' else '⚡'} {user_name}")
            u_data = day_data.get(user_name, {})
            
            if not u_data:
                st.info("No data entered for this day.")
                continue

            # 1. Energy Metric
            st.metric("Energy Level", f"{u_data.get('energy', 5)}/10")

            # 2. Work / Morning Section (Chronological Start)
            with st.expander("💼 Work & Daytime Plan", expanded=True):
                if user_name == "Joy":
                    st.write(f"**Schedule:** {u_data.get('work', 'Not set')}")
                    st.write(f"**Intensity:** {u_data.get('intensity', 5)}/10")
                    st.info(f"**Meetings:**\n{u_data.get('mtg', 'None')}")
                else:
                    st.write(f"**Gym:** {u_data.get('gym', 'Rest Day')}")
                    st.write(f"**Cycling:** {u_data.get('cycle', 'None')}")
                    st.info(f"**Tasks:**\n{u_data.get('tasks', 'None')}")
                
                # Appointments for this specific person
                user_appts = [a['desc'] for a in appts if a['owner'] in [user_name, "Both"]]
                if user_appts:
                    st.warning("**Appointments:**\n" + "\n".join([f"- {a}" for a in user_appts]))

            # 3. After Work Section
            with st.expander("🌆 After Work & Evening", expanded=True):
                st.write(f"**Plan:** {u_data.get('after', 'No plans yet')}")
                st.write(f"**Reminders:** {u_data.get('reminders', 'None')}")

            # 4. Personal Needs
            st.chat_message("user").write(f"**What I need from you:**\n{u_data.get('need', 'Nothing specific! :)')}")

# --- TAB 1: TODAY ---
with tabs[0]:
    today_str = datetime.now().strftime("%Y-%m-%d")
    st.header(f"Today: {datetime.now().strftime('%A, %b %d')}")
    render_rundown(today_str)

# --- TAB 2: TOMORROW ---
with tabs[1]:
    tmw_date = (datetime.now() + timedelta(days=1))
    tmw_str = tmw_date.strftime("%Y-%m-%d")
    st.header(f"Tomorrow: {tmw_date.strftime('%A, %b %d')}")
    
    # Dinner logic remains here as it's a "planning" phase
    if st.button("Calculate Tomorrow's Dinner"):
        # (Dinner logic remains the same, calculating based on history[tmw_str])
        st.write("Winner logic processed...") # Placeholder for previous logic
        
    render_rundown(tmw_str)

# --- TAB 3: INPUT FORM ---
with tabs[2]:
    st.header("Nightly Submission")
    target_date = st.date_input("What day is this for?", value=datetime.now() + timedelta(days=1))
    target_str = target_date.strftime("%Y-%m-%d")
    
    user = st.radio("Who is entering data?", ["Joy", "Marcy"], horizontal=True)
    
    with st.form("input_form"):
        energy = st.select_slider("⚡ Energy Level", options=range(0, 11), value=5)
        after = st.text_input("After Work Plan")
        reminders = st.text_area("Reminders")
        
        if user == "Joy":
            w_time = st.text_input("Work Schedule")
            w_mtg = st.text_area("Meetings")
            w_int = st.select_slider("Work Intensity", options=range(1, 11), value=5)
            need = st.text_area("What I need from Marcy")
        else:
            gym = st.text_input("Gym Plan")
            cycle = st.text_input("Cycling Plan")
            tasks = st.text_area("Tasks")
            need = st.text_area("What I need from Joy")
        
        groc_add = st.text_input("Groceries")
        
        # Dinner Voting... (Code from previous versions here)
        
        if st.form_submit_button("Save Entry"):
            if target_str not in data["history"]:
                data["history"][target_str] = {}
            
            entry = {"energy": energy, "after": after, "reminders": reminders, "need": need}
            if user == "Joy":
                entry.update({"work": w_time, "mtg": w_mtg, "intensity": w_int})
            else:
                entry.update({"gym": gym, "cycle": cycle, "tasks": tasks})
            
            data["history"][target_str][user] = entry
            save_data(data)
            st.success(f"Saved for {target_str}")

# --- OTHER TABS (FUTURE PLANNER & GROCERIES) ---
# [Keep logic from previous versions]
