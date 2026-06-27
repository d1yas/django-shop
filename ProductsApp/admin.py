from django.contrib import admin
from .models import Product, ProductImage


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    max_num = 6
    fields = ('image', 'order')
    ordering = ['order']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display  = ('id', 'name', 'category', 'price', 'badge', 'in_stock', 'created_at')
    list_filter   = ('category', 'badge', 'in_stock')
    search_fields = ('name', 'description', 'category')
    list_editable = ('price', 'in_stock', 'badge')
    ordering      = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ProductImageInline]

    fieldsets = (
        ('Основное', {
            'fields': ('name', 'category', 'description', 'price', 'discount_percent'),
        }),
        ('Параметры', {
            'fields': ('badge', 'in_stock', '_sizes'),
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'order', 'image')
    list_filter = ('product',)
    ordering = ('product', 'order')