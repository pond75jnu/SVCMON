#!/usr/bin/env python
import os
import sys
import django
from datetime import timedelta
import pytz

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'svcmon.settings')
django.setup()

from django.utils import timezone
from monitoring.models import Endpoint, Check

print("=== 시간대 문제 분석 ===")

# 현재 시간 다양한 방법으로 확인
import datetime

current_utc = timezone.now()
current_local = timezone.localtime(current_utc)
current_system = datetime.datetime.now()

print(f"Django timezone.now() (UTC): {current_utc}")
print(f"Django localtime: {current_local}")
print(f"System datetime.now(): {current_system}")

# 시간대 설정 확인
from django.conf import settings
print(f"Django TIME_ZONE: {settings.TIME_ZONE}")
print(f"Django USE_TZ: {settings.USE_TZ}")

# DB 데이터 확인
endpoint = Endpoint.objects.filter(is_enabled=True).first()
if endpoint:
    latest_check = endpoint.checks.first()
    if latest_check:
        print(f"\nDB 체크 시간: {latest_check.checked_at}")
        print(f"DB 체크 시간 (로컬 변환): {timezone.localtime(latest_check.checked_at)}")
        
        # 시간 차이 계산
        time_diff = current_utc - latest_check.checked_at
        print(f"시간 차이: {time_diff}")
        print(f"시간 차이 (초): {time_diff.total_seconds()}")
        
        # 만약 DB에 KST가 UTC로 저장되어 있다면 9시간을 빼야 함
        corrected_check_time = latest_check.checked_at - timedelta(hours=9)
        print(f"\n보정된 체크 시간 (9시간 차감): {corrected_check_time}")
        corrected_time_diff = current_utc - corrected_check_time
        print(f"보정된 시간 차이: {corrected_time_diff}")
        print(f"보정된 시간 차이 (초): {corrected_time_diff.total_seconds()}")
        
        # 호출주기와 비교
        expected_next_check = corrected_check_time + timedelta(seconds=endpoint.poll_interval_sec)
        print(f"보정된 예상 다음 체크: {expected_next_check}")
        
        is_overdue = current_utc > expected_next_check
        print(f"보정된 호출주기 초과 여부: {is_overdue}")
        
        if is_overdue:
            print(">>> 보정 후 결과: AMBER (신호없음)")
        else:
            print(">>> 보정 후 결과: GREEN (정상)")
