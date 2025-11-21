# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import streamlit_antd_components as sac
import json

# --- CONFIGURACIÓN DE PÁGINA Y CSS EXTREMO ---
st.set_page_config(page_title="Pro Manager v4", layout="wide", initial_sidebar_state="collapsed")

# CSS para eliminar espacios en blanco, hacer la barra enorme y cuadrada, y compactar todo
st.markdown("""
<style>
    /* Ocultar header default de Streamlit y footer */
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Eliminar padding superior para que la barra toque el techo */
    .block-container {
        padding-top: 0rem !important;
        padding-bottom: 1rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    
    /* Estilo para Inputs más compactos */
    .stTextInput input, .stSelectbox, .stNumberInput input {
        min-height: 0px;
        padding: 0px 5px;
        font-size: 0.9rem;
    }
    
    /* Ajuste de tablas */
    .stDataFrame { font-size: 0.85rem; }
    
    /* Titulos más pequeños */
    h3 { font-size: 1.3rem !important; margin-top: 10px; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# --- GESTOR DE BASE DE DATOS ROBUSTO (AUTO-MIGRACIÓN) ---
def init_db():
    conn = sqlite3.connect('manager_v4.db')
    c = conn.cursor()
    
    # Definimos tablas y columnas esperadas
    tables = {
        'employees': ['id_emp TEXT PRIMARY KEY', 'first_name TEXT', 'last_name TEXT', 'email TEXT', 
                      'type TEXT', 'rate REAL', 'manager TEXT', 'res_manager TEXT', 'department TEXT'],
        'projects': ['id_proj TEXT PRIMARY KEY', 'name TEXT', 'platform TEXT', 'product TEXT',
                     'capex_opex TEXT', 'budget REAL'],
        'tasks': ['id INTEGER PRIMARY KEY AUTOINCREMENT', 'id_proj TEXT', 'task_name TEXT',
                  'assigned_to TEXT', 'start_date TEXT', 'end_date TEXT', 'progress INTEGER'],
        'calendar': ['id INTEGER PRIMARY KEY AUTOINCREMENT', 'id_emp TEXT', 'date TEXT', 'type TEXT'],
        'assignments': ['id INTEGER PRIMARY KEY AUTOINCREMENT', 'id_proj TEXT', 'id_emp TEXT',
                        'week_start TEXT', 'percent INTEGER'],
        'timesheets': ['id INTEGER PRIMARY KEY AUTOINCREMENT', 'id_emp TEXT', 'month TEXT', 'hours REAL', 'id_proj TEXT'],
        'config_lists': ['category TEXT', 'value TEXT']
    }
    
    # Crear tablas si no existen
    for table, columns in tables.items():
        # Crear tabla basica
        cols_def = ", ".join(columns)
        c.execute(f"CREATE TABLE IF NOT EXISTS {table} ({cols_def})")
        
        # AUTO-MIGRACION: Verificar si faltan columnas (por si actualizas la app)
        current_cols_info = c.execute(f"PRAGMA table_info({table})").fetchall()
        current_cols = [col[1] for col in current_cols_info]
        
        for col_def in columns:
            col_name = col_def.split()[0]
            if col_name not in current_cols:
                # Si la columna es nueva en la versión nueva, la añadimos
                try:
                    c.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")
                    print(f"Migración: Columna {col_name} añadida a {table}")
                except:
                    pass # Ya existe o error sqlite

    # Restricciones UNIQUE separadas para evitar conflictos en migraciones
    try: c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_cal ON calendar(id_emp, date)")
    except: pass
    try: c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_assign ON assignments(id_proj, id_emp, week_start)")
    except: pass
    try: c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_config ON config_lists(category, value)")
    except: pass

    conn.commit()
    return conn

conn = init_db()

# --- HELPERS ---
def run_query(query, params=()):
    try:
        return pd.read_sql(query, conn, params=params)
    except Exception as e:
        st.error(f"Query Error: {e}")
        return pd.DataFrame()

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
        return ["IT", "HR", "Finance", "Ops"]
    return df['value'].tolist()

# --- BARRA DE NAVEGACIÓN SUPERIOR (ESTILO CUADRADO Y GRANDE) ---
# Usamos Segmented de SAC que es visualmente como botones cuadrados unidos
selected = sac.segmented(
    items=[
        sac.SegmentedItem(label='Employees', icon='people-fill'),
        sac.SegmentedItem(label='Projects', icon='rocket-takeoff-fill'),
        sac.SegmentedItem(label='Calendar', icon='calendar-date-fill'),
        sac.SegmentedItem(label='Assign', icon='table'),
        sac.SegmentedItem(label='Finance', icon='piggy-bank-fill'),
        sac.SegmentedItem(label='Time', icon='clock-fill'),
        sac.SegmentedItem(label='Admin', icon='gear-wide-connected'),
    ],
    label='', 
    align='center', 
    size='lg',  # Tamaño grande
    radius='sm', # Bordes casi cuadrados
    color='indigo', # Color base animado
    use_container_width=True # Ocupa todo el ancho
)

# --- 1. EMPLOYEES ---
if selected == "Employees":
    c_main, c_list = st.columns([1, 2])
    
    with c_main:
        st.markdown("### 👤 Add Employee")
        with st.container(border=True):
            eid = st.text_input("ID", placeholder="EMP-001")
            c1, c2 = st.columns(2)
            fname = c1.text_input("First Name")
            lname = c2.text_input("Last Name")
            email = st.text_input("Email")
            c3, c4 = st.columns(2)
            dept = c3.selectbox("Dept", get_list_values("department"))
            etype = c4.selectbox("Type", ["Internal", "External"])
            rate = st.number_input("Rate (€/h)", value=40.0)
            
            if st.button("💾 Save", use_container_width=True, type="primary"):
                if eid:
                    run_action("INSERT OR REPLACE INTO employees (id_emp, first_name, last_name, email, type, rate, department) VALUES (?,?,?,?,?,?,?)", 
                               (eid, fname, lname, email, etype, rate, dept))
                    st.success("Saved")
                    st.rerun()
                else:
                    st.warning("ID Required")

    with c_list:
        st.markdown("### 📋 List")
        df_emp = run_query("SELECT id_emp, first_name, last_name, department, type, rate FROM employees")
        st.dataframe(df_emp, use_container_width=True, height=400, hide_index=True)

# --- 2. PROJECTS ---
elif selected == "Projects":
    t1, t2 = st.tabs(["🛠️ Projects", "📊 Gantt"])
    
    with t1:
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown("### New Project")
            with st.container(border=True):
                pid = st.text_input("Project ID", placeholder="PRJ-2024-A")
                pname = st.text_input("Project Name")
                pbud = st.number_input("Budget Total (€)", min_value=0.0, step=1000.0)
                pcap = st.multiselect("Class", ["CAPEX", "OPEX"], default=["OPEX"])
                if st.button("🚀 Create Project", use_container_width=True, type="primary"):
                    run_action("INSERT OR REPLACE INTO projects (id_proj, name, capex_opex, budget) VALUES (?,?,?,?)", 
                               (pid, pname, ",".join(pcap), pbud))
                    st.rerun()
        with c2:
            st.dataframe(run_query("SELECT * FROM projects"), use_container_width=True, height=400)
            
    with t2:
        projs = run_query("SELECT id_proj FROM projects")
        if not projs.empty:
            sel_p = st.selectbox("Select Project to Edit Gantt", projs['id_proj'])
            # Formulario horizontal
            with st.form("gantt_add"):
                c1, c2, c3, c4, c5, c6 = st.columns([2, 2, 1.5, 1.5, 1, 1])
                tn = c1.text_input("Task")
                assignees = run_query("SELECT id_emp FROM employees")['id_emp'].tolist()
                ta = c2.selectbox("Who", assignees if assignees else ["Unassigned"])
                d1 = c3.date_input("Start")
                d2 = c4.date_input("End")
                pr = c5.number_input("%", 0, 100, step=10)
                if c6.form_submit_button("Add"):
                    run_action("INSERT INTO tasks (id_proj, task_name, assigned_to, start_date, end_date, progress) VALUES (?,?,?,?,?,?)",
                               (sel_p, tn, ta, str(d1), str(d2), pr))
                    st.rerun()
            
            # Visual
            df_t = run_query("SELECT * FROM tasks WHERE id_proj = ?", (sel_p,))
            if not df_t.empty:
                fig = px.timeline(df_t, x_start="start_date", x_end="end_date", y="task_name", color="progress", color_continuous_scale="RdBu")
                fig.update_yaxes(autorange="reversed")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No projects yet.")

# --- 3. CALENDAR ---
elif selected == "Calendar":
    st.markdown("### 📅 Team Availability")
    
    c_sel, c_act = st.columns([1, 3])
    emps = run_query("SELECT id_emp FROM employees")
    
    if not emps.empty:
        sel_emp = c_sel.selectbox("Select Employee", emps['id_emp'])
        
        with c_act.popover("🖊️ Modify Calendar (Click Here)"):
            d_range = st.date_input("Select Date Range", value=[])
            status_type = st.radio("Status", ["Vacation 🏖️", "Holiday 🎉", "Sick 🤒", "Working 💼"], horizontal=True)
            if st.button("Update Status"):
                if isinstance(d_range, tuple) and len(d_range) == 2:
                    s, e = d_range
                    curr = s
                    while curr <= e:
                        if "Working" in status_type:
                            run_action("DELETE FROM calendar WHERE id_emp=? AND date=?", (sel_emp, str(curr)))
                        else:
                            run_action("INSERT OR REPLACE INTO calendar (id_emp, date, type) VALUES (?,?,?)", (sel_emp, str(curr), status_type))
                        curr += timedelta(days=1)
                    st.success("Updated!")
                    st.rerun()
                elif isinstance(d_range, (datetime, pd.Timestamp)) or (d_range and not isinstance(d_range, tuple)):
                     # Caso un solo dia
                     date_str = str(d_range[0]) if isinstance(d_range, tuple) else str(d_range)
                     if "Working" in status_type:
                        run_action("DELETE FROM calendar WHERE id_emp=? AND date=?", (sel_emp, date_str))
                     else:
                        run_action("INSERT OR REPLACE INTO calendar (id_emp, date, type) VALUES (?,?,?)", (sel_emp, date_str, status_type))
                     st.rerun()

        # VISUAL HEATMAP LOGIC FIX
        now = datetime.now()
        # Fijamos variables start_y y end_y explícitamente para evitar error linea 253
        start_y = datetime(now.year, 1, 1)
        end_y = datetime(now.year + 1, 12, 31)
        
        dates = []
        curr = start_y
        while curr <= end_y:
            dates.append(curr)
            curr += timedelta(days=1)
            
        df_cal = pd.DataFrame({'date': dates})
        df_cal['date_str'] = df_cal['date'].dt.strftime('%Y-%m-%d')
        df_cal['month'] = df_cal['date'].dt.strftime('%Y-%m')
        df_cal['weekday'] = df_cal['date'].dt.weekday 
        
        df_ex = run_query("SELECT date, type FROM calendar WHERE id_emp = ?", (sel_emp,))
        df_final = df_cal.merge(df_ex, left_on='date_str', right_on='date', how='left')
        
        def get_color_val(row):
            if pd.notna(row['type']): 
                if "Vacation" in row['type']: return 0.2
                if "Holiday" in row['type']: return 0.0
                return 0.3
            if row['weekday'] >= 5: return 0.5 # Weekend
            return 1.0 # Working
            
        df_final['val'] = df_final.apply(get_color_val, axis=1)
        
        fig = go.Figure(data=go.Heatmap(
            z=df_final['val'],
            x=df_final['date'],
            y=[sel_emp] * len(df_final),
            colorscale=[[0, 'red'], [0.2, 'orange'], [0.5, '#eeeeee'], [1, '#2ecc71']],
            showscale=False
        ))
        fig.update_layout(height=180, margin=dict(t=10, b=10, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("🟩 Working | ⬜ Weekend | 🟧 Vacation | 🟥 Holiday")
    else:
        st.warning("Add employees first to see calendar.")

# --- 4. ASSIGNMENTS ---
elif selected == "Assign":
    st.markdown("### 📌 Resource Allocation Matrix")
    
    today = datetime.now()
    start_week = today - timedelta(days=today.weekday())
    # Generar 12 semanas
    weeks_cols = [(start_week + timedelta(weeks=i)).strftime('%Y-%m-%d') for i in range(12)]
    
    df_emp = run_query("SELECT id_emp FROM employees")
    df_prj = run_query("SELECT id_proj FROM projects")
    
    # FIX: Si no hay datos, mostrar aviso en vez de error
    if not df_emp.empty and not df_prj.empty:
        # Crear DataFrame Base
        index = pd.MultiIndex.from_product([df_emp['id_emp'], df_prj['id_proj']], names=['Resource', 'Project']).to_frame(index=False)
        
        # Traer datos existentes
        df_vals = run_query("SELECT * FROM assignments")
        
        if not df_vals.empty:
            pivot = df_vals.pivot(index=['id_emp', 'id_proj'], columns='week_start', values='percent').reset_index()
            pivot.rename(columns={'id_emp': 'Resource', 'id_proj': 'Project'}, inplace=True)
            final = pd.merge(index, pivot, on=['Resource', 'Project'], how='left')
        else:
            final = index
            
        # Rellenar semanas faltantes
        for w in weeks_cols:
            if w not in final.columns: final[w] = 0
        final = final.fillna(0)
        
        # Mostrar columnas ordenadas
        cols_to_show = ['Resource', 'Project'] + weeks_cols
        edited = st.data_editor(final[cols_to_show], hide_index=True, use_container_width=True, height=500)
        
        if st.button("💾 Save Matrix", type="primary"):
            # Guardar cambios
            melted = edited.melt(id_vars=['Resource', 'Project'], var_name='week', value_name='pct')
            melted = melted[melted['pct'] > 0]
            
            for i, row in melted.iterrows():
                run_action("INSERT OR REPLACE INTO assignments (id_proj, id_emp, week_start, percent) VALUES (?,?,?,?)",
                           (row['Project'], row['Resource'], row['week'], row['pct']))
            st.success("Allocations updated!")
    else:
        st.info("Please add Employees and Projects to enable Matrix.")

# --- 5. FINANCE ---
elif selected == "Finance":
    st.markdown("### 💰 Financial Overview")
    
    df = run_query("""
        SELECT p.name, p.budget, 
        COALESCE(SUM(t.hours * e.rate), 0) as actual
        FROM projects p 
        LEFT JOIN timesheets t ON p.id_proj = t.id_proj
        LEFT JOIN employees e ON t.id_emp = e.id_emp
        GROUP BY p.name, p.budget
    """)
    
    if not df.empty:
        df['margin'] = df['budget'] - df['actual']
        c1, c2 = st.columns(2)
        with c1:
            st.dataframe(df, use_container_width=True)
        with c2:
            fig = px.bar(df, x='name', y=['actual', 'margin'], title="Budget Consumption", barmode='stack')
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No financial data yet.")

# --- 6. TIMESHEETS ---
elif selected == "Time":
    st.markdown("### ⏱️ Monthly Timesheets")
    
    c1, c2, c3 = st.columns(3)
    ts_month = c1.selectbox("Month", ["2024-01", "2024-02", "2024-03", "2024-04", "2024-05", "2024-06"])
    
    emps = run_query("SELECT id_emp FROM employees")
    if not emps.empty:
        ts_emp = c2.selectbox("Employee", emps['id_emp'])
        
        projs = run_query("SELECT id_proj FROM projects")
        if not projs.empty:
            # Pre-cargar datos
            existing = run_query("SELECT id_proj, hours FROM timesheets WHERE id_emp=? AND month=?", (ts_emp, ts_month))
            
            input_data = []
            for p in projs['id_proj'].tolist():
                h = existing[existing['id_proj']==p]['hours'].sum() if not existing.empty else 0.0
                input_data.append({"Project": p, "Hours": h})
            
            df_in = pd.DataFrame(input_data)
            edited_ts = st.data_editor(df_in, use_container_width=True)
            
            if st.button("Submit Hours", type="primary"):
                for i, row in edited_ts.iterrows():
                    run_action("DELETE FROM timesheets WHERE id_emp=? AND month=? AND id_proj=?", (ts_emp, ts_month, row['Project']))
                    if row['Hours'] > 0:
                        run_action("INSERT INTO timesheets (id_emp, month, id_proj, hours) VALUES (?,?,?,?)", 
                                   (ts_emp, ts_month, row['Project'], row['Hours']))
                st.success("Timesheet Saved!")
        else:
            st.warning("No projects defined.")
    else:
        st.warning("No employees defined.")

# --- 7. ADMIN ---
elif selected == "Admin":
    st.markdown("### ⚙️ Admin & Backup")
    
    t1, t2 = st.tabs(["Lists", "💾 Backup/Restore"])
    
    with t1:
        st.write("**Departments List**")
        c1, c2 = st.columns([3,1])
        new_d = c1.text_input("New Department")
        if c2.button("Add"):
            run_action("INSERT INTO config_lists VALUES (?,?)", ("department", new_d))
            st.rerun()
        st.table(run_query("SELECT value FROM config_lists WHERE category='department'"))

    with t2:
        st.warning("⚠️ On Streamlit Cloud, data resets on reboot. Use this to save your data locally.")
        
        # EXPORT
        if st.button("📥 Download Backup (JSON)"):
            data = {}
            for t in ['employees', 'projects', 'tasks', 'calendar', 'assignments', 'timesheets', 'config_lists']:
                data[t] = run_query(f"SELECT * FROM {t}").to_dict(orient='records')
            
            st.download_button("Click to Download", json.dumps(data, indent=4), "backup.json", "application/json")
            
        st.markdown("---")
        
        # IMPORT
        up_file = st.file_uploader("📤 Restore Backup (JSON)", type=['json'])
        if up_file and st.button("Restore Data Now"):
            try:
                data = json.load(up_file)
                for t, rows in data.items():
                    if rows:
                        df = pd.DataFrame(rows)
                        # Truco: Append para no romper esquema, pero deberíamos limpiar antes si queremos restore completo
                        df.to_sql(t, conn, if_exists='append', index=False)
                st.success("Data Restored Successfully!")
            except Exception as e:
                st.error(f"Error: {e}")