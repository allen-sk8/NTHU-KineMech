# phase.py
from dataclasses import dataclass
from typing import Optional, Sequence
import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass

@dataclass
class CatchResult:
    catch_frame: Optional[int]     # 原始 frame id（跟 pipeline 的 frame_ids 對應）
    catch_idx: Optional[int]       # 在 kps_arr 裡的 index
    h_smooth: np.ndarray           # (T,) 平滑後的手相對高度，方便 debug
    
@dataclass
class ThrowResult:
    throw_frame: Optional[int]     # 原始 frame id
    throw_idx: Optional[int]       # 在 kps_arr 裡的 index
    h_smooth: np.ndarray           # (T,) 右手相對高度（整段），方便 debug

@dataclass
class LeadFootResult:
    frame: int       # 前導腳落地幀 (int 或 -1)
    ground_y: float  # 推估的地板位置 (debug 用)
    landing_frames: list  # 所有落地事件幀 (debug 用)

@dataclass
class LeadFootResult:
    frame: int       # 前導腳落地幀 (int 或 -1)
    ground_y: float  # 推估的地板位置 (debug 用)
    landing_frames: list  # 所有落地事件幀 (debug 用)

@dataclass
class PivotFootResult:
    frame: int        # 軸心腳落地幀 (int 或 -1)
    ground_y: float   # 推估的地板位置 (debug 用)
    landing_frames: list  # 所有落地事件幀 (debug 用)
        
def analyze_catch(frames: Sequence[int], kps_arr: np.ndarray, fps: float, conf_min: float = 0.3) -> CatchResult:
    """
    只用 ViTPose 骨架，找出「左手到最低點後往上抬」的那一幀。
    假設左手是手套手（COCO17: 7=left elbow, 9=left wrist, 11/12=hips）。
    """
    frames = list(frames)
    T = len(frames)
    if T == 0:
        return CatchResult(catch_frame=None, catch_idx=None, h_smooth=np.array([]))

    hand_y = np.full(T, np.nan, dtype=float)
    hip_y  = np.full(T, np.nan, dtype=float)

    for t in range(T):
        kps = kps_arr[t]  #[x,y,conf]

        hy = np.nan
        lw = kps[9]  
        le = kps[7]  
        if lw[2] >= conf_min:
            hy = lw[1]
        elif le[2] >= conf_min:
            hy = le[1]
        hand_y[t] = hy

        hips = []
        for j in (11, 12):
            if kps[j, 2] >= conf_min:
                hips.append(kps[j, 1])
        hip_y[t] = float(np.mean(hips)) if hips else np.nan

    h_rel = hand_y - hip_y

    h_smooth = np.full_like(h_rel, np.nan, dtype=float)
    win = 2  
    for t in range(T):
        lo = max(0, t - win)
        hi = min(T, t + win + 1)
        vals = h_rel[lo:hi]
        vals = vals[np.isfinite(vals)]
        if len(vals) > 0:
            h_smooth[t] = float(np.mean(vals))

    #elbow dist. 
    d_hands = np.full(T, np.nan, dtype=float)
    for t in range(T):
        kps = kps_arr[t]
        le = kps[7]  
        re = kps[8]  
        if le[2] >= conf_min and re[2] >= conf_min:
            lx, ly = le[0], le[1]
            rx, ry = re[0], re[1]
            d_hands[t] = float(np.hypot(lx - rx, ly - ry))

    # elbow dist. after smoothing
    d_smooth = np.full_like(d_hands, np.nan, dtype=float)
    for t in range(T):
        lo = max(0, t - win)
        hi = min(T, t + win + 1)
        vals = d_hands[lo:hi]
        vals = vals[np.isfinite(vals)]
        if len(vals) > 0:
            d_smooth[t] = float(np.mean(vals))

    if not np.isfinite(h_smooth).any():
        return CatchResult(catch_frame=None, catch_idx=None, h_smooth=h_smooth)

    candidates = []
    max_h = np.nanmax(h_smooth)
    thr_h = max_h * 0.7

    for t in range(1, T - 1):
        if not np.isfinite(h_smooth[t]):
            continue
        if h_smooth[t] < thr_h:
            continue
        if not (np.isfinite(h_smooth[t - 1]) and np.isfinite(h_smooth[t + 1])):
            continue
        if h_smooth[t] >= h_smooth[t - 1] and h_smooth[t] >= h_smooth[t + 1]:
            candidates.append(t)

    if not candidates:
        return CatchResult(catch_frame=None, catch_idx=None, h_smooth=h_smooth)

    best_t = None
    best_val = -1e9
    for t in candidates:
        if t < 5 or t > T - 5:
            continue
        val = h_smooth[t]
        if val > best_val:
            best_val = val
            best_t = t

    if best_t is None:
        return CatchResult(catch_frame=None, catch_idx=None, h_smooth=h_smooth)

    search_lo = best_t
    search_hi = min(T, best_t + int(fps * 1.0))

    t_catch = None
    seg = d_smooth[search_lo:search_hi]
    if np.isfinite(seg).any():
        rel = int(np.nanargmin(seg))
        t_catch = search_lo + rel
    else:
        t_catch = best_t

    catch_frame = frames[t_catch]

    return CatchResult(catch_frame=catch_frame, catch_idx=t_catch, h_smooth=h_smooth)

def analyze_throw(frames: Sequence[int], kps_arr: np.ndarray,fps: float, start_idx: int = 0, conf_min: float = 0.3) -> ThrowResult:
    """
    用 ViTPose 骨架找「右手丟球瞬間」。

    新版規則（只看 right wrist, COCO17: 10）：
      - 先把右手手腕座標 (x, y) 做時間平滑
      - 再計算「每一幀相對上一幀」的速度大小 v[t] = sqrt(Δx^2 + Δy^2)
      - 從 start_idx 之後，在所有有效的 v[t] 中找最大值所在的幀 t_throw
      - 第一個最大速度峰值視為出手幀
      - 若整段都沒有有效速度，就視為沒有出手（回傳 throw_idx=None）

    h_smooth 仍然回傳「右手 y 座標（像素）的平滑結果」，方便 debug。
    """
    frames = list(frames)
    T = len(frames)
    if T == 0:
        return ThrowResult(throw_frame=None, throw_idx=None, h_smooth=np.array([]))

    # 保險：start_idx 夾在合法範圍
    start_idx = max(0, min(start_idx, T - 1))

    J = 10  # right wrist

    # ----------------------------------------------------
    # 1) 先跟舊版一樣，記錄 hand_y & h_smooth（方便你畫圖）
    # ----------------------------------------------------
    hand_y = np.full(T, np.nan, dtype=float)
    for t in range(start_idx, T):
        kps = kps_arr[t]  # (17,3)
        rw = kps[J]
        if rw[2] >= conf_min:
            hand_y[t] = rw[1]
        else:
            hand_y[t] = np.nan

    h_smooth = np.full_like(hand_y, np.nan, dtype=float)
    win = 2
    for t in range(start_idx, T):
        lo = max(start_idx, t - win)
        hi = min(T, t + win + 1)
        vals = hand_y[lo:hi]
        vals = vals[np.isfinite(vals)]
        if len(vals) > 0:
            h_smooth[t] = float(np.mean(vals))

    # ----------------------------------------------------
    # 2) 取出右手手腕 (x, y) 並做時間平滑
    # ----------------------------------------------------
    x_raw = np.full(T, np.nan, dtype=float)
    y_raw = np.full(T, np.nan, dtype=float)

    for t in range(start_idx, T):
        kps = kps_arr[t]
        rw = kps[J]
        if rw[2] >= conf_min:
            x_raw[t] = rw[0]
            y_raw[t] = rw[1]

    x_smooth = np.full_like(x_raw, np.nan, dtype=float)
    y_smooth = np.full_like(y_raw, np.nan, dtype=float)

    for t in range(start_idx, T):
        lo = max(start_idx, t - win)
        hi = min(T, t + win + 1)
        xs = x_raw[lo:hi]
        xs = xs[np.isfinite(xs)]
        ys = y_raw[lo:hi]
        ys = ys[np.isfinite(ys)]
        if len(xs) > 0:
            x_smooth[t] = float(np.mean(xs))
        if len(ys) > 0:
            y_smooth[t] = float(np.mean(ys))

    # ----------------------------------------------------
    # 3) 計算速度 v[t] = 每一幀相對上一幀位移的大小
    # ----------------------------------------------------
    v = np.full(T, np.nan, dtype=float)
    for t in range(start_idx + 1, T):
        if (np.isfinite(x_smooth[t]) and np.isfinite(x_smooth[t - 1]) and np.isfinite(y_smooth[t]) and np.isfinite(y_smooth[t - 1])):
            dx = x_smooth[t] - x_smooth[t - 1]
            dy = y_smooth[t] - y_smooth[t - 1]
            v[t] = float(np.hypot(dx, dy))

    # 如果整段都沒有有效速度，就直接視為沒有 THROW
    if not np.isfinite(v[start_idx + 1:]).any():
        return ThrowResult(throw_frame=None, throw_idx=None, h_smooth=h_smooth)

    # ----------------------------------------------------
    # 4) 在 start_idx 之後找速度峰值（最大 v）
    # ----------------------------------------------------
    search_lo = start_idx + 1
    search_hi = T - 1

    sub_v = v[search_lo:search_hi + 1].copy()
    # 只看有限值
    if not np.isfinite(sub_v).any():
        return ThrowResult(throw_frame=None, throw_idx=None, h_smooth=h_smooth)

    rel = int(np.nanargmax(sub_v))
    t_throw = search_lo + rel

    throw_frame = frames[t_throw]

    return ThrowResult(throw_frame=throw_frame, throw_idx=t_throw, h_smooth=h_smooth)


def find_lead_foot_landing(kps_arr: np.ndarray,throw_idx: int,ankle_idx: int = 15,conf_min: float = 0.25,dist_thr: float = 8.0, vel_thr: float = 1.0, smooth_win: int = 2, max_lookback: int = 3) -> LeadFootResult:
    """
    找出前導腳在 THROW 之前「最近一次落地」的幀。

    改版重點：
      - ground_y 仍用高分位數，但先做平滑，避免單點噪音影響
      - dist_thr / vel_thr 會依 y 的變異度自動調整
      - contact 同時考慮垂直/水平速度，避免腳甩過地板被當落地
      - 真的取「THROW 前最近一次落地」，而不是最早一次
    """
    T = kps_arr.shape[0]
    if T == 0:
        return LeadFootResult(frame=-1, ground_y=-1, landing_frames=[])

    throw_idx = int(np.clip(throw_idx, 0, T - 1))

    # --------------------------
    # 1. 取出 ankle x, y, conf
    # --------------------------
    y_raw = kps_arr[:, ankle_idx, 1].astype(float)
    x_raw = kps_arr[:, ankle_idx, 0].astype(float)
    conf  = kps_arr[:, ankle_idx, 2].astype(float)

    y_raw[conf < conf_min] = np.nan
    x_raw[conf < conf_min] = np.nan

    valid = np.isfinite(y_raw)
    if not valid.any():
        return LeadFootResult(frame=-1, ground_y=-1, landing_frames=[])

    # --------------------------
    # 2. 時間平滑 x, y
    # --------------------------
    y_smooth = np.full(T, np.nan, dtype=float)
    x_smooth = np.full(T, np.nan, dtype=float)

    for t in range(T):
        s = max(0, t - smooth_win)
        e = min(T, t + smooth_win + 1)
        yw = y_raw[s:e]
        yw = yw[np.isfinite(yw)]
        if len(yw) > 0:
            y_smooth[t] = float(np.mean(yw))

        xw = x_raw[s:e]
        xw = xw[np.isfinite(xw)]
        if len(xw) > 0:
            x_smooth[t] = float(np.mean(xw))

    valid_smooth = np.isfinite(y_smooth)
    if not valid_smooth.any():
        return LeadFootResult(frame=-1, ground_y=-1, landing_frames=[])

    # --------------------------
    # 3. 推估 ground_y
    #    先用平滑後 y 的高分位數，再做一次平滑
    # --------------------------
    base_ground = float(np.nanquantile(y_smooth[valid_smooth], 0.9))

    ground_local = np.full(T, np.nan, dtype=float)
    win_g = smooth_win * 3 + 1  # 比 y_smooth 稍微大一點的窗
    for t in range(T):
        s = max(0, t - win_g // 2)
        e = min(T, t + win_g // 2 + 1)
        yw = y_smooth[s:e]
        yw = yw[np.isfinite(yw)]
        if len(yw) > 0:
            ground_local[t] = float(np.nanquantile(yw, 0.9))

    # 若 local 資料不足，就退回 global
    if np.isfinite(ground_local).any():
        ground_y = float(np.nanmedian(ground_local[np.isfinite(ground_local)]))
    else:
        ground_y = base_ground

    # --------------------------
    # 4. 距離地板 & 速度 vx, vy
    # --------------------------
    dist_ground = ground_y - y_smooth

    vy = np.full(T, np.nan, dtype=float)
    vx = np.full(T, np.nan, dtype=float)
    for t in range(1, T):
        if np.isfinite(y_smooth[t]) and np.isfinite(y_smooth[t - 1]):
            vy[t] = y_smooth[t] - y_smooth[t - 1]
        if np.isfinite(x_smooth[t]) and np.isfinite(x_smooth[t - 1]):
            vx[t] = x_smooth[t] - x_smooth[t - 1]

    # --------------------------
    # 5. 自適應門檻（依標準差調整）
    # --------------------------
    finite_dist = dist_ground[np.isfinite(dist_ground)]
    if len(finite_dist) > 0:
        dist_std = float(np.nanstd(finite_dist))
        dist_thr_eff = max(dist_thr, dist_std * 0.7)
    else:
        dist_thr_eff = dist_thr

    finite_vy = vy[np.isfinite(vy)]
    if len(finite_vy) > 0:
        vy_std = float(np.nanstd(finite_vy))
        vy_thr_eff = max(vel_thr, vy_std * 0.5)
    else:
        vy_thr_eff = vel_thr

    finite_vx = vx[np.isfinite(vx)]
    if len(finite_vx) > 0:
        vx_std = float(np.nanstd(finite_vx))
        vx_thr_eff = max(vel_thr, vx_std * 0.5)  # 水平速度門檻也用 vel_thr 當基準
    else:
        vx_thr_eff = vel_thr

    # --------------------------
    # 6. contact 判斷
    # --------------------------
    is_low  = dist_ground <= dist_thr_eff
    is_slow_v = np.abs(vy) <= vy_thr_eff
    is_slow_x = np.abs(vx) <= vx_thr_eff

    contact = np.logical_and(is_low, np.logical_and(is_slow_v, is_slow_x))
    contact[~np.isfinite(y_smooth)] = False

    # --------------------------
    # 7. 找落地事件（0 → 1），只看 THROW 之前
    # --------------------------
    landing_frames: list[int] = []
    upper = min(T, throw_idx + 1)
    for t in range(1, upper):
        if not contact[t - 1] and contact[t]:
            landing_frames.append(t)

    if len(landing_frames) == 0:
        return LeadFootResult(frame=-1, ground_y=ground_y, landing_frames=[])

    # 「THROW 之前最近一次落地」→ 取最大者
    raw_frame = max(landing_frames)

    # --------------------------
    # 8. 往前微調幾幀，讓時間更接近腳一碰地
    # --------------------------
    thr_back = dist_thr_eff + max(3.0, dist_thr_eff * 0.3)

    best_frame = raw_frame
    for t in range(raw_frame - 1, max(-1, raw_frame - max_lookback) - 1, -1):
        if np.isnan(dist_ground[t]):
            break
        if dist_ground[t] <= thr_back:
            best_frame = t
        else:
            break

    return LeadFootResult(frame=int(best_frame), ground_y=float(ground_y), landing_frames=landing_frames)


def find_pivot_foot_landing(kps_arr: np.ndarray,lead_idx: int,throw_idx: int,ankle_idx: int = 16,conf_min: float = 0.25,dist_thr: float = 8.0,vel_thr: float = 2.0,smooth_win: int = 2,max_lookback: int = 3,search_window: int = 8,) -> PivotFootResult:
    """
    找「軸心腳」在 THROW 之前、時間上最接近前導腳落地 (lead_idx) 的那次著地。

    改版重點：
      - ground_y / dist_thr / vel_thr 同樣自適應調整
      - contact 同時看 vx + vy
      - 優先用 0→1 contact 當落地事件，從中選出「最接近 lead_idx」的
      - 若完全沒有 0→1，就在 lead_idx 附近一小段內找 dist_ground 最小的當作落地
    """
    T = kps_arr.shape[0]
    if T == 0:
        return PivotFootResult(frame=-1, ground_y=-1, landing_frames=[])

    throw_idx = int(np.clip(throw_idx, 0, T - 1))
    lead_idx = int(np.clip(lead_idx, 0, T - 1))

    # 1. 取出 pivot ankle 的 x, y, conf
    y_raw = kps_arr[:, ankle_idx, 1].astype(float)
    x_raw = kps_arr[:, ankle_idx, 0].astype(float)
    conf  = kps_arr[:, ankle_idx, 2].astype(float)

    y_raw[conf < conf_min] = np.nan
    x_raw[conf < conf_min] = np.nan

    valid = np.isfinite(y_raw)
    if not valid.any():
        return PivotFootResult(frame=-1, ground_y=-1, landing_frames=[])

    # 2. 平滑
    y_smooth = np.full(T, np.nan, dtype=float)
    x_smooth = np.full(T, np.nan, dtype=float)
    for t in range(T):
        s = max(0, t - smooth_win)
        e = min(T, t + smooth_win + 1)
        yw = y_raw[s:e]
        yw = yw[np.isfinite(yw)]
        if len(yw) > 0:
            y_smooth[t] = float(np.mean(yw))

        xw = x_raw[s:e]
        xw = xw[np.isfinite(xw)]
        if len(xw) > 0:
            x_smooth[t] = float(np.mean(xw))

    valid_smooth = np.isfinite(y_smooth)
    if not valid_smooth.any():
        return PivotFootResult(frame=-1, ground_y=-1, landing_frames=[])

    # 3. 推估 ground_y
    base_ground = float(np.nanquantile(y_smooth[valid_smooth], 0.9))

    ground_local = np.full(T, np.nan, dtype=float)
    win_g = smooth_win * 3 + 1
    for t in range(T):
        s = max(0, t - win_g // 2)
        e = min(T, t + win_g // 2 + 1)
        yw = y_smooth[s:e]
        yw = yw[np.isfinite(yw)]
        if len(yw) > 0:
            ground_local[t] = float(np.nanquantile(yw, 0.9))

    if np.isfinite(ground_local).any():
        ground_y = float(np.nanmedian(ground_local[np.isfinite(ground_local)]))
    else:
        ground_y = base_ground

    # 4. dist_ground + vx, vy
    dist_ground = ground_y - y_smooth

    vy = np.full(T, np.nan, dtype=float)
    vx = np.full(T, np.nan, dtype=float)
    for t in range(1, T):
        if np.isfinite(y_smooth[t]) and np.isfinite(y_smooth[t - 1]):
            vy[t] = y_smooth[t] - y_smooth[t - 1]
        if np.isfinite(x_smooth[t]) and np.isfinite(x_smooth[t - 1]):
            vx[t] = x_smooth[t] - x_smooth[t - 1]

    # 5. 自適應門檻
    finite_dist = dist_ground[np.isfinite(dist_ground)]
    if len(finite_dist) > 0:
        dist_std = float(np.nanstd(finite_dist))
        dist_thr_eff = max(dist_thr, dist_std * 0.7)
    else:
        dist_thr_eff = dist_thr

    finite_vy = vy[np.isfinite(vy)]
    if len(finite_vy) > 0:
        vy_std = float(np.nanstd(finite_vy))
        vy_thr_eff = max(vel_thr, vy_std * 0.5)
    else:
        vy_thr_eff = vel_thr

    finite_vx = vx[np.isfinite(vx)]
    if len(finite_vx) > 0:
        vx_std = float(np.nanstd(finite_vx))
        vx_thr_eff = max(vel_thr, vx_std * 0.5)
    else:
        vx_thr_eff = vel_thr

    # 6. contact
    is_low  = dist_ground <= dist_thr_eff
    is_slow_v = np.abs(vy) <= vy_thr_eff
    is_slow_x = np.abs(vx) <= vx_thr_eff
    contact = np.logical_and(is_low, np.logical_and(is_slow_v, is_slow_x))
    contact[~np.isfinite(y_smooth)] = False

    # 7. 0→1 落地事件（只看 THROW 之前）
    landing_frames: list[int] = []
    for t in range(1, throw_idx):
        if not contact[t - 1] and contact[t]:
            landing_frames.append(t)

    raw_frame: int | None = None
    if landing_frames:
        # 在 THROW 之前所有落地中，找「時間上最接近 lead_idx」的那一個
        candidates = [t for t in landing_frames if 0 <= t < throw_idx]
        if candidates:
            raw_frame = min(candidates, key=lambda t: abs(t - lead_idx))

    # 8. 如果完全沒有 0→1（軸心腳幾乎都貼地）
    if raw_frame is None:
        lo = max(0, lead_idx - search_window)
        hi = min(T, lead_idx + search_window + 1)
        sub = dist_ground[lo:hi].copy()
        sub[~np.isfinite(sub)] = np.inf
        rel = int(np.argmin(sub))
        raw_frame = lo + rel

    # 9. 往前微調
    thr_back = dist_thr_eff + max(3.0, dist_thr_eff * 0.3)

    best_frame = raw_frame
    for t in range(raw_frame - 1, max(-1, raw_frame - max_lookback) - 1, -1):
        if np.isnan(dist_ground[t]):
            break
        if dist_ground[t] <= thr_back:
            best_frame = t
        else:
            break

    return PivotFootResult(frame=int(best_frame),ground_y=float(ground_y),landing_frames=landing_frames,)
    
def find_lead_step_after_catch(kps_arr: np.ndarray,catch_idx: int,end_idx: int,ankle_idx: int = 15,conf_min: float = 0.25,dist_thr: float = 25.0, smooth_win: int = 2,max_after: int = 45) -> LeadFootResult:
    """
    找「接球之後、end_idx 之前」的前導腳 (ankle_idx) 墊步 touchdown：
    - 先對 ankle y 做時域平滑（抗 jitters）
    - 再在一個小 window 內找 local minima（局部最低點）
    - 同時要求距離 ground_y 夠近
    """

    T = kps_arr.shape[0]

    # 1. index 檢查
    if catch_idx is None or catch_idx < 0 or catch_idx >= T:
        return LeadFootResult(frame=-1, ground_y=np.nan, landing_frames=[])

    if end_idx is None:
        end_idx = T - 1
    end_idx = min(end_idx, T - 1)

    if end_idx <= catch_idx:
        return LeadFootResult(frame=-1, ground_y=np.nan, landing_frames=[])

    # 2. 取出 ankle y + conf
    y_raw = kps_arr[:, ankle_idx, 1].astype(float).copy()
    conf = kps_arr[:, ankle_idx, 2].astype(float).copy()
    y_raw[conf < conf_min] = np.nan

    valid = y_raw[~np.isnan(y_raw)]
    if len(valid) == 0:
        return LeadFootResult(frame=-1, ground_y=np.nan, landing_frames=[])

    # 3. 推估 ground_y（用較高分位數避免被抬腳影響）
    ground_y = float(np.nanquantile(valid, 0.95))

    # 4. 對 y 做時域平滑（移動平均，消掉「往上跳一幀」這種 jitter）
    y_smooth = np.full_like(y_raw, np.nan)
    for t in range(T):
        s = max(0, t - smooth_win)
        e = min(T, t + smooth_win + 1)
        win = y_raw[s:e]
        win = win[~np.isnan(win)]
        if len(win) > 0:
            y_smooth[t] = float(np.mean(win))

    # 5. 計算距離地板（越小越貼地）
    dist_ground = ground_y - y_smooth

    # 6. 限制搜尋範圍：接球之後，到 end_idx / max_after 之內
    lo = catch_idx + 1
    hi = min(end_idx, catch_idx + max_after, T - 1)
    if lo >= hi:
        return LeadFootResult(frame=-1, ground_y=ground_y, landing_frames=[])

    # 7. 在 [lo, hi] 內找「局部最低點」做為 touchdown 候選
    #    （用小 window 看 local minima，可以抗掉中間一幀突然往上的抖動）
    cand_frames = []
    local_win = 2  # 看 t-2..t+2 的局部最低
    for t in range(lo, hi + 1):
        if not np.isfinite(y_smooth[t]):
            continue
        # 離地要夠近
        if not np.isfinite(dist_ground[t]) or dist_ground[t] > dist_thr:
            continue

        s = max(lo, t - local_win)
        e = min(hi, t + local_win)
        win = y_smooth[s:e + 1]
        win = win[np.isfinite(win)]
        if len(win) == 0:
            continue

        ymin = np.min(win)
        # 允許一點誤差（避免因為平滑/量化造成 ≈）
        if y_smooth[t] <= ymin + 1.0:
            cand_frames.append(t)

    # 8. 如果有候選：選「離 CATCH 最近」且在 CATCH 之後的那一幀
    if cand_frames:
        # 這裡的定義是「接球後最早的 touchdown」
        best_frame = min(cand_frames)
        return LeadFootResult(frame=best_frame,ground_y=ground_y,landing_frames=cand_frames)

    # 9. 如果連 local minima 候選都沒有 → fallback：
    #    在範圍內選 dist_ground 最小的幀，當作「最貼地」的那一幀
    sub = dist_ground[lo:hi + 1]
    if not np.isfinite(sub).any():
        return LeadFootResult(frame=-1, ground_y=ground_y, landing_frames=[])
    rel = int(np.nanargmin(sub))
    best_frame = lo + rel

    return LeadFootResult(frame=best_frame, ground_y=ground_y, landing_frames=cand_frames)

# phase.py 末端加上這個函式（放在 find_lead_step_after_catch 之後即可）

def find_pivot_foot_between_catch_and_lead(kps_arr: np.ndarray, catch_idx: int, lead_step_idx: int, ankle_idx: int = 16, conf_min: float = 0.25, dist_thr: float = 25.0, smooth_win: int = 2, max_lookback: int = 3) -> PivotFootResult:
    """
    在「接球 (catch_idx)」到「前導腳墊步落地 (lead_step_idx)」之間，
    找軸心腳 (ankle_idx) 的一次落地（邏輯大致比照其他落地偵測）。
    """
    T = kps_arr.shape[0]

    if catch_idx is None or lead_step_idx is None:
        return PivotFootResult(frame=-1, ground_y=np.nan, landing_frames=[])

    catch_idx = max(0, min(catch_idx, T - 1))
    lead_step_idx = max(0, min(lead_step_idx, T - 1))
    if lead_step_idx <= catch_idx:
        return PivotFootResult(frame=-1, ground_y=np.nan, landing_frames=[])

    # 1. 取出 ankle y + conf
    y_raw = kps_arr[:, ankle_idx, 1].astype(float).copy()
    conf = kps_arr[:, ankle_idx, 2].astype(float).copy()
    y_raw[conf < conf_min] = np.nan

    valid = y_raw[~np.isnan(y_raw)]
    if len(valid) == 0:
        return PivotFootResult(frame=-1, ground_y=np.nan, landing_frames=[])

    # 2. 推估 ground_y（高分位數，避免抬腳影響）
    ground_y = float(np.nanquantile(valid, 0.95))

    # 3. 時域平滑
    y_smooth = np.full_like(y_raw, np.nan)
    for t in range(T):
        s = max(0, t - smooth_win)
        e = min(T, t + smooth_win + 1)
        win = y_raw[s:e]
        win = win[~np.isnan(win)]
        if len(win) > 0:
            y_smooth[t] = float(np.mean(win))

    # 4. 距離地板（越小越貼地）
    dist_ground = ground_y - y_smooth

    # 5. 限制搜尋範圍：接球到 lead_step 之間
    lo = catch_idx
    hi = lead_step_idx
    if lo >= hi:
        return PivotFootResult(frame=-1, ground_y=ground_y, landing_frames=[])

    # 6. 在 [lo, hi] 內找 local minima 當 touchdown 候選
    cand_frames = []
    local_win = 2
    for t in range(lo, hi + 1):
        if not np.isfinite(y_smooth[t]):
            continue
        if not np.isfinite(dist_ground[t]) or dist_ground[t] > dist_thr:
            continue

        s = max(lo, t - local_win)
        e = min(hi, t + local_win)
        win = y_smooth[s:e + 1]
        win = win[np.isfinite(win)]
        if len(win) == 0:
            continue

        ymin = np.min(win)
        if y_smooth[t] <= ymin + 1.0:
            cand_frames.append(t)

    # 7. 選一個最佳幀：接球後最早的一次 touchdown
    if cand_frames:
        best_frame = min(cand_frames)
        return PivotFootResult(frame=best_frame, ground_y=ground_y, landing_frames=cand_frames,)

    # 8. fallback：沒有明顯 local minima，就選範圍內「最貼地」那一幀
    sub = dist_ground[lo:hi + 1]
    if not np.isfinite(sub).any():
        return PivotFootResult(frame=-1, ground_y=ground_y, landing_frames=[])
    rel = int(np.nanargmin(sub))
    raw_frame = lo + rel

    # 再往前微調幾幀（跟其他落地函式一樣）
    thr_back = dist_thr + 5.0
    best_frame = raw_frame
    for t in range(raw_frame - 1, max(-1, raw_frame - max_lookback) - 1, -1):
        if np.isnan(dist_ground[t]):
            break
        if dist_ground[t] <= thr_back:
            best_frame = t
        else:
            break

    return PivotFootResult(frame=best_frame, ground_y=ground_y, landing_frames=[])