import os
import pandas as pd
import numpy as np
import jumpmetrics
from jumpmetrics.core.processors import ForceTimeCurveCMJTakeoffProcessor
from jumpmetrics.core.io import find_frame_when_off_plate, find_landing_frame
from jumpmetrics.signal_processing.filters import butterworth_filter
import logging

# 關閉不必要的日誌輸出
logging.basicConfig(level=logging.WARNING)

def process_single_run(force_series, fs=1000):
    # 1. 預處理：濾波 (JumpMetrics 建議使用 26.64Hz 或類似的低通濾波)
    filtered_force = butterworth_filter(
        arr=force_series,
        cutoff_frequency=20, # 參考您的報告建議
        fps=fs,
        padding=fs # 增加 padding 減少邊緣效應
    )
    
    # 2. 偵測離地瞬間 (Takeoff)
    # 我們從數據中後半段找第一個力量接近 0 的點
    takeoff_frame = find_frame_when_off_plate(
        force_trace=pd.Series(filtered_force),
        sampling_frequency=fs,
        force_threshold=30 # 稍微提高閾值避免雜訊干擾
    )
    
    if takeoff_frame == -1:
        # 如果沒找到離地點，嘗試直接尋找最小值的點
        takeoff_frame = np.argmin(filtered_force)
        
    # 2.5 偵測著地瞬間 (Landing)
    landing_frame = find_landing_frame(
        force_series=filtered_force[takeoff_frame:],
        sampling_frequency=fs,
        threshold_value=30
    )
    if landing_frame != -1:
        landing_frame += takeoff_frame
        
    # 3. 截取數據：JumpMetrics 通常處理動作開始到離地的區段
    # 我們傳入完整的序列，讓它自己找 SoM
    processor = ForceTimeCurveCMJTakeoffProcessor(
        force_series=pd.Series(filtered_force[:takeoff_frame+1]),
        sampling_frequency=fs
    )
    
    # 執行分析
    processor.get_jump_events()
    processor.compute_jump_metrics()
    
    # 4. 提取事件映射
    # JumpMetrics 的屬性映射到您的 Excel 格式
    events_map = {
        "動作開始": processor.start_of_unweighting_phase,
        "制動開始": processor.start_of_braking_phase,
        "重心最低": processor.start_of_propulsive_phase,
        "最大推蹬力": processor.peak_force_frame,
        "離地瞬間": takeoff_frame,
        "著地瞬間": landing_frame
    }
    
    # 補充：攤還期 (Amortization Phase)
    # 參考實驗室數據，攤還期大約是在重心最低點前後各約 40-50ms 的區間
    # 這裡我們使用制動開始到推進開始的一半作為開始點？
    # 或者我們直接使用 JumpMetrics 的某些標記
    lowest_com = processor.start_of_propulsive_phase
    braking = processor.start_of_braking_phase
    if lowest_com >= 0 and braking >= 0:
        # 簡單估算：以最低點為中心
        events_map["攤還期開始"] = int(lowest_com - 44) if lowest_com > 44 else braking
        events_map["攤還期結束"] = int(lowest_com + 42) if lowest_com + 42 < len(filtered_force) else takeoff_frame

    # 補充一些需要手動計算的事件 (基於 JumpMetrics 的波形)
    # 最大失重
    som = processor.start_of_unweighting_phase
    braking = processor.start_of_braking_phase
    if som >= 0 and braking > som:
        events_map["最大失重"] = np.argmin(filtered_force[som:braking]) + som
    
    # 功率相關
    p_series = processor.force_series * processor.velocity_series
    v_series = processor.velocity_series
    s_series = processor.displacement_series
    f_net_series = processor.force_series - processor.body_weight
    
    lowest_com = processor.start_of_propulsive_phase
    if som >= 0 and lowest_com > som:
        events_map["最大離心功率"] = np.argmin(p_series[som:lowest_com]) + som
    if lowest_com >= 0 and takeoff_frame > lowest_com:
        events_map["最大向心功率"] = np.argmax(p_series[lowest_com:takeoff_frame]) + lowest_com

    # 5. 構建輸出 DataFrame
    results = []
    # 按照您的 Excel 順序排列
    event_names = ["動作開始", "最大失重", "制動開始", "重心最低", "最大推蹬力", "離地瞬間", "著地瞬間", "最大離心功率", "最大向心功率", "攤還期開始", "攤還期結束"]
    
    for name in event_names:
        idx = events_map.get(name, -1)
        # 如果索引超出了 processor 的處理範圍 (例如著地瞬間)，則手動計算部分數值
        if idx < 0 or idx >= len(f_net_series):
            if name == "著地瞬間" and idx >= 0 and idx < len(filtered_force):
                # 著地瞬間的力量值使用原始濾波後的數據
                results.append([name, float(idx), float(idx/fs), float(filtered_force[idx] - processor.body_weight), 0, 0, 0])
            else:
                results.append([name, 0, 0, 0, 0, 0, 0])
            continue
            
        results.append([
            name,
            float(idx),
            float(idx / fs),
            float(f_net_series[idx]),
            float(s_series[idx]),
            float(p_series[idx]),
            float(v_series[idx])
        ])
    
    res_df = pd.DataFrame(results, columns=["Event", "Frame", "Time (s)", "F-value (N)", "S-value (m)", "P-value (W)", "V-value (m/s)"])
    return res_df.T.reset_index()

def main():
    input_dir = 'outputs/force'
    output_dir = 'outputs/final'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    for file in os.listdir(input_dir):
        if not file.endswith('.csv'): continue
        
        print(f"分析中: {file}")
        df = pd.read_csv(os.path.join(input_dir, file))
        file_id = file.split('.')[0]
        
        # 遍歷所有的 Run
        num_runs = len(df.columns) // 2
        for r in range(1, num_runs + 1):
            # 合併力量
            f1 = df.iloc[:, (r-1)*2]
            f2 = df.iloc[:, (r-1)*2+1]
            total_f = (f1 + f2).dropna().values
            
            if len(total_f) < 1000: continue
            
            try:
                res = process_single_run(total_f)
                # 格式化輸出
                res.columns = res.iloc[0]
                res = res.drop(res.index[0])
                
                output_path = os.path.join(output_dir, f"{file_id}-{r}.xlsx")
                res.to_excel(output_path, index=False)
                print(f"  -> Run {r} 完成")
            except Exception as e:
                print(f"  -> Run {r} 失敗: {e}")

if __name__ == "__main__":
    main()
