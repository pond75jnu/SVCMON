#!/usr/bin/env python
"""
수동 엔드포인트 체크 스크립트
응답시간을 측정하여 데이터베이스에 저장합니다.
"""

import os
import django
import requests
import time
import uuid
from datetime import datetime
from django.utils import timezone

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'svcmon.settings')
django.setup()

from monitoring.models import Endpoint, Check

def check_endpoint(endpoint):
    """단일 엔드포인트를 체크하고 결과를 저장"""
    print(f"체킹 중: {endpoint.url}")
    
    start_time = time.time()
    
    try:
        # HTTP 요청 수행 (30초 타임아웃)
        response = requests.get(
            endpoint.url, 
            timeout=30,
            allow_redirects=True,
            verify=False  # SSL 인증서 검증 무시 (테스트용)
        )
        
        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)
        
        # Check 객체 생성 및 저장 (trace_id는 자동 생성)
        check = Check()
        check.endpoint = endpoint
        check.status_code = response.status_code
        check.latency_ms = latency_ms
        check.headers = str(dict(response.headers))[:4000]  # 헤더 크기 제한
        check.error = None
        check.checked_at = timezone.now()  # 시간대 인식 datetime 사용
        check.trace_id = uuid.uuid4()  # UUID 명시적 생성
        check.save()
        
        print(f"  ✅ 성공: {response.status_code} ({latency_ms}ms)")
        return True
        
    except requests.exceptions.Timeout:
        # 타임아웃 오류
        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)
        
        check = Check()
        check.endpoint = endpoint
        check.status_code = None
        check.latency_ms = latency_ms
        check.headers = None
        check.error = "요청 시간 초과 (30초)"
        check.checked_at = timezone.now()
        check.trace_id = uuid.uuid4()
        check.save()
        
        print(f"  ⏰ 타임아웃: 30초 초과")
        return False
        
    except requests.exceptions.ConnectionError as e:
        # 연결 오류
        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)
        
        check = Check()
        check.endpoint = endpoint
        check.status_code = None
        check.latency_ms = latency_ms
        check.headers = None
        check.error = f"연결 오류: {str(e)[:500]}"  # 오류 메시지 크기 제한
        check.checked_at = timezone.now()
        check.trace_id = uuid.uuid4()
        check.save()
        
        print(f"  ❌ 연결 오류: {str(e)[:100]}")
        return False
        
    except Exception as e:
        # 기타 오류
        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)
        
        check = Check()
        check.endpoint = endpoint
        check.status_code = None
        check.latency_ms = latency_ms
        check.headers = None
        check.error = f"예상치 못한 오류: {str(e)[:500]}"
        check.checked_at = timezone.now()
        check.trace_id = uuid.uuid4()
        check.save()
        
        print(f"  ❌ 오류: {str(e)[:100]}")
        return False

def main():
    """모든 활성화된 엔드포인트를 체크"""
    print("=== 엔드포인트 체크 시작 ===")
    
    # 활성화된 엔드포인트들을 가져오기
    endpoints = Endpoint.objects.filter(is_enabled=True)
    
    if not endpoints:
        print("활성화된 엔드포인트가 없습니다.")
        return
    
    print(f"총 {endpoints.count()}개의 엔드포인트를 체크합니다.")
    print()
    
    success_count = 0
    failure_count = 0
    
    for endpoint in endpoints:
        if check_endpoint(endpoint):
            success_count += 1
        else:
            failure_count += 1
    
    print()
    print("=== 체크 완료 ===")
    print(f"성공: {success_count}개")
    print(f"실패: {failure_count}개")
    print(f"총계: {success_count + failure_count}개")

if __name__ == "__main__":
    main()
