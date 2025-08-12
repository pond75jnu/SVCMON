-- SVCMON 콘솔 프로그램용 저장프로시저
-- 전남대학교 웹사이트 모니터링 시스템

USE [SVCMON]
GO

-- 다음 폴링 배치 조회 (콘솔용)
IF OBJECT_ID('dbo.usp_next_poll_batch', 'P') IS NOT NULL DROP PROCEDURE dbo.usp_next_poll_batch;
GO

CREATE PROCEDURE dbo.usp_next_poll_batch
    @now DATETIME2,
    @limit INT = 50,
    @max_concurrency INT = 50,
    @network_group_id BIGINT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    -- 현재 시간 기준으로 폴링이 필요한 엔드포인트들을 조회
    -- 마지막 체크 시간 + 폴링 간격 <= 현재 시간인 것들
    -- 망구분 필터링 지원
    SELECT TOP (@limit)
        e.id AS endpoint_id,
        e.url,
        e.poll_interval_sec,
        d.domain,
        d.site_name,
        ng.name AS network_group_name,
        ISNULL(latest_check.checked_at, DATEADD(year, -1, GETDATE())) AS last_checked_at,
        DATEADD(second, e.poll_interval_sec, ISNULL(latest_check.checked_at, DATEADD(year, -1, GETDATE()))) AS next_check_due
    FROM dbo.endpoints e
    INNER JOIN dbo.domains d ON e.domain_id = d.id
    INNER JOIN dbo.network_groups ng ON d.network_group_id = ng.id
    OUTER APPLY (
        SELECT TOP 1 checked_at
        FROM dbo.checks c
        WHERE c.endpoint_id = e.id
        ORDER BY c.checked_at DESC
    ) latest_check
    WHERE e.is_enabled = 1
      AND (@network_group_id IS NULL OR ng.id = @network_group_id)
      AND DATEADD(second, e.poll_interval_sec, ISNULL(latest_check.checked_at, DATEADD(year, -1, GETDATE()))) <= @now
    ORDER BY 
        -- 우선순위: 오래된 것부터, 그 다음 ID 순
        ISNULL(latest_check.checked_at, DATEADD(year, -1, GETDATE())),
        ng.id,
        d.id,
        e.id;
END
GO

-- 체크 결과 기록
IF OBJECT_ID('dbo.usp_record_check', 'P') IS NOT NULL DROP PROCEDURE dbo.usp_record_check;
GO

CREATE PROCEDURE dbo.usp_record_check
    @endpoint_id BIGINT,
    @status_code INT = NULL,
    @latency_ms INT = NULL,
    @headers NVARCHAR(MAX) = NULL,
    @error NVARCHAR(4000) = NULL,
    @checked_at DATETIME2 = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @check_id BIGINT;
    DECLARE @current_status NVARCHAR(6);
    
    IF @checked_at IS NULL SET @checked_at = GETDATE();
    
    BEGIN TRY
        BEGIN TRANSACTION;
        
        -- 체크 결과 기록
        INSERT INTO dbo.checks (endpoint_id, status_code, latency_ms, headers, error, checked_at)
        VALUES (@endpoint_id, @status_code, @latency_ms, @headers, @error, @checked_at);
        
        SET @check_id = SCOPE_IDENTITY();
        
        -- 상태 판정
        SET @current_status = CASE 
            WHEN @status_code = 200 THEN 'GREEN'
            WHEN @status_code IS NULL THEN 'AMBER'
            ELSE 'RED'
        END;
        
        -- 롤업 테이블 업데이트 (엔드포인트 레벨)
        EXEC dbo.usp_rollup_update 'endpoint', @endpoint_id;
        
        -- 상위 레벨 롤업도 업데이트
        DECLARE @domain_id BIGINT, @network_group_id BIGINT;
        
        SELECT @domain_id = d.id, @network_group_id = d.network_group_id
        FROM dbo.endpoints e
        INNER JOIN dbo.domains d ON e.domain_id = d.id
        WHERE e.id = @endpoint_id;
        
        EXEC dbo.usp_rollup_update 'domain', @domain_id;
        EXEC dbo.usp_rollup_update 'network', @network_group_id;
        
        COMMIT TRANSACTION;
        
        SELECT @check_id AS check_id, @current_status AS status, 'SUCCESS' AS result;
        
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        SELECT 0 AS check_id, 'ERROR' AS status, ERROR_MESSAGE() AS result;
    END CATCH
END
GO

-- 롤업 상태 업데이트
IF OBJECT_ID('dbo.usp_rollup_update', 'P') IS NOT NULL DROP PROCEDURE dbo.usp_rollup_update;
GO

CREATE PROCEDURE dbo.usp_rollup_update
    @level NVARCHAR(10),
    @ref_id BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @status NVARCHAR(6);
    DECLARE @reason NVARCHAR(400);
    DECLARE @red_count INT = 0;
    DECLARE @amber_count INT = 0;
    DECLARE @green_count INT = 0;
    
    BEGIN TRY
        IF @level = 'endpoint'
        BEGIN
            -- 엔드포인트 레벨: 최신 체크 결과 기준
            SELECT TOP 1 
                @status = CASE 
                    WHEN status_code = 200 THEN 'GREEN'
                    WHEN status_code IS NULL THEN 'AMBER'
                    ELSE 'RED'
                END,
                @reason = CASE 
                    WHEN status_code = 200 THEN '정상 응답'
                    WHEN status_code IS NULL THEN '응답 없음'
                    ELSE CONCAT('HTTP ', status_code, CASE WHEN error IS NOT NULL THEN ': ' + LEFT(error, 100) ELSE '' END)
                END
            FROM dbo.checks 
            WHERE endpoint_id = @ref_id 
            ORDER BY checked_at DESC;
            
            IF @status IS NULL
            BEGIN
                SET @status = 'AMBER';
                SET @reason = '체크 이력 없음';
            END
        END
        ELSE IF @level = 'domain'
        BEGIN
            -- 도메인 레벨: 하위 엔드포인트들의 상태 집계
            SELECT 
                @red_count = COUNT(CASE WHEN r.last_status = 'RED' THEN 1 END),
                @amber_count = COUNT(CASE WHEN r.last_status = 'AMBER' OR r.last_status IS NULL THEN 1 END),
                @green_count = COUNT(CASE WHEN r.last_status = 'GREEN' THEN 1 END)
            FROM dbo.endpoints e
            LEFT JOIN dbo.rollups r ON r.level = 'endpoint' AND r.ref_id = e.id
            WHERE e.domain_id = @ref_id AND e.is_enabled = 1;
            
            IF @red_count > 0
            BEGIN
                SET @status = 'RED';
                SET @reason = CONCAT('장애 ', @red_count, '개');
            END
            ELSE IF @amber_count > 0
            BEGIN
                SET @status = 'AMBER';
                SET @reason = CONCAT('신호없음 ', @amber_count, '개');
            END
            ELSE IF @green_count > 0
            BEGIN
                SET @status = 'GREEN';
                SET @reason = CONCAT('정상 ', @green_count, '개');
            END
            ELSE
            BEGIN
                SET @status = 'AMBER';
                SET @reason = '활성화된 엔드포인트 없음';
            END
        END
        ELSE IF @level = 'network'
        BEGIN
            -- 망구분 레벨: 하위 도메인들의 상태 집계
            SELECT 
                @red_count = COUNT(CASE WHEN r.last_status = 'RED' THEN 1 END),
                @amber_count = COUNT(CASE WHEN r.last_status = 'AMBER' OR r.last_status IS NULL THEN 1 END),
                @green_count = COUNT(CASE WHEN r.last_status = 'GREEN' THEN 1 END)
            FROM dbo.domains d
            LEFT JOIN dbo.rollups r ON r.level = 'domain' AND r.ref_id = d.id
            WHERE d.network_group_id = @ref_id;
            
            IF @red_count > 0
            BEGIN
                SET @status = 'RED';
                SET @reason = CONCAT('장애 도메인 ', @red_count, '개');
            END
            ELSE IF @amber_count > 0
            BEGIN
                SET @status = 'AMBER';
                SET @reason = CONCAT('신호없음 도메인 ', @amber_count, '개');
            END
            ELSE IF @green_count > 0
            BEGIN
                SET @status = 'GREEN';
                SET @reason = CONCAT('정상 도메인 ', @green_count, '개');
            END
            ELSE
            BEGIN
                SET @status = 'AMBER';
                SET @reason = '등록된 도메인 없음';
            END
        END
        
        -- 롤업 테이블 업데이트
        IF EXISTS (SELECT 1 FROM dbo.rollups WHERE level = @level AND ref_id = @ref_id)
        BEGIN
            UPDATE dbo.rollups 
            SET last_status = @status,
                last_change_at = CASE WHEN last_status != @status THEN GETDATE() ELSE last_change_at END,
                last_reason = @reason,
                updated_at = GETDATE()
            WHERE level = @level AND ref_id = @ref_id;
        END
        ELSE
        BEGIN
            INSERT INTO dbo.rollups (level, ref_id, last_status, last_change_at, last_reason, updated_at)
            VALUES (@level, @ref_id, @status, GETDATE(), @reason, GETDATE());
        END
        
    END TRY
    BEGIN CATCH
        -- 오류가 발생해도 진행 (롤업은 중요하지 않은 부가 기능)
        PRINT 'Rollup update error: ' + ERROR_MESSAGE();
    END CATCH
END
GO

-- 오래된 체크 데이터 정리
IF OBJECT_ID('dbo.usp_cleanup_old_checks', 'P') IS NOT NULL DROP PROCEDURE dbo.usp_cleanup_old_checks;
GO

CREATE PROCEDURE dbo.usp_cleanup_old_checks
    @retention_days INT = 180
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @cutoff_date DATETIME2 = DATEADD(day, -@retention_days, GETDATE());
    DECLARE @deleted_count INT;
    
    BEGIN TRY
        DELETE FROM dbo.checks 
        WHERE checked_at < @cutoff_date;
        
        SET @deleted_count = @@ROWCOUNT;
        
        SELECT @deleted_count AS deleted_count, 'SUCCESS' AS status, 
               CONCAT('오래된 체크 데이터 ', @deleted_count, '건이 삭제되었습니다.') AS message;
        
    END TRY
    BEGIN CATCH
        SELECT 0 AS deleted_count, 'ERROR' AS status, ERROR_MESSAGE() AS message;
    END CATCH
END
GO

-- 알림 기록
IF OBJECT_ID('dbo.usp_record_notification', 'P') IS NOT NULL DROP PROCEDURE dbo.usp_record_notification;
GO

CREATE PROCEDURE dbo.usp_record_notification
    @endpoint_id BIGINT,
    @level NVARCHAR(10),
    @title NVARCHAR(200),
    @body NVARCHAR(MAX),
    @sent_to NVARCHAR(254),
    @dedupe_key NVARCHAR(100) = NULL,
    @status NVARCHAR(10) = 'SENT'
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @notification_id BIGINT;
    DECLARE @dedupe_minutes INT = 30;
    
    BEGIN TRY
        -- 설정에서 중복 제거 시간 조회
        SELECT @dedupe_minutes = CAST([value] AS INT)
        FROM dbo.settings 
        WHERE [key] = 'notification_dedupe_minutes';
        
        -- 중복 제거 확인
        IF @dedupe_key IS NOT NULL
        BEGIN
            IF EXISTS (
                SELECT 1 FROM dbo.notifications 
                WHERE dedupe_key = @dedupe_key 
                  AND sent_at >= DATEADD(minute, -@dedupe_minutes, GETDATE())
            )
            BEGIN
                SELECT 0 AS notification_id, 'SKIPPED' AS status, '중복 알림으로 건너뜀' AS message;
                RETURN;
            END
        END
        
        -- 알림 기록
        INSERT INTO dbo.notifications (endpoint_id, level, title, body, sent_to, dedupe_key, status, sent_at)
        VALUES (@endpoint_id, @level, @title, @body, @sent_to, @dedupe_key, @status, GETDATE());
        
        SET @notification_id = SCOPE_IDENTITY();
        
        SELECT @notification_id AS notification_id, @status AS status, '알림이 기록되었습니다.' AS message;
        
    END TRY
    BEGIN CATCH
        SELECT 0 AS notification_id, 'FAILED' AS status, ERROR_MESSAGE() AS message;
    END CATCH
END
GO

-- 일괄 설정 업데이트
IF OBJECT_ID('dbo.usp_bulk_update_settings', 'P') IS NOT NULL DROP PROCEDURE dbo.usp_bulk_update_settings;
GO

CREATE PROCEDURE dbo.usp_bulk_update_settings
    @level NVARCHAR(10), -- 'network', 'domain'
    @ref_id BIGINT,
    @poll_interval_sec INT,
    @email_on_failure BIT
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @updated_count INT = 0;
    
    BEGIN TRY
        IF @level = 'network'
        BEGIN
            UPDATE e
            SET poll_interval_sec = @poll_interval_sec,
                email_on_failure = @email_on_failure,
                updated_at = GETDATE()
            FROM dbo.endpoints e
            INNER JOIN dbo.domains d ON e.domain_id = d.id
            WHERE d.network_group_id = @ref_id;
            
            SET @updated_count = @@ROWCOUNT;
        END
        ELSE IF @level = 'domain'
        BEGIN
            UPDATE dbo.endpoints 
            SET poll_interval_sec = @poll_interval_sec,
                email_on_failure = @email_on_failure,
                updated_at = GETDATE()
            WHERE domain_id = @ref_id;
            
            SET @updated_count = @@ROWCOUNT;
        END
        
        SELECT @updated_count AS updated_count, 'SUCCESS' AS status, 
               CONCAT(@updated_count, '개 엔드포인트 설정이 업데이트되었습니다.') AS message;
        
    END TRY
    BEGIN CATCH
        SELECT 0 AS updated_count, 'ERROR' AS status, ERROR_MESSAGE() AS message;
    END CATCH
END
GO

PRINT '콘솔 프로그램용 저장프로시저가 생성되었습니다.';
