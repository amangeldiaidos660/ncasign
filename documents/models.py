from django.db import models
from django.contrib.auth import get_user_model
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
    approvers = models.JSONField(default=list, verbose_name='Согласующие')
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