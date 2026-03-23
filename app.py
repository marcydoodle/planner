import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta

# --- CONFIG & CONSTANTS ---
DATA_FILE = "sync_data.json"
CATEGORIES = ["Mexican", "Asian", "Pasta", "Roast", "Caribbean"]

def load_data():
    """Load data with migration safety checks to prevent KeyErrors."""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            try:
                existing_data = json.load(f)
                # Migration: Add missing keys if they don't exist in the old JSON
                if "history" not in existing_data:
                    existing_data["history"] = {}
                if "multipliers" not in existing_data:
                    existing_data["multipliers"] = {cat: 1.0 for cat in CATEGORIES}
                if "other_multipliers" not in existing_data:
                    existing_data["other_multipliers"] = {}
                if "groceries" not in existing_data:
                    existing_data["groceries"] = []
                if "appointments" not in existing_data:
                    existing_data["appointments"] = []
                return existing_data
            except json.JSONDecodeError:
                pass # If file is corrupted, return the default structure below
    
    return {
        "multipliers": {cat: 1.0 for cat in CATEGORIES},
        "other_multipliers": {}, 
        "groceries": [],
        "appointments": [],
        "history": {} 
    }

def save_data(data_to_save):
    with open(DATA_FILE, "w") as f:
        json.dump(data_to_save, f)

# Initialize Data
data = load_data()

# --- APP SETUP ---
st.set_page_config(page_title="Joy & Marcy Sync", layout="wide")
st.title("🌙 The Daily Sync")

tabs = st.tabs(["📅 Today's Plan", "📋 Tomorrow's Rundown", "📝 Nightly Input", "🗓 Future Planner", "🛒 Groceries"])

def render_rundown(target_date_str):
    """Displays Joy and Marcy's day in chronological order."""
    day_data = data["history"].get(target_date_str, {})
    appts = [a for a in data["appointments"] if a["date"] == target_date_str]
    
    if not day_data and not appts:
        st.info(f"No plans recorded for {target_date_str}. Use the 'Nightly Input' tab to sync!")
        return

    col_j, col_m = st.columns(2)
    
    for user_name, col in zip(["Joy", "Marcy"], [col_j, col_m]):
        with col:
            st.subheader(f"{'🌸' if user_name == 'Joy' else '⚡'} {user_name}")
            u_data = day_data.get(user_name, {})
            
            # 1. Energy Metric (Top Level)
            if "energy" in u_data:
                st.metric("Energy Level", f"{u_data['energy']}/10")

            # 2. Work / Morning Section (Chronological)
            with st.expander("💼 Work & Daytime Plan", expanded=True):
                if user_name == "Joy":
                    st.write(f"**Schedule:** {u_data.get('work', '---')}")
                    st.write(f"**Intensity:** {u_data.get('intensity', '5')}/10")
                    st.info(f"**Meetings:**\n{u_data.get('mtg', 'None scheduled')}")
                else:
                    st.write(f"**Gym:** {u_data.get('gym', 'Rest Day')}")
                    st.write(f"**Cycling:** {u_data.get('cycle', 'No ride planned')}")
                    st.info(f"**Tasks:**\n{u_data.get('tasks', 'None listed')}")
                
                # Filter appointments for this person
                person_appts = [a['desc'] for a in appts if a['owner'] in [user_name, "Both"]]
                if person_appts:
                    st.warning("**Appointments:**\n" + "\n".join([f"- {a}" for a in person_appts]))

            # 3. After Work Section
            with st.expander("🌆 After Work & Evening", expanded=True):
                st.write(f"**Plan:** {u_data.get('after', 'Staying in')}")
                st.write(f"**Reminders:** {u_data.get('reminders', 'None')}")

            # 4. Partnership Needs (Communication)
            if "need" in u_data:
                st.chat_message("user").write(f"**Need from partner:** {u_data['need']}")

# --- TAB 1: TODAY'S PLAN ---
with tabs[0]:
    today_key = datetime.now().strftime("%Y-%m-%d")
    st.header(f"Today: {datetime.now().strftime('%A, %b %d')}")
    render_rundown(today_key)

# --- TAB 2: TOMORROW'S RUNDOWN ---
with tabs[1]:
    tmw_date = datetime.now() + timedelta(days=1)
    tmw_key = tmw_date.strftime("%Y-%m-%d")
    st.header(f"Tomorrow: {tmw_date.strftime('%A, %b %d')}")
    
    # Dinner logic trigger
    if st.button("🏆 Calculate Tomorrow's Dinner Winner"):
        scores = {}
        j_in = data["history"].get(tmw_key, {}).get("Joy", {})
        m_in = data["history"].get(tmw_key, {}).get("Marcy", {})
        
        # Calculate standard categories
        for cat in CATEGORIES:
            pts = j_in.get("votes", {}).get(cat, 0) + m_in.get("votes", {}).get(cat, 0)
            scores[cat] = pts * data["multipliers"].get(cat, 1.0)
            
        # Add 'Other' to calculation
        all_others = set([j_in.get("other_name"), m_in.get("other_name")])
        for o_name in all_others:
            if o_name:
                o_pts = (j_in.get("other_pts", 0) if j_in.get("other_name") == o_name else 0) + \
                        (m_in.get("other_pts", 0) if m_in.get("other_name") == o_name else 0)
                scores[f"Other: {o_name}"] = o_pts * data["other_multipliers"].get(o_name, 1.0)

        if any(scores.values()):
            winner = max(scores, key=scores.get)
            st.balloons()
            st.success(f"The Winner is: **{winner.upper()}**")
            # Multiplier updates
            for c in CATEGORIES:
                data["multipliers"][c] = 1.0 if c == winner else data["multipliers"][c] + 0.1
            for on in list(data["other_multipliers"].keys()):
                data["other_multipliers"][on] = 1.0 if f"Other: {on}" == winner else data["other_multipliers"][on] + 0.1
            save_data(data)
        else:
            st.warning("No dinner votes found for tomorrow yet!")

    render_rundown(tmw_key)

# --- TAB 3: NIGHTLY INPUT ---
with tabs[2]:
    st.header("Sync for Tomorrow")
    target_date = st.date_input("Day to plan:", value=datetime.now() + timedelta(days=1))
    t_key = target_date.strftime("%Y-%m-%d")
    
    user = st.radio("Who are you?", ["Joy", "Marcy"], horizontal=True)
    
    with st.form("input_form"):
        energy = st.select_slider("⚡ Your Energy Level (0-10)", options=range(0, 11), value=5)
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
            tasks = st.text_area("Tasks for the day")
            need = st.text_area("What I need from Joy")
            
        groc_add = st.text_input("Groceries to add (comma separated)")
        
        st.subheader("🍕 Dinner Voting (10 Points Total)")
        col_pts = st.columns(len(CATEGORIES) + 1)
        votes = {}
        for i, cat in enumerate(CATEGORIES):
            votes[cat] = col_pts[i].number_input(cat, 0, 10, 0)
        
        o_name = col_pts[-1].text_input("Other (e.g. Sushi)")
        o_pts = col_pts[-1].number_input("Other Points", 0, 10, 0)

        if st.form_submit_button("Submit Plan"):
            if sum(votes.values()) + o_pts > 10:
                st.error("You used more than 10 points!")
            else:
                if t_key not in data["history"]: data["history"][t_key] = {}
                
                entry = {"energy": energy, "after": after, "reminders": reminders, "need": need, "votes": votes, "other_name": o_name, "other_pts": o_pts}
                if user == "Joy": entry.update({"work": w_time, "mtg": w_mtg, "intensity": w_int})
                else: entry.update({"gym": gym, "cycle": cycle, "tasks": tasks})
                
                data["history"][t_key][user] = entry
                
                if groc_add:
                    for item in groc_add.split(","):
                        if item.strip(): data["groceries"].append({"item": item.strip(), "checked": False, "time": None})
                
                if o_name and o_name not in data["other_multipliers"]:
                    data["other_multipliers"][o_name] = 1.0
                
                save_data(data)
                st.success(f"Successfully saved for {t_key}!")

# --- TAB 4: FUTURE PLANNER ---
with tabs[3]:
    st.header("🗓 Long-Term Appointments")
    with st.expander("Add Future Appointment"):
        new_d = st.date_input("Date", value=datetime.now() + timedelta(days=7))
        new_o = st.selectbox("Who for?", ["Joy", "Marcy", "Both"])
        new_desc = st.text_input("What's happening?")
        if st.button("Save to Planner"):
            data["appointments"].append({"date": str(new_d), "owner": new_o, "desc": new_desc})
            save_data(data); st.rerun()

    if data["appointments"]:
        df = pd.DataFrame(data["appointments"]).sort_values("date")
        st.table(df)
        if st.button("Clean Past Appointments"):
            today_str = datetime.now().strftime("%Y-%m-%d")
            data["appointments"] = [a for a in data["appointments"] if a["date"] >= today_str]
            save_data(data); st.rerun()

# --- TAB 5: GROCERIES ---
with tabs[4]:
    st.header("🛒 Shared Shopping List")
    now = datetime.now()
    upd_g = []
    for i, g in enumerate(data["groceries"]):
        if g["checked"] and g["time"] and (now - datetime.fromisoformat(g["time"]) > timedelta(hours=24)):
            continue
        c1, c2 = st.columns([1, 9])
        chk = c1.checkbox("", value=g["checked"], key=f"gr_{i}")
        if chk and not g["checked"]:
            g["checked"], g["time"] = True, now.isoformat()
        elif not chk:
            g["checked"], g["time"] = False, None
        c2.write(f"~~{g['item']}~~" if chk else g['item'])
        upd_g.append(g)
    
    data["groceries"] = upd_g
    if st.button("Sync Grocery List"):
        save_data(data); st.rerun()
