from rest_framework import serializers
from .models import Product


class ProductSerializer(serializers.ModelSerializer):
    """
    Сериализатор для публичного API (/api/products/).
    Возвращает все поля, нужные фронтенду index.html.
    """

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


class ProductWriteSerializer(serializers.ModelSerializer):
    """
    Сериализатор для записи (admin panel).
    images_raw — строка через запятую, удобная для HTML-формы panel.html.
    sizes — список строк (приходит из чекбоксов).
    """
    images_raw = serializers.CharField(
        write_only=True, required=False, allow_blank=True, default=''
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
            'images_raw',
            'sizes',
            'sizes_raw',
        ]

    def _parse_images(self, raw: str) -> list[str]:
        return [s.strip() for s in raw.split(',') if s.strip()] if raw else ['👕']

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
        raw = validated_data.pop('images_raw', '')
        validated_data['images'] = self._parse_images(raw)
        validated_data = self._merge_sizes(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        raw = validated_data.pop('images_raw', None)
        if raw is not None:
            validated_data['images'] = self._parse_images(raw)
        validated_data = self._merge_sizes(validated_data)
        return super().update(instance, validated_data)
