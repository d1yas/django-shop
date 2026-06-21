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

    class Meta:
        model  = Product
        fields = [
            'id',
            'name',
            'category',
            'description',
            'price',
            'badge',
            'in_stock',
            'images_raw',
            'sizes',
        ]

    def _parse_images(self, raw: str) -> list[str]:
        return [s.strip() for s in raw.split(',') if s.strip()] if raw else ['👕']

    def create(self, validated_data):
        raw = validated_data.pop('images_raw', '')
        validated_data['images'] = self._parse_images(raw)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        raw = validated_data.pop('images_raw', None)
        if raw is not None:
            validated_data['images'] = self._parse_images(raw)
        return super().update(instance, validated_data)
