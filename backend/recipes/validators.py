from django.core.exceptions import ValidationError

from .constants import URL_USER_PROFILE


def username_validator(value):
    if value.lower() == URL_USER_PROFILE:
        raise ValidationError(
            f'Юзернейм {value} запрещено использовать')
