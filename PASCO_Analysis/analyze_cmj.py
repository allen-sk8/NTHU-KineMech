import os
import pandas as pd
import numpy as np
import argparse
import logging
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from jumpmetrics.core.io import find_frame_when_off_plate, find_landing_frame
from jumpmetrics.signal_processing.filters import butterworth_filter

# 匯入自定義進階肌力指標計算模組
from metrics_calculator import calculate_advanced_metrics, format_cmj_sheet

# 關閉不必要的日誌輸出
logging.basicConfig(level=logging.WARNING)

# 設定 Matplotlib 中文字型，避免亂碼警告
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'DFKai-SB', 'Segoe UI', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

class JumpAnalysisConfig:
    """
    垂直跳躍分析之參數配置類別，提供所有演算法微調參數的預設值
    """
    def __init__(self, 
                 fs=1000,
                 cutoff_frequency=20.0,
                 quiet_phase_max_sec=1.5,
                 quiet_phase_buffer_ms=200,
                 som_threshold_pct=0.025,
                 som_retrograde_window_ms=250,
                 takeoff_threshold_n=10.0,
                 landing_threshold_n=30.0,
                 landing_safety_window_ms=150,
                 amortization_before_ms=45,
                 amortization_after_ms=45):
        self.fs = fs
        self.cutoff_frequency = cutoff_frequency
        self.quiet_phase_max_sec = quiet_phase_max_sec
        self.quiet_phase_buffer_ms = quiet_phase_buffer_ms
        self.som_threshold_pct = som_threshold_pct
        self.som_retrograde_window_ms = som_retrograde_window_ms
        self.takeoff_threshold_n = takeoff_threshold_n
        self.landing_threshold_n = landing_threshold_n
        self.landing_safety_window_ms = landing_safety_window_ms
        self.amortization_before_ms = amortization_before_ms
        self.amortization_after_ms = amortization_after_ms

def process_single_run(force_series, config=None):
    """
    以物理公式及自定義生物力學特徵演算法處理單一跳躍序列
    """
    if config is None:
        config = JumpAnalysisConfig()
        
    fs = config.fs
    
    # 1. 預處理：低通濾波
    filtered_force = butterworth_filter(
        arr=force_series,
        cutoff_frequency=config.cutoff_frequency,
        fps=fs,
        padding=fs
    )
    
    # 2. 偵測離地瞬間 (Takeoff)
    # 先以濾波後的力量與 30N 門檻進行粗定位
    takeoff_rough = find_frame_when_off_plate(
        force_trace=pd.Series(filtered_force),
        sampling_frequency=fs,
        force_threshold=30
    )
    if takeoff_rough == -1:
        takeoff_rough = np.argmin(filtered_force)
        
    # 於粗定位點前 50 幀向後搜尋原始力量第一次小於設定閾值 (預設 10N) 的幀
    takeoff_frame = -1
    start_search = max(0, takeoff_rough - 50)
    for idx in range(start_search, len(force_series)):
        if force_series[idx] < config.takeoff_threshold_n:
            takeoff_frame = idx
            break
    if takeoff_frame == -1:
        takeoff_frame = takeoff_rough
        
    # 2.5 偵測著地瞬間 (Landing)
    # 著地安全時間視窗 (預設 150 毫秒) 之後，力量大於設定閾值 (預設 30N)
    landing_frame = -1
    safety_samples = int(config.landing_safety_window_ms * fs / 1000)
    for idx in range(takeoff_frame + safety_samples, len(force_series)):
        if force_series[idx] > config.landing_threshold_n:
            landing_frame = idx
            break
    if landing_frame == -1:
        # 退路：用內建邏輯尋找
        landing_frame_rough = find_landing_frame(
            force_series=filtered_force[takeoff_frame:],
            sampling_frequency=fs,
            threshold_value=config.landing_threshold_n
        )
        if landing_frame_rough != -1:
            landing_frame = landing_frame_rough + takeoff_frame
        else:
            landing_frame = len(force_series) - 1
            
    # 3. 動作開始 (SoM) 與體重 (BW) 判定
    # 3.1 尋找推蹬峰值 (Peak Force) 以避開離地前的力量下降區
    peak_rough = np.argmax(filtered_force[:takeoff_frame])
    
    # 3.2 尋找「最大失重」的粗估位置
    max_unweight_rough = np.argmin(filtered_force[:peak_rough])
    
    # 3.3 體重平均區間上限：min(設定靜態秒數, 最大失重 - 設定緩衝毫秒)
    quiet_samples_limit = int(config.quiet_phase_max_sec * fs)
    buffer_samples = int(config.quiet_phase_buffer_ms * fs / 1000)
    weight_end = min(quiet_samples_limit, max(0, max_unweight_rough - buffer_samples))
    if weight_end <= 0:
        weight_end = max(1, max_unweight_rough - 50)
        
    # 3.4 計算基準體重
    bw = np.mean(force_series[:weight_end])
    mass = bw / 9.81
    
    # 3.5 逆向回溯尋找 SoM (動作開始)
    som_threshold = bw * config.som_threshold_pct
    som_frame = -1
    retrograde_samples = int(config.som_retrograde_window_ms * fs / 1000)
    search_start = max(0, max_unweight_rough - retrograde_samples)
    for idx in range(max_unweight_rough, search_start - 1, -1):
        if abs(filtered_force[idx] - bw) < som_threshold:
            som_frame = idx + 1
            break
    if som_frame == -1:
        som_frame = search_start
        
    # 3.6 數值積分計算質心運動學 (以 SoM 點進行歸零校正)
    acc = (filtered_force - bw) / mass
    dt = 1.0 / fs
    
    # 速度積分 (V)
    v_orig = np.zeros_like(acc)
    v_orig[1:] = np.cumsum(0.5 * (acc[1:] + acc[:-1]) * dt)
    v_corrected = v_orig - v_orig[som_frame]
    v_corrected[:som_frame] = 0.0
    
    # 位移積分 (S)
    s_corrected = np.zeros_like(v_corrected)
    s_corrected[som_frame:] = np.cumsum(0.5 * (v_corrected[som_frame:] + np.roll(v_corrected, 1)[som_frame:]) * dt)
    s_corrected[:som_frame] = 0.0
    
    # 功率 (P) ── P = F_raw * V
    p_corrected = force_series * v_corrected
    p_corrected[:som_frame] = 0.0
    
    # 3.7 判定其他特徵點
    # 制動開始：速度最低點
    braking_frame = np.argmin(v_corrected[:takeoff_frame])
    
    # 重心最低：位移最低點
    lowest_com_frame = np.argmin(s_corrected[:takeoff_frame])
    
    # 最大失重：動作開始到制動開始之間，濾波力最低點
    if braking_frame > som_frame:
        max_unweight_frame = np.argmin(filtered_force[som_frame:braking_frame]) + som_frame
    else:
        max_unweight_frame = max_unweight_rough
        
    # 最大推蹬力：制動開始到離地之間，原始力的最大值
    if takeoff_frame > braking_frame:
        peak_force_frame = np.argmax(force_series[braking_frame:takeoff_frame]) + braking_frame
    else:
        peak_force_frame = np.argmax(force_series[:takeoff_frame])
        
    # 最大離心功率
    if lowest_com_frame > som_frame:
        max_ecc_power_frame = np.argmin(p_corrected[som_frame:lowest_com_frame]) + som_frame
    else:
        max_ecc_power_frame = som_frame
        
    # 最大向心功率
    if takeoff_frame > lowest_com_frame:
        max_con_power_frame = np.argmax(p_corrected[lowest_com_frame:takeoff_frame]) + lowest_com_frame
    else:
        max_con_power_frame = lowest_com_frame
        
    events_map = {
        "動作開始": som_frame,
        "最大失重": max_unweight_frame,
        "制動開始": braking_frame,
        "重心最低": lowest_com_frame,
        "最大推蹬力": peak_force_frame,
        "離地瞬間": takeoff_frame,
        "著地瞬間": landing_frame,
        "最大離心功率": max_ecc_power_frame,
        "最大向心功率": max_con_power_frame
    }
    
    # 補足：攤還期
    amort_before = int(config.amortization_before_ms * fs / 1000)
    amort_after = int(config.amortization_after_ms * fs / 1000)
    events_map["攤還期開始"] = int(lowest_com_frame - amort_before) if lowest_com_frame > amort_before else braking_frame
    events_map["攤還期結束"] = int(lowest_com_frame + amort_after) if lowest_com_frame + amort_after < len(filtered_force) else takeoff_frame
    
    v_series = v_corrected[:takeoff_frame+1]
    s_series = s_corrected[:takeoff_frame+1]
    p_series = p_corrected[:takeoff_frame+1]
    f_net_series = force_series - bw
    
    # 5. 構建輸出 DataFrame
    results = []
    event_names = ["動作開始", "最大失重", "制動開始", "重心最低", "最大推蹬力", "離地瞬間", "著地瞬間", "最大離心功率", "最大向心功率", "攤還期開始", "攤還期結束"]
    
    for name in event_names:
        idx = events_map.get(name, -1)
        if idx < 0 or idx >= len(s_series):
            if name == "著地瞬間" and idx >= 0 and idx < len(force_series):
                results.append([name, float(idx), float(idx/fs), float(force_series[idx] - bw), 0, 0, 0])
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
    res_df = res_df.T.reset_index()
    
    extra_curves = {
        "filtered_force": filtered_force,
        "v_curve": v_corrected,
        "s_curve": s_corrected,
        "power_curve": p_corrected,
        "bw": bw,
        "weight_end": weight_end,
        "max_unweight_rough": max_unweight_rough,
        "events_map": events_map
    }
    
    return res_df, extra_curves

def plot_jump_events_integrated(trial_id, force_series, extra_curves, config, save_path):
    """
    整合式繪圖函數，將特徵曲線、特徵事件點與防呆窗口繪製成高質感診斷圖表
    """
    filtered_force = extra_curves["filtered_force"]
    v_curve = extra_curves["v_curve"]
    s_curve = extra_curves["s_curve"]
    p_curve = extra_curves["power_curve"]
    bw = extra_curves["bw"]
    weight_end = extra_curves["weight_end"]
    max_unweight_rough = extra_curves["max_unweight_rough"]
    events_map = extra_curves["events_map"]
    
    fs = config.fs
    time_sec = np.arange(len(force_series)) / fs
    
    scale_v = 500.0
    scale_s = 3000.0
    scale_p = 0.5
    
    v_scaled = v_curve * scale_v
    s_scaled = s_curve * scale_s
    p_scaled = p_curve * scale_p
    
    # 載入對照組
    ref_path = f"refer_results/final/{trial_id}.xlsx"
    ref_events = {}
    if os.path.exists(ref_path):
        try:
            df_ref = pd.read_excel(ref_path, sheet_name="Details").set_index("Event")
            df_ref.index.name = "Event"
            for col in df_ref.columns:
                ref_events[col] = {
                    "Frame": int(df_ref.loc["Frame", col]),
                    "F": df_ref.loc["F-value (N)", col],
                    "S": df_ref.loc["S-value (m)", col],
                    "P": df_ref.loc["P-value (W)", col],
                    "V": df_ref.loc["V-value (m/s)", col]
                }
        except:
            pass
            
    fig, (ax_curve, ax_timeline) = plt.subplots(
        2, 1, figsize=(15, 12),
        gridspec_kw={'height_ratios': [2.8, 1.8]},
        sharex=True
    )
    
    # 繪製主曲線
    ax_curve.plot(time_sec, force_series, color='#2C3E50', alpha=0.25, label='原始力量 (Raw Force)')
    ax_curve.plot(time_sec, filtered_force, color='#2C3E50', linewidth=2.5, label='濾波力量 (Filtered Force)')
    ax_curve.plot(time_sec, v_scaled, color='#2980B9', linewidth=2.0, label=f'重心速度 (Velocity × {int(scale_v)})')
    ax_curve.plot(time_sec, s_scaled, color='#8E44AD', linewidth=2.0, label=f'重心位移 (Displacement × {int(scale_s)})')
    ax_curve.plot(time_sec, p_scaled, color='#27AE60', linewidth=1.5, label=f'機械功率 (Power × {scale_p})')
    
    # 體重線
    ax_curve.axhline(bw, color='#E74C3C', linestyle='--', alpha=0.5, label=f'體重基準線 ({bw:.1f} N)')
    ax_curve.axhline(0, color='#7F8C8D', linestyle='-', alpha=0.3)
    
    # 繪製防呆窗口背景陰影
    t_w_end = weight_end / fs
    ax_curve.axvspan(0, t_w_end, color='#3498DB', alpha=0.1, zorder=1)
    ax_curve.text(t_w_end / 2, bw * 1.5, "體重計算區間", color='#2980B9', fontsize=8.5, fontweight='bold', ha='center', alpha=0.7)
    
    t_search_start = max(0, max_unweight_rough - int(config.som_retrograde_window_ms * fs / 1000)) / fs
    t_search_end = max_unweight_rough / fs
    ax_curve.axvspan(t_search_start, t_search_end, color='#E67E22', alpha=0.1, zorder=1)
    ax_curve.text((t_search_start + t_search_end) / 2, bw * 1.65, f"SoM 搜尋區間\n(往回 {config.som_retrograde_window_ms}ms)", color='#D35400', fontsize=8.5, fontweight='bold', ha='center', alpha=0.7)
    
    # 攤還期陰影
    amort_start = events_map.get("攤還期開始", -1)
    amort_end = events_map.get("攤還期結束", -1)
    if amort_start >= 0 and amort_end >= 0:
        t_a_start = amort_start / fs
        t_a_end = amort_end / fs
        ax_curve.axvspan(t_a_start, t_a_end, color='#F1C40F', alpha=0.1, zorder=1)
        ax_timeline.axvspan(t_a_start, t_a_end, color='#F1C40F', alpha=0.1, zorder=1)
        ax_curve.text((t_a_start + t_a_end)/2, bw * 0.2, "攤還期", color='#D68910', fontsize=10, fontweight='bold', ha='center')
        
    ax_curve.grid(True, linestyle=':', alpha=0.5)
    ax_curve.set_ylabel("物理量幅值 (已等比縮放對齊)", fontsize=11, fontweight='bold')
    ax_curve.set_title(f"垂直跳躍整合分析圖 - Trial: {trial_id}", fontsize=15, fontweight='bold', pad=15)
    
    event_curves = {
        "動作開始": (filtered_force, "Force"),
        "最大失重": (filtered_force, "Force"),
        "制動開始": (v_scaled, "Velocity"),
        "重心最低": (s_scaled, "Displacement"),
        "最大推蹬力": (force_series, "Force"),
        "離地瞬間": (force_series, "Force"),
        "著地瞬間": (force_series, "Force"),
        "最大離心功率": (p_scaled, "Power"),
        "最大向心功率": (p_scaled, "Power"),
        "攤還期開始": (s_scaled, "Displacement"),
        "攤還期結束": (s_scaled, "Displacement")
    }
    
    event_names = ["動作開始", "最大失重", "制動開始", "重心最低", "最大推蹬力", "離地瞬間", "著地瞬間", "最大離心功率", "最大向心功率"]
    
    for i, name in enumerate(event_names):
        our_idx = events_map.get(name, -1)
        ref_idx = ref_events.get(name, {}).get("Frame", -1) if ref_events else -1
        
        y_val = len(event_names) - 1 - i
        ax_timeline.axhline(y_val, color='#BDC3C7', linestyle='--', alpha=0.3)
        ax_timeline.text(-0.05, y_val, name, ha='right', va='center', fontsize=10, fontweight='bold')
        
        if our_idx >= 0:
            our_t = our_idx / fs
            ax_timeline.scatter(our_t, y_val, color='blue', s=70, marker='o', edgecolors='black')
            
            curve_data, _ = event_curves.get(name, (filtered_force, "Force"))
            if our_idx < len(curve_data):
                y_curve_val = curve_data[our_idx]
                ax_curve.scatter(our_t, y_curve_val, color='blue', s=50, marker='o', edgecolors='black', zorder=5)
                ax_curve.axvline(our_t, color='blue', linestyle=':', alpha=0.4)
                ax_timeline.axvline(our_t, color='blue', linestyle=':', alpha=0.4)
                
        if ref_idx >= 0:
            ref_t = ref_idx / fs
            ax_timeline.scatter(ref_t, y_val, color='red', s=80, marker='x', linewidths=2)
            
            curve_data, _ = event_curves.get(name, (filtered_force, "Force"))
            if ref_idx < len(curve_data):
                y_curve_val = curve_data[ref_idx]
                ax_curve.scatter(ref_t, y_curve_val, color='red', s=40, marker='x', linewidths=1.5, zorder=5)
                ax_curve.axvline(ref_t, color='red', linestyle='--', alpha=0.3)
                ax_timeline.axvline(ref_t, color='red', linestyle='--', alpha=0.3)
                
        if our_idx >= 0 and ref_idx >= 0:
            diff = our_idx - ref_idx
            txt_color = 'green' if abs(diff) <= 2 else ('orange' if abs(diff) <= 10 else 'red')
            label_pos = max(our_t, ref_t) + 0.05
            ax_timeline.text(label_pos, y_val, f"Δ: {int(diff):+d} 毫秒", va='center', ha='left', fontsize=9, color=txt_color, fontweight='bold')

    ax_timeline.set_yticks([])
    ax_timeline.set_xlabel("時間 (Seconds)", fontsize=11, fontweight='bold')
    ax_timeline.set_xlim(0, len(force_series)/fs)
    ax_timeline.grid(True, linestyle=':', alpha=0.5)
    
    props = dict(boxstyle='round,pad=0.4', facecolor='#FDFEFE', edgecolor='#BDC3C7', alpha=0.9)
    formula_intro = (
        "【物理計算與微調參數】\n"
        f"• 濾波頻率: {config.cutoff_frequency} Hz\n"
        f"• SoM 門檻: {config.som_threshold_pct*100:.1f}% BW\n"
        f"• 攤還期區間: -{config.amortization_before_ms}ms / +{config.amortization_after_ms}ms"
    )
    ax_curve.text(0.01, 0.03, formula_intro, transform=ax_curve.transAxes, fontsize=9, verticalalignment='bottom', bbox=props)
    
    legend_elements = [
        Line2D([0], [0], color='#2C3E50', lw=2, label='力量 (Force, N)'),
        Line2D([0], [0], color='#2980B9', lw=2, label='速度 × 500 (Velocity, m/s)'),
        Line2D([0], [0], color='#8E44AD', lw=2, label='位移 × 3000 (Displacement, m)'),
        Line2D([0], [0], color='#27AE60', lw=1.5, label='功率 × 0.5 (Power, W)'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='none', markeredgecolor='blue', markersize=9, label='我們程式 (o)'),
    ]
    if ref_events:
        legend_elements.append(Line2D([0], [0], marker='x', color='w', markeredgecolor='red', markersize=10, markeredgewidth=2, label='對照組 (x)'))
    ax_curve.legend(handles=legend_elements, loc='upper right', framealpha=0.9, shadow=True, fontsize=9)
    
    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=150)
    plt.close()

def main():
    parser = argparse.ArgumentParser(description="PASCO CMJ (蹲跳) 垂直跳躍分析工具")
    parser.add_argument("--no-plot", action="store_false", dest="plot", help="若帶入此參數則不生成診斷繪圖")
    parser.add_argument("--force", action="store_true", help="是否強制重新計算並覆寫已存在的 Excel 報告")
    parser.add_argument("--fs", type=int, default=1000, help="數據取樣率 (Hz)")
    parser.add_argument("--cutoff", type=float, default=20.0, help="Butterworth 低通濾波切斷頻率 (Hz)")
    parser.add_argument("--quiet-max", type=float, default=1.5, help="靜態體重平均區間上限 (秒)")
    parser.add_argument("--quiet-buffer", type=int, default=200, help="體重平均前退最大失重之緩衝時間 (毫秒)")
    parser.add_argument("--som-pct", type=float, default=0.025, help="SoM 判定體重偏離閾值百分比 (如 0.025 代表 2.5%)")
    parser.add_argument("--som-window", type=int, default=280, help="SoM 逆向尋找最大窗口長度 (毫秒)")
    parser.add_argument("--takeoff-n", type=float, default=10.0, help="離地瞬間精確力閾值 (N)")
    parser.add_argument("--landing-n", type=float, default=30.0, help="著地瞬間精確力閾值 (N)")
    parser.add_argument("--landing-window", type=int, default=150, help="著地瞬間防餘震安全視窗時間 (毫秒)")
    parser.add_argument("--amort-before", type=int, default=45, help="攤還期開始前推偏移時間 (毫秒)")
    parser.add_argument("--amort-after", type=int, default=45, help="攤還期結束後推偏移時間 (毫秒)")
    
    args = parser.parse_args()
    
    config = JumpAnalysisConfig(
        fs=args.fs,
        cutoff_frequency=args.cutoff,
        quiet_phase_max_sec=args.quiet_max,
        quiet_phase_buffer_ms=args.quiet_buffer,
        som_threshold_pct=args.som_pct,
        som_retrograde_window_ms=args.som_window,
        takeoff_threshold_n=args.takeoff_n,
        landing_threshold_n=args.landing_n,
        landing_safety_window_ms=args.landing_window,
        amortization_before_ms=args.amort_before,
        amortization_after_ms=args.amort_after
    )
    
    # 核心輸出根目錄 (最外層以 cmj 區分)
    base_dir = 'outputs/cmj'
    
    if not os.path.exists(base_dir):
        print(f"錯誤: 輸入資料夾 {base_dir} 不存在。請先執行 convert_cap_to_csv.py 轉換數據。")
        return
        
    # 遍歷 base_dir 下的所有專案資料夾 (例如 outputs/cmj/2026跆拳)
    proj_folders = [f for f in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, f))]
    if len(proj_folders) == 0:
        print(f"提示: 資料夾 {base_dir} 內無任何專案子資料夾。")
        return
        
    for proj in proj_folders:
        proj_path = os.path.join(base_dir, proj)
        # 遍歷受試者資料夾 (例如 outputs/cmj/2026跆拳/001)
        subject_folders = [s for s in os.listdir(proj_path) if os.path.isdir(os.path.join(proj_path, s))]
        
        for subject in subject_folders:
            subject_dir = os.path.join(proj_path, subject)
            # 尋找該受試者資料夾下的 CSV 力量數據檔
            csv_files = [f for f in os.listdir(subject_dir) if f.endswith('.csv')]
            if len(csv_files) == 0:
                continue
                
            for file in csv_files:
                print(f"\n分析檔案: {os.path.join(proj, subject, file)}")
                df = pd.read_csv(os.path.join(subject_dir, file))
                file_id = file.split('.')[0]
                
                num_runs = len(df.columns) // 2
                for r in range(1, num_runs + 1):
                    trial_id = f"{file_id}-{r}"
                    output_path = os.path.join(subject_dir, f"{trial_id}.xlsx")
                    
                    if os.path.exists(output_path) and not args.force:
                        print(f"  -> Run {r} 已存在輸出 Excel，跳過計算。")
                        continue
                        
                    f1 = df.iloc[:, (r-1)*2]
                    f2 = df.iloc[:, (r-1)*2+1]
                    total_f = (f1 + f2).dropna().values
                    
                    if len(total_f) < 1000: continue
                    
                    try:
                        # 執行主要物理運動學與特徵點計算 (Details Sheet)
                        res, extra_curves = process_single_run(total_f, config)
                        
                        # 格式化 Details DataFrame
                        res.columns = res.iloc[0]
                        res_output = res.drop(res.index[0])
                        
                        # 將 Details 結果轉化為 dict，以便進階指標計算使用
                        res_temp = res_output.set_index("Event")
                        event_vals = {}
                        for event_name in res_temp.columns:
                            event_vals[event_name] = {
                                "Frame": float(res_temp.loc["Frame", event_name]),
                                "Time": float(res_temp.loc["Time (s)", event_name]),
                                "F": float(res_temp.loc["F-value (N)", event_name]),
                                "S": float(res_temp.loc["S-value (m)", event_name]),
                                "P": float(res_temp.loc["P-value (W)", event_name]),
                                "V": float(res_temp.loc["V-value (m/s)", event_name])
                            }
                        
                        # 計算進階肌力指標 (CMJ Sheet)
                        df_cmj = calculate_advanced_metrics(
                            event_vals=event_vals,
                            force_series=total_f,
                            p_series=extra_curves["power_curve"],
                            bw=extra_curves["bw"],
                            fs=config.fs,
                            height=np.nan, # 身高留為 nan
                            age=np.nan     # 年齡留為 nan
                        )
                        
                        # 直接與 CSV 放在同一個受試者資料夾下！
                        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                            res_output.to_excel(writer, sheet_name="Details", index=False)
                            df_cmj.to_excel(writer, sheet_name="CMJ", index=False)
                        
                        # 進行 CMJ 頁面合併儲存格與大標題後處理格式化
                        format_cmj_sheet(output_path)
                        
                        print(f"  -> Run {r} 計算並寫入 Excel 完成")
                        
                        # 自動繪圖控制
                        if args.plot:
                            plot_path = os.path.join(subject_dir, f"{trial_id}_comparison.png")
                            plot_jump_events_integrated(trial_id, total_f, extra_curves, config, plot_path)
                            print(f"  -> Run {r} 診斷圖表已生成: {plot_path}")
                    except Exception as e:
                        import traceback
                        print(f"  -> Run {r} 處理失敗: {e}")
                        traceback.print_exc()

if __name__ == "__main__":
    main()
