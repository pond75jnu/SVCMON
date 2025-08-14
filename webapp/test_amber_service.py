"""
AMBER 서비스 테스트 스크립트
"""

import os
import sys
import django

# Django 설정
sys.path.append('d:/MyRepos/SVCMON/webapp')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'svcmon.settings')
django.setup()

# AMBER 서비스 테스트
from common.amber_service import AmberCheckService

def test_amber_service():
    print("AMBER 서비스 테스트 시작...")
    
    # 서비스 인스턴스 생성
    service = AmberCheckService()
    
    # 활성 엔드포인트 조회 테스트
    print("1. 활성 엔드포인트 조회 테스트...")
    endpoints = service._get_active_endpoints()
    print(f"활성 엔드포인트 수: {len(endpoints)}")
    for endpoint in endpoints:
        print(f"  - ID: {endpoint['endpoint_id']}, URL: {endpoint['endpoint_url']}, 폴링간격: {endpoint['poll_interval_seconds']}초")
    
    # 마지막 체크 시간 조회 테스트
    if endpoints:
        endpoint_id = endpoints[0]['endpoint_id']
        print(f"\n2. 마지막 체크 시간 조회 테스트 (endpoint_id: {endpoint_id})...")
        last_check = service._get_last_check_time(endpoint_id)
        if last_check:
            print(f"  - 마지막 체크: {last_check[0]['last_checked_at']}")
            print(f"  - 상태 코드: {last_check[0]['status_code']}")
        else:
            print("  - 체크 데이터 없음")
    
    # AMBER 체크 실행 테스트
    print(f"\n3. AMBER 체크 실행 테스트...")
    service._check_and_insert_amber_records()
    print("AMBER 체크 완료")

if __name__ == '__main__':
    test_amber_service()
