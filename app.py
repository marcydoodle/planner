new_groceries = edited_g.to_dict('records')
    changes_detected = False
    
    for i, row in enumerate(new_groceries):
        # 🚨 THE FIX: Force native Python types so the JSON encoder doesn't crash
        row["checked"] = bool(row.get("checked", False))
        row["item"] = str(row.get("item", "")) if pd.notna(row.get("item")) else ""
        row["aisle"] = str(row.get("aisle", "Other")) if pd.notna(row.get("aisle")) else "Other"
        row["time"] = str(row.get("time")) if pd.notna(row.get("time")) else None
        
        # Determine if the checkbox was toggled just now
        old_checked = False
        if i < len(g_df):
            old_checked = bool(g_df.iloc[i].get("checked", False))
            
        if row["checked"] and not old_checked:
            row["time"] = now_time.isoformat()
            changes_detected = True
        elif not row["checked"] and old_checked:
            row["time"] = None
            changes_detected = True
    
    # Save if actual changes occurred
    if len(new_groceries) != len(active_groceries) or changes_detected or not edited_g.equals(g_df):
        d_up = load_data()
        d_up["groceries"] = new_groceries
        save_data(d_up)
        st.session_state.data = d_up
        st.rerun()
