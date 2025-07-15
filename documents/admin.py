from django.contrib import admin
from .models import GphDocument
from django.utils.html import format_html, mark_safe

@admin.register(GphDocument)
class GphDocumentAdmin(admin.ModelAdmin):
    list_display = ('doc_id', 'user', 'full_name', 'start_date', 'end_date', 'created_at', 'file_path', 'approvers_statuses')
    search_fields = ('doc_id', 'full_name', 'user__username')
    list_filter = ('doc_type', 'created_at')

    def approvers_statuses(self, obj):
        if not obj.approvers:
            return '-'
        html = ''
        for appr in obj.approvers:
            status = appr.get('status', 'ожидание')
            username = appr.get('username', '')
            full_name = appr.get('full_name', '')
            if status == 'ожидание':
                color = '#888'
            elif status == 'согласовано':
                color = 'green'
            elif status == 'отклонено':
                color = 'red'
            else:
                color = '#888'
            html += f'<div style="margin-bottom:2px;"><b>{full_name or username}</b>: <span style="color:{color};font-weight:bold;">{status}</span></div>'
        return mark_safe(html)
    approvers_statuses.short_description = 'Статусы согласующих'
