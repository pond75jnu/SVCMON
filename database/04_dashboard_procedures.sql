-- SVCMON 대시보드 및 조회 저장프로시저
-- 전남대학교 웹사이트 모니터링 시스템

USE [SVCMON]
GO

-- 대시보드 망구분 요약
IF OBJECT_ID('dbo.usp_dashboard_network_summary', 'P') IS NOT NULL DROP PROCEDURE dbo.usp_dashboard_network_summary;
GO

CREATE PROCEDURE dbo.usp_dashboard_network_summary
AS
BEGIN
    SET NOCOUNT ON;
    
    SELECT 
        ng.id,
        ng.name,
        ng.note,
        COUNT(DISTINCT d.id) AS domain_count,
        COUNT(DISTINCT e.id) AS endpoint_count,
        COUNT(DISTINCT CASE WHEN e.is_enabled = 1 THEN e.id END) AS enabled_endpoint_count,
        ISNULL(r.last_status, 'AMBER') AS last_status,
        r.last_change_at,
        r.last_reason,
        ng.created_at
    FROM dbo.network_groups ng
    LEFT JOIN dbo.domains d ON ng.id = d.network_group_id
    LEFT JOIN dbo.endpoints e ON d.id = e.domain_id
    LEFT JOIN dbo.rollups r ON r.level = 'network' AND r.ref_id = ng.id
    GROUP BY ng.id, ng.name, ng.note, ng.created_at, r.last_status, r.last_change_at, r.last_reason
    ORDER BY ng.name;
END
GO

-- 대시보드 도메인 요약 (특정 망구분)
IF OBJECT_ID('dbo.usp_dashboard_domain_summary', 'P') IS NOT NULL DROP PROCEDURE dbo.usp_dashboard_domain_summary;
GO

CREATE PROCEDURE dbo.usp_dashboard_domain_summary
    @network_group_id BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    
    SELECT 
        d.id,
        d.domain,
        d.site_name,
        d.owner_name,
        d.note,
        COUNT(DISTINCT e.id) AS endpoint_count,
        COUNT(DISTINCT CASE WHEN e.is_enabled = 1 THEN e.id END) AS enabled_endpoint_count,
        ISNULL(r.last_status, 'AMBER') AS last_status,
        r.last_change_at,
        r.last_reason,
        d.created_at
    FROM dbo.domains d
    LEFT JOIN dbo.endpoints e ON d.id = e.domain_id
    LEFT JOIN dbo.rollups r ON r.level = 'domain' AND r.ref_id = d.id
    WHERE d.network_group_id = @network_group_id
    GROUP BY d.id, d.domain, d.site_name, d.owner_name, d.note, d.created_at, 
             r.last_status, r.last_change_at, r.last_reason
    ORDER BY d.domain;
END
GO

-- 엔드포인트 목록 (특정 도메인)
IF OBJECT_ID('dbo.usp_endpoint_list', 'P') IS NOT NULL DROP PROCEDURE dbo.usp_endpoint_list;
GO

CREATE PROCEDURE dbo.usp_endpoint_list
    @domain_id BIGINT = NULL,
    @network_group_id BIGINT = NULL,
    @is_enabled BIT = NULL,
    @page INT = 1,
    @page_size INT = 20
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @offset INT = (@page - 1) * @page_size;
    
    SELECT 
        e.id,
        e.url,
        e.requires_db,
        e.note,
        e.poll_interval_sec,
        e.email_on_failure,
        e.is_enabled,
        e.created_at,
        e.updated_at,
        d.id AS domain_id,
        d.domain,
        d.site_name,
        d.owner_name,
        ng.id AS network_group_id,
        ng.name AS network_group_name,
        latest_check.status_code,
        latest_check.latency_ms,
        latest_check.checked_at AS last_checked_at,
        latest_check.error AS last_error,
        ISNULL(r.last_status, 'AMBER') AS last_status,
        COUNT(*) OVER() AS total_count
    FROM dbo.endpoints e
    INNER JOIN dbo.domains d ON e.domain_id = d.id
    INNER JOIN dbo.network_groups ng ON d.network_group_id = ng.id
    LEFT JOIN dbo.rollups r ON r.level = 'endpoint' AND r.ref_id = e.id
    OUTER APPLY (
        SELECT TOP 1 status_code, latency_ms, checked_at, error
        FROM dbo.checks c
        WHERE c.endpoint_id = e.id
        ORDER BY c.checked_at DESC
    ) latest_check
    WHERE (@domain_id IS NULL OR e.domain_id = @domain_id)
      AND (@network_group_id IS NULL OR d.network_group_id = @network_group_id)
      AND (@is_enabled IS NULL OR e.is_enabled = @is_enabled)
    ORDER BY ng.name, d.domain, e.url
    OFFSET @offset ROWS FETCH NEXT @page_size ROWS ONLY;
END
GO

-- 엔드포인트 최근 체크 결과 시계열
IF OBJECT_ID('dbo.usp_endpoint_recent_series', 'P') IS NOT NULL DROP PROCEDURE dbo.usp_endpoint_recent_series;
GO

CREATE PROCEDURE dbo.usp_endpoint_recent_series
    @endpoint_id BIGINT,
    @limit INT = 10
AS
BEGIN
    SET NOCOUNT ON;
    
    SELECT TOP (@limit)
        c.id,
        c.status_code,
        c.latency_ms,
        c.headers,
        c.error,
        c.checked_at,
        c.trace_id,
        CASE 
            WHEN c.status_code = 200 THEN 'GREEN'
            WHEN c.status_code IS NULL THEN 'AMBER'
            ELSE 'RED'
        END AS status
    FROM dbo.checks c
    WHERE c.endpoint_id = @endpoint_id
    ORDER BY c.checked_at DESC;
END
GO

-- 전체 통계
IF OBJECT_ID('dbo.usp_dashboard_stats', 'P') IS NOT NULL DROP PROCEDURE dbo.usp_dashboard_stats;
GO

CREATE PROCEDURE dbo.usp_dashboard_stats
AS
BEGIN
    SET NOCOUNT ON;
    
    SELECT 
        (SELECT COUNT(*) FROM dbo.network_groups) AS total_network_groups,
        (SELECT COUNT(*) FROM dbo.domains) AS total_domains,
        (SELECT COUNT(*) FROM dbo.endpoints WHERE is_enabled = 1) AS total_enabled_endpoints,
        (SELECT COUNT(*) FROM dbo.endpoints) AS total_endpoints,
        (SELECT COUNT(*) FROM dbo.users WHERE is_active = 1) AS total_active_users,
        (SELECT COUNT(*) FROM dbo.users WHERE is_active = 0) AS total_pending_users,
        (SELECT COUNT(*) FROM dbo.checks WHERE checked_at >= DATEADD(hour, -24, GETDATE())) AS checks_last_24h,
        (SELECT COUNT(*) FROM dbo.rollups WHERE last_status = 'RED') AS red_count,
        (SELECT COUNT(*) FROM dbo.rollups WHERE last_status = 'AMBER') AS amber_count,
        (SELECT COUNT(*) FROM dbo.rollups WHERE last_status = 'GREEN') AS green_count;
END
GO

-- 설정 조회
IF OBJECT_ID('dbo.usp_setting_get', 'P') IS NOT NULL DROP PROCEDURE dbo.usp_setting_get;
GO

CREATE PROCEDURE dbo.usp_setting_get
    @key NVARCHAR(100) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    IF @key IS NULL
    BEGIN
        SELECT [key], [value], updated_at FROM dbo.settings ORDER BY [key];
    END
    ELSE
    BEGIN
        SELECT [key], [value], updated_at FROM dbo.settings WHERE [key] = @key;
    END
END
GO

-- 설정 저장
IF OBJECT_ID('dbo.usp_setting_upsert', 'P') IS NOT NULL DROP PROCEDURE dbo.usp_setting_upsert;
GO

CREATE PROCEDURE dbo.usp_setting_upsert
    @key NVARCHAR(100),
    @value NVARCHAR(MAX)
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        IF EXISTS (SELECT 1 FROM dbo.settings WHERE [key] = @key)
        BEGIN
            UPDATE dbo.settings 
            SET [value] = @value, updated_at = GETDATE()
            WHERE [key] = @key;
        END
        ELSE
        BEGIN
            INSERT INTO dbo.settings ([key], [value], updated_at)
            VALUES (@key, @value, GETDATE());
        END
        
        SELECT @key AS [key], 'SUCCESS' AS status, '설정이 저장되었습니다.' AS message;
        
    END TRY
    BEGIN CATCH
        SELECT @key AS [key], 'ERROR' AS status, ERROR_MESSAGE() AS message;
    END CATCH
END
GO

-- 설정 변경 이력 추가
IF OBJECT_ID('dbo.usp_config_revision_bump', 'P') IS NOT NULL DROP PROCEDURE dbo.usp_config_revision_bump;
GO

CREATE PROCEDURE dbo.usp_config_revision_bump
    @reason NVARCHAR(500),
    @changed_by BIGINT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @revision_id BIGINT;
    
    INSERT INTO dbo.config_revisions (reason, changed_by, changed_at)
    VALUES (@reason, @changed_by, GETDATE());
    
    SET @revision_id = SCOPE_IDENTITY();
    
    SELECT @revision_id AS revision_id, 'SUCCESS' AS status;
END
GO

-- 최신 설정 변경 확인 (콘솔용)
IF OBJECT_ID('dbo.usp_reset_trigger_get', 'P') IS NOT NULL DROP PROCEDURE dbo.usp_reset_trigger_get;
GO

CREATE PROCEDURE dbo.usp_reset_trigger_get
AS
BEGIN
    SET NOCOUNT ON;
    
    SELECT TOP 1 
        id AS revision_id,
        reason,
        changed_at
    FROM dbo.config_revisions 
    ORDER BY changed_at DESC;
END
GO

-- 설정 변경 확인 처리 (콘솔용)
IF OBJECT_ID('dbo.usp_reset_trigger_ack', 'P') IS NOT NULL DROP PROCEDURE dbo.usp_reset_trigger_ack;
GO

CREATE PROCEDURE dbo.usp_reset_trigger_ack
    @revision_id BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    
    -- 실제로는 별도 테이블에 콘솔별 확인 상태를 저장할 수 있지만
    -- 단순하게 처리하기 위해 현재는 단순 확인만 수행
    SELECT @revision_id AS revision_id, 'SUCCESS' AS status;
END
GO

PRINT '대시보드 및 조회 저장프로시저가 생성되었습니다.';
