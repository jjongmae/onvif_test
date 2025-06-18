import csv
import time
import threading
import sys
from zeep.exceptions import Fault
from onvif import ONVIFCamera

# 입력 각도의 물리적 범위 (degree)
PAN_ANGLE_MIN = -180
PAN_ANGLE_MAX = 180
TILT_ANGLE_MIN = -8
TILT_ANGLE_MAX = 90

# 입력 줌 배율 범위 (배율)
ZOOM_RATIO_MIN = 1
ZOOM_RATIO_MAX = 36

# 카메라 접속 정보
camera_ip = '192.168.20.52'
camera_port = 80
username = 'root'
password = 'u1gisu1gis'
wsdl_dir = './wsdl'

def normalize(value, min_value, max_value):
    """min-max 정규화 (0~1)"""
    print(f"normalize {value} to range ({min_value}, {max_value})")
    return (value - min_value) / (max_value - min_value)

def normalize_to_minus1_1(value, min_value, max_value):
    """-1~1 정규화"""
    print(f"normalize_to_minus1_1 {value} to range ({min_value}, {max_value})")
    return 2 * (value - min_value) / (max_value - min_value) - 1

def send_ptz_ui(pan_deg, tilt_deg, zoom_ratio, status_label=None):
    try:
        # 카메라 연결 및 서비스 초기화
        camera = ONVIFCamera(camera_ip, camera_port, username, password, wsdl_dir)
        media_service = camera.create_media_service()
        ptz_service = camera.create_ptz_service()
        profiles = media_service.GetProfiles()
        profile = profiles[0]
        ptz_cfg = ptz_service.GetConfigurations()[0]
        opts = ptz_service.GetConfigurationOptions({'ConfigurationToken': ptz_cfg.token})
        pan_tilt_space = opts.Spaces.AbsolutePanTiltPositionSpace[0]
        pan_min = pan_tilt_space.XRange.Min
        pan_max = pan_tilt_space.XRange.Max
        tilt_min = pan_tilt_space.YRange.Min
        tilt_max = pan_tilt_space.YRange.Max
        zoom_space = opts.Spaces.AbsoluteZoomPositionSpace[0]
        zoom_min = zoom_space.XRange.Min
        zoom_max = zoom_space.XRange.Max
        # 정규화 및 클램핑
        if pan_min == -1 and pan_max == 1:
            pan_pos = normalize_to_minus1_1(pan_deg, PAN_ANGLE_MIN, PAN_ANGLE_MAX)
        else:
            pan_pos = normalize(pan_deg, PAN_ANGLE_MIN, PAN_ANGLE_MAX)
        if tilt_min == -1 and tilt_max == 1:
            tilt_pos = normalize_to_minus1_1(tilt_deg, TILT_ANGLE_MIN, TILT_ANGLE_MAX)
        else:
            tilt_pos = normalize(tilt_deg, TILT_ANGLE_MIN, TILT_ANGLE_MAX)
        zoom_pos = normalize(zoom_ratio, ZOOM_RATIO_MIN, ZOOM_RATIO_MAX)
        pan_pos = max(pan_min, min(pan_max, pan_pos))
        tilt_pos = max(tilt_min, min(tilt_max, tilt_pos))
        zoom_pos = max(zoom_min, min(zoom_max, zoom_pos))
        print(f"Normalized Pan: {pan_pos}, Tilt: {tilt_pos}, Zoom: {zoom_pos}")
        req = ptz_service.create_type('AbsoluteMove')
        req.ProfileToken = profile.token
        req.Position = {
            'PanTilt': {'x': pan_pos, 'y': tilt_pos},
            'Zoom': {'x': zoom_pos}
        }
        req.Speed = {
            'PanTilt': {'x': 1, 'y': 1},
            'Zoom': {'x': 1}
        }
        ptz_service.AbsoluteMove(req)
        if status_label:
            status_label.config(text=f'✅ PTZ 이동 명령 전송 완료! (Pan={pan_deg}, Tilt={tilt_deg}, Zoom={zoom_ratio})', fg='green')
    except Fault as fault:
        if status_label:
            status_label.config(text=f'❌ SOAP Fault 발생: {fault}', fg='red')
        else:
            print(f'❌ SOAP Fault 발생: {fault}')
    except Exception as e:
        if status_label:
            status_label.config(text=f'❌ 예외 발생: {e}', fg='red')
        else:
            print(f'❌ 예외 발생: {e}')

# CSV 파일 경로는 인자로 받음

def read_schedule(csv_path):
    schedule = []
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            schedule.append({
                'time': float(row['time']),
                'pan': float(row['pan']),
                'tilt': float(row['tilt']),
                'zoom': float(row['zoom'])
            })
    # 시간 순 정렬
    schedule.sort(key=lambda x: x['time'])
    return schedule

def run_schedule(schedule):
    start_time = time.time()
    for item in schedule:
        target_time = start_time + item['time']
        now = time.time()
        wait_sec = target_time - now
        if wait_sec > 0:
            time.sleep(wait_sec)
        now_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()) + f'.{int((time.time()%1)*1000):03d}'
        print(f"[{now_str}] [SCHEDULE] {item['time']}초: Pan={item['pan']}, Tilt={item['tilt']}, Zoom={item['zoom']}")
        # PTZ 명령 전송 (UI 없이)
        send_ptz_ui(item['pan'], item['tilt'], item['zoom'])
    print('스케줄 완료!')

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='PTZ 스케줄러')
    parser.add_argument('-f', '--file', required=True, help='PTZ 스케줄 CSV 파일 경로')
    args = parser.parse_args()
    csv_path = args.file
    schedule = read_schedule(csv_path)
    print(f"총 {len(schedule)}개의 PTZ 명령을 스케줄링합니다.")
    run_schedule(schedule)
