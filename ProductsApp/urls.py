from django.urls import path
from .views import (
    # Public API
    ProductListAPIView,
    ProductDetailAPIView,
    CategoryListAPIView,
    SizeListAPIView,
    # Auth
    AdminLoginView,
    AdminLogoutView,
    # Admin panel
    AdminPanelView,
    AdminProductCreateView,
    AdminProductUpdateView,
    AdminProductDeleteView,
)

urlpatterns = [
    # ── Публичный каталог ──────────────────────────────
    path('api/products/',              ProductListAPIView.as_view(),   name='api_products'),
    path('api/products/<int:pk>/',     ProductDetailAPIView.as_view(), name='api_product_detail'),
    path('api/products/categories/',   CategoryListAPIView.as_view(),  name='api_categories'),
    path('api/products/sizes/',        SizeListAPIView.as_view(),      name='api_sizes'),

    # ── Авторизация ────────────────────────────────────
    path('admin/login',                AdminLoginView.as_view(),       name='admin_login'),
    path('admin/logout',               AdminLogoutView.as_view(),      name='admin_logout'),

    # ── Панель управления ──────────────────────────────
    path('admin/panel',                AdminPanelView.as_view(),       name='admin_panel'),

    # ── CRUD товаров ───────────────────────────────────
    path('admin/products/add',         AdminProductCreateView.as_view(), name='admin_product_add'),
    path('admin/products/<int:pk>/edit',   AdminProductUpdateView.as_view(), name='admin_product_edit'),
    path('admin/products/<int:pk>/delete', AdminProductDeleteView.as_view(), name='admin_product_delete'),
]
