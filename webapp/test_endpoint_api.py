#!/usr/bin/env python
import os
import sys
import django
import requests
from urllib.parse import urljoin

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'svcmon.settings')
django.setup()

from monitoring.models import Endpoint

def test_endpoint_api():
    """엔드포인트 API 테스트"""
    # 첫 번째 엔드포인트 가져오기
    endpoints = Endpoint.objects.all()
    if not endpoints:
        print("엔드포인트가 없습니다.")
        return
    
    endpoint = endpoints.first()
    print(f"테스트 엔드포인트: {endpoint.url} (ID: {endpoint.id})")
    
    # API URL 생성
    base_url = "http://127.0.0.1:8000"  # 개발 서버 URL
    api_url = f"{base_url}/api/endpoint/{endpoint.id}/chart/"
    
    print(f"API URL: {api_url}")
    
    try:
        response = requests.get(api_url, timeout=10)
        print(f"응답 상태: {response.status_code}")
        
        if response.status_code == 200:
            print("응답 내용:")
            print(response.text[:500])  # 처음 500자만 출력
            try:
                data = response.json()
                print("API 응답 데이터:")
                print(f"  - 현재 상태: {data.get('current_status')}")
                print(f"  - 최신 지연시간: {data.get('latest_latency')}")
                print(f"  - 차트 데이터 개수: {len(data.get('chart_data', []))}")
                print(f"  - 체크 기록 개수: {len(data.get('check_records', []))}")
                print(f"  - 마지막 업데이트: {data.get('last_updated')}")
            except Exception as json_error:
                print(f"JSON 파싱 오류: {json_error}")
        else:
            print(f"오류 응답: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"API 요청 오류: {e}")
    except Exception as e:
        print(f"기타 오류: {e}")

if __name__ == "__main__":
    test_endpoint_api()
