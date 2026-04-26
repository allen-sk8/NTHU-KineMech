# vitpose/visualize.py
import cv2
import numpy as np
from typing import List, Dict, Tuple

# COCO-17 的骨架連線（與你 ViTPose 的 kinematic tree 對齊）
# 索引意義：0:鼻、1:左眼、2:右眼、3:左耳、4:右耳、5:左肩、6:右肩、7:左肘、8:右肘、
# 9:左腕、10:右腕、11:左髖、12:右髖、13:左膝、14:右膝、15:左踝、16:右踝
COCO17_PAIRS: List[Tuple[int, int]] = [
    (5, 7), (7, 9),   # 左臂
    (6, 8), (8, 10),  # 右臂
    (5, 6),           # 肩連線
    (11, 12),         # 髖連線
    (5, 11), (6, 12), # 軀幹
    (11, 13), (13, 15), # 左腿
    (12, 14), (14, 16), # 右腿
]

def _draw_kpt(img, x, y, conf, radius=3, thickness=2):
    if conf < 0.3:  # 低信心就不畫
        return
    cv2.circle(img, (int(x), int(y)), radius, (0, 255, 0), thickness, lineType=cv2.LINE_AA)

def _draw_limb(img, x1, y1, c1, x2, y2, c2, thickness=2):
    if c1 < 0.3 or c2 < 0.3:
        return
    cv2.line(img, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), thickness, lineType=cv2.LINE_AA)

def _map_keypoints_from_crop_to_full(kpts_crop: np.ndarray, box_xyxy: Tuple[float, float, float, float]):
    """
    kpts_crop: (17, 3) in crop-space (W=192, H=256)  # 你的 preprocess 即是 (192,256)
    box_xyxy: (x1, y1, x2, y2) 對應在原圖座標
    回傳：kpts_full (17, 3) -> 映射回原圖座標
    """
    x1, y1, x2, y2 = box_xyxy
    bw = max(x2 - x1, 1e-6)
    bh = max(y2 - y1, 1e-6)
    sx = bw / 192.0
    sy = bh / 256.0

    out = kpts_crop.copy()
    out[:, 0] = x1 + kpts_crop[:, 0] * sx
    out[:, 1] = y1 + kpts_crop[:, 1] * sy
    return out

def draw_skeletons_on_frame(
    frame,
    person_boxes: List[Tuple[float, float, float, float]],
    person_keypoints: List[np.ndarray],
    draw_bbox: bool = False,
):
    """
    將每個人的 17 關節 (x,y,conf) 畫回到 frame。
    - person_boxes: 與 keypoints 對齊的 bbox (x1,y1,x2,y2)
    - person_keypoints: list，每個元素為 (17,3)，座標應為「crop 空間」(192x256)
      若你是直接對整張圖估姿（非 crop），也可直接傳「原圖座標」進來，會原地畫。
    """
    for i, kpts in enumerate(person_keypoints):
        if kpts is None or len(kpts) == 0:
            continue

        # 檢查是否需要從 crop 座標映回原圖
        if person_boxes is not None and len(person_boxes) == len(person_keypoints):
            x1, y1, x2, y2 = person_boxes[i]
            # 偵測若 keypoint 超過 192x256 的合理範圍，視為原圖座標已經映好
            if (kpts[:, 0].max() <= 192.5) and (kpts[:, 1].max() <= 256.5):
                kpts = _map_keypoints_from_crop_to_full(kpts, (x1, y1, x2, y2))

            if draw_bbox:
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 165, 255), 2)

        # 畫關節點
        for j in range(min(17, kpts.shape[0])):
            _draw_kpt(frame, kpts[j, 0], kpts[j, 1], kpts[j, 2])

        # 畫骨架連線
        for (a, b) in COCO17_PAIRS:
            if a < kpts.shape[0] and b < kpts.shape[0]:
                _draw_limb(frame, kpts[a, 0], kpts[a, 1], kpts[a, 2],
                                  kpts[b, 0], kpts[b, 1], kpts[b, 2])
    return frame
