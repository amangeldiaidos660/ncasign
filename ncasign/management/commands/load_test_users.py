from django.core.management.base import BaseCommand
from ncasign.models import User
import json
import os

class Command(BaseCommand):
    help = 'Загружает тестовых пользователей из test_users.json (обновляет существующих и добавляет новых)'

    def handle(self, *args, **kwargs):
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'test_users.json')
        with open(path, encoding='utf-8') as f:
            users = json.load(f)
        created, updated = 0, 0
        for u in users:
            email = u['email']
            user, is_created = User.objects.update_or_create(
                email=email,
                defaults={
                    'full_name': u['full_name'],
                    'position': u['position'],
                    'role': u['role'],
                    'iin': u['iin'],
                    'phone_number': u['phone_number'],
                }
            )
            if is_created:
                user.set_password('Qwerty#01')
                user.save()
                created += 1
            else:
                updated += 1
        self.stdout.write(self.style.SUCCESS(f'Загружено пользователей: {created} новых, {updated} обновлено')) 