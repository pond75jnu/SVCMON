#!/usr/bin/env python
import os
import sys
import django
import requests

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'svcmon.settings')
django.setup()

from monitoring.models import Endpoint

def test_url_resolution():
    """URL 해결 테스트"""
    # 첫 번째 엔드포인트 가져오기
    endpoints = Endpoint.objects.all()
    if not endpoints:
        print("엔드포인트가 없습니다.")
        return
    
    endpoint = endpoints.first()
    endpoint_id = endpoint.id
    
    print(f"테스트 엔드포인트: {endpoint.url} (ID: {endpoint_id})")
    
    # 다양한 API URL 패턴 테스트
    base_url = "http://127.0.0.1:8000"
    
    test_urls = [
        f"{base_url}/api/endpoint/{endpoint_id}/chart/",
        f"{base_url}/endpoint/{endpoint_id}/chart/api/",
        f"{base_url}/api/endpoint/{endpoint_id}/chart",
    ]
    
    for test_url in test_urls:
        print(f"\n테스트 URL: {test_url}")
        try:
            response = requests.get(test_url, timeout=10)
            print(f"응답 상태: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"JSON 응답 성공 - 상태: {data.get('current_status')}")
                except:
                    print("JSON 파싱 실패 - HTML 응답")
            elif response.status_code == 404:
                print("404 - URL을 찾을 수 없음")
            else:
                print(f"기타 응답: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"요청 오류: {e}")

if __name__ == "__main__":
    test_url_resolution()
