from django import forms
from django.contrib import admin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.auth.models import Group
from django.contrib.auth.admin import UserAdmin as MainUserAdmin
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet

from .models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                     ShoppingList, Subscribe, Tag, User)


class UserAdminCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User


class UserAdminForm(UserChangeForm):
    password = forms.CharField(
        widget=forms.PasswordInput(render_value=False),
        label='Новый пароль',
        required=False,
        help_text='Введите новый пароль, если хотите его изменить')

    class Meta(UserChangeForm.Meta):
        model = User

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'password' not in self.initial:
            self.fields.pop('password')


@admin.register(User)
class UserAdmin(MainUserAdmin):
    form = UserAdminForm
    add_form = UserAdminCreationForm
    list_display = ('id', 'email', 'username', 'first_name', 'last_name',)
    search_fields = ('email', 'username',)
    list_display_links = ('username',)
    fieldsets = (
        ('Аккаунт', {'fields': ('email', 'password')}),
        ('Персональные данные', {'fields': ('username', 'first_name',
                                            'last_name', 'avatar')}),
        ('Доступы', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Важные даты', {'fields': ('last_login', 'date_joined')}),)

    def save_model(self, request, obj, form, change):
        if 'password' in form.changed_data:
            obj.set_password(form.cleaned_data['password'])
        obj.save()


class PageFormSet(BaseInlineFormSet):

    def clean(self):
        super(PageFormSet, self).clean()
        if all(form.cleaned_data.get('DELETE') for form in self.forms):
            raise ValidationError('Не бывает рецепта без ингредиентов')


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1
    formset = PageFormSet


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'author', 'favorites_count',)
    search_fields = ('author', 'name',)
    list_display_links = ('name',)
    list_filter = ('tags',)
    inlines = (RecipeIngredientInline,)
    readonly_fields = ('favorites_count',)

    @admin.display(description='Добавлен в избранное')
    def favorites_count(self, obj):
        return obj.favorites.count()


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'measurement_unit',)
    search_fields = ('name',)
    list_display_links = ('name',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug',)
    search_fields = ('name', 'slug',)
    list_display_links = ('name',)


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe',)
    search_fields = ('user', 'recipe',)


@admin.register(ShoppingList)
class ShoppingListAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe',)
    search_fields = ('user', 'recipe',)


@admin.register(Subscribe)
class SubscribeAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'author',)
    search_fields = ('user', 'author',)


admin.site.unregister(Group)
