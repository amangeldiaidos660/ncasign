from django.shortcuts import render
from documents.models import GphDocument
from documents.models import ActDocument
from documents.models import ActPackage
import io
from django.http import FileResponse, HttpResponse, JsonResponse
from docx import Document
from docx.shared import Inches
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from django.template.loader import render_to_string
import os
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json
from django.utils import timezone
import dropbox

# Create your views here.

def gph_list(request):
    gph_docs = GphDocument.objects.all().order_by('-created_at')
    return render(request, 'signers/gph_list.html', {'gph_docs': gph_docs})

def act_list(request):
    all_acts = ActDocument.objects.all().order_by('-created_at')
    packages = ActPackage.objects.all().order_by('-created_at')
    acts_in_packages = set()
    package_list = []
    for package in packages:
        package_acts = [act for act in all_acts if act.act_id in package.acts]
        is_in_progress = any(
            any(action['status'] not in ['подписано', 'согласовано'] for action in act.actions)
            for act in package_acts
        )
        package_list.append({
            'package': package,
            'acts': package_acts,
            'is_in_progress': is_in_progress
        })
        acts_in_packages.update(package.acts)
    single_acts = [act for act in all_acts if act.act_id not in acts_in_packages]
    return render(request, 'signers/act_list.html', {
        'single_acts': single_acts,
        'package_list': package_list,
    })

def package_docx(request, package_id):
    from documents.models import ActPackage, ActDocument, GphDocument
    try:
        package = ActPackage.objects.get(package_id=package_id)
        acts = [ActDocument.objects.get(act_id=act_id) for act_id in package.acts]
    except ActPackage.DoesNotExist:
        return HttpResponse('Пакет не найден', status=404)
    
    acts_data = []
    for act in acts:
        gph = act.gph_document
        amount = act.amount
        try:
            nds = float(amount) * 1.12
            nds_str = f'{nds:.2f}'
        except:
            nds_str = amount
        
        acts_data.append({
            'act_id': act.act_id,
            'date': act.created_at.strftime('%d.%m.%Y'),
            'gph_id': gph.doc_id,
            'executor': act.full_name,
            'description': act.text,
            'quantity': act.quantity,
            'unit_price': act.unit_price,
            'amount': amount,
            'nds_amount': nds_str
        })
    
    html_string = render_to_string('signers/package_docx_template.html', {
        'package_id': package.package_id,
        'acts': acts_data
    })
    
    return HttpResponse(html_string, content_type='text/html')

def wait_sign_list(request):
    user = request.user
    acts = ActDocument.objects.all()
    gphs = GphDocument.objects.all()
    packages = ActPackage.objects.all()
    wait_acts = []
    wait_gphs = []
    package_list = []
    acts_in_packages = set()
    executor_acts_in_packages = set()  # Акты исполнителя в пакетах
    
    for package in packages:
        package_acts = [act for act in acts if act.act_id in package.acts]
        user_is_executor_in_package = False
        
        # Проверяем, является ли пользователь исполнителем какого-либо акта в пакете
        for act in package_acts:
            for action in act.actions:
                if (action.get('username') == user.username and 
                    action.get('status') == 'ожидание' and 
                    action.get('role') == 'executor'):
                    user_is_executor_in_package = True
                    executor_acts_in_packages.add(act.act_id)
                    # Добавляем акт исполнителя в отдельный список
                    act.can_sign = can_user_sign_document(act, user)
                    act.can_approve = can_user_approve_document(act, user)
                    act.can_reject = can_user_reject_document(act, user)
                    act.can_upload = can_user_upload_files(act, user)
                    act.user_action = get_user_action(act, user)
                    wait_acts.append(act)
                    break
        
        # Проверяем, есть ли другие участники (не исполнители) в пакете
        other_participants = False
        for act in package_acts:
            for action in act.actions:
                if (action.get('username') == user.username and 
                    action.get('status') == 'ожидание' and 
                    action.get('role') != 'executor'):
                    other_participants = True
                    break
            if other_participants:
                break
        
        # Если пользователь не исполнитель, но участвует в пакете, показываем пакет
        if other_participants:
            # Добавляем информацию о доступности кнопок для каждого акта в пакете
            for act in package_acts:
                act.can_sign = can_user_sign_document(act, user)
                act.can_approve = can_user_approve_document(act, user)
                act.can_reject = can_user_reject_document(act, user)
                act.can_upload = can_user_upload_files(act, user)
                act.user_action = get_user_action(act, user)
            
            # Проверяем возможность согласования/подписания всего пакета
            can_approve_package = can_user_approve_package(package_acts, user)
            can_sign_package = can_user_sign_package(package_acts, user)
            can_reject_package = can_user_reject_package(package_acts, user)
            
            # Определяем роль пользователя в пакете
            user_role_in_package = None
            for act in package_acts:
                for action in act.actions:
                    if action.get('username') == user.username:
                        user_role_in_package = action.get('role')
                        break
                if user_role_in_package:
                    break
            
            package_list.append({
                'package': package,
                'acts': package_acts,
                'is_in_progress': True,
                'can_approve_package': can_approve_package,
                'can_sign_package': can_sign_package,
                'can_reject_package': can_reject_package,
                'user_role_in_package': user_role_in_package
            })
            acts_in_packages.update(package.acts)
    
    # Добавляем отдельные акты (не в пакетах)
    for act in acts:
        if act.act_id in acts_in_packages or act.act_id in executor_acts_in_packages:
            continue
        for action in act.actions:
            if action.get('username') == user.username and action.get('status') == 'ожидание':
                # Добавляем информацию о доступности кнопок
                act.can_sign = can_user_sign_document(act, user)
                act.can_approve = can_user_approve_document(act, user)
                act.can_reject = can_user_reject_document(act, user)
                act.can_upload = can_user_upload_files(act, user)
                act.user_action = get_user_action(act, user)
                wait_acts.append(act)
                break
    
    for gph in gphs:
        for action in gph.actions:
            if action.get('username') == user.username and action.get('status') == 'ожидание':
                # Добавляем информацию о доступности кнопок
                gph.can_sign = can_user_sign_document(gph, user)
                gph.can_approve = can_user_approve_document(gph, user)
                gph.can_reject = can_user_reject_document(gph, user)
                gph.can_upload = can_user_upload_files(gph, user)
                gph.user_action = get_user_action(gph, user)
                wait_gphs.append(gph)
                break
    
    return render(request, 'signers/wait_sign_list.html', {
        'wait_acts': wait_acts,
        'wait_gphs': wait_gphs,
        'package_list': package_list,
    })

def can_user_upload_files(document, user):
    """Проверяет, может ли пользователь загружать файлы (только исполнитель)"""
    user_action = None
    for action in document.actions:
        if action.get('username') == user.username:
            user_action = action
            break
    
    if not user_action or user_action.get('status') != 'ожидание':
        return False
    
    # Только исполнитель может загружать файлы
    return user_action.get('role') == 'executor'

def get_user_action(document, user):
    """Получает действие текущего пользователя в документе"""
    for action in document.actions:
        if action.get('username') == user.username:
            return action
    return None

def can_user_sign_document(document, user):
    """Проверяет, может ли пользователь подписать документ"""
    # Находим действие текущего пользователя
    user_action = None
    for action in document.actions:
        if action.get('username') == user.username:
            user_action = action
            break
    
    if not user_action or user_action.get('status') != 'ожидание':
        return False
    
    user_role = user_action.get('role')
    
    # Определяем порядок: executor -> initiator -> approvers (параллельно) -> signer
    if user_role == 'executor':
        # Исполнитель может подписать первым
        return True
    elif user_role == 'initiator':
        # Инициатор может подписать после исполнителя
        for action in document.actions:
            if action.get('role') == 'executor' and action.get('status') == 'ожидание':
                return False
        return True
    elif user_role == 'approver':
        # Согласующий может согласовать после исполнителя и инициатора
        for action in document.actions:
            if action.get('role') in ['executor', 'initiator'] and action.get('status') == 'ожидание':
                return False
        return True
    elif user_role == 'signer':
        # Подписант может подписать после всех остальных
        for action in document.actions:
            if action.get('role') in ['executor', 'initiator', 'approver'] and action.get('status') == 'ожидание':
                return False
        return True
    
    return False

def can_user_approve_document(document, user):
    """Проверяет, может ли пользователь согласовать документ"""
    return can_user_sign_document(document, user)

def can_user_reject_document(document, user):
    """Проверяет, может ли пользователь отклонить документ"""
    return can_user_sign_document(document, user)

def can_user_sign_package(package_acts, user):
    """Проверяет, может ли пользователь подписать весь пакет (только подписант)"""
    user_role = None
    user_action = None
    
    # Находим роль пользователя в пакете
    for act in package_acts:
        for action in act.actions:
            if action.get('username') == user.username:
                user_role = action.get('role')
                user_action = action
                break
        if user_role:
            break
    
    if not user_role or user_action.get('status') != 'ожидание':
        return False
    
    # Только подписант может подписать пакет
    if user_role == 'signer':
        # Проверяем, что все предыдущие этапы пройдены
        for act in package_acts:
            for action in act.actions:
                if action.get('role') in ['executor', 'initiator', 'approver'] and action.get('status') == 'ожидание':
                    return False
        return True
    
    return False

def can_user_approve_package(package_acts, user):
    """Проверяет, может ли пользователь согласовать весь пакет (инициатор и согласующие)"""
    user_role = None
    user_action = None
    
    # Находим роль пользователя в пакете
    for act in package_acts:
        for action in act.actions:
            if action.get('username') == user.username:
                user_role = action.get('role')
                user_action = action
                break
        if user_role:
            break
    
    if not user_role or user_action.get('status') != 'ожидание':
        return False
    
    # Только инициатор и согласующие могут согласовать пакет
    if user_role in ['initiator', 'approver']:
        # Проверяем, что все предыдущие этапы пройдены
        if user_role == 'initiator':
            # Инициатор может согласовать после исполнителей
            for act in package_acts:
                for action in act.actions:
                    if action.get('role') == 'executor' and action.get('status') == 'ожидание':
                        return False
        elif user_role == 'approver':
            # Согласующий может согласовать после исполнителей и инициаторов
            # Но согласующие работают параллельно, поэтому проверяем только исполнителей
            for act in package_acts:
                for action in act.actions:
                    if action.get('role') == 'executor' and action.get('status') == 'ожидание':
                        return False
        return True
    
    return False

def can_user_reject_package(package_acts, user):
    """Проверяет, может ли пользователь отклонить весь пакет"""
    user_role = None
    user_action = None
    
    # Находим роль пользователя в пакете
    for act in package_acts:
        for action in act.actions:
            if action.get('username') == user.username:
                user_role = action.get('role')
                user_action = action
                break
        if user_role:
            break
    
    if not user_role or user_action.get('status') != 'ожидание':
        return False
    
    # Все роли кроме исполнителя могут отклонить пакет
    if user_role in ['initiator', 'approver', 'signer']:
        # Проверяем, что все предыдущие этапы пройдены (кроме согласующих)
        if user_role == 'initiator':
            # Инициатор может отклонить после исполнителей
            for act in package_acts:
                for action in act.actions:
                    if action.get('role') == 'executor' and action.get('status') == 'ожидание':
                        return False
        elif user_role == 'approver':
            # Согласующий может отклонить после исполнителей (параллельно с инициатором)
            for act in package_acts:
                for action in act.actions:
                    if action.get('role') == 'executor' and action.get('status') == 'ожидание':
                        return False
        elif user_role == 'signer':
            # Подписант может отклонить после всех остальных
            for act in package_acts:
                for action in act.actions:
                    if action.get('role') in ['executor', 'initiator', 'approver'] and action.get('status') == 'ожидание':
                        return False
        return True
    
    return False

@login_required
@require_POST
@csrf_exempt
def approve_package(request, package_id):
    """Согласование всего пакета актов"""
    try:
        user = request.user
        package = ActPackage.objects.get(package_id=package_id)
        acts = [ActDocument.objects.get(act_id=act_id) for act_id in package.acts]
        
        # Проверяем возможность согласования пакета
        if not can_user_approve_package(acts, user):
            return JsonResponse({'success': False, 'error': 'Не можете согласовать этот пакет'})
        
        # Согласовываем все акты в пакете для текущего пользователя
        for act in acts:
            for action in act.actions:
                if action.get('username') == user.username:
                    action['status'] = 'согласовано'
                    break
            act.save()
        
        return JsonResponse({'success': True, 'message': 'Пакет успешно согласован'})
        
    except ActPackage.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Пакет не найден'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Ошибка: {str(e)}'})

@login_required
@require_POST
@csrf_exempt
def sign_package(request, package_id):
    """Подписание всего пакета актов"""
    try:
        user = request.user
        package = ActPackage.objects.get(package_id=package_id)
        acts = [ActDocument.objects.get(act_id=act_id) for act_id in package.acts]
        
        # Проверяем возможность подписания пакета
        if not can_user_sign_package(acts, user):
            return JsonResponse({'success': False, 'error': 'Не можете подписать этот пакет'})
        
        # Подписываем все акты в пакете для текущего пользователя
        for act in acts:
            for action in act.actions:
                if action.get('username') == user.username:
                    action['status'] = 'подписано'
                    break
            act.save()
        
        return JsonResponse({'success': True, 'message': 'Пакет успешно подписан'})
        
    except ActPackage.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Пакет не найден'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Ошибка: {str(e)}'})

@login_required
@require_POST
@csrf_exempt
def reject_package(request, package_id):
    """Отклонение всего пакета актов"""
    try:
        user = request.user
        package = ActPackage.objects.get(package_id=package_id)
        acts = [ActDocument.objects.get(act_id=act_id) for act_id in package.acts]
        
        # Проверяем возможность отклонения пакета
        if not can_user_reject_package(acts, user):
            return JsonResponse({'success': False, 'error': 'Не можете отклонить этот пакет'})
        
        # Отклоняем все акты в пакете для текущего пользователя
        for act in acts:
            for action in act.actions:
                if action.get('username') == user.username:
                    action['status'] = 'отклонено'
                    break
            act.save()
        
        return JsonResponse({'success': True, 'message': 'Пакет успешно отклонен'})
        
    except ActPackage.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Пакет не найден'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Ошибка: {str(e)}'})

@login_required
@require_POST
@csrf_exempt
def sign_document(request, doc_type, doc_id):
    """Подписание документа"""
    try:
        user = request.user
        
        if doc_type == 'act':
            document = ActDocument.objects.get(act_id=doc_id)
        elif doc_type == 'gph':
            document = GphDocument.objects.get(doc_id=doc_id)
        else:
            return JsonResponse({'success': False, 'error': 'Неверный тип документа'})
        
        # Проверяем, что пользователь может подписать этот документ
        user_action = None
        for action in document.actions:
            if action.get('username') == user.username:
                user_action = action
                break
        
        if not user_action:
            return JsonResponse({'success': False, 'error': 'Вы не являетесь участником этого документа'})
        
        if user_action.get('status') != 'ожидание':
            return JsonResponse({'success': False, 'error': 'Документ уже обработан'})
        
        # Проверяем порядок подписания
        if not can_user_sign_document(document, user):
            return JsonResponse({'success': False, 'error': 'Не ваш ход для подписания'})
        
        # Обновляем статус
        for action in document.actions:
            if action.get('username') == user.username:
                action['status'] = 'подписано'
                break
        
        document.save()
        
        return JsonResponse({'success': True, 'message': 'Документ успешно подписан'})
        
    except (ActDocument.DoesNotExist, GphDocument.DoesNotExist):
        return JsonResponse({'success': False, 'error': 'Документ не найден'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Ошибка: {str(e)}'})

@login_required
@require_POST
@csrf_exempt
def approve_document(request, doc_type, doc_id):
    """Согласование документа"""
    try:
        user = request.user
        
        if doc_type == 'act':
            document = ActDocument.objects.get(act_id=doc_id)
        elif doc_type == 'gph':
            document = GphDocument.objects.get(doc_id=doc_id)
        else:
            return JsonResponse({'success': False, 'error': 'Неверный тип документа'})
        
        # Проверяем, что пользователь может согласовать этот документ
        user_action = None
        for action in document.actions:
            if action.get('username') == user.username:
                user_action = action
                break
        
        if not user_action:
            return JsonResponse({'success': False, 'error': 'Вы не являетесь участником этого документа'})
        
        if user_action.get('status') != 'ожидание':
            return JsonResponse({'success': False, 'error': 'Документ уже обработан'})
        
        # Проверяем порядок согласования
        if not can_user_approve_document(document, user):
            return JsonResponse({'success': False, 'error': 'Не ваш ход для согласования'})
        
        # Обновляем статус
        for action in document.actions:
            if action.get('username') == user.username:
                action['status'] = 'согласовано'
                break
        
        document.save()
        
        return JsonResponse({'success': True, 'message': 'Документ успешно согласован'})
        
    except (ActDocument.DoesNotExist, GphDocument.DoesNotExist):
        return JsonResponse({'success': False, 'error': 'Документ не найден'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Ошибка: {str(e)}'})

@login_required
@require_POST
@csrf_exempt
def reject_document(request, doc_type, doc_id):
    """Отклонение документа"""
    try:
        user = request.user
        
        if doc_type == 'act':
            document = ActDocument.objects.get(act_id=doc_id)
        elif doc_type == 'gph':
            document = GphDocument.objects.get(doc_id=doc_id)
        else:
            return JsonResponse({'success': False, 'error': 'Неверный тип документа'})
        
        # Проверяем, что пользователь может отклонить этот документ
        user_action = None
        for action in document.actions:
            if action.get('username') == user.username:
                user_action = action
                break
        
        if not user_action:
            return JsonResponse({'success': False, 'error': 'Вы не являетесь участником этого документа'})
        
        if user_action.get('status') != 'ожидание':
            return JsonResponse({'success': False, 'error': 'Документ уже обработан'})
        
        # Проверяем порядок отклонения
        if not can_user_reject_document(document, user):
            return JsonResponse({'success': False, 'error': 'Не ваш ход для отклонения'})
        
        # Обновляем статус
        for action in document.actions:
            if action.get('username') == user.username:
                action['status'] = 'отклонено'
                break
        
        document.save()
        
        return JsonResponse({'success': True, 'message': 'Документ отклонен'})
        
    except (ActDocument.DoesNotExist, GphDocument.DoesNotExist):
        return JsonResponse({'success': False, 'error': 'Документ не найден'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Ошибка: {str(e)}'})

@login_required
@require_POST
@csrf_exempt
def upload_files(request, doc_type, doc_id):
    """Загрузка файлов исполнителем"""
    try:
        user = request.user
        
        if doc_type == 'act':
            document = ActDocument.objects.get(act_id=doc_id)
        elif doc_type == 'gph':
            document = GphDocument.objects.get(doc_id=doc_id)
        else:
            return JsonResponse({'success': False, 'error': 'Неверный тип документа'})
        
        # Проверяем, что пользователь может загружать файлы
        if not can_user_upload_files(document, user):
            return JsonResponse({'success': False, 'error': 'Вы не можете загружать файлы для этого документа'})
        
        # Получаем файлы из запроса
        files = request.FILES.getlist('files')
        if not files:
            return JsonResponse({'success': False, 'error': 'Файлы не выбраны'})
        
        # Обновляем токен доступа к Dropbox
        from ncasign.utils import get_dropbox_access_token
        access_token = get_dropbox_access_token()
        
        import dropbox
        dbx = dropbox.Dropbox(access_token)
        
        # Определяем префикс для названий файлов
        if doc_type == 'gph':
            prefix = 'ГПХ-Приложение'
        else:  # act
            prefix = 'АКТ-Приложение'
        
        # Получаем существующие приложения
        existing_attachments = document.attachments or []
        
        uploaded_files = []
        for i, file in enumerate(files):
            # Проверяем, что файл PDF
            if not file.name.lower().endswith('.pdf'):
                return JsonResponse({'success': False, 'error': f'Файл {file.name} не является PDF'})
            
            # Определяем номер приложения
            attachment_number = len(existing_attachments) + i + 1
            filename = f"{prefix}-{attachment_number}.pdf"
            
            # Путь в Dropbox
            dropbox_folder = f"/ncasign/{user.username}/"
            dropbox_path = dropbox_folder + filename
            
            # Загружаем файл в Dropbox
            file_content = file.read()
            dbx.files_upload(file_content, dropbox_path, mode=dropbox.files.WriteMode.overwrite)
            
            # Получаем публичную ссылку
            try:
                shared_link_metadata = dbx.sharing_create_shared_link_with_settings(dropbox_path)
                public_url = shared_link_metadata.url.replace('?dl=0', '?raw=1')
            except dropbox.exceptions.ApiError as e:
                if e.error.is_shared_link_already_exists():
                    # Если ссылка уже существует, получаем её
                    shared_links = dbx.sharing_list_shared_links(dropbox_path)
                    if shared_links.links:
                        public_url = shared_links.links[0].url.replace('?dl=0', '?raw=1')
                    else:
                        return JsonResponse({'success': False, 'error': f'Не удалось получить ссылку для файла {file.name}'})
                else:
                    return JsonResponse({'success': False, 'error': f'Ошибка Dropbox для файла {file.name}: {str(e)}'})
            
            # Добавляем информацию о файле
            file_info = {
                'filename': filename,
                'original_name': file.name,
                'url': public_url,
                'uploaded_at': timezone.now().isoformat(),
                'uploaded_by': user.username
            }
            uploaded_files.append(file_info)
        
        # Обновляем список приложений в документе
        document.attachments.extend(uploaded_files)
        document.save()
        
        return JsonResponse({
            'success': True, 
            'message': f'Загружено {len(files)} файлов',
            'files': uploaded_files
        })
        
    except (ActDocument.DoesNotExist, GphDocument.DoesNotExist):
        return JsonResponse({'success': False, 'error': 'Документ не найден'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Ошибка: {str(e)}'})
