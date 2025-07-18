from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
import json
from datetime import datetime
from django.db.models import JSONField  

User = get_user_model()

class GphDocument(models.Model):
    """Модель для хранения ГПХ договоров"""
    
    DOCUMENT_TYPES = [
        ('gph', 'ГПХ договор'),
        ('act', 'Акт выполненных работ'),
    ]
    
    doc_id = models.CharField(max_length=50, unique=True, verbose_name='ID документа')
    doc_type = models.CharField(max_length=10, choices=DOCUMENT_TYPES, verbose_name='Тип документа')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь')
    full_name = models.CharField(max_length=255, verbose_name='ФИО исполнителя')
    start_date = models.DateField(verbose_name='Дата начала')
    end_date = models.DateField(verbose_name='Дата окончания')
    file_path = models.CharField(max_length=255, verbose_name='Публичная ссылка на файл')
    actions = models.JSONField(default=list, verbose_name='Этапы согласования и подписания')
    attachments = models.JSONField(default=list, blank=True, verbose_name='Вложения')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания (секунды)')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    class Meta:
        verbose_name = 'Договор ГПХ'
        verbose_name_plural = 'Договоры ГПХ'
        db_table = 'gph_documents'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.doc_id} - {self.get_doc_type_display()}"
    
    def save(self, *args, **kwargs):
        if not self.doc_id:
            self.doc_id = self.generate_unique_id()
        super().save(*args, **kwargs)
    
    def generate_unique_id(self):
        from datetime import datetime
        import random
        current_year = str(datetime.now().year)[2:]
        current_month = str(datetime.now().month).zfill(2)
        current_day = str(datetime.now().day).zfill(2)
        current_time = datetime.now().strftime("%H%M%S")
        max_attempts = 100
        for attempt in range(max_attempts):
            random_suffix = str(random.randint(1000, 9999))
            doc_id = f"{current_year}{current_month}{current_day}-{current_time}-{random_suffix}"
            if not GphDocument.objects.filter(doc_id=doc_id).exists():
                return doc_id
        additional_suffix = str(random.randint(10000, 99999))
        return f"{current_year}{current_month}{current_day}-{current_time}-{random_suffix}-{additional_suffix}"


class ActDocument(models.Model):
    """Модель для хранения актов выполненных работ"""
    
    act_id = models.CharField(max_length=50, unique=True, verbose_name='ID акта')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Исполнитель')
    gph_document = models.ForeignKey(GphDocument, on_delete=models.CASCADE, verbose_name='ГПХ договор')
    full_name = models.CharField(max_length=255, verbose_name='ФИО исполнителя')
    phone_number = models.CharField(max_length=20, verbose_name='Номер телефона')
    iin = models.CharField(max_length=12, verbose_name='ИИН')
    # Основные даты акта (могут быть общими для всех работ)
    start_date = models.DateField(verbose_name='Дата начала работ', null=True, blank=True)
    end_date = models.DateField(verbose_name='Дата окончания работ', null=True, blank=True)
    # Массив работ/услуг
    works = models.JSONField(default=list, verbose_name='Список работ/услуг')
    # Итоговые суммы
    total_quantity = models.CharField(max_length=50, verbose_name='Общее количество', default='0')
    total_sum = models.CharField(max_length=50, verbose_name='Общая цена за единицу', default='0')
    total_amount = models.CharField(max_length=50, verbose_name='Общая стоимость', default='0')
    file_path = models.CharField(max_length=255, verbose_name='Публичная ссылка на файл')
    actions = models.JSONField(default=list, verbose_name='Этапы согласования и подписания')
    attachments = models.JSONField(default=list, blank=True, verbose_name='Вложения')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    # Оставляем старые поля для обратной совместимости (deprecated)
    quantity = models.CharField(max_length=50, verbose_name='Количество (устарело)', default='', blank=True)
    unit_price = models.CharField(max_length=50, verbose_name='Цена за единицу (устарело)', default='', blank=True)
    amount = models.CharField(max_length=50, verbose_name='Общая стоимость (устарело)', default='', blank=True)
    text = models.CharField(max_length=255, verbose_name='Наименование работ (устарело)', default='', blank=True)
    unit = models.CharField(max_length=50, verbose_name='Единица измерения (устарело)', default='', blank=True)
    additional_text = models.CharField(max_length=255, verbose_name='Сведения об отчете (устарело)', blank=True, default='')
    
    class Meta:
        verbose_name = 'Акт выполненных работ'
        verbose_name_plural = 'Акты выполненных работ'
        db_table = 'act_documents'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.act_id} - {self.full_name}"
    
    def save(self, *args, **kwargs):
        if not self.act_id:
            self.act_id = self.generate_unique_id()
        super().save(*args, **kwargs)
    
    def generate_unique_id(self):
        from datetime import datetime
        import random
        current_year = str(datetime.now().year)[2:]
        current_month = str(datetime.now().month).zfill(2)
        current_day = str(datetime.now().day).zfill(2)
        current_time = datetime.now().strftime("%H%M%S")
        max_attempts = 100
        for attempt in range(max_attempts):
            random_suffix = str(random.randint(1000, 9999))
            act_id = f"{current_year}{current_month}{current_day}-{current_time}-{random_suffix}"
            if not ActDocument.objects.filter(act_id=act_id).exists():
                return act_id
        additional_suffix = str(random.randint(10000, 99999))
        return f"{current_year}{current_month}{current_day}-{current_time}-{random_suffix}-{additional_suffix}"


class ActPackage(models.Model):
    """Модель для хранения пакетов актов выполненных работ"""
    
    PACKAGE_STATUS = [
        ('draft', 'Черновик'),
        ('ready', 'Готов к подписанию'),
        ('signed', 'Подписан'),
    ]
    
    package_id = models.CharField(max_length=50, unique=True, verbose_name='ID пакета')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Создатель пакета')
    acts = models.JSONField(default=list, verbose_name='Список ID актов в пакете')
    status = models.CharField(max_length=20, choices=PACKAGE_STATUS, default='draft', verbose_name='Статус пакета')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    class Meta:
        verbose_name = 'Пакет актов'
        verbose_name_plural = 'Пакеты актов'
        db_table = 'act_packages'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Пакет {self.package_id} - {self.get_status_display()}"
    
    def save(self, *args, **kwargs):
        if not self.package_id:
            self.package_id = self.generate_unique_id()
        super().save(*args, **kwargs)
    
    def generate_unique_id(self):
        from datetime import datetime
        import random
        current_year = str(datetime.now().year)[2:]
        current_month = str(datetime.now().month).zfill(2)
        current_day = str(datetime.now().day).zfill(2)
        current_time = datetime.now().strftime("%H%M%S")
        max_attempts = 100
        for attempt in range(max_attempts):
            random_suffix = str(random.randint(1000, 9999))
            package_id = f"ПАКЕТ-{current_year}{current_month}{current_day}-{current_time}-{random_suffix}"
            if not ActPackage.objects.filter(package_id=package_id).exists():
                return package_id
        additional_suffix = str(random.randint(10000, 99999))
        return f"ПАКЕТ-{current_year}{current_month}{current_day}-{current_time}-{random_suffix}-{additional_suffix}"
    
    @property
    def acts_count(self):
        """Количество актов в пакете"""
        return len(self.acts)
    
    @property
    def total_amount(self):
        """Общая сумма всех актов в пакете"""
        total = 0
        for act_id in self.acts:
            try:
                act = ActDocument.objects.get(act_id=act_id)
                amount = float(act.amount) if act.amount else 0
                total += amount
            except ActDocument.DoesNotExist:
                continue
        return total

