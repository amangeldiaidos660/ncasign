from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.contrib.auth import get_user_model
import os
from docx import Document as DocxDocument
from .forms import GPHContractForm, ActForm
from .models import GphDocument, ActDocument, ActPackage
from datetime import datetime
import dropbox
import io
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.views.decorators.http import require_GET
import json

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
@role_required([1, 5])  # Только Админ и Редактор могут создавать акты
def act_create(request):
    """Создание акта с формой и предпросмотром шаблона"""
    if request.method == 'POST':
        form = ActForm(request.POST)
        if form.is_valid():
            # Здесь будет логика обработки формы
            pass
    else:
        form = ActForm()
    
    # Получаем данные пользователей для JavaScript
    User = get_user_model()
    users_data = {}
    for user in User.objects.filter(role=4):
        users_data[user.username] = {
            'full_name': user.full_name or '',
            'phone_number': user.phone_number or '',
            'iin': user.iin or '',
        }
    
    import json
    users_data_json = json.dumps(users_data, ensure_ascii=False)
    
    return render(request, 'documents/act_create.html', {
        'form': form,
        'users_data_json': users_data_json
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
@role_required([1, 5])  # Только Админ и Редактор могут делать предпросмотр акта
def act_preview(request):
    """Предпросмотр шаблона акта с подстановкой данных"""
    try:
        html_path = os.path.join(settings.BASE_DIR, 'static', 'docs', 'act.html')
        if not os.path.exists(html_path):
            return JsonResponse({'success': False, 'error': 'Файл шаблона act.html не найден'})
        
        with open(html_path, 'r', encoding='utf-8') as file:
            html_content = file.read()
        
        # Если это POST запрос, подставляем данные из формы
        if request.method == 'POST':
            data = {
                'full_name': request.POST.get('full_name', ''),
                'phone_number': request.POST.get('phone_number', ''),
                'iin': request.POST.get('iin', ''),
                'doc_id': request.POST.get('doc_id', ''),
                'act_id': '',  # Оставляем пустым, будем генерировать на бэкенде
                'current_date': timezone.now().strftime('%d.%m.%Y'),
                'start_date': request.POST.get('start_date', ''),
                'end_date': request.POST.get('end_date', ''),
                'quantity': request.POST.get('quantity', ''),
                'unit_price': request.POST.get('unit_price', ''),
                'amount': request.POST.get('amount', ''),
                'created_date': '',  # Будем заполнять из ГПХ договора
            }
            
            # Если указан исполнитель, ищем его последний ГПХ договор только для ID
            executor_username = request.POST.get('executor', '')
            if executor_username and not data['doc_id']:
                try:
                    User = get_user_model()
                    user = User.objects.get(username=executor_username, role=4)
                    # Ищем последний ГПХ договор пользователя только для получения ID
                    last_gph = GphDocument.objects.filter(
                        user=user, 
                        doc_type='gph'
                    ).order_by('-created_at').first()
                    
                    if last_gph:
                        data['doc_id'] = last_gph.doc_id
                        data['created_date'] = last_gph.created_at.strftime('%d.%m.%Y') if last_gph.created_at else ''
                except User.DoesNotExist:
                    pass
            
            # Вычисляем общую стоимость (количество × цена за единицу)
            try:
                quantity = float(data['quantity']) if data['quantity'] else 0
                unit_price = float(data['unit_price']) if data['unit_price'] else 0
                if quantity > 0 and unit_price > 0:
                    data['amount'] = f"{quantity * unit_price:.2f}"
                else:
                    data['amount'] = ''
            except (ValueError, ZeroDivisionError):
                data['amount'] = ''
            
            # Подставляем данные в HTML
            html_content = html_content.replace('{{full_name}}', f'<strong>{data["full_name"]}</strong>' if data['full_name'] else '')
            html_content = html_content.replace('{{phone_number}}', f'<strong>{data["phone_number"]}</strong>' if data['phone_number'] else '')
            html_content = html_content.replace('{{iin}}', f'<strong>{data["iin"]}</strong>' if data['iin'] else '')
            html_content = html_content.replace('{{doc_id}}', f'<strong>{data["doc_id"]}</strong>' if data['doc_id'] else '')
            html_content = html_content.replace('{{created_date}}', f'<strong>{data["created_date"]}</strong>' if data['created_date'] else '')
            html_content = html_content.replace('{{act_id}}', f'<strong>{data["act_id"]}</strong>' if data['act_id'] else '')
            html_content = html_content.replace('{{current_date}}', f'<strong>{data["current_date"]}</strong>')
            html_content = html_content.replace('{{start_date}}', f'<strong>{data["start_date"]}</strong>' if data['start_date'] else '')
            html_content = html_content.replace('{{end_date}}', f'<strong>{data["end_date"]}</strong>' if data['end_date'] else '')
            html_content = html_content.replace('{{quantity}}', f'<strong>{data["quantity"]}</strong>' if data['quantity'] else '')
            html_content = html_content.replace('{{sum}}', f'<strong>{data["unit_price"]}</strong>' if data['unit_price'] else '')
            html_content = html_content.replace('{{amount}}', f'<strong>{data["amount"]}</strong>' if data['amount'] else '')
            
            # Вычисляем итоговые значения
            res_quantity = data['quantity'] if data['quantity'] else ''
            res_amount = data['amount'] if data['amount'] else ''
            html_content = html_content.replace('{{res_quantitu}}', f'<strong>{res_quantity}</strong>')
            html_content = html_content.replace('{{res}}', f'<strong>{res_amount}</strong>')
        else:
            # Для GET запроса показываем пустой шаблон
            html_content = html_content.replace('{{full_name}}', '')
            html_content = html_content.replace('{{phone_number}}', '')
            html_content = html_content.replace('{{iin}}', '')
            html_content = html_content.replace('{{doc_id}}', '')
            html_content = html_content.replace('{{act_id}}', '')
            html_content = html_content.replace('{{current_date}}', f'<strong>{timezone.now().strftime("%d.%m.%Y")}</strong>')
            html_content = html_content.replace('{{start_date}}', '')
            html_content = html_content.replace('{{end_date}}', '')
            html_content = html_content.replace('{{quantity}}', '')
            html_content = html_content.replace('{{sum}}', '')
            html_content = html_content.replace('{{amount}}', '')
            html_content = html_content.replace('{{res_quantitu}}', '')
            html_content = html_content.replace('{{res}}', '')
        
        preview_html = f'<div style="font-family: Times New Roman, serif; font-size: 14px; line-height: 1.5; color: #000;">{html_content}</div>'
        return JsonResponse({'success': True, 'preview_html': preview_html})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Ошибка загрузки документа: {str(e)}'})

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
            # Формируем actions
            actions = []
            for appr in approvers:
                actions.append({
                    'role': 'approver',
                    'username': appr['username'],
                    'full_name': appr['full_name'],
                    'status': 'ожидание'
                })
            # Подписант
            try:
                signer = User.objects.get(username='250003')
                signer_full_name = signer.full_name
            except Exception:
                signer_full_name = 'Подписант'
            actions.append({
                'role': 'signer',
                'username': '250003',
                'full_name': signer_full_name,
                'status': 'ожидание'
            })
            actions.append({
                'role': 'executor',
                'username': user.username,
                'full_name': user.full_name,
                'status': 'ожидание'
            })
            # 1. Создаем запись в БД (генерируется doc_id)
            document = GphDocument.objects.create(
                doc_type='gph',
                user=user,
                full_name=user.full_name,
                start_date=start_date,
                end_date=end_date,
                file_path='',  # временно
                approvers=approvers,
                actions=actions
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
@role_required([1, 5, 2])  # Админ, редактор, подписант (только просмотр)
def act_list(request):
    # Получаем все акты
    acts = ActDocument.objects.select_related('user', 'gph_document').order_by('-created_at')
    
    # Получаем все пакеты
    packages = ActPackage.objects.select_related('created_by').order_by('-created_at')
    
    # Создаем словарь для быстрого поиска актов в пакетах
    acts_in_packages = {}
    for package in packages:
        for act_id in package.acts:
            acts_in_packages[act_id] = package.package_id
    
    # Добавляем информацию о пакете к каждому акту
    for act in acts:
        act.package_id = acts_in_packages.get(act.act_id)
    
    return render(request, 'documents/act_list.html', {
        'acts': acts,
        'packages': packages,
        'acts_in_packages': acts_in_packages
    })

@login_required
@role_required([1, 5])  # Только Админ и Редактор могут скачивать акты
def act_download(request):
    """Скачивание акта в формате DOCX с подстановкой данных"""
    try:
        template_path = os.path.join(settings.BASE_DIR, 'static', 'docs', 'act.docx')
        if not os.path.exists(template_path):
            return JsonResponse({'success': False, 'error': 'Файл шаблона act.docx не найден'})
        
        # Создаем документ из шаблона
        doc = DocxDocument(template_path)
        
        # Получаем данные из запроса
        data = {
            'full_name': request.GET.get('full_name', ''),
            'phone_number': request.GET.get('phone_number', ''),
            'iin': request.GET.get('iin', ''),
            'doc_id': request.GET.get('doc_id', ''),
            'act_id': '',  # Оставляем пустым, будем генерировать на бэкенде
            'current_date': timezone.now().strftime('%d.%m.%Y'),
            'start_date': request.GET.get('start_date', ''),
            'end_date': request.GET.get('end_date', ''),
            'quantity': request.GET.get('quantity', ''),
            'unit_price': request.GET.get('unit_price', ''),
            'amount': request.GET.get('amount', ''),
            'created_date': '',  # Будем заполнять из ГПХ договора
        }
        
        # Если указан исполнитель, ищем его последний ГПХ договор только для ID
        executor_username = request.GET.get('executor', '')
        if executor_username and not data['doc_id']:
            try:
                User = get_user_model()
                user = User.objects.get(username=executor_username, role=4)
                # Ищем последний ГПХ договор пользователя только для получения ID
                last_gph = GphDocument.objects.filter(
                    user=user,
                    doc_type='gph'
                ).order_by('-created_at').first()
                
                if last_gph:
                    data['doc_id'] = last_gph.doc_id
                    data['created_date'] = last_gph.created_at.strftime('%d.%m.%Y') if last_gph.created_at else ''
            except User.DoesNotExist:
                pass
        
        # Вычисляем общую стоимость (количество × цена за единицу)
        try:
            quantity = float(data['quantity']) if data['quantity'] else 0
            unit_price = float(data['unit_price']) if data['unit_price'] else 0
            if quantity > 0 and unit_price > 0:
                data['amount'] = f"{quantity * unit_price:.2f}"
            else:
                data['amount'] = ''
        except (ValueError, ZeroDivisionError):
            data['amount'] = ''
        
        # Функция для замены плейсхолдеров
        def replace_placeholders(text):
            text = text.replace('{{full_name}}', data['full_name'])
            text = text.replace('{{phone_number}}', data['phone_number'])
            text = text.replace('{{iin}}', data['iin'])
            text = text.replace('{{doc_id}}', data['doc_id'])
            text = text.replace('{{created_date}}', data['created_date'])
            text = text.replace('{{act_id}}', data['act_id'])
            text = text.replace('{{current_date}}', data['current_date'])
            text = text.replace('{{start_date}}', data['start_date'])
            text = text.replace('{{end_date}}', data['end_date'])
            text = text.replace('{{quantity}}', data['quantity'])
            text = text.replace('{{sum}}', data['unit_price'])
            text = text.replace('{{amount}}', data['amount'])
            text = text.replace('{{res_quantitu}}', data['quantity'])
            text = text.replace('{{res}}', data['amount'])
            return text
        
        # Заменяем плейсхолдеры в параграфах
        for paragraph in doc.paragraphs:
            paragraph.text = replace_placeholders(paragraph.text)
        
        # Заменяем плейсхолдеры в таблицах
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        paragraph.text = replace_placeholders(paragraph.text)
        
        # Сохраняем в память
        file_stream = io.BytesIO()
        doc.save(file_stream)
        file_stream.seek(0)
        
        # Создаем HTTP ответ для скачивания
        response = HttpResponse(
            file_stream.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        response['Content-Disposition'] = 'attachment; filename="act.docx"'
        
        return response
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Ошибка создания документа: {str(e)}'})

@login_required
@role_required([1, 5])  # Только Админ и Редактор могут получать данные пользователей
def user_data_api(request, username):
    """API для получения данных пользователя по username"""
    try:
        User = get_user_model()
        user = User.objects.get(username=username, role=4)  # Только исполнители
        
        user_data = {
            'full_name': user.full_name or '',
            'phone_number': user.phone_number or '',
            'iin': user.iin or '',
        }
        
        return JsonResponse({'success': True, 'user': user_data})
        
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Пользователь не найден'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Ошибка: {str(e)}'})

@login_required
@role_required([1, 5])  # Только Админ и Редактор могут сохранять акты
def act_save(request):
    """Сохранение акта выполненных работ и загрузка в Dropbox"""
    if request.method == 'POST':
        form = ActForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            executor_username = data['executor']
            
            # Получаем пользователя-исполнителя
            User = get_user_model()
            try:
                user = User.objects.get(username=executor_username, role=4)
            except User.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Исполнитель не найден'})
            
            # Находим последний ГПХ договор пользователя
            last_gph = GphDocument.objects.filter(
                user=user, 
                doc_type='gph'
            ).order_by('-created_at').first()
            
            if not last_gph:
                return JsonResponse({'success': False, 'error': 'ГПХ договор не найден для данного исполнителя'})
            
            # Согласующие
            approvers = []
            if 'approvers' in request.POST:
                approver_usernames = request.POST.getlist('approvers')
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
            
            # Формируем actions
            actions = []
            for appr in approvers:
                actions.append({
                    'role': 'approver',
                    'username': appr['username'],
                    'full_name': appr['full_name'],
                    'status': 'ожидание'
                })
            actions.append({
                'role': 'signer',
                'username': '250003',
                'full_name': 'Подписант',
                'status': 'ожидание'
            })
            actions.append({
                'role': 'executor',
                'username': user.username,
                'full_name': user.full_name,
                'status': 'ожидание'
            })
            # Вычисляем общую стоимость
            try:
                quantity = float(data['quantity']) if data['quantity'] else 0
                unit_price = float(data['unit_price']) if data['unit_price'] else 0
                amount = f"{quantity * unit_price:.2f}" if quantity > 0 and unit_price > 0 else "0.00"
            except (ValueError, ZeroDivisionError):
                amount = "0.00"
            
            # 1. Создаем запись в БД (генерируется act_id)
            document = ActDocument.objects.create(
                user=user,
                gph_document=last_gph,
                full_name=data['full_name'],
                phone_number=data['phone_number'],
                iin=data['iin'],
                start_date=data['start_date'],
                end_date=data['end_date'],
                quantity=data['quantity'],
                unit_price=data['unit_price'],
                amount=amount,
                file_path='',  # временно
                approvers=approvers,
                actions=actions
            )
            act_id = document.act_id
            
            # 2. Формируем docx с подстановкой всех данных
            template_path = os.path.join(settings.BASE_DIR, 'static', 'docs', 'act.docx')
            doc = DocxDocument(template_path)
            
            def replace_placeholders(text):
                text = text.replace('{{full_name}}', data['full_name'])
                text = text.replace('{{phone_number}}', data['phone_number'])
                text = text.replace('{{iin}}', data['iin'])
                text = text.replace('{{doc_id}}', last_gph.doc_id)
                text = text.replace('{{created_date}}', last_gph.created_at.strftime('%d.%m.%Y') if last_gph.created_at else '')
                text = text.replace('{{act_id}}', act_id)
                text = text.replace('{{current_date}}', document.created_at.strftime('%d.%m.%Y'))
                text = text.replace('{{start_date}}', str(data['start_date']))
                text = text.replace('{{end_date}}', str(data['end_date']))
                text = text.replace('{{quantity}}', data['quantity'])
                text = text.replace('{{sum}}', data['unit_price'])
                text = text.replace('{{amount}}', amount)
                text = text.replace('{{res_quantitu}}', data['quantity'])
                text = text.replace('{{res}}', amount)
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
            dropbox_filename = f"Акт-{user.username}-{document.created_at.strftime('%Y%m%d-%H%M%S')}.docx"
            dropbox_path = dropbox_folder + dropbox_filename
            dbx.files_upload(file_stream.read(), dropbox_path, mode=dropbox.files.WriteMode.overwrite)
            
            # 5. Получаем публичную ссылку
            shared_link_metadata = dbx.sharing_create_shared_link_with_settings(dropbox_path)
            public_url = shared_link_metadata.url.replace('?dl=0', '?raw=1')
            
            # 6. Сохраняем ссылку в модель
            document.file_path = public_url
            document.save()
            
            return JsonResponse({'success': True, 'file_path': public_url, 'act_id': act_id})
        else:
            return JsonResponse({'success': False, 'error': 'Неверные данные формы'})
    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})

@login_required
@role_required([1, 5])  # Только Админ и Редактор могут добавлять акты в пакет
def add_act_to_package(request):
    """Добавление акта в пакет (сохранение акта + добавление в сессию)"""
    if request.method == 'POST':
        form = ActForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            executor_username = data['executor']
            
            # Получаем пользователя-исполнителя
            User = get_user_model()
            try:
                user = User.objects.get(username=executor_username, role=4)
            except User.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Исполнитель не найден'})
            
            # Проверяем, не добавлен ли уже этот исполнитель в пакет
            package_acts = request.session.get('package_acts', [])
            existing_executors = [act.get('executor_username') for act in package_acts]
            if executor_username in existing_executors:
                return JsonResponse({'success': False, 'error': 'Этот исполнитель уже добавлен в пакет'})
            
            # Находим последний ГПХ договор пользователя
            last_gph = GphDocument.objects.filter(
                user=user, 
                doc_type='gph'
            ).order_by('-created_at').first()
            
            if not last_gph:
                return JsonResponse({'success': False, 'error': 'ГПХ договор не найден для данного исполнителя'})
            
            # Согласующие
            approvers = []
            if 'approvers' in request.POST:
                approver_usernames = request.POST.getlist('approvers')
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
            
            # Вычисляем общую стоимость
            try:
                quantity = float(data['quantity']) if data['quantity'] else 0
                unit_price = float(data['unit_price']) if data['unit_price'] else 0
                amount = f"{quantity * unit_price:.2f}" if quantity > 0 and unit_price > 0 else "0.00"
            except (ValueError, ZeroDivisionError):
                amount = "0.00"
            # Формируем actions
            actions = []
            for appr in approvers:
                actions.append({
                    'role': 'approver',
                    'username': appr['username'],
                    'full_name': appr['full_name'],
                    'status': 'ожидание'
                })
            actions.append({
                'role': 'signer',
                'username': '250003',
                'full_name': 'Подписант',
                'status': 'ожидание'
            })
            actions.append({
                'role': 'executor',
                'username': user.username,
                'full_name': user.full_name,
                'status': 'ожидание'
            })
            # Создаем запись в БД
            document = ActDocument.objects.create(
                user=user,
                gph_document=last_gph,
                full_name=data['full_name'],
                phone_number=data['phone_number'],
                iin=data['iin'],
                start_date=data['start_date'],
                end_date=data['end_date'],
                quantity=data['quantity'],
                unit_price=data['unit_price'],
                amount=amount,
                file_path='',  # временно
                approvers=approvers,
                actions=actions
            )
            
            # Загружаем файл в Dropbox
            try:
                template_path = os.path.join(settings.BASE_DIR, 'static', 'docs', 'act.docx')
                doc = DocxDocument(template_path)
                
                def replace_placeholders(text):
                    text = text.replace('{{full_name}}', data['full_name'])
                    text = text.replace('{{phone_number}}', data['phone_number'])
                    text = text.replace('{{iin}}', data['iin'])
                    text = text.replace('{{doc_id}}', last_gph.doc_id)
                    text = text.replace('{{created_date}}', last_gph.created_at.strftime('%d.%m.%Y') if last_gph.created_at else '')
                    text = text.replace('{{act_id}}', document.act_id)
                    text = text.replace('{{current_date}}', document.created_at.strftime('%d.%m.%Y'))
                    text = text.replace('{{start_date}}', str(data['start_date']))
                    text = text.replace('{{end_date}}', str(data['end_date']))
                    text = text.replace('{{quantity}}', data['quantity'])
                    text = text.replace('{{sum}}', data['unit_price'])
                    text = text.replace('{{amount}}', amount)
                    text = text.replace('{{res_quantitu}}', data['quantity'])
                    text = text.replace('{{res}}', amount)
                    return text
                
                for paragraph in doc.paragraphs:
                    paragraph.text = replace_placeholders(paragraph.text)
                for table in doc.tables:
                    for row in table.rows:
                        for cell in row.cells:
                            for paragraph in cell.paragraphs:
                                paragraph.text = replace_placeholders(paragraph.text)
                
                file_stream = io.BytesIO()
                doc.save(file_stream)
                file_stream.seek(0)
                
                dbx = dropbox.Dropbox(settings.DROPBOX_TOKEN)
                dropbox_folder = f"/ncasign/{user.username}/"
                dropbox_filename = f"Акт-{user.username}-{document.created_at.strftime('%Y%m%d-%H%M%S')}.docx"
                dropbox_path = dropbox_folder + dropbox_filename
                dbx.files_upload(file_stream.read(), dropbox_path, mode=dropbox.files.WriteMode.overwrite)
                
                shared_link_metadata = dbx.sharing_create_shared_link_with_settings(dropbox_path)
                public_url = shared_link_metadata.url.replace('?dl=0', '?raw=1')
                
                document.file_path = public_url
                document.save()
                
            except Exception as e:
                # Если не удалось загрузить в Dropbox, удаляем запись
                document.delete()
                return JsonResponse({'success': False, 'error': f'Ошибка загрузки файла: {str(e)}'})
            
            # Добавляем акт в пакет (сессия)
            act_info = {
                'act_id': document.act_id,
                'executor_username': executor_username,
                'executor_name': data['full_name'],
                'amount': amount,
                'created_at': document.created_at.isoformat()
            }
            
            package_acts.append(act_info)
            request.session['package_acts'] = package_acts
            request.session.modified = True
            
            return JsonResponse({
                'success': True, 
                'message': f'Акт для {data["full_name"]} добавлен в пакет',
                'package_count': len(package_acts),
                'act_id': document.act_id
            })
        else:
            return JsonResponse({'success': False, 'error': 'Неверные данные формы'})
    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})

@login_required
@role_required([1, 5])  # Только Админ и Редактор могут сохранять пакеты
def save_package(request):
    """Сохранение пакета актов в БД"""
    if request.method == 'POST':
        package_acts = request.session.get('package_acts', [])
        
        if len(package_acts) < 2:
            return JsonResponse({'success': False, 'error': 'Для создания пакета нужно минимум 2 акта'})
        
        try:
            # Создаем пакет
            package = ActPackage.objects.create(
                created_by=request.user,
                acts=[act['act_id'] for act in package_acts],
                status='ready'
            )
            
            # Очищаем сессию
            request.session.pop('package_acts', None)
            request.session.modified = True
            
            return JsonResponse({
                'success': True, 
                'message': f'Пакет {package.package_id} успешно создан с {len(package_acts)} актами',
                'package_id': package.package_id
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Ошибка создания пакета: {str(e)}'})
    
    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})

@login_required
@role_required([1, 5])  # Только Админ и Редактор могут очищать пакеты
def clear_package(request):
    """Очистка пакета из сессии"""
    if request.method == 'POST':
        package_acts = request.session.get('package_acts', [])
        
        if not package_acts:
            return JsonResponse({'success': False, 'error': 'Пакет уже пуст'})
        
        # Удаляем все акты из БД
        for act_info in package_acts:
            try:
                act = ActDocument.objects.get(act_id=act_info['act_id'])
                act.delete()
            except ActDocument.DoesNotExist:
                pass
        
        # Очищаем сессию
        request.session.pop('package_acts', None)
        request.session.modified = True
        
        return JsonResponse({
            'success': True, 
            'message': f'Пакет очищен, удалено {len(package_acts)} актов'
        })
    
    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})

@login_required
@role_required([1, 5])  # Только Админ и Редактор могут получать информацию о пакете
def get_package_info(request):
    """Получение информации о текущем пакете в сессии"""
    package_acts = request.session.get('package_acts', [])
    
    return JsonResponse({
        'success': True,
        'package_count': len(package_acts),
        'acts': package_acts
    })

@login_required
@require_GET
def api_pending_approvals(request):
    """
    Возвращает структуру:
    {
      gph: [...],
      acts: [...],
      packages: [ ... ]
    }
    Для всех участников процесса: согласующий, подписант, исполнитель (статус 'ожидание').
    """
    user = request.user
    gph = []
    acts = []
    packages = []
    # ГПХ
    for doc in GphDocument.objects.all():
        for a in doc.actions:
            if a.get('username') == user.username and a.get('status') == 'ожидание':
                gph.append({
                    'doc_id': doc.doc_id,
                    'type': 'gph',
                    'full_name': doc.full_name,
                    'created_at': doc.created_at.strftime('%d.%m.%Y %H:%M'),
                    'status': a.get('status'),
                    'actions': doc.actions,
                })
                break
    # Одиночные акты (не в пакетах)
    acts_in_packages = set()
    for package in ActPackage.objects.all():
        acts_in_packages.update(package.acts)
    for act in ActDocument.objects.all():
        if act.act_id in acts_in_packages:
            continue
        for a in act.actions:
            if a.get('username') == user.username and a.get('status') == 'ожидание':
                acts.append({
                    'act_id': act.act_id,
                    'type': 'act',
                    'full_name': act.full_name,
                    'created_at': act.created_at.strftime('%d.%m.%Y %H:%M'),
                    'status': a.get('status'),
                    'actions': act.actions,
                })
                break
    # Пакеты
    for package in ActPackage.objects.all():
        package_acts = []
        for act_id in package.acts:
            try:
                act = ActDocument.objects.get(act_id=act_id)
            except ActDocument.DoesNotExist:
                continue
            for a in act.actions:
                if a.get('username') == user.username and a.get('status') == 'ожидание':
                    package_acts.append({
                        'act_id': act.act_id,
                        'full_name': act.full_name,
                        'created_at': act.created_at.strftime('%d.%m.%Y %H:%M'),
                        'status': a.get('status'),
                        'actions': act.actions,
                    })
                    break
        if package_acts:
            packages.append({
                'package_id': package.package_id,
                'created_at': package.created_at.strftime('%d.%m.%Y %H:%M'),
                'status': package.status,
                'acts': package_acts,
                'actions': [act['actions'] for act in package_acts if 'actions' in act]
            })
    return JsonResponse({'success': True, 'gph': gph, 'acts': acts, 'packages': packages})

@login_required
@require_GET
def api_user_history(request):
    """
    Возвращает структуру:
    {
      gph: [...],
      acts: [...],
      packages: [ { package_id, created_at, status, acts: [ ... ] } ]
    }
    Для всех участников процесса: если пользователь есть в actions, он видит документ в истории.
    """
    user = request.user
    gph = []
    acts = []
    packages = []
    # ГПХ
    for doc in GphDocument.objects.all():
        for a in doc.actions:
            if a.get('username') == user.username:
                gph.append({
                    'doc_id': doc.doc_id,
                    'type': 'gph',
                    'full_name': doc.full_name,
                    'created_at': doc.created_at.strftime('%d.%m.%Y %H:%M'),
                    'file_path': doc.file_path,
                    'status': a.get('status'),
                    'actions': doc.actions,
                })
                break
    # Одиночные акты (не в пакетах)
    acts_in_packages = set()
    for package in ActPackage.objects.all():
        acts_in_packages.update(package.acts)
    for act in ActDocument.objects.all():
        if act.act_id in acts_in_packages:
            continue
        for a in act.actions:
            if a.get('username') == user.username:
                acts.append({
                    'act_id': act.act_id,
                    'type': 'act',
                    'full_name': act.full_name,
                    'created_at': act.created_at.strftime('%d.%m.%Y %H:%M'),
                    'file_path': act.file_path,
                    'status': a.get('status'),
                    'actions': act.actions,
                })
                break
    # Пакеты
    for package in ActPackage.objects.all():
        package_acts = []
        for act_id in package.acts:
            try:
                act = ActDocument.objects.get(act_id=act_id)
            except ActDocument.DoesNotExist:
                continue
            for a in act.actions:
                if a.get('username') == user.username:
                    package_acts.append({
                        'act_id': act.act_id,
                        'full_name': act.full_name,
                        'created_at': act.created_at.strftime('%d.%m.%Y %H:%M'),
                        'file_path': act.file_path,
                        'status': a.get('status'),
                        'actions': act.actions,
                    })
                    break
        if package_acts:
            packages.append({
                'package_id': package.package_id,
                'created_at': package.created_at.strftime('%d.%m.%Y %H:%M'),
                'status': package.status,
                'acts': package_acts,
                'actions': [act['actions'] for act in package_acts if 'actions' in act]
            })
    return JsonResponse({'success': True, 'gph': gph, 'acts': acts, 'packages': packages})

@csrf_exempt
@login_required
def api_approve_action(request):
    """
    POST: {doc_type: 'gph'|'act', doc_id: '...', is_approve: true|false}
    Обновляет статус участника (approver, signer, executor) в actions (и approvers для согласующих).
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Только POST'})
    try:
        data = json.loads(request.body.decode('utf-8'))
        doc_type = data.get('doc_type')
        doc_id = data.get('doc_id')
        is_approve = data.get('is_approve')
        user = request.user
        # Находим документ
        if doc_type == 'gph':
            doc = GphDocument.objects.get(doc_id=doc_id)
        elif doc_type == 'act':
            doc = ActDocument.objects.get(act_id=doc_id)
        else:
            return JsonResponse({'success': False, 'error': 'Неверный тип документа'})
        # Обновляем actions
        updated = False
        for a in doc.actions:
            if a.get('username') == user.username and a.get('status') == 'ожидание':
                if a['role'] == 'approver':
                    a['status'] = 'согласовано' if is_approve else 'отклонено'
                elif a['role'] == 'signer':
                    a['status'] = 'подписано' if is_approve else 'отклонено'
                elif a['role'] == 'executor':
                    a['status'] = 'подписано' if is_approve else 'отклонено'
                updated = True
        # Для согласующих — обновляем и в approvers
        if hasattr(doc, 'approvers'):
            for appr in doc.approvers:
                if appr.get('username') == user.username and appr.get('status') == 'ожидание':
                    appr['status'] = 'согласовано' if is_approve else 'отклонено'
        if updated:
            doc.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'error': 'Нет прав или уже согласовано/подписано'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_POST
def api_approve_package(request):
    """
    POST: {package_id: '...', is_approve: true|false}
    Согласует/подписывает все акты в пакете для текущего пользователя (если статус 'ожидание').
    """
    data = json.loads(request.body.decode('utf-8'))
    package_id = data.get('package_id')
    is_approve = data.get('is_approve')
    user = request.user
    try:
        package = ActPackage.objects.get(package_id=package_id)
    except ActPackage.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Пакет не найден'})
    updated = False
    for act_id in package.acts:
        try:
            act = ActDocument.objects.get(act_id=act_id)
        except ActDocument.DoesNotExist:
            continue
        for a in act.actions:
            if a.get('username') == user.username and a.get('status') == 'ожидание':
                if a['role'] == 'approver':
                    a['status'] = 'согласовано' if is_approve else 'отклонено'
                elif a['role'] == 'signer':
                    a['status'] = 'подписано' if is_approve else 'отклонено'
                updated = True
        if updated:
            act.save()
    return JsonResponse({'success': True})
