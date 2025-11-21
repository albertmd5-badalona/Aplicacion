# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import streamlit_antd_components as sac
import json
import calendar as cal_module

# --- 1. CONFIGURACIÓN CORPORATE ELITE (BLUE THEME) ---
st.set_page_config(page_title="CorpManager v6", layout="wide", initial_sidebar_state="collapsed")

# PALETA DE COLORES "BLUE ELITE"
C_BG = "#F0F2F6"      # Fondo General
C_MAIN = "#2C3E50"    # Azul Oscuro (Texto/Headers)
C_ACCENT = "#2980B9"  # Azul Vibrante (Botones/Links)
C_LIGHT = "#ECF0F1"   # Gris Claro (Fondos paneles)
C_SUCCESS = "#27AE60" # Verde (Solo para confirmaciones)

# CSS BLINDADO: STICKY HEADER REAL Y ESTILO EXQUISITO
st.markdown(f"""
<style>
    /* ELIMINAR TODO EL RUIDO DE STREAMLIT */
    header, footer, #MainMenu {{display: none !important;}}
    
    /* AJUSTE CRÍTICO: ELIMINAR ESPACIO SUPERIOR */
    .block-container {{
        padding-top: 70px !important; /* Espacio exacto para la barra */
        padding-bottom: 2rem !important;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
        max-width: 100%;
    }}
    
    /* BARRA DE NAVEGACIÓN FIJA (STICKY REAL) */
    .fixed-header {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 60px;
        z-index: 999999;
        background-color: white;
        border-bottom: 1px solid #BDC3C7;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        display: flex;
        align-items: center;
        justify-content: center;
    }}
    
    /* ESTILOS GLOBALES AZULES/GRISES */
    h1, h2, h3, p, div {{ font-family: 'Segoe UI', Helvetica, sans-serif; color: {C_MAIN}; }}
    
    /* BOTONES REFINADOS */
    .stButton button {{
        background-color: white;
        border: 1px solid #BDC3C7;
        color: {C_MAIN};
        border-radius: 4px;
        font-size: 0.85rem;
        transition: all 0.2s;
    }}
    .stButton button:hover {{
        border-color: {C_ACCENT};
        color: {C_ACCENT};
        background-color: #F7F9F9;
    }}
    
    /* TABLAS ESTILO EXCEL */
    .stDataFrame {{ font-size: 0.8rem; }}
    
    /* GANTT Y GRAFICOS */
    .js-plotly-plot .plotly .modebar {{ display: none !important; }}
    
</style>
""", unsafe_allow_html=True)

# --- 2. MOTOR DE BASE DE DATOS (MIGRACIÓN SEGURA) ---
def init_db():
    conn = sqlite3.connect('corp_v6.db')
    c = conn.cursor()
    tables = {
        'employees': ['id_emp TEXT PRIMARY KEY', 'first_name TEXT', 'last_name TEXT', 'email TEXT', 'type TEXT', 'rate REAL', 'department TEXT'],
        'projects': ['id_proj TEXT PRIMARY KEY', 'name TEXT', 'budget REAL', 'capex_opex TEXT'],
        'tasks': ['id INTEGER PRIMARY KEY AUTOINCREMENT', 'id_proj TEXT', 'task_name TEXT', 'assigned_to TEXT', 'start_date TEXT', 'end_date TEXT', 'progress INTEGER'],
        'calendar': ['id INTEGER PRIMARY KEY AUTOINCREMENT', 'id_emp TEXT', 'date TEXT', 'type TEXT'],
        'assignments': ['id INTEGER PRIMARY KEY AUTOINCREMENT', 'id_proj TEXT', 'id_emp TEXT', 'week_start TEXT', 'percent INTEGER'],
        'timesheets': ['id INTEGER PRIMARY KEY AUTOINCREMENT', 'id_emp TEXT', 'month TEXT', 'hours REAL', 'id_proj TEXT'],
        'config': ['key TEXT PRIMARY KEY', 'value TEXT']
    }
    for t, cols in tables.items():
        c.execute(f"CREATE TABLE IF NOT EXISTS {t} ({', '.join(cols)})")
    conn.commit()
    return conn

conn = init_db()

# --- 3. UTILS ---
def run_query(q, p=()): return pd.read_sql(q, conn, params=p)
def run_action(q, p=()): 
    try: 
        conn.cursor().execute(q, p)
        conn.commit()
        return True
    except: return False

def get_options(table, key_col, label_col):
    df = run_query(f"SELECT {key_col}, {label_col} FROM {table}")
    if df.empty: return {}
    return {f"{row[label_col]} ({row[key_col]})": row[key_col] for i, row in df.iterrows()}

# --- 4. BARRA SUPERIOR INYECTADA EN EL CONTENEDOR FIJO ---
# Usamos un truco: Creamos el HTML del contenedor fijo y metemos el componente de Python dentro
with st.container():
    st.markdown('<div class="fixed-header">', unsafe_allow_html=True)
    # SAC Segmented Control: Elegante, Azul, Sin scroll
    selected = sac.segmented(
        items=[
            sac.SegmentedItem(label='Employees', icon='people-fill'),
            sac.SegmentedItem(label='Projects', icon='briefcase-fill'),
            sac.SegmentedItem(label='Availability', icon='calendar3'),
            sac.SegmentedItem(label='Capacity Plan', icon='grid-3x3-gap-fill'),
            sac.SegmentedItem(label='Finance', icon='bank2'),
            sac.SegmentedItem(label='Timesheet', icon='clock-fill'),
            sac.SegmentedItem(label='Dashboards', icon='pie-chart-fill'),
            sac.SegmentedItem(label='Admin', icon='gear-fill'),
        ],
        label='', align='center', size='sm', radius='md', color='indigo', bg_color='transparent', use_container_width=False
    )
    st.markdown('</div>', unsafe_allow_html=True)

# --- 5. LÓGICA DE APLICACIÓN ---

# A. EMPLOYEES
if selected == "Employees":
    c1, c2 = st.columns([1, 3])
    with c1:
        st.markdown("### 👤 Profile")
        with st.container(border=True):
            eid = st.text_input("ID", placeholder="EMP01")
            fn = st.text_input("First Name")
            ln = st.text_input("Last Name")
            rate = st.number_input("Rate (€/h)", value=50.0, step=5.0)
            dept = st.selectbox("Dept", ["Consulting", "Development", "Management", "Sales"])
            if st.button("Save Profile", type="primary", use_container_width=True):
                if eid and fn:
                    run_action("INSERT OR REPLACE INTO employees VALUES (?,?,?,?,?,?,?)", (eid, fn, ln, "", "Internal", rate, dept))
                    st.rerun()
    with c2:
        st.markdown("### 👥 Directory")
        df = run_query("SELECT id_emp, first_name, last_name, department, rate FROM employees")
        st.dataframe(df, use_container_width=True, hide_index=True, height=500)

# B. PROJECTS
elif selected == "Projects":
    t1, t2 = st.tabs(["Setup", "Gantt Scheduler"])
    with t1:
        c1, c2 = st.columns([1, 3])
        with c1:
            st.markdown("### 📁 Project Data")
            with st.container(border=True):
                pid = st.text_input("Project Code")
                pnm = st.text_input("Project Name")
                bg = st.number_input("Budget €", step=5000.0)
                tp = st.selectbox("Type", ["OPEX", "CAPEX"])
                if st.button("Create Project", type="primary", use_container_width=True):
                    if pid:
                        run_action("INSERT OR REPLACE INTO projects VALUES (?,?,?,?)", (pid, pnm, bg, tp))
                        st.rerun()
        with c2:
            st.dataframe(run_query("SELECT * FROM projects"), use_container_width=True, hide_index=True)

    with t2:
        st.markdown("### 📅 Gantt Scheduler")
        p_map = get_options("projects", "id_proj", "name")
        e_map = get_options("employees", "id_emp", "first_name")
        
        if p_map:
            c_sel, c_add = st.columns([1, 3])
            curr_lbl = c_sel.selectbox("Select Project", list(p_map.keys()))
            curr_pid = p_map[curr_lbl]
            
            with c_add.expander("➕ Add / Edit Task", expanded=False):
                with st.form("task_form"):
                    col_a, col_b, col_c, col_d, col_e, col_f = st.columns([2, 2, 1.5, 1.5, 1, 1])
                    t_name = col_a.text_input("Task Name")
                    t_ass = col_b.selectbox("Assign To", list(e_map.keys()) if e_map else ["Unassigned"])
                    t_s = col_c.date_input("Start")
                    t_e = col_d.date_input("End")
                    t_p = col_e.number_input("%", 0, 100, 0)
                    if col_f.form_submit_button("Add"):
                        ass_id = e_map[t_ass] if e_map else "Unassigned"
                        run_action("INSERT INTO tasks (id_proj, task_name, assigned_to, start_date, end_date, progress) VALUES (?,?,?,?,?,?)",
                                   (curr_pid, t_name, ass_id, str(t_s), str(t_e), t_p))
                        st.rerun()
            
            # GANTT VISUALIZATION (EXQUISITE)
            df_t = run_query("SELECT * FROM tasks WHERE id_proj=?", (curr_pid,))
            if not df_t.empty:
                # Ensure dates are datetime
                df_t['start_date'] = pd.to_datetime(df_t['start_date'])
                df_t['end_date'] = pd.to_datetime(df_t['end_date'])
                
                fig = px.timeline(
                    df_t, x_start="start_date", x_end="end_date", y="task_name", color="assigned_to",
                    text="progress", hover_data=["progress"],
                    color_discrete_sequence=px.colors.qualitative.Blues, # FORZAR AZULES
                    height=300 + (len(df_t) * 20)
                )
                fig.update_traces(marker_line_color='rgb(255,255,255)', marker_line_width=1, opacity=0.9, texttemplate='%{text}%')
                fig.update_yaxes(autorange="reversed", title="")
                fig.update_xaxes(title="", side="top")
                fig.update_layout(
                    plot_bgcolor='white', paper_bgcolor='white', 
                    margin=dict(l=10, r=10, t=30, b=10),
                    showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No tasks yet for this project.")

# C. AVAILABILITY SHEET (TRADITIONAL CALENDAR VIEW)
elif selected == "Availability":
    st.markdown("### 🗓️ Monthly Availability View")
    
    c_ctrl, c_view = st.columns([1, 4])
    e_map = get_options("employees", "id_emp", "first_name")
    
    if e_map:
        with c_ctrl:
            curr_lbl = st.selectbox("Resource", list(e_map.keys()))
            curr_emp = e_map[curr_lbl]
            
            st.markdown("---")
            st.caption("Edit Availability")
            with st.form("cal_upd"):
                dr = st.date_input("Select Range", value=[])
                st_type = st.selectbox("Status", ["Vacation (Blue)", "Holiday (Grey)", "Working (Clear)"])
                if st.form_submit_button("Update Status"):
                    if isinstance(dr, tuple) and len(dr) == 2:
                        s, e = dr
                        while s <= e:
                            if "Working" in st_type: run_action("DELETE FROM calendar WHERE id_emp=? AND date=?", (curr_emp, str(s)))
                            else: 
                                code = "V" if "Vacation" in st_type else "H"
                                run_action("INSERT OR REPLACE INTO calendar (id_emp, date, type) VALUES (?,?,?)", (curr_emp, str(s), code))
                            s += timedelta(days=1)
                        st.rerun()

        with c_view:
            # GENERADOR DE CALENDARIO VISUAL (CUADRÍCULA)
            # Generamos datos para el año actual
            year = datetime.now().year
            
            # Traemos excepciones
            df_exc = run_query("SELECT date, type FROM calendar WHERE id_emp=?", (curr_emp,))
            exc_dict = dict(zip(df_exc['date'], df_exc['type'])) if not df_exc.empty else {}

            # Creamos Subplots (3 filas x 4 columnas = 12 meses)
            fig = make_subplots(rows=3, cols=4, subplot_titles=cal_module.month_name[1:], 
                                horizontal_spacing=0.02, vertical_spacing=0.08)

            for month in range(1, 13):
                # Matriz del mes
                month_cal = cal_module.monthcalendar(year, month)
                month_grid = []
                text_grid = []
                
                for week in month_cal:
                    row_vals = []
                    row_text = []
                    for day in week:
                        if day == 0: 
                            row_vals.append(None) # Dia vacio
                            row_text.append("")
                        else:
                            d_str = f"{year}-{month:02d}-{day:02d}"
                            wd = datetime(year, month, day).weekday()
                            
                            # Logica de Colores: 0=Working, 1=Weekend, 2=Vacation, 3=Holiday
                            val = 0 
                            if wd >= 5: val = 1 # Weekend
                            if d_str in exc_dict:
                                val = 2 if exc_dict[d_str] == 'V' else 3
                            
                            row_vals.append(val)
                            row_text.append(str(day))
                    
                    # Rellenar semana si falta
                    while len(row_vals) < 7: 
                        row_vals.append(None)
                        row_text.append("")
                        
                    month_grid.append(row_vals)
                    text_grid.append(row_text)
                
                # Invertir eje Y para que semana 1 este arriba
                month_grid = month_grid[::-1]
                text_grid = text_grid[::-1]

                # Añadir Heatmap a la celda
                row_idx = (month - 1) // 4 + 1
                col_idx = (month - 1) % 4 + 1
                
                # COLORES AZULES Y GRISES
                colors = [
                    [0.0, 'white'],     # 0: Working
                    [0.33, '#ECF0F1'],  # 1: Weekend (Light Grey)
                    [0.66, '#3498DB'],  # 2: Vacation (Blue)
                    [1.0, '#2C3E50']    # 3: Holiday (Dark Blue)
                ]
                
                hm = go.Heatmap(
                    z=month_grid,
                    x=['M','T','W','T','F','S','S'],
                    text=text_grid,
                    texttemplate="%{text}",
                    colorscale=colors,
                    showscale=False,
                    xgap=1, ygap=1,
                    hoverinfo='skip'
                )
                fig.add_trace(hm, row=row_idx, col=col_idx)

            fig.update_layout(
                height=700, 
                margin=dict(l=0, r=0, t=40, b=0),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#2C3E50', size=10)
            )
            fig.update_xaxes(showticklabels=True, ticks="", side="top")
            fig.update_yaxes(showticklabels=False, ticks="")
            st.plotly_chart(fig, use_container_width=True)

# D. CAPACITY PLAN (FAST EXCEL)
elif selected == "Capacity Plan":
    st.markdown("### 🔢 Capacity Matrix")
    
    # Fechas (12 Semanas)
    start_w = datetime.now() - timedelta(days=datetime.now().weekday())
    weeks_col = [(start_w + timedelta(weeks=i)).strftime('%Y-%m-%d') for i in range(12)]
    weeks_lbl = [(start_w + timedelta(weeks=i)).strftime('%d %b') for i in range(12)]
    
    # Dataframe Maestro
    df_emp = run_query("SELECT id_emp, first_name FROM employees")
    df_prj = run_query("SELECT id_proj, name FROM projects")
    
    if not df_emp.empty and not df_prj.empty:
        # Crear esqueleto
        idx = pd.MultiIndex.from_product([df_emp['id_emp'], df_prj['id_proj']], names=['EmpID', 'ProjID'])
        df_base = pd.DataFrame(index=idx).reset_index()
        
        # Mapear Nombres
        e_dict = dict(zip(df_emp['id_emp'], df_emp['first_name']))
        p_dict = dict(zip(df_prj['id_proj'], df_prj['name']))
        df_base['Resource'] = df_base['EmpID'].map(e_dict)
        df_base['Project'] = df_base['ProjID'].map(p_dict)
        
        # Traer Datos y Pivotar
        df_vals = run_query("SELECT * FROM assignments")
        if not df_vals.empty:
            pivot = df_vals.pivot(index=['id_emp', 'id_proj'], columns='week_start', values='percent').reset_index()
            df_final = pd.merge(df_base, pivot, left_on=['EmpID', 'ProjID'], right_on=['id_emp', 'id_proj'], how='left')
        else:
            df_final = df_base
            
        # Limpiar y Ordenar
        for w in weeks_col:
            if w not in df_final.columns: df_final[w] = 0
        
        cols_show = ['Resource', 'Project'] + weeks_col
        df_edit = df_final[cols_show].fillna(0)
        
        # Renombrar para UI
        rename_map = dict(zip(weeks_col, weeks_lbl))
        df_edit.rename(columns=rename_map, inplace=True)
        
        # EDITOR CONFIGURADO PARA NO HACER ZOOM (LinkColumn hack o NumberColumn)
        col_cfg = {
            "Resource": st.column_config.TextColumn(disabled=True),
            "Project": st.column_config.TextColumn(disabled=True)
        }
        # Configurar columnas de semanas como Número (Evita modal de texto largo)
        for w_lbl in weeks_lbl:
            col_cfg[w_lbl] = st.column_config.NumberColumn(required=True, default=0, step=10)

        edited = st.data_editor(
            df_edit, 
            hide_index=True, 
            use_container_width=True, 
            height=600,
            column_config=col_cfg
        )
        
        if st.button("💾 Save Matrix", type="primary"):
            # Reverse Logic
            inv_rename = {v: k for k, v in rename_map.items()}
            saved = edited.rename(columns=inv_rename)
            
            # Recuperar IDs
            saved['id_emp'] = saved['Resource'].map({v: k for k, v in e_dict.items()})
            saved['id_proj'] = saved['Project'].map({v: k for k, v in p_dict.items()})
            
            melted = saved.melt(id_vars=['id_emp', 'id_proj'], value_vars=weeks_col, var_name='week', value_name='pct')
            melted = melted[melted['pct'] > 0]
            
            for _, r in melted.iterrows():
                run_action("INSERT OR REPLACE INTO assignments (id_proj, id_emp, week_start, percent) VALUES (?,?,?,?)",
                           (r['id_proj'], r['id_emp'], r['week'], r['pct']))
            st.success("Plan Updated")

# E. FINANCE
elif selected == "Finance":
    st.markdown("### 💶 Financial Status")
    df = run_query("""
        SELECT p.name, p.budget, 
        COALESCE(SUM(t.hours * e.rate), 0) as consumed
        FROM projects p 
        LEFT JOIN timesheets t ON p.id_proj = t.id_proj
        LEFT JOIN employees e ON t.id_emp = e.id_emp
        GROUP BY p.name
    """)
    df['margin'] = df['budget'] - df['consumed']
    
    c1, c2 = st.columns(2)
    with c1:
        st.dataframe(df.style.format({"budget":"€{:,.0f}", "consumed":"€{:,.0f}", "margin":"€{:,.0f}"}), use_container_width=True)
    with c2:
        fig = px.bar(df, x='name', y=['consumed', 'margin'], barmode='stack', color_discrete_sequence=['#2980B9', '#BDC3C7'])
        fig.update_layout(plot_bgcolor='white')
        st.plotly_chart(fig, use_container_width=True)

# F. TIMESHEET
elif selected == "Timesheet":
    st.markdown("### ⏱️ Hours Input")
    c1, c2, c3 = st.columns(3)
    m = c1.selectbox("Month", ["2024-01","2024-02","2024-03","2024-04"])
    e_map = get_options("employees", "id_emp", "first_name")
    
    if e_map:
        curr_e = c2.selectbox("Employee", list(e_map.keys()))
        eid = e_map[curr_e]
        
        projs = run_query("SELECT id_proj, name FROM projects")
        exist = run_query("SELECT id_proj, hours FROM timesheets WHERE id_emp=? AND month=?", (eid, m))
        
        data = []
        for _, p in projs.iterrows():
            h = exist[exist['id_proj']==p['id_proj']]['hours'].sum() if not exist.empty else 0.0
            data.append({"Project": p['name'], "ID": p['id_proj'], "Hours": h})
            
        out = st.data_editor(pd.DataFrame(data), use_container_width=True, hide_index=True, column_config={"ID": None})
        if st.button("Submit", type="primary"):
            for _, r in out.iterrows():
                run_action("DELETE FROM timesheets WHERE id_emp=? AND month=? AND id_proj=?", (eid, m, r['ID']))
                if r['Hours'] > 0:
                    run_action("INSERT INTO timesheets (id_emp, month, id_proj, hours) VALUES (?,?,?,?)", (eid, m, r['ID'], r['Hours']))
            st.success("Saved")

# G. DASHBOARDS
elif selected == "Dashboards":
    st.markdown("### 📊 Executive View")
    k1, k2, k3 = st.columns(3)
    k1.metric("Total Projects", len(run_query("SELECT * FROM projects")))
    k2.metric("Active Resources", len(run_query("SELECT * FROM employees")))
    budget = run_query("SELECT SUM(budget) as b FROM projects")['b'].iloc[0]
    k3.metric("Total Portfolio", f"€{budget:,.0f}" if budget else "0")
    
    g1, g2 = st.columns(2)
    with g1:
        df = run_query("SELECT p.name, SUM(t.hours) as h FROM timesheets t JOIN projects p ON t.id_proj=p.id_proj GROUP BY p.name")
        if not df.empty:
            fig = px.pie(df, values='h', names='name', hole=0.7, title="Hours per Project", color_discrete_sequence=px.colors.sequential.Blues_r)
            st.plotly_chart(fig, use_container_width=True)
    with g2:
        df2 = run_query("SELECT e.department, COUNT(*) as c FROM employees e GROUP BY e.department")
        if not df2.empty:
            fig = px.bar(df2, x='department', y='c', title="Headcount by Dept", color_discrete_sequence=['#34495E'])
            fig.update_layout(plot_bgcolor='white')
            st.plotly_chart(fig, use_container_width=True)

# H. ADMIN
elif selected == "Admin":
    st.markdown("### ⚙️ System")
    if st.button("📥 Download JSON Backup"):
        data = {t: run_query(f"SELECT * FROM {t}").to_dict(orient='records') for t in ['employees','projects','tasks','calendar','assignments','timesheets']}
        st.download_button("Click to Save", json.dumps(data), "backup.json")
    
    up = st.file_uploader("📤 Restore Data")
    if up and st.button("Restore"):
        d = json.load(up)
        for t, r in d.items(): 
            if r: pd.DataFrame(r).to_sql(t, conn, if_exists='append', index=False)
        st.success("Restored")