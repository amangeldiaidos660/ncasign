from django.contrib import admin
from .models import GphDocument, ActDocument, ActPackage
from django.utils.html import format_html, mark_safe

@admin.register(GphDocument)
class GphDocumentAdmin(admin.ModelAdmin):
    list_display = ['doc_id', 'doc_type', 'user', 'full_name', 'start_date', 'end_date', 'created_at']
    list_filter = ['doc_type', 'created_at']
    search_fields = ['doc_id', 'full_name', 'user__username']
    readonly_fields = ['doc_id', 'created_at', 'updated_at']
    ordering = ['-created_at']

@admin.register(ActDocument)
class ActDocumentAdmin(admin.ModelAdmin):
    list_display = ['act_id', 'user', 'full_name', 'start_date', 'end_date', 'amount', 'created_at']
    list_filter = ['created_at', 'start_date', 'end_date']
    search_fields = ['act_id', 'full_name', 'user__username', 'gph_document__doc_id']
    readonly_fields = ['act_id', 'created_at', 'updated_at']
    ordering = ['-created_at']

@admin.register(ActPackage)
class ActPackageAdmin(admin.ModelAdmin):
    list_display = ['package_id', 'created_by', 'acts_count_display', 'total_amount_display', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['package_id', 'created_by__username', 'created_by__full_name']
    readonly_fields = ['package_id', 'created_at', 'updated_at', 'acts_count_display', 'total_amount_display', 'acts_list_display']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('package_id', 'created_by', 'status')
        }),
        ('Акты в пакете', {
            'fields': ('acts', 'acts_count_display', 'total_amount_display', 'acts_list_display'),
            'classes': ('collapse',)
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def acts_count_display(self, obj):
        """Отображение количества актов в пакете"""
        count = obj.acts_count
        return format_html('<span style="color: #007bff; font-weight: bold;">{} актов</span>', count)
    acts_count_display.short_description = 'Количество актов'
    
    def total_amount_display(self, obj):
        """Отображение общей суммы пакета"""
        amount = obj.total_amount
        try:
            amount_float = float(amount)
            return format_html('<span style="color: #28a745; font-weight: bold;">{:.2f} ₸</span>', amount_float)
        except (ValueError, TypeError):
            return format_html('<span style="color: #dc3545; font-weight: bold;">Ошибка суммы</span>')
    total_amount_display.short_description = 'Общая сумма'
    
    def acts_list_display(self, obj):
        """Отображение списка актов в пакете"""
        if not obj.acts:
            return format_html('<span style="color: #6c757d;">Пакет пуст</span>')
        
        acts_html = []
        for act_id in obj.acts:
            try:
                act = ActDocument.objects.get(act_id=act_id)
                acts_html.append(
                    format_html(
                        '<div style="margin-bottom: 8px; padding: 8px; background: #f8f9fa; border-radius: 4px;">'
                        '<strong>{}</strong> - {} ({})<br>'
                        '<small style="color: #6c757d;">Даты: {} - {} | Сумма: {} ₸</small>'
                        '</div>',
                        act.act_id,
                        act.full_name,
                        act.user.username,
                        act.start_date,
                        act.end_date,
                        act.amount
                    )
                )
            except ActDocument.DoesNotExist:
                acts_html.append(
                    format_html(
                        '<div style="margin-bottom: 8px; padding: 8px; background: #f8d7da; border-radius: 4px; color: #721c24;">'
                        '<strong>{}</strong> - Акт не найден'
                        '</div>',
                        act_id
                    )
                )
        
        # Объединяем все HTML элементы
        combined_html = ''
        for html_element in acts_html:
            combined_html += str(html_element)
        
        return mark_safe(combined_html)
    acts_list_display.short_description = 'Список актов'
    
    def get_queryset(self, request):
        """Оптимизация запросов"""
        return super().get_queryset(request).select_related('created_by')
