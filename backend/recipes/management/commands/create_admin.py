from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = 'Команда создает суперпользователя'

    def add_arguments(self, parser):
        parser.add_argument('username')
        parser.add_argument('email')
        parser.add_argument('password')
        parser.add_argument('first_name')
        parser.add_argument('last_name')

    def handle(self, *args, **options):
        if not User.objects.filter(username=options['username']).exists():
            User.objects.create_superuser(
                email=options['email'],
                username=options['username'],
                password=options['password'],
                first_name=options['first_name'],
                last_name=options['last_name'])
            print('Суперпользователь успешно создан')
        else:
            print(f'Аккаунт администратора {options["username"]} уже создан')
