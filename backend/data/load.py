import json
import django
import os
from recipes.models import Ingredient

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "foodgram.settings")
django.setup()


def load_data():
    with open(
        "A:/Dev/foodgram/foodgram-st/backend/data/ingredients.json",
        "r",
        encoding="utf-8",
    ) as f:
        data = json.load(f)

    for item in data:
        Ingredient.objects.create(**item)

    print(f"Успешно загружено {len(data)} записей")


if __name__ == "__main__":
    load_data()
