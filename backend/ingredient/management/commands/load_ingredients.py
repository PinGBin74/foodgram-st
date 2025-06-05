import json
from django.core.management.base import BaseCommand
from ingredient.models import Ingredient


class Command(BaseCommand):
    help = "Load ingredients from JSON file"

    def handle(self, *args, **options):
        try:
            with open("data/ingredients.json", "r", encoding="utf-8") as file:
                ingredients = json.load(file)
                for ingredient in ingredients:
                    Ingredient.objects.get_or_create(
                        name=ingredient["name"],
                        measurement_unit=ingredient["measurement_unit"],
                    )
                self.stdout.write(self.style.SUCCESS("Successfully loaded ingredients"))
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR("ingredients.json file not found"))
        except json.JSONDecodeError:
            self.stdout.write(
                self.style.ERROR("Invalid JSON format in ingredients.json")
            )
