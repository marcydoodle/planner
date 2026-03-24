import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta

# --- CONFIG & CONSTANTS ---
DATA_FILE = "sync_data.json"
CATEGORIES = ["Mexican", "Asian", "Pasta", "Roast", "Caribbean", "Pizza", "Scrounge", "Starve"]
UTC_OFFSET = -4  # Eastern Daylight Time (EDT)

def get_local_now():
    """Returns the current local time based on the UTC offset."""
    return datetime.utcnow() + timedelta(hours=UTC_OFFSET)

def load_data():
    """Directly loads JSON from disk to ensure no stale/cached data."""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            try:
                d = json.load(f)
                # Ensure structure is robust
                required_keys = ["history", "multipliers", "other_multipliers", "groceries", "appointments"]
                for key in required_keys:
                    if key not in d:
                        d[key] = {} if key in ["history", "multipliers", "other_multipliers"] else []
                # Ensure new categories are in multipliers
                for cat in CATEGORIES:
                    if cat not in d["multipliers"]:
                        d["multipliers"][cat] = 1.0
                return d
            except:
                pass
    return {"multipliers": {cat: 1.0 for cat in CATEGORIES}, "other_multipliers": {}, "groceries": [], "appointments": [], "history": {}}

def save_data(data_to_save):
    with open(DATA_FILE, "w") as f:
        json.dump(data_to_save, f)

def force_data_correction(data_obj):
    """
    CRITICAL FIX: If Yesterday has data but Today is empty, 
    it means the user synced 'for tomorrow' and now that day has arrived.
    This function pushes that data into the Today slot.
    """
    now_dt = get_local_now()
    today_str = now_dt.strftime("%Y-%m-%d")
    yesterday_str = (now_dt - timedelta(days=1)).strftime("%Y-%m-%d")
    
    # If Today is empty but Yesterday has data, move it forward
    if yesterday_str in data_obj["history"] and today_str not in data_obj["history"]:
        data_obj["history"][today_str] = data_obj["history"][yesterday_str]
        # We don't delete yesterday so you can still refer to it if needed, 
        # but the app will now show it in 'Today'.
        save_data(data_obj)
    return data_obj

# --- INITIALIZE APP ---
st.set_page_config(page_title="Joy & Marcy Sync", layout="wide", page_icon="🌙")

# 1. Load data
# 2. Force the date shift if necessary
# 3. Define the current keys
data = force_data_correction(load_data())
local_now = get_local_now()
today_key = local_now.strftime("%Y-%m-%d")
tomorrow_key = (local_now + timedelta(days=1)).strftime("%Y-%m-%d")

st.title("🌙 The Daily Sync")
st.info(f"📅 **App Date:** {local_now.strftime('%A, %b %d')} | ⏰ **Local Time:** {local_now.strftime('%I:%M %p')}")

tabs = st.tabs(["📅 Today's Plan", "📋 Tomorrow's Rundown", "📝 Nightly Input", "🗓 Future Planner", "🛒 Groceries"])

def render_rundown(date_key):
    """Displays Joy and Marcy's day in chronological order."""
    day_data = data["history"].get(date_key, {})
    appts = [a for a in data["appointments"] if a["date"] == date_key]
    
    if not day_data and not appts:
        st.warning(f"No sync data found for {date_key}. Use 'Nightly Input' to sync!")
        return

    # Dinner Winner Display
    winner = day_data.get("dinner_winner")
    if winner:
        st.success(f"🍴 **Planned Dinner: {winner.upper()}**")

    col_j, col_m = st.columns(2)
    
    for user_name, col in zip(["Joy", "Marcy"], [col_j, col_m]):
        with col:
            st.subheader(f"{'🌸' if user_name == 'Joy' else '⚡'} {user_name}")
            u_data = day_data.get(user_name, {})

            # 1. MORNING & DAYTIME
            with st.expander("🌅 Morning & Daytime", expanded=True):
                if user_name == "Joy":
                    st.write(f"**Work Schedule:** {u_data.get('work', '---')}")
                    st.write(f"**Work Intensity:** {u_data.get('intensity', '5')}/10")
                    st.info(f"**Meetings:**\n{u_data.get('mtg', 'None scheduled')}")
                else:
                    st.write(f"**Gym Plan:** {u_data.get('gym', 'Rest day')}")
                    st.write(f"**Cycling:** {u_data.get('cycle', 'No ride planned')}")
                    st.info(f"**Daily Tasks:**\n{u_data.get('tasks', 'None listed')}")
                
                p_appts = [a['desc'] for a in appts if a['owner'] in [user_name, "Both"]]
                if p_appts:
                    st.error("⚠️ **Appointments:**\n" + "\n".join([f"- {a}" for a in p_appts]))

            # 2. AFTER WORK & EVENING
            with st.expander("🌆 After Work & Evening", expanded=True):
                st.write(f"**Plan:** {u_data.get('after', 'TBD')}")
                st.write(f"**Don't Forget:** {u_data.get('reminders', 'Nothing special')}")

            # 3. PARTNERSHIP
            with st.container(border=True):
                st.write("**🤝 Partnership & Needs**")
                if "energy" in u_data:
                    e = u_data['energy']
                    color = "green" if e > 7 else "orange" if e > 4 else "red"
                    st.markdown(f"**Energy Level:** :{color}[{e}/10]")
                
                if u_data.get("need"):
                    st.chat_message("user").write(u_data['need'])

# --- TAB 1: TODAY ---
with tabs[0]:
    render_rundown(today_key)

# --- TAB 2: TOMORROW ---
with tabs[1]:
    with st.container(border=True):
        st.write("### 🏆 Dinner Decider")
        if st.button("Decide Tomorrow's Dinner"):
            scores = {}
            j_v = data["history"].get(tomorrow_key, {}).get("Joy", {}).get("votes", {})
            m_v = data["history"].get(tomorrow_key, {}).get("Marcy", {}).get("votes", {})
            
            for c in CATEGORIES:
                v = (j_v.get(c, 0) if j_v else 0) + (m_v.get(c, 0) if m_v else 0)
                scores[c] = v * data["multipliers"].get(c, 1.0)
            
            if any(scores.values()):
                winner = max(scores, key=scores.get)
                if tomorrow_key not in data["history"]: data["history"][tomorrow_key] = {}
                data["history"][tomorrow_key]["dinner_winner"] = winner
                # Multipliers
                for c in CATEGORIES:
                    data["multipliers"][c] = 1.0 if c == winner else data["multipliers"][c] + 0.1
                save_data(data)
                st.balloons()
                st.rerun()
    render_rundown(tomorrow_key)

# --- TAB 3: NIGHTLY INPUT ---
with tabs[2]:
    st.header("Sync for Tomorrow")
    # Date picker defaults to Tomorrow based on local clock
    sel_date = st.date_input("Day to plan:", value=local_now.date() + timedelta(days=1))
    sel_key = sel_date.strftime("%Y-%m-%d")
    user = st.radio("Who are you?", ["Joy", "Marcy"], horizontal=True)
    
    with st.form("input_form"):
        # Morning Section
        st.subheader("🌅 Morning & Daytime")
        if user == "Joy":
            w_time = st.text_input("Work Schedule")
            w_int = st.select_slider("Work Intensity", options=range(1, 11), value=5)
            w_mtg = st.text_area("Meetings")
        else:
            gym = st.text_input("Gym Plan")
            cycle = st.text_input("Cycling Plan")
            tasks = st.text_area("Tasks")

        # Evening Section
        st.subheader("🌆 Evening")
        after = st.text_input("After Work Plans")
        reminders = st.text_area("Reminders")

        # Partnership Section
        st.subheader("🤝 Partnership")
        energy = st.select_slider("⚡ Energy Level (0-10)", options=range(0, 11), value=5)
        need = st.text_area(f"What I need from {'Marcy' if user == 'Joy' else 'Joy'}")
        
        # Dinner & Groceries
        st.subheader("🍕 Dinner & Groceries")
        groc_add = st.text_input("Add Groceries (comma separated)")
        
        st.write("Dinner Votes (10 points total):")
        cols = st.columns(4)
        votes = {cat: cols[i % 4].number_input(cat, 0, 10, 0) for i, cat in enumerate(CATEGORIES)}
        o_name = st.text_input("Other Name")
        o_pts = st.number_input("Other Points", 0, 10, 0)

        if st.form_submit_button("Submit Nightly Sync"):
            if sum(votes.values()) + o_pts > 10:
                st.error("Over 10 points!")
            else:
                # Reload to prevent overwriting partner
                current_data = load_data()
                if sel_key not in current_data["history"]: current_data["history"][sel_key] = {}
                
                entry = {
                    "energy": energy, "after": after, "reminders": reminders, "need": need, 
                    "votes": votes, "other_name": o_name, "other_pts": o_pts
                }
                if user == "Joy": entry.update({"work": w_time, "mtg": w_mtg, "intensity": w_int})
                else: entry.update({"gym": gym, "cycle": cycle, "tasks": tasks})
                
                current_data["history"][sel_key][user] = entry
                if groc_add: 
                    for i in groc_add.split(","): 
                        if i.strip(): current_data["groceries"].append({"item": i.strip(), "checked": False, "time": None})
                
                save_data(current_data)
                st.success(f"Successfully saved for {sel_key}!")

# --- TABS 4 & 5 (PLANNER & GROCERIES) ---
with tabs[3]:
    st.header("🗓 Future Planner")
    with st.expander("Add Item"):
        d, o, desc = st.date_input("Date"), st.selectbox("Who?", ["Joy", "Marcy", "Both"]), st.text_input("Event")
        if st.button("Save"):
            d_save = load_data()
            d_save["appointments"].append({"date": str(d), "owner": o, "desc": desc})
            save_data(d_save); st.rerun()
    if data["appointments"]:
        st.table(pd.DataFrame(data["appointments"]).sort_values("date"))

with tabs[4]:
    st.header("🛒 Shopping List")
    now_dt, upd_g = get_local_now(), []
    for i, g in enumerate(data["groceries"]):
        if g["checked"] and g["time"] and (now_dt - datetime.fromisoformat(g["time"]) > timedelta(hours=24)): continue
        c1, c2 = st.columns([1, 9])
        chk = c1.checkbox("", value=g["checked"], key=f"gr_{i}")
        if chk and not g["checked"]:
            g["checked"], g["time"] = True, now_dt.isoformat()
        elif not chk:
            g["checked"], g["time"] = False, None
        c2.write(f"~~{g['item']}~~" if chk else g['item'])
        upd_g.append(g)
    data["groceries"] = upd_g
    if st.button("Sync"): save_data(data); st.rerun()
