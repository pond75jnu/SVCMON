from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone
import os

User = get_user_model()


class Command(BaseCommand):
    help = '초기 관리자 사용자를 생성합니다'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default=os.getenv('ADMIN_USERNAME', 'jnuadmin'),
            help='관리자 사용자명 (기본값: jnuadmin)'
        )
        parser.add_argument(
            '--password',
            type=str,
            default=os.getenv('ADMIN_PASSWORD', 'Wjsskaeo1!'),
            help='관리자 비밀번호 (기본값: Wjsskaeo1!)'
        )
        parser.add_argument(
            '--email',
            type=str,
            default='admin@jnu.ac.kr',
            help='관리자 이메일 (기본값: admin@jnu.ac.kr)'
        )
        parser.add_argument(
            '--phone',
            type=str,
            default='062-530-0114',
            help='관리자 전화번호 (기본값: 062-530-0114)'
        )

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        email = options['email']
        phone = options['phone']

        # 이미 사용자가 존재하는지 확인
        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f'사용자 "{username}"가 이미 존재합니다.')
            )
            return

        try:
            # 관리자 사용자 생성
            admin_user = User.objects.create_superuser(
                username=username,
                email=email,
                phone=phone,
                password=password
            )
            
            # 관리자는 바로 활성화
            admin_user.is_active = True
            admin_user.approved_at = timezone.now()
            admin_user.save()

            self.stdout.write(
                self.style.SUCCESS(
                    f'관리자 사용자 "{username}"가 성공적으로 생성되었습니다.\n'
                    f'이메일: {email}\n'
                    f'전화번호: {phone}'
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'사용자 생성 중 오류가 발생했습니다: {str(e)}')
            )
