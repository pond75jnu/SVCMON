# SVCMON 시스템 설치 스크립트
# 데이터베이스 스키마 설치 및 초기 설정
import os
import sys
import pyodbc
from datetime import datetime

class SVCMONInstaller:
    """SVCMON 시스템 설치"""
    
    def __init__(self):
        self.connection_string = "Driver={ODBC Driver 17 for SQL Server};Server=devhakdb;Database=SVCMON;Trusted_Connection=yes;TrustServerCertificate=yes;"
        
    def get_connection(self):
        """데이터베이스 연결"""
        try:
            return pyodbc.connect(self.connection_string)
        except Exception as e:
            print(f"데이터베이스 연결 오류: {e}")
            return None
    
    def execute_sql_file(self, file_path: str) -> bool:
        """SQL 파일 실행"""
        if not os.path.exists(file_path):
            print(f"오류: {file_path} 파일을 찾을 수 없습니다.")
            return False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # GO로 구분된 배치들을 분리
            batches = []
            current_batch = []
            
            for line in sql_content.split('\n'):
                line = line.strip()
                if line.upper() == 'GO':
                    if current_batch:
                        batches.append('\n'.join(current_batch))
                        current_batch = []
                else:
                    current_batch.append(line)
            
            # 마지막 배치 추가
            if current_batch:
                batches.append('\n'.join(current_batch))
            
            # 각 배치 실행
            conn = self.get_connection()
            if not conn:
                return False
            
            try:
                cursor = conn.cursor()
                
                for i, batch in enumerate(batches):
                    batch = batch.strip()
                    if not batch or batch.startswith('--'):
                        continue
                    
                    try:
                        cursor.execute(batch)
                        conn.commit()
                    except Exception as e:
                        error_msg = str(e)
                        # 이미 존재하는 객체 오류는 무시
                        if "이미 있습니다" in error_msg or "already exists" in error_msg:
                            print(f"⚠️ 배치 {i+1}: 객체가 이미 존재합니다 (무시)")
                            continue
                        else:
                            print(f"배치 {i+1} 실행 오류: {e}")
                            print(f"SQL: {batch[:100]}...")
                            return False
                
                print(f"✅ {os.path.basename(file_path)} 실행 완료")
                return True
                
            finally:
                conn.close()
                
        except Exception as e:
            print(f"파일 실행 오류: {e}")
            return False
    
    def install_database(self):
        """데이터베이스 스키마 설치"""
        print("=== 데이터베이스 스키마 설치 ===")
        
        # 상위 디렉토리의 database 폴더에서 SQL 파일들 찾기
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        database_dir = os.path.join(base_dir, 'database')
        
        if not os.path.exists(database_dir):
            print(f"오류: {database_dir} 디렉토리를 찾을 수 없습니다.")
            return False
        
        # SQL 파일들을 순서대로 실행
        sql_files = [
            '01_create_tables.sql',
            '02_user_procedures.sql', 
            '03_monitoring_procedures.sql',
            '04_dashboard_procedures.sql',
            '05_console_procedures.sql'
        ]
        
        success = True
        for sql_file in sql_files:
            file_path = os.path.join(database_dir, sql_file)
            if not self.execute_sql_file(file_path):
                success = False
                break
        
        if success:
            print("✅ 데이터베이스 스키마 설치 완료")
        else:
            print("❌ 데이터베이스 스키마 설치 실패")
        
        return success
    
    def create_initial_data(self):
        """초기 데이터 생성"""
        print("=== 초기 데이터 생성 ===")
        
        conn = self.get_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            
            # 기본 설정 데이터
            settings = [
                ('notification_dedupe_minutes', '30', '알림 중복 제거 시간 (분)'),
                ('max_check_history_days', '180', '체크 기록 보관 기간 (일)'),
                ('default_poll_interval', '300', '기본 폴링 간격 (초)'),
                ('email_from', 'noreply@jnu.ac.kr', '알림 이메일 발신자'),
                ('smtp_server', 'smtp.jnu.ac.kr', 'SMTP 서버'),
                ('smtp_port', '587', 'SMTP 포트'),
                ('dashboard_refresh_interval', '30', '대시보드 새로고침 간격 (초)')
            ]
            
            for key, value, desc in settings:
                try:
                    cursor.execute("""
                        IF NOT EXISTS (SELECT 1 FROM dbo.settings WHERE [key] = ?)
                        INSERT INTO dbo.settings ([key], [value], description, updated_at)
                        VALUES (?, ?, ?, GETDATE())
                    """, (key, key, value, desc))
                except Exception as e:
                    print(f"설정 추가 오류 ({key}): {e}")
            
            # 설정 업데이트 리비전 초기화
            try:
                cursor.execute("""
                    IF NOT EXISTS (SELECT 1 FROM dbo.config_revisions)
                    INSERT INTO dbo.config_revisions (revision, updated_at, updated_by)
                    VALUES (1, GETDATE(), 'SYSTEM')
                """)
            except Exception as e:
                print(f"리비전 초기화 오류: {e}")
            
            conn.commit()
            print("✅ 초기 데이터 생성 완료")
            return True
            
        except Exception as e:
            print(f"초기 데이터 생성 오류: {e}")
            return False
        finally:
            conn.close()
    
    def check_installation(self):
        """설치 상태 확인"""
        print("=== 설치 상태 확인 ===")
        
        conn = self.get_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            
            # 테이블 존재 확인
            tables = [
                'users', 'network_groups', 'domains', 'endpoints', 
                'checks', 'rollups', 'settings', 'config_revisions', 'notifications'
            ]
            
            print("테이블 존재 확인:")
            for table in tables:
                cursor.execute("""
                    SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
                    WHERE TABLE_NAME = ?
                """, (table,))
                
                exists = cursor.fetchone()[0] > 0
                status = "✅" if exists else "❌"
                print(f"  {status} {table}")
            
            # 저장프로시저 존재 확인
            print("\n저장프로시저 존재 확인:")
            cursor.execute("""
                SELECT name FROM sys.procedures 
                WHERE name LIKE 'usp_%'
                ORDER BY name
            """)
            
            procedures = [row[0] for row in cursor.fetchall()]
            print(f"  총 {len(procedures)}개 저장프로시저 발견")
            
            if len(procedures) > 0:
                print("  주요 프로시저:")
                for proc in procedures[:10]:  # 처음 10개만 표시
                    print(f"    ✅ {proc}")
                if len(procedures) > 10:
                    print(f"    ... 및 {len(procedures) - 10}개 더")
            
            # 설정 데이터 확인
            cursor.execute("SELECT COUNT(*) FROM dbo.settings")
            setting_count = cursor.fetchone()[0]
            print(f"\n설정 데이터: {setting_count}개 항목")
            
            print("\n✅ 설치 상태 확인 완료")
            return True
            
        except Exception as e:
            print(f"설치 상태 확인 오류: {e}")
            return False
        finally:
            conn.close()
    
    def install_all(self):
        """전체 설치"""
        print("SVCMON 시스템 설치를 시작합니다.")
        print("=" * 50)
        
        steps = [
            ("데이터베이스 스키마 설치", self.install_database),
            ("초기 데이터 생성", self.create_initial_data),
            ("설치 상태 확인", self.check_installation)
        ]
        
        for step_name, step_func in steps:
            print(f"\n{step_name}...")
            if not step_func():
                print(f"❌ {step_name} 실패")
                return False
        
        print("\n" + "=" * 50)
        print("🎉 SVCMON 시스템 설치가 완료되었습니다!")
        print("=" * 50)
        print("\n다음 단계:")
        print("1. Django 관리자 계정 생성: python ../webapp/manage.py create_admin")
        print("2. 웹 서버 시작: python ../webapp/manage.py runserver")
        print("3. 서비스 설치: python service_manager.py install")
        print("4. 서비스 시작: python service_manager.py start")
        
        return True

def main():
    """메인 함수"""
    print("SVCMON 시스템 설치 도구")
    print("=" * 30)
    
    installer = SVCMONInstaller()
    
    # 연결 테스트
    print("데이터베이스 연결 테스트...")
    if not installer.get_connection():
        print("❌ 데이터베이스에 연결할 수 없습니다.")
        print("연결 문자열을 확인하세요:")
        print(installer.connection_string)
        sys.exit(1)
    
    print("✅ 데이터베이스 연결 성공")
    
    # 설치 확인
    choice = input("\nSVCMON 시스템을 설치하시겠습니까? (y/N): ").strip().lower()
    
    if choice in ('y', 'yes'):
        success = installer.install_all()
        sys.exit(0 if success else 1)
    else:
        print("설치를 취소했습니다.")
        sys.exit(0)

if __name__ == "__main__":
    main()
