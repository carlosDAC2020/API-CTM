# Cambia esta línea de 3.9 a 3.11
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

COPY requirements.txt .
# Ahora este comando funcionará porque Python 3.11 es compatible con click==8.3.0
RUN pip install --no-cache-dir -r requirements.txt

COPY . .