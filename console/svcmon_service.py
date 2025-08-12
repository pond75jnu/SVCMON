# SVCMON 콘솔 모니터링 프로그램
# 전남대학교 웹사이트 모니터링 시스템 - Windows 서비스 (망구분별 실행)
import os
import sys
import time
import asyncio
import aiohttp
import logging
import socket
import threading
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urlparse

import pyodbc
import win32serviceutil
import win32service
import win32event
import servicemanager

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('svcmon_service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('SVCMON')


@dataclass
class EndpointCheck:
    """체크할 엔드포인트 정보"""
    endpoint_id: int
    url: str
    poll_interval_sec: int
    domain: str
    site_name: str
    network_group_name: str
    last_checked_at: datetime
    next_check_due: datetime


@dataclass
class CheckResult:
    """체크 결과"""
    endpoint_id: int
    status_code: Optional[int] = None
    latency_ms: Optional[int] = None
    headers: Optional[str] = None
    error: Optional[str] = None
    checked_at: Optional[datetime] = None


class DatabaseManager:
    """데이터베이스 연결 및 저장프로시저 실행 관리"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._connection_pool = []
        self._pool_size = 5
        self._pool_lock = threading.Lock()
        
    def _get_connection(self) -> pyodbc.Connection:
        """연결 풀에서 연결 가져오기"""
        with self._pool_lock:
            if self._connection_pool:
                conn = self._connection_pool.pop()
                # 연결 상태 확인
                try:
                    conn.execute("SELECT 1")
                    return conn
                except:
                    # 연결이 끊어졌으면 새로 생성
                    pass
        
        # 새 연결 생성
        return pyodbc.connect(self.connection_string)
    
    def _return_connection(self, conn: pyodbc.Connection):
        """연결을 풀에 반환"""
        with self._pool_lock:
            if len(self._connection_pool) < self._pool_size:
                self._connection_pool.append(conn)
            else:
                conn.close()
    
    def execute_sp(self, sp_name: str, params: Dict = None) -> List[Dict]:
        """저장프로시저 실행 (결과 반환)"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            if params:
                param_list = list(params.values())
                cursor.execute(f"EXEC {sp_name} {','.join(['?' for _ in param_list])}", param_list)
            else:
                cursor.execute(f"EXEC {sp_name}")
            
            # 결과를 딕셔너리 리스트로 변환
            columns = [column[0] for column in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            
            result = []
            for row in rows:
                result.append(dict(zip(columns, row)))
            
            conn.commit()
            return result
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"저장프로시저 실행 오류 ({sp_name}): {e}")
            raise
        finally:
            if conn:
                self._return_connection(conn)
    
    def execute_sp_non_query(self, sp_name: str, params: Dict = None) -> bool:
        """저장프로시저 실행 (결과 반환 없음)"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            if params:
                param_list = list(params.values())
                cursor.execute(f"EXEC {sp_name} {','.join(['?' for _ in param_list])}", param_list)
            else:
                cursor.execute(f"EXEC {sp_name}")
            
            conn.commit()
            return True
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"저장프로시저 실행 오류 ({sp_name}): {e}")
            return False
        finally:
            if conn:
                self._return_connection(conn)


class HttpChecker:
    """HTTP 엔드포인트 체크 담당"""
    
    def __init__(self, timeout: int = 30, max_concurrent: int = 50):
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        
    async def check_endpoint(self, endpoint: EndpointCheck) -> CheckResult:
        """단일 엔드포인트 체크"""
        async with self._semaphore:
            start_time = datetime.now()
            result = CheckResult(endpoint_id=endpoint.endpoint_id, checked_at=start_time)
            
            try:
                # aiohttp로 HTTP 요청
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(endpoint.url) as response:
                        end_time = datetime.now()
                        latency = int((end_time - start_time).total_seconds() * 1000)
                        
                        result.status_code = response.status
                        result.latency_ms = latency
                        result.headers = str(dict(response.headers))[:4000]  # 헤더 크기 제한
                        
                        logger.info(f"체크 완료: {endpoint.url} - {response.status} ({latency}ms)")
                        
            except asyncio.TimeoutError:
                result.error = "요청 시간 초과"
                logger.warning(f"시간 초과: {endpoint.url}")
                
            except aiohttp.ClientError as e:
                result.error = f"클라이언트 오류: {str(e)}"
                logger.warning(f"클라이언트 오류: {endpoint.url} - {e}")
                
            except Exception as e:
                result.error = f"예상치 못한 오류: {str(e)}"
                logger.error(f"예상치 못한 오류: {endpoint.url} - {e}")
            
            return result
    
    async def check_batch(self, endpoints: List[EndpointCheck]) -> List[CheckResult]:
        """여러 엔드포인트 동시 체크"""
        if not endpoints:
            return []
        
        tasks = [self.check_endpoint(endpoint) for endpoint in endpoints]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 예외 처리
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # 예외가 발생한 경우 오류 결과 생성
                error_result = CheckResult(
                    endpoint_id=endpoints[i].endpoint_id,
                    error=f"체크 실행 오류: {str(result)}",
                    checked_at=datetime.now()
                )
                valid_results.append(error_result)
                logger.error(f"체크 실행 오류: {endpoints[i].url} - {result}")
            else:
                valid_results.append(result)
        
        return valid_results


class MonitoringService:
    """모니터링 서비스 메인 클래스 (망구분별 실행)"""
    
    def __init__(self, network_group_id: Optional[int] = None, network_group_name: Optional[str] = None):
        # 설정
        self.connection_string = "Driver={ODBC Driver 17 for SQL Server};Server=devhakdb;Database=SVCMON;Trusted_Connection=yes;TrustServerCertificate=yes;"
        self.batch_size = 50
        self.poll_interval = 10  # 메인 루프 간격 (초)
        self.max_concurrent = 50
        self.timeout = 30
        
        # 망구분 설정
        self.network_group_id = network_group_id
        self.network_group_name = network_group_name
        
        # 서비스 이름 설정 (망구분별)
        if network_group_name:
            self.service_name = f"SVCMON_{network_group_name}"
            self.service_display_name = f"SVCMON 모니터링 서비스 - {network_group_name}"
        else:
            self.service_name = "SVCMON_ALL"
            self.service_display_name = "SVCMON 모니터링 서비스 - 전체"
        
        # 로그 파일 설정 (망구분별)
        log_filename = f'svcmon_{network_group_name or "all"}.log'
        self._setup_logging(log_filename)
        
        # 컴포넌트 초기화
        self.db = DatabaseManager(self.connection_string)
        self.http_checker = HttpChecker(timeout=self.timeout, max_concurrent=self.max_concurrent)
        
        # 제어 플래그
        self.running = False
        self.stop_event = threading.Event()
        
        logger.info(f"모니터링 서비스 초기화 완료 - 망구분: {network_group_name or '전체'}")
    
    def _setup_logging(self, log_filename: str):
        """망구분별 로깅 설정"""
        # 기존 핸들러 제거
        logger.handlers.clear()
        
        # 새 핸들러 추가
        file_handler = logging.FileHandler(log_filename, encoding='utf-8')
        console_handler = logging.StreamHandler()
        
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
    def start(self):
        """서비스 시작"""
        logger.info(f"SVCMON 모니터링 서비스를 시작합니다 - 망구분: {self.network_group_name or '전체'}")
        self.running = True
        
        # 비동기 루프를 별도 스레드에서 실행
        self.loop_thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self.loop_thread.start()
        
    def stop(self):
        """서비스 종료"""
        logger.info(f"SVCMON 모니터링 서비스를 종료합니다 - 망구분: {self.network_group_name or '전체'}")
        self.running = False
        self.stop_event.set()
        
        if hasattr(self, 'loop_thread'):
            self.loop_thread.join(timeout=10)
    
    def _run_async_loop(self):
        """비동기 루프를 별도 스레드에서 실행"""
        asyncio.run(self._monitoring_loop())
    
    async def _monitoring_loop(self):
        """메인 모니터링 루프"""
        logger.info("모니터링 루프를 시작합니다.")
        
        while self.running:
            try:
                await self._process_batch()
                
                # 다음 주기까지 대기
                for _ in range(self.poll_interval):
                    if not self.running:
                        break
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"모니터링 루프 오류: {e}")
                await asyncio.sleep(5)  # 오류 시 잠시 대기
        
        logger.info("모니터링 루프가 종료되었습니다.")
    
    async def _process_batch(self):
        """한 배치의 엔드포인트들을 처리 (망구분별)"""
        try:
            # 다음 폴링 배치 조회 (망구분 필터링)
            now = datetime.now()
            params = {
                'now': now,
                'limit': self.batch_size,
                'max_concurrency': self.max_concurrent
            }
            
            # 망구분 필터링을 위해 일단 기존 SP 호출 후 애플리케이션에서 필터링
            batch_data = self.db.execute_sp('usp_next_poll_batch', params)
            
            # 망구분별 필터링 (애플리케이션 레벨)
            if self.network_group_name and batch_data:
                batch_data = [row for row in batch_data if row['network_group_name'] == self.network_group_name]
            
            if not batch_data:
                logger.debug(f"체크할 엔드포인트가 없습니다. (망구분: {self.network_group_name or '전체'})")
                return
            
            # EndpointCheck 객체로 변환
            endpoints = []
            for row in batch_data:
                endpoint = EndpointCheck(
                    endpoint_id=row['endpoint_id'],
                    url=row['url'],
                    poll_interval_sec=row['poll_interval_sec'],
                    domain=row['domain'],
                    site_name=row['site_name'],
                    network_group_name=row['network_group_name'],
                    last_checked_at=row['last_checked_at'],
                    next_check_due=row['next_check_due']
                )
                endpoints.append(endpoint)
            
            logger.info(f"{len(endpoints)}개 엔드포인트를 체크합니다.")
            
            # HTTP 체크 실행
            results = await self.http_checker.check_batch(endpoints)
            
            # 결과를 데이터베이스에 저장
            await self._save_results(results)
            
        except Exception as e:
            logger.error(f"배치 처리 오류: {e}")
    
    async def _save_results(self, results: List[CheckResult]):
        """체크 결과들을 데이터베이스에 저장"""
        for result in results:
            try:
                params = {
                    'endpoint_id': result.endpoint_id,
                    'status_code': result.status_code,
                    'latency_ms': result.latency_ms,
                    'headers': result.headers,
                    'error': result.error,
                    'checked_at': result.checked_at or datetime.now()
                }
                
                # 비동기로 저장하기 위해 스레드풀에서 실행
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None, 
                    lambda: self.db.execute_sp('usp_record_check', params)
                )
                
            except Exception as e:
                logger.error(f"결과 저장 오류 (endpoint_id: {result.endpoint_id}): {e}")


class SVCMONService(win32serviceutil.ServiceFramework):
    """Windows 서비스 래퍼 (망구분별)"""
    
    _svc_name_ = "SVCMON"  # 기본값, 동적으로 변경됨
    _svc_display_name_ = "전남대학교 웹사이트 모니터링 서비스"  # 기본값, 동적으로 변경됨
    _svc_description_ = "전남대학교 웹사이트들의 상태를 주기적으로 모니터링하는 서비스입니다."
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        self.monitoring_service = None
        
        # 명령행 인수에서 망구분 정보 추출
        self.network_group_id = getattr(args, 'network_group_id', None)
        self.network_group_name = getattr(args, 'network_group_name', None)
    
    def SvcStop(self):
        """서비스 중지"""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        
        if self.monitoring_service:
            self.monitoring_service.stop()
    
    def SvcDoRun(self):
        """서비스 실행"""
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        
        try:
            # 모니터링 서비스 시작 (망구분 지정)
            self.monitoring_service = MonitoringService(
                network_group_id=self.network_group_id,
                network_group_name=self.network_group_name
            )
            self.monitoring_service.start()
            
            # 서비스 종료 신호까지 대기
            win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)
            
        except Exception as e:
            logger.error(f"서비스 실행 오류: {e}")
            servicemanager.LogErrorMsg(f"서비스 실행 오류: {e}")
        
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STOPPED,
            (self._svc_name_, '')
        )


def main():
    """메인 함수 - 서비스 설치/제거/실행 (망구분별)"""
    parser = argparse.ArgumentParser(description='SVCMON 모니터링 서비스')
    parser.add_argument('--network-group-id', type=int, help='망구분 ID')
    parser.add_argument('--network-group-name', type=str, help='망구분 이름')
    parser.add_argument('action', nargs='?', help='서비스 액션 (install/remove/start/stop/debug)')
    
    # 서비스 관련 인수와 사용자 정의 인수 분리
    service_args = []
    custom_args = []
    
    i = 0
    while i < len(sys.argv[1:]):
        arg = sys.argv[i + 1]
        if arg.startswith('--network-group'):
            custom_args.append(arg)
            if '=' not in arg and i + 1 < len(sys.argv[1:]):
                i += 1
                custom_args.append(sys.argv[i + 1])
        else:
            service_args.append(arg)
        i += 1
    
    # 사용자 정의 인수 파싱
    args, _ = parser.parse_known_args(custom_args)
    
    if len(service_args) == 0:
        # 콘솔에서 직접 실행
        print(f"SVCMON 모니터링 서비스를 콘솔 모드로 실행합니다.")
        if args.network_group_name:
            print(f"망구분: {args.network_group_name}")
        print("Ctrl+C로 종료하세요.")
        
        service = MonitoringService(
            network_group_id=args.network_group_id,
            network_group_name=args.network_group_name
        )
        try:
            service.start()
            
            # 무한 대기
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n종료 신호를 받았습니다.")
        finally:
            service.stop()
            print("서비스가 종료되었습니다.")
    else:
        # Windows 서비스로 실행
        # 망구분별 서비스 이름 설정
        if args.network_group_name:
            SVCMONService._svc_name_ = f"SVCMON_{args.network_group_name}"
            SVCMONService._svc_display_name_ = f"SVCMON 모니터링 서비스 - {args.network_group_name}"
            
            # 서비스 클래스에 망구분 정보 전달
            original_init = SVCMONService.__init__
            def patched_init(self, svc_args):
                original_init(self, svc_args)
                self.network_group_id = args.network_group_id
                self.network_group_name = args.network_group_name
            SVCMONService.__init__ = patched_init
        
        # 서비스 인수만으로 명령행 처리
        sys.argv = [sys.argv[0]] + service_args
        win32serviceutil.HandleCommandLine(SVCMONService)


if __name__ == '__main__':
    main()
