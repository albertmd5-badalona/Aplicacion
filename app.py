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

# --- 1. CONFIGURACIÓN & CSS "BOSS EDITION" ---
st.set_page_config(page_title="CorpResource v7", layout="wide", initial_sidebar_state="collapsed")

# COLORES
C_NAV_BG = "#FFFFFF"
C_TXT = "#2C3E50"     # Azul oscuro corporativo
C_WORK = "#27AE60"    # Verde círculo
C_VAC = "#3498DB"     # Azul vacaciones
C_HOL = "#7F8C8D"     # Gris festivo

st.markdown(f"""
<style>
    /* Ocultar elementos nativos */
    header, footer, #MainMenu {{display: none !important;}}
    
    /* AJUSTE MILIMÉTRICO DEL CUERPO */
    .block-container {{
        padding-top: 80px !important; /* Espacio reservado para la barra */
        padding-bottom: 2rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
    }}
    
    /* --- LA BARRA FIJA REAL (STICKY NAVBAR) --- */
    /* Apuntamos al contenedor específico donde pondremos el menú */
    div[data-testid="stVerticalBlock"] > div:has(div.st-emotion-cache-1y4p8pa) {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        z-index: 999999;
        background: {C_NAV_BG};
        border-bottom: 1px solid #E0E0E0;
        padding-top: 10px;
        padding-bottom: 5px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
    }}
    
    /* ESTILOS DE TEXTO Y BOTONES */
    h3 {{ color: {C_TXT}; font-family: 'Segoe UI', sans-serif; font-size: 1.1rem; margin-top: 0; }}
    
    /* DATA EDITOR SIN ZOOM (Hack CSS) */
    div[data-testid="stDataEditor"] table {{ font-size: 0.8rem; }}
    
</style>
""", unsafe_allow_html=True)

# --- 2. BASE DE DATOS (ROBUSTA) ---
def init_db():
    conn = sqlite3.connect('corp_v7.db')
    c = conn.cursor()
    tables = {
        'employees': ['id_emp TEXT PRIMARY KEY', 'first_name TEXT', 'last_name TEXT', 'rate REAL', 'dept TEXT'],
        'projects': ['id_proj TEXT PRIMARY KEY', 'name TEXT', 'budget REAL', 'type TEXT'],
        'tasks': ['id INTEGER PRIMARY KEY AUTOINCREMENT', 'id_proj TEXT', 'task_name TEXT', 'assigned_to TEXT', 'start_date TEXT', 'end_date TEXT', 'progress INTEGER'],
        'calendar': ['id INTEGER PRIMARY KEY AUTOINCREMENT', 'id_emp TEXT', 'date TEXT', 'type TEXT'],
        'assignments': ['id INTEGER PRIMARY KEY AUTOINCREMENT', 'id_proj TEXT', 'id_emp TEXT', 'week_start TEXT', 'percent INTEGER'],
        'timesheets': ['id INTEGER PRIMARY KEY AUTOINCREMENT', 'id_emp TEXT', 'month TEXT', 'hours REAL', 'id_proj TEXT']
    }
    for t, cols in tables.items(): c.execute(f"CREATE TABLE IF NOT EXISTS {t} ({', '.join(cols)})")
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

def get_opt(table, k, v):
    df = run_query(f"SELECT {k}, {v} FROM {table}")
    return {f"{row[v]} ({row[k]})": row[k] for i, row in df.iterrows()} if not df.empty else {}

# --- 4. NAVEGACIÓN (DENTRO DE UN CONTAINER PARA EL CSS STICKY) ---
with st.container():
    # Este contenedor es el que el CSS "atrapa" y fija arriba
    selected = sac.segmented(
        items=[
            sac.SegmentedItem(label='Employees', icon='person-lines-fill'),
            sac.SegmentedItem(label='Projects', icon='briefcase'),
            sac.SegmentedItem(label='Availability', icon='calendar-check'), # Boton 2
            sac.SegmentedItem(label='Capacity Plan', icon='grid-3x3'),
            sac.SegmentedItem(label='Finance', icon='bank'),
            sac.SegmentedItem(label='Timesheet', icon='clock'),
            sac.SegmentedItem(label='Dashboard', icon='graph-up'),
            sac.SegmentedItem(label='Admin', icon='gear'),
        ],
        label='', align='center', size='sm', radius='md', color='indigo', bg_color='transparent', use_container_width=True
    )

# --- 5. PÁGINAS ---

# A. EMPLOYEES
if selected == "Employees":
    c1, c2 = st.columns([1, 3])
    with c1:
        with st.container(border=True):
            st.markdown("### 👤 Add Profile")
            eid = st.text_input("ID", placeholder="E.g. EMP01")
            fn = st.text_input("First Name")
            ln = st.text_input("Last Name")
            dept = st.selectbox("Department", ["Consulting", "Tech", "PMO", "Sales"])
            rate = st.number_input("Rate (€/h)", value=50.0)
            if st.button("Save", type="primary", use_container_width=True):
                if eid: 
                    run_action("INSERT OR REPLACE INTO employees VALUES (?,?,?,?,?)", (eid, fn, ln, rate, dept))
                    st.success("Saved")
                    st.rerun()
    with c2:
        st.markdown("### 👥 Staff List")
        st.dataframe(run_query("SELECT * FROM employees"), use_container_width=True, hide_index=True)

# B. PROJECTS
elif selected == "Projects":
    t1, t2 = st.tabs(["Setup", "Gantt"])
    with t1:
        c1, c2 = st.columns([1, 3])
        with c1:
            with st.container(border=True):
                st.markdown("### 📁 New Project")
                pid = st.text_input("Code")
                pnm = st.text_input("Name")
                bg = st.number_input("Budget", step=1000.0)
                tp = st.selectbox("Type", ["OPEX", "CAPEX"])
                if st.button("Create", type="primary", use_container_width=True):
                    run_action("INSERT OR REPLACE INTO projects VALUES (?,?,?,?)", (pid, pnm, bg, tp))
                    st.rerun()
        with c2:
            st.dataframe(run_query("SELECT * FROM projects"), use_container_width=True, hide_index=True)
    
    with t2:
        p_map = get_opt("projects", "id_proj", "name")
        if p_map:
            sel_p_lbl = st.selectbox("Select Project", list(p_map.keys()))
            pid = p_map[sel_p_lbl]
            
            with st.expander("➕ Add Task", expanded=False):
                with st.form("gantt"):
                    c1, c2, c3, c4, c5 = st.columns([3,2,2,2,1])
                    tn = c1.text_input("Task")
                    e_map = get_opt("employees", "id_emp", "first_name")
                    asn = c2.selectbox("Who", list(e_map.keys()) if e_map else ["-"])
                    d1 = c3.date_input("Start")
                    d2 = c4.date_input("End")
                    pg = c5.number_input("%", 0, 100, 0)
                    if st.form_submit_button("Add"):
                        aid = e_map[asn] if e_map else ""
                        run_action("INSERT INTO tasks (id_proj, task_name, assigned_to, start_date, end_date, progress) VALUES (?,?,?,?,?,?)",
                                   (pid, tn, aid, str(d1), str(d2), pg))
                        st.rerun()
            
            df_t = run_query("SELECT * FROM tasks WHERE id_proj=?", (pid,))
            if not df_t.empty:
                fig = px.timeline(df_t, x_start="start_date", x_end="end_date", y="task_name", color="progress", 
                                  color_continuous_scale="Blues", title="")
                fig.update_yaxes(autorange="reversed")
                fig.update_layout(height=300, margin=dict(t=10,b=10), paper_bgcolor='white', plot_bgcolor='white')
                st.plotly_chart(fig, use_container_width=True)

# C. AVAILABILITY (EL CALENDARIO DE CÍRCULOS)
elif selected == "Availability":
    c_ctrl, c_cal = st.columns([1, 4])
    e_map = get_opt("employees", "id_emp", "first_name")
    
    if e_map:
        with c_ctrl:
            st.markdown("### Resource")
            sel_e_lbl = st.selectbox("Select", list(e_map.keys()))
            eid = e_map[sel_e_lbl]
            
            st.markdown("---")
            st.markdown("**Set Status:**")
            with st.form("status_upd"):
                dr = st.date_input("Date Range", value=[])
                stt = st.radio("Type", ["Working (Green)", "Vacation (Blue)", "Holiday (Grey)"])
                if st.form_submit_button("Apply Change", type="primary"):
                    if isinstance(dr, tuple) and len(dr)==2:
                        s, e = dr
                        while s <= e:
                            if "Working" in stt: run_action("DELETE FROM calendar WHERE id_emp=? AND date=?", (eid, str(s)))
                            else: 
                                code = "V" if "Vacation" in stt else "H"
                                run_action("INSERT OR REPLACE INTO calendar (id_emp, date, type) VALUES (?,?,?)", (eid, str(s), code))
                            s += timedelta(days=1)
                        st.rerun()

        with c_cal:
            # --- LOGICA DE VISUALIZACION DE CIRCULOS ---
            st.markdown(f"### 📅 Calendar: {sel_e_lbl}")
            
            # Datos
            yr = datetime.now().year
            df_ex = run_query("SELECT date, type FROM calendar WHERE id_emp=?", (eid,))
            ex_dict = dict(zip(df_ex['date'], df_ex['type'])) if not df_ex.empty else {}
            
            # Generar 12 Meses
            fig = go.Figure()
            
            # Coordenadas para subplots manuales (4 columnas x 3 filas)
            # Usamos Scatter plots para dibujar los circulos
            months = list(range(1, 13))
            cols_pos = [0, 1, 2, 3] * 3
            rows_pos = [2, 2, 2, 2, 1, 1, 1, 1, 0, 0, 0, 0] # Invertido para que Enero esté arriba
            
            for idx, m in enumerate(months):
                # Calcular dias del mes
                cal = cal_module.monthcalendar(yr, m)
                x_vals = [] # Dia de la semana (0-6)
                y_vals = [] # Semana del mes (0-5)
                colors = [] # Color
                hover = []
                
                # Offset para posicionar el mes en la grilla grande
                x_offset = cols_pos[idx] * 8 # Espacio horizontal entre meses
                y_offset = rows_pos[idx] * 8 # Espacio vertical
                
                # Titulo del mes (truco: punto invisible con texto)
                fig.add_trace(go.Scatter(
                    x=[x_offset + 3.5], y=[y_offset + 6.5],
                    text=[cal_module.month_name[m]], mode="text",
                    textfont=dict(size=12, color="#2C3E50", family="Arial Black"),
                    hoverinfo="skip"
                ))

                # Dias
                for week_idx, week in enumerate(cal):
                    for day_idx, day in enumerate(week):
                        if day != 0:
                            # Logica de Color
                            d_str = f"{yr}-{m:02d}-{day:02d}"
                            is_weekend = day_idx >= 5
                            
                            c = "rgba(0,0,0,0)" # Transparente por defecto
                            line_c = "rgba(0,0,0,0)"
                            
                            if d_str in ex_dict:
                                if ex_dict[d_str] == 'V': c = C_VAC
                                else: c = C_HOL
                            elif not is_weekend:
                                c = C_WORK # Verde Circulo
                            
                            # Solo pintamos si no es fin de semana o si tiene excepcion
                            if c != "rgba(0,0,0,0)" or is_weekend == False:
                                x_vals.append(x_offset + day_idx)
                                y_vals.append(y_offset + (5 - week_idx)) # Invertir Y
                                colors.append(c)
                                hover.append(f"{day}/{m}")

                fig.add_trace(go.Scatter(
                    x=x_vals, y=y_vals, mode='markers+text',
                    marker=dict(size=14, color=colors, line=dict(width=0)),
                    text=[h.split('/')[0] for h in hover], # Numero del dia
                    textfont=dict(size=8, color="white"),
                    hoverinfo='text', hovertext=hover
                ))

            fig.update_layout(
                showlegend=False,
                width=1000, height=700,
                xaxis=dict(visible=False, range=[-1, 32]),
                yaxis=dict(visible=False, range=[-1, 24]),
                margin=dict(l=0,r=0,t=0,b=0),
                plot_bgcolor='white'
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Leyenda manual exquisita
            st.caption(f"🟢 Working ({C_WORK}) | 🔵 Vacation ({C_VAC}) | ⚫ Holiday ({C_HOL}) | Weekends hidden")

# D. CAPACITY PLAN
elif selected == "Capacity Plan":
    st.markdown("### 🔢 Capacity Matrix")
    
    # 12 Semanas
    start_w = datetime.now() - timedelta(days=datetime.now().weekday())
    weeks_col = [(start_w + timedelta(weeks=i)).strftime('%Y-%m-%d') for i in range(12)]
    weeks_lbl = [(start_w + timedelta(weeks=i)).strftime('%d-%b') for i in range(12)]
    
    # Datos
    df_e = run_query("SELECT id_emp, first_name FROM employees")
    df_p = run_query("SELECT id_proj, name FROM projects")
    
    if not df_e.empty and not df_p.empty:
        # Estructura Base
        idx = pd.MultiIndex.from_product([df_e['id_emp'], df_p['id_proj']], names=['eid','pid'])
        df_base = pd.DataFrame(index=idx).reset_index()
        
        # Mapeo visual
        e_d = dict(zip(df_e['id_emp'], df_e['first_name']))
        p_d = dict(zip(df_p['id_proj'], df_p['name']))
        df_base['Resource'] = df_base['eid'].map(e_d)
        df_base['Project'] = df_base['pid'].map(p_d)
        
        # Valores
        vals = run_query("SELECT * FROM assignments")
        if not vals.empty:
            piv = vals.pivot(index=['id_emp','id_proj'], columns='week_start', values='percent').reset_index()
            df_fin = pd.merge(df_base, piv, left_on=['eid','pid'], right_on=['id_emp','id_proj'], how='left')
        else: df_fin = df_base
        
        # Columnas finales
        for w in weeks_col: 
            if w not in df_fin.columns: df_fin[w] = 0
            
        cols = ['Resource','Project'] + weeks_col
        df_show = df_fin[cols].fillna(0)
        df_show.rename(columns=dict(zip(weeks_col, weeks_lbl)), inplace=True)
        
        # Configuración NO ZOOM
        cfg = {"Resource": st.column_config.TextColumn(disabled=True), "Project": st.column_config.TextColumn(disabled=True)}
        for w in weeks_lbl: cfg[w] = st.column_config.NumberColumn(step=10)
        
        ed = st.data_editor(df_show, hide_index=True, use_container_width=True, height=600, column_config=cfg)
        
        if st.button("💾 Update Plan", type="primary"):
            saved = ed.rename(columns=dict(zip(weeks_lbl, weeks_col)))
            saved['id_emp'] = saved['Resource'].map({v:k for k,v in e_d.items()})
            saved['id_proj'] = saved['Project'].map({v:k for k,v in p_d.items()})
            
            melt = saved.melt(id_vars=['id_emp','id_proj'], value_vars=weeks_col, var_name='wk', value_name='pct')
            melt = melt[melt['pct']>0]
            
            for _, r in melt.iterrows():
                run_action("INSERT OR REPLACE INTO assignments (id_proj, id_emp, week_start, percent) VALUES (?,?,?,?)",
                           (r['id_proj'], r['id_emp'], r['wk'], r['pct']))
            st.success("Updated")

# E. FINANCE
elif selected == "Finance":
    st.markdown("### 💶 Financial Overview")
    df = run_query("""
        SELECT p.name, p.budget, COALESCE(SUM(t.hours * e.rate), 0) as consumed 
        FROM projects p LEFT JOIN timesheets t ON p.id_proj=t.id_proj LEFT JOIN employees e ON t.id_emp=e.id_emp 
        GROUP BY p.name""")
    df['margin'] = df['budget'] - df['consumed']
    
    c1, c2 = st.columns(2)
    c1.dataframe(df.style.format("€{:,.0f}"), use_container_width=True)
    fig = px.bar(df, x='name', y=['consumed','margin'], barmode='stack', color_discrete_sequence=['#2980B9', '#ECF0F1'])
    fig.update_layout(plot_bgcolor='white')
    c2.plotly_chart(fig, use_container_width=True)

# F. TIMESHEET
elif selected == "Timesheet":
    st.markdown("### ⏱️ Log Hours")
    c1, c2, c3 = st.columns(3)
    mo = c1.selectbox("Month", ["2024-01","2024-02","2024-03"])
    emp_map = get_opt("employees", "id_emp", "first_name")
    if emp_map:
        sel_e = c2.selectbox("Employee", list(emp_map.keys()))
        eid = emp_map[sel_e]
        
        prjs = run_query("SELECT id_proj, name FROM projects")
        ex = run_query("SELECT id_proj, hours FROM timesheets WHERE id_emp=? AND month=?", (eid, mo))
        
        dat = []
        for _, row in prjs.iterrows():
            h = ex[ex['id_proj']==row['id_proj']]['hours'].sum() if not ex.empty else 0.0
            dat.append({"Project": row['name'], "PID": row['id_proj'], "Hours": h})
        
        edited = st.data_editor(pd.DataFrame(dat), hide_index=True, use_container_width=True, column_config={"PID": None})
        if st.button("Save", type="primary"):
            for _, r in edited.iterrows():
                run_action("DELETE FROM timesheets WHERE id_emp=? AND month=? AND id_proj=?", (eid, mo, r['PID']))
                if r['Hours'] > 0: run_action("INSERT INTO timesheets (id_emp, month, id_proj, hours) VALUES (?,?,?,?)", (eid, mo, r['PID'], r['Hours']))
            st.success("Saved")

# G. DASHBOARD
elif selected == "Dashboard":
    k1, k2, k3 = st.columns(3)
    k1.metric("Active Projects", len(run_query("SELECT * FROM projects")))
    tot_h = run_query("SELECT SUM(hours) as h FROM timesheets")['h'].iloc[0]
    k2.metric("Total Hours", f"{tot_h:.0f}" if tot_h else "0")
    bud = run_query("SELECT SUM(budget) as b FROM projects")['b'].iloc[0]
    k3.metric("Budget Managed", f"€{bud:,.0f}" if bud else "0")
    
    g1, g2 = st.columns(2)
    df_h = run_query("SELECT p.name, SUM(t.hours) as h FROM timesheets t JOIN projects p ON t.id_proj=p.id_proj GROUP BY p.name")
    if not df_h.empty: g1.plotly_chart(px.pie(df_h, values='h', names='name', hole=0.6, color_discrete_sequence=px.colors.sequential.Blues_r), use_container_width=True)

# H. ADMIN
elif selected == "Admin":
    if st.button("📥 Backup JSON"):
        d = {t: run_query(f"SELECT * FROM {t}").to_dict(orient='records') for t in ['employees','projects','tasks','calendar','assignments','timesheets']}
        st.download_button("Download", json.dumps(d), "backup.json")
    up = st.file_uploader("📤 Restore JSON")
    if up and st.button("Restore"):
        for t, r in json.load(up).items(): pd.DataFrame(r).to_sql(t, conn, if_exists='append', index=False)
        st.success("Restored")