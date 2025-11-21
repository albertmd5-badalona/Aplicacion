import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime, timedelta
import io

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Gestor de Proyectos & Recursos", layout="wide")

# --- GESTIÓN DE BASE DE DATOS (SQLite) ---
def init_db():
    conn = sqlite3.connect('gestor_recursos.db')
    c = conn.cursor()
    
    # 1. Empleados
    c.execute('''CREATE TABLE IF NOT EXISTS empleados (
        id_empleado TEXT PRIMARY KEY, nombre TEXT, apellido TEXT, mail TEXT, 
        tipo TEXT, tarifa REAL, manager TEXT, resource_manager TEXT)''')
    
    # 2. Proyectos
    c.execute('''CREATE TABLE IF NOT EXISTS proyectos (
        id_proyecto TEXT PRIMARY KEY, nombre TEXT, plataforma TEXT, producto TEXT,
        tipo_gasto TEXT, budget REAL)''')
        
    # 2.2 Tareas (Gantt)
    c.execute('''CREATE TABLE IF NOT EXISTS tareas (
        id INTEGER PRIMARY KEY AUTOINCREMENT, id_proyecto TEXT, nombre_tarea TEXT,
        asignado_a TEXT, fecha_inicio TEXT, fecha_fin TEXT, avance INTEGER)''')

    # 3. Vacaciones/Ausencias
    c.execute('''CREATE TABLE IF NOT EXISTS ausencias (
        id INTEGER PRIMARY KEY AUTOINCREMENT, id_empleado TEXT, fecha TEXT, tipo TEXT)''')

    # 4. Asignaciones
    c.execute('''CREATE TABLE IF NOT EXISTS asignaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT, id_proyecto TEXT, id_empleado TEXT,
        semana_inicio TEXT, porcentaje INTEGER)''')

    # 6. Timesheets
    c.execute('''CREATE TABLE IF NOT EXISTS timesheets (
        id INTEGER PRIMARY KEY AUTOINCREMENT, id_empleado TEXT, mes TEXT, horas REAL, id_proyecto TEXT)''')

    conn.commit()
    return conn

conn = init_db()

# --- FUNCIONES AUXILIARES ---
def run_query(query, params=()):
    try:
        df = pd.read_sql(query, conn, params=params)
        return df
    except Exception as e:
        st.error(f"Error en DB: {e}")
        return pd.DataFrame()

def run_action(query, params=()):
    c = conn.cursor()
    c.execute(query, params)
    conn.commit()

# --- INTERFAZ GRÁFICA ---

st.title("🏢 Sistema de Gestión de Proyectos y Recursos")

# Menú Lateral
menu = st.sidebar.selectbox("Navegación", [
    "1. Empleados", 
    "2. Proyectos & Gantt", 
    "3. Calendario & Disponibilidad", 
    "4. Asignaciones", 
    "5. Gestión Económica", 
    "6. Timesheets", 
    "7. Dashboards", 
    "8. Admin"
])

# --- 1. DATOS MAESTROS EMPLEADO ---
if menu == "1. Empleados":
    st.header("👥 Gestión de Empleados")
    
    with st.expander("➕ Añadir Nuevo Empleado"):
        col1, col2 = st.columns(2)
        with col1:
            eid = st.text_input("ID Empleado")
            nom = st.text_input("Nombre")
            ape = st.text_input("Apellido")
            mail = st.text_input("Email")
        with col2:
            tipo = st.selectbox("Interno/Externo", ["Interno", "Externo"])
            tarifa = st.number_input("Tarifa Hora (€)", min_value=0.0)
            mgr = st.text_input("Manager")
            res_mgr = st.text_input("Resource Manager")
        
        if st.button("Guardar Empleado"):
            try:
                run_action("INSERT INTO empleados VALUES (?,?,?,?,?,?,?,?)", 
                           (eid, nom, ape, mail, tipo, tarifa, mgr, res_mgr))
                st.success("Empleado añadido")
            except:
                st.error("Error: ID duplicado o datos inválidos")

    st.subheader("Listado de Empleados")
    df_emp = run_query("SELECT * FROM empleados")
    st.dataframe(df_emp, use_container_width=True)
    
    # Borrado simple
    del_id = st.text_input("ID Empleado a eliminar")
    if st.button("Eliminar Empleado"):
        run_action("DELETE FROM empleados WHERE id_empleado = ?", (del_id,))
        st.rerun()

# --- 2. PROYECTOS & GANTT ---
elif menu == "2. Proyectos & Gantt":
    st.header("🚀 Gestión de Proyectos")
    
    tab1, tab2 = st.tabs(["Alta Proyectos", "Gantt & Tareas"])
    
    with tab1:
        with st.expander("➕ Crear Proyecto"):
            pid = st.text_input("ID Proyecto")
            pnom = st.text_input("Nombre Proyecto")
            plat = st.text_input("Plataforma")
            prod = st.text_input("Producto")
            tipo_g = st.selectbox("CAPEX/OPEX", ["CAPEX", "OPEX"])
            bud = st.number_input("Budget Total (€)", min_value=0.0)
            
            if st.button("Crear Proyecto"):
                try:
                    run_action("INSERT INTO proyectos VALUES (?,?,?,?,?,?)", 
                               (pid, pnom, plat, prod, tipo_g, bud))
                    st.success("Proyecto Creado")
                except:
                    st.error("ID duplicado")
        
        st.dataframe(run_query("SELECT * FROM proyectos"), use_container_width=True)

    with tab2:
        lista_proyectos = run_query("SELECT id_proyecto FROM proyectos")
        if not lista_proyectos.empty:
            proj_sel = st.selectbox("Selecciona Proyecto para Gantt", lista_proyectos['id_proyecto'])
            
            # Añadir Tarea
            with st.form("add_task"):
                tnom = st.text_input("Nombre Tarea")
                tasig = st.selectbox("Asignado a", run_query("SELECT id_empleado FROM empleados")['id_empleado'])
                tini = st.date_input("Inicio")
                tfin = st.date_input("Fin")
                tprog = st.slider("% Avance", 0, 100, 0)
                if st.form_submit_button("Añadir Tarea"):
                    run_action("INSERT INTO tareas (id_proyecto, nombre_tarea, asignado_a, fecha_inicio, fecha_fin, avance) VALUES (?,?,?,?,?,?)",
                               (proj_sel, tnom, tasig, str(tini), str(tfin), tprog))
                    st.rerun()
            
            # Visualizar Gantt
            df_tasks = run_query("SELECT * FROM tareas WHERE id_proyecto = ?", (proj_sel,))
            if not df_tasks.empty:
                fig = px.timeline(df_tasks, x_start="fecha_inicio", x_end="fecha_fin", y="nombre_tarea", color="avance", hover_data=["asignado_a"])
                fig.update_yaxes(autorange="reversed")
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(df_tasks)
            else:
                st.info("No hay tareas en este proyecto.")
        else:
            st.warning("Crea un proyecto primero.")

# --- 3. CALENDARIO ---
elif menu == "3. Calendario & Disponibilidad":
    st.header("📅 Calendario de Ausencias")
    col1, col2 = st.columns(2)
    with col1:
        emp_cal = st.selectbox("Empleado", run_query("SELECT id_empleado FROM empleados")['id_empleado'])
        fecha_aus = st.date_input("Fecha")
        tipo_aus = st.selectbox("Tipo", ["Vacaciones", "Festivo", "Baja"])
        if st.button("Registrar Ausencia"):
            run_action("INSERT INTO ausencias (id_empleado, fecha, tipo) VALUES (?,?,?)", (emp_cal, str(fecha_aus), tipo_aus))
            st.success("Registrado")
    
    with col2:
        st.subheader("Ausencias Registradas")
        st.dataframe(run_query("SELECT * FROM ausencias ORDER BY fecha DESC"))

# --- 4. ASIGNACIONES ---
elif menu == "4. Asignaciones":
    st.header("📌 Asignación de Recursos")
    
    col1, col2 = st.columns(2)
    with col1:
        a_proj = st.selectbox("Proyecto", run_query("SELECT id_proyecto FROM proyectos")['id_proyecto'])
        a_emp = st.selectbox("Recurso", run_query("SELECT id_empleado FROM empleados")['id_empleado'])
    with col2:
        a_sem = st.date_input("Inicio Semana (Lunes)")
        a_pct = st.number_input("% Asignación", min_value=0, max_value=100, value=100)
    
    if st.button("Asignar"):
        run_action("INSERT INTO asignaciones (id_proyecto, id_empleado, semana_inicio, porcentaje) VALUES (?,?,?,?)",
                   (a_proj, a_emp, str(a_sem), a_pct))
        st.success("Asignación guardada")
    
    st.dataframe(run_query("SELECT * FROM asignaciones"), use_container_width=True)

# --- 5. GESTIÓN ECONÓMICA ---
elif menu == "5. Gestión Económica":
    st.header("💰 Control Financiero")
    
    # Lógica simple: Actual = Horas Timesheet * Tarifa. Forecast = Asignaciones futuras * Tarifa.
    
    df_fin = run_query("""
        SELECT p.id_proyecto, p.budget, 
        (SELECT SUM(t.horas * e.tarifa) 
         FROM timesheets t 
         JOIN empleados e ON t.id_empleado = e.id_empleado 
         WHERE t.id_proyecto = p.id_proyecto) as actual
        FROM proyectos p
    """)
    
    df_fin['actual'] = df_fin['actual'].fillna(0)
    df_fin['restante'] = df_fin['budget'] - df_fin['actual']
    
    st.dataframe(df_fin, use_container_width=True)
    
    if not df_fin.empty:
        fig = px.bar(df_fin, x='id_proyecto', y=['budget', 'actual'], barmode='group', title="Budget vs Actual")
        st.plotly_chart(fig)

# --- 6. TIMESHEETS ---
elif menu == "6. Timesheets":
    st.header("⏱️ Imputación de Horas")
    
    col1, col2 = st.columns(2)
    with col1:
        ts_emp = st.selectbox("Empleado", run_query("SELECT id_empleado FROM empleados")['id_empleado'])
        ts_pro = st.selectbox("Proyecto", run_query("SELECT id_proyecto FROM proyectos")['id_proyecto'])
    with col2:
        ts_mes = st.selectbox("Mes", ["2023-10", "2023-11", "2023-12", "2024-01", "2024-02"]) # Simplificado
        ts_horas = st.number_input("Horas Totales Mes", min_value=0.0)
    
    if st.button("Imputar Horas"):
        run_action("INSERT INTO timesheets (id_empleado, mes, horas, id_proyecto) VALUES (?,?,?,?)",
                   (ts_emp, ts_mes, ts_horas, ts_pro))
        st.success("Horas registradas")
        
    st.dataframe(run_query("SELECT * FROM timesheets ORDER BY id DESC"), use_container_width=True)

# --- 7. DASHBOARDS ---
elif menu == "7. Dashboards":
    st.header("📊 Informes")
    
    # KPIs
    tot_emp = run_query("SELECT count(*) as c FROM empleados")['c'].iloc[0]
    tot_proj = run_query("SELECT count(*) as c FROM proyectos")['c'].iloc[0]
    
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Total Empleados", tot_emp)
    kpi2.metric("Total Proyectos", tot_proj)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Cargabilidad (Horas imputadas por Proyecto)")
        df_load = run_query("SELECT id_proyecto, SUM(horas) as horas FROM timesheets GROUP BY id_proyecto")
        if not df_load.empty:
            fig = px.pie(df_load, values='horas', names='id_proyecto')
            st.plotly_chart(fig)
            
    with col2:
        st.subheader("Coste por Recurso")
        df_cost = run_query("""
            SELECT t.id_empleado, SUM(t.horas * e.tarifa) as coste 
            FROM timesheets t 
            JOIN empleados e ON t.id_empleado = e.id_empleado 
            GROUP BY t.id_empleado
        """)
        if not df_cost.empty:
            st.bar_chart(df_cost.set_index('id_empleado'))

# --- 8. ADMIN ---
elif menu == "8. Admin":
    st.header("🛠️ Administración")
    
    st.subheader("Exportar Datos")
    
    table_to_export = st.selectbox("Seleccionar Tabla", ["empleados", "proyectos", "timesheets", "asignaciones"])
    df_export = run_query(f"SELECT * FROM {table_to_export}")
    
    csv = df_export.to_csv(index=False).encode('utf-8')
    
    st.download_button(
        label=f"Descargar {table_to_export} como CSV",
        data=csv,
        file_name=f'{table_to_export}.csv',
        mime='text/csv',
    )
    
    st.info("Funciones de gestión de permisos y listas de valores se gestionan a nivel de código o DB en esta versión ligera.")