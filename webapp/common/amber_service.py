"""
백그라운드 AMBER 체크 서비스
웹서버가 실행되는 동안 주기적으로 폴링 간격을 체크하여 
콘솔 프로그램이 중지된 경우 AMBER 레코드를 자동 삽입합니다.
"""

import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from django.conf import settings
from common.database import DatabaseMiddleware

# 한국 시간대 설정
KST = timezone(timedelta(hours=9))

logger = logging.getLogger(__name__)


class AmberCheckService:
    """
    AMBER 상태 체크 서비스
    백그라운드에서 실행되어 폴링 간격을 모니터링하고 
    필요 시 AMBER 레코드를 삽입합니다.
    """
    
    def __init__(self):
        self.is_running = False
        self.check_thread = None
        self.check_interval = 30  # 30초마다 체크 (테스트용으로 짧게)
        self.db = DatabaseMiddleware()
        
    def start(self):
        """백그라운드 체크 서비스 시작"""
        if self.is_running:
            logger.warning("AMBER 체크 서비스가 이미 실행 중입니다.")
            return
            
        self.is_running = True
        self.check_thread = threading.Thread(target=self._check_loop, daemon=True)
        self.check_thread.start()
        logger.info("AMBER 체크 서비스가 시작되었습니다.")
    
    def stop(self):
        """백그라운드 체크 서비스 중지"""
        self.is_running = False
        if self.check_thread and self.check_thread.is_alive():
            self.check_thread.join(timeout=5)
        logger.info("AMBER 체크 서비스가 중지되었습니다.")
    
    def _check_loop(self):
        """메인 체크 루프"""
        logger.info("AMBER 체크 루프가 시작되었습니다.")
        
        while self.is_running:
            try:
                self._check_and_insert_amber_records()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"AMBER 체크 중 오류 발생: {e}")
                time.sleep(self.check_interval)
    
    def _check_and_insert_amber_records(self):
        """모든 엔드포인트에 대해 AMBER 조건 체크 및 레코드 삽입"""
        try:
            # 활성화된 모든 엔드포인트 조회
            endpoints = self._get_active_endpoints()
            current_time = datetime.now(KST)  # 한국 시간으로 변경
            
            logger.debug(f"AMBER 체크 시작 - 현재 시간: {current_time}, 엔드포인트 수: {len(endpoints)}")
            print(f"AMBER 체크 시작 - 현재 시간: {current_time}, 엔드포인트 수: {len(endpoints)}")  # 디버그용 콘솔 출력
            
            for endpoint in endpoints:
                try:
                    self._process_endpoint_amber_check(endpoint, current_time)
                except Exception as e:
                    logger.error(f"엔드포인트 {endpoint.get('endpoint_id')} AMBER 체크 중 오류: {e}")
                    
        except Exception as e:
            logger.error(f"AMBER 체크 프로세스 중 오류 발생: {e}")
    
    def _get_active_endpoints(self) -> List[Dict[str, Any]]:
        """활성화된 엔드포인트 목록 조회"""
        try:
            results = self.db.execute_sp('usp_get_active_endpoints')
            return results
        except Exception as e:
            logger.error(f"활성 엔드포인트 조회 중 오류: {e}")
            return []
    
    def _process_endpoint_amber_check(self, endpoint: Dict[str, Any], current_time: datetime):
        """개별 엔드포인트의 AMBER 조건 체크 및 처리"""
        endpoint_id = endpoint['endpoint_id']
        endpoint_url = endpoint['endpoint_url']
        poll_interval = endpoint['poll_interval_seconds']
        
        # 마지막 체크 시간 조회
        last_check_data = self._get_last_check_time(endpoint_id)
        
        if not last_check_data:
            logger.info(f"엔드포인트 {endpoint_id}의 체크 데이터가 없습니다. N/A 레코드 삽입")
            # 체크 데이터가 없으면 현재 시간에서 폴링 간격 이전 시간을 기준으로 N/A 삽입
            reference_time = current_time - timedelta(seconds=poll_interval * 2)
            self._insert_amber_records(endpoint, reference_time, current_time, poll_interval)
            return
            
        last_checked_at = last_check_data[0]['last_checked_at']
        if last_checked_at.tzinfo is None:
            last_checked_at = last_checked_at.replace(tzinfo=KST)  # 한국 시간대로 변경
        elif last_checked_at.tzinfo != KST:
            # UTC 시간을 한국 시간으로 변환
            last_checked_at = last_checked_at.astimezone(KST)
        
        # 경과 시간 계산
        elapsed_seconds = (current_time - last_checked_at).total_seconds()
        threshold_seconds = poll_interval * 1.5  # 폴링 간격의 1.5배
        
        logger.debug(f"엔드포인트 {endpoint_id} - 경과시간: {elapsed_seconds:.2f}초, 임계값: {threshold_seconds}초")
        
        # N/A 조건 체크
        if elapsed_seconds > threshold_seconds:
            logger.info(f"N/A 조건 충족 - 엔드포인트 {endpoint_id} ({endpoint_url})")
            try:
                self._insert_amber_records(endpoint, last_checked_at, current_time, poll_interval)
            except Exception as e:
                logger.error(f"N/A 레코드 삽입 실패 - 엔드포인트 {endpoint_id}: {e}")
        else:
            logger.debug(f"N/A 조건 불충족 - 엔드포인트 {endpoint_id}")
    
    def _get_last_check_time(self, endpoint_id: int) -> List[Dict[str, Any]]:
        """엔드포인트의 마지막 체크 시간 조회"""
        try:
            params = {'endpoint_id': endpoint_id}
            results = self.db.execute_sp('usp_get_last_check_time', params)
            return results
        except Exception as e:
            logger.error(f"마지막 체크 시간 조회 중 오류 (endpoint_id: {endpoint_id}): {e}")
            return []
    
    def _insert_amber_records(self, endpoint: Dict[str, Any], last_checked_at: datetime, 
                            current_time: datetime, poll_interval: int):
        """N/A 레코드 삽입 - 현재 시간에 1개만 삽입"""
        endpoint_id = endpoint['endpoint_id']
        endpoint_url = endpoint['endpoint_url']
        
        logger.info(f"현재 시간에 N/A 레코드 삽입: {endpoint_id} - {current_time}")
        
        # 현재 시간에 N/A 레코드 1개만 삽입
        try:
            params = {
                'endpoint_id': endpoint_id,
                'status_code': 'N/A',
                'latency_ms': 0,
                'headers': '',
                'error': '체크값 없음 (신호 끊김)',
                'checked_at': current_time
            }
            
            self.db.execute_sp_non_query('usp_record_check', params)
            logger.info(f"N/A 레코드 삽입 완료: {endpoint_url} - {current_time}")
            
        except Exception as e:
            logger.error(f"N/A 레코드 삽입 실패: {endpoint_url} - {current_time}: {e}")
            
        # 강제 리로드를 위한 주석 추가


# 글로벌 서비스 인스턴스
amber_service = AmberCheckService()


def start_amber_service():
    """AMBER 서비스 시작"""
    amber_service.start()


def stop_amber_service():
    """AMBER 서비스 중지"""
    amber_service.stop()
