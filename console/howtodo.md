# SVCMON 콘솔 프로그램 사용법

## 📋 목차
1. [테스트용 사용 방법](#테스트용-사용-방법)
2. [Windows 서비스 등록 방법](#windows-서비스-등록-방법)
3. [서비스 관리](#서비스-관리)
4. [문제 해결](#문제-해결)

---

## 🧪 테스트용 사용 방법

### 1. 환경 준비
```powershell
# 콘솔 폴더로 이동
cd D:\MyRepos\SVCMON\console

# 필요한 패키지 설치
pip install -r requirements.txt
```

### 2. 데이터베이스 설치 (최초 1회)
```powershell
# 데이터베이스 스키마 및 초기 데이터 설치
python install.py
```

### 3. 콘솔 모드 테스트 실행

#### 전체 망구분 모니터링 테스트
```powershell
# 전체 망구분의 모든 엔드포인트 모니터링
python svcmon_service.py
```

#### 특정 망구분 모니터링 테스트
```powershell
# 교내망 망구분만 모니터링 (ID: 1)
python svcmon_service.py --network-group-name 교내망 --network-group-id 1

# DMZ 망구분만 모니터링 (ID: 2)
python svcmon_service.py --network-group-name DMZ --network-group-id 2

# INTERNAL 망구분만 모니터링 (ID: 3)
python svcmon_service.py --network-group-name INTERNAL --network-group-id 3
```

#### service_manager를 통한 콘솔 모드
```powershell
# 전체 망구분 콘솔 모드
python service_manager.py console

# 특정 망구분 콘솔 모드
python service_manager.py --network-group-name 교내망 --network-group-id 1 console
```

### 4. 테스트 결과 확인
- 콘솔 창에서 실시간 로그 확인
- `svcmon_service.log` 파일에서 상세 로그 확인
- 웹 대시보드에서 결과 확인: http://127.0.0.1:8000

---

## 🪟 Windows 서비스 등록 방법

### ⚠️ 중요사항
- **관리자 권한**으로 PowerShell 실행 필수
- 서비스 등록/해제 전에 기존 서비스 중지 권장

### 1. 전체 망구분 서비스 등록

#### 서비스 설치
```powershell
# 관리자 권한 PowerShell에서 실행
python service_manager.py install
```

#### 서비스 시작
```powershell
python service_manager.py start
```

### 2. 특정 망구분 서비스 등록

#### 교내망 서비스
```powershell
# 서비스 설치
python service_manager.py --network-group-name 교내망 --network-group-id 1 install

# 서비스 시작
python service_manager.py --network-group-name 교내망 start
```

#### DMZ 서비스
```powershell
# 서비스 설치
python service_manager.py --network-group-name DMZ --network-group-id 2 install

# 서비스 시작
python service_manager.py --network-group-name DMZ start
```

#### INTERNAL 서비스
```powershell
# 서비스 설치
python service_manager.py --network-group-name INTERNAL --network-group-id 3 install

# 서비스 시작
python service_manager.py --network-group-name INTERNAL start
```

### 3. 다중 망구분 서비스 운영 예시
```powershell
# 1. 교내망 서비스 설치 및 시작
python service_manager.py --network-group-name 교내망 --network-group-id 1 install
python service_manager.py --network-group-name 교내망 start

# 2. DMZ 서비스 설치 및 시작
python service_manager.py --network-group-name DMZ --network-group-id 2 install
python service_manager.py --network-group-name DMZ start

# 3. INTERNAL 서비스 설치 및 시작
python service_manager.py --network-group-name INTERNAL --network-group-id 3 install
python service_manager.py --network-group-name INTERNAL start
```

---

## 🔧 서비스 관리

### 서비스 상태 확인
```powershell
# 모든 SVCMON 서비스 목록
python service_manager.py list

# 특정 서비스 상태 확인
python service_manager.py --network-group-name 교내망 status

# Windows 서비스 관리자에서 확인
sc query SVCMON_교내망
sc query SVCMON_DMZ
sc query SVCMON_INTERNAL
```

### 서비스 제어
```powershell
# 서비스 중지
python service_manager.py --network-group-name 교내망 stop

# 서비스 재시작
python service_manager.py --network-group-name 교내망 restart

# 서비스 제거
python service_manager.py --network-group-name 교내망 remove
```

### 로그 확인
```powershell
# 서비스 로그 파일 확인
type svcmon_service.log
type svcmon_교내망.log
type svcmon_DMZ.log

# 실시간 로그 모니터링 (PowerShell)
Get-Content svcmon_service.log -Wait -Tail 20
```

### 관리 도구 사용
```powershell
# 시스템 상태 확인 및 관리
python admin_tool.py
```

---

## 🚨 문제 해결

### 일반적인 문제들

#### 1. 서비스 설치 실패
**증상**: "액세스가 거부되었습니다" 오류
**해결방법**:
```powershell
# 관리자 권한으로 PowerShell 실행 후 재시도
python service_manager.py --network-group-name 교내망 install
```

#### 2. 데이터베이스 연결 실패
**증상**: "연결할 수 없습니다" 오류
**해결방법**:
```powershell
# 1. SQL Server 서비스 확인
services.msc

# 2. 연결 문자열 확인 (각 .py 파일에서)
Server=devhakdb;Database=SVCMON;Trusted_Connection=True;MultipleActiveResultSets=true;Encrypt=no;

# 3. ODBC Driver 17 설치 확인
```

#### 3. 모니터링이 동작하지 않음
**확인사항**:
- 웹 애플리케이션에서 엔드포인트 등록 여부
- 엔드포인트 활성화 상태 (`is_enabled = True`)
- 네트워크 연결 상태

**디버깅**:
```powershell
# 콘솔 모드로 실행하여 로그 확인
python svcmon_service.py --network-group-name 교내망

# 관리 도구로 상태 점검
python admin_tool.py
```

#### 4. 서비스가 시작되지 않음
```powershell
# 1. 서비스 상태 확인
python service_manager.py --network-group-name 교내망 status

# 2. 서비스 재설치
python service_manager.py --network-group-name 교내망 remove
python service_manager.py --network-group-name 교내망 install
python service_manager.py --network-group-name 교내망 start

# 3. Windows 이벤트 로그 확인
eventvwr.msc
```

### 성능 튜닝

#### 동시 실행 수 조정 (svcmon_service.py)
```python
# 최대 동시 HTTP 요청 수
max_concurrent = 50

# 한 번에 처리할 엔드포인트 수  
batch_size = 50

# HTTP 요청 타임아웃
timeout = 30
```

#### 폴링 간격 조정
- 웹 애플리케이션에서 엔드포인트별 `poll_interval_sec` 설정
- 기본값: 30초

### 유용한 명령어 모음

#### 빠른 서비스 재시작
```powershell
# 교내망 서비스 빠른 재시작
python service_manager.py --network-group-name 교내망 restart
```

#### 모든 서비스 한번에 관리
```powershell
# 모든 SVCMON 서비스 중지
python service_manager.py --network-group-name 교내망 stop
python service_manager.py --network-group-name DMZ stop
python service_manager.py --network-group-name INTERNAL stop

# 모든 SVCMON 서비스 시작
python service_manager.py --network-group-name 교내망 start
python service_manager.py --network-group-name DMZ start  
python service_manager.py --network-group-name INTERNAL start
```

#### 로그 분석
```powershell
# 최근 오류 로그 확인
Select-String -Path "svcmon_service.log" -Pattern "ERROR" | Select-Object -Last 10

# 특정 망구분 로그 필터링
Select-String -Path "svcmon_service.log" -Pattern "교내망"
```

---

## 📝 요약

### 테스트 시작하기
1. `pip install -r requirements.txt`
2. `python install.py` (최초 1회)
3. `python svcmon_service.py --network-group-name 교내망` (콘솔 모드 테스트)

### 서비스 등록하기
1. **관리자 권한** PowerShell 실행
2. `python service_manager.py --network-group-name 교내망 --network-group-id 1 install`
3. `python service_manager.py --network-group-name 교내망 start`

### 문제 발생시
1. 로그 파일 확인: `svcmon_service.log`
2. 콘솔 모드로 디버깅: `python svcmon_service.py`
3. 관리 도구 사용: `python admin_tool.py`

---

**💡 팁**: 처음 사용할 때는 콘솔 모드로 테스트해보고, 정상 동작 확인 후 Windows 서비스로 등록하는 것을 권장합니다.
