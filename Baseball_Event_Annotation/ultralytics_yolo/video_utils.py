import os
import cv2
from pathlib import Path

# ---------- public APIs ----------

def extract_frames(video_path: str, frame_rate=15):
    """
    依指定的 frame_rate 抽幀，回傳 [(frame_idx, frame_bgr), ...]
    支援 .MTS / .MT4 / .mp4 直接讀，不需要轉檔
    """
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"[extract_frames] 找不到影片：{video_path}")

    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 0:
        fps = 30  # 無法讀 fps 時 fallback

    interval = max(int(round(fps / frame_rate)), 1)
    frames = []
    idx = 0
    kept = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        # 每隔 interval 抽一次
        if idx % interval == 0:
            frames.append((idx, frame))
            kept += 1
        idx += 1

    cap.release()
    print(f"[extract_frames] 總幀數={idx}, 保留幀數={kept}, fps≈{fps:.2f}, interval={interval}")
    return frames

# ---------- quick test ----------
if __name__ == "__main__":
    # 這裡直接測 MTS，不轉 mp4
    raw_video = Path("data/raw/00227.MTS")  # 改成你的測試檔案
    try:
        frames = extract_frames(str(raw_video), frame_rate=15)
        print(f"成功抽取 {len(frames)} 幀")
        # 顯示前 3 幀
        for _, f in frames[:3]:
            cv2.imshow("frame", f)
            cv2.waitKey(500)
        cv2.destroyAllWindows()
    except Exception as e:
        print("發生錯誤：", e)
