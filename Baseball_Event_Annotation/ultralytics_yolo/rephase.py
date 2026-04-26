from pathlib import Path
import argparse
import numpy as np

from ultralytics_yolo.pipeline import run_phase_and_update_csv

def rephase_single(video_id: str):
    base_dir = Path(__file__).resolve().parents[1]
    out_root = base_dir / "data" / "outputs"
    result_dir = out_root / f"{video_id}_result"

    kps_path = result_dir / f"{video_id}_kps.npy"
    frame_ids_path = result_dir / f"{video_id}_frame_ids.npy"
    fps_path = result_dir / f"{video_id}_fps.npy"

    if not kps_path.exists():
        raise FileNotFoundError(f"[rephase] 找不到 kps 檔案：{kps_path}")

    kps_arr = np.load(kps_path)
    frame_ids = np.load(frame_ids_path).tolist()
    fps_arr = np.load(fps_path)
    fps = float(fps_arr[0]) if fps_arr.ndim > 0 else float(fps_arr)

    print(f"[rephase] video_id={video_id}, frames={len(frame_ids)}, fps={fps}")

    run_phase_and_update_csv(
        video_id=video_id,
        frame_ids=frame_ids,
        kps_arr=kps_arr,
        out_root=out_root,
        fps=fps,
    )

def rephase_all():
    """
    掃 data/outputs 底下所有 *_result 資料夾，
    只要裡面有 {video_id}_kps.npy，就幫它重跑一次 phase。
    """
    base_dir = Path(__file__).resolve().parents[1]
    out_root = base_dir / "data" / "outputs"

    result_dirs = sorted(
        d for d in out_root.iterdir()
        if d.is_dir() and d.name.endswith("_result")
    )

    if not result_dirs:
        print("[rephase] 找不到任何 *_result 資料夾")
        return

    for d in result_dirs:
        # 例：d.name = "00227_result" → video_id = "00227"
        name = d.name
        video_id = name[:-7]  # 去掉 "_result"
        kps_path = d / f"{video_id}_kps.npy"
        frame_ids_path = d / f"{video_id}_frame_ids.npy"
        fps_path = d / f"{video_id}_fps.npy"

        if not kps_path.exists():
            print(f"[rephase] skip {video_id} (no kps.npy)")
            continue

        kps_arr = np.load(kps_path)
        frame_ids = np.load(frame_ids_path).tolist()
        fps_arr = np.load(fps_path)
        fps = float(fps_arr[0]) if fps_arr.ndim > 0 else float(fps_arr)

        print(f"[rephase] video_id={video_id}, frames={len(frame_ids)}, fps={fps}")
        run_phase_and_update_csv(
            video_id=video_id,
            frame_ids=frame_ids,
            kps_arr=kps_arr,
            out_root=out_root,
            fps=fps,
        )

    print("[rephase] 全部影片 phase 重跑完成。")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video_id", help="單一影片的 video_id，例如 00227")
    ap.add_argument("--run_all", action="store_true", help="對所有影片重跑 phase")
    args = ap.parse_args()

    if args.run_all:
        rephase_all()
    elif args.video_id:
        rephase_single(args.video_id)
    else:
        ap.error("請提供 --video_id 或加上 --run_all")

if __name__ == "__main__":
    main()
