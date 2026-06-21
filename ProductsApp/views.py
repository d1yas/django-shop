from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.views import View
from django.db.models import Count, Q
from django.conf import settings

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

import json

from .models import Product
from .serializers import ProductSerializer, ProductWriteSerializer


# ─────────────────────────────────────────────
# PUBLIC API  (используется index.html)
# ─────────────────────────────────────────────

class ProductListAPIView(APIView):
    """
    GET /api/products/
    Возвращает все товары для публичного каталога.
    Поддерживает query-параметры:
      ?category=Футболки
      ?badge=new|hot
      ?in_stock=true
      ?search=текст
    """

    def get(self, request):
        qs = Product.objects.all()

        category = request.query_params.get('category')
        badge    = request.query_params.get('badge')
        in_stock = request.query_params.get('in_stock')
        search   = request.query_params.get('search', '').strip()

        if category:
            qs = qs.filter(category=category)
        if badge:
            qs = qs.filter(badge=badge)
        if in_stock is not None:
            qs = qs.filter(in_stock=in_stock.lower() == 'true')
        if search:
            qs = qs.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )

        serializer = ProductSerializer(qs, many=True)
        return Response(serializer.data)


class ProductDetailAPIView(APIView):
    """
    GET /api/products/<id>/
    """

    def get(self, request, pk):
        product    = get_object_or_404(Product, pk=pk)
        serializer = ProductSerializer(product)
        return Response(serializer.data)


class CategoryListAPIView(APIView):
    """
    GET /api/products/categories/
    Возвращает список уникальных категорий.
    """

    def get(self, request):
        categories = (
            Product.objects.values_list('category', flat=True)
            .distinct()
            .order_by('category')
        )
        return Response({'categories': list(categories)})


class SizeListAPIView(APIView):
    """
    GET /api/products/sizes/
    Возвращает список уникальных размеров из всех товаров.
    """

    def get(self, request):
        sizes_set: set[str] = set()
        for product in Product.objects.all():
            sizes_set.update(product.sizes)
        return Response({'sizes': sorted(sizes_set)})


# ─────────────────────────────────────────────
# ADMIN  —  сессионный вход (login.html)
# ─────────────────────────────────────────────

class AdminLoginView(View):
    """
    GET  /admin/login  → показывает login.html
    POST /admin/login  → проверяет пароль, редиректит в панель
    """
    template_name = 'login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('admin_panel')
        return render(request, self.template_name)

    def post(self, request):
        password = request.POST.get('password', '')
        # Используем стандартного superuser Django: имя берём из настроек
        admin_username = getattr(settings, 'ADMIN_USERNAME', 'admin')
        user = authenticate(request, username=admin_username, password=password)

        if user is not None and user.is_staff:
            login(request, user)
            return redirect('admin_panel')

        return render(request, self.template_name, {'error': 'Неверный пароль'})


class AdminLogoutView(View):
    """GET /admin/logout"""

    def get(self, request):
        logout(request)
        return redirect('admin_login')


# ─────────────────────────────────────────────
# ADMIN PANEL  (panel.html)
# ─────────────────────────────────────────────

SIZES_ALL = ['XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL']


@method_decorator(login_required(login_url='/admin/login'), name='dispatch')
class AdminPanelView(View):
    """
    GET /admin/panel  → рендерит panel.html с данными
    """
    template_name = 'panel.html'

    def _get_context(self):
        products = Product.objects.all()
        stats = {
            'total': products.count(),
            'cats' : products.values('category').distinct().count(),
            'new'  : products.filter(badge='new').count(),
            'hot'  : products.filter(badge='hot').count(),
        }
        # Сериализованные продукты для JS (openEdit)
        products_json = json.dumps([
            {
                'id': p.id,
                'name': p.name,
                'category': p.category,
                'description': p.description,
                'price': p.price,
                'badge': p.badge,
                'in_stock': p.in_stock,
                'images': p.images,
                'sizes': p.sizes,
            }
            for p in products
        ], ensure_ascii=False)
        return {
            'products' : products,
            'products_json': products_json,
            'stats'    : stats,
            'sizes_all': SIZES_ALL,
        }

    def get(self, request):
        return render(request, self.template_name, self._get_context())


# ─────────────────────────────────────────────
# ADMIN API — CRUD товаров (из panel.html)
# ─────────────────────────────────────────────

@method_decorator(login_required(login_url='/admin/login'), name='dispatch')
class AdminProductCreateView(APIView):
    """
    POST /admin/products/add
    Принимает данные HTML-формы (form-encoded / multipart).
    """

    def post(self, request):
        data = self._parse_form(request)
        serializer = ProductWriteSerializer(data=data)

        if serializer.is_valid():
            serializer.save()
            if self._is_browser(request):
                return redirect('admin_panel')
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if self._is_browser(request):
            return redirect('admin_panel')
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @staticmethod
    def _parse_form(request) -> dict:
        # DRF QueryDict → plain dict
        if hasattr(request.data, 'dict'):
            data = request.data.dict()
        else:
            data = dict(request.data)

        # sizes приходят как список из чекбоксов
        data['sizes'] = request.data.getlist('sizes', [])

        # in_stock: если чекбокс есть в запросе → True
        data['in_stock'] = 'in_stock' in request.data

        # Если sizes пустой — ставим пустой список
        # (уже есть от getlist)
        return data

    @staticmethod
    def _is_browser(request) -> bool:
        if hasattr(request, 'accepted_media_type'):
            return 'text/html' in request.accepted_media_type
        return True


@method_decorator(login_required(login_url='/admin/login'), name='dispatch')
class AdminProductUpdateView(APIView):
    """
    POST /admin/products/<id>/edit
    """

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        data = AdminProductCreateView._parse_form(request)
        serializer = ProductWriteSerializer(product, data=data, partial=True)

        if serializer.is_valid():
            serializer.save()
            if AdminProductCreateView._is_browser(request):
                return redirect('admin_panel')
            return Response(serializer.data)

        if AdminProductCreateView._is_browser(request):
            return redirect('admin_panel')
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(login_required(login_url='/admin/login'), name='dispatch')
class AdminProductDeleteView(APIView):
    """
    POST /admin/products/<id>/delete
    DELETE /admin/products/<id>/delete  (для REST-клиентов)
    """

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        product.delete()
        if AdminProductCreateView._is_browser(request):
            return redirect('admin_panel')
        return Response(status=status.HTTP_204_NO_CONTENT)

    def delete(self, request, pk):
        return self.post(request, pk)
