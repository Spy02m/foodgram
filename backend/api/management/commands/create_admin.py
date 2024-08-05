from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = 'Команда создает суперпользователя'

    def handle(self, *args, **options):
        if User.objects.count() == 0:
            User.objects.create_superuser(
                email='admin@admin.com',
                username='admin',
                password='admin123',
                first_name='admin',
                last_name='admin')
            print('Суперпользователь успешно создан')
        else:
            print('Аккаунт администратора может быть создан, '
                  'если нет других учетных записей')
