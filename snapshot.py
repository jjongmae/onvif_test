import os
import sys
import requests
from onvif import ONVIFCamera
from onvif.exceptions import ONVIFError

# ─── 설정 부분 (자신 환경에 맞게 수정) ───────────────────────────
CAMERA_IP    = '192.168.20.52'      # 카메라 IP
CAMERA_PORT  = 80                 # ONVIF 포트
USERNAME     = 'root'              # ONVIF 계정
PASSWORD     = 'u1gisu1gis'      # ONVIF 비밀번호

# WSDL 폴더 위치 (현재 작업 디렉터리의 wsdl/ 하위라고 가정)
WSDL_DIR = os.path.join(os.getcwd(), 'wsdl')
# ──────────────────────────────────────────────────────────────

def main():
    # 1) WSDL 경로 존재 확인
    if not os.path.isdir(WSDL_DIR):
        print(f"[ERROR] 지정된 WSDL 폴더를 찾을 수 없습니다:\n   {WSDL_DIR}")
        sys.exit(1)

    # 2) ONVIFCamera 생성 (wsdl_dir 인자 필수)
    try:
        cam = ONVIFCamera(CAMERA_IP, CAMERA_PORT, USERNAME, PASSWORD, wsdl_dir=WSDL_DIR)
    except Exception as e:
        print(f"[ERROR] ONVIFCamera 생성 실패:\n  {e}")
        sys.exit(1)

    # 3) Media 서비스 가져오기
    try:
        media_service = cam.create_media_service()
    except Exception as e:
        print(f"[ERROR] create_media_service 실패:\n  {e}")
        sys.exit(1)

    # 4) 카메라 기본 정보 및 서비스 Capabilities 확인 (선택 사항)
    try:
        device_service = cam.create_devicemgmt_service()
        dev_info = device_service.GetDeviceInformation()
        print("=== Device Information ===")
        print(f"Manufacturer: {dev_info.Manufacturer}")
        print(f"Model       : {dev_info.Model}")
        print(f"FirmwareVer : {dev_info.FirmwareVersion}")
        print(f"SerialNum   : {dev_info.SerialNumber}")
        print(f"HardwareId  : {dev_info.HardwareId}\n")
    except Exception:
        # Devicemgmt 서비스가 없거나 인증 문제 등으로 안 될 수도 있음
        pass

    # 5) 사용 가능한 프로파일 전체 출력
    print("=== Available Profiles ===")
    try:
        profiles = media_service.GetProfiles()
        if not profiles:
            print("[ERROR] 사용 가능한 ONVIF 프로파일이 없습니다.\n")
            sys.exit(1)
    except ONVIFError as e:
        print(f"[ERROR] GetProfiles 호출 실패:\n  {e}\n")
        sys.exit(1)

    for idx, p in enumerate(profiles):
        name = p.Name if hasattr(p, 'Name') else "(NoName)"
        token = p.token if hasattr(p, 'token') else "(NoToken)"
        print(f"  Profile #{idx} – Name: {name}, Token: {token}")
    print()

    # 6) 각 프로파일에 대해 GetSnapshotUri 시도
    print("=== Attempting GetSnapshotUri for each Profile ===")
    for idx, p in enumerate(profiles):
        token = p.token
        try:
            resp = media_service.GetSnapshotUri({'ProfileToken': token})
            uri = resp.Uri
            print(f"[SUCCESS] Profile #{idx} ({token}) Snapshot URI: {uri}")
        except ONVIFError as oe:
            print(f"[FAIL] Profile #{idx} ({token}) – GetSnapshotUri 실패:\n  {oe}")
        except Exception as ex:
            print(f"[FAIL] Profile #{idx} ({token}) – 기타 오류:\n  {ex}")
    print()

    # 7) (선택) 정상적으로 URI를 얻은 프로파일이 있으면, 실제 HTTP GET 테스트도 가능
    #    아래 코드는 첫 번째 성공 프로파일만 사용 예시로 작성했습니다.
    first_success_uri = None
    for p in profiles:
        try:
            tmp = media_service.GetSnapshotUri({'ProfileToken': p.token})
            first_success_uri = tmp.Uri
            break
        except Exception:
            continue

    if first_success_uri:
        print(f"[INFO] 첫 번째 정상 URI: {first_success_uri}")
        try:
            r = requests.get(first_success_uri, auth=(USERNAME, PASSWORD), timeout=5)
            if r.status_code == 200:
                save_path = os.path.join(os.getcwd(), 'snapshot.jpg')
                with open(save_path, 'wb') as f:
                    f.write(r.content)
                print(f"[SUCCESS] 스냅샷 이미지 파일 저장됨: {save_path}")
            else:
                print(f"[ERROR] HTTP GET 실패: 응답 코드 {r.status_code}")
        except Exception as e:
            print(f"[ERROR] HTTP GET 중 예외 발생:\n  {e}")
    else:
        print("[WARN] 유효한 Snapshot URI를 얻은 프로파일이 없어, HTTP GET 테스트를 수행하지 않습니다.")


if __name__ == '__main__':
    main()
