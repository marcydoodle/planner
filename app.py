import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta

# --- CONFIG & CONSTANTS ---
DATA_FILE = "sync_data.json"
CATEGORIES = ["Mexican", "Asian", "Pasta", "Roast", "Caribbean"]

# --- DATA ENGINE ---
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {
        "multipliers": {cat: 1.0 for cat in CATEGORIES},
        "other_multipliers": {}, # Stores { "Sushi": 1.2 }
        "groceries": [],
        "appointments": [], # List of { "date": str, "owner": str, "desc": str }
        "daily_inputs": {"Joy": {}, "Marcy": {}},
        "last_update": str(datetime.now().date())
    }

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

data = load_data()

# --- APP SETUP ---
st.set_page_config(page_title="Joy & Marcy Sync", layout="wide")
st.title("🌙 The Night-Before Sync")

tabs = st.tabs(["📝 Daily Input", "📋 Tomorrow's Rundown", "🗓 Future Planner", "🛒 Groceries"])

# --- TAB 1: DAILY INPUT ---
with tabs[0]:
    user = st.radio("Who is entering data?", ["Joy", "Marcy"], horizontal=True)
    
    with st.form("daily_form"):
        st.subheader(f"Update for {user}")
        if user == "Joy":
            w_time = st.text_input("Work Schedule (Time)")
            w_mtg = st.text_area("Meetings")
            w_int = st.select_slider("Work Intensity", options=range(1, 11), value=5)
            reminders = st.text_area("Reminders")
            after = st.text_input("After Work Plan")
            intimacy = st.text_input("Intimacy/Energy")
            need = st.text_area("What I need from Marcy")
        else:
            read = st.text_input("Reading Goals")
            gym = st.text_input("Gym Plan")
            cycle = st.text_input("Cycling Plan")
            tasks = st.text_area("Tasks for the Day")
            reminders = st.text_area("Reminders")
            after = st.text_input("After Work Plan")
            intimacy = st.text_input("Intimacy/Energy")
            need = st.text_area("What I need from Joy")
            
        groc_add = st.text_input("Add Groceries (comma separated)")
        
        st.divider()
        st.subheader("🍕 Dinner Voting (10 Points Total)")
        col_pts = st.columns(len(CATEGORIES) + 1)
        votes = {}
        for i, cat in enumerate(CATEGORIES):
            votes[cat] = col_pts[i].number_input(cat, 0, 10, 0)
        
        other_name = col_pts[-1].text_input("Other Name")
        other_pts = col_pts[-1].number_input("Other Points", 0, 10, 0)

        if st.form_submit_button("Submit Nightly Sync"):
            total_pts = sum(votes.values()) + other_pts
            if total_pts > 10:
                st.error(f"Total points is {total_pts}. Please limit to 10!")
            else:
                # Store daily data
                entry = {
                    "reminders": reminders, "after": after, "intimacy": intimacy, "need": need, "votes": votes
                }
                if user == "Joy":
                    entry.update({"work": w_time, "mtg": w_mtg, "intensity": w_int})
                else:
                    entry.update({"read": read, "gym": gym, "cycle": cycle, "tasks": tasks})
                
                data["daily_inputs"][user] = entry
                
                # Handle Groceries
                if groc_add:
                    for item in groc_add.split(","):
                        if item.strip():
                            data["groceries"].append({"item": item.strip(), "checked": False, "time": None})
                
                # Update "Other" Multipliers if name provided
                if other_name and other_name not in data["other_multipliers"]:
                    data["other_multipliers"][other_name] = 1.0
                
                save_data(data)
                st.success("Data Saved!")

# --- TAB 2: RUNDOWN & DINNER ALGO ---
with tabs[1]:
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    st.header(f"Rundown for {tomorrow}")
    
    # DINNER CALCULATION
    st.subheader("🍽 Dinner Decision")
    if st.button("Calculate Dinner Winner"):
        scores = {}
        # Combine votes
        joy_v = data["daily_inputs"].get("Joy", {}).get("votes", {})
        marcy_v = data["daily_inputs"].get("Marcy", {}).get("votes", {})
        
        for cat in CATEGORIES:
            total_v = joy_v.get(cat, 0) + marcy_v.get(cat, 0)
            scores[cat] = total_v * data["multipliers"].get(cat, 1.0)
            
        winner = max(scores, key=scores.get)
        st.info(f"The Winner is: **{winner.upper()}**")
        
        # Multiplier Logic (Linear +0.1)
        for cat in CATEGORIES:
            if cat == winner:
                data["multipliers"][cat] = 1.0
            else:
                data["multipliers"][cat] += 0.1
        save_data(data)

    # AUTO-PULL APPOINTMENTS
    tmw_appts = [a for a in data["appointments"] if a["date"] == tomorrow]
    
    col_j, col_m = st.columns(2)
    with col_j:
        st.markdown("### 🌸 Joy")
        j = data["daily_inputs"].get("Joy", {})
        if j:
            color = "red" if j.get("intensity", 0) > 7 else "green"
            st.markdown(f"**Intensity:** :{color}[{j.get('intensity', 'N/A')}/10]")
            st.write(f"**Work:** {j.get('work')}")
            st.write(f"**Meetings:** {j.get('mtg')}")
            st.write(f"**Needs from Marcy:** {j.get('need')}")
        
        st.write("**Appointments:**")
        for a in tmw_appts:
            if a["owner"] in ["Joy", "Both"]: st.write(f"- {a['desc']}")

    with col_m:
        st.markdown("### ⚡ Marcy")
        m = data["daily_inputs"].get("Marcy", {})
        if m:
            st.write(f"**Gym:** {m.get('gym')}")
            st.write(f"**Cycling:** {m.get('cycle')}")
            st.write(f"**Tasks:** {m.get('tasks')}")
            st.write(f"**Needs from Joy:** {m.get('need')}")

        st.write("**Appointments:**")
        for a in tmw_appts:
            if a["owner"] in ["Marcy", "Both"]: st.write(f"- {a['desc']}")

# --- TAB 3: FUTURE PLANNER ---
with tabs[2]:
    st.header("🗓 Future Appointments")
    with st.expander("Add New Appointment"):
        new_date = st.date_input("Date")
        new_owner = st.selectbox("Who for?", ["Joy", "Marcy", "Both"])
        new_desc = st.text_input("Event Description")
        if st.button("Add to Calendar"):
            data["appointments"].append({"date": str(new_date), "owner": new_owner, "desc": new_desc})
            save_data(data)
            st.rerun()

    if data["appointments"]:
        df_appts = pd.DataFrame(data["appointments"]).sort_values("date")
        st.table(df_appts)
        if st.button("Clear Past Appointments"):
            today_str = str(datetime.now().date())
            data["appointments"] = [a for a in data["appointments"] if a["date"] >= today_str]
            save_data(data)
            st.rerun()

# --- TAB 4: GROCERIES ---
with tabs[3]:
    st.header("🛒 Shared Shopping List")
    now = datetime.now()
    new_groc_list = []
    
    for i, g in enumerate(data["groceries"]):
        # Option B: Remove if checked > 24 hours ago
        if g["checked"] and g["time"]:
            if now - datetime.fromisoformat(g["time"]) > timedelta(hours=24):
                continue
        
        c1, c2 = st.columns([1, 9])
        checked = c1.checkbox("", value=g["checked"], key=f"g_{i}")
        
        if checked and not g["checked"]: # Just checked
            g["checked"] = True
            g["time"] = now.isoformat()
        elif not checked:
            g["checked"] = False
            g["time"] = None
            
        label = f"~~{g['item']}~~" if g["checked"] else g["item"]
        c2.write(label)
        new_groc_list.append(g)

    data["groceries"] = new_groc_list
    if st.button("Save Grocery Changes"):
        save_data(data)
        st.rerun()
