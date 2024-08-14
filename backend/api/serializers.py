from django.contrib.auth import get_user_model
from djoser.serializers import UserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from recipes.constants import MIN_VALUE_AMOUNT
from recipes.models import (BaseFavoriteAndShoppingList, Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingList, Subscribe, Tag)

User = get_user_model()


class UserGetSerializer(UserSerializer):
    """Сериализатор пользователей."""
    is_subscribed = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'email',
                  'is_subscribed', 'avatar')

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        return (request.user.is_authenticated
                and request.user.follower.filter(author=obj).exists())


class AvatarSerializer(UserGetSerializer):
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


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Сериализатор ингредиентов в рецепте."""
    name = serializers.StringRelatedField(source='ingredient')
    measurement_unit = serializers.StringRelatedField(
        source='ingredient.measurement_unit')

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')
        read_only_fields = ('name', 'measurement_unit')


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор получения рецептов."""
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageField()
    tags = TagSerializer(many=True)
    ingredients = RecipeIngredientSerializer(
        many=True, source='ingredient_recipe')
    author = UserGetSerializer()

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients', 'is_favorited',
                  'is_in_shopping_cart', 'name', 'image', 'text',
                  'cooking_time')
        read_only_fields = ('author', 'ingredients', 'tags', 'is_favorited',
                            'is_in_shopping_cart')

    def get_is_favorited(self, obj):
        user = self.context.get('request').user
        return (user.is_authenticated
                and user.favorites.filter(recipe=obj).exists())

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        return (user.is_authenticated
                and user.shoppinglists.filter(recipe=obj).exists())


class IngredientPostSerializer(serializers.ModelSerializer):
    """Сериализатор добавления ингредиентов в рецепт."""
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(), source='ingredient')
    amount = serializers.IntegerField(min_value=MIN_VALUE_AMOUNT)

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
    author = UserGetSerializer(read_only=True)

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients', 'name', 'image',
                  'text', 'cooking_time')

    def validate(self, attrs):
        tags = attrs.get('tags')
        if not tags:
            raise serializers.ValidationError('Вы не добавили теги')
        if len(tags) != len(set(tags)):
            raise serializers.ValidationError('Теги не должны повторяться')
        ingredients = attrs.get('ingredient_recipe')
        if not ingredients:
            raise serializers.ValidationError('Вы не добавили ингредиенты')
        ingredients_list = []
        for i in ingredients:
            if i in ingredients_list:
                raise serializers.ValidationError(
                    'Вы уже добавили этот ингредиент')
            ingredients_list.append(i)
        if (not attrs.get('image')
           and self.context.get('request').method == 'POST'):
            raise serializers.ValidationError('Вы не добавлили картинку')
        return attrs

    def __add_ingredients(self, recipe, ingredients):
        ingredients_list = []
        for i in ingredients:
            ingredients_list.append(RecipeIngredient(
                ingredient=i.get('ingredient'),
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


class SubscribeUserSerializer(UserGetSerializer):
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
        recipes = obj.recipes.all()
        if recipes_limit and recipes_limit.isdigit():
            recipes = obj.recipes.all()[:int(recipes_limit)]
        return CutRecipeSerializer(recipes, many=True).data


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

    def to_representation(self, instance):
        request = self.context.get('request')
        return SubscribeUserSerializer(
            instance.author, context={'request': request}).data


class BaseFavoriteAndShoppingListSerializer(serializers.ModelSerializer):
    """Базовый сериализатор для избранного и списка покупок."""

    class Meta:
        fields = ('user', 'recipe')

    def validate(self, attrs):
        model_class = self.Meta.model
        if model_class.objects.filter(
           user=attrs['user'], recipe=attrs['recipe']).exists():
            raise serializers.ValidationError(
                f'Рецепт уже добавлен в {model_class.__name__.lower()}'
            )
        return attrs

    def to_representation(self, instance):
        request = self.context.get('request')
        return CutRecipeSerializer(
            instance.recipe, context={'request': request}).data


class ShoppingListSerializer(BaseFavoriteAndShoppingListSerializer):
    """Сериализатор списка покупок."""

    class Meta(BaseFavoriteAndShoppingListSerializer.Meta):
        model = ShoppingList


class FavoriteSerializer(BaseFavoriteAndShoppingListSerializer):
    """Сериализатор избранного."""

    class Meta(BaseFavoriteAndShoppingListSerializer.Meta):
        model = Favorite
