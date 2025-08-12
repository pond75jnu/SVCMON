-- SVCMON 사용자 관리 저장프로시저
-- 전남대학교 웹사이트 모니터링 시스템

USE [SVCMON]
GO

-- 사용자 생성
IF OBJECT_ID('dbo.usp_user_create', 'P') IS NOT NULL DROP PROCEDURE dbo.usp_user_create;
GO

CREATE PROCEDURE dbo.usp_user_create
    @username NVARCHAR(150),
    @email NVARCHAR(254),
    @phone NVARCHAR(20),
    @password_hash NVARCHAR(128),
    @role NVARCHAR(10) = 'user'
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @user_id BIGINT;
    
    BEGIN TRY
        -- 중복 확인
        IF EXISTS (SELECT 1 FROM dbo.users WHERE username = @username)
        BEGIN
            RAISERROR('이미 존재하는 사용자명입니다.', 16, 1);
            RETURN;
        END
        
        IF EXISTS (SELECT 1 FROM dbo.users WHERE email = @email)
        BEGIN
            RAISERROR('이미 존재하는 이메일입니다.', 16, 1);
            RETURN;
        END
        
        -- 사용자 생성
        INSERT INTO dbo.users (username, email, phone, password_hash, role, is_active, created_at, updated_at)
        VALUES (@username, @email, @phone, @password_hash, @role, 
                CASE WHEN @role = 'admin' THEN 1 ELSE 0 END, GETDATE(), GETDATE());
        
        SET @user_id = SCOPE_IDENTITY();
        
        SELECT @user_id AS user_id, 'SUCCESS' AS status, '사용자가 생성되었습니다.' AS message;
        
    END TRY
    BEGIN CATCH
        SELECT 0 AS user_id, 'ERROR' AS status, ERROR_MESSAGE() AS message;
    END CATCH
END
GO

-- 사용자 업데이트
IF OBJECT_ID('dbo.usp_user_update', 'P') IS NOT NULL DROP PROCEDURE dbo.usp_user_update;
GO

CREATE PROCEDURE dbo.usp_user_update
    @user_id BIGINT,
    @email NVARCHAR(254) = NULL,
    @phone NVARCHAR(20) = NULL,
    @role NVARCHAR(10) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        -- 사용자 존재 확인
        IF NOT EXISTS (SELECT 1 FROM dbo.users WHERE id = @user_id)
        BEGIN
            RAISERROR('존재하지 않는 사용자입니다.', 16, 1);
            RETURN;
        END
        
        -- 이메일 중복 확인
        IF @email IS NOT NULL AND EXISTS (SELECT 1 FROM dbo.users WHERE email = @email AND id != @user_id)
        BEGIN
            RAISERROR('이미 존재하는 이메일입니다.', 16, 1);
            RETURN;
        END
        
        -- 업데이트
        UPDATE dbo.users 
        SET email = ISNULL(@email, email),
            phone = ISNULL(@phone, phone),
            role = ISNULL(@role, role),
            updated_at = GETDATE()
        WHERE id = @user_id;
        
        SELECT @user_id AS user_id, 'SUCCESS' AS status, '사용자 정보가 업데이트되었습니다.' AS message;
        
    END TRY
    BEGIN CATCH
        SELECT @user_id AS user_id, 'ERROR' AS status, ERROR_MESSAGE() AS message;
    END CATCH
END
GO

-- 사용자 승인
IF OBJECT_ID('dbo.usp_user_approve', 'P') IS NOT NULL DROP PROCEDURE dbo.usp_user_approve;
GO

CREATE PROCEDURE dbo.usp_user_approve
    @user_id BIGINT,
    @approved_by BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        -- 사용자 존재 확인
        IF NOT EXISTS (SELECT 1 FROM dbo.users WHERE id = @user_id)
        BEGIN
            RAISERROR('존재하지 않는 사용자입니다.', 16, 1);
            RETURN;
        END
        
        -- 승인자 확인
        IF NOT EXISTS (SELECT 1 FROM dbo.users WHERE id = @approved_by AND role = 'admin')
        BEGIN
            RAISERROR('승인 권한이 없습니다.', 16, 1);
            RETURN;
        END
        
        -- 사용자 승인
        UPDATE dbo.users 
        SET is_active = 1,
            approved_by = @approved_by,
            approved_at = GETDATE(),
            updated_at = GETDATE()
        WHERE id = @user_id;
        
        SELECT @user_id AS user_id, 'SUCCESS' AS status, '사용자가 승인되었습니다.' AS message;
        
    END TRY
    BEGIN CATCH
        SELECT @user_id AS user_id, 'ERROR' AS status, ERROR_MESSAGE() AS message;
    END CATCH
END
GO

-- 사용자 삭제
IF OBJECT_ID('dbo.usp_user_delete', 'P') IS NOT NULL DROP PROCEDURE dbo.usp_user_delete;
GO

CREATE PROCEDURE dbo.usp_user_delete
    @user_id BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        -- 사용자 존재 확인
        IF NOT EXISTS (SELECT 1 FROM dbo.users WHERE id = @user_id)
        BEGIN
            RAISERROR('존재하지 않는 사용자입니다.', 16, 1);
            RETURN;
        END
        
        -- 관리자는 삭제 불가
        IF EXISTS (SELECT 1 FROM dbo.users WHERE id = @user_id AND role = 'admin')
        BEGIN
            RAISERROR('관리자는 삭제할 수 없습니다.', 16, 1);
            RETURN;
        END
        
        -- 사용자 삭제
        DELETE FROM dbo.users WHERE id = @user_id;
        
        SELECT @user_id AS user_id, 'SUCCESS' AS status, '사용자가 삭제되었습니다.' AS message;
        
    END TRY
    BEGIN CATCH
        SELECT @user_id AS user_id, 'ERROR' AS status, ERROR_MESSAGE() AS message;
    END CATCH
END
GO

-- 사용자 목록 조회
IF OBJECT_ID('dbo.usp_user_list', 'P') IS NOT NULL DROP PROCEDURE dbo.usp_user_list;
GO

CREATE PROCEDURE dbo.usp_user_list
    @role NVARCHAR(10) = NULL,
    @is_active BIT = NULL,
    @page INT = 1,
    @page_size INT = 20
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @offset INT = (@page - 1) * @page_size;
    
    SELECT 
        u.id,
        u.username,
        u.email,
        u.phone,
        u.role,
        u.is_active,
        u.approved_at,
        approver.username AS approved_by_username,
        u.created_at,
        u.updated_at,
        COUNT(*) OVER() AS total_count
    FROM dbo.users u
    LEFT JOIN dbo.users approver ON u.approved_by = approver.id
    WHERE (@role IS NULL OR u.role = @role)
      AND (@is_active IS NULL OR u.is_active = @is_active)
    ORDER BY u.created_at DESC
    OFFSET @offset ROWS FETCH NEXT @page_size ROWS ONLY;
END
GO

-- 사용자 인증
IF OBJECT_ID('dbo.usp_user_authenticate', 'P') IS NOT NULL DROP PROCEDURE dbo.usp_user_authenticate;
GO

CREATE PROCEDURE dbo.usp_user_authenticate
    @username NVARCHAR(150)
AS
BEGIN
    SET NOCOUNT ON;
    
    SELECT 
        id,
        username,
        email,
        phone,
        password_hash,
        role,
        is_active,
        last_login,
        created_at
    FROM dbo.users 
    WHERE username = @username;
END
GO

-- 로그인 시간 업데이트
IF OBJECT_ID('dbo.usp_user_update_login', 'P') IS NOT NULL DROP PROCEDURE dbo.usp_user_update_login;
GO

CREATE PROCEDURE dbo.usp_user_update_login
    @user_id BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    
    UPDATE dbo.users 
    SET last_login = GETDATE(),
        updated_at = GETDATE()
    WHERE id = @user_id;
END
GO

PRINT '사용자 관리 저장프로시저가 생성되었습니다.';
