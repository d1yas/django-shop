from rest_framework import serializers
from .models import Product, ProductImage


class ProductImageSerializer(serializers.ModelSerializer):
    """Сериализатор для изображений товара"""

    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'order']


class ProductSerializer(serializers.ModelSerializer):
    """
    Сериализатор для публичного API (/api/products/).
    Возвращает все поля, нужные фронтенду index.html.
    """
    images = serializers.SerializerMethodField()

    class Meta:
        model  = Product
        fields = [
            'id',
            'name',
            'category',
            'description',
            'price',
            'discount_percent',
            'badge',
            'in_stock',
            'images',
            'sizes',
        ]

    def get_images(self, obj):
        """Возвращает список URL изображений"""
        images = obj.product_images.all().order_by('order')
        if not images:
            return ['👕']
        return [img.image.url for img in images]


class ProductWriteSerializer(serializers.ModelSerializer):
    """
    Сериализатор для записи (admin panel).
    Обрабатывает загрузку файлов изображений (минимум 1, максимум 6).
    sizes — список строк (приходит из чекбоксов).
    """
    images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        allow_empty=True
    )
    sizes = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    sizes_raw = serializers.CharField(
        write_only=True, required=False, allow_blank=True, default=''
    )
    discount_percent = serializers.IntegerField(
        required=False, min_value=0, max_value=100, default=0
    )

    class Meta:
        model  = Product
        fields = [
            'id',
            'name',
            'category',
            'description',
            'price',
            'discount_percent',
            'badge',
            'in_stock',
            'images',
            'sizes',
            'sizes_raw',
        ]

    def validate_images(self, value):
        """Валидация: минимум 1, максимум 6 изображений (только при создании)"""
        if value and len(value) > 6:
            raise serializers.ValidationError("Максимум 6 изображений")
        return value

    def _parse_sizes(self, raw: str) -> list[str]:
        return [s.strip() for s in raw.split(',') if s.strip()] if raw else []

    def _merge_sizes(self, validated_data: dict) -> dict:
        raw = validated_data.pop('sizes_raw', '')
        sizes = validated_data.get('sizes', []) or []
        merged = []
        for size in sizes + self._parse_sizes(raw):
            if size and size not in merged:
                merged.append(size)
        validated_data['sizes'] = merged
        return validated_data

    def create(self, validated_data):
        images_data = validated_data.pop('images', [])

        # Валидация при создании - обязательно минимум 1 изображение
        if not images_data or len(images_data) < 1:
            raise serializers.ValidationError({'images': 'Необходимо загрузить минимум 1 изображение'})

        validated_data = self._merge_sizes(validated_data)

        # Создаем товар
        product = super().create(validated_data)

        # Создаем изображения
        for idx, image_file in enumerate(images_data):
            ProductImage.objects.create(
                product=product,
                image=image_file,
                order=idx
            )

        return product

    def update(self, instance, validated_data):
        images_data = validated_data.pop('images', None)
        validated_data = self._merge_sizes(validated_data)

        # Обновляем товар
        instance = super().update(instance, validated_data)

        # Если переданы новые изображения, заменяем старые
        if images_data is not None and len(images_data) > 0:
            # Удаляем старые изображения (файлы тоже удаляются)
            for img in instance.product_images.all():
                img.image.delete(save=False)  # Удаляем файл с диска
                img.delete()  # Удаляем запись из БД

            # Создаем новые
            for idx, image_file in enumerate(images_data):
                ProductImage.objects.create(
                    product=instance,
                    image=image_file,
                    order=idx
                )

        return instance
