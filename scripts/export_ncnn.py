"""yolo11n.pt → NCNN 1회 변환 스크립트.

가능하면 PC에서 실행한 뒤 생성된 yolo11n_ncnn_model/ 폴더를
Raspberry Pi의 models/ 디렉토리로 복사하세요.
(라파이에서 직접 export는 5~10분 걸립니다.)

사용:
    python scripts/export_ncnn.py
"""
from ultralytics import YOLO

if __name__ == "__main__":
    # 최초 실행 시 yolo11n.pt(약 5.4MB) 자동 다운로드
    model = YOLO("yolo11n.pt")
    model.export(format="ncnn", imgsz=320)
    print("\n[OK] NCNN model created → ./yolo11n_ncnn_model/")
    print("이 폴더를 라즈베리파이의 Smart-Factory/models/ 아래로 복사하세요.")
