# Generated by Django 5.2.4 on 2025-07-17 16:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0008_actdocument_additional_text_actdocument_text_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='actdocument',
            name='attachments',
            field=models.JSONField(blank=True, default=list, verbose_name='Вложения'),
        ),
        migrations.AddField(
            model_name='gphdocument',
            name='attachments',
            field=models.JSONField(blank=True, default=list, verbose_name='Вложения'),
        ),
    ]
