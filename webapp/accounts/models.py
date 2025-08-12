from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """사용자 매니저"""
    
    def create_user(self, username, email, phone, password=None, **extra_fields):
        if not email:
            raise ValueError('이메일은 필수입니다.')
        if not phone:
            raise ValueError('핸드폰번호는 필수입니다.')
        
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, username, email, phone, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(username, email, phone, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """커스텀 사용자 모델"""
    
    ROLE_CHOICES = [
        ('admin', '관리자'),
        ('user', '일반사용자'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    password = models.CharField(max_length=128, db_column='password_hash')
    username = models.CharField('사용자명', max_length=150, unique=True)
    email = models.EmailField('이메일', unique=True)
    phone = models.CharField('핸드폰번호', max_length=20)
    role = models.CharField('역할', max_length=10, choices=ROLE_CHOICES, default='user')
    is_active = models.BooleanField('활성상태', default=False)
    is_staff = models.BooleanField('스태프 권한', default=False)
    approved_by = models.BigIntegerField('승인자', null=True, blank=True)
    approved_at = models.DateTimeField('승인일시', null=True, blank=True)
    last_login = models.DateTimeField('최종로그인', null=True, blank=True)
    created_at = models.DateTimeField('생성일시', auto_now_add=True)
    updated_at = models.DateTimeField('수정일시', auto_now=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'phone']
    
    class Meta:
        db_table = 'users'
        verbose_name = '사용자'
        verbose_name_plural = '사용자'
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def is_admin(self):
        return self.role == 'admin'
    
    def approve_user(self, approved_by_user):
        """사용자를 승인합니다."""
        self.is_active = True
        self.approved_by = approved_by_user.id if approved_by_user else None
        self.approved_at = timezone.now()
        self.save()
    
    def get_approved_by_user(self):
        """승인자 사용자 객체를 반환합니다."""
        if self.approved_by:
            try:
                return User.objects.get(id=self.approved_by)
            except User.DoesNotExist:
                return None
        return None
