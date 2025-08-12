# SVCMON 서비스 설치/관리 스크립트 (망구분별)
# Windows 서비스로 등록, 시작, 중지, 제거
import os
import sys
import subprocess
import time
import argparse

def run_command(cmd, check=True):
    """명령어 실행"""
    print(f"실행: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, check=check, 
                              capture_output=True, text=True, encoding='utf-8')
        if result.stdout:
            print(result.stdout)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"오류: {e}")
        if e.stderr:
            print(f"stderr: {e.stderr}")
        return False

def check_admin():
    """관리자 권한 확인"""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def get_service_name(network_group_name=None):
    """망구분에 따른 서비스 이름 반환"""
    if network_group_name:
        return f"SVCMON_{network_group_name}"
    else:
        return "SVCMON_ALL"

def install_service(network_group_id=None, network_group_name=None):
    """서비스 설치 (망구분별)"""
    service_name = get_service_name(network_group_name)
    print(f"=== {service_name} 서비스 설치 ===")
    
    if not check_admin():
        print("오류: 관리자 권한이 필요합니다.")
        print("PowerShell을 관리자로 실행한 후 다시 시도하세요.")
        return False
    
    # 현재 디렉토리에서 실행
    service_path = os.path.join(os.getcwd(), "svcmon_service.py")
    
    if not os.path.exists(service_path):
        print(f"오류: {service_path} 파일을 찾을 수 없습니다.")
        return False
    
    # 서비스 설치 명령 구성
    cmd = f'python "{service_path}"'
    if network_group_id:
        cmd += f" --network-group-id {network_group_id}"
    if network_group_name:
        cmd += f" --network-group-name {network_group_name}"
    cmd += " install"
    
    return run_command(cmd)

def remove_service(network_group_name=None):
    """서비스 제거 (망구분별)"""
    service_name = get_service_name(network_group_name)
    print(f"=== {service_name} 서비스 제거 ===")
    
    if not check_admin():
        print("오류: 관리자 권한이 필요합니다.")
        return False
    
    # 서비스 중지
    print("서비스 중지 중...")
    run_command(f"net stop {service_name}", check=False)
    
    # 서비스 제거
    service_path = os.path.join(os.getcwd(), "svcmon_service.py")
    cmd = f'python "{service_path}"'
    if network_group_name:
        cmd += f" --network-group-name {network_group_name}"
    cmd += " remove"
    return run_command(cmd)

def start_service(network_group_name=None):
    """서비스 시작 (망구분별)"""
    service_name = get_service_name(network_group_name)
    print(f"=== {service_name} 서비스 시작 ===")
    return run_command(f"net start {service_name}")

def stop_service(network_group_name=None):
    """서비스 중지 (망구분별)"""
    service_name = get_service_name(network_group_name)
    print(f"=== {service_name} 서비스 중지 ===")
    return run_command(f"net stop {service_name}")

def status_service(network_group_name=None):
    """서비스 상태 확인 (망구분별)"""
    service_name = get_service_name(network_group_name)
    print(f"=== {service_name} 서비스 상태 ===")
    return run_command(f"sc query {service_name}")

def restart_service(network_group_name=None):
    """서비스 재시작 (망구분별)"""
    service_name = get_service_name(network_group_name)
    print(f"=== {service_name} 서비스 재시작 ===")
    stop_service(network_group_name)
    time.sleep(2)
    return start_service(network_group_name)

def run_console(network_group_id=None, network_group_name=None):
    """콘솔 모드로 실행 (망구분별)"""
    print("=== SVCMON 콘솔 모드 실행 ===")
    if network_group_name:
        print(f"망구분: {network_group_name}")
    print("Ctrl+C로 종료하세요.")
    
    service_path = os.path.join(os.getcwd(), "svcmon_service.py")
    
    if not os.path.exists(service_path):
        print(f"오류: {service_path} 파일을 찾을 수 없습니다.")
        return False
    
    # 명령 구성
    cmd = [sys.executable, service_path]
    if network_group_id:
        cmd.extend(["--network-group-id", str(network_group_id)])
    if network_group_name:
        cmd.extend(["--network-group-name", network_group_name])
    
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n콘솔 모드가 종료되었습니다.")
    except subprocess.CalledProcessError as e:
        print(f"실행 오류: {e}")
        return False
    
    return True

def list_all_services():
    """모든 SVCMON 서비스 목록 조회"""
    print("=== 모든 SVCMON 서비스 상태 ===")
    return run_command("sc query type= service state= all | findstr SVCMON")

def show_menu():
    """메뉴 표시"""
    print("\n" + "="*60)
    print("SVCMON 서비스 관리 도구 (망구분별)")
    print("="*60)
    print("1. 서비스 설치 (망구분 지정)")
    print("2. 서비스 제거 (망구분 지정)") 
    print("3. 서비스 시작 (망구분 지정)")
    print("4. 서비스 중지 (망구분 지정)")
    print("5. 서비스 재시작 (망구분 지정)")
    print("6. 서비스 상태 확인 (망구분 지정)")
    print("7. 콘솔 모드로 실행 (망구분 지정)")
    print("8. 모든 SVCMON 서비스 목록")
    print("9. 종료")
    print("="*60)

def get_network_group_input():
    """사용자로부터 망구분 정보 입력받기"""
    print("\n망구분 정보 입력:")
    network_group_name = input("망구분 이름 (예: INTERNAL, DMZ 등, 전체는 빈값): ").strip()
    network_group_id = None
    
    if network_group_name:
        try:
            network_group_id = int(input("망구분 ID (숫자): ").strip())
        except ValueError:
            print("잘못된 ID입니다. ID 없이 진행합니다.")
            network_group_id = None
    
    return network_group_id, network_group_name if network_group_name else None

def main():
    """메인 함수 (망구분별)"""
    parser = argparse.ArgumentParser(description='SVCMON 서비스 관리 도구')
    parser.add_argument('--network-group-id', type=int, help='망구분 ID')
    parser.add_argument('--network-group-name', type=str, help='망구분 이름')
    parser.add_argument('action', nargs='?', help='액션 (install|remove|start|stop|restart|status|console|list)')
    
    # 명령줄 인수 파싱
    args = parser.parse_args()
    
    if args.action:
        # 명령줄 인수로 직접 실행
        action = args.action.lower()
        
        if action == 'list':
            list_all_services()
            sys.exit(0)
        
        actions = {
            'install': lambda: install_service(args.network_group_id, args.network_group_name),
            'remove': lambda: remove_service(args.network_group_name),
            'start': lambda: start_service(args.network_group_name),
            'stop': lambda: stop_service(args.network_group_name),
            'restart': lambda: restart_service(args.network_group_name),
            'status': lambda: status_service(args.network_group_name),
            'console': lambda: run_console(args.network_group_id, args.network_group_name)
        }
        
        if action in actions:
            success = actions[action]()
            sys.exit(0 if success else 1)
        else:
            print(f"지원하지 않는 명령: {action}")
            print("사용법: python service_manager.py [install|remove|start|stop|restart|status|console|list]")
            print("예시: python service_manager.py --network-group-name INTERNAL --network-group-id 1 install")
            sys.exit(1)
    
    # 대화형 메뉴
    while True:
        show_menu()
        try:
            choice = input("선택하세요 (1-9): ").strip()
            
            if choice in ['1', '2', '3', '4', '5', '6', '7']:
                network_group_id, network_group_name = get_network_group_input()
                
                if choice == '1':
                    install_service(network_group_id, network_group_name)
                elif choice == '2':
                    remove_service(network_group_name)
                elif choice == '3':
                    start_service(network_group_name)
                elif choice == '4':
                    stop_service(network_group_name)
                elif choice == '5':
                    restart_service(network_group_name)
                elif choice == '6':
                    status_service(network_group_name)
                elif choice == '7':
                    run_console(network_group_id, network_group_name)
                    
            elif choice == '8':
                list_all_services()
            elif choice == '9':
                print("프로그램을 종료합니다.")
                break
            else:
                print("잘못된 선택입니다. 1-9 사이의 숫자를 입력하세요.")
                
        except KeyboardInterrupt:
            print("\n프로그램을 종료합니다.")
            break
        except Exception as e:
            print(f"오류 발생: {e}")
        
        input("\n계속하려면 Enter를 누르세요...")

if __name__ == "__main__":
    main()
