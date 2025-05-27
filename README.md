# Foodgram

Foodgram - это социальная сеть для обмена рецептами. Пользователи могут публиковать свои рецепты, подписываться на других пользователей, добавлять рецепты в избранное и создавать списки покупок.

## Технологии

### Backend
- Python 3.9+
- Django 3.2
- Django REST Framework
- PostgreSQL
- Docker
- Nginx

### Frontend
- React
- JavaScript
- HTML/CSS
- Docker
- Nginx

## Основные функции

- Регистрация и авторизация пользователей
- Создание, редактирование и удаление рецептов
- Подписка на других пользователей
- Добавление рецептов в избранное
- Создание списка покупок
- Фильтрация рецептов по тегам
- API для взаимодействия с приложением

## Установка и запуск

### Требования
- Docker
- Docker Compose

### Локальный запуск

1. Клонируйте репозиторий:
```bash
git clone https://github.com/PinGBin74/foodgram-st.git
cd foodgram
```

2. Создайте файл .env в директории backend со следующими переменными:
```
DB_ENGINE=django.db.backends.postgresql
DB_NAME=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432
```

3. Запустите проект с помощью Docker Compose:
```bash
docker-compose up -d
```

4. Примените миграции:
```bash
docker-compose exec backend python manage.py migrate
```

5. Создайте суперпользователя:
```bash
docker-compose exec backend python manage.py createsuperuser
```

6. Соберите статические файлы:
```bash
docker-compose exec backend python manage.py collectstatic --no-input
```

После этого проект будет доступен по адресу http://localhost/

## API Endpoints

API документация доступна по адресу http://localhost/api/docs/

Основные эндпоинты:
- `/api/users/` - управление пользователями
- `/api/recipes/` - управление рецептами
- `/api/tags/` - управление тегами
- `/api/ingredients/` - управление ингредиентами

