# Foodgram

Foodgram is a social network for food lovers. Users can share their recipes, subscribe to other users, add recipes to favorites, and create shopping lists.

## Features

- User registration and authentication
- Recipe creation and management
- Ingredient management
- Recipe favorites
- Shopping list generation
- User subscriptions
- Recipe filtering and search

## Tech Stack

- Python 3.9
- Django 4.2
- Django REST Framework
- PostgreSQL
- Docker
- Nginx
- React (frontend)

## Setup

1. Clone the repository:
```bash
git clone https://github.com/PinGBin74/foodgram.git
cd foodgram
```

2. Create a `.env` file in the `infra` directory with the following variables:
```
DEBUG=False
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
POSTGRES_DB=foodgram
POSTGRES_USER=foodgram_user
POSTGRES_PASSWORD=your-password
DB_HOST=db
DB_PORT=5432
```

3. Build and start the containers:
```bash
cd infra
docker-compose up -d
```

4. Run migrations:
```bash
docker-compose exec backend python manage.py migrate
```

5. Create a superuser:
```bash
docker-compose exec backend python manage.py createsuperuser
```

6. Load initial data:
```bash
docker-compose exec backend python manage.py load_ingredients
```

## API Documentation

API documentation is available at `/api/docs/` when the server is running.

## License

This project is licensed under the MIT License.

