import os
import requests

from django.db.models import F, Sum
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingList, Subscribe, Tag)
from .filters import IngredientFilter, RecipeFilter
from .paginations import CustomPagination
from .permissions import IsAuthorOrReadOnly
from .serializers import (AvatarSerializer, IngredientSerializer,
                          CustomUserSerializer, CutRecipeSerializer,
                          FavoriteSerializer, RecipeSerializer,
                          RecipeWriteSerializer, ShoppingListSerializer,
                          SubscribeSerializer, SubscribeUserSerializer,
                          TagSerializer)

User = get_user_model()


class CustomUserViewSet(UserViewSet):
    queryset = User.objects.all()
    serializer_class = CustomUserSerializer
    pagination_class = CustomPagination

    @action(detail=False, permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        return super().me(request)

    @action(methods=['PUT', 'DELETE'], detail=False,
            permission_classes=[permissions.IsAuthenticated],
            url_path='me/avatar')
    def avatar(self, request):
        user = request.user
        if request.method == 'PUT':
            serializer = AvatarSerializer(user, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        if user.avatar:
            os.remove(user.avatar.path)
            user.avatar = None
            user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({"errors": "У вас нет аватара"},
                        status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['POST', 'DELETE'], detail=True,
            permission_classes=[permissions.IsAuthenticated])
    def subscribe(self, request, id=None):
        user = request.user
        author = get_object_or_404(User, pk=id)
        if request.method == 'POST':
            serializer = SubscribeSerializer(
                data={'user': user.pk, 'author': author.pk},)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            serializer = SubscribeUserSerializer(
                author, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        if Subscribe.objects.filter(user=user, author=author).exists():
            Subscribe.objects.filter(user=user, author=author).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({'errors': 'Подписки не существует'},
                        status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, permission_classes=[permissions.IsAuthenticated])
    def subscriptions(self, request):
        followings = User.objects.filter(
            following__user=request.user).prefetch_related('recipes')
        pages = self.paginate_queryset(followings)
        serializer = SubscribeUserSerializer(
            pages, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    pagination_class = CustomPagination
    permission_classes = (IsAuthorOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    http_method_names = ('get', 'post', 'patch', 'delete')

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return RecipeSerializer
        return RecipeWriteSerializer

    @action(detail=True, url_path='get-link')
    def get_link(self, request, pk=None):
        endpoint = 'https://clck.ru/--'
        url = request.build_absolute_uri(f'/api/recipes/{pk}/')
        response = requests.get(endpoint, params={'url': url})
        return Response({'short-link': response.text})

    def __recipe(self, request, model, serializer_class, pk=None):
        model_text = 'список покупок' if model == ShoppingList else 'избранное'
        user = request.user
        recipe = get_object_or_404(Recipe, pk=pk)
        if request.method == 'POST':
            if model.objects.filter(user=user, recipe=recipe).exists():
                return Response(
                    {'errors': f'Рецепт уже добавлен в {model_text}'},
                    status=status.HTTP_400_BAD_REQUEST)
            serializer = serializer_class(
                data={'user': user.pk, 'recipe': recipe.pk})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            serializer = CutRecipeSerializer(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        if model.objects.filter(user=user, recipe=recipe).exists():
            model.objects.filter(user=user, recipe=recipe).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({'errors': f'Рецепт не был добавлен в {model_text}'},
                        status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['POST', 'DELETE'], detail=True,
            permission_classes=[permissions.IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        return self.__recipe(request, ShoppingList, ShoppingListSerializer, pk)

    @action(methods=['POST', 'DELETE'], detail=True,
            permission_classes=[permissions.IsAuthenticated])
    def favorite(self, request, pk=None):
        return self.__recipe(request, Favorite, FavoriteSerializer, pk)

    @action(detail=False, permission_classes=[permissions.IsAuthenticated])
    def download_shopping_cart(self, request):
        ingredients = RecipeIngredient.objects.filter(
            recipe__shoppinglists__user=request.user).values(
            name=F('ingredient__name'),
            measurement_unit=F('ingredient__measurement_unit')).annotate(
            amount=Sum('amount'))
        data = []
        for ingredient in ingredients:
            data.append(
                f' - {ingredient["name"]} '
                f'{ingredient["amount"]} '
                f'{ingredient["measurement_unit"]}')
        data += [f'\nЗагружено с сайта {request.build_absolute_uri("/")}']
        content = 'Список покупок:\n' + '\n'.join(data)
        filename = 'shopping_cart.txt'
        request = HttpResponse(content, content_type='text/plain')
        request['Content-Disposition'] = f'attachment; filename={filename}'
        return request
