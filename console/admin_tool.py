# SVCMON 콘솔 도구 - 데이터베이스 관리 및 상태 확인
import os
import sys
import pyodbc
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class SVCMONAdmin:
    """SVCMON 관리 도구"""
    
    def __init__(self):
        self.connection_string = "Driver={ODBC Driver 17 for SQL Server};Server=devhakdb;Database=SVCMON;Trusted_Connection=yes;TrustServerCertificate=yes;"
        
    def get_connection(self):
        """데이터베이스 연결"""
        try:
            return pyodbc.connect(self.connection_string)
        except Exception as e:
            print(f"데이터베이스 연결 오류: {e}")
            return None
    
    def execute_query(self, query: str, params: List = None) -> List[Dict]:
        """쿼리 실행"""
        conn = self.get_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # 컬럼명 가져오기
            columns = [column[0] for column in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            
            # 딕셔너리 리스트로 변환
            result = []
            for row in rows:
                result.append(dict(zip(columns, row)))
            
            return result
            
        except Exception as e:
            print(f"쿼리 실행 오류: {e}")
            return []
        finally:
            conn.close()
    
    def execute_sp(self, sp_name: str, params: Dict = None) -> List[Dict]:
        """저장프로시저 실행"""
        conn = self.get_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            
            if params:
                param_list = list(params.values())
                cursor.execute(f"EXEC {sp_name} {','.join(['?' for _ in param_list])}", param_list)
            else:
                cursor.execute(f"EXEC {sp_name}")
            
            columns = [column[0] for column in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            
            result = []
            for row in rows:
                result.append(dict(zip(columns, row)))
            
            conn.commit()
            return result
            
        except Exception as e:
            print(f"저장프로시저 실행 오류: {e}")
            return []
        finally:
            conn.close()
    
    def show_dashboard_summary(self):
        """대시보드 요약 정보 표시"""
        print("\n" + "="*60)
        print("SVCMON 대시보드 요약")
        print("="*60)
        
        # 망구분별 상태
        networks = self.execute_sp('usp_dashboard_network_summary')
        if networks:
            print("\n[망구분별 현황]")
            print(f"{'망구분명':<20} {'상태':<8} {'도메인수':<8} {'엔드포인트수':<12} {'마지막변경':<20}")
            print("-" * 70)
            
            for net in networks:
                status_color = {
                    'GREEN': '🟢',
                    'AMBER': '🟡', 
                    'RED': '🔴'
                }.get(net['status'], '⚪')
                
                last_change = net['last_change_at'].strftime("%Y-%m-%d %H:%M") if net['last_change_at'] else "N/A"
                
                print(f"{net['name']:<20} {status_color}{net['status']:<7} {net['domain_count']:<8} {net['endpoint_count']:<12} {last_change:<20}")
        
        # 전체 통계
        stats = self.execute_query("""
            SELECT 
                COUNT(DISTINCT ng.id) as network_count,
                COUNT(DISTINCT d.id) as domain_count,
                COUNT(DISTINCT e.id) as total_endpoints,
                COUNT(DISTINCT CASE WHEN e.is_enabled = 1 THEN e.id END) as active_endpoints,
                COUNT(DISTINCT CASE WHEN r.last_status = 'GREEN' THEN e.id END) as green_count,
                COUNT(DISTINCT CASE WHEN r.last_status = 'AMBER' THEN e.id END) as amber_count,
                COUNT(DISTINCT CASE WHEN r.last_status = 'RED' THEN e.id END) as red_count
            FROM dbo.network_groups ng
            LEFT JOIN dbo.domains d ON ng.id = d.network_group_id
            LEFT JOIN dbo.endpoints e ON d.id = e.domain_id
            LEFT JOIN dbo.rollups r ON r.level = 'endpoint' AND r.ref_id = e.id
        """)
        
        if stats:
            stat = stats[0]
            print(f"\n[전체 통계]")
            print(f"망구분: {stat['network_count']}개")
            print(f"도메인: {stat['domain_count']}개") 
            print(f"엔드포인트: {stat['active_endpoints']}/{stat['total_endpoints']}개 (활성/전체)")
            print(f"상태별: 🟢{stat['green_count']} 🟡{stat['amber_count']} 🔴{stat['red_count']}")
    
    def show_recent_checks(self, limit: int = 10):
        """최근 체크 결과 표시"""
        print(f"\n[최근 체크 결과 {limit}건]")
        print(f"{'시간':<17} {'URL':<40} {'상태':<8} {'응답시간':<8} {'오류':<30}")
        print("-" * 105)
        
        checks = self.execute_query(f"""
            SELECT TOP {limit}
                c.checked_at,
                e.url,
                c.status_code,
                c.latency_ms,
                c.error
            FROM dbo.checks c
            INNER JOIN dbo.endpoints e ON c.endpoint_id = e.id
            ORDER BY c.checked_at DESC
        """)
        
        for check in checks:
            time_str = check['checked_at'].strftime("%m-%d %H:%M:%S") if check['checked_at'] else "N/A"
            url = (check['url'][:37] + "...") if len(check['url']) > 40 else check['url']
            
            if check['status_code'] == 200:
                status = "🟢 200"
            elif check['status_code'] is None:
                status = "🟡 NULL"
            else:
                status = f"🔴 {check['status_code']}"
            
            latency = f"{check['latency_ms']}ms" if check['latency_ms'] else "N/A"
            error = (check['error'][:27] + "...") if check['error'] and len(check['error']) > 30 else (check['error'] or "")
            
            print(f"{time_str:<17} {url:<40} {status:<8} {latency:<8} {error:<30}")
    
    def show_problem_endpoints(self):
        """문제가 있는 엔드포인트 표시"""
        print("\n[문제 엔드포인트]")
        
        problems = self.execute_query("""
            SELECT 
                e.url,
                d.domain,
                ng.name as network_group,
                r.last_status,
                r.last_reason,
                r.last_change_at,
                latest_check.checked_at as last_checked
            FROM dbo.endpoints e
            INNER JOIN dbo.domains d ON e.domain_id = d.id
            INNER JOIN dbo.network_groups ng ON d.network_group_id = ng.id
            LEFT JOIN dbo.rollups r ON r.level = 'endpoint' AND r.ref_id = e.id
            OUTER APPLY (
                SELECT TOP 1 checked_at
                FROM dbo.checks c
                WHERE c.endpoint_id = e.id
                ORDER BY c.checked_at DESC
            ) latest_check
            WHERE e.is_enabled = 1 
              AND (r.last_status IN ('RED', 'AMBER') OR r.last_status IS NULL)
            ORDER BY r.last_change_at DESC
        """)
        
        if not problems:
            print("🎉 문제가 있는 엔드포인트가 없습니다!")
            return
        
        print(f"{'URL':<40} {'망구분':<15} {'상태':<8} {'이유':<25} {'변경시간':<17}")
        print("-" * 105)
        
        for problem in problems:
            url = (problem['url'][:37] + "...") if len(problem['url']) > 40 else problem['url']
            network = (problem['network_group'][:12] + "...") if len(problem['network_group']) > 15 else problem['network_group']
            
            status_icon = {
                'RED': '🔴',
                'AMBER': '🟡'
            }.get(problem['last_status'], '⚪')
            
            status = f"{status_icon} {problem['last_status'] or 'NULL'}"
            reason = (problem['last_reason'][:22] + "...") if problem['last_reason'] and len(problem['last_reason']) > 25 else (problem['last_reason'] or "N/A")
            change_time = problem['last_change_at'].strftime("%m-%d %H:%M:%S") if problem['last_change_at'] else "N/A"
            
            print(f"{url:<40} {network:<15} {status:<8} {reason:<25} {change_time:<17}")
    
    def cleanup_old_data(self, days: int = 180):
        """오래된 데이터 정리"""
        print(f"\n{days}일 이전 체크 데이터를 정리합니다...")
        
        result = self.execute_sp('usp_cleanup_old_checks', {'retention_days': days})
        
        if result:
            res = result[0]
            print(f"결과: {res['message']}")
        else:
            print("데이터 정리 실행에 실패했습니다.")
    
    def show_settings(self):
        """시스템 설정 표시"""
        print("\n[시스템 설정]")
        
        settings = self.execute_query("SELECT [key], [value], description FROM dbo.settings ORDER BY [key]")
        
        if not settings:
            print("설정된 항목이 없습니다.")
            return
        
        print(f"{'키':<30} {'값':<20} {'설명':<40}")
        print("-" * 90)
        
        for setting in settings:
            key = setting['key'][:27] + "..." if len(setting['key']) > 30 else setting['key']
            value = setting['value'][:17] + "..." if len(setting['value']) > 20 else setting['value']
            desc = setting['description'][:37] + "..." if setting['description'] and len(setting['description']) > 40 else (setting['description'] or "")
            
            print(f"{key:<30} {value:<20} {desc:<40}")
    
    def show_menu(self):
        """메뉴 표시"""
        print("\n" + "="*50)
        print("SVCMON 관리 도구")
        print("="*50)
        print("1. 대시보드 요약")
        print("2. 최근 체크 결과 (10건)")
        print("3. 문제 엔드포인트 목록")
        print("4. 시스템 설정 보기")
        print("5. 오래된 데이터 정리 (180일)")
        print("6. 종료")
        print("="*50)

def main():
    """메인 함수"""
    admin = SVCMONAdmin()
    
    # 연결 테스트
    if not admin.get_connection():
        print("데이터베이스에 연결할 수 없습니다.")
        print("연결 문자열을 확인하세요.")
        sys.exit(1)
    
    print("SVCMON 관리 도구에 오신 것을 환영합니다!")
    
    while True:
        admin.show_menu()
        try:
            choice = input("선택하세요 (1-6): ").strip()
            
            if choice == '1':
                admin.show_dashboard_summary()
            elif choice == '2':
                admin.show_recent_checks()
            elif choice == '3':
                admin.show_problem_endpoints()
            elif choice == '4':
                admin.show_settings()
            elif choice == '5':
                days = input("보관 기간 입력 (기본값: 180일): ").strip()
                try:
                    days = int(days) if days else 180
                    admin.cleanup_old_data(days)
                except ValueError:
                    print("올바른 숫자를 입력하세요.")
            elif choice == '6':
                print("프로그램을 종료합니다.")
                break
            else:
                print("잘못된 선택입니다. 1-6 사이의 숫자를 입력하세요.")
                
        except KeyboardInterrupt:
            print("\n프로그램을 종료합니다.")
            break
        except Exception as e:
            print(f"오류 발생: {e}")
        
        input("\n계속하려면 Enter를 누르세요...")

if __name__ == "__main__":
    main()
