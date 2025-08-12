# SVCMON 시스템 설치 및 실행 가이드
전남대학교 웹사이트 모니터링 시스템 완전 설치 가이드

## 🚀 빠른 시작

### 1단계: 환경 준비
```powershell
# 프로젝트 디렉토리로 이동
cd d:\MyRepos\SVCMON

# Python 환경 확인 (3.8 이상 필요)
python --version
```

### 2단계: 웹 애플리케이션 설정
```powershell
cd webapp

# 의존성 설치
pip install -r requirements.txt

# 데이터베이스 마이그레이션
python manage.py migrate

# 관리자 계정 생성
python manage.py create_admin
```

### 3단계: 데이터베이스 스키마 설치
```powershell
cd ..\console

# 콘솔 의존성 설치
pip install -r requirements.txt

# 데이터베이스 스키마 및 저장프로시저 설치
python install.py
```

### 4단계: 웹 서버 시작
```powershell
cd ..\webapp

# 개발 서버 시작
python manage.py runserver
```

### 5단계: 웹 브라우저에서 설정
1. http://127.0.0.1:8000 접속
2. 생성한 관리자 계정으로 로그인
3. 망구분, 도메인, 엔드포인트 등록

### 6단계: 모니터링 서비스 시작
```powershell
# 새 PowerShell 창 (관리자 권한)
cd d:\MyRepos\SVCMON\console

# 서비스 설치
python service_manager.py install

# 서비스 시작
python service_manager.py start
```

## 📋 상세 설치 단계

### A. 시스템 요구사항 확인

#### 필수 소프트웨어
- Windows 10/11 또는 Windows Server 2016+
- Python 3.8+ (https://python.org)
- MS SQL Server 2019+ 
- ODBC Driver 17 for SQL Server

#### Python 패키지 설치
```powershell
# 웹 애플리케이션 패키지
pip install django==5.0.7 mssql-django djangorestframework Pillow

# 콘솔 프로그램 패키지
pip install aiohttp pyodbc pywin32 python-dateutil colorlog
```

### B. 데이터베이스 준비

#### 1. SQL Server 데이터베이스 생성
```sql
-- SQL Server Management Studio에서 실행
CREATE DATABASE SVCMON;
```

#### 2. 연결 문자열 확인
기본 설정: `Server=devhakdb;Database=SVCMON;Trusted_Connection=True;`

연결 문자열 수정이 필요한 경우:
- `webapp/svcmon/settings.py` 의 `DATABASES` 설정
- `console/svcmon_service.py` 의 `connection_string` 변수
- `console/admin_tool.py` 의 `connection_string` 변수  
- `console/install.py` 의 `connection_string` 변수

### C. 웹 애플리케이션 설정

#### 1. Django 설정
```powershell
cd webapp

# 정적 파일 수집
python manage.py collectstatic --noinput

# 데이터베이스 마이그레이션
python manage.py migrate

# 슈퍼유저 생성 (대화형)
python manage.py createsuperuser

# 또는 스크립트로 관리자 생성
python manage.py create_admin
```

#### 2. 개발 서버 시작
```powershell
# 기본 포트 (8000)
python manage.py runserver

# 사용자 지정 포트
python manage.py runserver 0.0.0.0:8080
```

### D. 데이터베이스 스키마 설치

#### 1. 자동 설치 (권장)
```powershell
cd console
python install.py
```

#### 2. 수동 설치
```powershell
# SQL 파일들을 순서대로 실행
sqlcmd -S devhakdb -d SVCMON -i ..\database\01_create_tables.sql
sqlcmd -S devhakdb -d SVCMON -i ..\database\02_user_procedures.sql
sqlcmd -S devhakdb -d SVCMON -i ..\database\03_monitoring_procedures.sql
sqlcmd -S devhakdb -d SVCMON -i ..\database\04_dashboard_procedures.sql
sqlcmd -S devhakdb -d SVCMON -i ..\database\05_console_procedures.sql
```

### E. 모니터링 서비스 설정

#### 1. 콘솔 모드 테스트
```powershell
cd console

# 직접 실행 (테스트용)
python svcmon_service.py
```

#### 2. Windows 서비스 설치
```powershell
# 관리자 권한 PowerShell에서 실행
python service_manager.py install

# 서비스 시작
python service_manager.py start

# 서비스 상태 확인
python service_manager.py status
```

### F. 초기 데이터 설정

#### 1. 웹 브라우저에서 설정
1. http://127.0.0.1:8000/admin 접속
2. 관리자 계정으로 로그인
3. 다음 순서로 데이터 등록:
   - Network groups (망구분)
   - Domains (도메인)  
   - Endpoints (엔드포인트)

#### 2. 예제 데이터
```
망구분: 학사정보시스템
  도메인: jinhakapply.jnu.ac.kr
    엔드포인트: https://jinhakapply.jnu.ac.kr/

망구분: 도서관시스템  
  도메인: library.jnu.ac.kr
    엔드포인트: https://library.jnu.ac.kr/
```

## 🔧 운영 및 관리

### 시스템 상태 확인
```powershell
cd console

# 관리 도구 실행
python admin_tool.py

# 대시보드 요약 정보
# 최근 체크 결과
# 문제 엔드포인트 목록
```

### 서비스 관리
```powershell
# 서비스 상태 확인
python service_manager.py status

# 서비스 재시작
python service_manager.py restart

# 서비스 로그 확인
type svcmon_service.log
```

### 웹 대시보드 확인
- http://127.0.0.1:8000/ - 메인 대시보드
- http://127.0.0.1:8000/admin/ - 관리자 페이지

## 🐛 문제 해결

### 자주 발생하는 오류

#### 1. "pyodbc 모듈을 찾을 수 없음"
```powershell
pip install pyodbc
```

#### 2. "ODBC 드라이버를 찾을 수 없음"
- Microsoft ODBC Driver 17 for SQL Server 설치
- https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server

#### 3. "데이터베이스 연결 실패"
- SQL Server 서비스 실행 상태 확인
- 연결 문자열의 서버명 확인
- Windows 인증 또는 SQL 인증 설정 확인

#### 4. "서비스 설치 실패"
- PowerShell을 관리자 권한으로 실행
- Windows 서비스 관련 권한 확인

#### 5. "마이그레이션 오류"
```powershell
# 마이그레이션 파일 삭제 후 재생성
rm webapp\*/migrations\0*.py
python manage.py makemigrations
python manage.py migrate
```

### 로그 확인 위치
- Django 로그: `webapp/logs/django.log`
- 서비스 로그: `console/svcmon_service.log`
- Windows 이벤트 로그: 이벤트 뷰어 > 애플리케이션

### 성능 최적화
1. 엔드포인트별 적절한 폴링 간격 설정 (기본 300초)
2. 동시 처리 수 조정 (`max_concurrent` 설정)
3. 오래된 체크 데이터 정기 정리

## 📞 지원

문제가 발생하면 다음 정보와 함께 문의:
1. 오류 메시지 전문
2. 로그 파일 내용
3. Python 버전 (`python --version`)
4. 운영체제 버전
5. SQL Server 버전

---
**주의**: 이 시스템은 전남대학교 내부 네트워크 환경에 최적화되어 있습니다.
