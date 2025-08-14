"""
AMBER 레코드 삽입 테스트
"""

import os
import sys
import django
from datetime import datetime, timezone, timedelta

# Django 설정
sys.path.append('d:/MyRepos/SVCMON/webapp')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'svcmon.settings')
django.setup()

# AMBER 서비스 테스트
from common.amber_service import AmberCheckService

def test_amber_insertion():
    print("AMBER 레코드 삽입 테스트 시작...")
    
    service = AmberCheckService()
    
    # 테스트용 엔드포인트 정보
    test_endpoint = {
        'endpoint_id': 1,
        'endpoint_url': 'https://www.jnu.ac.kr/jnumain.aspx',
        'poll_interval_seconds': 30
    }
    
    # 현재 시간에서 10분 전을 마지막 체크 시간으로 설정
    current_time = datetime.now(timezone.utc)
    last_checked_at = current_time - timedelta(minutes=10)
    
    print(f"현재 시간: {current_time}")
    print(f"가상 마지막 체크 시간: {last_checked_at}")
    print(f"경과 시간: {(current_time - last_checked_at).total_seconds()}초")
    print(f"임계값: {test_endpoint['poll_interval_seconds'] * 1.5}초")
    
    # AMBER 레코드 삽입 테스트
    print("\nAMBER 레코드 삽입 실행...")
    try:
        service._insert_amber_records(
            test_endpoint, 
            last_checked_at, 
            current_time, 
            test_endpoint['poll_interval_seconds']
        )
        print("AMBER 레코드 삽입 완료!")
    except Exception as e:
        print(f"AMBER 레코드 삽입 실패: {e}")
    
    # 삽입된 레코드 확인
    print("\n삽입된 AMBER 레코드 확인...")
    from common.database import DatabaseMiddleware
    db = DatabaseMiddleware()
    
    params = {'endpoint_id': test_endpoint['endpoint_id']}
    recent_checks = db.execute_sp('usp_get_last_check_time', params)
    
    if recent_checks:
        latest = recent_checks[0]
        print(f"최근 체크: {latest['last_checked_at']}")
        print(f"상태 코드: {latest['status_code']}")
        print(f"에러: {latest['error']}")
    
    # N/A 상태 레코드 조회
    try:
        import pyodbc
        conn_str = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=devhakdb;DATABASE=SVCMON;Trusted_Connection=yes;"
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT TOP 5 endpoint_id, status_code, checked_at, error 
            FROM checks 
            WHERE endpoint_id = ? AND status_code = 'N/A'
            ORDER BY checked_at DESC
        """, test_endpoint['endpoint_id'])
        
        na_records = cursor.fetchall()
        print(f"\nN/A 상태 레코드 수: {len(na_records)}")
        for record in na_records:
            print(f"  - 시간: {record.checked_at}, 에러: {record.error}")
            
        conn.close()
        
    except Exception as e:
        print(f"N/A 레코드 조회 실패: {e}")

if __name__ == '__main__':
    test_amber_insertion()
