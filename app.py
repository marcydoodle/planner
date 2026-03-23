import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta

# --- CONFIG & CONSTANTS ---
DATA_FILE = "sync_data.json"
CATEGORIES = ["Mexican", "Asian", "Pasta", "Roast", "Caribbean"]

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {
        "multipliers": {cat: 1.0 for cat in CATEGORIES},
        "other_multipliers": {}, 
        "groceries": [],
        "appointments": [],
        "daily_inputs": {"Joy": {}, "Marcy": {}}
    }

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

data = load_data()

st.set_page_config(page_title="Joy & Marcy Sync", layout="wide")
st.title("🌙 The Night-Before Sync")

tabs = st.tabs(["📝 Daily Input", "📋 Tomorrow's Rundown", "🗓 Future Planner", "🛒 Groceries"])

# --- TAB 1: DAILY INPUT ---
with tabs[0]:
    user = st.radio("Who is entering data?", ["Joy", "Marcy"], horizontal=True)
    
    with st.form("daily_form"):
        st.subheader(f"Update for {user}")
        
        # Shared fields but with specific logic
        energy = st.select_slider("⚡ Personal Energy Level", options=range(0, 11), value=5, help="0 = Exhausted, 10 = Ready for anything")
        after = st.text_input("After Work Plan")
        reminders = st.text_area("Reminders")
        
        if user == "Joy":
            w_time = st.text_input("Work Schedule (Time)")
            w_mtg = st.text_area("Meetings")
            w_int = st.select_slider("Work Intensity", options=range(1, 11), value=5)
            need = st.text_area("What I need from Marcy")
        else: # Marcy
            gym = st.text_input("Gym Plan")
            cycle = st.text_input("Cycling Plan")
            tasks = st.text_area("Tasks for the Day")
            need = st.text_area("What I need from Joy")
            
        groc_add = st.text_input("Add Groceries (comma separated)")
        
        st.divider()
        st.subheader("🍕 Dinner Voting (10 Points Total)")
        col_pts = st.columns(len(CATEGORIES) + 1)
        votes = {}
        for i, cat in enumerate(CATEGORIES):
            votes[cat] = col_pts[i].number_input(cat, 0, 10, 0)
        
        other_name = col_pts[-1].text_input("Other Name (e.g. Sushi)")
        other_pts = col_pts[-1].number_input("Other Points", 0, 10, 0)

        if st.form_submit_button("Submit Nightly Sync"):
            total_pts = sum(votes.values()) + other_pts
            if total_pts > 10:
                st.error(f"Total points is {total_pts}. Please limit to 10!")
            else:
                entry = {
                    "energy": energy, "after": after, "reminders": reminders, 
                    "need": need, "votes": votes, "other_name": other_name, "other_pts": other_pts
                }
                if user == "Joy":
                    entry.update({"work": w_time, "mtg": w_mtg, "intensity": w_int})
                else:
                    entry.update({"gym": gym, "cycle": cycle, "tasks": tasks})
                
                data["daily_inputs"][user] = entry
                
                if groc_add:
                    for item in groc_add.split(","):
                        if item.strip():
                            data["groceries"].append({"item": item.strip(), "checked": False, "time": None})
                
                if other_name and other_name not in data["other_multipliers"]:
                    data["other_multipliers"][other_name] = 1.0
                
                save_data(data)
                st.success("Entry saved!")

# --- TAB 2: RUNDOWN ---
with tabs[1]:
    tmw = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    st.header(f"Rundown for {tmw}")
    
    # DINNER ENGINE
    if st.button("Calculate Dinner Winner"):
        scores = {}
        j_in = data["daily_inputs"].get("Joy", {})
        m_in = data["daily_inputs"].get("Marcy", {})
        
        for cat in CATEGORIES:
            v = j_in.get("votes", {}).get(cat, 0) + m_in.get("votes", {}).get(cat, 0)
            scores[cat] = v * data["multipliers"].get(cat, 1.0)
        
        # Handle "Other" votes from both
        for person_data in [j_in, m_in]:
            oth_n = person_data.get("other_name")
            if oth_n:
                o_pts = person_data.get("other_pts", 0)
                scores[f"Other: {oth_n}"] = o_pts * data["other_multipliers"].get(oth_n, 1.0)

        if scores:
            winner = max(scores, key=scores.get)
            st.balloons()
            st.info(f"The Winner is: **{winner.upper()}**")
            
            # Reset/Increment Multipliers
            for cat in CATEGORIES:
                data["multipliers"][cat] = 1.0 if cat == winner else data["multipliers"][cat] + 0.1
            for oth in list(data["other_multipliers"].keys()):
                data["other_multipliers"][oth] = 1.0 if f"Other: {oth}" == winner else data["other_multipliers"][oth] + 0.1
            save_data(data)

    tmw_appts = [a for a in data["appointments"] if a["date"] == tmw]
    col_j, col_m = st.columns(2)
    
    for user_name, col in zip(["Joy", "Marcy"], [col_j, col_m]):
        with col:
            st.markdown(f"### {'🌸' if user_name == 'Joy' else '⚡'} {user_name}")
            u_data = data["daily_inputs"].get(user_name, {})
            if u_data:
                e_val = u_data.get("energy", 5)
                st.metric("Energy Level", f"{e_val}/10")
                if user_name == "Joy":
                    st.write(f"**Intensity:** {u_data.get('intensity')}/10")
                    st.write(f"**Work:** {u_data.get('work')}")
                else:
                    st.write(f"**Gym:** {u_data.get('gym')}")
                    st.write(f"**Cycling:** {u_data.get('cycle')}")
                st.write(f"**After Work:** {u_data.get('after')}")
                st.warning(f"**Need:** {u_data.get('need')}")
            
            st.write("**Appointments:**")
            for a in [app for app in tmw_appts if app["owner"] in [user_name, "Both"]]:
                st.write(f"- {a['desc']}")

# --- TAB 3: FUTURE PLANNER ---
with tabs[2]:
    st.header("🗓 Future Appointments")
    with st.expander("Add New"):
        d = st.date_input("Date")
        o = st.selectbox("Who?", ["Joy", "Marcy", "Both"])
        desc = st.text_input("Description")
        if st.button("Save Appointment"):
            data["appointments"].append({"date": str(d), "owner": o, "desc": desc})
            save_data(data)
            st.rerun()
    st.table(pd.DataFrame(data["appointments"]).sort_values("date") if data["appointments"] else [])

# --- TAB 4: GROCERIES ---
with tabs[3]:
    st.header("🛒 Shared Shopping List")
    now = datetime.now()
    updated_g = []
    for i, g in enumerate(data["groceries"]):
        if g["checked"] and g["time"] and (now - datetime.fromisoformat(g["time"]) > timedelta(hours=24)):
            continue
        c1, c2 = st.columns([1, 9])
        is_checked = c1.checkbox("", value=g["checked"], key=f"g_{i}")
        if is_checked and not g["checked"]:
            g["checked"], g["time"] = True, now.isoformat()
        elif not is_checked:
            g["checked"], g["time"] = False, None
        c2.write(f"~~{g['item']}~~" if is_checked else g['item'])
        updated_g.append(g)
    data["groceries"] = updated_g
    if st.button("Sync List"):
        save_data(data); st.rerun()
