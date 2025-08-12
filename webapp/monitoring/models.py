from django.db import models
from django.utils import timezone
import uuid


class NetworkGroup(models.Model):
    """망구분 모델 (교내망, KT망, LG망, 해외망 등)"""
    
    name = models.CharField('망구분명', max_length=100, unique=True)
    note = models.TextField('비고', blank=True)
    created_at = models.DateTimeField('생성일시', auto_now_add=True)
    updated_at = models.DateTimeField('수정일시', auto_now=True)
    
    class Meta:
        db_table = 'network_groups'
        verbose_name = '망구분'
        verbose_name_plural = '망구분'
    
    def __str__(self):
        return self.name


class Domain(models.Model):
    """도메인 모델"""
    
    network_group = models.ForeignKey(
        NetworkGroup,  # NetworkGroup이 먼저 정의됨
        on_delete=models.CASCADE, 
        verbose_name='망구분',
        related_name='domains'
    )
    domain = models.CharField('도메인명', max_length=255)
    site_name = models.CharField('사이트명', max_length=255)
    owner_name = models.CharField('담당자명', max_length=100)
    owner_contact = models.CharField('담당자 연락처', max_length=100, blank=True, default='')
    is_active = models.BooleanField('활성 상태', default=True)
    note = models.TextField('비고', blank=True)
    created_at = models.DateTimeField('생성일시', auto_now_add=True)
    updated_at = models.DateTimeField('수정일시', auto_now=True)
    
    class Meta:
        db_table = 'domains'
        verbose_name = '도메인'
        verbose_name_plural = '도메인'
        unique_together = ['network_group', 'domain']
    
    def __str__(self):
        return f"{self.domain} ({self.site_name})"


class Endpoint(models.Model):
    """엔드포인트(URL) 모델"""
    
    domain = models.ForeignKey(
        Domain, 
        on_delete=models.CASCADE, 
        verbose_name='도메인',
        related_name='endpoints'
    )
    url = models.URLField('URL', max_length=2000)
    requires_db = models.BooleanField('DB연결 필요여부', default=False)
    note = models.TextField('비고', blank=True)
    poll_interval_sec = models.IntegerField('호출주기(초)', default=300)  # 기본 5분
    email_on_failure = models.BooleanField('장애시 이메일 발송', default=True)
    is_enabled = models.BooleanField('활성화', default=True)
    created_at = models.DateTimeField('생성일시', auto_now_add=True)
    updated_at = models.DateTimeField('수정일시', auto_now=True)
    
    class Meta:
        db_table = 'endpoints'
        verbose_name = '엔드포인트'
        verbose_name_plural = '엔드포인트'
    
    def __str__(self):
        return f"{self.url} ({self.domain.site_name})"


class Check(models.Model):
    """헬스체크 결과 모델"""
    
    endpoint = models.ForeignKey(
        Endpoint, 
        on_delete=models.CASCADE, 
        verbose_name='엔드포인트',
        related_name='checks'
    )
    status_code = models.IntegerField('HTTP 상태코드', null=True)
    latency_ms = models.IntegerField('응답시간(ms)', null=True)
    headers = models.TextField('응답헤더', null=True, blank=True)
    error = models.TextField('오류메시지', null=True, blank=True)
    checked_at = models.DateTimeField('체크일시', default=timezone.now)
    trace_id = models.UUIDField('추적ID', default=uuid.uuid4, editable=False)
    
    class Meta:
        db_table = 'checks'
        verbose_name = '헬스체크'
        verbose_name_plural = '헬스체크'
        ordering = ['-checked_at']
        indexes = [
            models.Index(fields=['endpoint', '-checked_at']),
        ]
    
    def __str__(self):
        return f"{self.endpoint.url} - {self.status_code} ({self.checked_at})"
    
    @property
    def is_success(self):
        """성공 여부 (200번대만 성공으로 간주)"""
        return self.status_code == 200
    
    @property
    def is_failure(self):
        """장애 여부 (200이 아닌 모든 경우)"""
        return self.status_code != 200 if self.status_code else True


class Rollup(models.Model):
    """상태 롤업 모델 (망구분, 도메인, 엔드포인트별 최종 상태)"""
    
    STATUS_CHOICES = [
        ('GREEN', '정상'),
        ('AMBER', '신호없음'),
        ('RED', '장애'),
    ]
    
    LEVEL_CHOICES = [
        ('network', '망구분'),
        ('domain', '도메인'),
        ('endpoint', '엔드포인트'),
    ]
    
    level = models.CharField('레벨', max_length=10, choices=LEVEL_CHOICES)
    ref_id = models.IntegerField('참조ID')  # NetworkGroup, Domain, Endpoint의 ID
    last_status = models.CharField('최종상태', max_length=6, choices=STATUS_CHOICES, default='AMBER')
    last_change_at = models.DateTimeField('최종변경일시', default=timezone.now)
    last_reason = models.CharField('최종사유', max_length=400, blank=True)
    updated_at = models.DateTimeField('갱신일시', auto_now=True)
    
    class Meta:
        db_table = 'rollups'
        verbose_name = '상태롤업'
        verbose_name_plural = '상태롤업'
        unique_together = ['level', 'ref_id']
    
    def __str__(self):
        return f"{self.get_level_display()} {self.ref_id} - {self.get_last_status_display()}"


class Setting(models.Model):
    """설정 모델"""
    
    key = models.CharField('키', max_length=100, unique=True)
    value = models.TextField('값')
    updated_at = models.DateTimeField('수정일시', auto_now=True)
    
    class Meta:
        db_table = 'settings'
        verbose_name = '설정'
        verbose_name_plural = '설정'
    
    def __str__(self):
        return f"{self.key}: {self.value}"


class ConfigRevision(models.Model):
    """설정 변경 이력 모델 (콘솔 프로그램 리셋 트리거용)"""
    
    reason = models.CharField('변경사유', max_length=500)
    changed_by = models.ForeignKey(
        'accounts.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name='변경자'
    )
    changed_at = models.DateTimeField('변경일시', auto_now_add=True)
    
    class Meta:
        db_table = 'config_revisions'
        verbose_name = '설정변경이력'
        verbose_name_plural = '설정변경이력'
        ordering = ['-changed_at']
    
    def __str__(self):
        return f"{self.id}: {self.reason} ({self.changed_at})"


class Notification(models.Model):
    """알림 모델"""
    
    STATUS_CHOICES = [
        ('SENT', '발송완료'),
        ('SKIPPED', '건너뜀'),
        ('FAILED', '발송실패'),
    ]
    
    endpoint = models.ForeignKey(
        Endpoint, 
        on_delete=models.CASCADE, 
        verbose_name='엔드포인트',
        related_name='notifications'
    )
    level = models.CharField('알림레벨', max_length=10)
    title = models.CharField('제목', max_length=200)
    body = models.TextField('내용')
    sent_to = models.EmailField('수신자')
    sent_at = models.DateTimeField('발송일시', auto_now_add=True)
    dedupe_key = models.CharField('중복제거키', max_length=100, null=True, blank=True)
    status = models.CharField('상태', max_length=10, choices=STATUS_CHOICES, default='SENT')
    
    class Meta:
        db_table = 'notifications'
        verbose_name = '알림'
        verbose_name_plural = '알림'
        ordering = ['-sent_at']
    
    def __str__(self):
        return f"{self.title} -> {self.sent_to} ({self.status})"
