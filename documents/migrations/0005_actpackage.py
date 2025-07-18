# Generated by Django 5.2.4 on 2025-07-16 05:37

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0004_actdocument'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ActPackage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('package_id', models.CharField(max_length=50, unique=True, verbose_name='ID пакета')),
                ('acts', models.JSONField(default=list, verbose_name='Список ID актов в пакете')),
                ('status', models.CharField(choices=[('draft', 'Черновик'), ('ready', 'Готов к подписанию'), ('signed', 'Подписан')], default='draft', max_length=20, verbose_name='Статус пакета')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Дата обновления')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Создатель пакета')),
            ],
            options={
                'verbose_name': 'Пакет актов',
                'verbose_name_plural': 'Пакеты актов',
                'db_table': 'act_packages',
                'ordering': ['-created_at'],
            },
        ),
    ]
