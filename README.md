# planner
A Planner 
# 🌙 Joy & Marcy's Night-Before Sync

A custom Streamlit dashboard for daily coordination, meal planning, and long-term scheduling.

## 🚀 Features
- **Daily Brain Dump:** Separate inputs for Joy and Marcy (Work intensity, Gym plans, Reminders).
- **The Dinner Engine:** A weighted voting system where points for unselected meals carry over as multipliers ($1.0 + 0.1$ per day).
- **Future Planner:** A chronological list of upcoming appointments that automatically injects into the daily rundown.
- **Shared Groceries:** A persistent shopping list with a 24-hour "Option B" archive for checked items.

## 🛠 Setup
1. **Clone the Repo:**
   `git clone [YOUR_REPO_URL]`
2. **Install Requirements:**
   `pip install streamlit pandas`
3. **Run the App:**
   `streamlit run app.py`

## 📦 Data Storage
- All data is stored locally in `sync_data.json`.
- **Note:** This file is included in `.gitignore` to keep personal schedules off public GitHub history.

## 🍕 Dinner Categories
- Mexican, Asian, Pasta, Roast, Caribbean, and custom "Other" entries.
