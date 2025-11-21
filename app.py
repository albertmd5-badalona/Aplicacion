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

# --- 1. CONFIGURACIÓN & CSS "NUCLEAR STICKY" ---
st.set_page_config(page_title="CorpApp v8", layout="wide", initial_sidebar_state="collapsed")

# PALETA DE COLORES CORPORATIVA AZUL
C_NAV_BG = "#FFFFFF"
C_TXT = "#2C3E50"     # Azul Navy
C_ACCENT = "#3498DB"  # Azul Corporativo
C_WORK = "#27AE60"    # Verde
C_VAC = "#3498DB"     # Azul
C_HOL = "#95A5A6"     # Gris

st.markdown(f"""
<style>
    /* 1. OCULTAR LA CABECERA NATIVA DE STREAMLIT Y EL FOOTER */
    header[data-testid="stHeader"] {{ display: none !important; }}
    footer {{ display: none !important; }}
    #MainMenu {{ display: none !important; }}

    /* 2. EMPUJAR EL CONTENIDO HACIA ABAJO PARA QUE NO QUEDE TAPADO */
    .block-container {{
        padding-top: 80px !important; /* Espacio reservado para tu barra */
        padding-bottom: 2rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
    }}

    /* 3. LA BARRA FIJA (SOLUCIÓN DEFINITIVA) */
    /* Creamos un contenedor flotante que ignora el scroll */
    .sticky-nav-container {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw; /* Ancho total de la ventana */
        height: 70px;
        background-color: {C_NAV_BG};
        z-index: 9999999; /* Capa superior absoluta */
        border-bottom: 1px solid #dce4ec;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
        display: flex;
        align-items: center;
        justify-content: center;
        padding-top: 10px;
    }}

    /* AJUSTES VISUALES */
    h3 {{ color: {C_TXT}; font-family: 'Helvetica Neue', sans-serif; margin-top: 0; }}
    .stButton button {{ border-radius: 5px; }}
    
    /* HACK PARA QUE EL CALENDARIO NO SE VEA GIGANTE */
    .js-plotly-plot {{ height: auto !important; }}
    
</style>
""", unsafe_allow_html=True)

# --- 2. BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect('corp_v8.db')
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

# --- 4. RENDERIZADO DE LA BARRA FIJA ---
# Usamos un contenedor st.markdown para inyectar el DIV fijo, y dentro metemos el menú.
# TRUCO: Como Streamlit procesa en orden, primero inyectamos el div apertura, luego el menu, luego el cierre.

st.markdown('<div class="sticky-nav-container">', unsafe_allow_html=True)
# NOTA: El componente SAC se renderiza donde le toca. Para que "entre" visualmente en la barra, 
# confiamos en que el CSS sticky-nav-container está posicionado encima. 
# Pero SAC crea su propio iframe. El truco visual es el siguiente:
with st.container():
    selected = sac.segmented(
        items=[
            sac.SegmentedItem(label='Employees', icon='person-vcard'),
            sac.SegmentedItem(label='Projects', icon='briefcase'),
            sac.SegmentedItem(label='Availability', icon='calendar-week'),
            sac.SegmentedItem(label='Capacity Plan', icon='grid-3x3'),
            sac.SegmentedItem(label='Finance', icon='cash-coin'),
            sac.SegmentedItem(label='Timesheet', icon='clock'),
            sac.SegmentedItem(label='Dashboard', icon='bar-chart-line'),
            sac.SegmentedItem(label='Admin', icon='gear'),
        ],
        label='', align='center', size='sm', radius='md', color='indigo', bg_color='transparent', use_container_width=False
    )
st.markdown('</div>', unsafe_allow_html=True)


# --- 5. LÓGICA DE PÁGINAS ---

# A. EMPLOYEES
if selected == "Employees":
    c1, c2 = st.columns([1, 3])
    with c1:
        st.markdown("### 👤 New Profile")
        with st.container(border=True):
            eid = st.text_input("ID", placeholder="E.g. EMP001")
            fn = st.text_input("Name")
            ln = st.text_input("Surname")
            dept = st.selectbox("Department", ["Consulting", "Engineering", "Sales", "HR"])
            rate = st.number_input("Rate (€/h)", value=45.0)
            if st.button("Save Employee", type="primary", use_container_width=True):
                if eid:
                    run_action("INSERT OR REPLACE INTO employees VALUES (?,?,?,?,?)", (eid, fn, ln, rate, dept))
                    st.success("Saved successfully")
                    st.rerun()
    with c2:
        st.markdown("### 👥 Staff Directory")
        st.dataframe(run_query("SELECT * FROM employees"), use_container_width=True, hide_index=True)

# B. PROJECTS
elif selected == "Projects":
    t1, t2 = st.tabs(["Project Setup", "Gantt View"])
    with t1:
        c1, c2 = st.columns([1, 3])
        with c1:
            st.markdown("### 📁 Create Project")
            with st.container(border=True):
                pid = st.text_input("Code", placeholder="PRJ-2024-X")
                pnm = st.text_input("Project Name")
                bg = st.number_input("Budget (€)", step=1000.0)
                tp = st.selectbox("Type", ["OPEX", "CAPEX"])
                if st.button("Save Project", type="primary", use_container_width=True):
                    run_action("INSERT OR REPLACE INTO projects VALUES (?,?,?,?)", (pid, pnm, bg, tp))
                    st.rerun()
        with c2:
            st.dataframe(run_query("SELECT * FROM projects"), use_container_width=True, hide_index=True)
    
    with t2:
        st.markdown("### 📅 Interactive Gantt")
        p_map = get_opt("projects", "id_proj", "name")
        if p_map:
            c_sel, c_form = st.columns([1, 3])
            curr_p_lbl = c_sel.selectbox("Select Project", list(p_map.keys()))
            pid = p_map[curr_p_lbl]
            
            with c_form.expander("➕ Add New Task", expanded=False):
                with st.form("add_task_gantt"):
                    c1, c2, c3, c4, c5 = st.columns([3,2,2,2,1])
                    tn = c1.text_input("Task Name")
                    e_map = get_opt("employees", "id_emp", "first_name")
                    asignee = c2.selectbox("Assignee", list(e_map.keys()) if e_map else ["Unassigned"])
                    d1 = c3.date_input("Start")
                    d2 = c4.date_input("End")
                    pg = c5.number_input("%", 0, 100, 0)
                    if st.form_submit_button("Add"):
                        aid = e_map[asignee] if e_map else ""
                        run_action("INSERT INTO tasks (id_proj, task_name, assigned_to, start_date, end_date, progress) VALUES (?,?,?,?,?,?)",
                                   (pid, tn, aid, str(d1), str(d2), pg))
                        st.rerun()
            
            df_t = run_query("SELECT * FROM tasks WHERE id_proj=?", (pid,))
            if not df_t.empty:
                fig = px.timeline(df_t, x_start="start_date", x_end="end_date", y="task_name", color="progress",
                                  color_continuous_scale="Blues", height=300)
                fig.update_yaxes(autorange="reversed")
                fig.update_layout(margin=dict(t=10,b=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No tasks scheduled.")

# C. AVAILABILITY (CIRCULOS Y CALENDARIO COMPACTO)
elif selected == "Availability":
    c_ctrl, c_cal = st.columns([1, 3])
    e_map = get_opt("employees", "id_emp", "first_name")
    
    if e_map:
        with c_ctrl:
            st.markdown("### Resource")
            sel_e = st.selectbox("Select Employee", list(e_map.keys()))
            eid = e_map[sel_e]
            
            st.markdown("---")
            st.caption("Update Availability")
            with st.form("cal_upd"):
                dr = st.date_input("Dates", value=[])
                stt = st.radio("Status", ["Working (Clear)", "Vacation (Blue)", "Holiday (Grey)"])
                if st.form_submit_button("Apply"):
                    if isinstance(dr, tuple) and len(dr)==2:
                        s,e = dr
                        while s<=e:
                            if "Working" in stt: run_action("DELETE FROM calendar WHERE id_emp=? AND date=?", (eid, str(s)))
                            else: 
                                code = "V" if "Vacation" in stt else "H"
                                run_action("INSERT OR REPLACE INTO calendar (id_emp, date, type) VALUES (?,?,?)", (eid, str(s), code))
                            s += timedelta(days=1)
                        st.rerun()
        
        with c_cal:
            st.markdown(f"### 🗓️ Calendar: {sel_e}")
            yr = datetime.now().year
            df_ex = run_query("SELECT date, type FROM calendar WHERE id_emp=?", (eid,))
            ex_dict = dict(zip(df_ex['date'], df_ex['type'])) if not df_ex.empty else {}
            
            # VISUALIZACIÓN DE PUNTOS (SCATTER)
            fig = go.Figure()
            months = list(range(1, 13))
            # Layout 4x3
            cols_pos = [0,1,2,3] * 3
            rows_pos = [2,2,2,2, 1,1,1,1, 0,0,0,0]
            
            for idx, m in enumerate(months):
                cal = cal_module.monthcalendar(yr, m)
                x_off = cols_pos[idx] * 8
                y_off = rows_pos[idx] * 8
                
                # Etiqueta Mes
                fig.add_trace(go.Scatter(x=[x_off+3.5], y=[y_off+6.5], text=[cal_module.month_abbr[m]], mode="text", textfont=dict(color=C_TXT, size=10, weight='bold'), hoverinfo='skip'))
                
                for w_idx, week in enumerate(cal):
                    for d_idx, day in enumerate(week):
                        if day != 0:
                            d_str = f"{yr}-{m:02d}-{day:02d}"
                            is_we = d_idx >= 5
                            color = 'rgba(0,0,0,0)'
                            
                            if d_str in ex_dict:
                                color = C_VAC if ex_dict[d_str]=='V' else C_HOL
                            elif not is_we:
                                color = C_WORK # Verde por defecto laborable
                            
                            # Pintar solo si tiene color (es decir, ocultamos finde si no hay excepcion)
                            if color != 'rgba(0,0,0,0)':
                                fig.add_trace(go.Scatter(
                                    x=[x_off + d_idx], 
                                    y=[y_off + (5-w_idx)],
                                    mode='markers+text',
                                    marker=dict(size=12, color=color, line=dict(width=0)),
                                    text=[str(day)], textfont=dict(color='white', size=7),
                                    hoverinfo='text', hovertext=f"{day}/{m} - {color}"
                                ))
            
            fig.update_layout(
                width=900, height=500, showlegend=False,
                xaxis=dict(visible=False, range=[-1, 32]),
                yaxis=dict(visible=False, range=[-1, 24]),
                margin=dict(l=0,r=0,t=0,b=0), plot_bgcolor='white'
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Leyenda: 🟢 Laborable | 🔵 Vacaciones | ⚫ Festivo")

# D. CAPACITY PLAN (EXCEL STYLE)
elif selected == "Capacity Plan":
    st.markdown("### 🔢 Capacity Planning Matrix")
    start_w = datetime.now() - timedelta(days=datetime.now().weekday())
    weeks = [(start_w+timedelta(weeks=i)) for i in range(12)]
    cols_sql = [w.strftime('%Y-%m-%d') for w in weeks]
    cols_lbl = [w.strftime('%d-%b') for w in weeks]
    
    df_e = run_query("SELECT id_emp, first_name FROM employees")
    df_p = run_query("SELECT id_proj, name FROM projects")
    
    if not df_e.empty and not df_p.empty:
        # Generar Matriz
        idx = pd.MultiIndex.from_product([df_e['id_emp'], df_p['id_proj']], names=['eid','pid']).to_frame(index=False)
        idx['Resource'] = idx['eid'].map(dict(zip(df_e['id_emp'], df_e['first_name'])))
        idx['Project'] = idx['pid'].map(dict(zip(df_p['id_proj'], df_p['name'])))
        
        vals = run_query("SELECT * FROM assignments")
        if not vals.empty:
            piv = vals.pivot(index=['id_emp','id_proj'], columns='week_start', values='percent').reset_index()
            df_full = pd.merge(idx, piv, left_on=['eid','pid'], right_on=['id_emp','id_proj'], how='left')
        else:
            df_full = idx
        
        for c in cols_sql: 
            if c not in df_full.columns: df_full[c] = 0
            
        df_show = df_full[['Resource','Project'] + cols_sql].fillna(0)
        df_show.rename(columns=dict(zip(cols_sql, cols_lbl)), inplace=True)
        
        # CONFIGURACION SIN ZOOM (NumberColumn)
        cfg = {"Resource": st.column_config.TextColumn(disabled=True), "Project": st.column_config.TextColumn(disabled=True)}
        for c in cols_lbl: cfg[c] = st.column_config.NumberColumn(min_value=0, max_value=100, step=10)
        
        edited = st.data_editor(df_show, hide_index=True, use_container_width=True, height=600, column_config=cfg)
        
        if st.button("💾 Update Matrix", type="primary"):
            save = edited.rename(columns=dict(zip(cols_lbl, cols_sql)))
            # Recuperar IDs
            e_map = dict(zip(df_e['first_name'], df_e['id_emp']))
            p_map = dict(zip(df_p['name'], df_p['id_proj']))
            save['eid'] = save['Resource'].map(e_map)
            save['pid'] = save['Project'].map(p_map)
            
            melted = save.melt(id_vars=['eid','pid'], value_vars=cols_sql, var_name='wk', value_name='pct')
            melted = melted[melted['pct'] > 0]
            
            for _, r in melted.iterrows():
                run_action("INSERT OR REPLACE INTO assignments (id_proj, id_emp, week_start, percent) VALUES (?,?,?,?)",
                           (r['pid'], r['eid'], r['wk'], r['pct']))
            st.success("Plan Updated")

# E. FINANCE
elif selected == "Finance":
    st.markdown("### 💶 Financial Control")
    df = run_query("""
        SELECT p.name, p.budget, COALESCE(SUM(t.hours*e.rate),0) as actual 
        FROM projects p LEFT JOIN timesheets t ON p.id_proj=t.id_proj 
        LEFT JOIN employees e ON t.id_emp=e.id_emp GROUP BY p.name
    """)
    df['margin'] = df['budget'] - df['actual']
    c1, c2 = st.columns(2)
    c1.dataframe(df.style.format("€{:,.0f}"), use_container_width=True)
    c2.plotly_chart(px.bar(df, x='name', y=['actual','margin'], barmode='stack', color_discrete_sequence=[C_ACCENT, '#ECF0F1']), use_container_width=True)

# F. TIMESHEET
elif selected == "Timesheet":
    st.markdown("### ⏱️ Monthly Hours")
    c1,c2,c3 = st.columns(3)
    mo = c1.selectbox("Month", ["2024-01","2024-02","2024-03"])
    e_map = get_opt("employees", "id_emp", "first_name")
    if e_map:
        sel_e = c2.selectbox("Employee", list(e_map.keys()))
        eid = e_map[sel_e]
        p_df = run_query("SELECT id_proj, name FROM projects")
        ts = run_query("SELECT id_proj, hours FROM timesheets WHERE id_emp=? AND month=?", (eid,mo))
        
        dat = []
        for _,r in p_df.iterrows():
            h = ts[ts['id_proj']==r['id_proj']]['hours'].sum() if not ts.empty else 0.0
            dat.append({"Project":r['name'], "PID":r['id_proj'], "Hours":h})
        
        ed = st.data_editor(pd.DataFrame(dat), hide_index=True, use_container_width=True, column_config={"PID":None})
        if st.button("Save Hours", type="primary"):
            for _,r in ed.iterrows():
                run_action("DELETE FROM timesheets WHERE id_emp=? AND month=? AND id_proj=?", (eid,mo,r['PID']))
                if r['Hours']>0: run_action("INSERT INTO timesheets (id_emp,month,id_proj,hours) VALUES (?,?,?,?)",(eid,mo,r['PID'],r['Hours']))
            st.success("Saved")

# G. DASHBOARD
elif selected == "Dashboard":
    k1,k2,k3 = st.columns(3)
    k1.metric("Total Projects", len(run_query("SELECT * FROM projects")))
    h_tot = run_query("SELECT SUM(hours) as h FROM timesheets")['h'].iloc[0]
    k2.metric("Hours Logged", f"{h_tot:.0f}" if h_tot else "0")
    b_tot = run_query("SELECT SUM(budget) as b FROM projects")['b'].iloc[0]
    k3.metric("Portfolio Value", f"€{b_tot:,.0f}" if b_tot else "0")
    
    g1,g2 = st.columns(2)
    df_pie = run_query("SELECT p.name, SUM(t.hours) as h FROM timesheets t JOIN projects p ON t.id_proj=p.id_proj GROUP BY p.name")
    if not df_pie.empty: g1.plotly_chart(px.pie(df_pie, values='h', names='name', hole=0.6), use_container_width=True)

# H. ADMIN
elif selected == "Admin":
    if st.button("📥 Backup"):
        d = {t: run_query(f"SELECT * FROM {t}").to_dict(orient='records') for t in ['employees','projects','tasks','calendar','assignments','timesheets']}
        st.download_button("Download JSON", json.dumps(d), "backup.json")
    up = st.file_uploader("📤 Restore")
    if up and st.button("Restore"):
        for t,r in json.load(up).items(): pd.DataFrame(r).to_sql(t, conn, if_exists='append', index=False)
        st.success("Restored")