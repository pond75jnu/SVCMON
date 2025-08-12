#!/usr/bin/env python
import requests
import json

def test_dashboard_api():
    """대시보드 API 테스트"""
    print("=== 대시보드 API 테스트 ===")
    
    base_url = "http://127.0.0.1:8000"
    
    # 1. 홈 대시보드 API 테스트
    try:
        response = requests.get(f"{base_url}/api/dashboard/")
        if response.status_code == 200:
            data = response.json()
            print("✅ 홈 대시보드 API 성공")
            print(f"총 망구분: {len(data.get('network_groups', []))}")
            
            # 상태 분석
            for network in data.get('network_groups', [])[:3]:  # 상위 3개만
                print(f"망구분: {network['name']}")
                print(f"상태: {network['status']}")
                print(f"총 URL: {network['total_endpoints']}")
                print("-" * 30)
        else:
            print(f"❌ 홈 대시보드 API 실패: {response.status_code}")
    except Exception as e:
        print(f"❌ 홈 대시보드 API 오류: {e}")
    
    print("\n" + "="*50)
    
    # 2. 망구분 상세 API 테스트
    try:
        response = requests.get(f"{base_url}/api/network/1/detail/")
        if response.status_code == 200:
            data = response.json()
            print("✅ 망구분 상세 API 성공")
            print(f"망구분명: {data.get('network_group', {}).get('name', 'N/A')}")
            print(f"총 도메인: {len(data.get('domains', []))}")
            
            # 도메인별 상태 확인
            for domain in data.get('domains', [])[:3]:  # 상위 3개만
                print(f"도메인: {domain['domain']}")
                print(f"상태: {domain['status']}")
                print(f"총 URL: {domain['total_endpoints']}")
                print("-" * 30)
        else:
            print(f"❌ 망구분 상세 API 실패: {response.status_code}")
    except Exception as e:
        print(f"❌ 망구분 상세 API 오류: {e}")
    
    print("\n" + "="*50)
    
    # 3. 도메인 상세 API 테스트
    try:
        response = requests.get(f"{base_url}/api/domain/1/detail/")
        if response.status_code == 200:
            data = response.json()
            print("✅ 도메인 상세 API 성공")
            print(f"도메인명: {data.get('domain', {}).get('domain', 'N/A')}")
            print(f"총 URL: {len(data.get('endpoints', []))}")
            
            # URL별 상태 확인
            for endpoint in data.get('endpoints', [])[:3]:  # 상위 3개만
                print(f"URL: {endpoint['url']}")
                print(f"상태: {endpoint['status']}")
                print(f"호출주기: {endpoint['poll_interval_sec']}초")
                if endpoint.get('latest_check'):
                    print(f"최근 체크: {endpoint['latest_check']['checked_at']}")
                print("-" * 40)
        else:
            print(f"❌ 도메인 상세 API 실패: {response.status_code}")
    except Exception as e:
        print(f"❌ 도메인 상세 API 오류: {e}")

if __name__ == "__main__":
    test_dashboard_api()
