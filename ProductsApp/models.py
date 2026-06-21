import json
from django.db import models


class Product(models.Model):
    BADGE_CHOICES = [
        ('',    'Нет'),
        ('new', 'Новинка'),
        ('hot', 'Хит'),
    ]

    name        = models.CharField('Название', max_length=255)
    category    = models.CharField('Категория', max_length=100)
    description = models.TextField('Описание', blank=True, default='')
    price       = models.PositiveIntegerField('Цена (сум)')
    badge       = models.CharField('Значок', max_length=10, choices=BADGE_CHOICES, blank=True, default='')
    in_stock    = models.BooleanField('В наличии', default=True)

    # SQLite не поддерживает ArrayField — храним как JSON-строку
    # Пример значения в БД: '["https://…/1.jpg", "https://…/2.jpg"]'
    _images = models.TextField('Фото (JSON)', db_column='images', blank=True, default='[]')
    _sizes  = models.TextField('Размеры (JSON)', db_column='sizes', blank=True, default='[]')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ── Python-свойства: снаружи работаем со списками ──

    @property
    def images(self) -> list[str]:
        try:
            return json.loads(self._images) or ['👕']
        except (ValueError, TypeError):
            return ['👕']

    @images.setter
    def images(self, value: list[str]):
        self._images = json.dumps(value, ensure_ascii=False)

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