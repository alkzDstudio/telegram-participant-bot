FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

# Копируем participants.json из data/
COPY data/participants.json ./

COPY . .

CMD ["python", "bot.py"]
