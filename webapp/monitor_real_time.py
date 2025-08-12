#!/usr/bin/env python
import os
import sys
import django
import time
from datetime import timedelta

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'svcmon.settings')
django.setup()

from django.utils import timezone
from monitoring.models import Endpoint, Check

def monitor_status_changes():
    """실시간 상태 변화 모니터링"""
    print("=== 실시간 상태 변화 모니터링 ===")
    print("5초마다 상태를 체크합니다. Ctrl+C로 중단하세요.")
    print()
    
    previous_statuses = {}
    
    try:
        while True:
            current_time = timezone.now()
            print(f"\n[{current_time.strftime('%H:%M:%S')}] 상태 체크")
            
            status_changed = False
            
            for endpoint in Endpoint.objects.filter(is_enabled=True):
                latest_check = endpoint.checks.first()
                
                if latest_check:
                    # 시간 보정 적용
                    corrected_check_time = latest_check.checked_at - timedelta(hours=9)
                    expected_next_check = corrected_check_time + timedelta(seconds=endpoint.poll_interval_sec)
                    
                    # 상태 판정
                    if current_time > expected_next_check:
                        current_status = 'AMBER'
                        time_overdue = (current_time - expected_next_check).total_seconds()
                        status_detail = f"호출주기 {time_overdue:.1f}초 초과"
                    elif (latest_check.status_code and 
                          200 <= latest_check.status_code < 300 and 
                          not latest_check.error):
                        current_status = 'GREEN'
                        status_detail = "정상"
                    else:
                        current_status = 'RED'
                        status_detail = f"오류 (HTTP {latest_check.status_code})"
                else:
                    current_status = 'AMBER'
                    status_detail = "체크 이력 없음"
                
                # 상태 변화 감지
                url_short = endpoint.url.replace('https://', '').replace('http://', '')[:30]
                if endpoint.id not in previous_statuses:
                    print(f"  {url_short}: {current_status} ({status_detail})")
                    status_changed = True
                elif previous_statuses[endpoint.id] != current_status:
                    print(f"  🔄 {url_short}: {previous_statuses[endpoint.id]} → {current_status} ({status_detail})")
                    status_changed = True
                
                previous_statuses[endpoint.id] = current_status
            
            if not status_changed and previous_statuses:
                print("  상태 변화 없음")
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\n\n모니터링 종료")

if __name__ == "__main__":
    monitor_status_changes()
