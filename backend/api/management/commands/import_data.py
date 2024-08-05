from csv import reader

from django.core.management.base import BaseCommand

from recipes.models import Ingredient, Tag

NAME_TAGS = ['Завтрак', 'Обед', 'Ужин']
SLUG_TAGS = ['breakfast', 'lunch', 'dinner']


class Command(BaseCommand):
    help = 'Команда импортирует ингредиенты из .csv файла и теги списка.'

    def handle(self, *args, **options):
        with (open('data/ingredients.csv', 'r', encoding='UTF-8')
              as ingredients):
            for data in reader(ingredients):
                name, measurement_unit = data
                Ingredient.objects.get_or_create(
                    name=name, measurement_unit=measurement_unit)
            for value in range(3):
                Tag.objects.get_or_create(
                    name=NAME_TAGS[value], slug=SLUG_TAGS[value])
        print('Импорт игредиентов и тегов успешно завершен')
