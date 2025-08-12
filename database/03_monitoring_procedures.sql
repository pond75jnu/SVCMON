-- SVCMON 모니터링 관리 저장프로시저
-- 전남대학교 웹사이트 모니터링 시스템

USE [SVCMON]
GO

-- 망구분 생성/수정
IF OBJECT_ID('dbo.usp_network_group_upsert', 'P') IS NOT NULL DROP PROCEDURE dbo.usp_network_group_upsert;
GO

CREATE PROCEDURE dbo.usp_network_group_upsert
    @id BIGINT = NULL,
    @name NVARCHAR(100),
    @note NVARCHAR(MAX) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @network_group_id BIGINT;
    
    BEGIN TRY
        -- 이름 중복 확인
        IF EXISTS (SELECT 1 FROM dbo.network_groups WHERE name = @name AND (@id IS NULL OR id != @id))
        BEGIN
            RAISERROR('이미 존재하는 망구분명입니다.', 16, 1);
            RETURN;
        END
        
        IF @id IS NULL
        BEGIN
            -- 생성
            INSERT INTO dbo.network_groups (name, note, created_at, updated_at)
            VALUES (@name, @note, GETDATE(), GETDATE());
            
            SET @network_group_id = SCOPE_IDENTITY();
        END
        ELSE
        BEGIN
            -- 수정
            UPDATE dbo.network_groups 
            SET name = @name,
                note = @note,
                updated_at = GETDATE()
            WHERE id = @id;
            
            SET @network_group_id = @id;
        END
        
        SELECT @network_group_id AS network_group_id, 'SUCCESS' AS status, '망구분이 저장되었습니다.' AS message;
        
    END TRY
    BEGIN CATCH
        SELECT 0 AS network_group_id, 'ERROR' AS status, ERROR_MESSAGE() AS message;
    END CATCH
END
GO

-- 망구분 삭제
IF OBJECT_ID('dbo.usp_network_group_delete', 'P') IS NOT NULL DROP PROCEDURE dbo.usp_network_group_delete;
GO

CREATE PROCEDURE dbo.usp_network_group_delete
    @id BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        -- 하위 도메인 존재 확인
        IF EXISTS (SELECT 1 FROM dbo.domains WHERE network_group_id = @id)
        BEGIN
            RAISERROR('하위에 도메인이 있는 망구분은 삭제할 수 없습니다.', 16, 1);
            RETURN;
        END
        
        DELETE FROM dbo.network_groups WHERE id = @id;
        
        SELECT @id AS network_group_id, 'SUCCESS' AS status, '망구분이 삭제되었습니다.' AS message;
        
    END TRY
    BEGIN CATCH
        SELECT @id AS network_group_id, 'ERROR' AS status, ERROR_MESSAGE() AS message;
    END CATCH
END
GO

-- 도메인 생성/수정
IF OBJECT_ID('dbo.usp_domain_upsert', 'P') IS NOT NULL DROP PROCEDURE dbo.usp_domain_upsert;
GO

CREATE PROCEDURE dbo.usp_domain_upsert
    @id BIGINT = NULL,
    @network_group_id BIGINT,
    @domain NVARCHAR(255),
    @site_name NVARCHAR(255),
    @owner_name NVARCHAR(100),
    @note NVARCHAR(MAX) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @domain_id BIGINT;
    
    BEGIN TRY
        -- 망구분 존재 확인
        IF NOT EXISTS (SELECT 1 FROM dbo.network_groups WHERE id = @network_group_id)
        BEGIN
            RAISERROR('존재하지 않는 망구분입니다.', 16, 1);
            RETURN;
        END
        
        -- 도메인 중복 확인
        IF EXISTS (SELECT 1 FROM dbo.domains WHERE network_group_id = @network_group_id AND domain = @domain AND (@id IS NULL OR id != @id))
        BEGIN
            RAISERROR('해당 망구분에 이미 존재하는 도메인입니다.', 16, 1);
            RETURN;
        END
        
        IF @id IS NULL
        BEGIN
            -- 생성
            INSERT INTO dbo.domains (network_group_id, domain, site_name, owner_name, note, created_at, updated_at)
            VALUES (@network_group_id, @domain, @site_name, @owner_name, @note, GETDATE(), GETDATE());
            
            SET @domain_id = SCOPE_IDENTITY();
        END
        ELSE
        BEGIN
            -- 수정
            UPDATE dbo.domains 
            SET network_group_id = @network_group_id,
                domain = @domain,
                site_name = @site_name,
                owner_name = @owner_name,
                note = @note,
                updated_at = GETDATE()
            WHERE id = @id;
            
            SET @domain_id = @id;
        END
        
        SELECT @domain_id AS domain_id, 'SUCCESS' AS status, '도메인이 저장되었습니다.' AS message;
        
    END TRY
    BEGIN CATCH
        SELECT 0 AS domain_id, 'ERROR' AS status, ERROR_MESSAGE() AS message;
    END CATCH
END
GO

-- 도메인 삭제
IF OBJECT_ID('dbo.usp_domain_delete', 'P') IS NOT NULL DROP PROCEDURE dbo.usp_domain_delete;
GO

CREATE PROCEDURE dbo.usp_domain_delete
    @id BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        -- 하위 엔드포인트 존재 확인
        IF EXISTS (SELECT 1 FROM dbo.endpoints WHERE domain_id = @id)
        BEGIN
            RAISERROR('하위에 엔드포인트가 있는 도메인은 삭제할 수 없습니다.', 16, 1);
            RETURN;
        END
        
        DELETE FROM dbo.domains WHERE id = @id;
        
        SELECT @id AS domain_id, 'SUCCESS' AS status, '도메인이 삭제되었습니다.' AS message;
        
    END TRY
    BEGIN CATCH
        SELECT @id AS domain_id, 'ERROR' AS status, ERROR_MESSAGE() AS message;
    END CATCH
END
GO

-- 엔드포인트 생성/수정
IF OBJECT_ID('dbo.usp_endpoint_upsert', 'P') IS NOT NULL DROP PROCEDURE dbo.usp_endpoint_upsert;
GO

CREATE PROCEDURE dbo.usp_endpoint_upsert
    @id BIGINT = NULL,
    @domain_id BIGINT,
    @url NVARCHAR(2000),
    @requires_db BIT = 0,
    @note NVARCHAR(MAX) = NULL,
    @poll_interval_sec INT = 300,
    @email_on_failure BIT = 1,
    @is_enabled BIT = 1
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @endpoint_id BIGINT;
    
    BEGIN TRY
        -- 도메인 존재 확인
        IF NOT EXISTS (SELECT 1 FROM dbo.domains WHERE id = @domain_id)
        BEGIN
            RAISERROR('존재하지 않는 도메인입니다.', 16, 1);
            RETURN;
        END
        
        IF @id IS NULL
        BEGIN
            -- 생성
            INSERT INTO dbo.endpoints (domain_id, url, requires_db, note, poll_interval_sec, email_on_failure, is_enabled, created_at, updated_at)
            VALUES (@domain_id, @url, @requires_db, @note, @poll_interval_sec, @email_on_failure, @is_enabled, GETDATE(), GETDATE());
            
            SET @endpoint_id = SCOPE_IDENTITY();
        END
        ELSE
        BEGIN
            -- 수정
            UPDATE dbo.endpoints 
            SET domain_id = @domain_id,
                url = @url,
                requires_db = @requires_db,
                note = @note,
                poll_interval_sec = @poll_interval_sec,
                email_on_failure = @email_on_failure,
                is_enabled = @is_enabled,
                updated_at = GETDATE()
            WHERE id = @id;
            
            SET @endpoint_id = @id;
        END
        
        SELECT @endpoint_id AS endpoint_id, 'SUCCESS' AS status, '엔드포인트가 저장되었습니다.' AS message;
        
    END TRY
    BEGIN CATCH
        SELECT 0 AS endpoint_id, 'ERROR' AS status, ERROR_MESSAGE() AS message;
    END CATCH
END
GO

-- 엔드포인트 삭제
IF OBJECT_ID('dbo.usp_endpoint_delete', 'P') IS NOT NULL DROP PROCEDURE dbo.usp_endpoint_delete;
GO

CREATE PROCEDURE dbo.usp_endpoint_delete
    @id BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        DELETE FROM dbo.endpoints WHERE id = @id;
        
        SELECT @id AS endpoint_id, 'SUCCESS' AS status, '엔드포인트가 삭제되었습니다.' AS message;
        
    END TRY
    BEGIN CATCH
        SELECT @id AS endpoint_id, 'ERROR' AS status, ERROR_MESSAGE() AS message;
    END CATCH
END
GO

-- 망구분 복사 (다른 망구분의 도메인/엔드포인트 복사)
IF OBJECT_ID('dbo.usp_endpoint_clone_from_group', 'P') IS NOT NULL DROP PROCEDURE dbo.usp_endpoint_clone_from_group;
GO

CREATE PROCEDURE dbo.usp_endpoint_clone_from_group
    @source_network_group_id BIGINT,
    @target_network_group_id BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @cloned_count INT = 0;
    
    BEGIN TRY
        BEGIN TRANSACTION;
        
        -- 망구분 존재 확인
        IF NOT EXISTS (SELECT 1 FROM dbo.network_groups WHERE id = @source_network_group_id)
        BEGIN
            RAISERROR('소스 망구분이 존재하지 않습니다.', 16, 1);
            RETURN;
        END
        
        IF NOT EXISTS (SELECT 1 FROM dbo.network_groups WHERE id = @target_network_group_id)
        BEGIN
            RAISERROR('대상 망구분이 존재하지 않습니다.', 16, 1);
            RETURN;
        END
        
        -- 도메인과 엔드포인트 복사
        DECLARE @domain_id BIGINT, @new_domain_id BIGINT;
        DECLARE @domain NVARCHAR(255), @site_name NVARCHAR(255), @owner_name NVARCHAR(100), @note NVARCHAR(MAX);
        
        DECLARE domain_cursor CURSOR FOR
        SELECT id, domain, site_name, owner_name, note
        FROM dbo.domains 
        WHERE network_group_id = @source_network_group_id;
        
        OPEN domain_cursor;
        FETCH NEXT FROM domain_cursor INTO @domain_id, @domain, @site_name, @owner_name, @note;
        
        WHILE @@FETCH_STATUS = 0
        BEGIN
            -- 도메인 복사
            INSERT INTO dbo.domains (network_group_id, domain, site_name, owner_name, note, created_at, updated_at)
            VALUES (@target_network_group_id, @domain, @site_name, @owner_name, @note, GETDATE(), GETDATE());
            
            SET @new_domain_id = SCOPE_IDENTITY();
            
            -- 해당 도메인의 엔드포인트들 복사
            INSERT INTO dbo.endpoints (domain_id, url, requires_db, note, poll_interval_sec, email_on_failure, is_enabled, created_at, updated_at)
            SELECT @new_domain_id, url, requires_db, note, poll_interval_sec, email_on_failure, is_enabled, GETDATE(), GETDATE()
            FROM dbo.endpoints 
            WHERE domain_id = @domain_id;
            
            SET @cloned_count = @cloned_count + @@ROWCOUNT;
            
            FETCH NEXT FROM domain_cursor INTO @domain_id, @domain, @site_name, @owner_name, @note;
        END
        
        CLOSE domain_cursor;
        DEALLOCATE domain_cursor;
        
        COMMIT TRANSACTION;
        
        SELECT @cloned_count AS cloned_count, 'SUCCESS' AS status, 
               CONCAT('망구분 복사가 완료되었습니다. (', @cloned_count, '개 엔드포인트)') AS message;
        
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        
        IF CURSOR_STATUS('global', 'domain_cursor') >= -1
        BEGIN
            CLOSE domain_cursor;
            DEALLOCATE domain_cursor;
        END
        
        SELECT 0 AS cloned_count, 'ERROR' AS status, ERROR_MESSAGE() AS message;
    END CATCH
END
GO

PRINT '모니터링 관리 저장프로시저가 생성되었습니다.';
