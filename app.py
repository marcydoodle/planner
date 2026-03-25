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
                for k in ["history", "weights", "groceries", "appointments"]:
                    if k not in d: d[k] = {} if k in ["history", "weights"] else []
                return d
            except: pass
    return {
        "weights": {"Joy": {c: 1.0 for c in CATEGORIES}, "Marcy": {c: 1.0 for c in CATEGORIES}},
        "groceries": [], "appointments": [], "history": {}
    }

def save_data(d):
    with open(DATA_FILE, "w") as f:
        json.dump(d, f)

# --- INITIALIZE ---
st.cache_data.clear()
data = load_data()
now_dt = get_local_now()
today_str = now_dt.strftime("%Y-%m-%d")
tomorrow_str = (now_dt + timedelta(days=1)).strftime("%Y-%m-%d")

st.set_page_config(page_title="Joy & Marcy Sync", layout="wide")
st.title("🌙 The Daily Sync")

# --- DINNER BANNER ---
current_winner = data["history"].get(today_str, {}).get("dinner_winner", "TBD")
st.info(f"### 🍴 Tonight's Dinner: {current_winner.upper()}")
st.divider()

tabs = st.tabs(["📅 Today's Plan", "📋 Tomorrow's Rundown", "📝 Nightly Input", "📊 Standings", "🗓 Future Planner", "🛒 Groceries"])

def render_rundown(date_key, label):
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
            
            # 1. DAYTIME BLOCK
            with st.expander("🌅 Morning & Daytime", expanded=True):
                if name == "Joy":
                    st.write(f"**Work:** {u.get('work', '---')} (Int: {u.get('intensity', '5')}/10)")
                    st.info(f"**Meetings:** {u.get('mtg', 'None')}")
                else:
                    st.write(f"**Gym:** {u.get('gym', 'Rest')} | **Cycle:** {u.get('cycle', 'No')}")
                    st.info(f"**Tasks:** {u.get('tasks', 'None')}")
                for a in [a['desc'] for a in day_appts if a['owner'] in [name, "Both"]]:
                    st.error(f"⚠️ **Scheduled:** {a}")
            
            # 2. EVENING BLOCK
            with st.expander("🌆 After Work & Evening", expanded=True):
                st.write(f"**Plan:** {u.get('after', 'TBD')}")
                st.write(f"**Don't Forget:** {u.get('reminders', 'None')}")
            
            # 3. ENERGY STATUS (Separate)
            energy = u.get('energy', '5')
            color = "green" if int(energy) > 7 else "orange" if int(energy) > 4 else "red"
            st.markdown(f"**Current Energy:** :{color}[{energy}/10]")

            # 4. PARTNERSHIP BLOCK (Request Only)
            with st.container(border=True):
                st.write("### 🤝 What we need from each other")
                req = u.get("need")
                if req:
                    st.chat_message("user").write(f"**{name}'s Request:** {req}")
                else:
                    st.caption("No specific request listed.")

# --- TAB LOGIC ---
with tabs[0]: render_rundown(today_str, "Today")
with tabs[1]: render_rundown(tomorrow_str, "Tomorrow")

with tabs[2]:
    st.header("Nightly Sync")
    target_date = st.date_input("Planning for:", value=now_dt.date() + timedelta(days=1))
    t_key = target_date.strftime("%Y-%m-%d")
    user = st.radio("Who are you?", ["Joy", "Marcy"], horizontal=True)
    
    with st.form("input_form"):
        st.subheader("📋 Essentials")
        if user == "Joy":
            w_t, w_i, w_m = st.text_input("Work"), st.select_slider("Intensity", range(1, 11), 5), st.text_area("Meetings")
        else:
            gym, cyc, tsk = st.text_input("Gym"), st.text_input("Cycling"), st.text_area("Tasks")
        aft, rem = st.text_input("Evening Plan"), st.text_area("Reminders")
        
        st.subheader("🤝 Support")
        nrg = st.select_slider("Energy Level", range(0, 11), 5)
        nd = st.text_area("What do you need from your partner tomorrow?")
        
        st.subheader("🛒 Shopping")
        g_add = st.text_input("Add Items to Grocery List (Milk, Bread, etc.)")
        
        st.subheader("🍕 Dinner")
        v_cols = st.columns(4)
        v_res = {c: v_cols[i % 4].number_input(c, 0, 10, 0) for i, c in enumerate(CATEGORIES)}
        
        if st.form_submit_button("Submit Sync"):
            d_up = load_data()
            if t_key not in d_up["history"]: d_up["history"][t_key] = {}
            
            # Save User Data
            entry = {"energy": nrg, "after": aft, "reminders": rem, "need": nd, "votes": v_res}
            if user == "Joy": entry.update({"work": w_t, "mtg": w_m, "intensity": w_i})
            else: entry.update({"gym": gym, "cycle": cyc, "tasks": tsk})
            d_up["history"][t_key][user] = entry
            
            # Save Groceries
            if g_add:
                for item in [i.strip() for i in g_add.split(",") if i.strip()]:
                    d_up["groceries"].append({"item": item, "checked": False, "time": None})
            
            save_data(d_up); st.success("Saved!"); st.rerun()

with tabs[3]:
    st.header("📊 Weights")
    display_data = [{"Category": c, "Joy": f"{data['weights']['Joy'].get(c, 1.0):.2f}x", "Marcy": f"{data['weights']['Marcy'].get(c, 1.0):.2f}x"} for c in CATEGORIES]
    st.table(pd.DataFrame(display_data))

with tabs[5]:
    st.header("🛒 Groceries")
    now_g = get_local_now()
    new_groceries = []
    
    for i, g in enumerate(data["groceries"]):
        if g["checked"] and g["time"] and (now_g - datetime.fromisoformat(g["time"]) > timedelta(hours=24)):
            continue
            
        col1, col2, col3 = st.columns([1, 8, 1])
        is_checked = col1.checkbox("", value=g["checked"], key=f"chk_{i}")
        
        if is_checked and not g["checked"]:
            g["checked"], g["time"] = True, now_g.isoformat()
        elif not is_checked:
            g["checked"], g["time"] = False, None
            
        label = f"~~{g['item']}~~" if is_checked else g['item']
        col2.write(label)
        
        if col3.button("🗑️", key=f"del_{i}"):
            continue
            
        new_groceries.append(g)
    
    if st.button("Sync Changes"):
        data["groceries"] = new_groceries
        save_data(data); st.rerun()
