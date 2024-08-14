from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models

from .constants import (MAX_LEN_NAME, MAX_LEN_EMAIL, MAX_LEN_USER_FIELD,
                        MIN_VALUE_AMOUNT, MAX_LEN_SLUG,
                        MAX_LEN_MEASUREMENT_UNIT, MIN_VALUE_COOKING_TIME)
from .validators import username_validator


class Ingredient(models.Model):
    """Модель ингредиента."""
    name = models.CharField(
        verbose_name='Название',
        max_length=MAX_LEN_NAME,
        db_index=True,
    )
    measurement_unit = models.CharField(
        verbose_name='Единица измерения',
        max_length=MAX_LEN_MEASUREMENT_UNIT,
    )

    class Meta:
        ordering = ('name',)
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'measurement_unit'],
                name='unique_name_measurement_unit')]

    def __str__(self):
        return self.name


class Tag(models.Model):
    """Модель тега."""
    name = models.CharField(
        verbose_name='Название',
        max_length=MAX_LEN_NAME,
        unique=True,
    )
    slug = models.SlugField(
        verbose_name='Slug',
        max_length=MAX_LEN_SLUG,
        unique=True,
        db_index=True,
    )

    class Meta:
        ordering = ('name',)
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'slug'],
                name='unique_name_slug')]

    def __str__(self):
        return self.name


class User(AbstractUser):
    """Модель пользователя."""
    email = models.EmailField(
        verbose_name='Email',
        max_length=MAX_LEN_EMAIL,
        unique=True,
    )
    username = models.CharField(
        verbose_name='Юзернейм',
        max_length=MAX_LEN_USER_FIELD,
        validators=[RegexValidator(regex=r'^[\w.@+-]+\Z',),
                    username_validator],
        unique=True,
    )
    first_name = models.CharField(
        verbose_name='Имя',
        max_length=MAX_LEN_USER_FIELD,
    )
    last_name = models.CharField(
        verbose_name='Фамилия',
        max_length=MAX_LEN_USER_FIELD,
    )
    avatar = models.ImageField(
        verbose_name='Аватар',
        upload_to='users',
        blank=True,
        null=True,
    )
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        ordering = ('username',)
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.username


class Recipe(models.Model):
    """Модель рецептов."""
    name = models.CharField(
        max_length=MAX_LEN_NAME,
        verbose_name='Название',
    )
    image = models.ImageField(
        upload_to='recipes',
        verbose_name='Картинка',
    )
    text = models.TextField(
        verbose_name='Текстовое описание',
    )
    author = models.ForeignKey(
        User,
        verbose_name='Автор',
        on_delete=models.CASCADE,
        related_name='recipes',
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        verbose_name='Ингредиенты',
        through='RecipeIngredient',
        related_name='recipes',
    )
    tags = models.ManyToManyField(
        Tag,
        verbose_name='Теги',
        related_name='recipes',
    )
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name='Время приготовления',
        validators=[MinValueValidator(MIN_VALUE_COOKING_TIME), ]
    )

    class Meta:
        ordering = ('-id',)
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        default_related_name = 'recipes'

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    """Промежуточная модель ингредиентов в рецепте."""
    recipe = models.ForeignKey(
        Recipe,
        verbose_name='Рецепт',
        on_delete=models.CASCADE,
        related_name='ingredient_recipe'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        verbose_name='Ингредиент',
        on_delete=models.CASCADE,
        related_name='ingredient_recipe'
    )
    amount = models.PositiveSmallIntegerField(
        verbose_name='Количество',
        validators=[MinValueValidator(MIN_VALUE_AMOUNT), ],
    )

    class Meta:
        ordering = ('id',)
        verbose_name = 'Ингредиент в рецепте'
        verbose_name_plural = 'Ингредиенты в рецепте'
        default_related_name = 'ingredient_recipe'

    def __str__(self):
        return (f'{self.recipe.name}. '
                f'{self.ingredient.name}: '
                f'{self.amount} '
                f'{self.ingredient.measurement_unit}')


class Subscribe(models.Model):
    """Модель подписки."""
    user = models.ForeignKey(
        User,
        verbose_name='Подписчик',
        on_delete=models.CASCADE,
        related_name='follower',
    )
    author = models.ForeignKey(
        User,
        verbose_name='Автор',
        on_delete=models.CASCADE,
        related_name='following',
    )

    class Meta:
        ordering = ('author',)
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'],
                name='unique_user_author'),]

    def __str__(self):
        return f'{self.user} подписан на {self.author}'

    def clean(self):
        if self.user == self.author:
            raise ValidationError('Нельзя подписаться на самого себя')
        super().clean()


class BaseFavoriteAndShoppingList(models.Model):
    """Абстрактная модель для избранного и списка покупок."""
    user = models.ForeignKey(
        User,
        verbose_name='Пользователь',
        on_delete=models.CASCADE,
    )
    recipe = models.ForeignKey(
        Recipe,
        verbose_name='Рецепт',
        on_delete=models.CASCADE,
    )

    class Meta:
        abstract = True

    def __str__(self):
        return f'{self.user} - {self.recipe}'


class Favorite(BaseFavoriteAndShoppingList):
    """Модель избранного."""

    class Meta:
        ordering = ('id',)
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'
        default_related_name = 'favorites'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_user_favorite')]


class ShoppingList(BaseFavoriteAndShoppingList):
    """Модель списка покупок."""

    class Meta:
        ordering = ('id',)
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Списки покупок'
        default_related_name = 'shoppinglists'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_user_list')]
