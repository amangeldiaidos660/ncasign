from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.conf import settings
from django.contrib.auth import get_user_model
import os
from docx import Document as DocxDocument
import mammoth
from .forms import GPHContractForm
from .models import GphDocument
from datetime import datetime
import dropbox
import io
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

# Универсальный декоратор для проверки ролей (копия из ncasign/views.py)
from functools import wraps

def role_required(roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.role not in roles:
                return render(request, '403.html', status=403)
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

@login_required
@role_required([1, 5, 2])  # Админ, Редактор, Подписант (только просмотр)
def gph_list(request):
    from .models import GphDocument
    docs = GphDocument.objects.select_related('user').order_by('-created_at')
    return render(request, 'documents/gph_list.html', {'docs': docs})

@login_required
@role_required([1, 5, 2])  # Админ, Редактор, Подписант (только просмотр)
def acts_list(request):
    return render(request, 'documents/acts_list.html')

@login_required
@role_required([1, 5])  # Только Админ и Редактор могут создавать документы
def gph_create(request):
    """Создание нового ГПХ договора"""
    if request.method == 'POST':
        form = GPHContractForm(request.POST)
        if form.is_valid():
            # Здесь будет логика обработки формы
            pass
    else:
        form = GPHContractForm()
    
    return render(request, 'documents/gph_create.html', {
        'form': form
    })

@login_required
@role_required([1, 5])  # Только Админ и Редактор могут делать предпросмотр
def gph_preview(request):
    if request.method == 'POST':
        data = {
            'full_name': '',
            'start_date': request.POST.get('start_date', ''),
            'end_date': request.POST.get('end_date', ''),
        }
        executor_id = request.POST.get('executor', '')
        if executor_id:
            User = get_user_model()
            try:
                executor = User.objects.get(username=executor_id, role=4)
                data['full_name'] = executor.full_name
            except User.DoesNotExist:
                pass
        try:
            template_path = os.path.join(settings.BASE_DIR, 'static', 'docs', 'gph.docx')
            if os.path.exists(template_path):
                doc = DocxDocument(template_path)
                def replace_placeholders(text):
                    text = text.replace('{{full_name}}', f'<strong>{data["full_name"]}</strong>' if data['full_name'] else '')
                    text = text.replace('{{doc_id}}', '<em>будет сгенерирован при сохранении</em>')
                    text = text.replace('{{year}}', '<strong>2025</strong>')
                    text = text.replace('{{current_date}}', '<strong>13.07.2025</strong>')
                    text = text.replace('{{start_date}}', f'<strong>{data["start_date"]}</strong>' if data['start_date'] else '')
                    text = text.replace('{{end_date}}', f'<strong>{data['end_date']}</strong>' if data['end_date'] else '')
                    text = text.replace('{{nca_datas}}', '<strong>Данные подписи НУЦ</strong>')
                    return text
                for paragraph in doc.paragraphs:
                    paragraph.text = replace_placeholders(paragraph.text)
                for table in doc.tables:
                    for row in table.rows:
                        for cell in row.cells:
                            for paragraph in cell.paragraphs:
                                paragraph.text = replace_placeholders(paragraph.text)
                preview_html = '<div style="padding: 20px; background: white; border-radius: 10px; font-family: Arial, sans-serif;">'
                preview_html += '<div style="border: 1px solid #ddd; padding: 20px; background: #f9f9f9;">'
                for paragraph in doc.paragraphs:
                    if paragraph.text.strip():
                        processed_text = replace_placeholders(paragraph.text)
                        preview_html += f'<p style="margin-bottom: 10px;">{processed_text}</p>'
                for table in doc.tables:
                    preview_html += '<table style="width:100%; margin-bottom: 20px; border-collapse: collapse;">'
                    for row in table.rows:
                        preview_html += '<tr>'
                        for cell in row.cells:
                            cell_texts = []
                            for p in cell.paragraphs:
                                if p.text.strip():
                                    processed_text = replace_placeholders(p.text)
                                    cell_texts.append(processed_text)
                            cell_text = '<br>'.join(cell_texts)
                            preview_html += f'<td style="border:1px solid #ccc; padding:5px;">{cell_text}</td>'
                        preview_html += '</tr>'
                    preview_html += '</table>'
                preview_html += '</div>'
                preview_html += '</div>'
                return JsonResponse({'success': True, 'preview_html': preview_html})
            else:
                preview_html = f"""
                <div style=\"padding: 20px; background: white; border-radius: 10px;\">
                    <h3>Файл шаблона gph.docx не найден</h3>
                </div>
                """
                return JsonResponse({'success': True, 'preview_html': preview_html})
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Ошибка загрузки документа: {str(e)}'})
    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})

@login_required
@role_required([1, 5])  # Только Админ и Редактор могут сохранять документы
def gph_save(request):
    """Сохранение ГПХ договора и загрузка в Dropbox"""
    if request.method == 'POST':
        form = GPHContractForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            user = data['executor']
            start_date = data['start_date']
            end_date = data['end_date']
            # Согласующие
            approvers = []
            if 'approvers' in request.POST:
                approver_usernames = request.POST.getlist('approvers')
                User = get_user_model()
                for username in approver_usernames:
                    try:
                        appr = User.objects.get(username=username, role=3)
                        approvers.append({
                            'username': appr.username,
                            'full_name': appr.full_name,
                            'status': 'ожидание'
                        })
                    except User.DoesNotExist:
                        pass
            # 1. Создаем запись в БД (генерируется doc_id)
            document = GphDocument.objects.create(
                doc_type='gph',
                user=user,
                full_name=user.full_name,
                start_date=start_date,
                end_date=end_date,
                file_path='',  # временно
                approvers=approvers
            )
            doc_id = document.doc_id
            # 2. Формируем docx с подстановкой всех данных
            from docx import Document as DocxDocument
            import io
            template_path = os.path.join(settings.BASE_DIR, 'static', 'docs', 'gph.docx')
            doc = DocxDocument(template_path)
            def replace_placeholders(text):
                text = text.replace('{{full_name}}', user.full_name)
                text = text.replace('{{doc_id}}', doc_id)
                text = text.replace('{{year}}', str(document.created_at.year))
                text = text.replace('{{current_date}}', document.created_at.strftime('%d.%m.%Y %H:%M:%S'))
                text = text.replace('{{start_date}}', str(start_date))
                text = text.replace('{{end_date}}', str(end_date))
                text = text.replace('{{nca_datas}}', 'Данные подписи НУЦ')
                return text
            for paragraph in doc.paragraphs:
                paragraph.text = replace_placeholders(paragraph.text)
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for paragraph in cell.paragraphs:
                            paragraph.text = replace_placeholders(paragraph.text)
            # 3. Сохраняем docx в память
            file_stream = io.BytesIO()
            doc.save(file_stream)
            file_stream.seek(0)
            # 4. Загружаем в Dropbox
            dbx = dropbox.Dropbox(settings.DROPBOX_TOKEN)
            dropbox_folder = f"/ncasign/{user.username}/"
            dropbox_filename = f"ГПХ-{user.username}-{document.created_at.strftime('%Y%m%d-%H%M%S')}.docx"
            dropbox_path = dropbox_folder + dropbox_filename
            dbx.files_upload(file_stream.read(), dropbox_path, mode=dropbox.files.WriteMode.overwrite)
            # 5. Получаем публичную ссылку
            shared_link_metadata = dbx.sharing_create_shared_link_with_settings(dropbox_path)
            public_url = shared_link_metadata.url.replace('?dl=0', '?raw=1')
            # 6. Сохраняем ссылку в модель
            document.file_path = public_url
            document.save()
            return JsonResponse({'success': True, 'file_path': public_url, 'doc_id': doc_id})
        else:
            return JsonResponse({'success': False, 'error': 'Неверные данные формы'})
    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})

@login_required
@role_required([1, 5, 2, 3])  # Все роли, кроме гостей, могут видеть свои уведомления
def api_pending_approvals(request):
    """API: Список документов, требующих согласования текущим пользователем"""
    user = request.user
    docs = GphDocument.objects.all().order_by('-created_at')
    pending = []
    for doc in docs:
        for appr in doc.approvers:
            if appr['username'] == user.username and appr['status'] not in ['согласовано', 'отклонено']:
                pending.append({
                    'doc_id': doc.doc_id,
                    'created_at': doc.created_at.strftime('%d.%m.%Y %H:%M:%S'),
                    'file_path': doc.file_path,
                    'status': appr['status'],
                    'full_name': doc.full_name,
                    'start_date': str(doc.start_date),
                    'end_date': str(doc.end_date),
                })
                break
    return JsonResponse({'success': True, 'pending': pending})

@csrf_exempt
@require_POST
@login_required
@role_required([1, 5, 2, 3])  # Все роли, кроме гостей, могут согласовывать
def api_approve_document(request):
    """API: Согласовать или отклонить документ для текущего пользователя"""
    import json
    user = request.user
    try:
        data = json.loads(request.body.decode('utf-8'))
        doc_id = data.get('doc_id')
        action = data.get('action')  # 'approve' или 'reject'
        if action not in ['approve', 'reject']:
            return JsonResponse({'success': False, 'error': 'Некорректное действие'})
        doc = GphDocument.objects.get(doc_id=doc_id)
        updated = False
        for appr in doc.approvers:
            if appr['username'] == user.username:
                appr['status'] = 'согласовано' if action == 'approve' else 'отклонено'
                appr['decision_time'] = timezone.now().strftime('%d.%m.%Y %H:%M:%S')
                updated = True
        if updated:
            doc.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'error': 'Вы не являетесь согласующим'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@role_required([1, 5, 2, 3])  # Все роли, кроме гостей, могут видеть историю
def api_user_history(request):
    """API: Все ГПХ, где пользователь — исполнитель или согласующий (любой статус)"""
    user = request.user
    docs = GphDocument.objects.all().order_by('-created_at')
    history = []
    for doc in docs:
        is_executor = (doc.user == user)
        is_approver = any(appr['username'] == user.username for appr in doc.approvers)
        if is_executor or is_approver:
            # Найти статус для этого пользователя (если он согласующий)
            user_status = None
            for appr in doc.approvers:
                if appr['username'] == user.username:
                    user_status = appr['status']
            history.append({
                'doc_id': doc.doc_id,
                'created_at': doc.created_at.strftime('%d.%m.%Y %H:%M:%S'),
                'file_path': doc.file_path,
                'status': user_status if user_status else ('исполнитель' if is_executor else ''),
                'full_name': doc.full_name,
                'start_date': str(doc.start_date),
                'end_date': str(doc.end_date),
            })
    return JsonResponse({'success': True, 'history': history})
