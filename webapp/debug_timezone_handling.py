#!/usr/bin/env python
"""
시간대 처리 확인 스크립트
"""
import os
import sys
import django
from datetime import timedelta
import pytz

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'svcmon.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.utils import timezone
from django.conf import settings
from monitoring.models import NetworkGroup, Endpoint, Check

def check_timezone_handling():
    """시간대 처리 확인"""
    print(f"=== 시간대 처리 확인 ===")
    print(f"Django TIME_ZONE: {settings.TIME_ZONE}")
    print(f"Django USE_TZ: {settings.USE_TZ}")
    
    current_utc = timezone.now()
    kst = pytz.timezone('Asia/Seoul')
    current_kst = current_utc.astimezone(kst)
    
    print(f"현재 UTC: {current_utc}")
    print(f"현재 KST: {current_kst}")
    print()
    
    # 최근 체크 확인
    latest_check = Check.objects.first()
    if latest_check:
        print(f"최근 체크 시간 (저장된 값): {latest_check.checked_at}")
        print(f"체크 시간의 timezone info: {latest_check.checked_at.tzinfo}")
        
        # 체크 시간을 KST로 변환
        if latest_check.checked_at.tzinfo is None:
            # naive datetime인 경우 KST로 가정
            kst_check_time = kst.localize(latest_check.checked_at)
        else:
            kst_check_time = latest_check.checked_at.astimezone(kst)
        
        print(f"체크 시간 (KST로 해석): {kst_check_time}")
        
        # UTC로 변환
        utc_check_time = kst_check_time.astimezone(pytz.UTC)
        print(f"체크 시간 (UTC로 변환): {utc_check_time}")
        
        # 시간 차이 계산
        time_diff = current_utc - utc_check_time
        print(f"현재와의 시간 차이: {time_diff.total_seconds():.1f}초")

if __name__ == "__main__":
    check_timezone_handling()
