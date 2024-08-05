from django.db.models import F
from django.contrib.auth import get_user_model
from djoser.serializers import UserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingList, Subscribe, Tag)

User = get_user_model()


class CustomUserSerializer(UserSerializer):
    """Сериализатор пользователей."""
    is_subscribed = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'email',
                  'is_subscribed', 'avatar')

    def get_is_subscribed(self, obj):
        current_user = self.context.get('request').user
        return (current_user.is_authenticated
                and Subscribe.objects.filter(user=current_user,
                                             author=obj).exists())


class AvatarSerializer(CustomUserSerializer):
    """Сериализатор аватара."""
    avatar = Base64ImageField()

    class Meta:
        model = User
        fields = ('avatar',)


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор тегов."""

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug',)


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор ингредиентов."""

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit',)


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор получения рецептов."""
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageField()
    tags = TagSerializer(many=True)
    ingredients = serializers.SerializerMethodField()
    author = CustomUserSerializer()

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients', 'is_favorited',
                  'is_in_shopping_cart', 'name', 'image', 'text',
                  'cooking_time')
        read_only_fields = ('author', 'ingredients', 'tags', 'is_favorited',
                            'is_in_shopping_cart')

    def get_ingredients(self, obj):
        return obj.ingredients.values('id', 'name', 'measurement_unit',
                                      amount=F('ingredient_recipe__amount'))

    def get_is_favorited(self, obj):
        return Favorite.objects.filter(
            user=self.context.get('request').user.id, recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj):
        return ShoppingList.objects.filter(
            user=self.context.get('request').user.id, recipe=obj).exists()


class IngredientPostSerializer(serializers.ModelSerializer):
    """Сериализатор добавления ингредиентов в рецепт."""
    id = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')


class RecipeWriteSerializer(serializers.ModelSerializer):
    """Сериализатор создания, обновления и удаления рецептов."""
    image = Base64ImageField()
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True)
    ingredients = IngredientPostSerializer(
        many=True, source='ingredient_recipe')
    author = CustomUserSerializer(read_only=True)

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients', 'name', 'image',
                  'text', 'cooking_time')

    def validate(self, attrs):
        if not self.initial_data.get('ingredients'):
            raise serializers.ValidationError('Вы не добавили ингредиенты')
        if not self.initial_data.get('tags'):
            raise serializers.ValidationError('Вы не добавили теги')
        return attrs

    def validate_ingredients(self, value):
        ingredient_list = []
        for i in value:
            try:
                ingredient = Ingredient.objects.get(id=i.get('id'))
            except Ingredient.DoesNotExist:
                raise serializers.ValidationError(
                    'Вы указали несуществующий ингредиент')
            if ingredient in ingredient_list:
                raise serializers.ValidationError(
                    'Вы уже добавили этот ингредиент')
            ingredient_list.append(ingredient)
        return value

    def validate_tags(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError('Теги не должны повторяться')
        return value

    def validate_image(self, value):
        if not value:
            raise serializers.ValidationError('Вы не добавили картинку')
        return value

    def __add_ingredients(self, recipe, ingredients):
        ingredients_list = []
        for i in ingredients:
            ingredients_list.append(RecipeIngredient(
                ingredient=Ingredient.objects.get(id=i.get('id')),
                amount=i.get('amount'),
                recipe=recipe))
        RecipeIngredient.objects.bulk_create(ingredients_list)

    def create(self, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredient_recipe')
        recipe = Recipe.objects.create(
            author=self.context.get('request').user, **validated_data)
        recipe.tags.set(tags)
        self.__add_ingredients(recipe, ingredients)
        recipe.save()
        return recipe

    def update(self, instance, validated_data):
        ingredients = validated_data.pop('ingredient_recipe')
        tags = validated_data.pop('tags')
        super().update(instance, validated_data)
        instance.tags.clear()
        instance.ingredients.clear()
        RecipeIngredient.objects.filter(recipe=instance).delete()
        instance.tags.set(tags)
        self.__add_ingredients(instance, ingredients)
        instance.save()
        return instance

    def to_representation(self, instance):
        return RecipeSerializer(instance, context=self.context).data


class CutRecipeSerializer(serializers.ModelSerializer):
    """Краткий сериализатор рецепта."""

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class SubscribeSerializer(serializers.ModelSerializer):
    """Сериализатор подписки."""

    class Meta:
        model = Subscribe
        fields = ('user', 'author')
        validators = [
            UniqueTogetherValidator(
                queryset=Subscribe.objects.all(),
                fields=('user', 'author'))]

    def validate(self, attrs):
        if attrs.get('user') == attrs.get('author'):
            raise serializers.ValidationError('Нельзя подписаться на себя')
        return super().validate(attrs)


class SubscribeUserSerializer(CustomUserSerializer):
    """Сериализатор подписки пользователя."""
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(read_only=True,
                                             source='recipes.count')

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name', 'last_name',
                  'is_subscribed', 'recipes', 'recipes_count', 'avatar')

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes_limit = request.query_params.get('recipes_limit')
        if recipes_limit:
            recipes = obj.recipes.all()[:int(recipes_limit)]
        else:
            recipes = obj.recipes.all()
        return CutRecipeSerializer(recipes, many=True).data


class ShoppingListSerializer(serializers.ModelSerializer):
    """Сериализатор списка покупок."""

    class Meta:
        model = ShoppingList
        fields = ('user', 'recipe')
        validators = [
            UniqueTogetherValidator(
                queryset=ShoppingList.objects.all(),
                fields=('user', 'recipe'))]


class FavoriteSerializer(serializers.ModelSerializer):
    """Сериализатор избранного."""

    class Meta:
        model = Favorite
        fields = ('user', 'recipe')
        validators = [
            UniqueTogetherValidator(
                queryset=Favorite.objects.all(),
                fields=('user', 'recipe'))]
