# Generated migration for discount_percent field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ProductsApp', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='discount_percent',
            field=models.PositiveSmallIntegerField(default=0, verbose_name='Скидка (%)'),
        ),
    ]
