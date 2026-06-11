"""데모용 수동 제어 — 엔터를 누를 때마다 정해진 다음 동작 1개를 수행.

발표/시연용. 자동 분류 로직(카메라) 대신 고정 시퀀스를 한 스텝씩 진행한다.
LED·OLED는 동작에 맞춰 자동 제어된다.

LED (상태 LED, 항상 하나만 점등):
  - 레일 가동            → run     (작동중 색)
  - 레일 중단 / 분류 / 서보 → inspect (검사중 색)
  - 최종 정지(마지막 단계) → stop    (중단·빨강)

OLED (분류레일 위치 → 과일 카운트 +1):
  - 0번 → Strawberry,  1번 → Orange,  2번 → Banana
  (luma 기본 폰트가 한글 미지원이라 영문 라벨 사용)

사용:  python -m scripts.demo_control
"""
from luma.core.render import canvas

from src.hardware import Hardware
from src.display import Display

# 분류레일 위치(0/1/2) → OLED 표시 과일
DEMO_LABELS = {0: "Strawberry", 1: "Orange", 2: "Banana"}


def draw_counts(display, counts):
    """데모 카운트를 OLED 한 페이지에 그린다."""
    with canvas(display.device) as draw:
        y = 2
        for idx in (0, 1, 2):
            draw.text((4, y), f"{DEMO_LABELS[idx]}: {counts[idx]}", fill="white")
            y += 20


def main():
    hw = Hardware()
    display = Display()
    counts = {0: 0, 1: 0, 2: 0}

    # 시작 상태: 정지(빨강) + OLED 0
    hw.set_status("stop")
    draw_counts(display, counts)

    # ----- 동작 정의 -----
    def rail_run():
        hw.set_status("run")          # 작동중
        hw.conveyor_on()

    def rail_stop():
        hw.conveyor_off()
        hw.set_status("inspect")      # 검사중

    def rail_stop_final():
        hw.conveyor_off()
        hw.set_status("stop")         # 중단(빨강)

    def sort_to(idx):
        def _do():
            hw.set_status("inspect")  # 분류중(검사중 색 유지)
            hw.move_rail_to(idx)      # 분류 레일을 해당 바구니로
            counts[idx] += 1          # OLED 카운트 +1
            draw_counts(display, counts)
        return _do

    # ----- 시퀀스 (label, 동작) -----
    steps = [
        ("1. 레일 가동",             rail_run),
        ("2. 레일 중단 (검사중)",     rail_stop),
        ("3. 분류레일 0번 → Strawberry", sort_to(0)),
        ("4. 서보 기울임",           hw.tilt_forward),
        ("5. 서보 되돌림",           hw.tilt_level),
        ("6. 레일 가동",             rail_run),
        ("7. 레일 중단",             rail_stop),
        ("8. 분류레일 1번 → Orange", sort_to(1)),
        ("9. 서보 기울임",           hw.tilt_forward),
        ("10. 서보 되돌림",          hw.tilt_level),
        ("11. 레일 가동",            rail_run),
        ("12. 레일 중단",            rail_stop),
        ("13. 분류레일 2번 → Banana", sort_to(2)),
        ("14. 서보 기울임",          hw.tilt_forward),
        ("15. 서보 되돌림",          hw.tilt_level),
        ("16. 레일 가동",            rail_run),
        ("17. 레일 중단",            rail_stop_final),
    ]

    print("=" * 46)
    print("  데모 제어 — 엔터: 다음 동작 실행 / 'q'+엔터: 종료")
    print("=" * 46)
    try:
        for n, (label, fn) in enumerate(steps, 1):
            cmd = input(f"[{n:2d}/{len(steps)}] ▶ {label}   (엔터) ")
            if cmd.strip().lower() == "q":
                break
            fn()
            print(f"      ✓ {label}")
        else:
            input("\n데모 완료 — 엔터로 정리·종료 ")
    except (KeyboardInterrupt, EOFError):
        print("\n중단됨.")
    finally:
        hw.cleanup()
        display.close()
        print("정리 완료.")


if __name__ == "__main__":
    main()
