# SVCMON 콘솔 프로그램 (망구분별)
전남대학교 웹사이트 모니터링 시스템 - Windows 서비스

## 개요
SVCMON 콘솔 프로그램은 등록된 웹사이트들을 주기적으로 모니터링하여 상태를 데이터베이스에 기록하는 Windows 서비스입니다.
**망구분별로 독립적인 서비스 인스턴스를 실행할 수 있습니다.**

## 주요 기능
- 🔍 **웹사이트 상태 모니터링**: HTTP 응답 코드, 응답 시간 측정
- ⚡ **비동기 처리**: aiohttp를 사용한 고성능 동시 처리
- 🗄️ **데이터베이스 연동**: MS SQL Server 저장프로시저 기반 데이터 처리
- 🪟 **Windows 서비스**: 백그라운드에서 자동 실행
- 📊 **상태 집계**: 엔드포인트/도메인/망구분별 상태 롤업
- 🌐 **망구분별 실행**: 망구분별로 독립적인 모니터링 서비스 실행
- 🔧 **관리 도구**: 설치, 상태 확인, 데이터 정리 도구 제공

## 시스템 요구사항
- Windows 10/11 또는 Windows Server 2016 이상
- Python 3.8 이상
- MS SQL Server 2019 이상
- ODBC Driver 17 for SQL Server

## 설치 및 설정

### 1. 의존성 설치
```powershell
cd console
pip install -r requirements.txt
```

### 2. 데이터베이스 설치
```powershell
python install.py
```

### 3. 망구분별 서비스 설치 (관리자 권한 필요)

#### 전체 망구분 모니터링
```powershell
python service_manager.py install
```

#### 특정 망구분 모니터링 (예: INTERNAL)
```powershell
python service_manager.py --network-group-name INTERNAL --network-group-id 1 install
```

#### 다른 망구분 모니터링 (예: DMZ)
```powershell
python service_manager.py --network-group-name DMZ --network-group-id 2 install
```

### 4. 서비스 시작
```powershell
# 전체 망구분
python service_manager.py start

# 특정 망구분
python service_manager.py --network-group-name INTERNAL start
```

## 사용법

### 망구분별 서비스 관리
```powershell
# 특정 망구분 서비스 상태 확인
python service_manager.py --network-group-name INTERNAL status

# 특정 망구분 서비스 시작
python service_manager.py --network-group-name INTERNAL start

# 특정 망구분 서비스 중지  
python service_manager.py --network-group-name INTERNAL stop

# 특정 망구분 서비스 재시작
python service_manager.py --network-group-name INTERNAL restart

# 특정 망구분 서비스 제거
python service_manager.py --network-group-name INTERNAL remove

# 모든 SVCMON 서비스 목록 조회
python service_manager.py list
```

### 콘솔 모드 실행 (테스트용)
```powershell
# 전체 망구분 콘솔 모드
python svcmon_service.py

# 특정 망구분 콘솔 모드
python svcmon_service.py --network-group-name INTERNAL --network-group-id 1

# service_manager를 통한 콘솔 모드
python service_manager.py --network-group-name DMZ --network-group-id 2 console
```

### 관리 도구
```powershell
# 시스템 상태 확인 및 관리
python admin_tool.py
```

## 망구분별 실행 예시

### 시나리오: INTERNAL과 DMZ 망구분을 별도 서비스로 실행

1. **INTERNAL 망구분 서비스 설치 및 시작**
```powershell
# 서비스 설치
python service_manager.py --network-group-name INTERNAL --network-group-id 1 install

# 서비스 시작
python service_manager.py --network-group-name INTERNAL start
```

2. **DMZ 망구분 서비스 설치 및 시작**
```powershell
# 서비스 설치
python service_manager.py --network-group-name DMZ --network-group-id 2 install

# 서비스 시작
python service_manager.py --network-group-name DMZ start
```

3. **서비스 상태 확인**
```powershell
# 모든 SVCMON 서비스 목록
python service_manager.py list

# 특정 서비스 상태
sc query SVCMON_INTERNAL
sc query SVCMON_DMZ
```

## 구성 파일

### svcmon_service.py
- 메인 모니터링 서비스 로직 (망구분별 실행 지원)
- HTTP 체크 및 결과 저장
- Windows 서비스 래퍼

### service_manager.py
- 망구분별 서비스 설치/관리 도구
- Windows 서비스 관리
- 콘솔 모드 실행

### service_manager.py  
- 서비스 설치/제거/시작/중지 관리
- 대화형 메뉴 제공

### admin_tool.py
- 시스템 상태 모니터링
- 문제 엔드포인트 확인
- 데이터 정리 기능

### install.py
- 데이터베이스 스키마 설치
- 초기 설정 데이터 생성

## 로그 파일
- `svcmon_service.log`: 서비스 실행 로그
- Windows 이벤트 로그: 서비스 시작/중지 이벤트

## 데이터베이스 연결
기본 연결 문자열:
```
Server=devhakdb;Database=SVCMON;Trusted_Connection=True;MultipleActiveResultSets=true;Encrypt=no;
```

연결 문자열 수정이 필요한 경우 각 파일의 `connection_string` 변수를 수정하세요.

## 모니터링 로직

### 폴링 스케줄링
1. `usp_next_poll_batch` 저장프로시저로 체크 대상 조회
2. 마지막 체크 시간 + 폴링 간격 <= 현재 시간인 엔드포인트 선택
3. 배치 크기(기본 50개) 단위로 처리

### 상태 판정
- **GREEN**: HTTP 200 응답
- **AMBER**: 응답 없음 (타임아웃, 네트워크 오류)
- **RED**: HTTP 오류 응답 (4xx, 5xx)

### 롤업 처리
1. 엔드포인트 레벨: 최신 체크 결과
2. 도메인 레벨: 하위 엔드포인트 상태 집계
3. 망구분 레벨: 하위 도메인 상태 집계

## 문제 해결

### 서비스 설치 실패
- 관리자 권한으로 PowerShell 실행 확인
- pywin32 설치 확인: `pip install pywin32`

### 데이터베이스 연결 실패  
- SQL Server 서비스 실행 확인
- ODBC Driver 17 설치 확인
- 연결 문자열의 서버명/DB명 확인

### 모니터링 동작 안함
- 웹 애플리케이션에서 엔드포인트 등록 확인
- `admin_tool.py`로 엔드포인트 활성화 상태 확인
- 로그 파일에서 오류 메시지 확인

## 성능 튜닝

### 동시 실행 수 조정
`svcmon_service.py`에서 다음 값들을 조정:
- `max_concurrent`: 최대 동시 HTTP 요청 수 (기본 50)
- `batch_size`: 한 번에 처리할 엔드포인트 수 (기본 50)
- `timeout`: HTTP 요청 타임아웃 (기본 30초)

### 폴링 간격 조정
- 웹 애플리케이션에서 엔드포인트별 `poll_interval_sec` 설정
- 시스템 설정에서 `default_poll_interval` 조정

## 라이선스
전남대학교 내부 사용 목적으로 개발된 소프트웨어입니다.
