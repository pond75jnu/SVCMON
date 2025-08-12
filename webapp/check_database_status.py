#!/usr/bin/env python
import os
import sys
import django

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'svcmon.settings')
django.setup()

from monitoring.models import NetworkGroup, Domain, Endpoint, Check

def check_database_status():
    """데이터베이스 상태 확인"""
    print("=== 데이터베이스 상태 확인 ===")
    
    # 망구분 확인
    network_count = NetworkGroup.objects.count()
    print(f"망구분 수: {network_count}")
    
    if network_count > 0:
        networks = NetworkGroup.objects.all()[:3]
        for network in networks:
            print(f"  - {network.name}")
    
    # 도메인 확인
    domain_count = Domain.objects.count()
    print(f"도메인 수: {domain_count}")
    
    if domain_count > 0:
        domains = Domain.objects.all()[:3]
        for domain in domains:
            print(f"  - {domain.domain} ({domain.site_name})")
    
    # 엔드포인트 확인
    endpoint_count = Endpoint.objects.count()
    print(f"엔드포인트 수: {endpoint_count}")
    
    if endpoint_count > 0:
        endpoints = Endpoint.objects.filter(is_enabled=True)[:5]
        for endpoint in endpoints:
            print(f"  - {endpoint.url}")
            print(f"    호출주기: {endpoint.poll_interval_sec}초")
            
            # 최근 체크 확인
            latest_check = endpoint.checks.first()
            if latest_check:
                print(f"    최근 체크: {latest_check.checked_at}")
                print(f"    상태코드: {latest_check.status_code}")
            else:
                print("    체크 이력 없음")
            print()
    
    # 체크 이력 확인
    check_count = Check.objects.count()
    print(f"체크 이력 수: {check_count}")

if __name__ == "__main__":
    check_database_status()
