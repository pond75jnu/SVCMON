from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password
from django.db import connection
from .models import User


class CustomAuthBackend(BaseBackend):
    """커스텀 인증 백엔드 - raw SQL 사용"""
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """사용자 인증"""
        if username is None or password is None:
            return None
            
        try:
            # raw SQL로 사용자 조회
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, username, email, phone, password_hash, role, 
                           is_active, is_staff, is_superuser, approved_by, 
                           approved_at, last_login, created_at, updated_at 
                    FROM users 
                    WHERE username = %s
                """, [username])
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                # 패스워드 검증
                if not check_password(password, row[4]):  # row[4] = password_hash
                    return None
                
                # User 객체 생성
                user = User(
                    id=row[0],
                    username=row[1],
                    email=row[2],
                    phone=row[3],
                    role=row[5],
                    is_active=bool(row[6]),
                    is_staff=bool(row[7]),
                    is_superuser=bool(row[8]),
                    approved_by=row[9],
                    approved_at=row[10],
                    last_login=row[11],
                    created_at=row[12],
                    updated_at=row[13]
                )
                
                # password 속성 설정 (Django가 요구함)
                user._password = row[4]
                
                return user
                
        except Exception as e:
            print(f"Authentication error: {e}")
            return None
    
    def get_user(self, user_id):
        """사용자 ID로 사용자 조회"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, username, email, phone, password_hash, role, 
                           is_active, is_staff, is_superuser, approved_by, 
                           approved_at, last_login, created_at, updated_at 
                    FROM users 
                    WHERE id = %s
                """, [user_id])
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                user = User(
                    id=row[0],
                    username=row[1],
                    email=row[2],
                    phone=row[3],
                    role=row[5],
                    is_active=bool(row[6]),
                    is_staff=bool(row[7]),
                    is_superuser=bool(row[8]),
                    approved_by=row[9],
                    approved_at=row[10],
                    last_login=row[11],
                    created_at=row[12],
                    updated_at=row[13]
                )
                
                user._password = row[4]
                return user
                
        except Exception as e:
            print(f"Get user error: {e}")
            return None
