# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import streamlit_antd_components as sac
import json

# --- CONFIGURACIÓN "ELEGANT BLUE" ---
st.set_page_config(page_title="Resource Plan v5", layout="wide", initial_sidebar_state="collapsed")

# CSS AVANZADO: Sticky Header, Minimalismo y Paleta Azul/Gris
st.markdown("""
<style>
    /* 1. LIMPIEZA GENERAL */
    header, footer, #MainMenu {visibility: hidden;}
    
    /* 2. STICKY HEADER (Barra Fija) */
    .sticky-nav {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        z-index: 999999;
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        border-bottom: 1px solid #e0e0e0;
        padding-top: 10px;
        padding-bottom: 10px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    
    /* 3. AJUSTE DE CONTENIDO (Para que no quede tapado por la barra) */
    .block-container {
        padding-top: 90px !important; /* Espacio para la barra fija */
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 100%;
    }
    
    /* 4. ESTILOS MINIMALISTAS */
    h3 { font-family: 'Helvetica Neue', sans-serif; font-weight: 600; color: #2c3e50; font-size: 1.1rem !important; margin: 0 0 10px 0;}
    .stButton button { border-radius: 6px !important; font-weight: 500; }
    
    /* 5. TABLAS COMPACTAS (Excel style) */
    .stDataFrame { font-size: 0.8rem; }
    div[data-testid="stDataEditor"] table { font-size: 0.8rem; }
    
    /* 6. Inputs Refinados */
    .stSelectbox div[data-baseweb="select"] { min-height: 32px; }
    .stTextInput input { min-height: 32px; padding: 4px 8px; }
    
</style>
""", unsafe_allow_html=True)

# --- GESTOR DE BBDD (Migración Automática) ---
def init_db():
    conn = sqlite3.connect('manager_v5.db')
    c = conn.cursor()
    tables = {
        'employees': ['id_emp TEXT PRIMARY KEY', 'first_name TEXT', 'last_name TEXT', 'email TEXT', 'type TEXT', 'rate REAL', 'manager TEXT', 'department TEXT'],
        'projects': ['id_proj TEXT PRIMARY KEY', 'name TEXT', 'platform TEXT', 'product TEXT', 'capex_opex TEXT', 'budget REAL'],
        'tasks': ['id INTEGER PRIMARY KEY AUTOINCREMENT', 'id_proj TEXT', 'task_name TEXT', 'assigned_to TEXT', 'start_date TEXT', 'end_date TEXT', 'progress INTEGER'],
        'calendar': ['id INTEGER PRIMARY KEY AUTOINCREMENT', 'id_emp TEXT', 'date TEXT', 'type TEXT'],
        'assignments': ['id INTEGER PRIMARY KEY AUTOINCREMENT', 'id_proj TEXT', 'id_emp TEXT', 'week_start TEXT', 'percent INTEGER'],
        'timesheets': ['id INTEGER PRIMARY KEY AUTOINCREMENT', 'id_emp TEXT', 'month TEXT', 'hours REAL', 'id_proj TEXT'],
        'config_lists': ['category TEXT', 'value TEXT']
    }
    for table, columns in tables.items():
        c.execute(f"CREATE TABLE IF NOT EXISTS {table} ({', '.join(columns)})")
        # (Omitimos lógica de migración compleja para ahorrar espacio, asumiendo esquema estable)
    conn.commit()
    return conn

conn = init_db()

# --- HELPERS INTELIGENTES (ID + NOMBRE) ---
def run_query(query, params=()):
    try: return pd.read_sql(query, conn, params=params)
    except: return pd.DataFrame()

def run_action(query, params=()):
    try: 
        conn.cursor().execute(query, params)
        conn.commit()
        return True
    except: return False

def get_emp_options():
    df = run_query("SELECT id_emp, first_name, last_name FROM employees")
    if df.empty: return {}
    # Crea un diccionario: {"EMP01 - Juan Perez": "EMP01"}
    return {f"{row['id_emp']} - {row['first_name']} {row['last_name']}": row['id_emp'] for i, row in df.iterrows()}

def get_proj_options():
    df = run_query("SELECT id_proj, name FROM projects")
    if df.empty: return {}
    return {f"{row['id_proj']} - {row['name']}": row['id_proj'] for i, row in df.iterrows()}

# --- NAVEGACIÓN STICKY (FIJA) ---
with st.container():
    st.markdown('<div class="sticky-nav">', unsafe_allow_html=True)
    # Menú SAC Segmented: Pequeño, Redondeado y Elegante
    selected = sac.segmented(
        items=[
            sac.SegmentedItem(label='Employees', icon='person-badge'),
            sac.SegmentedItem(label='Projects', icon='box-seam'),
            sac.SegmentedItem(label='Availability Sheet', icon='calendar4-week'),
            sac.SegmentedItem(label='Capacity Plan', icon='grid-3x3-gap'),
            sac.SegmentedItem(label='Finance', icon='currency-euro'),
            sac.SegmentedItem(label='Timesheet', icon='clock'),
            sac.SegmentedItem(label='Dashboards', icon='graph-up'),
            sac.SegmentedItem(label='Admin', icon='sliders'),
        ],
        label='', align='center', size='sm', radius='md', color='indigo', use_container_width=False
    )
    st.markdown('</div>', unsafe_allow_html=True)

# --- 1. EMPLOYEES ---
if selected == "Employees":
    c1, c2 = st.columns([1, 3])
    with c1:
        st.markdown("### 👤 New / Edit")
        with st.container(border=True):
            eid = st.text_input("Employee ID")
            fn = st.text_input("Name")
            ln = st.text_input("Surname")
            mail = st.text_input("Email")
            dep = st.selectbox("Dept", ["IT", "HR", "Finance", "Ops"])
            rate = st.number_input("Rate €", value=40.0)
            
            if st.button("Save Profile", type="primary", use_container_width=True):
                if eid:
                    run_action("INSERT OR REPLACE INTO employees VALUES (?,?,?,?,?,?,?,?)", 
                               (eid, fn, ln, mail, "Internal", rate, "Mgr", dep))
                    st.success("Saved")
                    st.rerun()
    
    with c2:
        st.markdown("### 👥 Employee Database")
        df = run_query("SELECT id_emp as ID, first_name as Name, last_name as Surname, department as Dept, rate as Rate FROM employees")
        st.dataframe(df, use_container_width=True, height=500, hide_index=True)

# --- 2. PROJECTS ---
elif selected == "Projects":
    t1, t2 = st.tabs(["List & Setup", "Gantt View"])
    with t1:
        c1, c2 = st.columns([1, 3])
        with c1:
            st.markdown("### 📦 New Project")
            with st.container(border=True):
                pid = st.text_input("Proj Code")
                pnm = st.text_input("Proj Name")
                pbg = st.number_input("Budget €", step=1000.0)
                pcp = st.multiselect("Type", ["OPEX", "CAPEX"], default=["OPEX"])
                if st.button("Create", type="primary", use_container_width=True):
                    run_action("INSERT OR REPLACE INTO projects VALUES (?,?,?,?,?,?)", 
                               (pid, pnm, "Web", "Prod", ",".join(pcp), pbg))
                    st.rerun()
        with c2:
            st.dataframe(run_query("SELECT id_proj, name, capex_opex, budget FROM projects"), use_container_width=True, hide_index=True)
            
    with t2:
        proj_map = get_proj_options()
        if proj_map:
            c_sel, _ = st.columns([2, 4])
            # Selector Inteligente: Muestra ID - Nombre
            p_label = c_sel.selectbox("Select Project", list(proj_map.keys()))
            p_id = proj_map[p_label]
            
            # Gantt Form Compacto
            with st.expander("➕ Add Task", expanded=False):
                with st.form("tsk"):
                    c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 2, 1])
                    tn = c1.text_input("Task Name")
                    # Selector Empleados Inteligente
                    emp_map = get_emp_options()
                    ass_label = c2.selectbox("Assignee", list(emp_map.keys()) if emp_map else ["Unassigned"])
                    ass_id = emp_map[ass_label] if emp_map else ""
                    
                    d1 = c3.date_input("Start")
                    d2 = c4.date_input("End")
                    if c5.form_submit_button("Add"):
                        run_action("INSERT INTO tasks (id_proj, task_name, assigned_to, start_date, end_date, progress) VALUES (?,?,?,?,?,?)",
                                   (p_id, tn, ass_id, str(d1), str(d2), 0))
                        st.rerun()
            
            # Gantt Chart Azul/Gris
            df_t = run_query("SELECT * FROM tasks WHERE id_proj=?", (p_id,))
            if not df_t.empty:
                fig = px.timeline(df_t, x_start="start_date", x_end="end_date", y="task_name", color="assigned_to", 
                                  color_discrete_sequence=px.colors.qualitative.Prism)
                fig.update_yaxes(autorange="reversed")
                fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig, use_container_width=True)

# --- 3. AVAILABILITY SHEET (FIXED) ---
elif selected == "Availability Sheet":
    st.markdown("### 📅 Availability Sheet")
    
    c1, c2 = st.columns([1, 3])
    emp_map = get_emp_options()
    
    if emp_map:
        sel_label = c1.selectbox("Select Resource", list(emp_map.keys()))
        sel_emp = emp_map[sel_label]
        
        # Panel de Edición Compacto
        with c2.popover("🖊️ Set Status (Vacation/Holiday)", use_container_width=False):
            dates = st.date_input("Select Range", value=[])
            status = st.radio("Type", ["Vacation", "Holiday", "Working"], horizontal=True)
            if st.button("Apply", type="primary"):
                # Logic simplificada para guardar
                if isinstance(dates, tuple) and len(dates) == 2:
                    s, e = dates
                    while s <= e:
                        if status == "Working": run_action("DELETE FROM calendar WHERE id_emp=? AND date=?", (sel_emp, str(s)))
                        else: run_action("INSERT OR REPLACE INTO calendar (id_emp, date, type) VALUES (?,?,?)", (sel_emp, str(s), status))
                        s += timedelta(days=1)
                st.rerun()

        # --- LOGICA CALENDARIO REPARADA 100% ---
        # 1. Generar DataFrame Maestro de Fechas (2 años)
        start_date = pd.Timestamp(datetime.now().year, 1, 1)
        end_date = pd.Timestamp(datetime.now().year + 1, 12, 31)
        all_dates = pd.date_range(start=start_date, end=end_date, freq='D')
        
        df_cal = pd.DataFrame({'date_dt': all_dates})
        df_cal['date_str'] = df_cal['date_dt'].dt.strftime('%Y-%m-%d')
        df_cal['weekday'] = df_cal['date_dt'].dt.weekday # 5=Sat, 6=Sun
        
        # 2. Traer Excepciones DB
        df_ex = run_query("SELECT date, type FROM calendar WHERE id_emp=?", (sel_emp,))
        
        # 3. Merge Seguro (Left Join)
        df_final = pd.merge(df_cal, df_ex, left_on='date_str', right_on='date', how='left')
        
        # 4. Asignar Valores Numéricos para Colores (Azul/Gris/Verde)
        def get_score(row):
            if pd.notna(row['type']):
                if row['type'] == 'Vacation': return 0.2 # Azul/Cyan
                if row['type'] == 'Holiday': return 0.0 # Azul Oscuro
            if row['weekday'] >= 5: return 0.5 # Gris (Fin de semana)
            return 1.0 # Verde (Working)

        df_final['val'] = df_final.apply(get_score, axis=1)
        
        # 5. Plotly Heatmap (Paleta Personalizada)
        # 0.0: Dark Blue, 0.2: Light Blue, 0.5: Grey, 1.0: Green
        custom_colors = [
            [0.0, '#1f4e79'], # Holiday (Azul oscuro)
            [0.2, '#3498db'], # Vacation (Azul claro)
            [0.5, '#ecf0f1'], # Weekend (Gris muy claro)
            [1.0, '#27ae60']  # Working (Verde elegante)
        ]
        
        fig = go.Figure(data=go.Heatmap(
            z=df_final['val'],
            x=df_final['date_dt'],
            y=[sel_label] * len(df_final),
            colorscale=custom_colors,
            showscale=False,
            xgap=1, ygap=1
        ))
        fig.update_layout(height=160, margin=dict(t=10, b=10, l=0, r=0), font=dict(size=10))
        st.plotly_chart(fig, use_container_width=True)
        
        st.caption("🟩 Available | ⬜ Weekend | 🟦 Vacation | 🟦 Holiday")
    else:
        st.info("Add employees first.")

# --- 4. CAPACITY PLAN (EXCEL-LIKE) ---
elif selected == "Capacity Plan":
    st.markdown("### 🔢 Capacity Plan")
    
    # Fechas Semanales
    today = datetime.now()
    start_w = today - timedelta(days=today.weekday())
    weeks = [(start_w + timedelta(weeks=i)).strftime('%d-%b') for i in range(12)] # Formato DD-Mes corto
    weeks_sql = [(start_w + timedelta(weeks=i)).strftime('%Y-%m-%d') for i in range(12)] # Para DB
    
    # Preparar Datos
    df_idx = run_query("SELECT e.id_emp, p.id_proj FROM employees e CROSS JOIN projects p")
    
    if not df_idx.empty:
        # Data existente
        df_assign = run_query("SELECT id_emp, id_proj, week_start, percent FROM assignments")
        
        # Crear Matriz (Pivot)
        matrix = pd.DataFrame(index=pd.MultiIndex.from_frame(df_idx), columns=weeks_sql).fillna(0)
        
        if not df_assign.empty:
            pivot = df_assign.pivot(index=['id_emp', 'id_proj'], columns='week_start', values='percent')
            matrix.update(pivot)
        
        # Reset index para visualización
        display_df = matrix.reset_index()
        
        # Mapear nombres para que sea legible en la tabla
        e_map = get_emp_options()
        p_map = get_proj_options()
        # Invertir mapas para buscar por ID
        e_map_inv = {v: k for k, v in e_map.items()}
        p_map_inv = {v: k for k, v in p_map.items()}
        
        display_df['Resource'] = display_df['id_emp'].map(e_map_inv)
        display_df['Project'] = display_df['id_proj'].map(p_map_inv)
        
        # Limpiar y ordenar columnas
        cols_final = ['Resource', 'Project'] + weeks_sql
        display_df = display_df[cols_final]
        # Renombrar columnas SQL a visuales para el usuario
        rename_map = dict(zip(weeks_sql, weeks))
        display_df = display_df.rename(columns=rename_map)
        
        # --- EDITOR DE DATOS (Compacto y Rápido) ---
        edited = st.data_editor(
            display_df, 
            hide_index=True, 
            use_container_width=True, 
            height=600,
            column_config={
                "Resource": st.column_config.TextColumn(disabled=True),
                "Project": st.column_config.TextColumn(disabled=True)
            }
        )
        
        if st.button("💾 Update Plan", type="primary"):
            # Proceso inverso: De visual a SQL
            # 1. Renombrar de vuelta a formato SQL
            inv_rename = {v: k for k, v in rename_map.items()}
            to_save = edited.rename(columns=inv_rename)
            
            # 2. Obtener IDs originales (Resource "EMP01 - Juan" -> "EMP01")
            to_save['id_emp'] = to_save['Resource'].map(e_map)
            to_save['id_proj'] = to_save['Project'].map(p_map)
            
            # 3. Melt
            melted = to_save.melt(id_vars=['id_emp', 'id_proj'], value_vars=weeks_sql, var_name='week', value_name='pct')
            melted = melted[melted['pct'] > 0]
            
            # 4. Guardar
            for _, row in melted.iterrows():
                run_action("INSERT OR REPLACE INTO assignments (id_proj, id_emp, week_start, percent) VALUES (?,?,?,?)",
                           (row['id_proj'], row['id_emp'], row['week'], row['pct']))
            st.success("Updated!")

# --- 5. FINANCE ---
elif selected == "Finance":
    st.markdown("### 💶 Project Financials")
    df = run_query("""
        SELECT p.name as Project, p.budget as Budget, 
        COALESCE(SUM(t.hours * e.rate), 0) as Actual,
        (p.budget - COALESCE(SUM(t.hours * e.rate), 0)) as Margin
        FROM projects p 
        LEFT JOIN timesheets t ON p.id_proj = t.id_proj
        LEFT JOIN employees e ON t.id_emp = e.id_emp
        GROUP BY p.name
    """)
    st.dataframe(df.style.format({"Budget":"€{:,.0f}", "Actual":"€{:,.0f}", "Margin":"€{:,.0f}"}), use_container_width=True, hide_index=True)

# --- 6. TIMESHEET ---
elif selected == "Timesheet":
    st.markdown("### ⏱️ Monthly Log")
    c1, c2, c3 = st.columns(3)
    month = c1.selectbox("Month", ["2024-01","2024-02","2024-03","2024-04"])
    emp_map = get_emp_options()
    
    if emp_map:
        emp_lbl = c2.selectbox("Employee", list(emp_map.keys()))
        emp_id = emp_map[emp_lbl]
        
        # Cargar datos
        projs = run_query("SELECT id_proj, name FROM projects")
        existing = run_query("SELECT id_proj, hours FROM timesheets WHERE id_emp=? AND month=?", (emp_id, month))
        
        data = []
        for _, p in projs.iterrows():
            h = existing[existing['id_proj']==p['id_proj']]['hours'].sum() if not existing.empty else 0.0
            data.append({"Project ID": p['id_proj'], "Project Name": p['name'], "Hours": h})
            
        edited_ts = st.data_editor(pd.DataFrame(data), use_container_width=True, hide_index=True)
        
        if st.button("Submit Timesheet", type="primary"):
            for _, row in edited_ts.iterrows():
                run_action("DELETE FROM timesheets WHERE id_emp=? AND month=? AND id_proj=?", (emp_id, month, row['Project ID']))
                if row['Hours'] > 0:
                    run_action("INSERT INTO timesheets (id_emp, month, id_proj, hours) VALUES (?,?,?,?)", (emp_id, month, row['Project ID'], row['Hours']))
            st.success("Saved")

# --- 7. DASHBOARDS (NUEVO) ---
elif selected == "Dashboards":
    st.markdown("### 📈 Executive Dashboard")
    
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Projects", len(run_query("SELECT * FROM projects")))
    k2.metric("Employees", len(run_query("SELECT * FROM employees")))
    hrs = run_query("SELECT SUM(hours) as h FROM timesheets")['h'].iloc[0]
    k3.metric("Total Hours", f"{hrs:.0f}" if hrs else "0")
    budget = run_query("SELECT SUM(budget) as b FROM projects")['b'].iloc[0]
    k4.metric("Total Budget", f"€{budget:,.0f}" if budget else "0")
    
    g1, g2 = st.columns(2)
    with g1:
        # Hours by Dept
        df_d = run_query("SELECT e.department, SUM(t.hours) as h FROM timesheets t JOIN employees e ON t.id_emp=e.id_emp GROUP BY e.department")
        if not df_d.empty:
            fig = px.pie(df_d, names='department', values='h', title='Hours by Department', hole=0.6, color_discrete_sequence=px.colors.sequential.Blues_r)
            st.plotly_chart(fig, use_container_width=True)
    with g2:
        # Burn Rate
        df_b = run_query("""SELECT p.name, p.budget, SUM(t.hours*e.rate) as cost FROM projects p JOIN timesheets t ON p.id_proj=t.id_proj JOIN employees e ON t.id_emp=e.id_emp GROUP BY p.name""")
        if not df_b.empty:
            fig = px.bar(df_b, x='name', y=['budget', 'cost'], barmode='group', title='Budget vs Actual Cost', color_discrete_sequence=['#95a5a6', '#3498db'])
            st.plotly_chart(fig, use_container_width=True)

# --- 8. ADMIN ---
elif selected == "Admin":
    st.markdown("### ⚙️ Data Management")
    t1, t2 = st.tabs(["Lists", "Backup"])
    with t1:
        c1, c2 = st.columns([3, 1])
        nd = c1.text_input("New Dept")
        if c2.button("Add"): run_action("INSERT INTO config_lists VALUES (?,?)", ("department", nd))
    with t2:
        if st.button("📥 Download JSON Backup"):
            data = {t: run_query(f"SELECT * FROM {t}").to_dict(orient='records') for t in ['employees','projects','tasks','calendar','assignments','timesheets']}
            st.download_button("Click to Save", json.dumps(data), "backup.json")
        
        up = st.file_uploader("📤 Restore JSON")
        if up and st.button("Restore"):
            d = json.load(up)
            for t, r in d.items(): 
                if r: pd.DataFrame(r).to_sql(t, conn, if_exists='append', index=False)
            st.success("Restored")