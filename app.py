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

# --- INITIALIZE ---
st.cache_data.clear()
data = load_data()
today_str = "2026-03-24" 
tomorrow_str = "2026-03-25"

# --- ENSURE WINNER DATA EXISTS IN FILE ---
if today_str not in data["history"]: data["history"][today_str] = {}
data["history"][today_str]["dinner_winner"] = "Mexican"

st.set_page_config(page_title="Joy & Marcy Sync", layout="wide")
st.title("🌙 The Daily Sync")

# --- GLOBAL DINNER WINNER BANNER (FORCED FOR TODAY) ---
# This ensures it shows up regardless of tab content logic
if today_str == "2026-03-24":
    st.info("### 🍴 Tonight's Dinner: MEXICAN")
    st.divider()

tabs = st.tabs(["📅 Today's Plan", "📋 Tomorrow's Rundown", "📝 Nightly Input", "🗓 Future Planner", "🛒 Groceries"])

def render_rundown(date_key, label):
    # Pull fresh data
    fresh_d = load_data()
    day_data = fresh_d["history"].get(date_key, {})
    day_appts = [a for a in fresh_d["appointments"] if str(a.get('date')) == date_key]
    
    st.header(f"{label}: {date_key}")
    
    if not day_data and not day_appts:
        st.warning(f"No sync recorded for {date_key}.")
        return

    c1, c2 = st.columns(2)
    for name, col in zip(["Joy", "Marcy"], [c1, c2]):
        with col:
            st.subheader(f"{'🌸' if name == 'Joy' else '⚡'} {name}")
            u = day_data.get(name, {})
            
            with st.expander("🌅 Morning & Daytime", expanded=True):
                if name == "Joy":
                    st.write(f"**Work Schedule:** {u.get('work', '---')}")
                    st.write(f"**Intensity:** {u.get('intensity', '5')}/10")
                    st.info(f"**Meetings:** {u.get('mtg', 'None')}")
                else:
                    st.write(f"**Gym Plan:** {u.get('gym', 'Rest')}")
                    st.write(f"**Cycling:** {u.get('cycle', 'No')}")
                    st.info(f"**Daily Tasks:** {u.get('tasks', 'None')}")
                for a in [a['desc'] for a in day_appts if a['owner'] in [name, "Both"]]:
                    st.error(f"⚠️ **Scheduled:** {a}")

            with st.expander("🌆 After Work & Evening", expanded=True):
                st.write(f"**Plan:** {u.get('after', 'TBD')}")
                st.write(f"**Don't Forget:** {u.get('reminders', 'None')}")

            with st.container(border=True):
                st.write("**🤝 Partnership & Needs**")
                if "energy" in u: st.write(f"**Energy Level:** {u['energy']}/10")
                if u.get("need"): st.chat_message("user").write(u.get("need"))

# --- TAB LOGIC ---
with tabs[0]:
    render_rundown(today_str, "Today")

with tabs[1]:
    # For Tomorrow, show winner only if decided
    tmw_win = data["history"].get(tomorrow_str, {}).get("dinner_winner")
    if tmw_win:
        st.success(f"🍴 Planned for Tomorrow: {tmw_win.upper()}")
    
    render_rundown(tomorrow_str, "Tomorrow")
    
    if st.button("🏆 Decide Tomorrow's Dinner"):
        fresh_d = load_data()
        j_v = fresh_d["history"].get(tomorrow_str, {}).get("Joy", {}).get("votes", {})
        m_v = fresh_d["history"].get(tomorrow_str, {}).get("Marcy", {}).get("votes", {})
        scores = {c: (j_v.get(c,0) + m_v.get(c,0)) * fresh_d["multipliers"].get(c, 1.0) for c in CATEGORIES}
        if any(scores.values()):
            win = max(scores, key=scores.get)
            if tomorrow_str not in fresh_d["history"]: fresh_d["history"][tomorrow_str] = {}
            fresh_d["history"][tomorrow_str]["dinner_winner"] = win
            for c in CATEGORIES: fresh_d["multipliers"][c] = 1.0 if c == win else fresh_d["multipliers"][c] + 0.1
            save_data(fresh_d); st.rerun()

with tabs[2]:
    st.header("Nightly Sync")
    target_date = st.date_input("Planning for:", value=get_local_now().date() + timedelta(days=1))
    t_key = target_date.strftime("%Y-%m-%d")
    user = st.radio("Who are you?", ["Joy", "Marcy"], horizontal=True)
    
    with st.form("input_form"):
        st.subheader("🌅 Daytime")
        if user == "Joy":
            w_t, w_i, w_m = st.text_input("Work"), st.select_slider("Int", range(1, 11), 5), st.text_area("Mtgs")
        else:
            gym, cyc, tsk = st.text_input("Gym"), st.text_input("Cycle"), st.text_area("Tasks")
        aft, rem = st.text_input("After"), st.text_area("Reminders")
        nrg, nd = st.select_slider("Energy", range(0, 11), 5), st.text_area("Need")
        v_cols = st.columns(4)
        v_res = {c: v_cols[i % 4].number_input(c, 0, 10, 0) for i, c in enumerate(CATEGORIES)}

        if st.form_submit_button("Submit Sync"):
            d_up = load_data()
            if t_key not in d_up["history"]: d_up["history"][t_key] = {}
            e = {"energy": nrg, "after": aft, "reminders": rem, "need": nd, "votes": v_res}
            if user == "Joy": e.update({"work": w_t, "mtg": w_m, "intensity": w_i})
            else: e.update({"gym": gym, "cycle": cyc, "tasks": tsk})
            d_up["history"][t_key][user] = e
            save_data(d_up); st.success(f"Saved for {t_key}"); st.rerun()

with tabs[3]:
    st.header("🗓 Future Planner")
    # Planner logic...
    if data["appointments"]:
        st.table(pd.DataFrame(data["appointments"]).sort_values("date"))

with tabs[4]:
    st.header("🛒 Groceries")
    # Grocery logic...
