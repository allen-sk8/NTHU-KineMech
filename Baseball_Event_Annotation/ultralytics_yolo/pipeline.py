from pathlib import Path
import argparse, csv
import cv2
import torch
import numpy as np
import logging
logging.basicConfig(level=logging.INFO) 

from ultralytics import YOLO
from ultralytics_yolo.video_utils import extract_frames
from ultralytics_yolo.phase import (analyze_catch, analyze_throw, find_lead_foot_landing, find_lead_step_after_catch,find_pivot_foot_between_catch_and_lead)
from vitpose.vitpose.vitpose import ViTPose
from vitpose.image_preprocess import preprocess_for_vitpose
from types import SimpleNamespace

def pick_main_person(boxes):
    """從多個 person box 中挑最大面積者。boxes: [(x1,y1,x2,y2,conf), ...]"""
    if not boxes:
        return None
    areas = [(x2 - x1) * (y2 - y1) for (x1, y1, x2, y2, _) in boxes]
    idx = int(np.argmax(areas))
    return boxes[idx]

def extract_person(results):
    """從 YOLO 結果解析出 person 的偵測框。"""
    persons = []
    for b in results.boxes:
        cls_id = int(b.cls[0])
        confv = float(b.conf[0])
        x1, y1, x2, y2 = map(int, b.xyxy[0].tolist())

        if cls_id == 0:  # person
            persons.append((x1, y1, x2, y2, confv))

    return persons

def compress_foot_seq(foot_seq, max_gap=2):
    """
    foot_seq: List[(side, frame_idx, kind)] 已依時間排序
    max_gap: 多少 frame 以內視為同一個「落地事件」
    回傳: 壓縮後的 foot_seq
    """
    if not foot_seq:
        return []

    compressed = []
    cur_side, cur_frame, cur_kind = foot_seq[0]

    for side, frame, kind in foot_seq[1:]:
        # 同一隻腳，且 frame 差距很小 → 視為同一事件，取最早的那幀
        if side == cur_side and (frame - cur_frame) <= max_gap:
            continue
        else:
            compressed.append((cur_side, cur_frame, cur_kind))
            cur_side, cur_frame, cur_kind = side, frame, kind

    compressed.append((cur_side, cur_frame, cur_kind))
    return compressed

def compute_segment_ratios_from_events(events_for_csv: list[tuple[int, str]])-> list[str]:
    """
    給一串已經決定要寫進 CSV 的 events_for_csv = [(frame_idx, kind), ...]
    回傳對應的 segment_ratios（字串 list），長度相同。

    定義：
      - 如果 events <= 1，全部留空 ""
      - 否則：
          total_span = 最後一個事件 frame - 第一個事件 frame
          每一段 = (這個 event 的 frame - 前一個 event 的 frame) / total_span
          再把這個比例寫在「後面的那個」 event 上
          第一個 event 沒有前一個 → 留空 ""
    """
    n = len(events_for_csv)
    if n <= 1:
        return ["" for _ in events_for_csv]

    total_span = events_for_csv[-1][0] - events_for_csv[0][0]
    if total_span <= 0:
        return ["" for _ in events_for_csv]

    segment_ratios: list[str] = []

    for i, (idx_e, kind) in enumerate(events_for_csv):
        if i == 0:
            # 第一個 event 沒有前一個 → 留空
            segment_ratios.append("")
            continue

        prev_idx, _ = events_for_csv[i - 1]
        seg = idx_e - prev_idx

        if seg <= 0:
            segment_ratios.append("")
        else:
            ratio = seg / total_span
            segment_ratios.append(f"{ratio:.6f}")

    return segment_ratios

def write_event_summary(out_root: Path, video_id: str, pattern: str, events: list[tuple[int, str]], frame_ids: list[int], segment_ratios: list[str] | None = None) -> None:
    """
    把本支影片的事件寫進 data/outputs/all_events.csv

    欄位順序：
    [video_id, pattern, event_name, 腳步踩踏方式, 腳步中文, 區間中文, segment_ratio, frame_idx]
    """
    summary_path = out_root / "all_events.csv"
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    event_name_zh_map = {
        "CATCH":     "接球",
        "THROW":     "球出手",
        "PIVOT_CL":  "軸心腳著地",
        "PIVOT":     "軸心腳再度著地",
        "LEAD":      "前導腳著地",
        "LEAD_STEP": "前導腳著地",
    }

    pattern_zh_map = {
        "TWO_STEP":   "兩步組",
        "THREE_STEP": "三步組",
        "FOUR_STEP":  "四步組",
        "UNKNOWN":    "未知",
    }

    header = ["video_id","pattern","event_name","腳步踩踏方式", "腳步", "區間", "segment_ratio","frame_idx",]

    old_rows: list[list[str]] = []

    if summary_path.exists():
        with summary_path.open("r", newline="", encoding="utf-8-sig") as f:
            r = csv.reader(f)
            try:
                first = next(r)
                if first and first[0] != "video_id":
                    old_rows.append(first)
            except StopIteration:
                pass

            for row in r:
                if not row:
                    continue
                if row[0] != video_id:
                    old_rows.append(row)

    new_rows: list[list[str]] = []

    if not events:
        with summary_path.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(old_rows)
        return

    n = len(events)
    segment_zh_list = ["" for _ in range(n)]

    if pattern in ("TWO_STEP", "THREE_STEP", "FOUR_STEP"):
        if pattern == "TWO_STEP":
            labels = ["腳離地期", "跨步期", "加速期"] 
        elif pattern == "THREE_STEP":
            labels = ["腳離地前期", "腳離地期", "跨步期", "加速期"] 
        elif pattern == "FOUR_STEP":
            labels = ["腳離地期", "墊步期", "跨步期", "加速期"]

        for i, label in enumerate(labels, start=1):
            if i < n:
                segment_zh_list[i] = label

    step_pattern_zh_full = pattern_zh_map.get(pattern, "未知")

    for i, (frame_idx, kind) in enumerate(events):
        if frame_idx is not None and 0 <= frame_idx < len(frame_ids):
            fid = frame_ids[frame_idx]
        else:
            fid = ""

        seg_ratio = ""
        if segment_ratios is not None and i < len(segment_ratios):
            seg_ratio = segment_ratios[i]
        
        step_pattern_zh = step_pattern_zh_full if i == 0 else ""
        event_name_zh = event_name_zh_map.get(kind, "")
        segment_zh = segment_zh_list[i] if i < len(segment_zh_list) else ""

        new_rows.append([video_id,pattern,kind,step_pattern_zh,event_name_zh,segment_zh,seg_ratio, str(frame_idx),])

    with summary_path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(old_rows)
        w.writerows(new_rows)


def run_phase_and_update_csv(video_id: str, frame_ids: list[int], kps_arr: np.ndarray, out_root: Path, fps: float,) -> None:
    """
    只用關鍵點 (kps_arr) + frame_ids 做 phase 分析，
    並直接更新 data/outputs/all_events.csv 裡這支影片的事件列。
    """

    # --- CATCH ---
    catch_res = analyze_catch(frame_ids, kps_arr, fps=fps, conf_min=0.25)

    # --- THROW（象限版） ---
    start_idx = catch_res.catch_idx if catch_res.catch_idx is not None else 0
    throw_res = analyze_throw(frame_ids, kps_arr, fps=fps, start_idx=start_idx, conf_min=0.25)

    # --- LEAD FOOT（THROW 前最近一次落地） ---
    lead_res = None
    lead_idx = None
    if throw_res.throw_idx is not None:
        lead_res = find_lead_foot_landing(kps_arr, throw_res.throw_idx, ankle_idx=15, conf_min=0.25)
        if lead_res is not None and lead_res.frame is not None and lead_res.frame >= 0:
            lead_idx = lead_res.frame
    # --- PIVOT FOOT（LEAD 附近、THROW 前） ---
    pivot_res = None
    pivot_idx = None
    if throw_res.throw_idx is not None and lead_idx is not None:
        from ultralytics_yolo.phase import find_pivot_foot_landing

        pivot_res = find_pivot_foot_landing(kps_arr,lead_idx=lead_idx,throw_idx=throw_res.throw_idx,ankle_idx=16,conf_min=0.25,)
        if pivot_res is not None and pivot_res.frame is not None and pivot_res.frame >= 0:
            pivot_idx = pivot_res.frame

    # --- LEAD STEP（CATCH 之後、PIVOT 之前的墊步） ---
    lead_step_res = None
    lead_step_idx = None
    if catch_res.catch_idx is not None and pivot_idx is not None:
        end_idx = pivot_idx
        lead_step_res = find_lead_step_after_catch(kps_arr, catch_idx=catch_res.catch_idx, end_idx=end_idx, ankle_idx=15, conf_min=0.25,)
        if (lead_step_res is not None and lead_step_res.frame is not None and lead_step_res.frame >= 0):
            lead_step_idx = lead_step_res.frame

    # --- PIVOT C-L（CATCH~LEAD_STEP 之間的軸心腳） ---
    pivot_cl_res = None
    pivot_cl_idx = None
    if catch_res.catch_idx is not None and lead_step_idx is not None:
        pivot_cl_res = find_pivot_foot_between_catch_and_lead(kps_arr,catch_idx=catch_res.catch_idx, lead_step_idx=lead_step_idx, ankle_idx=16, conf_min=0.25)
        if (pivot_cl_res is not None and pivot_cl_res.frame is not None and pivot_cl_res.frame >= 0):
            pivot_cl_idx = pivot_cl_res.frame

    events: list[tuple[int, str]] = []

    def add_event(kind: str, idx: int | None):
        if idx is not None and idx >= 0:
            events.append((idx, kind))

    catch_idx = catch_res.catch_idx
    throw_idx = throw_res.throw_idx

    add_event("CATCH", catch_idx)
    add_event("PIVOT_CL", pivot_cl_idx)
    add_event("LEAD_STEP", lead_step_idx)
    add_event("PIVOT", pivot_idx)
    add_event("LEAD", lead_idx)
    add_event("THROW", throw_idx)

    if catch_idx is not None and throw_idx is not None:
        events = [(i, k) for (i, k) in events if catch_idx <= i <= throw_idx]

    events.sort(key=lambda x: x[0])

    foot_seq: list[tuple[str, int, str]] = []
    for idx_e, kind in events:
        if kind in ("PIVOT_CL", "PIVOT"):
            foot_seq.append(("P", idx_e, kind))
        elif kind in ("LEAD_STEP", "LEAD"):
            foot_seq.append(("L", idx_e, kind))

    foot_seq = compress_foot_seq(foot_seq, max_gap=2)
    
    def classify_step_pattern(foot_seq):
        """
        foot_seq: List[("P" or "L", idx, kind)]

        直接用 P/L 序列 + 長度來對應你定義的三種步組：
        - ["P","L"]            → TWO_STEP
        - ["L","P","L"]        → THREE_STEP
        - ["P","L","P","L"]    → FOUR_STEP
        其他情況再 fallback 到舊邏輯（防止偵測有掉點時還有個 best-effort）。
        """

        if not foot_seq:
            return "UNKNOWN"

        seq = [side for (side, _, _) in foot_seq] 
        
        if seq == ["P", "L"]:
            return "TWO_STEP"
        if seq == ["L", "P", "L"]:
            return "THREE_STEP"
        if seq == ["P", "L", "P", "L"]:
            return "FOUR_STEP"

        seq_str = "".join(seq)
        pairs = []
        i = 0
        while i + 1 < len(seq):
            s1 = seq[i]
            s2 = seq[i + 1]
            if s1 == "P" and s2 == "L":
                pairs.append((i, i + 1))
            i += 1

        if not pairs:
            return "UNKNOWN"

        if seq_str.endswith("PL"):
            cnt = 0
            i = len(seq_str) - 2
            while i >= 0 and seq_str[i:i+2] == "PL":
                cnt += 1
                i -= 2
            if cnt == 1:
                return "TWO_STEP"
            elif cnt == 2:
                return "THREE_STEP"
            elif cnt >= 3:
                return "FOUR_STEP"

        return "UNKNOWN"

    def select_events_for_csv(pattern, events, foot_seq):
        """
        根據步法 pattern，把要寫進 all_events.csv 的事件挑出來。

        events: List[(frame_idx, kind)]
        foot_seq: List[( "P"/"L", frame_idx, kind )]
        """
        events_for_csv = []

        if pattern == "TWO_STEP":
            keep_kinds = {"CATCH", "PIVOT", "LEAD", "THROW"}
            for idx_e, kind in events:
                if kind in keep_kinds:
                    events_for_csv.append((idx_e, kind))
            return events_for_csv

        if pattern == "THREE_STEP":
            first_pivot_frame = None
            # 找 foot_seq 裡第一個 P 的 frame
            for side, frame, kind in foot_seq:
                if side == "P":
                    first_pivot_frame = frame
                    break

            for idx_e, kind in events:
                # 第一個 P (frame 對到 first_pivot_frame) 就跳過
                if first_pivot_frame is not None and idx_e == first_pivot_frame and kind in ("PIVOT_CL", "PIVOT"):
                    continue  # 這個是 X，不寫 CSV
                events_for_csv.append((idx_e, kind))
            return events_for_csv

        if pattern == "FOUR_STEP":
            events_for_csv = []

            # 先找「第一次前導腳著地」的 frame（foot_seq 中第一個 side == "L"）
            first_lead_frame = None
            for side, frame, kind in foot_seq:
                if side == "L":
                    first_lead_frame = frame
                    break

            keep_frames = set()

            if foot_seq:
                # 第一個腳步（不管是 P 或 L，都先視為候選）
                first_frame = foot_seq[0][1]
                keep_frames.add(first_frame)

                # 最後兩個腳步
                tail = foot_seq[-2:] if len(foot_seq) >= 2 else foot_seq
                for _, frame, _ in tail:
                    keep_frames.add(frame)

            for idx_e, kind in events:
                # CATCH / THROW 一律寫入
                if kind in ("CATCH", "THROW"):
                    events_for_csv.append((idx_e, kind))
                    continue

                # 四步組：第一次前導腳著地「一定不要」寫入 CSV
                if (first_lead_frame is not None and idx_e == first_lead_frame and kind in ("LEAD_STEP", "LEAD")):
                    continue

                # 其他腳步只有在 keep_frames 裡才寫入
                if idx_e in keep_frames:
                    events_for_csv.append((idx_e, kind))

            return events_for_csv


        # 其他 pattern（UNKNOWN 等）→ 全部照舊寫入
        return list(events)

    pattern = classify_step_pattern(foot_seq)

    events_for_csv = select_events_for_csv(pattern, events, foot_seq)
    # --------------------------------------------------------
    # 用「前一個 event 到這個 event」佔總區間 (最後一個 - 第一個) 的比率
    # 前減後 → 寫在後面的那一個
    # --------------------------------------------------------
    segment_ratios = compute_segment_ratios_from_events(events_for_csv)

    write_event_summary(out_root=out_root, video_id=video_id, pattern=pattern, events=events_for_csv,frame_ids=frame_ids,segment_ratios=segment_ratios,)

def run_single(args):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    base_dir = Path(__file__).resolve().parents[1]
    video_path = (base_dir / args.video).resolve() if not Path(args.video).is_absolute() else Path(args.video)
    if not video_path.exists():
        raise FileNotFoundError(f"[pipeline] 找不到影片：{video_path}")

    video_stem = video_path.stem 
    # 只取檔名裡的數字，如果沒有數字就用整個檔名
    video_id = "".join(ch for ch in video_stem if ch.isdigit()) or video_stem

    out_root = base_dir / "data" / "outputs"
    result_dir = out_root / f"{video_id}_result"
    result_dir.mkdir(parents=True, exist_ok=True)

    # debug 用的子資料夾（存 crop、骨架圖等）
    debug_dir = result_dir / "debug"
    debug_dir.mkdir(parents=True, exist_ok=True)

    # ---- YOLO ----
    yolo = YOLO(args.det_model)
    if device == "cuda":
        yolo.to("cuda")

    # ---- ViTPose ----
    weights = base_dir / "vitpose" / "vitpose" / "vitpose+_base.pth"
    mode = {
        "coco17": ViTPose.OutputMode.coco17,
        "coco133": ViTPose.OutputMode.coco133,
        "hybrid": ViTPose.OutputMode.hybrid,
    }[args.pose_mode]
    vit = ViTPose(weights_path=str(weights), output_mode=mode).to(device).eval()

    # 影片資訊
    cap0 = cv2.VideoCapture(str(video_path))
    src_fps = cap0.get(cv2.CAP_PROP_FPS) or 30
    cap0.release()

    eff_rate = src_fps

    writer_fps = eff_rate

    # 取樣幀
    frames = extract_frames(str(video_path), frame_rate=eff_rate)

    # for phase
    kps_series = []  # 每幀的姿態關鍵點資料, List[(17,3)]
    frame_ids = []

    # YOLO 抓到的主守備者框 (x1, y1, x2, y2, conf)
    main_boxes = []

    for idx, (fid, frame) in enumerate(frames):
        main_box = None
        # --- 單次推論 ---
        res = yolo.predict(source=frame,imgsz=args.imgsz,conf=0.05,iou=args.det_iou,agnostic_nms=True,verbose=False,)[0]

        # --- 解析人 ---
        persons = extract_person(res)
        person_boxes = persons
        main_box = pick_main_person(person_boxes)

        # keep keypoint info.
        kps_now = np.full((17, 3), np.nan, dtype=float)

        if main_box:
            x1, y1, x2, y2, conf = main_box
            crop = frame[y1:y2, x1:x2]
            # 把從原始影格裁下來的人物區域 (crop) 做前處理，轉換成 ViTPose 模型可以輸入的 Tensor 格式
            inp = preprocess_for_vitpose(crop, device=device)
            with torch.no_grad():
                heat = vit(inp)
                kps = ViTPose.heatmaps_to_keypoints(heat, to_image_shape=True)[0].cpu().numpy()

                if idx < 2:
                    crop_h, crop_w = crop.shape[:2]

            # 映回原圖
            crop_h, crop_w = crop.shape[:2]
            scale_x = crop_w / 192.0
            scale_y = crop_h / 256.0

            # 乘上縮放比例 + 平移(左上角為(0,0))
            kps[:, 0] = kps[:, 0] * scale_x + x1
            kps[:, 1] = kps[:, 1] * scale_y + y1
            kps_now = kps
        # 把這一幀的 main_box 存起來（就算是 None 也存）
        main_boxes.append(main_box)
        kps_series.append(kps_now)
        frame_ids.append(fid)

    # --- Phase 分析 ---
    kps_arr = np.stack(kps_series, axis=0)
    # --- 存 kps.npy / frame_ids.npy / fps.npy ---
    kps_path = result_dir / f"{video_id}_kps.npy"
    frame_ids_path = result_dir / f"{video_id}_frame_ids.npy"
    fps_path = result_dir / f"{video_id}_fps.npy"

    np.save(kps_path, kps_arr)
    np.save(frame_ids_path, np.array(frame_ids, dtype=int))
    np.save(fps_path, np.array([writer_fps], dtype=float))

    # --- Phase 分析（不再自己做，直接使用共用函式） ---
    run_phase_and_update_csv(video_id=video_id, frame_ids=frame_ids, kps_arr=kps_arr, out_root=out_root, fps=writer_fps,)
    
    main_boxes_arr = np.array(main_boxes, dtype=object)
    boxes_path = result_dir / f"{video_id}_main_boxes.npy"
    np.save(boxes_path, main_boxes_arr, allow_pickle=True)
    print("[pipeline] 完成。")

def main(args):
    """
    如果加上 --run_all，就掃 raw_dir 底下所有影片逐一跑。
    否則就只跑單支 --video。
    """
    base_dir = Path(__file__).resolve().parents[1]

    if getattr(args, "run_all", False):
        # ---- batch 模式：處理一整個資料夾 ----
        raw_dir = (base_dir / args.raw_dir).resolve()
        if not raw_dir.exists():
            return

        out_root = base_dir / "data" / "outputs"
        summary_path = out_root / "all_events.csv"
        if summary_path.exists():
            summary_path.unlink()
            
        exts = set(args.ext)
        videos = sorted(p for p in raw_dir.iterdir() if p.is_file() and p.suffix in exts)

        if not videos:
            return

        for v in videos:
            print(f"  - {v.name}")
        print()

        for v in videos:
            rel_video_path = v.relative_to(base_dir)

            sub_args_dict = vars(args).copy()
            sub_args_dict["video"] = str(rel_video_path)
            sub_args_dict["run_all"] = False
            sub_args = SimpleNamespace(**sub_args_dict)

            try:
                run_single(sub_args)
            except Exception as e:
                continue
    else:
        # ---- 單支影片模式 ----
        if not getattr(args, "video", None):
            raise SystemExit("[pipeline] 請提供 --video，或使用 --run_all 搭配 --raw_dir")
        run_single(args)
        
if __name__ == "__main__":
    ap = argparse.ArgumentParser()

    ap.add_argument("--video", help="單一影片路徑：例如 data/raw/00227.MTS（也支援 .MT4/.mp4）")
    ap.add_argument("--run_all", action="store_true", help="若加上此參數，會對 raw_dir 底下所有影片執行 pipeline")
    ap.add_argument("--raw_dir", default="data/raw", help="搭配 --run_all 使用的影片資料夾（預設：data/raw）")
    ap.add_argument("--ext", nargs="+", default=[".MTS", ".MT4", ".mp4", ".MP4"], help="搭配 --run_all 要處理的影片副檔名列表",)
    ap.add_argument("--det_model", default="yolo11n.pt", help="Ultralytics YOLO 權重")
    ap.add_argument("--pose_mode", choices=["coco17", "coco133", "hybrid"], default="coco17", help="ViTPose 模式")
    ap.add_argument("--imgsz", type=int, default=1280)
    ap.add_argument("--det_conf", type=float, default=0.20)
    ap.add_argument("--det_iou", type=float, default=0.50)

    args = ap.parse_args()

    if not args.run_all and not args.video:
        ap.error("請提供 --video 或加上 --run_all 搭配 --raw_dir")

    main(args)