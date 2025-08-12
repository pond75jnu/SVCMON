"""
Database connection and stored procedure execution middleware.
모든 데이터베이스 입출력은 이 클래스를 통해 저장프로시저로 처리됩니다.
"""

import logging
from typing import Dict, List, Any, Optional
from django.db import connection
from django.conf import settings

logger = logging.getLogger(__name__)


class DatabaseMiddleware:
    """
    MS SQL Server 저장프로시저 호출을 위한 미들웨어 클래스
    """
    
    @staticmethod
    def execute_sp(sp_name: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        저장프로시저를 실행하고 결과를 반환합니다.
        
        Args:
            sp_name: 저장프로시저 이름
            params: 파라미터 딕셔너리
            
        Returns:
            결과 집합의 리스트
        """
        with connection.cursor() as cursor:
            try:
                # 파라미터 준비
                if params:
                    param_list = []
                    param_values = []
                    for key, value in params.items():
                        param_list.append(f"@{key} = %s")
                        param_values.append(value)
                    
                    sql = f"EXEC {sp_name} {', '.join(param_list)}"
                    cursor.execute(sql, param_values)
                else:
                    sql = f"EXEC {sp_name}"
                    cursor.execute(sql)
                
                # 결과 가져오기
                columns = [col[0] for col in cursor.description] if cursor.description else []
                results = []
                
                for row in cursor.fetchall():
                    row_dict = dict(zip(columns, row))
                    results.append(row_dict)
                
                logger.info(f"SP {sp_name} executed successfully. Returned {len(results)} rows.")
                return results
                
            except Exception as e:
                logger.error(f"Error executing SP {sp_name}: {str(e)}")
                raise
    
    @staticmethod
    def execute_sp_non_query(sp_name: str, params: Optional[Dict[str, Any]] = None) -> int:
        """
        결과 집합을 반환하지 않는 저장프로시저를 실행합니다.
        
        Args:
            sp_name: 저장프로시저 이름
            params: 파라미터 딕셔너리
            
        Returns:
            영향받은 행의 수
        """
        with connection.cursor() as cursor:
            try:
                # 파라미터 준비
                if params:
                    param_list = []
                    param_values = []
                    for key, value in params.items():
                        param_list.append(f"@{key} = %s")
                        param_values.append(value)
                    
                    sql = f"EXEC {sp_name} {', '.join(param_list)}"
                    result = cursor.execute(sql, param_values)
                else:
                    sql = f"EXEC {sp_name}"
                    result = cursor.execute(sql)
                
                row_count = cursor.rowcount
                logger.info(f"SP {sp_name} executed successfully. {row_count} rows affected.")
                return row_count
                
            except Exception as e:
                logger.error(f"Error executing SP {sp_name}: {str(e)}")
                raise
    
    @staticmethod
    def execute_sp_scalar(sp_name: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        단일 값을 반환하는 저장프로시저를 실행합니다.
        
        Args:
            sp_name: 저장프로시저 이름
            params: 파라미터 딕셔너리
            
        Returns:
            단일 값
        """
        with connection.cursor() as cursor:
            try:
                # 파라미터 준비
                if params:
                    param_list = []
                    param_values = []
                    for key, value in params.items():
                        param_list.append(f"@{key} = %s")
                        param_values.append(value)
                    
                    sql = f"EXEC {sp_name} {', '.join(param_list)}"
                    cursor.execute(sql, param_values)
                else:
                    sql = f"EXEC {sp_name}"
                    cursor.execute(sql)
                
                # 첫 번째 행의 첫 번째 컬럼 값 반환
                row = cursor.fetchone()
                result = row[0] if row else None
                
                logger.info(f"SP {sp_name} executed successfully. Returned scalar value: {result}")
                return result
                
            except Exception as e:
                logger.error(f"Error executing SP {sp_name}: {str(e)}")
                raise


class SPRepository:
    """
    저장프로시저를 통한 데이터 액세스 리포지토리 기본 클래스
    """
    
    def __init__(self):
        self.db = DatabaseMiddleware()
    
    def execute_query(self, sp_name: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """조회용 저장프로시저 실행"""
        return self.db.execute_sp(sp_name, params)
    
    def execute_command(self, sp_name: str, params: Optional[Dict[str, Any]] = None) -> int:
        """CUD 작업용 저장프로시저 실행"""
        return self.db.execute_sp_non_query(sp_name, params)
    
    def execute_scalar(self, sp_name: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """단일 값 반환 저장프로시저 실행"""
        return self.db.execute_sp_scalar(sp_name, params)
