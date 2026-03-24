import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta

# --- CONFIG & CONSTANTS ---
DATA_FILE = "sync_data.json"
CATEGORIES = ["Mexican", "Asian", "Pasta", "Roast", "Caribbean", "Pizza", "Scrounge", "Starve"]
UTC_OFFSET = -4  # EDT

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

data = load_data()

# DYNAMIC DATE CALCULATION
now = get_local_now()
today_str = now.strftime("%Y-%m-%d")
tomorrow_dt = now + timedelta(days=1)
tomorrow_str = tomorrow_dt.strftime("%Y-%m-%d")

st.set_page_config(page_title="Joy & Marcy Sync", layout="wide", page_icon="🌙")
st.title("🌙 The Daily Sync")
tabs = st.tabs(["📅 Today", "📋 Tomorrow", "📝 Input", "🗓 Planner", "🛒 Groceries"])

def render_rundown(date_key):
    """Renders data including the Dinner Winner if it exists."""
    day_content = data["history"].get(date_key, {})
    day_appts = [a for a in data["appointments"] if a["date"] == date_key]
    
    if not day_content and not day_appts:
        st.info(f"No entries found for {date_key}")
        return

    # SHOW DINNER WINNER AT THE VERY TOP IF DECIDED
    winner = day_content.get("dinner_winner")
    if winner:
        st.success(f"🍴 **Tonight's Dinner: {winner.upper()}**")

    c1, c2 = st.columns(2)
    for name, col in zip(["Joy", "Marcy"], [c1, c2]):
        with col:
            st.subheader(f"{'🌸' if name == 'Joy' else '⚡'} {name}")
            u = day_content.get(name, {})
            
            with st.expander("🌅 Morning & Daytime", expanded=True):
                if name == "Joy":
                    st.write(f"**Work Schedule:** {u.get('work', '---')}")
                    st.write(f"**Intensity:** {u.get('intensity', '5')}/10")
                    st.info(f"**Meetings:**\n{u.get('mtg', 'None')}")
                else:
                    st.write(f"**Gym:** {u.get('gym', 'Rest')}")
                    st.write(f"**Cycling:** {u.get('cycle', 'No')}")
                    st.info(f"**Tasks:**\n{u.get('tasks', 'None')}")
                
                p_appts = [a['desc'] for a in day_appts if a['owner'] in [name, "Both"]]
                if p_appts:
                    st.error("⚠️ **Appts:**\n" + "\n".join([f"- {x}" for x in p_appts]))

            with st.expander("🌆 Evening", expanded=True):
                st.write(f"**Plan:** {u.get('after', 'TBD')}")
                st.write(f"**Reminders:** {u.get('reminders', 'None')}")

            with st.container(border=True):
                st.write("**🤝 Partnership**")
                if "energy" in u:
                    e = u['energy']
                    color = "green" if e > 7 else "orange" if e > 4 else "red"
                    st.markdown(f"**Energy:** :{color}[{e}/10]")
                if u.get("need"):
                    st.chat_message("user").write(u.get("need"))

# --- TAB 1 & 2 ---
with tabs[0]:
    st.header(f"Today: {now.strftime('%A, %b %d')}")
    render_rundown(today_str)

with tabs[1]:
    st.header(f"Tomorrow: {tomorrow_dt.strftime('%A, %b %d')}")
    with st.container(border=True):
        st.write("### 🏆 Dinner Selection")
        if st.button("Decide Tomorrow's Dinner"):
            scores = {}
            j_v = data["history"].get(tomorrow_str, {}).get("Joy", {}).get("votes", {})
            m_v = data["history"].get(tomorrow_str, {}).get("Marcy", {}).get("votes", {})
            for c in CATEGORIES:
                v = j_v.get(c, 0) + m_v.get(c, 0)
                scores[c] = v * data["multipliers"].get(c, 1.0)
            
            # Others
            o_names = {data["history"].get(tomorrow_str, {}).get(u, {}).get("other_name") for u in ["Joy", "Marcy"]}
            for o in o_names:
                if o:
                    o_pts = sum(data["history"].get(tomorrow_str, {}).get(u, {}).get("other_pts", 0) for u in ["Joy", "Marcy"] if data["history"].get(tomorrow_str, {}).get(u, {}).get("other_name") == o)
                    scores[f"Other: {o}"] = o_pts * data["other_multipliers"].get(o, 1.0)

            if any(scores.values()):
                winner = max(scores, key=scores.get)
                # SAVE WINNER TO HISTORY
                if tomorrow_str not in data["history"]: data["history"][tomorrow_str] = {}
                data["history"][tomorrow_str]["dinner_winner"] = winner
                # Multipliers
                for c in CATEGORIES: data["multipliers"][c] = 1.0 if c == winner else data["multipliers"][c] + 0.1
                for o in list(data["other_multipliers"].keys()): data["other_multipliers"][o] = 1.0 if f"Other: {o}" == winner else data["other_multipliers"][o] + 0.1
                save_data(data)
                st.balloons()
                st.rerun()

    render_rundown(tomorrow_str)

# --- TAB 3: INPUT ---
with tabs[2]:
    st.header("Nightly Sync")
    sel_date = st.date_input("Planning Date", value=tomorrow_dt)
    sel_key = sel_date.strftime("%Y-%m-%d")
    user = st.radio("User", ["Joy", "Marcy"], horizontal=True)
    
    with st.form("input_f"):
        st.subheader("🌅 Morning & Daytime")
        if user == "Joy":
            w_t, w_i, w_m = st.text_input("Work Time"), st.select_slider("Intensity", range(1, 11), 5), st.text_area("Meetings")
        else:
            gym, cyc, tsk = st.text_input("Gym"), st.text_input("Cycling"), st.text_area("Tasks")

        st.subheader("🌆 Evening")
        aft, rem = st.text_input("After Work"), st.text_area("Reminders")

        st.subheader("🤝 Partnership")
        nrg, nd = st.select_slider("Energy Level", range(0, 11), 5), st.text_area("Need from Partner")

        st.subheader("🍕 Dinner & Groceries")
        g_in = st.text_input("Add Groceries")
        v_cols = st.columns(4)
        v_res = {c: v_cols[i % 4].number_input(c, 0, 10, 0) for i, c in enumerate(CATEGORIES)}
        oname, opts = st.text_input("Other Meal"), st.number_input("Other Pts", 0, 10, 0)

        if st.form_submit_button("Submit"):
            if sum(v_res.values()) + opts > 10: st.error("Over 10 pts!")
            else:
                if sel_key not in data["history"]: data["history"][sel_key] = {}
                e = {"energy": nrg, "after": aft, "reminders": rem, "need": nd, "votes": v_res, "other_name": oname, "other_pts": opts}
                if user == "Joy": e.update({"work": w_t, "mtg": w_m, "intensity": w_i})
                else: e.update({"gym": gym, "cycle": cyc, "tasks": tsk})
                data["history"][sel_key][user] = e
                if g_in:
                    for i in g_in.split(","):
                        if i.strip(): data["groceries"].append({"item": i.strip(), "checked": False, "time": None})
                if oname and oname not in data["other_multipliers"]: data["other_multipliers"][oname] = 1.0
                save_data(data); st.success(f"Saved for {sel_key}!")

# --- TAB 4 & 5 ---
with tabs[3]:
    st.header("🗓 Planner")
    with st.expander("Add Appt"):
        d, o, desc = st.date_input("Date"), st.selectbox("Who?", ["Joy", "Marcy", "Both"]), st.text_input("What?")
        if st.button("Save"): data["appointments"].append({"date": str(d), "owner": o, "desc": desc}); save_data(data); st.rerun()
    if data["appointments"]: st.table(pd.DataFrame(data["appointments"]).sort_values("date"))

with tabs[4]:
    st.header("🛒 Groceries")
    now_dt, upd_g = get_local_now(), []
    for i, g in enumerate(data["groceries"]):
        if g["checked"] and g["time"] and (now_dt - datetime.fromisoformat(g["time"]) > timedelta(hours=24)): continue
        c1, c2 = st.columns([1, 9])
        chk = c1.checkbox("", value=g["checked"], key=f"gr_{i}")
        if chk and not g["checked"]: g["checked"], g["time"] = True, now_dt.isoformat()
        elif not chk: g["checked"], g["time"] = False, None
        c2.write(f"~~{g['item']}~~" if chk else g['item'])
        upd_g.append(g)
    data["groceries"] = upd_g
    if st.button("Sync"): save_data(data); st.rerun()
