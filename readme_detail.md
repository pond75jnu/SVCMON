
# 개요

-	주요 웹사이트의 health check용 [웹 애플리케이션]과 [콘솔프로그램] 개발

---

## 1) 범위(스코프)

- **헬스체크 대상**: HTTP/HTTPS URL (GET 호출 기본)
- **상태 판정**: 응답코드 200이면 정상, 그 외(비200/타임아웃/연결실패/SSL오류/해석불가)는 장애. **3xx도 장애로 처리**. 세부 사유는 코드/에러메시지로 기록
- **주기적 호출**: 망구분/도메인/URL 레벨에서 각각 주기 설정 가능(초·분). 상향레벨 일괄적용 허용
- **보관/관측성**: 응답코드, 지연(ms), 응답헤더, 호출시각 저장. 최근 10회 시계열 그래프 제공

---

## 2) 용어 정의

- **망구분(NetworkGroup)**: 교내망, KT망 등 상위 카테고리
- **도메인(Domain)**: 도메인명, 사이트명, 담당자 등 메타
- **URL(Endpoint)**: 실제 호출 대상 URL. DB 연결 필요여부 플래그 포함
- **상태(Status)**: 정상(GREEN), 신호없음/미응답(AMBER), 장애(RED); 우선순위 RED>AMBER>GREEN

---

## 3) 고수준 아키텍처

- **Web**: Django + MS SQL 2019 (mssql-django), Tailwind, Noto Sans KR
- **Console**: Python 3.11+, Windows 10+, pywin32 서비스. 비동기/병렬 호출, 설정 변경시 핫리로드
- **DB I/O 원칙**: 모든 입출력은 **저장프로시저(Stored Procedure)** 경유. SP 호출용 **미들웨어 클래스** 공통화

---

## 4) 데이터 모델(논리)

### 4.1 테이블

- **users**(id, username, email, phone, pw_hash, role[admin|user], is_active, approved_by, approved_at, created_at, updated_at)
- **network_groups**(id, name, note, created_at, updated_at)
- **domains**(id, network_group_id FK, domain, site_name, owner_name, note, created_at, updated_at)
- **endpoints**(id, domain_id FK, url, requires_db BIT, note, poll_interval_sec INT NULL, email_on_failure BIT NULL, is_enabled BIT, created_at, updated_at)
- **checks**(id, endpoint_id FK, status_code INT NULL, latency_ms INT NULL, headers NVARCHAR(MAX) NULL, error NVARCHAR(4000) NULL, checked_at DATETIME2, trace_id UNIQUEIDENTIFIER DEFAULT NEWID())
- **rollups**(id, level[network|domain|endpoint], ref_id, last_status[GREEN|AMBER|RED], last_change_at, last_reason NVARCHAR(400), updated_at)
- **settings**(id, key, value, updated_at) — 예: 전역 타임아웃, 동시성, 메일서버, 보존기간 등
- **config_revisions**(id, reason, changed_by, changed_at) — 변경 발생 시 증가; 콘솔이 구독하여 리셋 트리거로 사용
- **notifications**(id, endpoint_id, level, title, body, sent_to, sent_at, dedupe_key, status[SENT|SKIPPED|FAILED])

### 4.2 인덱스/보존

- **checks**: (endpoint_id, checked_at DESC) 커버링 인덱스. **보존기간 최대 6개월**(정책값) 후 파티션/정리 SP로 삭제
- **rollups**: (level, ref_id) 유니크

### 4.3 상태 판정 규칙(제안)

- **GREEN**: 최근 호출이 200
- **AMBER**: 최근 호출 결과 없음(주기×2 경과) 또는 429 등 임시적 비정상
- **RED**: 3xx/4xx/5xx/타임아웃/연결불가/SSL오류

---

## 5) 저장프로시저 규격(대표)

> 네이밍: `usp_<영역>_<동사>`

- 구성/CRUD
  - `usp_user_create/update/delete/approve`
  - `usp_network_group_upsert/delete`
  - `usp_domain_upsert/delete`
  - `usp_endpoint_upsert/delete/clone_from_group`(다른 망구분 하위 내용 복사 등록)
  - `usp_setting_upsert`
  - `usp_config_revision_bump(reason)`
- 조회/롤업
  - `usp_dashboard_network_summary()` → 각 망구분의 색상/카운트
  - `usp_dashboard_domain_summary(@network_group_id)`
  - `usp_endpoint_list(@domain_id)`
  - `usp_endpoint_recent_series(@endpoint_id, @limit=10)`
  - `usp_rollup_update(level, ref_id)` — checks 기반으로 색상 갱신
- 수집기(콘솔) 보조
  - `usp_next_poll_batch(@now, @limit, @max_concurrency)` — 호출 순서/대상 추출
  - `usp_record_check(@endpoint_id, @status_code, @latency_ms, @headers, @error, @checked_at)`
  - `usp_reset_trigger_get()` / `usp_reset_trigger_ack(@revision_id)`

---

## 6) Django 백엔드 API 규격(요약)

- 인증: Django auth + 세션/토큰(운영은 세션 권장). 비밀번호 정책·2FA(옵션)
- 엔드포인트(예)
  - `POST /auth/signup`(email, phone 필수) → 승인대기
  - `POST /auth/login`, `POST /auth/logout`
  - `GET/POST /admin/users`(승인/비번초기화/비활성)
  - `GET/POST /network-groups`
  - `GET/POST /domains`
  - `GET/POST /endpoints`(+ 그룹복제)
  - `GET /dashboard`(망구분 썸네일 상태)
  - `GET /dashboard/{network_group_id}`(도메인 썸네일 상태)
  - `GET /domains/{id}/endpoints`(리스트)
  - `GET /endpoints/{id}/series?limit=10`(최근 10회)
  - `POST /settings`(주기 일괄적용/메일알림 정책)

> 모든 DB 접근은 SP 호출 전용 **Repository/Service 클래스** 사용

---

## 7) UI 규격(요약)

- **메뉴**: 홈(대시보드) / 웹URL 등록 / 모니터링 상태 / 모니터링 설정 / 회원관리
- **대시보드(홈)**: 망구분 카드형(rounded) — 색상: RED/AMBER/GREEN. 클릭 시 도메인 카드로 드릴다운, 다시 엔드포인트 테이블로 진입. 각 엔드포인트 행에 현재 상태/최근 호출시각. 상세 화면에서 **최근 10회 꺾은선 그래프**(x=호출시간, y=응답속도)
- **스타일**: Tailwind + Noto Sans KR. 반응형, 접근성 대비 준수

---

## 8) 콘솔(Windows 서비스) 설계

- **실행형태**: pywin32 서비스. 단독 실행(개발 모드)도 지원
- **호출**: 비동기(Asyncio/ThreadPool) + 연결 수 제한. 타임아웃(기본 10s), 재시도(옵션)
- **스케줄링**: DB `usp_next_poll_batch`로 대상 배정; 완료 후 `usp_record_check`
- **리셋 감지**: `config_revisions`를 폴링/DB SIGNAL로 감지하여 워커 풀을 재구성(추가/삭제/주기변경 시)
- **헤더 처리**: 원문을 JSON 문자열로 저장(최대 길이 방어)
- **병렬정책**: 망구분/도메인 round-robin + URL id 정렬 기준

---

## 9) 알림/정책

- **이메일 발송**: 장애 발생 시 사용자 통지(엔드포인트/도메인/망구분 설정에 따름). 동일 원인 반복 알림 방지(dedupe 창구시간)
- **정책 일괄적용**: 망구분/도메인/URL 레벨 일괄적용 API 제공

---

## 10) 보안·운영·감사

- **초기 관리자**: 설치 마법사에서 최초 관리자 생성(기본 ID/PW 하드코딩 금지). 환경변수/비밀저장소 활용
- **비밀번호 정책**: 길이/복잡도/만료(옵션), 비밀번호 변경 이력
- **로그/감사**: 관리작업(등록/수정/삭제/정책변경) `config_revisions`와 감사로그 저장
- **SMTP/DB 시크릿**: .env + OS 비밀 저장소. 연결문자열은 배포환경에서 주입

---

## 11) 테스트/품질

- **단위**: SP별, Repository, 상태판정 유닛테스트
- **통합**: Dev SQL Server 컨테이너/인스턴스 사용, API/콘솔 E2E
- **성능**: 500 URL 기준 동시 50 호출에서 95퍼센타일 2s 내 기록/저장. 대시보드 1s 내 렌더
- **신뢰성**: 콘솔 비정상 종료 대비 재기동 시 미완료 작업 복구

---

## 12) 수용 기준(Acceptance Criteria)

- **등록/주기**: 망구분/도메인/URL CRUD 및 일괄적용 동작. URL별 주기 반영 확인
- **대시보드**: 색상 규칙(RED>AMBER>GREEN) 정확; RED/AMBER 사례 시뮬레이션 통과
- **그래프**: 최근 10회 데이터 X=시간, Y=ms로 라인 차트 표시
- **알림**: RED 전환 시 이메일 발송·중복 억제 동작
- **리셋**: URL 추가/삭제/주기변경 시 콘솔 워커가 1분 내 재구성
