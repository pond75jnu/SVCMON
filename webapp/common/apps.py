from django.apps import AppConfig
import os


class CommonConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'common'
    
    def ready(self):
        """앱이 준비되었을 때 AMBER 서비스 시작"""
        try:
            from .amber_service import start_amber_service
            start_amber_service()
            print("AMBER 서비스가 시작되었습니다.")  # 콘솔에 직접 출력
        except Exception as e:
            print(f"AMBER 서비스 시작 중 오류: {e}")  # 콘솔에 직접 출력
