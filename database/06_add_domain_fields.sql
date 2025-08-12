-- Domain 테이블에 새 필드 추가
-- 실행 전에 백업을 권장합니다

USE svcmon;
GO

-- 담당자 연락처 필드 추가
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('domains') AND name = 'owner_contact')
BEGIN
    ALTER TABLE domains 
    ADD owner_contact NVARCHAR(100) NULL;
    PRINT 'owner_contact 필드가 추가되었습니다.';
END
ELSE
BEGIN
    PRINT 'owner_contact 필드가 이미 존재합니다.';
END
GO

-- 활성 상태 필드 추가
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('domains') AND name = 'is_active')
BEGIN
    ALTER TABLE domains 
    ADD is_active BIT NOT NULL DEFAULT 1;
    PRINT 'is_active 필드가 추가되었습니다.';
END
ELSE
BEGIN
    PRINT 'is_active 필드가 이미 존재합니다.';
END
GO

-- 기존 데이터의 is_active를 1(활성)로 설정
UPDATE domains SET is_active = 1 WHERE is_active IS NULL;
GO

PRINT '도메인 테이블 스키마 업데이트가 완료되었습니다.';
