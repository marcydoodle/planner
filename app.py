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
                # Ensure all necessary keys exist
                if "history" not in d: d["history"] = {}
                if "multipliers" not in d: d["multipliers"] = {c: 1.0 for c in CATEGORIES}
                if "vote_powers" not in d: d["vote_powers"] = {"Joy": 1.0, "Marcy": 1.0}
                if "groceries" not in d: d["groceries"] = []
                if "appointments" not in d: d["appointments"] = []
                return d
            except: pass
    return {
        "multipliers": {c: 1.0 for c in CATEGORIES}, 
        "vote_powers": {"Joy": 1.0, "Marcy": 1.0},
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

# --- ENSURE WINNER DATA EXISTS FOR TODAY ---
if today_str not in data["history"]: 
    data["history"][today_str] = {"dinner_winner": "Mexican"}

st.set_page_config(page_title="Joy & Marcy Sync", layout="wide")
st.title("🌙 The Daily Sync")

# --- GLOBAL DINNER WINNER BANNER ---
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

# --- TABS ---

with tabs[0]:
    render_rundown(today_str, "Today")

with tabs[1]:
    render_rundown(tomorrow_str, "Tomorrow")
    if st.button("🏆 Decide Tomorrow's Dinner"):
        fresh_d = load_data()
        powers = fresh_d.get("vote_powers", {"Joy": 1.0, "Marcy": 1.0})
        
        j_v = fresh_d["history"].get(tomorrow_str, {}).get("Joy", {}).get("votes", {})
        m_v = fresh_d["history"].get(tomorrow_str, {}).get("Marcy", {}).get("votes", {})
        
        # SCORE CALCULATION: (Individual Vote * Personal Power) * Category Multiplier
        scores = {}
        for c in CATEGORIES:
            weighted_j = j_v.get(c, 0) * powers.get("Joy", 1.0)
            weighted_m = m_v.get(c, 0) * powers.get("Marcy", 1.0)
            scores[c] = (weighted_j + weighted_m) * fresh_d["multipliers"].get(c, 1.0)
        
        if any(scores.values()):
            win = max(scores, key=scores.get)
            
            # --- UPDATE POWER FOR NEXT TIME ---
            new_powers = {"Joy": 1.0, "Marcy": 1.0}
            for person, votes in [("Joy", j_v), ("Marcy", m_v)]:
                # Calculate "Lost Potential" (points spent on things that didn't win)
                lost_points = sum([v for cat, v in votes.items() if cat != win])
                # Increase power by 5% per lost point. Maxes out significantly.
                new_powers[person] = round(1.0 + (lost_points * 0.05), 2)

            if tomorrow_str not in fresh_d["history"]: fresh_d["history"][tomorrow_str] = {}
            fresh_d["history"][tomorrow_str]["dinner_winner"] = win
            fresh_d["vote_powers"] = new_powers
            
            # Update category multipliers
            for c in CATEGORIES: 
                fresh_d["multipliers"][c] = 1.0 if c == win else fresh_d["multipliers"][c] + 0.1
            
            save_data(fresh_d)
            st.success(f"Winner: {win}!")
            st.rerun()

with tabs[2]:
    st.header("Nightly Sync")
    target_date = st.date_input("Planning for:", value=get_local_now().date() + timedelta(days=1))
    t_key = target_date.strftime("%Y-%m-%d")
    user = st.radio("Who are you?", ["Joy", "Marcy"], horizontal=True)
    
    with st.form("input_form"):
        st.subheader("🌅 Daytime")
        if user == "Joy":
            w_t, w_i, w_m = st.text_input("Work"), st.select_slider("Intensity", range(1, 11), 5), st.text_area("Meetings")
        else:
            gym, cyc, tsk = st.text_input("Gym"), st.text_input("Cycling"), st.text_area("Tasks")
        
        aft, rem = st.text_input("After Work Plan"), st.text_area("Reminders")
        nrg, nd = st.select_slider("Energy Level", range(0, 11), 5), st.text_area("Specific Need/Request")
        
        st.subheader("🍕 Dinner Votes (0-10)")
        v_cols = st.columns(4)
        v_res = {c: v_cols[i % 4].number_input(c, 0, 10, 0) for i, c in enumerate(CATEGORIES)}
        
        if st.form_submit_button("Submit Sync"):
            d_up = load_data()
            if t_key not in d_up["history"]: d_up["history"][t_key] = {}
            e = {"energy": nrg, "after": aft, "reminders": rem, "need": nd, "votes": v_res}
            if user == "Joy": e.update({"work": w_t, "mtg": w_m, "intensity": w_i})
            else: e.update({"gym": gym, "cycle": cyc, "tasks": tsk})
            d_up["history"][t_key][user] = e
            save_data(d_up)
            st.success("Sync Saved!")
            st.rerun()

with tabs[3]:
    st.header("📊 Dinner Standings")
    
    # 1. SHOW CURRENT VOTE POWER
    powers = data.get("vote_powers", {"Joy": 1.0, "Marcy": 1.0})
    st.subheader("⚡ Influence Levels")
    c1, c2 = st.columns(2)
    c1.metric("Joy's Influence", f"{powers['Joy']}x")
    c2.metric("Marcy's Influence", f"{powers['Marcy']}x")
    st.caption("If you lost the vote yesterday, your weight is boosted today.")
    
    st.divider()
    
    # 2. SHOW CATEGORY MULTIPLIERS
    st.subheader("📈 Category Multipliers")
    m_data = [{"Category": k, "Multiplier": round(v, 2)} for k, v in data["multipliers"].items()]
    df_m = pd.DataFrame(m_data).sort_values("Multiplier", ascending=False)
    
    col_a, col_b = st.columns([2, 1])
    with col_a:
        st.dataframe(df_m, use_container_width=True, hide_index=True)
    with col_b:
        st.write("**Recent Wins:**")
        history_dates = sorted([k for k in data["history"].keys() if isinstance(data["history"][k], dict)], reverse=True)
        for d_key in history_dates[:7]:
            win = data["history"][d_key].get("dinner_winner")
            if win: st.write(f"*{d_key}:* **{win}**")

with tabs[4]:
    st.header("🗓 Future Planner")
    with st.expander("Add Event"):
        d, o, desc = st.date_input("Date"), st.selectbox("Who?", ["Joy", "Marcy", "Both"]), st.text_input("What?")
        if st.button("Save Event"):
            d_save = load_data()
            d_save["appointments"].append({"date": str(d), "owner": o, "desc": desc})
            save_data(d_save)
            st.rerun()
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
    
    new_item = st.text_input("Add to list...")
    if st.button("Add"):
        data["groceries"].append({"item": new_item, "checked": False, "time": None})
        save_data(data); st.rerun()
    if st.button("Sync List"): 
        data["groceries"] = upd_g
        save_data(data); st.rerun()
