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
                # Initialize Weights (Multiplier) if they don't exist
                if "weights" not in d:
                    d["weights"] = {
                        "Joy": {c: 1.0 for c in CATEGORIES},
                        "Marcy": {c: 1.0 for c in CATEGORIES}
                    }
                if "history" not in d: d["history"] = {}
                if "groceries" not in d: d["groceries"] = []
                if "appointments" not in d: d["appointments"] = []
                return d
            except: pass
    return {
        "weights": {
            "Joy": {c: 1.0 for c in CATEGORIES},
            "Marcy": {c: 1.0 for c in CATEGORIES}
        },
        "groceries": [], 
        "appointments": [], 
        "history": {}
    }

def save_data(d):
    with open(DATA_FILE, "w") as f:
        json.dump(d, f)

# --- INITIALIZE ---
st.cache_data.clear()
data = load_data()
today_str = "2026-03-24" 
tomorrow_str = "2026-03-25"

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
            with st.expander("🌅 Morning & Daytime", expanded=True):
                if name == "Joy":
                    st.write(f"**Work:** {u.get('work', '---')} (Int: {u.get('intensity', '5')}/10)")
                    st.info(f"**Meetings:** {u.get('mtg', 'None')}")
                else:
                    st.write(f"**Gym:** {u.get('gym', 'Rest')} | **Cycle:** {u.get('cycle', 'No')}")
                    st.info(f"**Tasks:** {u.get('tasks', 'None')}")
                for a in [a['desc'] for a in day_appts if a['owner'] in [name, "Both"]]:
                    st.error(f"⚠️ **Scheduled:** {a}")
            with st.expander("🌆 Evening", expanded=True):
                st.write(f"**Plan:** {u.get('after', 'TBD')}")
                st.write(f"**Don't Forget:** {u.get('reminders', 'None')}")
            if u.get("need"):
                st.chat_message("user").write(f"**{name}'s Need:** {u.get('need')}")

# --- TAB LOGIC ---

with tabs[0]: render_rundown(today_str, "Today")

with tabs[1]:
    render_rundown(tomorrow_str, "Tomorrow")
    if st.button("🏆 Decide Tomorrow's Dinner"):
        fresh_d = load_data()
        w = fresh_d["weights"]
        
        j_v = fresh_d["history"].get(tomorrow_str, {}).get("Joy", {}).get("votes", {})
        m_v = fresh_d["history"].get(tomorrow_str, {}).get("Marcy", {}).get("votes", {})
        
        # CALCULATION: (Vote * Current Category Weight)
        scores = {}
        for c in CATEGORIES:
            val_j = j_v.get(c, 0) * w["Joy"].get(c, 1.0)
            val_m = m_v.get(c, 0) * w["Marcy"].get(c, 1.0)
            scores[c] = val_j + val_m
        
        if any(scores.values()):
            win = max(scores, key=scores.get)
            
            # --- UPDATE WEIGHTS ---
            for c in CATEGORIES:
                if c == win:
                    fresh_d["weights"]["Joy"][c] = 1.0
                    fresh_d["weights"]["Marcy"][c] = 1.0
                else:
                    # Increment weight by 0.05 per point voted
                    fresh_d["weights"]["Joy"][c] += round(j_v.get(c, 0) * 0.05, 2)
                    fresh_d["weights"]["Marcy"][c] += round(m_v.get(c, 0) * 0.05, 2)

            if tomorrow_str not in fresh_d["history"]: fresh_d["history"][tomorrow_str] = {}
            fresh_d["history"][tomorrow_str]["dinner_winner"] = win
            save_data(fresh_d); st.success(f"Winner: {win}!"); st.rerun()

with tabs[2]:
    st.header("Nightly Sync")
    target_date = st.date_input("Planning for:", value=get_local_now().date() + timedelta(days=1))
    t_key = target_date.strftime("%Y-%m-%d")
    user = st.radio("Who are you?", ["Joy", "Marcy"], horizontal=True)
    
    with st.form("input_form"):
        if user == "Joy":
            w_t, w_i, w_m = st.text_input("Work"), st.select_slider("Intensity", range(1, 11), 5), st.text_area("Meetings")
        else:
            gym, cyc, tsk = st.text_input("Gym"), st.text_input("Cycling"), st.text_area("Tasks")
        aft, rem = st.text_input("Evening Plan"), st.text_area("Reminders")
        nrg, nd = st.select_slider("Energy", range(0, 11), 5), st.text_area("Request")
        
        st.subheader("🍕 Dinner Votes")
        st.caption("Votes for losing categories increase your personal weight for that meal by 0.05 per point.")
        v_cols = st.columns(4)
        v_res = {c: v_cols[i % 4].number_input(c, 0, 10, 0) for i, c in enumerate(CATEGORIES)}
        
        if st.form_submit_button("Submit Sync"):
            d_up = load_data()
            if t_key not in d_up["history"]: d_up["history"][t_key] = {}
            e = {"energy": nrg, "after": aft, "reminders": rem, "need": nd, "votes": v_res}
            if user == "Joy": e.update({"work": w_t, "mtg": w_m, "intensity": w_i})
            else: e.update({"gym": gym, "cycle": cyc, "tasks": tsk})
            d_up["history"][t_key][user] = e
            save_data(d_up); st.success("Saved!"); st.rerun()

with tabs[3]:
    st.header("📊 Personal Meal Weights")
    st.write("Your weight increases when you vote for a meal and it loses. It resets to 1.0 when it wins.")
    
    # Visualizing the weight table
    display_data = []
    for c in CATEGORIES:
        display_data.append({
            "Category": c,
            "Joy's Weight": f"{data['weights']['Joy'].get(c, 1.0):.2f}x",
            "Marcy's Weight": f"{data['weights']['Marcy'].get(c, 1.0):.2f}x"
        })
    st.table(pd.DataFrame(display_data))

with tabs[4]:
    st.header("🗓 Future Planner")
    with st.expander("Add Event"):
        d, o, desc = st.date_input("Date"), st.selectbox("Who?", ["Joy", "Marcy", "Both"]), st.text_input("What?")
        if st.button("Save Event"):
            d_save = load_data()
            d_save["appointments"].append({"date": str(d), "owner": o, "desc": desc})
            save_data(d_save); st.rerun()
    if data["appointments"]:
        st.table(pd.DataFrame(data["appointments"]).sort_values("date"))

with tabs[5]:
    st.header("🛒 Groceries")
    now_g = get_local_now()
    upd_g = []
    for i, g in enumerate(data["groceries"]):
        if g["checked"] and g["time"] and (now_g - datetime.fromisoformat(g["time"]) > timedelta(hours=24)): continue
        c1, c2 = st.columns([1, 9])
        chk = c1.checkbox("", value=g["checked"], key=f"gr_{i}")
        if chk and not g["checked"]: g["checked"], g["time"] = True, now_g.isoformat()
        elif not chk: g["checked"], g["time"] = False, None
        c2.write(f"~~{g['item']}~~" if chk else g['item'])
        upd_g.append(g)
    
    new_item = st.text_input("Add item...")
    if st.button("Add"):
        data["groceries"].append({"item": new_item, "checked": False, "time": None})
        save_data(data); st.rerun()
    if st.button("Sync List"): 
        data["groceries"] = upd_g
        save_data(data); st.rerun()
