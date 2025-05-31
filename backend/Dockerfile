FROM python:3.12
# Для корректной работы со SCRAM используется python 3.12
WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y libpq-dev gcc

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/static/ /var/html/media/recipes_photo /var/html/media/avatar_photos && \
    chown -R www-data:www-data /var/html/media/ && \
    chmod -R 755 /var/html/media/

USER www-data

CMD sh -c "python manage.py collectstatic --noinput && python manage.py migrate && gunicorn foodgram.wsgi --bind 0.0.0.0:8000"