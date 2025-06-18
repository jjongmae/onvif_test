import tkinter as tk
from tkinter import messagebox
from onvif import ONVIFCamera
from zeep.exceptions import Fault
import threading

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
    except Exception as e:
        if status_label:
            status_label.config(text=f'❌ 예외 발생: {e}', fg='red')

def get_ptz_status_ui(status_label=None):
    try:
        camera = ONVIFCamera(camera_ip, camera_port, username, password, wsdl_dir)
        media_service = camera.create_media_service()
        ptz_service = camera.create_ptz_service()
        profiles = media_service.GetProfiles()
        profile = profiles[0]
        status = ptz_service.GetStatus({'ProfileToken': profile.token})
        msg = ''
        if status.Position:
            if status.Position.PanTilt:
                pan_raw = status.Position.PanTilt.x
                tilt_raw = status.Position.PanTilt.y
                if pan_raw >= -1 and pan_raw <= 1:
                    pan_deg = ((pan_raw + 1) / 2) * (PAN_ANGLE_MAX - PAN_ANGLE_MIN) + PAN_ANGLE_MIN
                else:
                    pan_deg = pan_raw * (PAN_ANGLE_MAX - PAN_ANGLE_MIN) + PAN_ANGLE_MIN
                if tilt_raw >= -1 and tilt_raw <= 1:
                    tilt_deg = ((tilt_raw + 1) / 2) * (TILT_ANGLE_MAX - TILT_ANGLE_MIN) + TILT_ANGLE_MIN
                else:
                    tilt_deg = tilt_raw * (TILT_ANGLE_MAX - TILT_ANGLE_MIN) + TILT_ANGLE_MIN
                msg += f"Pan: {pan_raw:.4f} (→ {pan_deg:.2f} deg)\n"
                msg += f"Tilt: {tilt_raw:.4f} (→ {tilt_deg:.2f} deg)\n"
            if status.Position.Zoom:
                zoom_raw = status.Position.Zoom.x
                zoom_ratio = zoom_raw * (ZOOM_RATIO_MAX - ZOOM_RATIO_MIN) + ZOOM_RATIO_MIN
                msg += f"Zoom: {zoom_raw:.4f} (→ {zoom_ratio:.2f}x)"
        else:
            msg = '⚠️ PTZ 위치 정보 없음'
        if status_label:
            status_label.config(text=msg, fg='black')
    except Fault as fault:
        if status_label:
            status_label.config(text=f'❌ SOAP Fault 발생: {fault}', fg='red')
    except Exception as e:
        if status_label:
            status_label.config(text=f'❌ 예외 발생: {e}', fg='red')

if __name__ == '__main__':
    root = tk.Tk()
    root.title('ONVIF PTZ Test')
    root.geometry('650x300')
    root.resizable(False, False)

    # ✅ 상단에 약간의 공백 추가
    spacer_top = tk.Frame(root, height=10)
    spacer_top.pack(fill='x')

    # ✅ 상단 프레임: 상태 메시지 + 상태 조회 버튼
    frame_top = tk.Frame(root)
    frame_top.pack(fill='x', padx=10, pady=(10, 5))

    ptz_status_label = tk.Label(frame_top, text='', anchor='w', fg='black', height=3, relief='groove', justify='left')
    ptz_status_label.pack(side='left', fill='x', expand=True, padx=(0, 5))

    def on_get_status():
        ptz_status_label.config(text='PTZ 상태 조회 중...', fg='blue')
        root.update_idletasks()
        def worker():
            get_ptz_status_ui(ptz_status_label)
        threading.Thread(target=worker, daemon=True).start()

    tk.Button(frame_top, text='PTZ 상태 조회', command=on_get_status, width=16, height=3).pack(side='right')

    # ✅ 중단 프레임: 입력 필드 + 전송 버튼
    frame_middle = tk.Frame(root)
    frame_middle.pack(fill='x', padx=10, pady=(5, 5))

    # 입력 필드 (왼쪽)
    input_frame = tk.Frame(frame_middle)
    input_frame.pack(side='left', fill='x', expand=True)

    tk.Label(input_frame, text='Pan (deg):').grid(row=0, column=0, sticky='e', padx=5, pady=2)
    tk.Label(input_frame, text='Tilt (deg):').grid(row=1, column=0, sticky='e', padx=5, pady=2)
    tk.Label(input_frame, text='Zoom (x):').grid(row=2, column=0, sticky='e', padx=5, pady=2)

    pan_var = tk.DoubleVar(value=0)
    tilt_var = tk.DoubleVar(value=0)
    zoom_var = tk.DoubleVar(value=1)

    tk.Entry(input_frame, textvariable=pan_var, width=20).grid(row=0, column=1, sticky='w', padx=5, pady=2)
    tk.Entry(input_frame, textvariable=tilt_var, width=20).grid(row=1, column=1, sticky='w', padx=5, pady=2)
    tk.Entry(input_frame, textvariable=zoom_var, width=20).grid(row=2, column=1, sticky='w', padx=5, pady=2)

    def on_send():
        status_label.config(text='PTZ 이동 명령 전송 중...', fg='blue')
        root.update_idletasks()
        def worker():
            send_ptz_ui(pan_var.get(), tilt_var.get(), zoom_var.get(), status_label)
        threading.Thread(target=worker, daemon=True).start()

    # 전송 버튼 (오른쪽)
    tk.Button(frame_middle, text='전송', command=on_send, width=16, height=3).pack(side='right', padx=(10, 0))

    # ✅ 하단 상태 표시 (위와 같은 높이로)
    status_label = tk.Label(root, text='', anchor='w', fg='black', height=3, relief='groove', justify='left')
    status_label.pack(fill='x', padx=10, pady=(10, 0))

    root.mainloop()
