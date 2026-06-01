"""상태머신 메인 루프.

상태 전이:
  IDLE
    └─(토글 ON)──→ RUNNING
  RUNNING (컨베이어 가동)
    ├─(검사대 IR 감지)──→ INSPECTING
    └─(토글 OFF)────────→ IDLE
  INSPECTING (컨베이어 정지, N프레임 YOLO 추론)
    ├─(클래스 확정)─────→ SORTING
    └─(불확실)──────────→ RUNNING  (블럭 통과시킨 후)
  SORTING (LED ON + 서보 기울임 + 컨베이어 재가동)
    └─(도착 IR 감지 or 타임아웃)──→ RUNNING
  토글 OFF 시 어느 상태에서든 IDLE로 복귀

실행:  python -m src.main
"""
import signal
import time

from src.config import (
    PATH_MAP, CLASS_NAMES,
    TILT_HOLD_TIME, DEBOUNCE_TIME, DROP_TIMEOUT,
)
from src.hardware import Hardware
from src.vision import Vision


class FruitSorter:
    def __init__(self):
        self.hw = Hardware()
        self.vision = Vision()
        self.alive = True
        signal.signal(signal.SIGINT, self._on_sigint)
        signal.signal(signal.SIGTERM, self._on_sigint)

    def _on_sigint(self, *_):
        print("\n[Main] Stop signal received.")
        self.alive = False

    # ============================================================
    # 상태 핸들러
    # ============================================================
    def _idle(self):
        """토글 OFF 상태에서 대기."""
        self.hw.reset()
        print("[Main] IDLE — toggle the switch ON to start.")
        while self.alive and not self.hw.is_running:
            time.sleep(0.1)

    def _running(self) -> bool:
        """컨베이어 가동 → 검사대 IR 트리거 대기.
        Return: True=감지됨, False=토글 OFF로 중단."""
        print("[Main] RUNNING — conveyor on.")
        self.hw.conveyor_on()
        while self.alive and self.hw.is_running:
            if self.hw.inspection_triggered():
                self.hw.conveyor_off()
                time.sleep(DEBOUNCE_TIME)   # 정지 후 흔들림 안정화
                return True
            time.sleep(0.02)
        # 토글 OFF로 중단된 경우
        self.hw.conveyor_off()
        return False

    def _inspecting(self):
        """N프레임 다수결 추론. 확정 클래스 반환 또는 None."""
        print("[Main] INSPECTING — running YOLO.")
        return self.vision.classify_stable()

    def _sorting(self, cls_id: int):
        """LED ON → 서보 기울임 → 컨베이어 재가동 → 도착 IR 대기."""
        name = CLASS_NAMES[cls_id]
        direction = PATH_MAP[cls_id]
        print(f"[Main] SORTING — {name} → {direction}")

        # 1) LED 점등, 서보 기울임
        self.hw.led_on(cls_id)
        self.hw.set_path(direction)
        time.sleep(0.3)   # 서보 회전 안정화

        # 2) 컨베이어 재가동 (블럭을 분기 플랩 너머로 밀어냄)
        self.hw.conveyor_on()

        # 3) 도착 IR 감지 대기
        t0 = time.time()
        while self.alive and self.hw.is_running:
            if self.hw.rail_triggered(cls_id):
                print(f"[Main] Drop confirmed at {name} rail.")
                break
            if time.time() - t0 > DROP_TIMEOUT:
                print(f"[Main] WARN: drop timeout ({DROP_TIMEOUT}s) for {name}.")
                break
            time.sleep(0.02)

        # 4) 안정화 후 복귀
        time.sleep(TILT_HOLD_TIME)
        self.hw.conveyor_off()
        self.hw.set_path("neutral")
        self.hw.led_off(cls_id)

    def _skip(self):
        """분류 실패 시 — 블럭을 통과시키고 다음 사이클로."""
        print("[Main] SKIP — no confident class. Passing through.")
        self.hw.conveyor_on()
        time.sleep(1.0)
        self.hw.conveyor_off()

    # ============================================================
    # 메인 루프
    # ============================================================
    def run(self):
        try:
            while self.alive:
                # 토글 OFF면 IDLE로
                if not self.hw.is_running:
                    self._idle()
                    continue

                # 컨베이어 가동 → 검사대 도달 대기
                inspected = self._running()
                if not inspected:
                    continue   # 토글 OFF로 중단됨

                # YOLO 추론
                cls_id = self._inspecting()
                if cls_id is None:
                    self._skip()
                    continue

                # 분기 + 낙하 확인
                self._sorting(cls_id)

        finally:
            print("[Main] Cleaning up.")
            self.hw.cleanup()
            self.vision.close()


if __name__ == "__main__":
    FruitSorter().run()
