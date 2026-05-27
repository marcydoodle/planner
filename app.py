import streamlit as st
import json
import pandas as pd
from datetime import datetime, timedelta
import pytz

DATA_FILE = "sync_data.json"
CATEGORIES = ["Mexican", "Asian", "Pasta", "Roast", "Caribbean"]

def get_local_now():
    return datetime.now(pytz.timezone("US/Eastern"))

def load_data():
    with open(DATA_FILE, "r") as f:
        try:
            d = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            d = {}
        
        # Ensure base keys exist
        for k in ["history", "groceries", "appointments"]:
            if k not in d: 
                d[k] = {} if k == "history" else []
                
        # Safely ensure weight keys exist to prevent KeyErrors for new users
        if "weights" not in d:
            d["weights"] = {"Joy": {}, "Marcy": {}}
        else:
            if "Joy" not in d["weights"]: d["weights"]["Joy"] = {}
            if "Marcy" not in d["weights"]: d["weights"]["Marcy"] = {}
            
        return d

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
st.divider()

# --- TABS ---
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
                
                with st.container(border=True):
                    st.write("### 🤝 What we need from each other")
                    req = u.get("need")
                    if req:
                        st.chat_message("user").write(f"**{name}'s Request:** {req}")
                    else:
                        st.caption("No specific request listed.")
                    
                    st.write(f"**Reminders:** {u.get('reminders', 'None')}")
                    energy = u.get('energy', 5)
                    color = "green" if energy > 7 else "orange" if energy > 4 else "red"
                    st.markdown(f"**Energy Level:** :{color}[{energy}/10]")

def decide_winner(date_key):
    """Calculates weighted scores and updates data for a specific date."""
    d = st.session_state.data
    w = d["weights"]
    j_v = d["history"].get(date_key, {}).get("Joy", {}).get("votes", {})
    m_v = d["history"].get(date_key, {}).get("Marcy", {}).get("votes", {})

    scores = {c: 0 for c in CATEGORIES}
    
    # Calculate scores based on votes * weights
    for c in CATEGORIES:
        j_score = j_v.get(c, 0) * w.get("Joy", {}).get(c, 1.0)
        m_score = m_v.get(c, 0) * w.get("Marcy", {}).get(c, 1.0)
        scores[c] = j_score + m_score

    if any(scores.values()):
        win = max(scores, key=scores.get)
        
        # Weight Adjustment: Reset winner to 1.0, increment others slightly based on unfulfilled votes
        for p in ["Joy", "Marcy"]:
            for c in CATEGORIES:
                if c == win:
                    d["weights"][p][c] = 1.0
                else:
                    vote_amt = j_v.get(c, 0) if p == "Joy" else m_v.get(c, 0)
                    d["weights"][p][c] += round(vote_amt * 0.1, 2)

        if date_key not in d["history"]: d["history"][date_key] = {}
        d["history"][date_key]["dinner_winner"] = win
        save_data(d)
        st.success(f"Winner: {win.upper()}!")
        st.balloons()
        st.rerun()
    else:
        st.error("No votes found! Go to Nightly Input first.")

# --- TAB LOGIC ---

with tabs[0]: # TODAY
    render_rundown(today_str, "Today")
    day_data = st.session_state.data["history"].get(today_str, {})
    if "Joy" in day_data and "Marcy" in day_data:
        if st.button("🏆 Decide Tonight's Dinner", type="primary"):
            decide_winner(today_str)
    elif day_data:
        st.warning("Waiting for both Joy and Marcy to submit their sync before deciding dinner!")

with tabs[1]: # TOMORROW
    render_rundown(tomorrow_str, "Tomorrow")
    day_data = st.session_state.data["history"].get(tomorrow_str, {})
    if "Joy" in day_data and "Marcy" in day_data:
        if st.button("🏆 Decide Tomorrow's Dinner"):
            decide_winner(tomorrow_str)
    elif day_data:
        st.warning("Waiting for both Joy and Marcy to submit their sync before deciding dinner!")

with tabs[2]: # INPUT
    st.header("Nightly Sync")
    target_date = st.date_input("Planning for:", value=now_dt.date() + timedelta(days=1))
    t_key = target_date.strftime("%Y-%m-%d")
    user = st.radio("Who are you?", ["Joy", "Marcy"], horizontal=True)

    with st.form("input_form", clear_on_submit=True):
        st.subheader("📋 Essentials")
        if user == "Joy":
            w_t = st.text_input("Work Focus", key=f"wt_{user}")
            w_i = st.select_slider("Work Intensity", range(1, 11), 5, key=f"wi_{user}")
            w_m = st.text_area("Key Meetings", key=f"mtg_{user}")
        else:
            gym = st.text_input("Gym Focus", key=f"gym_{user}")
            cyc = st.text_input("Cycling Plan", key=f"cyc_{user}")
            tsk = st.text_area("Main Tasks", key=f"tsk_{user}")
            
        aft = st.text_input("Evening Plan", key=f"aft_{user}")
        rem = st.text_area("Reminders/Don't Forget", key=f"rem_{user}")

        st.subheader("🤝 Support")
        nrg = st.select_slider("Energy Level", range(1, 11), 5, key=f"nrg_{user}")
        nd = st.text_area("What do you need from your partner tomorrow?", key=f"nd_{user}")

        st.subheader("🍕 Dinner Votes (0-10)")
        v_cols = st.columns(len(CATEGORIES))
        v_res = {c: v_cols[i % len(CATEGORIES)].number_input(c, 0, 10, 0, key=f"vote_{c}_{user}") for i, c in enumerate(CATEGORIES)}

        if st.form_submit_button("Submit Sync"):
            d_up = st.session_state.data
            if t_key not in d_up["history"]: d_up["history"][t_key] = {}
            
            entry = {"energy": nrg, "after": aft, "reminders": rem, "need": nd, "votes": v_res}
            if user == "Joy": entry.update({"work": w_t, "mtg": w_m, "intensity": w_i})
            else: entry.update({"gym": gym, "cycle": cyc, "tasks": tsk})
            
            d_up["history"][t_key][user] = entry
            save_data(d_up)
            st.session_state.data = d_up
            st.success(f"Sync Saved for {user}!")
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
        with st.form("appt_form", clear_on_submit=True):
            a_date = st.date_input("Date")
            a_owner = st.selectbox("Who", ["Joy", "Marcy", "Both"])
            a_desc = st.text_input("Description (e.g., Dentist 4pm)")
            if st.form_submit_button("Add to Calendar"):
                if a_desc.strip():
                    st.session_state.data["appointments"].append({
                        "date": a_date.strftime("%Y-%m-%d"),
                        "owner": a_owner,
                        "desc": a_desc
                    })
                    save_data(st.session_state.data)
                    st.rerun()
                else:
                    st.error("Please provide a description.")

    if st.session_state.data["appointments"]:
        st.subheader("Upcoming")
        appts_df = pd.DataFrame(st.session_state.data["appointments"])
        appts_df = appts_df[appts_df['date'] >= today_str].sort_values('date')
        st.table(appts_df)
        if st.button("Clear Old Appointments"):
            st.session_state.data["appointments"] = [a for a in st.session_state.data["appointments"] if a['date'] >= today_str]
            save_data(st.session_state.data)
            st.rerun()

with tabs[5]: # GROCERIES
    st.header("🛒 Shared Grocery List")
    
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
    
    new_groceries = edited_g.to_dict('records')
    if st.session_state.data["groceries"] != new_groceries:
        st.session_state.data["groceries"] = new_groceries
        save_data(st.session_state.data)
        st.rerun()
