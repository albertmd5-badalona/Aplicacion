FROM python:3.9-slim

WORKDIR /app

# Instalamos dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el código
COPY . .

# Render necesita saber que exponemos este puerto (aunque usaremos la variable de entorno)
EXPOSE 8080

# COMANDO IMPORTANTE:
# Usamos 'python' directo en lugar de 'flet run'.
# Esto evita el error de flet_desktop.
CMD ["python", "main.py"]