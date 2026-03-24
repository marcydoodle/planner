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
    """Returns exact local time to prevent server-side 'date-drift'."""
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

st.set_page_config(page_title="Joy & Marcy Sync", layout="wide")
st.title("🌙 The Daily Sync")

# --- SIDEBAR: SYSTEM CHECK ---
with st.sidebar:
    st.header("🕵️‍♂️ Data Auditor")
    st.write(f"**Actual Today:** {today_str}")
    st.write(f"**Actual Tomorrow:** {tomorrow_str}")
    
    # List all dates that actually have data
    stored_dates = sorted([k for k in data["history"].keys() if k != "multipliers"])
    st.write("**Data found for these dates:**")
    for d_key in stored_dates:
        st.write(f"- {d_key}")
    
    if st.button("♻️ Force System Refresh"):
        st.rerun()

tabs = st.tabs(["📅 Today", "📋 Tomorrow", "📝 Input", "🗓 Planner", "🛒 Groceries"])

def render_rundown(date_key, label):
    """Strictly renders the specific date requested."""
    # Force a fresh file read to bypass any memory issues
    current_data = load_data()
    day_data = current_data["history"].get(date_key, {})
    day_appts = [a for a in current_data["appointments"] if a["date"] == date_key]
    
    st.header(f"{label}: {date_key}")
    
    if not day_data and not day_appts:
        st.warning(f"No sync data found in the file for {date_key}.")
        return

    # Dinner Winner
    winner = day_data.get("dinner_winner")
    if winner: st.success(f"🍴 **Planned Dinner: {winner.upper()}**")

    c1, c2 = st.columns(2)
    for name, col in zip(["Joy", "Marcy"], [c1, c2]):
        with col:
            st.subheader(f"{'🌸' if name == 'Joy' else '⚡'} {name}")
            u = day_data.get(name, {})
            
            with st.expander("🌅 Morning & Daytime", expanded=True):
                if name == "Joy":
                    st.write(f"**Work:** {u.get('work', '---')} | **Intensity:** {u.get('intensity', '5')}/10")
                    st.info(f"**Meetings:**\n{u.get('mtg', 'None')}")
                else:
                    st.write(f"**Gym:** {u.get('gym', 'Rest')} | **Cycling:** {u.get('cycle', 'No')}")
                    st.info(f"**Tasks:**\n{u.get('tasks', 'None')}")
                # Pull appts
                for a in [a['desc'] for a in day_appts if a['owner'] in [name, "Both"]]:
                    st.error(f"⚠️ **Appt:** {a}")

            with st.expander("🌆 After Work & Evening", expanded=True):
                st.write(f"**Plan:** {u.get('after', 'TBD')}")
                st.write(f"**Reminders:** {u.get('reminders', 'None')}")

            with st.container(border=True):
                st.write("**🤝 Partnership**")
                if "energy" in u:
                    st.write(f"**Energy:** {u['energy']}/10")
                if u.get("need"):
                    st.chat_message("user").write(u.get("need"))

# --- TAB 1: TODAY ---
with tabs[0]:
    render_rundown(today_str, "Today")

# --- TAB 2: TOMORROW ---
with tabs[1]:
    render_rundown(tomorrow_str, "Tomorrow")
    if st.button("🏆 Finalize Tomorrow's Dinner"):
        j_v = data["history"].get(tomorrow_str, {}).get("Joy", {}).get("votes", {})
        m_v = data["history"].get(tomorrow_str, {}).get("Marcy", {}).get("votes", {})
        scores = {c: (j_v.get(c, 0) + m_v.get(c, 0)) * data["multipliers"].get(c, 1.0) for c in CATEGORIES}
        if any(scores.values()):
            winner = max(scores, key=scores.get)
            if tomorrow_str not in data["history"]: data["history"][tomorrow_str] = {}
            data["history"][tomorrow_str]["dinner_winner"] = winner
            for c in CATEGORIES: data["multipliers"][c] = 1.0 if c == winner else data["multipliers"][c] + 0.1
            save_data(data); st.rerun()

# --- TAB 3: INPUT ---
with tabs[2]:
    st.header("Nightly Sync")
    # Date picker defaults to tomorrow based on the EDT clock
    planning_for = st.date_input("What day are you planning for?", value=now_dt.date() + timedelta(days=1))
    p_key = planning_for.strftime("%Y-%m-%d")
    st.write(f"Saving to: **{planning_for.strftime('%A, %b %d')}**")
    
    user = st.radio("User", ["Joy", "Marcy"], horizontal=True)
    with st.form("sync_form"):
        st.subheader("🌅 Daytime")
        if user == "Joy":
            w_t, w_i, w_m = st.text_input("Work Time"), st.select_slider("Intensity", range(1, 11), 5), st.text_area("Meetings")
        else:
            gym, cyc, tsk = st.text_input("Gym"), st.text_input("Cycling"), st.text_area("Tasks")
        
        st.subheader("🌆 Evening")
        aft, rem = st.text_input("After Work"), st.text_area("Reminders")
        
        st.subheader("🤝 Partnership")
        nrg, nd = st.select_slider("Energy", range(0, 11), 5), st.text_area("Need")
        
        st.subheader("🍕 Dinner & Groceries")
        g_in = st.text_input("Add Groceries")
        v_cols = st.columns(4)
        v_res = {c: v_cols[i % 4].number_input(c, 0, 10, 0) for i, c in enumerate(CATEGORIES)}
        oname, opts = st.text_input("Other Meal"), st.number_input("Other Pts", 0, 10, 0)

        if st.form_submit_button("Submit Sync"):
            # Deep reload to prevent overwriting partner's work
            current_data = load_data()
            if p_key not in current_data["history"]: current_data["history"][p_key] = {}
            
            entry = {"energy": nrg, "after": aft, "reminders": rem, "need": nd, "votes": v_res, "other_name": oname, "other_pts": opts}
            if user == "Joy": entry.update({"work": w_t, "mtg": w_m, "intensity": w_i})
            else: entry.update({"gym": gym, "cycle": cyc, "tasks": tsk})
            
            current_data["history"][p_key][user] = entry
            if g_in:
                for i in g_in.split(","):
                    if i.strip(): current_data["groceries"].append({"item": i.strip(), "checked": False, "time": None})
            
            save_data(current_data); st.success(f"Saved for {p_key}!")

# --- PLANNER & GROCERIES ---
with tabs[3]:
    st.header("🗓 Planner")
    with st.expander("Add Appt"):
        d, o, desc = st.date_input("Date"), st.selectbox("Who?", ["Joy", "Marcy", "Both"]), st.text_input("What?")
        if st.button("Save Appt"):
            d_save = load_data()
            d_save["appointments"].append({"date": str(d), "owner": o, "desc": desc})
            save_data(d_save); st.rerun()
    if data["appointments"]: st.table(pd.DataFrame(data["appointments"]).sort_values("date"))

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
