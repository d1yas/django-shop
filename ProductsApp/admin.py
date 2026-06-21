from django.contrib import admin
from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display  = ('id', 'name', 'category', 'price', 'badge', 'in_stock', 'created_at')
    list_filter   = ('category', 'badge', 'in_stock')
    search_fields = ('name', 'description', 'category')
    list_editable = ('price', 'in_stock', 'badge')
    ordering      = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')

fieldsets = (
    ('Основное', {
        'fields': ('name', 'category', 'description', 'price'),
    }),
    ('Параметры', {
        'fields': ('badge', 'in_stock', '_sizes', '_images'),
    }),
    ('Даты', {
        'fields': ('created_at', 'updated_at'),
        'classes': ('collapse',),
    }),
)