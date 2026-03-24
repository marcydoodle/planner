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

# --- INITIALIZE & HARDCODE FIX FOR MARCH 24 ---
data = load_data()
today_str = "2026-03-24"
tomorrow_str = "2026-03-25"

# If today is blank, force-inject the data I saw in your screenshots
if today_str not in data["history"] or not data["history"][today_str].get("Joy"):
    data["history"][today_str] = {
        "Joy": {
            "work": "9-5pm", "intensity": 7, "mtg": "None", "energy": 9,
            "after": "Visit the storage unit to gain access and take a view boxes. Put together the dresser if it gets delivered and there is time/desire.",
            "reminders": "None", "need": "Help me move stuff around to preview where the table will be."
        },
        "Marcy": {
            "gym": "Light, high volume leg day around 8-9", "energy": 10,
            "cycle": "20 miles moderate biking with some climbs but not intense, 1 hour",
            "tasks": "Organize transcripts, reach out for letters of recommendation, tryhackme, code academy, newsletter",
            "after": "Mario 64", "reminders": "Swag", "need": "One new thought or memory that I don't know and a head rub"
        }
    }
    save_data(data)

st.set_page_config(page_title="Joy & Marcy Sync", layout="wide")
st.title("🌙 The Daily Sync")

tabs = st.tabs(["📅 Today", "📋 Tomorrow", "📝 Input", "🗓 Planner", "🛒 Groceries"])

def render_rundown(date_key, label):
    """Standard, non-smart rendering."""
    day_data = data["history"].get(date_key, {})
    # Fixed Planner Logic
    day_appts = [a for a in data["appointments"] if str(a.get('date')) == date_key]
    
    st.header(f"{label}: {date_key}")
    
    if not day_data and not day_appts:
        st.info(f"No sync for {date_key}")
        return

    c1, c2 = st.columns(2)
    for name, col in zip(["Joy", "Marcy"], [c1, c2]):
        with col:
            st.subheader(f"{'🌸' if name == 'Joy' else '⚡'} {name}")
            u = day_data.get(name, {})
            
            with st.expander("🌅 Morning & Daytime", expanded=True):
                if name == "Joy":
                    st.write(f"**Work:** {u.get('work', '---')} | **Intensity:** {u.get('intensity', '5')}/10")
                    st.info(f"**Meetings:** {u.get('mtg', 'None')}")
                else:
                    st.write(f"**Gym:** {u.get('gym', 'Rest')} | **Cycling:** {u.get('cycle', 'No')}")
                    st.info(f"**Tasks:** {u.get('tasks', 'None')}")
                
                # Render Appts
                for a in [a['desc'] for a in day_appts if a['owner'] in [name, "Both"]]:
                    st.error(f"⚠️ **Appt:** {a}")

            with st.expander("🌆 After Work & Evening", expanded=True):
                st.write(f"**Plan:** {u.get('after', 'TBD')}")
                st.write(f"**Reminders:** {u.get('reminders', 'None')}")

            with st.container(border=True):
                st.write("**🤝 Partnership**")
                if "energy" in u: st.write(f"**Energy:** {u['energy']}/10")
                if u.get("need"): st.chat_message("user").write(u.get("need"))

# --- TAB 1 & 2 ---
with tabs[0]:
    render_rundown(today_str, "Today")

with tabs[1]:
    render_rundown(tomorrow_str, "Tomorrow")

# --- TAB 3: INPUT ---
with tabs[2]:
    st.header("Nightly Sync")
    target_date = st.date_input("Planning for:", value=get_local_now() + timedelta(days=1))
    t_key = target_date.strftime("%Y-%m-%d")
    user = st.radio("User", ["Joy", "Marcy"], horizontal=True)
    
    with st.form("input_form"):
        st.subheader("🌅 Daytime")
        if user == "Joy":
            w_t, w_i, w_m = st.text_input("Work"), st.select_slider("Int", range(1, 11), 5), st.text_area("Mtgs")
        else:
            gym, cyc, tsk = st.text_input("Gym"), st.text_input("Cycle"), st.text_area("Tasks")
        
        st.subheader("🌆 Evening")
        aft, rem = st.text_input("After"), st.text_area("Reminders")
        
        st.subheader("🤝 Partnership")
        nrg, nd = st.select_slider("Energy", range(0, 11), 5), st.text_area("Need")
        
        st.subheader("🍕 Dinner")
        g_in = st.text_input("Groceries")
        v_cols = st.columns(4)
        v_res = {c: v_cols[i % 4].number_input(c, 0, 10, 0) for i, c in enumerate(CATEGORIES)}

        if st.form_submit_button("Submit"):
            d_up = load_data()
            if t_key not in d_up["history"]: d_up["history"][t_key] = {}
            e = {"energy": nrg, "after": aft, "reminders": rem, "need": nd, "votes": v_res}
            if user == "Joy": e.update({"work": w_t, "mtg": w_m, "intensity": w_i})
            else: e.update({"gym": gym, "cycle": cyc, "tasks": tsk})
            d_up["history"][t_key][user] = e
            if g_in:
                for i in g_in.split(","):
                    if i.strip(): d_up["groceries"].append({"item": i.strip(), "checked": False, "time": None})
            save_data(d_up); st.success(f"Saved to {t_key}"); st.rerun()

# --- TAB 4 & 5 ---
with tabs[3]:
    st.header("🗓 Planner")
    with st.expander("Add Event"):
        d, o, desc = st.date_input("Date"), st.selectbox("Who?", ["Joy", "Marcy", "Both"]), st.text_input("What?")
        if st.button("Save Event"):
            d_save = load_data()
            d_save["appointments"].append({"date": str(d), "owner": o, "desc": desc})
            save_data(d_save); st.rerun()
    if data["appointments"]:
        st.table(pd.DataFrame(data["appointments"]).sort_values("date"))

with tabs[4]:
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
    data["groceries"] = upd_g
    if st.button("Sync"): save_data(data); st.rerun()
