# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import streamlit_antd_components as sac # Nueva librería visual
import json
import io

# --- CONFIGURACIÓN VISUAL AVANZADA (CSS) ---
st.set_page_config(page_title="Project Master Pro", layout="wide", initial_sidebar_state="collapsed")

# Estilos CSS para hacer el menú fijo (Sticky) y compactar la pantalla
st.markdown("""
<style>
    /* Quitar el header por defecto de Streamlit */
    header {visibility: hidden;}
    
    /* Ajustar el contenedor principal para que no quede tapado por el menú fijo */
    .block-container {
        padding-top: 100px !important; 
        padding-bottom: 2rem;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    
    /* Contenedor fijo para el Menú */
    .sticky-menu {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        z-index: 99999;
        background-color: white;
        padding-top: 10px;
        padding-bottom: 10px;
        box-shadow: 0px 2px 10px rgba(0,0,0,0.1);
        text-align: center;
    }
    
    /* Reducir tamaños de fuentes globales para ver más datos */
    html, body, [class*="css"] {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .stDataFrame {font-size: 0.85rem;}
    .stTextInput, .stSelectbox, .stNumberInput {font-size: 0.85rem;}
    
</style>
""", unsafe_allow_html=True)

# --- GESTIÓN DE BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect('app_db_v3.db')
    c = conn.cursor()
    
    # 1. Employees
    c.execute('''CREATE TABLE IF NOT EXISTS employees (
        id_emp TEXT PRIMARY KEY, first_name TEXT, last_name TEXT, email TEXT, 
        type TEXT, rate REAL, manager TEXT, res_manager TEXT, department TEXT)''')
    
    # 2. Projects
    c.execute('''CREATE TABLE IF NOT EXISTS projects (
        id_proj TEXT PRIMARY KEY, name TEXT, platform TEXT, product TEXT,
        capex_opex TEXT, budget REAL)''')
        
    # 2.2 Tasks
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT, id_proj TEXT, task_name TEXT,
        assigned_to TEXT, start_date TEXT, end_date TEXT, progress INTEGER)''')

    # 3. Calendar
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

    # 8. Config
    c.execute('''CREATE TABLE IF NOT EXISTS config_lists (
        category TEXT, value TEXT, UNIQUE(category, value))''')

    conn.commit()
    return conn

conn = init_db()

# --- HELPERS ---
def run_query(query, params=()):
    return pd.read_sql(query, conn, params=params)

def run_action(query, params=()):
    try:
        c = conn.cursor()
        c.execute(query, params)
        conn.commit()
        return True
    except Exception as e:
        st.error(f"DB Error: {e}")
        return False

def get_list_values(category):
    df = run_query("SELECT value FROM config_lists WHERE category = ?", (category,))
    if df.empty and category == "department":
        return ["IT", "HR", "Finance", "Operations"]
    return df['value'].tolist()

# --- MENÚ SUPERIOR FIJO (STICKY) ---
# Usamos un contenedor vacío primero para reservar el espacio visual
placeholder = st.empty()

# Renderizamos el menú dentro de un container que luego subiremos con CSS
with st.container():
    st.markdown('<div class="sticky-menu">', unsafe_allow_html=True)
    # Usamos SAC (Streamlit Antd Components) para botones más bonitos
    selected = sac.tabs([
        sac.TabsItem(label='Employees', icon='people-fill'),
        sac.TabsItem(label='Projects', icon='briefcase-fill'),
        sac.TabsItem(label='Calendar', icon='calendar-week-fill'),
        sac.TabsItem(label='Assignments', icon='table'),
        sac.TabsItem(label='Finance', icon='cash-coin'),
        sac.TabsItem(label='Timesheets', icon='clock-history'),
        sac.TabsItem(label='Dashboards', icon='graph-up-arrow'),
        sac.TabsItem(label='Admin', icon='gear-fill'),
    ], align='center', size='lg', variant='outline') # variant='outline' da efecto botón separado
    st.markdown('</div>', unsafe_allow_html=True)


# --- LÓGICA DE PÁGINAS ---

# 1. EMPLOYEES
if selected == "Employees":
    st.markdown("### 👥 Employees Management")
    
    with st.expander("➕ Add / Edit Employee", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        eid = c1.text_input("Employee ID")
        fname = c2.text_input("First Name")
        lname = c3.text_input("Last Name")
        email = c4.text_input("Email")
        
        c5, c6, c7, c8 = st.columns(4)
        etype = c5.selectbox("Type", ["Internal", "External"])
        dept = c6.selectbox("Department", get_list_values("department"))
        rate = c7.number_input("Hourly Rate (€)", min_value=0.0, step=10.0)
        mgr = c8.text_input("Manager")
        
        if st.button("💾 Save Employee", use_container_width=True):
            run_action("INSERT OR REPLACE INTO employees VALUES (?,?,?,?,?,?,?,?,?)", 
                       (eid, fname, lname, email, etype, rate, mgr, "ResMgr", dept))
            st.success("Saved!")
            st.rerun()

    st.dataframe(run_query("SELECT * FROM employees"), use_container_width=True, hide_index=True)

# 2. PROJECTS
elif selected == "Projects":
    st.markdown("### 🚀 Projects & Gantt")
    
    t1, t2 = st.tabs(["📋 Project List", "📊 Gantt Chart"])
    
    with t1:
        with st.expander("➕ New Project"):
            c1, c2, c3 = st.columns(3)
            pid = c1.text_input("Project ID")
            pname = c2.text_input("Project Name")
            pbud = c3.number_input("Budget (€)", min_value=0.0)
            
            c4, c5, c6 = st.columns(3)
            pcap = c4.multiselect("CAPEX / OPEX", ["CAPEX", "OPEX"], default=["OPEX"])
            pplat = c5.text_input("Platform")
            pprod = c6.text_input("Product")
            
            if st.button("Create Project", use_container_width=True):
                pcap_str = ",".join(pcap)
                run_action("INSERT OR REPLACE INTO projects VALUES (?,?,?,?,?,?)", 
                           (pid, pname, pplat, pprod, pcap_str, pbud))
                st.success("Project Created!")
                st.rerun()
        
        st.dataframe(run_query("SELECT * FROM projects"), use_container_width=True)
        
    with t2:
        projs = run_query("SELECT id_proj FROM projects")['id_proj'].tolist()
        if projs:
            c_sel, c_rest = st.columns([1, 3])
            sel_p = c_sel.selectbox("Select Project", projs)
            
            # Gantt Controls
            with c_rest.expander("Add Task to Gantt"):
                f1, f2, f3, f4, f5, f6 = st.columns([2, 2, 2, 2, 1, 1])
                tn = f1.text_input("Task")
                ta = f2.selectbox("Who", run_query("SELECT id_emp FROM employees")['id_emp'].tolist())
                d1 = f3.date_input("Start")
                d2 = f4.date_input("End")
                pr = f5.number_input("%", 0, 100, 0)
                if f6.button("Add"):
                    run_action("INSERT INTO tasks (id_proj, task_name, assigned_to, start_date, end_date, progress) VALUES (?,?,?,?,?,?)",
                               (sel_p, tn, ta, str(d1), str(d2), pr))
                    st.rerun()

            # Render Gantt
            df_t = run_query("SELECT * FROM tasks WHERE id_proj = ?", (sel_p,))
            if not df_t.empty:
                fig = px.timeline(df_t, x_start="start_date", x_end="end_date", y="task_name", color="progress", 
                                  title=f"Gantt: {sel_p}", color_continuous_scale='Blues')
                fig.update_yaxes(autorange="reversed")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No projects found.")

# 3. CALENDAR
elif selected == "Calendar":
    st.markdown("### 📅 Availability Calendar")
    
    c1, c2 = st.columns([1, 3])
    emps = run_query("SELECT id_emp FROM employees")['id_emp'].tolist()
    sel_emp = c1.selectbox("Select Employee", emps) if emps else None
    
    with c2:
        with st.popover("🖊️ Set Vacation / Holiday"):
            d_sel = st.date_input("Select Dates", value=[])
            status = st.selectbox("Type", ["Vacation", "Holiday", "Sick", "Working"])
            if st.button("Update Calendar"):
                if isinstance(d_sel, tuple) and len(d_sel) == 2:
                    start, end = d_sel
                    curr = start
                    while curr <= end:
                        if status == "Working":
                            run_action("DELETE FROM calendar WHERE id_emp=? AND date=?", (sel_emp, str(curr)))
                        else:
                            run_action("INSERT OR REPLACE INTO calendar (id_emp, date, type) VALUES (?,?,?)", (sel_emp, str(curr), status))
                        curr += timedelta(days=1)
                elif d_sel:
                     if status == "Working":
                         run_action("DELETE FROM calendar WHERE id_emp=? AND date=?", (sel_emp, str(d_sel)))
                     else:
                        run_action("INSERT OR REPLACE INTO calendar (id_emp, date, type) VALUES (?,?,?)", (sel_emp, str(d_sel), status))
                st.rerun()

    if sel_emp:
        # Heatmap Visual
        now = datetime.now()
        start_