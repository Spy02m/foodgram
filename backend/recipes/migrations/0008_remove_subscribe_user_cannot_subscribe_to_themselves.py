# Generated by Django 3.2 on 2024-08-13 10:53

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0007_subscribe_user_cannot_subscribe_to_themselves'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='subscribe',
            name='user_cannot_subscribe_to_themselves',
        ),
    ]
