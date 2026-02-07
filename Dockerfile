FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

# Копируем .env
COPY .env ./

COPY . .

CMD ["python", "bot.py"]
