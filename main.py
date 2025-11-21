# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import streamlit_antd_components as sac
import calendar as cal_module
import time

# --- 1. CONFIGURACIÓN ANDROID MATERIAL ---
st.set_page_config(page_title="App v11", layout="wide", initial_sidebar_state="collapsed")

# COLORES MATERIAL DESIGN
C_PRIMARY = "#2196F3"    # Azul Android
C_BG_MAIN = "#F5F5F5"    # Gris fondo App
C_CARD = "#FFFFFF"       # Blanco Tarjeta
C_TEXT = "#37474F"       # Gris Oscuro Texto

# --- CSS "ANDROID STYLE" (ESTILO MÓVIL) ---
st.markdown(f"""
<style>
    /* IMPORTAR FUENTE ROBOTO */
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Roboto', sans-serif;
        background-color: {C_BG_MAIN};
        color: {C_TEXT};
    }}

    /* OCULTAR CABECERA NATIVA */
    header[data-testid="stHeader"] {{display: none;}}
    #MainMenu {{display: none;}}
    footer {{display: none;}}

    /* --- BARRA SUPERIOR FIJA (STICKY REAL) --- */
    /* Creamos un panel blanco arriba del todo que flota sobre el resto */
    .fixed-header {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 70px;
        z-index: 999999;
        background: {C_CARD};
        box-shadow: 0 2px 4px rgba(0,0,0,0.1); /* Sombra suave */
        display: flex;
        align-items: center;
        padding-top: 10px;
        padding-bottom: 0px;
        border-bottom: 1px solid #eee;
    }}

    /* EMPUJAR EL CONTENIDO PARA QUE NO SE TAPE */
    .block-container {{
        padding-top: 90px !important;
        padding-bottom: 2rem;
    }}

    /* --- ESTÉTICA DE TARJETAS (CARD UI) --- */
    /* Contenedores redondeados como en Android */
    div[data-testid="stVerticalBlock"] > div[style*="background-color"] {{
        border-radius: 16px;
    }}
    
    .stDataFrame {{
        background: white;
        border-radius: 12px;
        padding: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }}

    /* INPUTS REDONDEADOS */
    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stNumberInput input {{
        border-radius: 8px !important;
        border: 1px solid #cfd8dc;
    }}
    
    /* BOTONES TIPO APP (PILL SHAPE) */
    .stButton button {{
        border-radius: 20px !important;
        font-weight: 500;
        background-color: {C_PRIMARY};
        color: white;
        border: none;
        box-shadow: 0 2px 5px rgba(0,0,0,0.15);
        transition: 0.2s;
    }}
    .stButton button:hover {{
        background-color: #1976D2;
        transform: translateY(-1px);
    }}

</style>
""", unsafe_allow_html=True)

# --- 2. DB ---
def init_db():
    conn = sqlite3.connect('android_v11.db', check_same_thread=False)
    c = conn.cursor()
    tables = {
        'employees': ['id TEXT PRIMARY KEY', 'name TEXT', 'surname TEXT', 'role TEXT', 'rate REAL', 'dept TEXT'],
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

def run_query(q, p=()): 
    try: return pd.read_sql(q, conn, params=p)
    except: return pd.DataFrame()

def run_action(q, p=()):
    try: conn.cursor().execute(q, p); conn.commit(); return True
    except Exception as e: st.error(e); return False

# --- 3. BARRA FIJA ---
# Inyectamos el HTML de la barra fija y metemos el menú dentro
placeholder = st.container()
with placeholder:
    st.markdown('<div class="fixed-header">', unsafe_allow_html=True)
    # Menú estilo Segmented (Botones planos unidos)
    selected = sac.segmented(
        items=[
            sac.SegmentedItem(label='Team', icon='people-fill'),
            sac.SegmentedItem(label='Projects', icon='briefcase-fill'),
            sac.SegmentedItem(label='Availability', icon='calendar-date-fill'), # Icono Calendario
            sac.SegmentedItem(label='Capacity', icon='grid-3x3-gap-fill'),
            sac.SegmentedItem(label='Finance', icon='pie-chart-fill'),
            sac.SegmentedItem(label='Admin', icon='gear-fill'),
        ],
        align='center', size='sm', radius='lg', color='blue', bg_color='transparent', use_container_width=True
    )
    st.markdown('</div>', unsafe_allow_html=True)

# --- 4. VISTAS ---

# A. TEAM
if selected == "Team":
    c1, c2 = st.columns([1, 2])
    with c1:
        with st.container(border=True):
            st.markdown("##### 👤 Add Member")
            eid = st.text_input("ID", placeholder="EMP01")
            fn = st.text_input("First Name")
            ln = st.text_input("Last Name")
            dp = st.selectbox("Dept", ["IT", "HR", "Sales", "Ops"])
            rt = st.number_input("Rate", value=40.0)
            if st.button("Save", use_container_width=True):
                run_action("INSERT OR REPLACE INTO employees VALUES (?,?,?,?,?,?)", (eid, fn, ln, "Staff", rt, dp))
                st.rerun()
    with c2:
        st.markdown("##### 👥 Employee List")
        df = run_query("SELECT id, name, surname, dept, rate FROM employees")
        st.dataframe(df, use_container_width=True, hide_index=True)

# B. PROJECTS
elif selected == "Projects":
    t1, t2 = st.tabs(["List", "Gantt"])
    with t1:
        c1, c2 = st.columns([1, 2])
        with c1:
            with st.container(border=True):
                st.markdown("##### 📂 New Project")
                pid = st.text_input("Code")
                pnm = st.text_input("Name")
                bg = st.number_input("Budget", step=1000.0)
                if st.button("Create", use_container_width=True):
                    run_action("INSERT OR REPLACE INTO projects VALUES (?,?,?,?,?)", (pid, pnm, bg, "OPEX", "Active"))
                    st.rerun()
        with c2:
            st.dataframe(run_query("SELECT id, name, budget, status FROM projects"), use_container_width=True)
            
    with t2:
        projs = run_query("SELECT id, name FROM projects")
        if not projs.empty:
            p_map = dict(zip(projs['name'], projs['id']))
            sel_p = st.selectbox("Select Project", list(p_map.keys()))
            pid = p_map[sel_p]
            
            with st.expander("➕ Add Task"):
                c_a, c_b, c_c = st.columns([2,1,1])
                tn = c_a.text_input("Task Name")
                d1 = c_b.date_input("Start")
                d2 = c_c.date_input("End")
                if st.button("Add Task"):
                    run_action("INSERT INTO tasks (proj_id, name, assignee, start, end, progress) VALUES (?,?,?,?,?,?)",
                               (pid, tn, "", str(d1), str(d2), 0))
                    st.rerun()
            
            df_t = run_query("SELECT * FROM tasks WHERE proj_id=?", (pid,))
            if not df_t.empty:
                fig = px.timeline(df_t, x_start="start", x_end="end", y="name", color_discrete_sequence=[C_PRIMARY])
                fig.update_yaxes(autorange="reversed")
                fig.update_layout(height=300, margin=dict(t=10,b=10))
                st.plotly_chart(fig, use_container_width=True)

# C. AVAILABILITY (CALENDARIO ESTILO DATE PICKER REAL)
elif selected == "Availability":
    c_ctrl, c_cal = st.columns([1, 2])
    
    emps = run_query("SELECT id, name FROM employees")
    if not emps.empty:
        e_map = dict(zip(emps['name'], emps['id']))
        with c_ctrl:
            with st.container(border=True):
                st.markdown("##### 1. Select Resource")
                sel_e = st.selectbox("Employee", list(e_map.keys()))
                eid = e_map[sel_e]
                
                st.markdown("##### 2. Update Status")
                st.info("Select dates below to block days.")
                with st.form("update_cal"):
                    dr = st.date_input("Select Dates", value=[])
                    stt = st.radio("Mark as:", ["Vacation (Blue)", "Holiday (Grey)", "Working (Clear)"])
                    if st.form_submit_button("Apply Changes", use_container_width=True):
                        if isinstance(dr, tuple) and len(dr) == 2:
                            s, e = dr
                            while s <= e:
                                code = "V" if "Vacation" in stt else ("H" if "Holiday" in stt else "W")
                                if code == "W": run_action("DELETE FROM calendar WHERE emp_id=? AND date=?", (eid, str(s)))
                                else: run_action("INSERT OR REPLACE INTO calendar (emp_id, date, type) VALUES (?,?,?)", (eid, str(s), code))
                                s += timedelta(days=1)
                            st.rerun()

        with c_cal:
            # --- CALENDARIO VISUAL TIPO "MÓVIL" ---
            # Mostramos un mes grande, estilo date picker
            col_m, col_y = st.columns([2, 1])
            curr_month = datetime.now().month
            curr_year = datetime.now().year
            
            # Selector de mes manual para navegar
            nav_m = col_m.selectbox("Month", list(cal_module.month_name)[1:], index=curr_month-1)
            nav_y = col_y.number_input("Year", value=curr_year, step=1)
            
            month_idx = list(cal_module.month_name).index(nav_m)
            
            # Datos DB
            df_ex = run_query("SELECT date, type FROM calendar WHERE emp_id=?", (eid,))
            ex_dict = dict(zip(df_ex['date'], df_ex['type'])) if not df_ex.empty else {}
            
            # Generar Matriz del Mes
            cal_matrix = cal_module.monthcalendar(nav_y, month_idx)
            
            # Preparar datos para Plotly Heatmap (Cuadrícula)
            z = []
            text = []
            
            # Invertir para que la semana 1 esté arriba en el gráfico
            for week in cal_matrix[::-1]:
                row_z = []
                row_t = []
                for day in week:
                    if day == 0:
                        row_z.append(None) # Vacío
                        row_t.append("")
                    else:
                        d_str = f"{nav_y}-{month_idx:02d}-{day:02d}"
                        wd = datetime(nav_y, month_idx, day).weekday()
                        is_we = wd >= 5
                        
                        # Colores: 0=Clear, 1=Weekend, 2=Vacation, 3=Holiday
                        val = 0
                        if d_str in ex_dict:
                            val = 2 if ex_dict[d_str] == 'V' else 3
                        elif is_we:
                            val = 1
                        
                        row_z.append(val)
                        row_t.append(str(day))
                z.append(row_z)
                text.append(row_t)

            # COLORES "DATE PICKER"
            # 0: Blanco, 1: Gris Claro (Finde), 2: Azul (Vac), 3: Gris Oscuro (Hol)
            colors = [
                [0.0, 'white'],      # Working
                [0.33, '#F5F5F5'],   # Weekend
                [0.66, '#2196F3'],   # Vacation (Azul Android)
                [1.0, '#607D8B']     # Holiday (Slate)
            ]
            
            fig = go.Figure(data=go.Heatmap(
                z=z,
                x=['Mon','Tue','Wed','Thu','Fri','Sat','Sun'],
                text=text,
                texttemplate="%{text}",
                textfont={"size":14, "color":"#37474F"},
                colorscale=colors,
                showscale=False,
                xgap=2, ygap=2 # Hueco entre celdas para efecto botón
            ))
            
            fig.update_layout(
                title=dict(text=f"{nav_m} {nav_y}", x=0.5),
                height=350,
                margin=dict(l=10, r=10, t=40, b=10),
                xaxis=dict(side="top", showgrid=False, tickfont=dict(weight='bold')),
                yaxis=dict(showticklabels=False, showgrid=False),
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig, use_container_width=True)
            
            st.caption("🟦 Vacation | ⬛ Holiday | ⬜ Working")

# D. CAPACITY (EXCEL STYLE)
elif selected == "Capacity":
    st.markdown("#### 🔢 Capacity Plan")
    
    # Fechas
    today = datetime.now()
    start_w = today - timedelta(days=today.weekday())
    weeks = [(start_w + timedelta(weeks=i)) for i in range(12)]
    cols_sql = [w.strftime('%Y-%m-%d') for w in weeks]
    cols_lbl = [w.strftime('%d/%m') for w in weeks]
    
    df_e = run_query("SELECT id, name FROM employees")
    df_p = run_query("SELECT id, name FROM projects")
    
    if not df_e.empty and not df_p.empty:
        # Matriz Base
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
        
        # Render Tabla Editable
        df_show = full[['Resource', 'Project'] + cols_sql].fillna(0)
        df_show.columns = ['Resource', 'Project'] + cols_lbl
        
        cfg = {"Resource": st.column_config.TextColumn(disabled=True), "Project": st.column_config.TextColumn(disabled=True)}
        for c in cols_lbl: cfg[c] = st.column_config.NumberColumn(min_value=0, max_value=100, step=10)
        
        edited = st.data_editor(df_show, hide_index=True, use_container_width=True, height=500, column_config=cfg)
        
        if st.button("💾 Save Plan", use_container_width=True):
            # Guardar lógica inversa
            save = edited.copy()
            save.columns = ['Resource', 'Project'] + cols_sql
            
            e_map = dict(zip(df_e['name'], df_e['id']))
            p_map = dict(zip(df_p['name'], df_p['id']))
            save['eid'] = save['Resource'].map(e_map)
            save['pid'] = save['Project'].map(p_map)
            
            melted = save.melt(id_vars=['eid','pid'], value_vars=cols_sql, var_name='wk', value_name='pct')
            melted = melted[melted['pct'] > 0]
            
            for _, r in melted.iterrows():
                run_action("INSERT OR REPLACE INTO assignments (proj_id, emp_id, week, percent) VALUES (?,?,?,?)",
                           (r['pid'], r['eid'], r['wk'], r['pct']))
            st.success("Updated!")

# E. FINANCE
elif selected == "Finance":
    st.markdown("#### 💶 Financial Status")
    df = run_query("""
        SELECT p.name, p.budget, COALESCE(SUM(t.hours * e.rate), 0) as actual
        FROM projects p LEFT JOIN timesheets t ON p.id=t.proj_id LEFT JOIN employees e ON t.emp_id=e.id 
        GROUP BY p.name""")
    df['margin'] = df['budget'] - df['actual']
    
    c1, c2 = st.columns(2)
    with c1: st.dataframe(df.style.format("€{:,.0f}"), use_container_width=True)
    with c2: st.plotly_chart(px.bar(df, x='name', y=['actual','margin'], barmode='stack'), use_container_width=True)

# F. ADMIN
elif selected == "Admin":
    st.markdown("#### ⚙️ Settings")
    if st.button("Backup JSON"):
        data = {t: run_query(f"SELECT * FROM {t}").to_dict(orient='records') for t in ['employees','projects','tasks','calendar','assignments','timesheets']}
        st.download_button("Download", json.dumps(data), "backup.json")