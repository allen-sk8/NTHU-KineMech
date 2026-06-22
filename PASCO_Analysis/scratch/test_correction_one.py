import pandas as pd
import numpy as np
import jumpmetrics
from jumpmetrics.core.processors import ForceTimeCurveCMJTakeoffProcessor
from jumpmetrics.core.io import find_frame_when_off_plate, find_landing_frame
from jumpmetrics.signal_processing.filters import butterworth_filter

# 讀取原始力量數據
df_raw = pd.read_csv("outputs/force/001.csv")
f1 = df_raw.iloc[:, 0]
f2 = df_raw.iloc[:, 1]
total_f = (f1 + f2).dropna().values

fs = 1000

# 預處理：濾波
filtered_force = butterworth_filter(
    arr=total_f,
    cutoff_frequency=20,
    fps=fs,
    padding=fs
)

# 偵測離地瞬間 (Takeoff)
takeoff_frame = find_frame_when_off_plate(
    force_trace=pd.Series(filtered_force),
    sampling_frequency=fs,
    force_threshold=30
)

# 偵測著地瞬間 (Landing)
landing_frame = find_landing_frame(
    force_series=filtered_force[takeoff_frame:],
    sampling_frequency=fs,
    threshold_value=30
)
if landing_frame != -1:
    landing_frame += takeoff_frame

# 使用 JumpMetrics 處理
processor = ForceTimeCurveCMJTakeoffProcessor(
    force_series=pd.Series(filtered_force[:takeoff_frame+1]),
    sampling_frequency=fs
)
processor.get_jump_events()

som = processor.start_of_unweighting_phase
print(f"動作開始 SoM 幀: {som}")

# 獲取原始的運動學序列
v_orig = processor.velocity_series
s_orig = processor.displacement_series

# 執行校正：以動作開始 (som) 的值進行歸零
v_corrected = v_orig - v_orig[som]
# 重新計算位移：對校正後的速度進行積分
dt = 1.0 / fs
s_corrected = np.zeros_like(s_orig)
s_corrected[som:] = np.cumsum(0.5 * (v_corrected[som:] + np.roll(v_corrected, 1)[som:]) * dt)
# 注意：在 som 之前，我們將位移和速度都設為 0
v_corrected[:som] = 0.0
s_corrected[:som] = 0.0

# 重新計算功率
p_corrected = processor.force_series * v_corrected

# 比較在重心最低、離地瞬間等點的數值
df_ref = pd.read_excel("refer_results/final/001-1.xlsx").set_index("Event")

events_to_compare = ["動作開始", "重心最低", "最大推蹬力", "離地瞬間"]
metrics = ["Frame", "Time (s)", "F-value (N)", "S-value (m)", "P-value (W)", "V-value (m/s)"]

print("\n--- 比較結果 (校正前 vs 校正後 vs 對照組) ---")
for event in events_to_compare:
    # 找出該事件在我們計算中的 frame index
    if event == "動作開始":
        idx = som
    elif event == "重心最低":
        idx = processor.start_of_propulsive_phase
    elif event == "最大推蹬力":
        idx = processor.peak_force_frame
    elif event == "離地瞬間":
        idx = takeoff_frame
    else:
        continue
        
    print(f"\n[事件: {event}]")
    print(f"  Frame: 計算={idx}, 對照={df_ref.loc['Frame', event]}")
    
    # 校正前的值
    v_pre = v_orig[idx]
    s_pre = s_orig[idx]
    p_pre = (processor.force_series * v_orig)[idx]
    
    # 校正後的值
    v_post = v_corrected[idx]
    s_post = s_corrected[idx]
    p_post = p_corrected[idx]
    
    # 對照組的值
    v_ref = df_ref.loc["V-value (m/s)", event]
    s_ref = df_ref.loc["S-value (m)", event]
    p_ref = df_ref.loc["P-value (W)", event]
    
    print(f"  V-value: 校正前={v_pre:8.4f} | 校正後={v_post:8.4f} | 對照組={v_ref:8.4f}")
    print(f"  S-value: 校正前={s_pre:8.4f} | 校正後={s_post:8.4f} | 對照組={s_ref:8.4f}")
    print(f"  P-value: 校正前={p_pre:8.4f} | 校正後={p_post:8.4f} | 對照組={p_ref:8.4f}")
