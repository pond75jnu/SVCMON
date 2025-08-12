#!/usr/bin/env python
import os
import sys
import django
from datetime import timedelta

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'svcmon.settings')
django.setup()

from django.utils import timezone
from monitoring.models import NetworkGroup, Endpoint, Check

print("=== API 응답 테스트 ===")

try:
    # 모든 망구분 상태 (all_networks_status_api_view와 동일한 로직)
    network_groups = NetworkGroup.objects.all()
    network_status = []
    
    current_time = timezone.now()
    print(f"현재 시간: {current_time}")
    
    for ng in network_groups:
        print(f"\n--- {ng.name} ---")
        
        # 해당 망구분의 모든 엔드포인트
        endpoints = Endpoint.objects.filter(
            domain__network_group=ng,
            is_enabled=True
        )
        
        # 상태 계산
        total_endpoints = endpoints.count()
        red_count = 0
        amber_count = 0
        green_count = 0
        
        for endpoint in endpoints:
            latest_check = endpoint.checks.first()
            
            if latest_check:
                # 호출주기 기반으로 신호 없음 판단
                expected_next_check = latest_check.checked_at + timedelta(seconds=endpoint.poll_interval_sec)
                
                if current_time > expected_next_check:
                    # 호출주기를 넘어서면 신호없음 (AMBER)
                    amber_count += 1
                elif (latest_check.status_code and 
                      200 <= latest_check.status_code < 300 and 
                      not latest_check.error):
                    # 성공 조건
                    green_count += 1
                else:
                    # 체크는 있지만 실패한 경우
                    red_count += 1
            else:
                # 체크 이력이 없는 경우
                amber_count += 1
        
        # 우선순위: RED > AMBER > GREEN
        # 등록된 엔드포인트가 없는 경우 AMBER로 표시
        if total_endpoints == 0:
            status = 'AMBER'
        elif red_count > 0:
            status = 'RED'
        elif amber_count > 0:
            status = 'AMBER'
        else:
            status = 'GREEN'
        
        print(f"총 엔드포인트: {total_endpoints}")
        print(f"정상: {green_count}, 신호없음: {amber_count}, 장애: {red_count}")
        print(f"최종 상태: {status}")
        
        network_status.append({
            'network_group_id': ng.id,
            'name': ng.name,
            'status': status,
            'total_endpoints': total_endpoints,
            'red_count': red_count,
            'amber_count': amber_count,
            'green_count': green_count,
        })
    
    print(f"\n=== API 응답 데이터 ===")
    for item in network_status:
        print(f"망구분: {item['name']}")
        print(f"  - 상태: {item['status']}")
        print(f"  - 정상: {item['green_count']}, 신호없음: {item['amber_count']}, 장애: {item['red_count']}")

except Exception as e:
    print(f"오류 발생: {e}")
    import traceback
    traceback.print_exc()
