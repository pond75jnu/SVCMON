import os
import django

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'svcmon.settings')
django.setup()

from monitoring.models import Domain, NetworkGroup

print("=== Django ORM으로 조회 ===")
try:
    domains = Domain.objects.all()
    print(f"Django ORM으로 조회된 도메인 수: {domains.count()}")
    
    for domain in domains:
        print(f"ID: {domain.id}, 망구분: {domain.network_group.name}, 도메인: {domain.domain}")
        print(f"  사이트명: {domain.site_name}, 담당자: {domain.owner_name}")
        if hasattr(domain, 'owner_contact'):
            print(f"  연락처: {domain.owner_contact}, 활성: {domain.is_active}")
        print()
        
except Exception as e:
    print(f"오류 발생: {e}")

print("\n=== 망구분 정보 ===")
network_groups = NetworkGroup.objects.all()
for ng in network_groups:
    print(f"ID: {ng.id}, 이름: {ng.name}")

print("\n=== 테이블 존재 여부 확인 ===")
from django.db import connection
cursor = connection.cursor()
try:
    cursor.execute("SELECT COUNT(*) FROM domains")
    count = cursor.fetchone()[0]
    print(f"domains 테이블에 {count}개의 레코드가 있습니다.")
except Exception as e:
    print(f"domains 테이블 조회 오류: {e}")
