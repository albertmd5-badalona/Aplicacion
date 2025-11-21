FROM python:3.9-slim

WORKDIR /app

# Instalamos dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del código
COPY . .

# IMPORTANTE: Render nos da un puerto en la variable de entorno PORT.
# Si no existe, usamos el 8080.
ENV FLET_SERVER_PORT=8080
ENV FLET_FORCE_WEB_SERVER=1

# Comando para arrancar. 
# --host 0.0.0.0 es OBLIGATORIO para que se vea desde fuera.
CMD flet run main.py --port ${PORT:-8080} --web --host 0.0.0.0