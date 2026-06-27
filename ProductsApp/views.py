from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.views import View
from django.db.models import Count, Q
from django.conf import settings

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import urllib.request
import urllib.parse

import json

from .models import Product
from .serializers import ProductSerializer, ProductWriteSerializer


# ─────────────────────────────────────────────
# PUBLIC PAGES (главная страница и каталог)
# ─────────────────────────────────────────────

class HomePageView(View):
    """
    GET /  → показывает главную страницу (home.html)
    """
    template_name = 'home.html'

    def get(self, request):
        # Передаём опциональный Telegram-юзернейм администратора в шаблон
        return render(request, self.template_name, {
            'admin_tg': getattr(settings, 'ADMIN_TG_USERNAME', ''),
        })


class CatalogPageView(View):
    """
    GET /catalog/  → показывает каталог товаров (catalog.html)
    """
    template_name = 'catalog.html'

    def get(self, request):
        # Передаём опциональный Telegram-юзернейм и numeric id администратора
        return render(request, self.template_name, {
            'admin_tg': getattr(settings, 'ADMIN_TG_USERNAME', ''),
            'admin_tg_id': getattr(settings, 'ADMIN_TG_ID', ''),
        })


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
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        
        # Проверка на пустые поля
        if not username or not password:
            return render(request, self.template_name, {'error': 'Заполните все поля'})
        
        # Попытка аутентификации
        user = authenticate(request, username=username, password=password)
        
        if user is None:
            # Проверяем, существует ли пользователь
            try:
                User.objects.get(username=username)
                # Пользователь существует, но пароль неверный
                return render(request, self.template_name, {'error': 'Неверный пароль'})
            except User.DoesNotExist:
                # Пользователь не найден
                return render(request, self.template_name, {'error': 'Пользователь не найден'})
        
        # Проверяем права доступа
        if user.is_staff:
            login(request, user)
            return redirect('admin_panel')
        else:
            return render(request, self.template_name, {'error': 'У вас нет прав доступа'})


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

    def _get_context(self, request):
        search_id = request.GET.get('search_id', '').strip()
        order_product_id = request.GET.get('product_id', '').strip()
        order_size = request.GET.get('size', '').strip()
        order_name = request.GET.get('name', '').strip()

        products = Product.objects.all()
        if search_id.isdigit():
            products = products.filter(id=int(search_id))

        stats = {
            'total': products.count(),
            'cats' : products.values('category').distinct().count(),
            'new'  : products.filter(badge='new').count(),
            'hot'  : products.filter(badge='hot').count(),
        }
        order_info = None
        if order_product_id and order_size:
            order_info = {
                'id': order_product_id,
                'name': order_name,
                'size': order_size,
            }
        # Сериализованные продукты для JS (openEdit)
        products_json = json.dumps([
            {
                'id': p.id,
                'name': p.name,
                'category': p.category,
                'description': p.description,
                'price': p.price,
                'discount_percent': p.discount_percent,
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
            'sizes_all_json': json.dumps(SIZES_ALL),
            'search_id': search_id,
            'order_info': order_info,
        }

    def get(self, request):
        return render(request, self.template_name, self._get_context(request))


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

        # Получаем файлы изображений (множественные)
        images = request.FILES.getlist('images')

        # Валидация количества изображений
        if not images or len(images) < 1:
            if self._is_browser(request):
                return redirect('admin_panel')
            return Response({'error': 'Необходимо загрузить минимум 1 изображение'}, status=status.HTTP_400_BAD_REQUEST)

        if len(images) > 6:
            if self._is_browser(request):
                return redirect('admin_panel')
            return Response({'error': 'Максимум 6 изображений'}, status=status.HTTP_400_BAD_REQUEST)

        data['images'] = images

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


class SendOrderAPIView(APIView):
    """
    POST /api/send_order/
    Accepts JSON: { product_id, name, size, price, contact (optional) }
    Sends a message to admin via Telegram Bot API using settings.TELEGRAM_BOT_TOKEN
    and settings.ADMIN_TG_ID.
    """

    def post(self, request):
        bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
        admin_chat = getattr(settings, 'ADMIN_TG_ID', '')

        if not bot_token or not admin_chat:
            return Response({'detail': 'Bot token or admin chat id not configured'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        data = request.data if hasattr(request, 'data') else request.POST
        name = data.get('name') or ''
        size = data.get('size') or ''
        price = data.get('price') or ''

        size_part = f" | Размер: {size}" if size else ''
        text = (
            "Привет! Хочу заказать:\n\n"
            f"👕 {name}{size_part}\n"
            f"💰 Цена: {price}\n\n"
            "Ожидаю подтверждения заказа!"
        )

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {'chat_id': admin_chat, 'text': text}
        data_encoded = urllib.parse.urlencode(payload).encode()
        req = urllib.request.Request(url, data=data_encoded)
        try:
            resp = urllib.request.urlopen(req, timeout=10)
            return Response({'ok': True}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'ok': False, 'error': str(e)}, status=status.HTTP_502_BAD_GATEWAY)


@method_decorator(login_required(login_url='/admin/login'), name='dispatch')
class AdminProductUpdateView(APIView):
    """
    POST /admin/products/<id>/edit
    """

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        data = AdminProductCreateView._parse_form(request)

        # Получаем файлы изображений (множественные)
        images = request.FILES.getlist('images')

        # Если загружены новые изображения, добавляем их в data
        if images:
            # Валидация количества изображений
            if len(images) > 6:
                if AdminProductCreateView._is_browser(request):
                    return redirect('admin_panel')
                return Response({'error': 'Максимум 6 изображений'}, status=status.HTTP_400_BAD_REQUEST)

            data['images'] = images

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


@method_decorator(login_required(login_url='/admin/login'), name='dispatch')
class AdminProductQuickUpdateView(APIView):
    """
    PATCH /admin/products/<id>/quick-update
    Быстрое обновление статуса, цены, размеров и наличия товара
    Принимает JSON: { price?, in_stock?, sizes?, discount_percent? }
    """

    def patch(self, request, pk):
        product = get_object_or_404(Product, pk=pk)

        # Обновляем только переданные поля
        if 'price' in request.data:
            try:
                product.price = int(request.data['price'])
            except (ValueError, TypeError):
                return Response({'error': 'Неверный формат цены'}, status=status.HTTP_400_BAD_REQUEST)

        if 'discount_percent' in request.data:
            try:
                discount = int(request.data['discount_percent'])
                if 0 <= discount <= 100:
                    product.discount_percent = discount
                else:
                    return Response({'error': 'Скидка должна быть от 0 до 100'}, status=status.HTTP_400_BAD_REQUEST)
            except (ValueError, TypeError):
                return Response({'error': 'Неверный формат скидки'}, status=status.HTTP_400_BAD_REQUEST)

        if 'in_stock' in request.data:
            product.in_stock = bool(request.data['in_stock'])

        if 'sizes' in request.data:
            sizes = request.data['sizes']
            if isinstance(sizes, list):
                product.sizes = sizes
            else:
                return Response({'error': 'Размеры должны быть массивом'}, status=status.HTTP_400_BAD_REQUEST)

        product.save()

        serializer = ProductSerializer(product)
        return Response(serializer.data, status=status.HTTP_200_OK)
