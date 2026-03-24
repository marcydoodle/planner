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

# --- INITIALIZE ---
st.cache_data.clear()
data = load_data()
now_dt = get_local_now()
today_str = now_dt.strftime("%Y-%m-%d")
tomorrow_str = (now_dt + timedelta(days=1)).strftime("%Y-%m-%d")
yesterday_str = (now_dt - timedelta(days=1)).strftime("%Y-%m-%d")

st.set_page_config(page_title="Joy & Marcy Sync", layout="wide")

# --- SIDEBAR TOOLS ---
with st.sidebar:
    st.header("🛠 Emergency Sync")
    if st.button("🚀 PUSH TOMORROW TO TODAY"):
        if tomorrow_str in data["history"]:
            data["history"][today_str] = data["history"][tomorrow_str]
            save_data(data)
            st.success("Data pushed!")
            st.rerun()

st.title("🌙 The Daily Sync")
st.info(f"📅 **App Date:** {now_dt.strftime('%A, %b %d')} | ⏰ **Time:** {now_dt.strftime('%I:%M %p')}")

tabs = st.tabs(["📅 Today's Plan", "📋 Tomorrow's Rundown", "📝 Nightly Input", "🗓 Future Planner", "🛒 Groceries"])

def render_rundown(date_key, label, is_today=False):
    """Renders the day with the correct Dinner Winner logic."""
    current_data = load_data()
    day_data = current_data["history"].get(date_key, {})
    day_appts = [a for a in current_data["appointments"] if str(a.get('date')) == date_key]
    
    st.header(f"{label}: {date_key}")
    
    # DINNER WINNER LOGIC
    # If it's the Today tab, we look for the winner decided 'Yesterday'
    if is_today:
        yesterday_data = current_data["history"].get(yesterday_str, {})
        winner = yesterday_data.get("dinner_winner")
        if winner:
            st.success(f"🍴 **Tonight's Dinner (Decided Yesterday): {winner.upper()}**")
    else:
        # For Tomorrow's tab, show the winner if it was just decided
        winner = day_data.get("dinner_winner")
        if winner:
            st.success(f"🍴 **Planned Dinner: {winner.upper()}**")

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
                    st.info(f"**Tasks:** {u.get('tasks', 'None')}")
                for a in [a['desc'] for a in day_appts if a['owner'] in [name, "Both"]]:
                    st.error(f"⚠️ **Scheduled:** {a}")

            with st.expander("🌆 After Work & Evening", expanded=True):
                st.write(f"**Plan:** {u.get('after', 'TBD')}")
                st.write(f"**Reminders:** {u.get('reminders', 'None')}")

            with st.container(border=True):
                st.write("**🤝 Partnership & Needs**")
                if "energy" in u:
                    st.write(f"**Energy Level:** {u['energy']}/10")
                if u.get("need"):
                    st.chat_message("user").write(u.get("need"))

# --- TAB LOGIC ---
with tabs[0]:
    render_rundown(today_str, "Today", is_today=True)

with tabs[1]:
    render_rundown(tomorrow_str, "Tomorrow", is_today=False)
    if st.button("🏆 Decide Tomorrow's Dinner"):
        scores = {}
        j_v = data["history"].get(tomorrow_str, {}).get("Joy", {}).get("votes", {})
        m_v = data["history"].get(tomorrow_str, {}).get("Marcy", {}).get("votes", {})
        for c in CATEGORIES:
            v = (j_v.get(c, 0) if j_v else 0) + (m_v.get(c, 0) if m_v else 0)
            scores[c] = v * data["multipliers"].get(c, 1.0)
        if any(scores.values()):
            winner = max(scores, key=scores.get)
            if tomorrow_str not in data["history"]: data["history"][tomorrow_str] = {}
            data["history"][tomorrow_str]["dinner_winner"] = winner
            for c in CATEGORIES: data["multipliers"][c] = 1.0 if c == winner else data["multipliers"][c] + 0.1
            save_data(data); st.balloons(); st.rerun()

with tabs[2]:
    st.header("Nightly Sync")
    target_date = st.date_input("Planning for:", value=now_dt.date() + timedelta(days=1))
    t_key = target_date.strftime("%Y-%m-%d")
    user = st.radio("Who are you?", ["Joy", "Marcy"], horizontal=True)
    
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

        if st.form_submit_button("Submit Sync"):
            d_up = load_data()
            if t_key not in d_up["history"]: d_up["history"][t_key] = {}
            e = {"energy": nrg, "after": aft, "reminders": rem, "need": nd, "votes": v_res}
            if user == "Joy": e.update({"work": w_t, "mtg": w_m, "intensity": w_i})
            else: e.update({"gym": gym, "cycle": cyc, "tasks": tsk})
            d_up["history"][t_key][user] = e
            if g_in:
                for i in g_in.split(","):
                    if i.strip(): d_up["groceries"].append({"item": i.strip(), "checked": False, "time": None})
            save_data(d_up); st.success(f"Saved for {t_key}!"); st.rerun()

# --- PLANNER & GROCERIES ---
with tabs[3]:
    st.header("🗓 Planner")
    with st.expander("Add Event"):
        d, o, desc = st.date_input("Date"), st.selectbox("Who?", ["Joy", "Marcy", "Both"]), st.text_input("What?")
        if st.button("Save Event"):
            d_save = load_data()
            d_save["appointments"].append({"date": str(d), "owner": o, "desc": desc})
            save_data(d_save); st.rerun()
    if data["appointments"]:
        for a in sorted(data["appointments"], key=lambda x: x['date']):
            st.write(f"**{a['date']}** | {a['owner']}: {a['desc']}")

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
    if st.button("Sync List"): save_data(data); st.rerun()
