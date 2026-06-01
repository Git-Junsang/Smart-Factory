"""Picamera2 + YOLO 추론 계층.

apple(47), banana(46), orange(49) 세 클래스 외에는 반응하지 않습니다.
필터링은 두 단계로 적용:
  1) model.predict(classes=[46, 47, 49]) — 추론 단계에서 차단
  2) detect_once() 내부에서 한 번 더 검증 — 안전망
"""
import time
from collections import Counter
from typing import Optional

import numpy as np
from picamera2 import Picamera2
from ultralytics import YOLO

from src.config import (
    MODEL_PATH, IMG_SIZE, CONF_TH, N_FRAMES, VOTE_MIN,
    TARGET_CLASSES, CLASS_NAMES,
)


class Vision:
    def __init__(self):
        # ---------- Picamera2 초기화 ----------
        self.picam2 = Picamera2()
        config = self.picam2.create_preview_configuration(
            main={"size": (640, 480), "format": "RGB888"}
        )
        self.picam2.configure(config)
        self.picam2.start()
        time.sleep(1.0)   # AE/AWB 안정화

        # ---------- YOLO 모델 로딩 ----------
        # NCNN 모델은 task를 자동 추론 못 하므로 명시 필요
        self.model = YOLO(MODEL_PATH, task="detect")
        print(f"[Vision] Model loaded: {MODEL_PATH}")
        print(f"[Vision] Target classes: "
              f"{[CLASS_NAMES[c] for c in TARGET_CLASSES]}")

    def get_frame(self) -> np.ndarray:
        return self.picam2.capture_array()

    def detect_once(self, frame: np.ndarray) -> Optional[int]:
        """
        단일 프레임 추론.
        Return: 대상 클래스 중 최고 신뢰도의 class_id, 또는 None.
        """
        results = self.model.predict(
            frame,
            imgsz=IMG_SIZE,
            conf=CONF_TH,
            classes=TARGET_CLASSES,   # ★ 사과/바나나/오렌지 외 모두 무시
            verbose=False,
        )

        if not results:
            return None

        boxes = results[0].boxes
        if boxes is None or len(boxes) == 0:
            return None

        # 신뢰도 최고 박스 선택
        best_idx = int(boxes.conf.argmax())
        cls_id = int(boxes.cls[best_idx])
        conf   = float(boxes.conf[best_idx])

        # 이중 안전망
        if cls_id not in TARGET_CLASSES or conf < CONF_TH:
            return None
        return cls_id

    def classify_stable(self) -> Optional[int]:
        """N프레임 다수결로 최종 클래스 결정.
        최다 득표가 VOTE_MIN 미만이면 None.
        """
        votes = Counter()
        for _ in range(N_FRAMES):
            cls = self.detect_once(self.get_frame())
            if cls is not None:
                votes[cls] += 1

        if not votes:
            print("[Vision] No target-class detection in N frames.")
            return None

        top_cls, top_count = votes.most_common(1)[0]
        if top_count < VOTE_MIN:
            human = {CLASS_NAMES[k]: v for k, v in votes.items()}
            print(f"[Vision] Inconclusive votes: {human}")
            return None

        print(f"[Vision] → {CLASS_NAMES[top_cls]} "
              f"({top_count}/{N_FRAMES})")
        return top_cls

    def close(self):
        try:
            self.picam2.stop()
            self.picam2.close()
        except Exception:
            pass
