from django.contrib import admin
from .models import GphDocument, ActDocument
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
