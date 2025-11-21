import os
import flet as ft
import sqlite3
import pandas as pd
import datetime
import calendar
import plotly.express as px
from plotly.graph_objects import Figure

# --- CONFIGURACIÓN DE COLORES (PALETA AZUL CORPORATIVA) ---
C_PRIMARY = ft.colors.INDIGO
C_SECONDARY = ft.colors.BLUE_GREY_50
C_BG = ft.colors.WHITE
C_SURFACE = ft.colors.WHITE
C_TEXT = ft.colors.SLATE_900
C_GREEN_WORK = ft.colors.GREEN_600
C_BLUE_VAC = ft.colors.BLUE_600
C_GREY_HOL = ft.colors.GREY_500

# --- BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect("app_flet.db", check_same_thread=False)
    c = conn.cursor()
    tables = {
        'employees': ['id TEXT PRIMARY KEY', 'name TEXT', 'surname TEXT', 'rate REAL', 'dept TEXT'],
        'projects': ['id TEXT PRIMARY KEY', 'name TEXT', 'budget REAL', 'type TEXT'],
        'tasks': ['id INTEGER PRIMARY KEY AUTOINCREMENT', 'proj_id TEXT', 'name TEXT', 'assignee TEXT', 'start TEXT', 'end TEXT', 'progress INT'],
        'calendar': ['id INTEGER PRIMARY KEY AUTOINCREMENT', 'emp_id TEXT', 'date TEXT', 'type TEXT'],
        'assignments': ['id INTEGER PRIMARY KEY AUTOINCREMENT', 'proj_id TEXT', 'emp_id TEXT', 'week TEXT', 'percent INT'],
        'timesheets': ['id INTEGER PRIMARY KEY AUTOINCREMENT', 'emp_id TEXT', 'month TEXT', 'hours REAL', 'proj_id TEXT']
    }
    for t, cols in tables.items():
        c.execute(f"CREATE TABLE IF NOT EXISTS {t} ({', '.join(cols)})")
    conn.commit()
    return conn

db = init_db()

# --- UTILIDADES ---
def run_query(query, params=()):
    try:
        return pd.read_sql(query, db, params=params)
    except Exception as e:
        print(f"Error DB: {e}")
        return pd.DataFrame()

def run_action(query, params=()):
    try:
        c = db.cursor()
        c.execute(query, params)
        db.commit()
        return True
    except Exception as e:
        print(f"Error Action: {e}")
        return False

# --- COMPONENTES UI REUTILIZABLES ---
def Title(text):
    return ft.Text(text, size=24, weight=ft.FontWeight.BOLD, color=C_PRIMARY)

def SubTitle(text):
    return ft.Text(text, size=16, weight=ft.FontWeight.W_500, color=ft.colors.SLATE_500)

def Card(content):
    return ft.Container(
        content=content,
        padding=20,
        border_radius=12,
        bgcolor=C_SURFACE,
        shadow=ft.BoxShadow(spread_radius=1, blur_radius=10, color=ft.colors.BLUE_GREY_100, offset=ft.Offset(0, 5))
    )

# --- VISTAS DE LA APLICACIÓN ---

def view_employees(page):
    # Formulario
    id_field = ft.TextField(label="ID", width=100, text_size=12)
    name_field = ft.TextField(label="Name", expand=True, text_size=12)
    last_field = ft.TextField(label="Surname", expand=True, text_size=12)
    dept_field = ft.Dropdown(label="Dept", options=[ft.dropdown.Option(x) for x in ["IT", "HR", "Ops"]], width=100, text_size=12)
    rate_field = ft.TextField(label="Rate €", width=80, text_size=12, keyboard_type=ft.KeyboardType.NUMBER)
    
    grid = ft.DataTable(
        columns=[ft.DataColumn(ft.Text("ID")), ft.DataColumn(ft.Text("Name")), ft.DataColumn(ft.Text("Dept")), ft.DataColumn(ft.Text("Rate"))],
        rows=[]
    )

    def load_data():
        df = run_query("SELECT * FROM employees")
        grid.rows.clear()
        for _, r in df.iterrows():
            grid.rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(r['id'])), ft.DataCell(ft.Text(f"{r['name']} {r['surname']}")),
                ft.DataCell(ft.Text(r['dept'])), ft.DataCell(ft.Text(str(r['rate'])))
            ]))
        page.update()

    def save(e):
        if id_field.value:
            run_action("INSERT OR REPLACE INTO employees VALUES (?,?,?,?,?)", 
                       (id_field.value, name_field.value, last_field.value, float(rate_field.value or 0), dept_field.value))
            load_data()
            page.snack_bar = ft.SnackBar(ft.Text("Employee Saved!"), bgcolor=ft.colors.GREEN)
            page.snack_bar.open = True
            page.update()

    load_data()
    return ft.Column([
        Title("👥 Team Management"),
        Card(ft.Row([id_field, name_field, last_field, dept_field, rate_field, 
                     ft.ElevatedButton("Save", on_click=save, bgcolor=C_PRIMARY, color="white")], wrap=True)),
        Card(grid)
    ], scroll=ft.ScrollMode.AUTO)

def view_projects(page):
    # UI Proyecto
    p_id = ft.TextField(label="Code", width=100)
    p_name = ft.TextField(label="Project Name", expand=True)
    p_bud = ft.TextField(label="Budget", width=120)
    p_type = ft.Dropdown(label="Type", width=100, options=[ft.dropdown.Option("OPEX"), ft.dropdown.Option("CAPEX")])
    
    # UI Gantt
    gantt_chart = ft.PlotlyChart(Figure(), expand=True)
    
    def load_gantt(proj_id):
        df = run_query("SELECT * FROM tasks WHERE proj_id=?", (proj_id,))
        if not df.empty:
            fig = px.timeline(df, x_start="start", x_end="end", y="name", color="progress", color_continuous_scale="Blues")
            fig.update_yaxes(autorange="reversed")
            gantt_chart.figure = fig
        else:
            gantt_chart.figure = Figure()
        page.update()

    def add_project(e):
        run_action("INSERT OR REPLACE INTO projects VALUES (?,?,?,?)", (p_id.value, p_name.value, float(p_bud.value or 0), p_type.value))
        load_projects()
    
    proj_list = ft.ListView(height=200)
    
    def load_projects():
        df = run_query("SELECT * FROM projects")
        proj_list.controls.clear()
        for _, r in df.iterrows():
            proj_list.controls.append(
                ft.ListTile(
                    leading=ft.Icon(ft.icons.FOLDER, color=C_PRIMARY),
                    title=ft.Text(f"{r['name']} ({r['id']})"),
                    subtitle=ft.Text(f"Budget: €{r['budget']}"),
                    on_click=lambda e, pid=r['id']: load_gantt(pid)
                )
            )
        page.update()

    load_projects()

    return ft.Column([
        Title("🚀 Projects & Gantt"),
        Card(ft.Row([p_id, p_name, p_bud, p_type, ft.ElevatedButton("Add", on_click=add_project, bgcolor=C_PRIMARY, color="white")])),
        ft.Row([
            ft.Container(content=proj_list, width=300, bgcolor="white", border_radius=10, padding=10),
            ft.Container(content=gantt_chart, expand=True, bgcolor="white", border_radius=10, padding=10)
        ], expand=True)
    ])

def view_calendar(page):
    # Este es el calendario visual con círculos
    current_emp = ft.Dropdown(label="Select Resource", expand=True)
    
    def generate_calendar(e=None):
        if not current_emp.value: return
        eid = current_emp.value
        
        # Limpiar vista
        cal_container.controls.clear()
        
        # Traer excepciones
        df_ex = run_query("SELECT date, type FROM calendar WHERE emp_id=?", (eid,))
        ex_map = dict(zip(df_ex['date'], df_ex['type'])) if not df_ex.empty else {}

        year = datetime.datetime.now().year
        
        # Generar 12 meses
        for month in range(1, 13):
            month_name = calendar.month_name[month]
            cal = calendar.monthcalendar(year, month)
            
            month_col = ft.Column(spacing=2)
            month_col.controls.append(ft.Text(month_name, weight=ft.FontWeight.BOLD, color=C_PRIMARY))
            
            # Grid del mes
            rows = []
            for week in cal:
                row_controls = []
                for day in week:
                    if day == 0:
                        row_controls.append(ft.Container(width=25, height=25)) # Espacio vacío
                    else:
                        d_str = f"{year}-{month:02d}-{day:02d}"
                        wd = datetime.date(year, month, day).weekday()
                        
                        # Logica visual
                        bgcolor = ft.colors.TRANSPARENT
                        content = ft.Text(str(day), size=10, color=ft.colors.GREY_400) # Finde por defecto
                        
                        is_weekend = wd >= 5
                        
                        if d_str in ex_map:
                            t = ex_map[d_str]
                            color = C_BLUE_VAC if t == 'V' else C_GREY_HOL
                            content = ft.Container(
                                content=ft.Text(str(day), size=10, color="white", text_align="center"),
                                width=25, height=25, bgcolor=color, border_radius=12.5, alignment=ft.alignment.center
                            )
                        elif not is_weekend:
                             content = ft.Container(
                                content=ft.Text(str(day), size=10, color="white", text_align="center"),
                                width=25, height=25, bgcolor=C_GREEN_WORK, border_radius=12.5, alignment=ft.alignment.center,
                                on_click=lambda e, d=d_str: toggle_date(d)
                            )
                        
                        row_controls.append(content)
                rows.append(ft.Row(row_controls, alignment="center"))
            
            cal_container.controls.append(ft.Container(
                content=ft.Column(rows), 
                padding=10, border=ft.border.all(1, ft.colors.GREY_200), border_radius=8
            ))
        page.update()

    def toggle_date(date_str):
        # Simple toggle logic: Work -> Vac -> Hol -> Work
        eid = current_emp.value
        # Chequear estado actual
        curr = run_query("SELECT type FROM calendar WHERE emp_id=? AND date=?", (eid, date_str))
        if curr.empty:
            run_action("INSERT INTO calendar (emp_id, date, type) VALUES (?,?,?)", (eid, date_str, "V"))
        elif curr.iloc[0]['type'] == 'V':
            run_action("UPDATE calendar SET type='H' WHERE emp_id=? AND date=?", (eid, date_str))
        else:
            run_action("DELETE FROM calendar WHERE emp_id=? AND date=?", (eid, date_str))
        generate_calendar()

    cal_container = ft.GridView(runs_count=4, max_extent=250, child_aspect_ratio=1.0, spacing=10, run_spacing=10, expand=True)
    
    def load_emps():
        df = run_query("SELECT id, name FROM employees")
        current_emp.options = [ft.dropdown.Option(key=r['id'], text=r['name']) for _, r in df.iterrows()]
        page.update()

    load_emps()
    current_emp.on_change = generate_calendar

    return ft.Column([
        Title("📅 Availability Calendar"),
        ft.Row([current_emp, ft.Text("Click on green circles to toggle status (Work -> Vacation -> Holiday)", size=12, color="grey")]),
        ft.Divider(),
        ft.Container(content=cal_container, expand=True)
    ], expand=True)

def view_planning(page):
    # Matriz estilo Excel
    cols = []
    rows_container = ft.Column(scroll=ft.ScrollMode.AUTO)

    # Fechas
    today = datetime.date.today()
    start_w = today - datetime.timedelta(days=today.weekday())
    weeks = [(start_w + datetime.timedelta(weeks=i)).strftime("%Y-%m-%d") for i in range(12)]
    
    def load_matrix():
        rows_container.controls.clear()
        
        # Header
        header_row = [ft.Container(width=150, content=ft.Text("Resource", weight="bold")), 
                      ft.Container(width=150, content=ft.Text("Project", weight="bold"))]
        for w in weeks:
            header_row.append(ft.Container(width=60, content=ft.Text(w[5:], size=10, weight="bold"))) # Show MM-DD
        rows_container.controls.append(ft.Row(header_row))

        # Data
        df_e = run_query("SELECT id, name FROM employees")
        df_p = run_query("SELECT id, name FROM projects")
        if df_e.empty or df_p.empty: return

        # Build grid
        for _, emp in df_e.iterrows():
            for _, proj in df_p.iterrows():
                row_ctrls = [
                    ft.Container(width=150, content=ft.Text(emp['name'], size=12)),
                    ft.Container(width=150, content=ft.Text(proj['name'], size=12))
                ]
                
                # Get existing assignments
                for w in weeks:
                    val = ""
                    exist = run_query("SELECT percent FROM assignments WHERE emp_id=? AND proj_id=? AND week=?", (emp['id'], proj['id'], w))
                    if not exist.empty: val = str(exist.iloc[0]['percent'])
                    
                    # Input Cell
                    txt = ft.TextField(value=val, width=55, height=30, text_size=11, content_padding=5, 
                                       on_blur=lambda e, ep=emp['id'], pj=proj['id'], wk=w: update_cell(ep, pj, wk, e.control.value))
                    row_ctrls.append(ft.Container(width=60, content=txt))
                
                rows_container.controls.append(ft.Row(row_ctrls))
        page.update()

    def update_cell(eid, pid, wk, val):
        if not val: return
        try:
            pct = int(val)
            # Delete old
            run_action("DELETE FROM assignments WHERE emp_id=? AND proj_id=? AND week=?", (eid, pid, wk))
            if pct > 0:
                run_action("INSERT INTO assignments (proj_id, emp_id, week, percent) VALUES (?,?,?,?)", (pid, eid, wk, pct))
        except: pass

    load_matrix()
    return ft.Column([Title("🔢 Capacity Plan (Excel View)"), ft.Container(content=rows_container, expand=True)], expand=True)

# --- MAIN APP STRUCTURE ---

def main(page: ft.Page):
    page.title = "CorpManager Pro"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.spacing = 0
    
    # --- BARRA SUPERIOR FIJA (NATIVA DE FLET = 100% STICKY) ---
    page.appbar = ft.AppBar(
        leading=ft.Icon(ft.icons.GRID_VIEW_ROUNDED, color=C_PRIMARY),
        leading_width=40,
        title=ft.Text("CorpManager v1.0", weight=ft.FontWeight.BOLD, color=C_TEXT),
        center_title=False,
        bgcolor=ft.colors.WHITE,
        shadow_color=ft.colors.BLACK12,
        elevation=4,
        actions=[
            ft.IconButton(ft.icons.PEOPLE, tooltip="Employees", on_click=lambda e: navigate(0)),
            ft.IconButton(ft.icons.ROCKET_LAUNCH, tooltip="Projects", on_click=lambda e: navigate(1)),
            ft.IconButton(ft.icons.CALENDAR_MONTH, tooltip="Calendar", on_click=lambda e: navigate(2)),
            ft.IconButton(ft.icons.TABLE_CHART, tooltip="Planning", on_click=lambda e: navigate(3)),
            ft.Container(width=20)
        ]
    )

    # --- CONTENEDOR PRINCIPAL (CAMBIA SEGÚN BOTÓN) ---
    main_content = ft.Container(padding=20, expand=True)

    def navigate(index):
        main_content.content = None # Clear
        if index == 0: main_content.content = view_employees(page)
        elif index == 1: main_content.content = view_projects(page)
        elif index == 2: main_content.content = view_calendar(page)
        elif index == 3: main_content.content = view_planning(page)
        page.update()

    # Inicio
    navigate(0)
    
    page.add(main_content)

import os # <--- Asegúrate de importar os arriba del todo del archivo

# ... todo tu código anterior ...

if __name__ == "__main__":
    # Obtenemos el puerto de la nube o usamos 8080 por defecto
    port = int(os.environ.get("PORT", 8080))
    
    # Ejecutamos la app directamente
    ft.app(
        target=main, 
        view=ft.AppView.WEB_BROWSER, 
        port=port, 
        host="0.0.0.0"
    )
    # Ejecutar en modo escritorio o web
    ft.app(target=main, view=ft.AppView.WEB_BROWSER)