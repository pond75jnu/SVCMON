-- SVCMON 데이터베이스 스키마 생성 스크립트
-- 전남대학교 웹사이트 모니터링 시스템

USE [SVCMON]
GO

-- SET 옵션 설정
SET QUOTED_IDENTIFIER ON
SET ANSI_NULLS ON
GO

-- 데이터베이스가 없다면 생성
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = N'SVCMON')
BEGIN
    CREATE DATABASE [SVCMON]
    COLLATE SQL_Latin1_General_CP1_CI_AS
END
GO

USE [SVCMON]
GO

-- 기존 테이블 삭제 (역순으로)
IF OBJECT_ID('dbo.notifications', 'U') IS NOT NULL DROP TABLE dbo.notifications;
IF OBJECT_ID('dbo.checks', 'U') IS NOT NULL DROP TABLE dbo.checks;
IF OBJECT_ID('dbo.rollups', 'U') IS NOT NULL DROP TABLE dbo.rollups;
IF OBJECT_ID('dbo.config_revisions', 'U') IS NOT NULL DROP TABLE dbo.config_revisions;
IF OBJECT_ID('dbo.settings', 'U') IS NOT NULL DROP TABLE dbo.settings;
IF OBJECT_ID('dbo.endpoints', 'U') IS NOT NULL DROP TABLE dbo.endpoints;
IF OBJECT_ID('dbo.domains', 'U') IS NOT NULL DROP TABLE dbo.domains;
IF OBJECT_ID('dbo.network_groups', 'U') IS NOT NULL DROP TABLE dbo.network_groups;
IF OBJECT_ID('dbo.users', 'U') IS NOT NULL DROP TABLE dbo.users;
GO

-- 1. 사용자 테이블
CREATE TABLE dbo.users (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    username NVARCHAR(150) NOT NULL UNIQUE,
    email NVARCHAR(254) NOT NULL UNIQUE,
    phone NVARCHAR(20) NOT NULL,
    password_hash NVARCHAR(128) NOT NULL,
    role NVARCHAR(10) NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'user')),
    is_active BIT NOT NULL DEFAULT 0,
    is_staff BIT NOT NULL DEFAULT 0,
    is_superuser BIT NOT NULL DEFAULT 0,
    approved_by BIGINT NULL,
    approved_at DATETIME2 NULL,
    last_login DATETIME2 NULL,
    created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    updated_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    
    CONSTRAINT FK_users_approved_by FOREIGN KEY (approved_by) REFERENCES dbo.users(id)
);
GO

-- 2. 망구분 테이블
CREATE TABLE dbo.network_groups (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(100) NOT NULL UNIQUE,
    note NVARCHAR(MAX) NULL,
    created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    updated_at DATETIME2 NOT NULL DEFAULT GETDATE()
);
GO

-- 3. 도메인 테이블
CREATE TABLE dbo.domains (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    network_group_id BIGINT NOT NULL,
    domain NVARCHAR(255) NOT NULL,
    site_name NVARCHAR(255) NOT NULL,
    owner_name NVARCHAR(100) NOT NULL,
    note NVARCHAR(MAX) NULL,
    created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    updated_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    
    CONSTRAINT FK_domains_network_group FOREIGN KEY (network_group_id) REFERENCES dbo.network_groups(id) ON DELETE CASCADE,
    CONSTRAINT UQ_domains_network_domain UNIQUE (network_group_id, domain)
);
GO

-- 4. 엔드포인트 테이블
CREATE TABLE dbo.endpoints (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    domain_id BIGINT NOT NULL,
    url NVARCHAR(2000) NOT NULL,
    requires_db BIT NOT NULL DEFAULT 0,
    note NVARCHAR(MAX) NULL,
    poll_interval_sec INT NOT NULL DEFAULT 300,
    email_on_failure BIT NOT NULL DEFAULT 1,
    is_enabled BIT NOT NULL DEFAULT 1,
    created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    updated_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    
    CONSTRAINT FK_endpoints_domain FOREIGN KEY (domain_id) REFERENCES dbo.domains(id) ON DELETE CASCADE
);
GO

-- 5. 헬스체크 결과 테이블
CREATE TABLE dbo.checks (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    endpoint_id BIGINT NOT NULL,
    status_code INT NULL,
    latency_ms INT NULL,
    headers NVARCHAR(MAX) NULL,
    error NVARCHAR(4000) NULL,
    checked_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    trace_id UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
    
    CONSTRAINT FK_checks_endpoint FOREIGN KEY (endpoint_id) REFERENCES dbo.endpoints(id) ON DELETE CASCADE
);
GO

-- 6. 상태 롤업 테이블
CREATE TABLE dbo.rollups (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    level NVARCHAR(10) NOT NULL CHECK (level IN ('network', 'domain', 'endpoint')),
    ref_id BIGINT NOT NULL,
    last_status NVARCHAR(6) NOT NULL DEFAULT 'AMBER' CHECK (last_status IN ('GREEN', 'AMBER', 'RED')),
    last_change_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    last_reason NVARCHAR(400) NULL,
    updated_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    
    CONSTRAINT UQ_rollups_level_ref UNIQUE (level, ref_id)
);
GO

-- 7. 설정 테이블
CREATE TABLE dbo.settings (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    [key] NVARCHAR(100) NOT NULL UNIQUE,
    [value] NVARCHAR(MAX) NOT NULL,
    description NVARCHAR(500) NULL,
    updated_at DATETIME2 NOT NULL DEFAULT GETDATE()
);
GO

-- 8. 설정변경이력 테이블
CREATE TABLE dbo.config_revisions (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    reason NVARCHAR(500) NOT NULL,
    changed_by BIGINT NULL,
    changed_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    
    CONSTRAINT FK_config_revisions_user FOREIGN KEY (changed_by) REFERENCES dbo.users(id) ON DELETE SET NULL
);
GO

-- 9. 알림 테이블
CREATE TABLE dbo.notifications (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    endpoint_id BIGINT NOT NULL,
    level NVARCHAR(10) NOT NULL,
    title NVARCHAR(200) NOT NULL,
    body NVARCHAR(MAX) NOT NULL,
    sent_to NVARCHAR(254) NOT NULL,
    sent_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    dedupe_key NVARCHAR(100) NULL,
    status NVARCHAR(10) NOT NULL DEFAULT 'SENT' CHECK (status IN ('SENT', 'SKIPPED', 'FAILED')),
    
    CONSTRAINT FK_notifications_endpoint FOREIGN KEY (endpoint_id) REFERENCES dbo.endpoints(id) ON DELETE CASCADE
);
GO

-- 인덱스 생성
CREATE INDEX IX_users_username ON dbo.users (username);
CREATE INDEX IX_users_email ON dbo.users (email);
CREATE INDEX IX_users_role_active ON dbo.users (role, is_active);

CREATE INDEX IX_domains_network_group ON dbo.domains (network_group_id);
CREATE INDEX IX_domains_domain ON dbo.domains (domain);

CREATE INDEX IX_endpoints_domain ON dbo.endpoints (domain_id);
CREATE INDEX IX_endpoints_enabled ON dbo.endpoints (is_enabled);
CREATE INDEX IX_endpoints_poll_interval ON dbo.endpoints (poll_interval_sec);

-- 커버링 인덱스: 최근 체크 결과 조회용
CREATE INDEX IX_checks_endpoint_checked_at ON dbo.checks (endpoint_id, checked_at DESC) 
INCLUDE (status_code, latency_ms, headers, error, trace_id);

CREATE INDEX IX_checks_checked_at ON dbo.checks (checked_at DESC);
CREATE INDEX IX_checks_trace_id ON dbo.checks (trace_id);

CREATE INDEX IX_rollups_level_ref ON dbo.rollups (level, ref_id);
CREATE INDEX IX_rollups_status ON dbo.rollups (last_status);

CREATE INDEX IX_config_revisions_changed_at ON dbo.config_revisions (changed_at DESC);

CREATE INDEX IX_notifications_endpoint ON dbo.notifications (endpoint_id);
CREATE INDEX IX_notifications_sent_at ON dbo.notifications (sent_at DESC);
CREATE INDEX IX_notifications_dedupe ON dbo.notifications (dedupe_key) WHERE dedupe_key IS NOT NULL;

-- 기본 설정 데이터 삽입
INSERT INTO dbo.settings ([key], [value]) VALUES
('global_timeout_sec', '30'),
('max_concurrent_checks', '50'),
('smtp_server', 'smtp.gmail.com'),
('smtp_port', '587'),
('smtp_use_tls', 'true'),
('retention_days', '180'),
('console_poll_interval_sec', '60'),
('notification_dedupe_minutes', '30');
GO

PRINT 'SVCMON 데이터베이스 스키마가 성공적으로 생성되었습니다.';
