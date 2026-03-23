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
            try:
                existing_data = json.load(f)
                keys = ["history", "multipliers", "other_multipliers", "groceries", "appointments"]
                for key in keys:
                    if key not in existing_data:
                        existing_data[key] = {} if "multipliers" in key or "history" in key else []
                return existing_data
            except json.JSONDecodeError:
                pass 
    return {"multipliers": {cat: 1.0 for cat in CATEGORIES}, "other_multipliers": {}, "groceries": [], "appointments": [], "history": {}}

def save_data(data_to_save):
    with open(DATA_FILE, "w") as f:
        json.dump(data_to_save, f)

data = load_data()

st.set_page_config(page_title="Joy & Marcy Sync", layout="wide")
st.title("🌙 The Daily Sync")

tabs = st.tabs(["📅 Today's Plan", "📋 Tomorrow's Rundown", "📝 Nightly Input", "🗓 Future Planner", "🛒 Groceries"])

def render_rundown(target_date_str):
    """Displays Joy and Marcy's day in CHRONOLOGICAL order."""
    day_data = data["history"].get(target_date_str, {})
    appts = [a for a in data["appointments"] if a["date"] == target_date_str]
    
    if not day_data and not appts:
        st.info(f"No plans recorded for {target_date_str}.")
        return

    col_j, col_m = st.columns(2)
    
    for user_name, col in zip(["Joy", "Marcy"], [col_j, col_m]):
        with col:
            st.subheader(f"{'🌸' if user_name == 'Joy' else '⚡'} {user_name}")
            u_data = day_data.get(user_name, {})
            
            # 1. THE STATUS (Chronological Start)
            if "energy" in u_data:
                e = u_data['energy']
                color = "green" if e > 7 else "orange" if e > 4 else "red"
                st.markdown(f"**Current Energy:** :{color}[{e}/10]")

            # 2. MORNING & DAYTIME
            with st.expander("🌅 Morning & Daytime", expanded=True):
                if user_name == "Joy":
                    st.write(f"**Work Schedule:** {u_data.get('work', '---')}")
                    st.write(f"**Work Intensity:** {u_data.get('intensity', '5')}/10")
                    st.info(f"**Meetings:** {u_data.get('mtg', 'None')}")
                else:
                    st.write(f"**Gym Plan:** {u_data.get('gym', 'Rest day')}")
                    st.write(f"**Cycling:** {u_data.get('cycle', 'No ride')}")
                    st.info(f"**Day Tasks:** {u_data.get('tasks', 'None')}")
                
                p_appts = [a['desc'] for a in appts if a['owner'] in [user_name, "Both"]]
                if p_appts:
                    st.error("⚠️ **Scheduled:**\n" + "\n".join([f"- {a}" for a in p_appts]))

            # 3. EVENING
            with st.expander("🌆 After Work & Evening", expanded=True):
                st.write(f"**Plan:** {u_data.get('after', 'TBD')}")
                st.write(f"**Don't Forget:** {u_data.get('reminders', 'Nothing special')}")

            # 4. PARTNERSHIP
            if u_data.get("need"):
                st.chat_message("user").write(f"**Need from partner:** {u_data['need']}")

# --- TAB 1 & 2 (TODAY & TOMORROW) ---
with tabs[0]:
    t_key = datetime.now().strftime("%Y-%m-%d")
    st.header(f"Today: {datetime.now().strftime('%A, %b %d')}")
    render_rundown(t_key)

with tabs[1]:
    tmw_date = datetime.now() + timedelta(days=1)
    tmw_key = tmw_date.strftime("%Y-%m-%d")
    st.header(f"Tomorrow: {tmw_date.strftime('%A, %b %d')}")
    render_rundown(tmw_key)

# --- TAB 3: INPUT (REARRANGED CHRONOLOGICALLY) ---
with tabs[2]:
    st.header("Sync for Tomorrow")
    target_date = st.date_input("Planning for:", value=datetime.now() + timedelta(days=1))
    t_key = target_date.strftime("%Y-%m-%d")
    user = st.radio("User:", ["Joy", "Marcy"], horizontal=True)
    
    with st.form("input_form"):
        # 1. START OF DAY: Energy & Morning Work/Gym
        st.subheader("🌅 Start of Day & Work")
        energy = st.select_slider("⚡ Energy Level (0-10)", options=range(0, 11), value=5)
        
        if user == "Joy":
            w_time = st.text_input("Work Schedule (Time)")
            w_int = st.select_slider("Work Intensity (1-10)", options=range(1, 11), value=5)
            w_mtg = st.text_area("Meetings & Calls")
        else:
            gym = st.text_input("Gym Plan")
            cycle = st.text_input("Cycling Plan")
            tasks = st.text_area("Daily Tasks")

        # 2. AFTER WORK & EVENING
        st.subheader("🌆 After Work & Evening")
        after = st.text_input("After Work Plans")
        reminders = st.text_area("Specific Reminders / Don't Forgets")

        # 3. PARTNERSHIP & NEEDS
        st.subheader("🤝 Partnership")
        need = st.text_area(f"What I need from {'Marcy' if user == 'Joy' else 'Joy'} tomorrow")
        
        # 4. HOUSEHOLD: Dinner & Groceries
        st.subheader("🍕 Dinner & Groceries")
        groc_add = st.text_input("Add to Shopping List (comma separated)")
        
        cols = st.columns(len(CATEGORIES) + 1)
        votes = {cat: cols[i].number_input(cat, 0, 10, 0) for i, cat in enumerate(CATEGORIES)}
        o_name = cols[-1].text_input("Other Name")
        o_pts = cols[-1].number_input("Other Pts", 0, 10, 0)

        if st.form_submit_button("Save Sync Entry"):
            if sum(votes.values()) + o_pts > 10: st.error("Over 10 points allocated!")
            else:
                if t_key not in data["history"]: data["history"][t_key] = {}
                entry = {"energy": energy, "after": after, "reminders": reminders, "need": need, "votes": votes, "other_name": o_name, "other_pts": o_pts}
                if user == "Joy": entry.update({"work": w_time, "mtg": w_mtg, "intensity": w_int})
                else: entry.update({"gym": gym, "cycle": cycle, "tasks": tasks})
                data["history"][t_key][user] = entry
                if groc_add: 
                    for i in groc_add.split(","): 
                        if i.strip(): data["groceries"].append({"item": i.strip(), "checked": False, "time": None})
                if o_name and o_name not in data["other_multipliers"]: data["other_multipliers"][o_name] = 1.0
                save_data(data); st.success("Saved successfully!")

# --- TAB 4 & 5 (FUTURE & GROCERY) ---
with tabs[3]:
    st.header("🗓 Future Planner")
    with st.expander("Add Appointment"):
        d, o, desc = st.date_input("Date"), st.selectbox("Who?", ["Joy", "Marcy", "Both"]), st.text_input("What?")
        if st.button("Save Appt"): data["appointments"].append({"date": str(d), "owner": o, "desc": desc}); save_data(data); st.rerun()
    st.table(pd.DataFrame(data["appointments"]).sort_values("date") if data["appointments"] else [])

with tabs[4]:
    st.header("🛒 Shopping List")
    now, upd_g = datetime.now(), []
    for i, g in enumerate(data["groceries"]):
        if g["checked"] and g["time"] and (now - datetime.fromisoformat(g["time"]) > timedelta(hours=24)): continue
        c1, c2 = st.columns([1, 9])
        chk = c1.checkbox("", value=g["checked"], key=f"gr_{i}")
        if chk and not g["checked"]: g["checked"], g["time"] = True, now.isoformat()
        elif not chk: g["checked"], g["time"] = False, None
        c2.write(f"~~{g['item']}~~" if chk else g['item'])
        upd_g.append(g)
    data["groceries"] = upd_g
    if st.button("Sync"): save_data(data); st.rerun()
