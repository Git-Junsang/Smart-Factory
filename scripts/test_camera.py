"""카메라 + YOLO 단독 점검.

컨베이어/서보/IR 없이 비전 모듈만 검증합니다.
검사대 위치에 사과/바나나/오렌지 사진을 두고 결과를 확인하세요.

사용:  python -m scripts.test_camera
"""
import time
from src.vision import Vision


def main():
    # 기여자: 서준상 1.0 | 기능: 비전 모듈 단독 점검 — 1초 주기로 classify_stable 결과를 반복 출력
    v = Vision()
    print("Press Ctrl+C to stop.\n")
    try:
        while True:
            cls = v.classify_stable()
            print(f"  → result: {cls}\n")
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nbye.")
    finally:
        v.close()


if __name__ == "__main__":
    main()
