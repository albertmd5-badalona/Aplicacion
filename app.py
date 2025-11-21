# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from streamlit_option_menu import option_menu
import json
import io

# --- PAGE CONFIG & CSS ---
st.set_page_config(page_title="Project & Resource Master", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS for "Compact Mode" and Visuals
st.markdown("""
<style>
    /* Compact layout */
    .block-container {padding-top: 1rem; padding-bottom: 1rem; padding-left: 2rem; padding-right: 2rem;}
    h1 {font-size: 1.8rem !important; margin-bottom: 0px;}
    h2, h3 {font-size: 1.2rem !important; margin-top: 10px;}
    .stButton button {padding: 0px 10px; font-size: 0.8rem;}
    .stDataFrame {font-size: 0.8rem;}
    
    /* Interactive visual tweaks */
    div[data-testid="stMetricValue"] {font-size: 1.2rem !important;}
</style>
""", unsafe_allow_html=True)

# --- DATABASE MANAGER ---
def init_db():
    conn = sqlite3.connect('app_db_v2.db')
    c = conn.cursor()
    
    # 1. Employees
    c.execute('''CREATE TABLE IF NOT EXISTS employees (
        id_emp TEXT PRIMARY KEY, first_name TEXT, last_name TEXT, email TEXT, 
        type TEXT, rate REAL, manager TEXT, res_manager TEXT, department TEXT)''')
    
    # 2. Projects
    c.execute('''CREATE TABLE IF NOT EXISTS projects (
        id_proj TEXT PRIMARY KEY, name TEXT, platform TEXT, product TEXT,
        capex_opex TEXT, budget REAL)''')
        
    # 2.2 Gantt Tasks
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT, id_proj TEXT, task_name TEXT,
        assigned_to TEXT, start_date TEXT, end_date TEXT, progress INTEGER)''')

    # 3. Calendar (Availability)
    c.execute('''CREATE TABLE IF NOT EXISTS calendar (
        id INTEGER PRIMARY KEY AUTOINCREMENT, id_emp TEXT, date TEXT, type TEXT,
        UNIQUE(id_emp, date))''')

    # 4. Assignments
    c.execute('''CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT, id_proj TEXT, id_emp TEXT,
        week_start TEXT, percent INTEGER,
        UNIQUE(id_proj, id_emp, week_start))''')

    # 6. Timesheets
    c.execute('''CREATE TABLE IF NOT EXISTS timesheets (
        id INTEGER PRIMARY KEY AUTOINCREMENT, id_emp TEXT, month TEXT, hours REAL, id_proj TEXT)''')

    # 8. Admin Lists
    c.execute('''CREATE TABLE IF NOT EXISTS config_lists (
        category TEXT, value TEXT, UNIQUE(category, value))''')

    conn.commit()
    return conn

conn = init_db()

# --- HELPERS ---
def run_query(query, params=()):
    return pd.read_sql(query, conn, params=params)

def run_action(query, params=()):
    c = conn.cursor()
    try:
        c.execute(query, params)
        conn.commit()
        return True
    except Exception as e:
        st.error(f"DB Error: {e}")
        return False

def get_list_values(category):
    df = run_query("SELECT value FROM config_lists WHERE category = ?", (category,))
    if df.empty and category == "department":
        return ["IT", "HR", "Finance", "Operations"] # Default
    return df['value'].tolist()

# --- NAVIGATION (TOP HORIZONTAL) ---
selected = option_menu(
    menu_title=None,
    options=["Employees", "Projects", "Calendar", "Assignments", "Finance", "Timesheets", "Dashboards", "Admin"],
    icons=["people", "briefcase", "calendar3", "table", "cash-stack", "clock", "graph-up", "gear"],
    menu_icon="cast",
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": "#f0f2f6"},
        "icon": {"color": "orange", "font-size": "14px"}, 
        "nav-link": {"font-size": "14px", "text-align": "center", "margin":"0px", "--hover-color": "#e1e1e1"},
        "nav-link-selected": {"background-color": "#0099ff"},
    }
)

# --- 1. EMPLOYEES ---
if selected == "Employees":
    st.subheader("?? Master Data: Employees")
    
    with st.expander("? Add / Edit Employee", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        eid = c1.text_input("Employee ID")
        fname = c2.text_input("First Name")
        lname = c3.text_input("Last Name")
        email = c4.text_input("Email")
        
        c5, c6, c7, c8 = st.columns(4)
        etype = c5.selectbox("Type", ["Internal", "External"])
        dept = c6.selectbox("Department", get_list_values("department"))
        rate = c7.number_input("Hourly Rate", min_value=0.0)
        mgr = c8.text_input("Manager")
        
        if st.button("Save Employee"):
            run_action("INSERT OR REPLACE INTO employees VALUES (?,?,?,?,?,?,?,?,?)", 
                       (eid, fname, lname, email, etype, rate, mgr, "ResMgr", dept))
            st.success("Saved!")
            st.rerun()

    df_emp = run_query("SELECT * FROM employees")
    st.dataframe(df_emp, use_container_width=True, hide_index=True)

# --- 2. PROJECTS ---
elif selected == "Projects":
    st.subheader("?? Master Data: Projects & Gantt")
    
    t1, t2 = st.tabs(["Project List", "Gantt Chart"])
    
    with t1:
        with st.expander("? New Project"):
            c1, c2, c3 = st.columns(3)
            pid = c1.text_input("Project ID")
            pname = c2.text_input("Name")
            pbud = c3.number_input("Total Budget", min_value=0.0)
            
            c4, c5, c6 = st.columns(3)
            # Multi-select for CAPEX/OPEX
            pcap = c4.multiselect("Type", ["CAPEX", "OPEX"], default=["OPEX"])
            pplat = c5.text_input("Platform")
            pprod = c6.text_input("Product")
            
            if st.button("Create Project"):
                pcap_str = ",".join(pcap)
                run_action("INSERT OR REPLACE INTO projects VALUES (?,?,?,?,?,?)", 
                           (pid, pname, pplat, pprod, pcap_str, pbud))
                st.success("Created!")
                st.rerun()
        
        st.dataframe(run_query("SELECT * FROM projects"), use_container_width=True)
        
    with t2:
        projs = run_query("SELECT id_proj FROM projects")['id_proj'].tolist()
        if projs:
            sel_p = st.selectbox("Select Project", projs)
            
            # Add Task Inline
            with st.form("gantt"):
                c1, c2, c3, c4, c5 = st.columns([2,2,1,1,1])
                tn = c1.text_input("Task Name")
                ta = c2.selectbox("Assignee", run_query("SELECT id_emp FROM employees")['id_emp'].tolist())
                d1 = c3.date_input("Start")
                d2 = c4.date_input("End")
                pr = c5.slider("%", 0, 100, 0)
                if st.form_submit_button("Add Task"):
                    run_action("INSERT INTO tasks (id_proj, task_name, assigned_to, start_date, end_date, progress) VALUES (?,?,?,?,?,?)",
                               (sel_p, tn, ta, str(d1), str(d2), pr))
                    st.rerun()
            
            # Render Gantt
            df_t = run_query("SELECT * FROM tasks WHERE id_proj = ?", (sel_p,))
            if not df_t.empty:
                fig = px.timeline(df_t, x_start="start_date", x_end="end_date", y="task_name", color="progress", range_x=[df_t['start_date'].min(), df_t['end_date'].max()])
                fig.update_yaxes(autorange="reversed")
                fig.update_layout(height=300, margin=dict(l=0, r=0, t=0, b=0))
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No projects defined.")

# --- 3. CALENDAR ---
elif selected == "Calendar":
    st.subheader("?? Resource Availability")
    
    # Layout: Controls on top
    c1, c2, c3 = st.columns([1, 1, 2])
    emps = run_query("SELECT id_emp FROM employees")['id_emp'].tolist()
    sel_emp = c1.selectbox("Select Resource", emps) if emps else None
    
    # Modify Availability
    with c2.popover("??? Change Status"):
        d_sel = st.date_input("Date(s)", value=[])
        status = st.selectbox("Set Status", ["Vacation", "Holiday", "Sick", "Working"])
        if st.button("Apply Change"):
            if isinstance(d_sel, tuple) and len(d_sel) == 2:
                start, end = d_sel
                curr = start
                while curr <= end:
                    if status == "Working":
                        run_action("DELETE FROM calendar WHERE id_emp=? AND date=?", (sel_emp, str(curr)))
                    else:
                        run_action("INSERT OR REPLACE INTO calendar (id_emp, date, type) VALUES (?,?,?)", (sel_emp, str(curr), status))
                    curr += timedelta(days=1)
            elif d_sel: # Single day
                if status == "Working":
                     run_action("DELETE FROM calendar WHERE id_emp=? AND date=?", (sel_emp, str(d_sel)))
                else:
                    run_action("INSERT OR REPLACE INTO calendar (id_emp, date, type) VALUES (?,?,?)", (sel_emp, str(d_sel), status))
            st.rerun()

    # Visual Heatmap
    if sel_emp:
        # Generate date range: Jan 1st current year -> Dec 31st next year
        now = datetime.now()
        start_y = datetime(now.year, 1, 1)
        end_y = datetime(now.year + 1, 12, 31)
        
        dates = []
        curr = start_y
        while curr <= end_y:
            dates.append(curr)
            curr += timedelta(days=1)
            
        df_cal_base = pd.DataFrame({'date': dates})
        df_cal_base['date_str'] = df_cal_base['date'].dt.strftime('%Y-%m-%d')
        df_cal_base['weekday'] = df_cal_base['date'].dt.weekday # 0=Mon, 6=Sun
        
        # Fetch exceptions
        df_ex = run_query("SELECT date, type FROM calendar WHERE id_emp = ?", (sel_emp,))
        
        # Merge
        df_final = df_cal_base.merge(df_ex, left_on='date_str', right_on='date', how='left')
        
        # Logic: Default Mon-Fri = 1 (Working-Green), Sat-Sun = 0 (Weekend-Grey), Exception = 2 (Red)
        def get_val(row):
            if pd.notna(row['type']): return 0.2 if row['type'] == 'Holiday' else 0.1 # Vacation/Holiday
            if row['weekday'] >= 5: return 0.5 # Weekend
            return 1.0 # Working
            
        df_final['score'] = df_final.apply(get_val, axis=1)
        
        # Plotly Heatmap
        fig = go.Figure(data=go.Heatmap(
            z=df_final['score'],
            x=df_final['date'],
            y=[sel_emp] * len(df_final),
            colorscale=[[0, 'red'], [0.5, 'lightgrey'], [1, 'green']],
            showscale=False,
            xgap=1, ygap=1
        ))
        fig.update_layout(height=150, margin=dict(l=0, r=0, t=0, b=0), title_text=f"Availability: {sel_emp}")
        st.plotly_chart(fig, use_container_width=True)
        
        st.caption("Green: Available | Grey: Weekend | Red: Vacation/Holiday")

# --- 4. ASSIGNMENTS (MATRIX) ---
elif selected == "Assignments":
    st.subheader("?? Weekly Assignment Matrix (%)")
    
    # 1. Prepare Columns (Next 12 weeks for example)
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())
    weeks = [(start_of_week + timedelta(weeks=i)).strftime('%Y-%m-%d') for i in range(12)]
    
    # 2. Fetch Data
    df_assign = run_query("SELECT * FROM assignments")
    df_projs = run_query("SELECT id_proj FROM projects")
    df_emps = run_query("SELECT id_emp FROM employees")
    
    if not df_projs.empty and not df_emps.empty:
        # Create Cartesian Product of Emp x Proj for the rows
        index_cols = pd.MultiIndex.from_product([df_emps['id_emp'], df_projs['id_proj']], names=['Resource', 'Project']).to_frame(index=False)
        
        # Pivot existing data
        if not df_assign.empty:
            pivot = df_assign.pivot(index=['id_emp', 'id_proj'], columns='week_start', values='percent').reset_index()
            pivot.rename(columns={'id_emp': 'Resource', 'id_proj': 'Project'}, inplace=True)
            # Merge with full list to show empty rows
            main_df = pd.merge(index_cols, pivot, on=['Resource', 'Project'], how='left')
        else:
            main_df = index_cols
            
        # Ensure all week columns exist
        for w in weeks:
            if w not in main_df.columns:
                main_df[w] = 0
        
        # Fill NaNs
        main_df = main_df.fillna(0)
        
        # Filter only relevant columns
        display_cols = ['Resource', 'Project'] + weeks
        final_df = main_df[display_cols]

        # EDITABLE EDITOR
        edited_df = st.data_editor(final_df, hide_index=True, use_container_width=True, num_rows="dynamic")
        
        if st.button("?? Save Assignments"):
            # Unpivot (Melt) back to DB format
            melted = edited_df.melt(id_vars=['Resource', 'Project'], var_name='week_start', value_name='percent')
            melted = melted[melted['percent'] > 0] # Store only positive assignments
            
            # Clean old assignments for this range
            c = conn.cursor()
            for index, row in melted.iterrows():
                c.execute("INSERT OR REPLACE INTO assignments (id_proj, id_emp, week_start, percent) VALUES (?,?,?,?)",
                          (row['Project'], row['Resource'], row['week_start'], row['percent']))
            conn.commit()
            st.success("Matrix updated successfully!")
    else:
        st.info("Please add Employees and Projects first.")

# --- 5. FINANCE ---
elif selected == "Finance":
    st.subheader("?? Financial Control")
    
    df_fin = run_query("""
        SELECT p.id_proj, p.budget, p.capex_opex,
        COALESCE(SUM(t.hours * e.rate), 0) as actual_cost
        FROM projects p
        LEFT JOIN timesheets t ON p.id_proj = t.id_proj
        LEFT JOIN employees e ON t.id_emp = e.id_emp
        GROUP BY p.id_proj
    """)
    
    df_fin['remaining'] = df_fin['budget'] - df_fin['actual_cost']
    
    # Visuals
    c1, c2 = st.columns([2, 1])
    with c1:
        st.dataframe(df_fin.style.format({"budget": "€{:.2f}", "actual_cost": "€{:.2f}", "remaining": "€{:.2f}"}), use_container_width=True)
    with c2:
        if not df_fin.empty:
            fig = px.bar(df_fin, x='id_proj', y=['actual_cost', 'remaining'], title="Budget Usage", barmode='stack')
            fig.update_layout(height=300, margin=dict(l=0,r=0,b=0))
            st.plotly_chart(fig, use_container_width=True)

# --- 6. TIMESHEETS ---
elif selected == "Timesheets":
    st.subheader("?? Monthly Timesheets")
    
    c1, c2, c3 = st.columns(3)
    ts_month = c1.selectbox("Month", ["2023-11", "2023-12", "2024-01", "2024-02", "2024-03"])
    ts_emp = c2.selectbox("Employee", run_query("SELECT id_emp FROM employees")['id_emp'].tolist())
    
    # Grid input for timesheets
    projs = run_query("SELECT id_proj FROM projects")['id_proj'].tolist()
    
    # Check existing
    existing = run_query("SELECT id_proj, hours FROM timesheets WHERE id_emp=? AND month=?", (ts_emp, ts_month))
    
    ts_data = []
    for p in projs:
        hr = existing[existing['id_proj']==p]['hours'].sum() if not existing.empty else 0.0
        ts_data.append({"Project": p, "Hours": hr})
        
    df_ts = pd.DataFrame(ts_data)
    
    edited_ts = st.data_editor(df_ts, use_container_width=True)
    
    if st.button("Submit Timesheet"):
        for index, row in edited_ts.iterrows():
            # Delete old entry for this project/month/emp
            run_action("DELETE FROM timesheets WHERE id_emp=? AND month=? AND id_proj=?", (ts_emp, ts_month, row['Project']))
            # Insert new if > 0
            if row['Hours'] > 0:
                run_action("INSERT INTO timesheets (id_emp, month, id_proj, hours) VALUES (?,?,?,?)", 
                           (ts_emp, ts_month, row['Project'], row['Hours']))
        st.success("Timesheet Saved")

# --- 7. DASHBOARDS ---
elif selected == "Dashboards":
    st.subheader("?? Analytics")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Headcount", len(run_query("SELECT * FROM employees")))
    c2.metric("Active Projects", len(run_query("SELECT * FROM projects")))
    c3.metric("Total Hours Logged", run_query("SELECT SUM(hours) as h FROM timesheets")['h'].iloc[0])
    
    g1, g2 = st.columns(2)
    
    with g1:
        st.markdown("**Utilization by Department**")
        df_dept = run_query("""
            SELECT e.department, SUM(t.hours) as hours 
            FROM timesheets t JOIN employees e ON t.id_emp = e.id_emp 
            GROUP BY e.department""")
        if not df_dept.empty:
            st.plotly_chart(px.pie(df_dept, names='department', values='hours', hole=0.4), use_container_width=True)
            
    with g2:
        st.markdown("**Project Burn Rate (Actual vs Budget)**")
        df_burn = run_query("""
            SELECT p.name, p.budget, SUM(t.hours * e.rate) as cost
            FROM projects p 
            JOIN timesheets t ON p.id_proj = t.id_proj 
            JOIN employees e ON t.id_emp = e.id_emp
            GROUP BY p.name
        """)
        if not df_burn.empty:
            st.plotly_chart(px.bar(df_burn, x='name', y=['budget', 'cost'], barmode='group'), use_container_width=True)

# --- 8. ADMIN ---
elif selected == "Admin":
    st.subheader("??? System Administration")
    
    tab1, tab2 = st.tabs(["Dropdown Lists", "Backup & Restore"])
    
    with tab1:
        st.markdown("### Manage Department List")
        new_dept = st.text_input("Add new Department")
        if st.button("Add Department"):
            if new_dept:
                run_action("INSERT INTO config_lists VALUES (?,?)", ("department", new_dept))
                st.success(f"Added {new_dept}")
        
        curr_depts = run_query("SELECT value FROM config_lists WHERE category='department'")
        st.table(curr_depts)
        
    with tab2:
        st.markdown("### Full Data Export (JSON)")
        
        if st.button("Generate Backup"):
            tables = ["employees", "projects", "tasks", "calendar", "assignments", "timesheets", "config_lists"]
            backup = {}
            for t in tables:
                df = run_query(f"SELECT * FROM {t}")
                backup[t] = df.to_dict(orient='records')
            
            json_str = json.dumps(backup, indent=4)
            st.download_button("Download JSON Backup", json_str, "backup.json", "application/json")
            
        st.markdown("### Import Data")
        up_file = st.file_uploader("Upload JSON Backup", type=['json'])
        if up_file:
            try:
                data = json.load(up_file)
                # Basic restore logic
                for table, rows in data.items():
                    if rows:
                        df = pd.DataFrame(rows)
                        df.to_sql(table, conn, if_exists='append', index=False)
                st.success("Data Imported Successfully!")
            except Exception as e:
                st.error(f"Import failed: {e}")