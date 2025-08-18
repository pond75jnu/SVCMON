import configparser
import os

def get_connection_string():
    """config.ini 파일에서 연결 문자열을 읽어 반환합니다."""
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"설정 파일({config_path})을 찾을 수 없습니다.")
        
    config.read(config_path, encoding='utf-8')
    
    try:
        return config['Database']['connection_string']
    except KeyError:
        raise KeyError("설정 파일에 [Database] 섹션이나 connection_string 키가 없습니다.")

CONNECTION_STRING = get_connection_string()
