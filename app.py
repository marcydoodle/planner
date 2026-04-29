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
                # Ensure all keys exist
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
        json.dump(d, f, indent=4)

# --- INITIALIZE ---
if 'data' not in st.session_state:
    st.session_state.data = load_data()

now_dt = get_local_now()
today_str = now_dt.strftime("%Y-%m-%d")
tomorrow_str = (now_dt + timedelta(days=1)).strftime("%Y-%m-%d")

st.set_page_config(page_title="Joy & Marcy Sync", layout="wide", page_icon="🌙")
st.title("🌙 The Daily Sync")

# --- DINNER BANNER ---
current_winner = st.session_state.data["history"].get(today_str, {}).get("dinner_winner", "TBD")
st.info(f"### 🍴 Tonight's Dinner: {current_winner.upper()}")

tabs = st.tabs(["📅 Today", "📋 Tomorrow", "📝 Nightly Input", "📊 Standings", "🗓 Future Planner", "🛒 Groceries"])

def render_rundown(date_key, label):
    d = st.session_state.data
    day_data = d["history"].get(date_key, {})
    day_appts = [a for a in d["appointments"] if a.get('date') == date_key]
    
    st.header(f"{label}: {date_key}")
    
    if not day_data and not day_appts:
        st.warning(f"No sync recorded for {date_key}.")
        return

    # Display Appointments for the day first
    if day_appts:
        with st.container(border=True):
            st.subheader("📅 Scheduled Appointments")
            for a in day_appts:
                st.error(f"**{a['owner']}**: {a['desc']}")

    c1, c2 = st.columns(2)
    for name, col in zip(["Joy", "Marcy"], [c1, c2]):
        with col:
            st.subheader(f"{'🌸' if name == 'Joy' else '⚡'} {name}")
            u = day_data.get(name, {})
            if not u:
                st.caption("No input yet.")
                continue
            
            with st.expander("🌅 Daytime", expanded=True):
                col_left, col_right = st.columns(2)
                if name == "Joy":
                    col_left.write(f"**Work:** {u.get('work', '---')}")
                    col_right.write(f"**Intensity:** {u.get('intensity', '5')}/10")
                    st.info(f"**Meetings:** {u.get('mtg', 'None')}")
                else:
                    col_left.write(f"**Gym:** {u.get('gym', 'Rest')}")
                    col_right.write(f"**Cycle:** {u.get('cycle', 'No')}")
                    st.info(f"**Tasks:** {u.get('tasks', 'None')}")
            
            with st.expander("🌆 Evening", expanded=True):
                st.write(f"**Plan:** {u.get('after', 'TBD')}")
                st.write(f"**Reminders:** {u.get('reminders', 'None')}")
                energy = u.get('energy', 5)
                color = "green" if int(energy) > 7 else "orange" if int(energy) > 4 else "red"
                st.markdown(f"**Energy Level:** :{color}[{energy}/10]")

            if u.get("need"):
                st.chat_message("assistant").write(f"**Request for Partner:** {u.get('need')}")

def decide_winner(date_key):
    d = st.session_state.data
    w = d["weights"]
    j_v = d["history"].get(date_key, {}).get("Joy", {}).get("votes", {})
    m_v = d["history"].get(date_key, {}).get("Marcy", {}).get("votes", {})
    
    scores = {}
    for c in CATEGORIES:
        val_j = j_v.get(c, 0) * w["Joy"].get(c, 1.0)
        val_m = m_v.get(c, 0) * w["Marcy"].get(c, 1.0)
        scores[c] = val_j + val_m
    
    if any(scores.values()):
        win = max(scores, key=scores.get)
        # Weight Adjustment: Reset winner to 1.0, increment others slightly based on unfulfilled votes
        for c in CATEGORIES:
            for p in ["Joy", "Marcy"]:
                if c == win:
                    d["weights"][p][c] = 1.0
                else:
                    vote_amt = j_v.get(c, 0) if p == "Joy" else m_v.get(c, 0)
                    d["weights"][p][c] += round(vote_amt * 0.1, 2)

        if date_key not in d["history"]: d["history"][date_key] = {}
        d["history"][date_key]["dinner_winner"] = win
        save_data(d)
        st.balloons()
        st.rerun()
    else:
        st.error("No votes found! Go to Nightly Input first.")

# --- TABS ---

with tabs[0]: # TODAY
    render_rundown(today_str, "Today")
    if st.button("🏆 Decide Tonight's Dinner", type="primary"):
        decide_winner(today_str)

with tabs[1]: # TOMORROW
    render_rundown(tomorrow_str, "Tomorrow")
    if st.button("🏆 Decide Tomorrow's Dinner"):
        decide_winner(tomorrow_str)

with tabs[2]: # INPUT
    st.header("Nightly Sync")
    target_date = st.date_input("Planning for:", value=now_dt.date() + timedelta(days=1))
    t_key = target_date.strftime("%Y-%m-%d")
    user = st.radio("Who are you?", ["Joy", "Marcy"], horizontal=True)
    
    with st.form("input_form", clear_on_submit=True):
        st.subheader("📋 Essentials")
        if user == "Joy":
            w_t = st.text_input("Work Focus")
            w_i = st.select_slider("Work Intensity", range(1, 11), 5)
            w_m = st.text_area("Key Meetings")
        else:
            gym = st.text_input("Gym Focus")
            cyc = st.text_input("Cycling Plan")
            tsk = st.text_area("Main Tasks")
            
        aft = st.text_input("Evening Plan")
        rem = st.text_area("Reminders/Don't Forget")
        
        st.subheader("🤝 Support")
        nrg = st.select_slider("Energy Level", range(1, 11), 5)
        nd = st.text_area("What do you need from your partner tomorrow?")
        
        st.subheader("🍕 Dinner Votes (0-10)")
        v_cols = st.columns(4)
        v_res = {c: v_cols[i % 4].number_input(c, 0, 10, 0, key=f"vote_{c}") for i, c in enumerate(CATEGORIES)}
        
        if st.form_submit_button("Submit Sync"):
            d_up = load_data()
            if t_key not in d_up["history"]: d_up["history"][t_key] = {}
            
            entry = {"energy": nrg, "after": aft, "reminders": rem, "need": nd, "votes": v_res}
            if user == "Joy": entry.update({"work": w_t, "mtg": w_m, "intensity": w_i})
            else: entry.update({"gym": gym, "cycle": cyc, "tasks": tsk})
            
            d_up["history"][t_key][user] = entry
            save_data(d_up)
            st.session_state.data = d_up
            st.success("Sync Saved!")
            st.rerun()

with tabs[3]: # STANDINGS
    st.header("📊 Multiplier Status")
    st.write("The more you vote for something and *don't* get it, the higher your multiplier grows.")
    display_data = []
    for c in CATEGORIES:
        display_data.append({
            "Category": c, 
            "Joy Multiplier": f"{st.session_state.data['weights']['Joy'].get(c, 1.0):.2f}x",
            "Marcy Multiplier": f"{st.session_state.data['weights']['Marcy'].get(c, 1.0):.2f}x"
        })
    st.table(pd.DataFrame(display_data))

with tabs[4]: # FUTURE PLANNER
    st.header("🗓 Appointment Planner")
    with st.expander("➕ Add New Appointment"):
        with st.form("appt_form"):
            a_date = st.date_input("Date")
            a_owner = st.selectbox("Who", ["Joy", "Marcy", "Both"])
            a_desc = st.text_input("Description (e.g., Dentist 4pm)")
            if st.form_submit_button("Add to Calendar"):
                st.session_state.data["appointments"].append({
                    "date": a_date.strftime("%Y-%m-%d"),
                    "owner": a_owner,
                    "desc": a_desc
                })
                save_data(st.session_state.data)
                st.rerun()

    if st.session_state.data["appointments"]:
        st.subheader("Upcoming")
        appts_df = pd.DataFrame(st.session_state.data["appointments"])
        # Filter for future or today
        appts_df = appts_df[appts_df['date'] >= today_str].sort_values('date')
        st.table(appts_df)
        if st.button("Clear Old Appointments"):
            st.session_state.data["appointments"] = [a for a in st.session_state.data["appointments"] if a['date'] >= today_str]
            save_data(st.session_state.data)
            st.rerun()

with tabs[5]: # GROCERIES
    st.header("🛒 Shared Grocery List")
    
    # Use Data Editor for a better experience
    g_df = pd.DataFrame(st.session_state.data["groceries"])
    if g_df.empty:
        g_df = pd.DataFrame(columns=["item", "checked"])
    
    edited_g = st.data_editor(
        g_df, 
        column_config={
            "checked": st.column_config.CheckboxColumn("Done?", default=False),
            "item": st.column_config.TextColumn("Item Name")
        },
        num_rows="dynamic",
        use_container_width=True,
        key="grocery_editor"
    )
    
    if st.button("Save List Changes"):
        st.session_state.data["groceries"] = edited_g.to_dict('records')
        save_data(st.session_state.data)
        st.success("Groceries updated!")
        st.rerun()
