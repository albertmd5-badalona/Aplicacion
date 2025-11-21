FROM python:3.9-slim

WORKDIR /app

# 1. Instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Copiar el código
COPY . .

# 3. Exponer el puerto 8080 (aunque usamos la variable de entorno)
EXPOSE 8080

# 4. COMANDO DE ARRANQUE
# Usamos python directo para evitar errores de flet_desktop
CMD ["python", "main.py"]