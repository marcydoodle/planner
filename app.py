import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta

# --- CONFIG & CONSTANTS ---
DATA_FILE = "sync_data.json"
CATEGORIES = ["Mexican", "Asian", "Pasta", "Roast", "Caribbean"]

def load_data():
    """Load data with strict migration safety to prevent KeyErrors."""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            try:
                existing_data = json.load(f)
                # Ensure all primary keys exist
                required_keys = ["history", "multipliers", "other_multipliers", "groceries", "appointments"]
                for key in required_keys:
                    if key not in existing_data:
                        existing_data[key] = {} if key in ["history", "multipliers", "other_multipliers"] else []
                return existing_data
            except json.JSONDecodeError:
                pass 
    return {"multipliers": {cat: 1.0 for cat in CATEGORIES}, "other_multipliers": {}, "groceries": [], "appointments": [], "history": {}}

def save_data(data_to_save):
    with open(DATA_FILE, "w") as f:
        json.dump(data_to_save, f)

data = load_data()

# --- APP SETUP ---
st.set_page_config(page_title="Joy & Marcy Sync", layout="wide", page_icon="🌙")
st.title("🌙 The Daily Sync")

tabs = st.tabs(["📅 Today's Plan", "📋 Tomorrow's Rundown", "📝 Nightly Input", "🗓 Future Planner", "🛒 Groceries"])

def render_rundown(target_date_str):
    """Displays Joy and Marcy's day in strict CHRONOLOGICAL order."""
    day_data = data["history"].get(target_date_str, {})
    appts = [a for a in data["appointments"] if a["date"] == target_date_str]
    
    if not day_data and not appts:
        st.info(f"No plans recorded for {target_date_str}. Use 'Nightly Input' to sync.")
        return

    col_j, col_m = st.columns(2)
    
    for user_name, col in zip(["Joy", "Marcy"], [col_j, col_m]):
        with col:
            st.subheader(f"{'🌸' if user_name == 'Joy' else '⚡'} {user_name}")
            u_data = day_data.get(user_name, {})
            
            # 1. Energy Status (Top of Chronological Flow)
            if "energy" in u_data:
                e = u_data['energy']
                color = "green" if e > 7 else "orange" if e > 4 else "red"
                st.markdown(f"**Energy Level:** :{color}[{e}/10]")

            # 2. Morning & Daytime
            with st.expander("🌅 Morning & Daytime", expanded=True):
                if user_name == "Joy":
                    st.write(f"**Work Schedule:** {u_data.get('work', 'Not specified')}")
                    st.write(f"**Work Intensity:** {u_data.get('intensity', '5')}/10")
                    st.info(f"**Meetings:**\n{u_data.get('mtg', 'None scheduled')}")
                else:
                    st.write(f"**Gym Plan:** {u_data.get('gym', 'Rest day')}")
                    st.write(f"**Cycling:** {u_data.get('cycle', 'No ride')}")
                    st.info(f"**Daily Tasks:**\n{u_data.get('tasks', 'None listed')}")
                
                # Auto-pull from Future Planner
                p_appts = [a['desc'] for a in appts if a['owner'] in [user_name, "Both"]]
                if p_appts:
                    st.error("⚠️ **Scheduled Appointments:**\n" + "\n".join([f"- {a}" for a in p_appts]))

            # 3. After Work & Evening
            with st.expander("🌆 After Work & Evening", expanded=True):
                st.write(f"**Plan:** {u_data.get('after', 'TBD')}")
                st.write(f"**Reminders:** {u_data.get('reminders', 'None')}")

            # 4. Partnership Needs
            if u_data.get("need"):
                st.chat_message("user").write(f"**Need from partner:** {u_data['need']}")

# --- TAB 1 & 2: RUNDOWNS ---
with tabs[0]:
    t_key = datetime.now().strftime("%Y-%m-%d")
    st.header(f"Today: {datetime.now().strftime('%A, %b %d')}")
    render_rundown(t_key)

with tabs[1]:
    tmw_date = datetime.now() + timedelta(days=1)
    tmw_key = tmw_date.strftime("%Y-%m-%d")
    st.header(f"Tomorrow: {tmw_date.strftime('%A, %b %d')}")
    
    # Dinner Algorithm
    with st.container(border=True):
        st.write("🍴 **Dinner Selection Logic**")
        if st.button("🏆 Run Selection Algorithm"):
            scores = {}
            j_in = data["history"].get(tmw_key, {}).get("Joy", {})
            m_in = data["history"].get(tmw_key, {}).get("Marcy", {})
            
            # Standard Multiplier Calc
            for c in CATEGORIES:
                v = j_in.get("votes", {}).get(c, 0) + m_in.get("votes", {}).get(c, 0)
                scores[c] = v * data["multipliers"].get(c, 1.0)
            
            # "Other" Multiplier Calc
            others = {d.get("other_name") for d in [j_in, m_in] if d.get("other_name")}
            for o in others:
                pts = (j_in.get("other_pts", 0) if j_in.get("other_name") == o else 0) + \
                      (m_in.get("other_pts", 0) if m_in.get("other_name") == o else 0)
                scores[f"Other: {o}"] = pts * data["other_multipliers"].get(o, 1.0)

            if scores and any(scores.values()):
                winner = max(scores, key=scores.get)
                st.balloons(); st.success(f"Winner: **{winner.upper()}**")
                # Reset winner, increment losers
                for c in CATEGORIES: data["multipliers"][c] = 1.0 if c == winner else data["multipliers"][c] + 0.1
                for o in list(data["other_multipliers"].keys()): 
                    data["other_multipliers"][o] = 1.0 if f"Other: {o}" == winner else data["other_multipliers"][o] + 0.1
                save_data(data)
            else:
                st.warning("No dinner votes found for tomorrow yet!")

    render_rundown(tmw_key)

# --- TAB 3: NIGHTLY INPUT (CHRONOLOGICAL) ---
with tabs[2]:
    st.header("Sync for Tomorrow")
    target_date = st.date_input("Planning Date:", value=datetime.now() + timedelta(days=1))
    t_key = target_date.strftime("%Y-%m-%d")
    user_choice = st.radio("Who are you?", ["Joy", "Marcy"], horizontal=True)
    
    with st.form("input_form"):
        st.subheader("🌅 Start of Day & Work")
        energy = st.select_slider("⚡ Energy Level (0-10)", options=range(0, 11), value=5)
        
        if user_choice == "Joy":
            w_time = st.text_input("Work Schedule")
            w_int = st.select_slider("Work Intensity (1-10)", options=range(1, 11), value=5)
            w_mtg = st.text_area("Meetings & Calls")
        else:
            gym = st.text_input("Gym Plan")
            cycle = st.text_input("Cycling Plan")
            tasks = st.text_area("Daily Tasks")

        st.subheader("🌆 After Work & Evening")
        after = st.text_input("After Work Plans")
        reminders = st.text_area("Reminders")

        st.subheader("🤝 Partnership")
        need = st.text_area(f"What I need from {'Marcy' if user_choice == 'Joy' else 'Joy'}")
        
        st.subheader("🍕 Dinner & Groceries")
        groc_add = st.text_input("Add Groceries (comma separated)")
        
        cols = st.columns(len(CATEGORIES) + 1)
        votes = {cat: cols[i].number_input(cat, 0, 10, 0) for i, cat in enumerate(CATEGORIES)}
        o_name = cols[-1].text_input("Other Name")
        o_pts = cols[-1].number_input("Other Pts", 0, 10, 0)

        if st.form_submit_button("Submit Plan"):
            if sum(votes.values()) + o_pts > 10:
                st.error("Point total exceeds 10!")
            else:
                if t_key not in data["history"]: data["history"][t_key] = {}
                entry = {"energy": energy, "after": after, "reminders": reminders, "need": need, "votes": votes, "other_name": o_name, "other_pts": o_pts}
                if user_choice == "Joy": entry.update({"work": w_time, "mtg": w_mtg, "intensity": w_int})
                else: entry.update({"gym": gym, "cycle": cycle, "tasks": tasks})
                
                data["history"][t_key][user_choice] = entry
                if groc_add: 
                    for i in groc_add.split(","): 
                        if i.strip(): data["groceries"].append({"item": i.strip(), "checked": False, "time": None})
                if o_name and o_name not in data["other_multipliers"]: data["other_multipliers"][o_name] = 1.0
                save_data(data); st.success(f"Successfully saved for {t_key}!")

# --- TAB 4: FUTURE PLANNER ---
with tabs[3]:
    st.header("🗓 Long-Term Appointments")
    with st.expander("Add New Item"):
        d, o, desc = st.date_input("Date"), st.selectbox("For?", ["Joy", "Marcy", "Both"]), st.text_input("Event")
        if st.button("Save to Planner"):
            data["appointments"].append({"date": str(d), "owner": o, "desc": desc})
            save_data(data); st.rerun()
    if data["appointments"]:
        st.table(pd.DataFrame(data["appointments"]).sort_values("date"))
        if st.button("Clear Past Items"):
            today_str = datetime.now().strftime("%Y-%m-%d")
            data["appointments"] = [a for a in data["appointments"] if a["date"] >= today_str]
            save_data(data); st.rerun()

# --- TAB 5: GROCERIES ---
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
    if st.button("Sync & Purge Old Items"): save_data(data); st.rerun()
