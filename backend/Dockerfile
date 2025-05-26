FROM python:3.9.13

# Установка рабочей директории
WORKDIR /app

# Установка зависимостей
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Копирование проекта
COPY . .

# Создание директории для статических файлов
RUN mkdir -p /app/static/

# Запуск миграций, сбор статики и запуск сервера
CMD sh -c "python manage.py collectstatic --noinput && python manage.py migrate && gunicorn foodgram.wsgi --bind 0.0.0.0:8000"