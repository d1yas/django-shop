import json
from django.db import models
from django.core.exceptions import ValidationError


class Product(models.Model):
    BADGE_CHOICES = [
        ('',    'Нет'),
        ('new', 'Новинка'),
        ('hot', 'Хит'),
    ]

    name             = models.CharField('Название', max_length=255)
    category         = models.CharField('Категория', max_length=100)
    description      = models.TextField('Описание', blank=True, default='')
    price            = models.PositiveIntegerField('Цена (сум)')
    discount_percent = models.PositiveSmallIntegerField('Скидка (%)', default=0)
    badge            = models.CharField('Значок', max_length=10, choices=BADGE_CHOICES, blank=True, default='')
    in_stock         = models.BooleanField('В наличии', default=True)

    _sizes  = models.TextField('Размеры (JSON)', db_column='sizes', blank=True, default='[]')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ── Python-свойства: снаружи работаем со списками ──

    @property
    def images(self) -> list[str]:
        """Возвращает список URL изображений из связанных ProductImage"""
        return [img.image.url for img in self.product_images.all().order_by('order')]

    @property
    def sizes(self) -> list[str]:
        try:
            return json.loads(self._sizes) or []
        except (ValueError, TypeError):
            return []

    @sizes.setter
    def sizes(self, value: list[str]):
        self._sizes = json.dumps(value, ensure_ascii=False)

    class Meta:
        verbose_name        = 'Товар'
        verbose_name_plural = 'Товары'
        ordering            = ['-created_at']

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    """
    Модель для хранения изображений товара.
    Каждый товар может иметь от 1 до 6 изображений.
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='product_images',
        verbose_name='Товар'
    )
    image = models.ImageField(
        upload_to='products/%Y/%m/%d/',
        verbose_name='Изображение'
    )
    order = models.PositiveSmallIntegerField(
        default=0,
        verbose_name='Порядок'
    )

    class Meta:
        verbose_name = 'Изображение товара'
        verbose_name_plural = 'Изображения товаров'
        ordering = ['order']

    def __str__(self):
        return f"{self.product.name} - Изображение {self.order}"

    def delete(self, *args, **kwargs):
        # Удаляем файл изображения с диска при удалении записи
        if self.image:
            self.image.delete(save=False)
        super().delete(*args, **kwargs)