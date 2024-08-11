# Foodgram
![Foodgram workflow](https://github.com/spy02m/foodgram/actions/workflows/main.yml/badge.svg)

## Описание
 - Фудграм — сайт, на котором пользователи могут публиковать свои рецепты, добавлять чужие рецепты в избранное и подписываться на публикации других авторов. Зарегистрированным пользователям также доступен сервис «Список покупок». Он позволит создавать список продуктов, которые нужно купить для приготовления выбранных блюд.
 - Проект состоит из бэкенд-приложения на Django и фронтенд-приложения на React.

[Ссылка на развернутый проект](https://foodgram.serveminecraft.net/)
#### Данные для входа в админ-зону:
 - Email: `admin@admin.com`
 - Пароль: `admin123`

## Технологии
 - Python
 - Docker
 - PostgreSQL
 - Django REST Framework
 - Nginx
 - React

## Отличия продакшн-версии от обычной
Продакшн-версия — это готовый продукт, оптимизированный для публичного использования и предназначен для развертывания на сервере.

Обычная версия — это тестовая версия, созданная для удобства разработчиков и используется для локального развертывания и отладки.

## Инструкция по локальному развертыванию
 - Клонировать репозиторий
```
git clone git@github.com:Spy02m/foodgram.git
```
 - Перейти в папку с проектом
```
cd foodgram
```
 - Создать файл .env с переменными окружения
```
POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD
DB_NAME
DB_HOST
DB_PORT
SECRET_KEY
DEBUG
ALLOWED_HOSTS
```
 - Развернуть проект
```
docker compose -f docker-compose.yml up
```
 - Сделать сбор статики и миграции
```
sudo docker compose -f docker-compose.production.yml exec backend python manage.py migrate
sudo docker compose -f docker-compose.production.yml exec backend python manage.py collectstatic
sudo docker compose -f docker-compose.production.yml exec backend cp -r /app/collected_static/. /app/web/static/
```
 - Создать суперпользователя
```
sudo docker compose -f docker-compose.production.yml exec backend python manage.py create_admin
```
 - Импортировать ингредиенты из .csv файла и теги списка
```
sudo docker compose -f docker-compose.production.yml exec backend python manage.py import_data
```
 - Проект будет доступен по локальному адресу: http://127.0.0.1:7777
## Инструкция по удаленному развертыванию
 - Cделать форк к себе в репозиторий.
 - Создать файл .env с переменными окружения на удаленном сервере в папке проекта
```
sudo nano .env
```
```
POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD
DB_NAME
DB_HOST
DB_PORT
SECRET_KEY
DEBUG
ALLOWED_HOSTS
```
 - Создать в репозитории секреты Github Actions:
```
DOCKER_PASSWORD
DOCKER_USERNAME
HOST
USER
SECRET_KEY_DJANGO
SSH_KEY
SSH_PASSPHRASE
TELEGRAM_TO
TELEGRAM_TOKEN
DJANGO_ADMIN_USERNAME
DJANGO_ADMIN_PASSWORD
DJANGO_ADMIN_EMAIL
DJANGO_ADMIN_FIRST_NAME
DJANGO_ADMIN_LAST_NAME
```
 - Изменить файл `.github/workflows/main.yml` под свои параметры
 - Отправить изменения в свой репозиторий
```
git push
```
Проект автоматически развернется на удаленном сервере.
 - Настроить сервер Nginx на порт 7777
```
sudo nano /etc/nginx/sites-enabled/default
```
```
server {
    server_name your-domen.com;

    location / {
        proxy_set_header Host $http_host;
        proxy_pass http://127.0.0.1:7777;
    }

    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/your-domen.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domen.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
}
server {
    if ($host = your-domen.com) {
        return 301 https://$host$request_uri;
    }

    listen 80;
    server_name your-domen.com;
    return 404;
}
```
## Автор
Сергей Баданов