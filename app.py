import streamlit as st
import json
import pandas as pd
from datetime import datetime, timedelta
import pytz
import requests

# --- CONFIG ---
CATEGORIES = ["Mexican", "Asian", "Pasta", "Roast", "Caribbean","Scrounge"]
AISLES = ["Produce", "Dairy & Fridge", "Vegan Meat", "Pantry", "Frozen", "Household", "Other"]

# Pull keys securely from Streamlit Cloud Secrets
try:
    BIN_ID = st.secrets["BIN_ID"]
    API_KEY = st.secrets["API_KEY"]
except KeyError:
    st.error("Missing Streamlit secrets. Please make sure BIN_ID and API_KEY are in your app settings.")
    st.stop()

BIN_URL = f"https://api.jsonbin.io/v3/b/{BIN_ID}"
WEBHOOK_URL = st.secrets.get("WEBHOOK_URL", None) # Optional webhook

def get_local_now():
    return datetime.now(pytz.timezone("US/Eastern"))

def send_notification(user_name):
    """Fires a webhook notification to Discord/Slack if configured."""
    if WEBHOOK_URL:
        msg = f"🌙 **{user_name}** just submitted their nightly sync! Waiting on you."
        try:
            requests.post(WEBHOOK_URL, json={"content": msg}, timeout=2)
        except Exception:
            pass # Fail silently so it doesn't break the app

def load_data():
    headers = {"X-Master-Key": API_KEY}
    try:
        response = requests.get(BIN_URL, headers=headers)
        if response.status_code == 200:
            d = response.json().get('record', {})
        else:
            d = {}
    except Exception:
        d = {}
    
    # Ensure base keys exist
    for k in ["history", "groceries", "appointments"]:
        if k not in d: d[k] = {} if k == "history" else []
            
    if "weights" not in d:
        d["weights"] = {"Joy": {}, "Marcy": {}}
    else:
        if "Joy" not in d["weights"]: d["weights"]["Joy"] = {}
        if "Marcy" not in d["weights"]: d["weights"]["Marcy"] = {}
        
    # Ensure custom write-in categories exist
    if "custom_categories" not in d:
        d["custom_categories"] = []
        
    return d

def save_data(d):
    headers = {
        "Content-Type": "application/json",
        "X-Master-Key": API_KEY
    }
    requests.put(BIN_URL, json=d, headers=headers)

def calculate_streak(history_data):
    """Calculates consecutive days synced without unfairly resetting to 0 during the day."""
    streak = 0
    today = get_local_now().date()
    
    today_str = today.strftime("%Y-%m-%d")
    if "Joy" in history_data.get(today_str, {}) and "Marcy" in history_data.get(today_str, {}):
        streak += 1
        check_date = today - timedelta(days=1)
    else:
        check_date = today - timedelta(days=1)
        
    while True:
        date_str = check_date.strftime("%Y-%m-%d")
        day_data = history_data.get(date_str, {})
        if "Joy" in day_data and "Marcy" in day_data:
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break
            
    return streak

# --- INITIALIZE ---
if 'data' not in st.session_state:
    st.session_state.data = load_data()

now_dt = get_local_now()
today_str = now_dt.strftime("%Y-%m-%d")
tomorrow_str = (now_dt + timedelta(days=1)).strftime("%Y-%m-%d")

st.set_page_config(page_title="Joy & Marcy Sync", layout="wide", page_icon="🌙")
st.title("🌙 The Daily Sync")

# --- DINNER & STREAK BANNER ---
current_winner = st.session_state.data["history"].get(today_str, {}).get("dinner_winner", "TBD")
streak = calculate_streak(st.session_state.data["history"])

banner_col1, banner_col2 = st.columns([3, 1])

with banner_col1:
    st.info(f"### 🍴 Tonight's Dinner: {current_winner.upper()}")

with banner_col2:
    with st.container(border=True):
        st.metric(label="🔥 Sync Streak", value=f"{streak} Days")

st.divider()

# --- TABS ---
tabs = st.tabs(["📅 Today", "📋 Tomorrow", "📝 Nightly Input", "📊 Standings & Insights", "🗓 Future Planner", "🛒 Groceries", "📜 History"])

def render_rundown(date_key, label):
    d = st.session_state.data
    day_data = d["history"].get(date_key, {})
    day_appts = [a for a in d["appointments"] if a.get('date') == date_key]
    
    st.header(f"{label}: {date_key}")

    if not day_data and not day_appts:
        st.warning(f"No sync recorded for {date_key}.")
        return

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
    d = load_data() 
    w = d["weights"]
    j_v = d["history"].get(date_key, {}).get("Joy", {}).get("votes", {})
    m_v = d["history"].get(date_key, {}).get("Marcy", {}).get("votes", {})

    # Active categories include base + any active custom write-ins
    active_categories = CATEGORIES + d.get("custom_categories", [])
    scores = {c: 0 for c in active_categories}
    
    for c in active_categories:
        j_score = j_v.get(c, 0) * w.get("Joy", {}).get(c, 1.0)
        m_score = m_v.get(c, 0) * w.get("Marcy", {}).get(c, 1.0)
        scores[c] = j_score + m_score

    if any(scores.values()):
        win = max(scores, key=scores.get)
        
        for p in ["Joy", "Marcy"]:
            for c in active_categories:
                if c not in d["weights"][p]:
                    d["weights"][p][c] = 1.0
                    
                if c == win:
                    d["weights"][p][c] = 1.0
                else:
                    vote_amt = j_v.get(c, 0) if p == "Joy" else m_v.get(c, 0)
                    d["weights"][p][c] += round(vote_amt * 0.1, 2)

        # Cleanup: If a custom write-in won, remove it from the active rotation
        if win in d.get("custom_categories", []):
            d["custom_categories"].remove(win)
            # Remove its weight memory so it doesn't bloat the JSON
            for p in ["Joy", "Marcy"]:
                d["weights"][p].pop(win, None)

        if date_key not in d["history"]: d["history"][date_key] = {}
        d["history"][date_key]["dinner_winner"] = win
        save_data(d)
        st.session_state.data = d 
        st.toast(f"Winner: {win.upper()}!", icon="🎉")
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

        st.subheader("🍕 Dinner Votes (Max 10 Points Total)")
        active_cats = CATEGORIES + st.session_state.data.get("custom_categories", [])
        
        # Display existing and active custom options across 4 columns
        v_cols = st.columns(4)
        v_res = {}
        for i, c in enumerate(active_cats):
            v_res[c] = v_cols[i % 4].number_input(c, 0, 10, 0, key=f"vote_{c}_{user}")
            
        st.write("---")
        st.markdown("**Craving something else? Write in a new option:**")
        w_col1, w_col2 = st.columns([3, 1])
        new_cat_name = w_col1.text_input("New Suggestion", key=f"new_cat_{user}").strip().title()
        new_cat_vote = w_col2.number_input("Votes for New Suggestion", 0, 10, 0, key=f"new_vote_{user}")

        if st.form_submit_button("Submit Sync"):
            total_votes = sum(v_res.values()) + new_cat_vote
            
            if total_votes > 10:
                st.error(f"⚠️ You used {total_votes} points. Please adjust your votes to a maximum of 10 points and try again!")
            else:
                with st.spinner("Syncing to cloud..."):
                    d_up = load_data()
                    if t_key not in d_up["history"]: d_up["history"][t_key] = {}
                    
                    # Handle new write-in category
                    if new_cat_name and new_cat_vote > 0:
                        if new_cat_name not in active_cats:
                            d_up["custom_categories"].append(new_cat_name)
                            d_up["weights"]["Joy"][new_cat_name] = 1.0
                            d_up["weights"]["Marcy"][new_cat_name] = 1.0
                        # Inject the write-in vote into the results so it counts
                        v_res[new_cat_name] = v_res.get(new_cat_name, 0) + new_cat_vote
                    
                    entry = {"energy": nrg, "after": aft, "reminders": rem, "need": nd, "votes": v_res}
                    if user == "Joy": entry.update({"work": w_t, "mtg": w_m, "intensity": w_i})
                    else: entry.update({"gym": gym, "cycle": cyc, "tasks": tsk})
                    
                    d_up["history"][t_key][user] = entry
                    save_data(d_up)
                    st.session_state.data = d_up 
                
                send_notification(user)
                st.toast(f"Sync Saved securely for {user}! 🌙", icon="✅")
                st.rerun()

with tabs[3]: # STANDINGS & INSIGHTS
    st.header("📊 Standings & Insights")
    st.write("The more you vote for something and *don't* get it, the higher your multiplier grows.")
    st.divider()

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Multiplier Status")
        display_data = []
        active_cats = CATEGORIES + st.session_state.data.get("custom_categories", [])
        for c in active_cats:
            display_data.append({
                "Category": c, 
                "Joy Multiplier": f"{st.session_state.data['weights']['Joy'].get(c, 1.0):.2f}x",
                "Marcy Multiplier": f"{st.session_state.data['weights']['Marcy'].get(c, 1.0):.2f}x"
            })
        st.dataframe(pd.DataFrame(display_data), hide_index=True)

    with col2:
        st.subheader("Energy & Intensity (Last 14 Days)")
        chart_data = []
        hist = st.session_state.data["history"]
        
        recent_dates = sorted([d for d in hist.keys() if d <= today_str])[-14:]
        
        for d in recent_dates:
            chart_data.append({
                "Date": d,
                "Joy's Work Intensity": hist[d].get("Joy", {}).get("intensity", 5),
                "Marcy's Energy": hist[d].get("Marcy", {}).get("energy", 5)
            })
            
        if chart_data:
            df_chart = pd.DataFrame(chart_data).set_index("Date")
            st.line_chart(df_chart, color=["#FF4B4B", "#0068C9"])
        else:
            st.info("Not enough data to graph yet!")

with tabs[4]: # FUTURE PLANNER
    st.header("🗓 Appointment Planner")
    with st.expander("➕ Add New Appointment"):
        with st.form("appt_form", clear_on_submit=True):
            a_date = st.date_input("Date")
            a_owner = st.selectbox("Who", ["Joy", "Marcy", "Both"])
            a_desc = st.text_input("Description (e.g., Dentist 4pm)")
            if st.form_submit_button("Add to Calendar"):
                if a_desc.strip():
                    d_up = load_data() 
                    d_up["appointments"].append({
                        "date": a_date.strftime("%Y-%m-%d"),
                        "owner": a_owner,
                        "desc": a_desc
                    })
                    save_data(d_up)
                    st.session_state.data = d_up
                    st.toast("Appointment added!", icon="📅")
                    st.rerun()
                else:
                    st.error("Please provide a description.")

    if st.session_state.data["appointments"]:
        st.subheader("Upcoming")
        appts_df = pd.DataFrame(st.session_state.data["appointments"])
        appts_df = appts_df[appts_df['date'] >= today_str].sort_values('date')
        st.dataframe(appts_df, hide_index=True, use_container_width=True)
        if st.button("Clear Old Appointments"):
            d_up = load_data()
            d_up["appointments"] = [a for a in d_up["appointments"] if a['date'] >= today_str]
            save_data(d_up)
            st.session_state.data = d_up
            st.rerun()

with tabs[5]: # GROCERIES
    st.header("🛒 Shared Grocery List")
    now_time = get_local_now()
    
    active_groceries = []
    needs_cleanup_save = False
    
    for g in st.session_state.data["groceries"]:
        if g.get("checked") and g.get("time"):
            try:
                checked_time = datetime.fromisoformat(g["time"])
                if now_time - checked_time > timedelta(hours=24):
                    needs_cleanup_save = True
                    continue
            except ValueError:
                pass
        
        if "aisle" not in g:
            g["aisle"] = "Other"
            
        active_groceries.append(g)
        
    if needs_cleanup_save:
        st.session_state.data["groceries"] = active_groceries
        d_up = load_data()
        d_up["groceries"] = active_groceries
        save_data(d_up)
        
    g_df = pd.DataFrame(active_groceries)
    if g_df.empty:
        g_df = pd.DataFrame(columns=["checked", "item", "aisle", "time"])

    g_df['aisle'] = pd.Categorical(g_df['aisle'], categories=AISLES, ordered=True)
    g_df = g_df.sort_values(['checked', 'aisle', 'item']).reset_index(drop=True)

    edited_g = st.data_editor(
        g_df, 
        column_config={
            "checked": st.column_config.CheckboxColumn("Done?", default=False, width="small"),
            "item": st.column_config.TextColumn("Item Name", required=True),
            "aisle": st.column_config.SelectboxColumn("Aisle", options=AISLES, default="Other", required=True),
            "time": None 
        },
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="grocery_editor"
    )
    
    new_groceries = edited_g.to_dict('records')
    changes_detected = False
    
    for i, row in enumerate(new_groceries):
        old_checked = False
        if i < len(g_df):
            old_checked = g_df.iloc[i].get("checked", False)
            
        if row.get("checked") and not old_checked:
            row["time"] = now_time.isoformat()
            changes_detected = True
        elif not row.get("checked") and old_checked:
            row["time"] = None
            changes_detected = True
            
        if pd.isna(row.get("aisle")):
            row["aisle"] = "Other"
            changes_detected = True
    
    if len(new_groceries) != len(active_groceries) or changes_detected or not edited_g.equals(g_df):
        d_up = load_data()
        d_up["groceries"] = new_groceries
        save_data(d_up)
        st.session_state.data = d_up
        st.rerun()

with tabs[6]: # HISTORY
    st.header("📜 Time Machine")
    st.write("Select a past date to view its daily rundown.")
    
    history_date = st.date_input(
        "Historical Date:", 
        value=now_dt.date() - timedelta(days=1), 
        max_value=now_dt.date()
    )
    h_key = history_date.strftime("%Y-%m-%d")
    
    st.divider()
    render_rundown(h_key, "Historical Rundown")
