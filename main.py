# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import streamlit_antd_components as sac
import json
import calendar as cal_module
import time

# --- 1. CONFIGURACIÓN ULTRA-PREMIUM ---
st.set_page_config(
    page_title="Nexus ERP | Resource Management",
    layout="wide",
    initial_sidebar_state="collapsed",
    page_icon="💎"
)

# COLORES CORPORATIVOS (Deep Ocean Theme)
C_NAV = "rgba(255, 255, 255, 0.85)" # Glass effect
C_TXT = "#1e293b"
C_ACCENT = "#3b82f6" # Blue 500
C_BG_MAIN = "#f8fafc" # Slate 50

# --- CSS DE INGENIERÍA (STICKY HEADER REAL) ---
st.markdown(f"""
<style>
    /* Ocultar elementos nativos molestos */
    header[data-testid="stHeader"] {{display: none;}}
    #MainMenu {{display: none;}}
    footer {{display: none;}}
    
    /* Fondo general sutil */
    .stApp {{
        background-color: {C_BG_MAIN};
    }}

    /* --- EL TRUCO MAESTRO PARA LA BARRA FIJA --- */
    /* Fijamos el contenedor del menú en la parte superior */
    .fixed-header {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        z-index: 999999;
        background: {C_NAV};
        backdrop-filter: blur(12px); /* Efecto Cristal */
        -webkit-backdrop-filter: blur(12px);
        border-bottom: 1px solid rgba(226, 232, 240, 0.8);
        padding: 0.8rem 2rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }}

    /* Empujamos el contenido hacia abajo para que no se tape */
    .block-container {{
        padding-top: 110px !important;
        padding-bottom: 3rem;
    }}

    /* TARJETAS KPI (SOPHISTICATED) */
    .kpi-card {{
        background: white;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        border: 1px solid #e2e8f0;
        text-align: center;
        transition: transform 0.2s;
    }}
    .kpi-card:hover {{ transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05); }}
    .kpi-val {{ font-size: 2rem; font-weight: 700; color: #0f172a; }}
    .kpi-lbl {{ font-size: 0.85rem; color: #64748b; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }}

    /* TABLAS LIMPIAS */
    .stDataFrame {{ border-radius: 10px; overflow: hidden; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }}
    
</style>
""", unsafe_allow_html=True)

# --- 2. MOTOR DE BASE DE DATOS (SQLite Robusto) ---
def init_db():
    conn = sqlite3.connect('nexus_erp.db', check_same_thread=False)
    c = conn.cursor()
    # Tablas maestras
    tables = {
        'employees': ['id TEXT PRIMARY KEY', 'name TEXT', 'surname TEXT', 'role TEXT', 'rate REAL', 'dept TEXT', 'active INTEGER'],
        'projects': ['id TEXT PRIMARY KEY', 'name TEXT', 'budget REAL', 'type TEXT', 'status TEXT'],
        'tasks': ['id INTEGER PRIMARY KEY AUTOINCREMENT', 'proj_id TEXT', 'name TEXT', 'assignee TEXT', 'start TEXT', 'end TEXT', 'progress INT'],
        'calendar': ['id INTEGER PRIMARY KEY AUTOINCREMENT', 'emp_id TEXT', 'date TEXT', 'type TEXT'],
        'assignments': ['id INTEGER PRIMARY KEY AUTOINCREMENT', 'proj_id TEXT', 'emp_id TEXT', 'week TEXT', 'percent INT'],
        'timesheets': ['id INTEGER PRIMARY KEY AUTOINCREMENT', 'emp_id TEXT', 'month TEXT', 'hours REAL', 'proj_id TEXT']
    }
    for t, cols in tables.items(): c.execute(f"CREATE TABLE IF NOT EXISTS {t} ({', '.join(cols)})")
    conn.commit()
    return conn

conn = init_db()

# --- 3. FUNCIONES CORE ---
def run_query(q, p=()): 
    try: return pd.read_sql(q, conn, params=p)
    except: return pd.DataFrame()

def run_action(q, p=()):
    try: conn.cursor().execute(q, p); conn.commit(); return True
    except Exception as e: st.error(f"Error: {e}"); return False

def kpi(label, value, delta=None):
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-lbl">{label}</div>
        <div class="kpi-val">{value}</div>
    </div>
    """, unsafe_allow_html=True)

# --- 4. BARRA DE NAVEGACIÓN FIJA (INYECCIÓN DIRECTA) ---
# Usamos un contenedor vacío para reservar el espacio visual, pero el CSS hace el trabajo sucio.
placeholder = st.container()

with placeholder:
    st.markdown('<div class="fixed-header">', unsafe_allow_html=True)
    selected = sac.segmented(
        items=[
            sac.SegmentedItem(label='Dashboard', icon='speedometer'),
            sac.SegmentedItem(label='Talent', icon='people'),
            sac.SegmentedItem(label='Portfolio', icon='briefcase'),
            sac.SegmentedItem(label='Availability', icon='calendar4-week'),
            sac.SegmentedItem(label='Capacity', icon='grid-3x3'),
            sac.SegmentedItem(label='Financials', icon='graph-up-arrow'),
            sac.SegmentedItem(label='Admin', icon='sliders'),
        ],
        label='', align='center', size='sm', radius='lg', color='indigo', bg_color='transparent', use_container_width=True
    )
    st.markdown('</div>', unsafe_allow_html=True)

# --- 5. PÁGINAS INTELIGENTES ---

# A. DASHBOARD (EXECUTIVE VIEW)
if selected == "Dashboard":
    st.markdown("### 🚀 Executive Overview")
    
    # KPIs en vivo
    cols = st.columns(4)
    headcount = run_query("SELECT COUNT(*) as c FROM employees")['c'].iloc[0]
    active_projs = run_query("SELECT COUNT(*) as c FROM projects")['c'].iloc[0]
    total_hours = run_query("SELECT SUM(hours) as h FROM timesheets")['h'].iloc[0] or 0
    total_budget = run_query("SELECT SUM(budget) as b FROM projects")['b'].iloc[0] or 0
    
    with cols[0]: kpi("Total Talent", headcount)
    with cols[1]: kpi("Active Projects", active_projs)
    with cols[2]: kpi("Logged Hours", f"{total_hours:,.0f}")
    with cols[3]: kpi("Portfolio Value", f"€{total_budget/1000:,.0f}k")

    st.markdown("---")
    
    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("📊 Budget Burn Rate")
        df_burn = run_query("""
            SELECT p.name, p.budget, COALESCE(SUM(t.hours * e.rate),0) as actual
            FROM projects p 
            LEFT JOIN timesheets t ON p.id=t.proj_id 
            LEFT JOIN employees e ON t.emp_id=e.id 
            GROUP BY p.name
        """)
        if not df_burn.empty:
            fig = px.bar(df_burn, x='name', y=['actual', 'budget'], barmode='group', 
                         color_discrete_sequence=['#3b82f6', '#cbd5e1'], height=350)
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(t=10))
            st.plotly_chart(fig, use_container_width=True)
            
    with c2:
        st.subheader("🧩 Utilization by Dept")
        df_dept = run_query("SELECT e.dept, COUNT(*) as c FROM employees e GROUP BY e.dept")
        if not df_dept.empty:
            fig = px.pie(df_dept, values='c', names='dept', hole=0.6, color_discrete_sequence=px.colors.sequential.Blues_r, height=350)
            st.plotly_chart(fig, use_container_width=True)

# B. TALENT (EMPLOYEES)
elif selected == "Talent":
    c1, c2 = st.columns([1, 3])
    with c1:
        with st.container(border=True):
            st.markdown("#### 👤 Add Profile")
            eid = st.text_input("Employee ID", placeholder="EMP-000")
            fn = st.text_input("First Name")
            ln = st.text_input("Last Name")
            role = st.text_input("Role / Title")
            dept = st.selectbox("Department", ["Engineering", "Product", "Design", "Sales", "HR"])
            rate = st.number_input("Hourly Rate (€)", 0.0, 500.0, 50.0)
            if st.button("Create Profile", type="primary", use_container_width=True):
                run_action("INSERT OR REPLACE INTO employees VALUES (?,?,?,?,?,?,1)", (eid, fn, ln, role, rate, dept))
                st.toast("Profile Created!", icon="✅")
                time.sleep(1)
                st.rerun()
                
    with c2:
        st.markdown("#### 👥 Roster")
        df = run_query("SELECT id as ID, name as Name, surname as Surname, role as Role, dept as Dept, rate as Rate FROM employees")
        st.dataframe(df, use_container_width=True, hide_index=True, height=500)

# C. PORTFOLIO (PROJECTS & GANTT)
elif selected == "Portfolio":
    tab1, tab2 = st.tabs(["📂 Projects Setup", "📅 Gantt Timeline"])
    
    with tab1:
        c1, c2 = st.columns([1, 2])
        with c1:
            with st.container(border=True):
                st.markdown("#### New Project")
                pid = st.text_input("Project Code")
                pnm = st.text_input("Project Name")
                bg = st.number_input("Budget Total", step=1000.0)
                typ = st.selectbox("Class", ["OPEX", "CAPEX"])
                sts = st.selectbox("Status", ["Planning", "Active", "On Hold", "Done"])
                if st.button("Launch Project", type="primary", use_container_width=True):
                    run_action("INSERT OR REPLACE INTO projects VALUES (?,?,?,?,?)", (pid, pnm, bg, typ, sts))
                    st.rerun()
        with c2:
            st.dataframe(run_query("SELECT * FROM projects"), use_container_width=True)
            
    with tab2:
        col_sel, col_add = st.columns([1, 3])
        projs = run_query("SELECT id, name FROM projects")
        if not projs.empty:
            p_map = dict(zip(projs['name'], projs['id']))
            sel_name = col_sel.selectbox("Select Project Context", list(p_map.keys()))
            pid = p_map[sel_name]
            
            with col_add.expander("➕ Add Phase / Task", expanded=False):
                with st.form("gantt_f"):
                    c1, c2, c3, c4 = st.columns(4)
                    tn = c1.text_input("Task Name")
                    start = c2.date_input("Start")
                    end = c3.date_input("End")
                    prog = c4.slider("%", 0, 100, 0)
                    if st.form_submit_button("Add Task"):
                        run_action("INSERT INTO tasks (proj_id, name, assignee, start, end, progress) VALUES (?,?,?,?,?,?)",
                                   (pid, tn, "", str(start), str(end), prog))
                        st.rerun()

            # GANTT VISUALIZATION
            df_t = run_query("SELECT * FROM tasks WHERE proj_id=?", (pid,))
            if not df_t.empty:
                fig = px.timeline(df_t, x_start="start", x_end="end", y="name", color="progress", 
                                  color_continuous_scale="Blues", title=f"Timeline: {sel_name}")
                fig.update_yaxes(autorange="reversed")
                fig.update_layout(height=400, margin=dict(t=40, b=20), paper_bgcolor='white', plot_bgcolor='white')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No timeline data initialized for this project.")

# D. AVAILABILITY (CALENDAR SQUARES/CIRCLES)
elif selected == "Availability":
    c1, c2 = st.columns([1, 3])
    
    emps = run_query("SELECT id, name, surname FROM employees")
    if not emps.empty:
        e_map = {f"{r['name']} {r['surname']}": r['id'] for _, r in emps.iterrows()}
        
        with c1:
            st.markdown("#### 🗓️ Resource")
            sel_e = st.selectbox("Select Employee", list(e_map.keys()))
            eid = e_map[sel_e]
            
            st.info("Select a range to update status.")
            with st.form("cal_upd"):
                dr = st.date_input("Date Range", value=[])
                stt = st.radio("Type", ["Working", "Vacation", "Holiday"])
                if st.form_submit_button("Update Status", type="primary"):
                    if isinstance(dr, tuple) and len(dr)==2:
                        s, e = dr
                        while s <= e:
                            code = "V" if stt == "Vacation" else ("H" if stt == "Holiday" else "W")
                            if code == "W": run_action("DELETE FROM calendar WHERE emp_id=? AND date=?", (eid, str(s)))
                            else: run_action("INSERT OR REPLACE INTO calendar (emp_id, date, type) VALUES (?,?,?)", (eid, str(s), code))
                            s += timedelta(days=1)
                        st.rerun()

        with c2:
            # LOGICA DE VISUALIZACION (SCATTER PLOT TIPO GITHUB/CALENDAR)
            yr = datetime.now().year
            df_cal = run_query("SELECT date, type FROM calendar WHERE emp_id=?", (eid,))
            cal_dict = dict(zip(df_cal['date'], df_cal['type'])) if not df_cal.empty else {}
            
            fig = go.Figure()
            months = range(1, 13)
            
            # Layout Grid 4x3
            for idx, m in enumerate(months):
                matrix = cal_module.monthcalendar(yr, m)
                x_off, y_off = (idx % 4) * 8, (2 - idx // 4) * 8
                
                # Titulo Mes
                fig.add_trace(go.Scatter(x=[x_off+3.5], y=[y_off+6.5], text=[cal_module.month_abbr[m]], 
                                         mode="text", textfont=dict(color="#334155", weight="bold")))
                
                for w_i, week in enumerate(matrix):
                    for d_i, day in enumerate(week):
                        if day != 0:
                            d_str = f"{yr}-{m:02d}-{day:02d}"
                            is_we = d_i >= 5
                            
                            color = "rgba(0,0,0,0)"
                            text_col = "#94a3b8"
                            
                            if d_str in cal_dict:
                                if cal_dict[d_str] == 'V': color = "#3b82f6" # Azul Vacaciones
                                else: color = "#64748b" # Gris Festivo
                                text_col = "white"
                            elif not is_we:
                                color = "#22c55e" # Verde Trabajo
                                text_col = "white"
                                
                            if color != "rgba(0,0,0,0)":
                                fig.add_trace(go.Scatter(
                                    x=[x_off + d_i], y=[y_off + (5 - w_i)],
                                    mode='markers+text',
                                    marker=dict(size=12, color=color),
                                    text=[str(day)], textfont=dict(color=text_col, size=8),
                                    hoverinfo='skip'
                                ))
            
            fig.update_layout(width=900, height=500, showlegend=False, 
                              xaxis=dict(visible=False, range=[-1, 32]), 
                              yaxis=dict(visible=False, range=[-1, 24]),
                              margin=dict(t=0, b=0, l=0, r=0), plot_bgcolor="white")
            
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Legend: 🟢 Working | 🔵 Vacation | ⚫ Holiday")

# E. CAPACITY PLAN (EXCEL GRID)
elif selected == "Capacity":
    st.markdown("### 🔢 Capacity Matrix")
    
    # Logica de fechas
    today = datetime.now()
    start_w = today - timedelta(days=today.weekday())
    weeks = [(start_w + timedelta(weeks=i)) for i in range(12)]
    cols_sql = [w.strftime('%Y-%m-%d') for w in weeks]
    cols_lbl = [w.strftime('%d %b') for w in weeks] # Formato "12 Nov"
    
    df_e = run_query("SELECT id, name FROM employees")
    df_p = run_query("SELECT id, name FROM projects")
    
    if not df_e.empty and not df_p.empty:
        # Crear matriz base
        idx = pd.MultiIndex.from_product([df_e['id'], df_p['id']], names=['eid', 'pid']).to_frame(index=False)
        idx['Resource'] = idx['eid'].map(dict(zip(df_e['id'], df_e['name'])))
        idx['Project'] = idx['pid'].map(dict(zip(df_p['id'], df_p['name'])))
        
        vals = run_query("SELECT * FROM assignments")
        if not vals.empty:
            piv = vals.pivot(index=['emp_id', 'proj_id'], columns='week', values='percent').reset_index()
            full = pd.merge(idx, piv, left_on=['eid', 'pid'], right_on=['emp_id', 'proj_id'], how='left')
        else:
            full = idx
            
        for c in cols_sql:
            if c not in full.columns: full[c] = 0
            
        # Preparar para mostrar
        show_df = full[['Resource', 'Project'] + cols_sql].fillna(0)
        show_df.columns = ['Resource', 'Project'] + cols_lbl # Renombrar bonito
        
        # Configuración de columnas
        col_cfg = {"Resource": st.column_config.TextColumn(disabled=True), 
                   "Project": st.column_config.TextColumn(disabled=True)}
        for c in cols_lbl:
            col_cfg[c] = st.column_config.NumberColumn(min_value=0, max_value=100, step=10)
            
        edited = st.data_editor(show_df, hide_index=True, use_container_width=True, height=600, column_config=col_cfg)
        
        if st.button("💾 Save Capacity Plan", type="primary"):
            # Invertir renombrado
            save_df = edited.copy()
            save_df.columns = ['Resource', 'Project'] + cols_sql
            
            # Recuperar IDs
            e_map = dict(zip(df_e['name'], df_e['id']))
            p_map = dict(zip(df_p['name'], df_p['id']))
            save_df['eid'] = save_df['Resource'].map(e_map)
            save_df['pid'] = save_df['Project'].map(p_map)
            
            melted = save_df.melt(id_vars=['eid', 'pid'], value_vars=cols_sql, var_name='wk', value_name='pct')
            melted = melted[melted['pct'] > 0]
            
            for _, r in melted.iterrows():
                run_action("INSERT OR REPLACE INTO assignments (proj_id, emp_id, week, percent) VALUES (?,?,?,?)",
                           (r['pid'], r['eid'], r['wk'], r['pct']))
            st.success("Plan updated successfully!")

# F. FINANCIALS
elif selected == "Financials":
    st.markdown("### 💶 Financial Health")
    df = run_query("""
        SELECT p.name, p.budget, COALESCE(SUM(t.hours * e.rate), 0) as actual
        FROM projects p 
        LEFT JOIN timesheets t ON p.id=t.proj_id 
        LEFT JOIN employees e ON t.emp_id=e.id 
        GROUP BY p.name
    """)
    df['margin'] = df['budget'] - df['actual']
    
    c1, c2 = st.columns(2)
    with c1:
        st.dataframe(df.style.format({"budget": "€{:,.0f}", "actual": "€{:,.0f}", "margin": "€{:,.0f}"}), use_container_width=True)
    with c2:
        fig = px.bar(df, x='name', y=['actual', 'margin'], title="Budget vs Actual", barmode='stack', 
                     color_discrete_sequence=['#3b82f6', '#e2e8f0'])
        st.plotly_chart(fig, use_container_width=True)

# G. ADMIN (BACKUP)
elif selected == "Admin":
    st.warning("⚠️ System Area")
    
    if st.button("📥 Export Database (JSON)"):
        data = {t: run_query(f"SELECT * FROM {t}").to_dict(orient='records') for t in ['employees','projects','tasks','calendar','assignments','timesheets']}
        st.download_button("Download Backup", json.dumps(data, indent=2), "nexus_backup.json")
        
    up = st.file_uploader("📤 Restore Database")
    if up and st.button("Restore Data"):
        d = json.load(up)
        for t, r in d.items():
            if r: pd.DataFrame(r).to_sql(t, conn, if_exists='append', index=False)
        st.success("System restored successfully.")