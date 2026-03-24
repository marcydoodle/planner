import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta

# --- CONFIG ---
DATA_FILE = "sync_data.json"
CATEGORIES = ["Mexican", "Asian", "Pasta", "Roast", "Caribbean", "Pizza", "Scrounge", "Starve"]
UTC_OFFSET = -4  # Eastern Time (EDT)

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

# --- THE AUTO-ROUTER FIX ---
def get_smart_data(data_obj, target_date_str):
    """
    If the requested date is empty, check if there's data in the 
    immediate 'Tomorrow' slot and pull it forward.
    """
    if target_date_str in data_obj["history"]:
        return data_obj["history"][target_date_str]
    
    # Check if we accidentally saved 'Today's' data into 'Tomorrow'
    tmw = (datetime.strptime(target_date_str, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    if tmw in data_obj["history"]:
        return data_obj["history"][tmw]
    
    return {}

# Initialize
data = load_data()
local_now = get_local_now()
today_key = local_now.strftime("%Y-%m-%d")
tomorrow_key = (local_now + timedelta(days=1)).strftime("%Y-%m-%d")

st.set_page_config(page_title="Joy & Marcy Sync", layout="wide")
st.title("🌙 The Daily Sync")

tabs = st.tabs(["📅 Today", "📋 Tomorrow", "📝 Input", "🗓 Planner", "🛒 Groceries"])

def render_rundown(date_key, label, is_today=False):
    # Use the smart router for the Today tab specifically
    day_data = get_smart_data(data, date_key) if is_today else data["history"].get(date_key, {})
    day_appts = [a for a in data["appointments"] if a["date"] == date_key]
    
    st.header(f"{label}: {date_key}")
    
    if not day_data and not day_appts:
        st.warning("No sync data found.")
        return

    c1, c2 = st.columns(2)
    for name, col in zip(["Joy", "Marcy"], [c1, c2]):
        with col:
            st.subheader(f"{'🌸' if name == 'Joy' else '⚡'} {name}")
            u = day_data.get(name, {})
            
            with st.expander("🌅 Morning & Daytime", expanded=True):
                if name == "Joy":
                    st.write(f"**Work Schedule:** {u.get('work', 'None')}")
                    st.write(f"**Intensity:** {u.get('intensity', 'None')}/10")
                    st.info(f"**Meetings:** {u.get('mtg', 'None')}")
                else:
                    st.write(f"**Gym Plan:** {u.get('gym', 'None')}")
                    st.write(f"**Cycling:** {u.get('cycle', 'None')}")
                    st.info(f"**Daily Tasks:** {u.get('tasks', 'None')}")

            with st.expander("🌆 Evening", expanded=True):
                st.write(f"**Plan:** {u.get('after', 'None')}")
                st.write(f"**Don't Forget:** {u.get('reminders', 'None')}")

            with st.container(border=True):
                st.write("**🤝 Partnership & Needs**")
                st.write(f"**Energy Level:** {u.get('energy', 'None')}/10")
                if u.get("need"):
                    st.chat_message("user").write(u.get("need"))

# --- TAB LOGIC ---
with tabs[0]:
    render_rundown(today_key, "Today", is_today=True)

with tabs[1]:
    render_rundown(tomorrow_key, "Tomorrow")

with tabs[2]:
    st.header("Nightly Sync")
    # THE SOURCE OF TRUTH: User explicitly picks the date
    target_date = st.date_input("Which day are you planning for?", value=local_now + timedelta(days=1))
    t_key = target_date.strftime("%Y-%m-%d")
    
    user = st.radio("User", ["Joy", "Marcy"], horizontal=True)
    with st.form("input_form"):
        # Morning Section
        st.subheader("🌅 Daytime")
        if user == "Joy":
            w_t = st.text_input("Work Time")
            w_i = st.select_slider("Intensity", range(1, 11), 5)
            w_m = st.text_area("Meetings")
        else:
            gym = st.text_input("Gym")
            cyc = st.text_input("Cycling")
            tsk = st.text_area("Tasks")
        
        # Evening Section
        st.subheader("🌆 Evening")
        aft = st.text_input("After Work")
        rem = st.text_area("Reminders")
        
        # Partnership Section
        st.subheader("🤝 Partnership")
        nrg = st.select_slider("Energy", range(0, 11), 5)
        nd = st.text_area("Need")
        
        # Dinner & Groceries
        st.subheader("🍕 Dinner & Groceries")
        g_in = st.text_input("Add Groceries")
        v_cols = st.columns(4)
        v_res = {c: v_cols[i % 4].number_input(c, 0, 10, 0) for i, c in enumerate(CATEGORIES)}
        oname = st.text_input("Other Meal")
        opts = st.number_input("Other Pts", 0, 10, 0)

        if st.form_submit_button("Submit Sync"):
            d_up = load_data()
            if t_key not in d_up["history"]: d_up["history"][t_key] = {}
            e = {"energy": nrg, "after": aft, "reminders": rem, "need": nd, "votes": v_res, "other_name": oname, "other_pts": opts}
            if user == "Joy": e.update({"work": w_t, "mtg": w_m, "intensity": w_i})
            else: e.update({"gym": gym, "cycle": cyc, "tasks": tsk})
            d_up["history"][t_key][user] = e
            if g_in:
                for i in g_in.split(","):
                    if i.strip(): d_up["groceries"].append({"item": i.strip(), "checked": False, "time": None})
            save_data(d_up); st.success(f"Saved for {t_key}!")

with tabs[4]:
    st.header("🛒 Groceries")
    now_g = get_local_now()
    upd_g = []
    for i, g in enumerate(data["groceries"]):
        if g["checked"] and g["time"] and (now_g - datetime.fromisoformat(g["time"]) > timedelta(hours=24)): continue
        c1, c2 = st.columns([1, 9])
        chk = c1.checkbox("", value=g["checked"], key=f"gr_{i}")
        if chk and not g["checked"]: g["checked"], g["time"] = now_g.isoformat()
        elif not chk: g["checked"], g["time"] = False, None
        c2.write(f"~~{g['item']}~~" if chk else g['item'])
        upd_g.append(g)
    data["groceries"] = upd_g
    if st.button("Sync"): save_data(data); st.rerun()
