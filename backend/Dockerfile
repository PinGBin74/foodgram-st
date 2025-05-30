FROM python:3.10
# Для корректной работы со SCRUM используется python 3.10
WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y libpq-dev gcc

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/static/

CMD sh -c "python manage.py collectstatic --noinput && python manage.py migrate && gunicorn foodgram.wsgi --bind 0.0.0.0:8000"