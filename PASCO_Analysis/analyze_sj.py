import os
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from scipy.signal import butter, filtfilt
import openpyxl

# 載入我們的指標計算庫
from metrics_calculator import calculate_sj_metrics, format_sj_sheet

class JumpAnalysisConfig:
    """跳躍分析參數配置類別"""
    def __init__(self, fs=1000, cutoff_frequency=20.0, quiet_phase_max_sec=1.0, 
                 som_threshold_pct=0.025, takeoff_threshold_n=10.0, 
                 landing_threshold_n=30.0, landing_safety_window_ms=150):
        self.fs = fs                                     # 取樣率 (Hz)
        self.cutoff_frequency = cutoff_frequency         # 低通濾波截止頻率 (Hz)
        self.quiet_phase_max_sec = quiet_phase_max_sec   # 靜態體重平均區間上限 (秒)
        self.som_threshold_pct = som_threshold_pct       # SoM 判定體重偏離閾值百分比 (如 0.025 代表 2.5%)
        self.takeoff_threshold_n = takeoff_threshold_n   # 離地瞬間力閾值 (N)
        self.landing_threshold_n = landing_threshold_n   # 著地瞬間力閾值 (N)
        self.landing_safety_window_ms = landing_safety_window_ms # 著地安全視窗，避開餘震 (毫秒)

def butterworth_filter(arr, cutoff_frequency=20.0, fps=1000.0, padding=1000):
    """
    四階雙向 Butterworth 低通濾波器，以消除信號雜訊
    """
    nyq = 0.5 * fps
    normal_cutoff = cutoff_frequency / nyq
    b, a = butter(4, normal_cutoff, btype='low', analog=False)
    return filtfilt(b, a, arr)

def find_frame_when_off_plate(force_trace, sampling_frequency, force_threshold=30.0):
    """
    粗定位受試者離地的幀數 (尋找力值第一次低於設定閾值的瞬間)
    """
    for idx in range(len(force_trace)):
        if force_trace[idx] < force_threshold:
            return idx
    return -1

def process_single_run(force_series, config):
    """
    針對單次跳躍 (Single Run) 進行特徵點定位與物理量計算 (Details)
    
    參數:
        force_series (np.ndarray): 原始力量序列 (N)
        config (JumpAnalysisConfig): 配置參數
        
    回傳:
        res_df (pd.DataFrame): Details 報表數據
        extra_curves (dict): 計算過程的中間物理量曲線
    """
    fs = config.fs
    
    # 進行低通濾波
    filtered_force = butterworth_filter(force_series, cutoff_frequency=config.cutoff_frequency, fps=fs)
    
    # 1. 離地瞬間判定
    # 先粗定位 (力值降至 30N 以下)
    takeoff_rough = find_frame_when_off_plate(
        force_trace=pd.Series(filtered_force),
        sampling_frequency=fs,
        force_threshold=30.0
    )
    
    # 往回 50 幀開始尋找原始力量第一次小於 takeoff_threshold_n (如 10N) 的精確幀
    takeoff_frame = -1
    for idx in range(max(0, takeoff_rough - 50), len(force_series)):
        if force_series[idx] < config.takeoff_threshold_n:
            takeoff_frame = idx
            break
    if takeoff_frame == -1:
        takeoff_frame = takeoff_rough
        
    # 2. 著地瞬間判定
    # 在離地瞬間加上安全視窗之後，尋找第一個原始力重新突破 landing_threshold_n (如 30N) 的精確幀
    landing_frame = len(force_series) - 1
    landing_search_start = takeoff_frame + int(config.landing_safety_window_ms * fs / 1000)
    for idx in range(landing_search_start, len(force_series)):
        if force_series[idx] > config.landing_threshold_n:
            landing_frame = idx
            break
            
    # 3. 動作開始 (SoM) 與體重 (BW) 判定
    # 3.1 尋找推蹬峰值 (Peak Force) 的粗定位
    peak_rough = np.argmax(filtered_force[:takeoff_frame])
    
    # 3.2 體重平均區間：SJ 使用起跳前最前面 1.0 秒作為靜態準備期
    quiet_samples_limit = int(config.quiet_phase_max_sec * fs)
    weight_end = min(quiet_samples_limit, len(force_series))
    bw = np.mean(force_series[:weight_end])
    mass = bw / 9.81
    
    # 3.3 逆向回溯尋找 SoM (動作開始)
    # 從推蹬峰值 peak_rough 往回搜尋，直到力量第一次低於 bw + som_threshold (2.5% BW)
    som_threshold = bw * config.som_threshold_pct
    som_frame = -1
    for idx in range(peak_rough, 0, -1):
        if filtered_force[idx] < bw + som_threshold:
            som_frame = idx + 1
            break
    if som_frame == -1:
        som_frame = 0
        
    # 4. 數值積分計算質心運動學 (以 SoM 點進行歸零校正)
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
    
    # 機械功率 (P) ── P = F_raw * V
    p_corrected = force_series * v_corrected
    p_corrected[:som_frame] = 0.0
    
    # 5. 判定其他特徵點
    # 最大推蹬力：SoM 到離地之間，原始力的最大值
    peak_force_frame = np.argmax(force_series[som_frame:takeoff_frame]) + som_frame
    
    # 最大向心功率：SoM 到離地之間，功率的最大值
    max_con_power_frame = np.argmax(p_corrected[som_frame:takeoff_frame]) + som_frame
    
    events_map = {
        "動作開始": som_frame,
        "最大推蹬力": peak_force_frame,
        "離地瞬間": takeoff_frame,
        "著地瞬間": landing_frame,
        "最大向心功率": max_con_power_frame
    }
    
    v_series = v_corrected[:takeoff_frame+1]
    s_series = s_corrected[:takeoff_frame+1]
    p_series = p_corrected[:takeoff_frame+1]
    f_net_series = force_series - bw
    
    # 6. 構建輸出 DataFrame (只包含這 5 個事件)
    results = []
    event_names = ["動作開始", "最大推蹬力", "離地瞬間", "著地瞬間", "最大向心功率"]
    
    for name in event_names:
        idx = events_map.get(name, -1)
        if idx < 0:
            results.append([name, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
            continue
            
        # 著地瞬間通常超出推進段 s_series 範圍，進行特別處理
        if idx >= len(s_series):
            if name == "著地瞬間" and idx >= 0 and idx < len(force_series):
                results.append([name, float(idx), float(idx/fs), float(force_series[idx] - bw), 0.0, 0.0, 0.0])
            else:
                results.append([name, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
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
        "peak_rough": peak_rough,
        "events_map": events_map
    }
    
    return res_df, extra_curves

def plot_jump_events_integrated(trial_id, force_series, extra_curves, config, save_path):
    """
    整合式繪圖函數，將 SJ 特徵曲線、特徵事件點與防呆窗口繪製成高質感診斷圖表
    """
    filtered_force = extra_curves["filtered_force"]
    v_curve = extra_curves["v_curve"]
    s_curve = extra_curves["s_curve"]
    p_curve = extra_curves["power_curve"]
    bw = extra_curves["bw"]
    weight_end = extra_curves["weight_end"]
    peak_rough = extra_curves["peak_rough"]
    events_map = extra_curves["events_map"]
    
    fs = config.fs
    time_sec = np.arange(len(force_series)) / fs
    
    # 物理量縮放比例 (為能顯示在同一張圖中)
    scale_v = 500.0
    scale_s = 3000.0
    scale_p = 0.5
    
    v_scaled = v_curve * scale_v
    s_scaled = s_curve * scale_s
    p_scaled = p_curve * scale_p
    
    # 嘗試加載對照組參考值 (Details)
    ref_path = f"refer_results/sj/SJ Excel/{trial_id}.xlsx"
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
    
    # 繪製各物理量曲線
    ax_curve.plot(time_sec, force_series, color='#2C3E50', alpha=0.25, label='原始力量 (Raw Force)')
    ax_curve.plot(time_sec, filtered_force, color='#2C3E50', linewidth=2.5, label='濾波力量 (Filtered Force)')
    ax_curve.plot(time_sec, v_scaled, color='#2980B9', linewidth=2.0, label=f'重心速度 (Velocity × {int(scale_v)})')
    ax_curve.plot(time_sec, s_scaled, color='#8E44AD', linewidth=2.0, label=f'重心位移 (Displacement × {int(scale_s)})')
    ax_curve.plot(time_sec, p_scaled, color='#27AE60', linewidth=1.5, label=f'機械功率 (Power × {scale_p})')
    
    # 體重與零基準線
    ax_curve.axhline(bw, color='#E74C3C', linestyle='--', alpha=0.5, label=f'體重基準線 ({bw:.1f} N)')
    ax_curve.axhline(0, color='#7F8C8D', linestyle='-', alpha=0.3)
    
    # 繪製防呆窗口背景陰影
    t_w_end = weight_end / fs
    ax_curve.axvspan(0, t_w_end, color='#3498DB', alpha=0.1, zorder=1)
    ax_curve.text(t_w_end / 2, bw * 1.5, "體重計算區間", color='#2980B9', fontsize=8.5, fontweight='bold', ha='center', alpha=0.7)
    
    # SoM 搜尋區間陰影 (自峰值往前搜尋至 SoM)
    som_f = events_map.get("動作開始", 0)
    t_search_start = som_f / fs
    t_search_end = peak_rough / fs
    ax_curve.axvspan(t_search_start, t_search_end, color='#E67E22', alpha=0.1, zorder=1)
    ax_curve.text((t_search_start + t_search_end) / 2, bw * 1.65, "SoM 反向尋找區間", color='#D35400', fontsize=8.5, fontweight='bold', ha='center', alpha=0.7)
    
    ax_curve.grid(True, linestyle=':', alpha=0.5)
    ax_curve.set_ylabel("物理量幅值 (已等比縮放對齊)", fontsize=11, fontweight='bold')
    ax_curve.set_title(f"Squat Jump (SJ) 垂直跳躍整合分析圖 - Trial: {trial_id}", fontsize=15, fontweight='bold', pad=15)
    
    # 特徵事件點物理量映射表
    event_curves = {
        "動作開始": (filtered_force, "Force"),
        "最大推蹬力": (force_series, "Force"),
        "離地瞬間": (force_series, "Force"),
        "著地瞬間": (force_series, "Force"),
        "最大向心功率": (p_scaled, "Power")
    }
    
    event_names = ["動作開始", "最大推蹬力", "離地瞬間", "著地瞬間", "最大向心功率"]
    
    # 繪製下半部的時間定位軸與對照組比對結果
    for i, name in enumerate(event_names):
        our_idx = events_map.get(name, -1)
        ref_idx = ref_events.get(name, {}).get("Frame", -1) if ref_events else -1
        
        y_val = len(event_names) - 1 - i
        ax_timeline.axhline(y_val, color='#BDC3C7', linestyle='--', alpha=0.3)
        ax_timeline.text(-0.05, y_val, name, ha='right', va='center', fontsize=10, fontweight='bold')
        
        # 繪製本系統計算點
        if our_idx >= 0:
            our_t = our_idx / fs
            ax_timeline.scatter(our_t, y_val, color='blue', s=70, marker='o', edgecolors='black')
            
            curve_data, _ = event_curves.get(name, (filtered_force, "Force"))
            if our_idx < len(curve_data):
                y_curve_val = curve_data[our_idx]
                ax_curve.scatter(our_t, y_curve_val, color='blue', s=50, marker='o', edgecolors='black', zorder=5)
                ax_curve.axvline(our_t, color='blue', linestyle=':', alpha=0.4)
                ax_timeline.axvline(our_t, color='blue', linestyle=':', alpha=0.4)
                
        # 繪製對照組點
        if ref_idx >= 0:
            ref_t = ref_idx / fs
            ax_timeline.scatter(ref_t, y_val, color='red', s=80, marker='x', linewidths=2)
            
            curve_data, _ = event_curves.get(name, (filtered_force, "Force"))
            if ref_idx < len(curve_data):
                y_curve_val = curve_data[ref_idx]
                ax_curve.scatter(ref_t, y_curve_val, color='red', s=40, marker='x', linewidths=1.5, zorder=5)
                ax_curve.axvline(ref_t, color='red', linestyle='--', alpha=0.3)
                ax_timeline.axvline(ref_t, color='red', linestyle='--', alpha=0.3)
                
        # 計算誤差毫秒差並加註標籤
        if our_idx >= 0 and ref_idx >= 0:
            diff = our_idx - ref_idx
            txt_color = 'green' if abs(diff) <= 2 else ('orange' if abs(diff) <= 10 else 'red')
            label_pos = max(our_t, ref_t) + 0.05
            ax_timeline.text(label_pos, y_val, f"Δ: {int(diff):+d} 毫秒", va='center', ha='left', fontsize=9, color=txt_color, fontweight='bold')
            
    ax_timeline.set_yticks([])
    ax_timeline.set_xlabel("時間 (Seconds)", fontsize=11, fontweight='bold')
    ax_timeline.set_xlim(0, len(force_series)/fs)
    ax_timeline.grid(True, linestyle=':', alpha=0.5)
    
    # 浮動物理說明資訊
    props = dict(boxstyle='round,pad=0.4', facecolor='#FDFEFE', edgecolor='#BDC3C7', alpha=0.9)
    formula_intro = (
        "【物理計算與微調參數】\n"
        f"• 濾波頻率: {config.cutoff_frequency} Hz\n"
        f"• SoM 門檻: {config.som_threshold_pct*100:.1f}% BW (Peak backward)\n"
        f"• 離地門檻: {config.takeoff_threshold_n} N\n"
        f"• 著地安全窗: {config.landing_safety_window_ms} ms"
    )
    ax_curve.text(0.01, 0.03, formula_intro, transform=ax_curve.transAxes, fontsize=9, verticalalignment='bottom', bbox=props)
    
    # 圖例
    legend_elements = [
        Line2D([0], [0], color='#2C3E50', lw=2, label='力量 (Force, N)'),
        Line2D([0], [0], color='#2980B9', lw=2, label='速度 × 500 (Velocity, m/s)'),
        Line2D([0], [0], color='#8E44AD', lw=2, label='位移 × 3000 (Displacement, m)'),
        Line2D([0], [0], color='#27AE60', lw=1.5, label='功率 × 0.5 (Power, W)'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='none', markeredgecolor='blue', markersize=9, label='本系統計算 (o)'),
    ]
    if ref_events:
        legend_elements.append(Line2D([0], [0], marker='x', color='w', markeredgecolor='red', markersize=10, markeredgewidth=2, label='對照組 (x)'))
    ax_curve.legend(handles=legend_elements, loc='upper right', framealpha=0.9, shadow=True, fontsize=9)
    
    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=150)
    plt.close()

def main():
    parser = argparse.ArgumentParser(description="PASCO SJ (Squat Jump) 垂直跳躍分析工具")
    parser.add_argument("--no-plot", action="store_false", dest="plot", help="若帶入此參數則不生成診斷繪圖")
    parser.add_argument("--force", action="store_true", help="是否強制重新計算並覆寫已存在的 Excel 報告")
    parser.add_argument("--fs", type=int, default=1000, help="數據取樣率 (Hz)")
    parser.add_argument("--cutoff", type=float, default=20.0, help="Butterworth 低通濾波切斷頻率 (Hz)")
    parser.add_argument("--quiet-max", type=float, default=1.0, help="靜態體重平均區間上限 (秒)")
    parser.add_argument("--som-pct", type=float, default=0.025, help="SoM 判定體重偏離閾值百分比 (如 0.025 代表 2.5%)")
    parser.add_argument("--takeoff-n", type=float, default=10.0, help="離地瞬間精確力閾值 (N)")
    parser.add_argument("--landing-n", type=float, default=30.0, help="著地瞬間精確力閾值 (N)")
    parser.add_argument("--landing-window", type=int, default=150, help="著地瞬間防餘震安全視窗時間 (毫秒)")
    
    args = parser.parse_args()
    
    config = JumpAnalysisConfig(
        fs=args.fs,
        cutoff_frequency=args.cutoff,
        quiet_phase_max_sec=args.quiet_max,
        som_threshold_pct=args.som_pct,
        takeoff_threshold_n=args.takeoff_n,
        landing_threshold_n=args.landing_n,
        landing_safety_window_ms=args.landing_window
    )
    
    # 核心輸出根目錄 (最外層以 sj 區分)
    base_dir = 'outputs/sj'
    
    if not os.path.exists(base_dir):
        print(f"錯誤: 輸入資料夾 {base_dir} 不存在。請先執行 convert_cap_to_csv.py 轉換數據。")
        return
        
    # 遍歷 base_dir 下的所有專案資料夾 (例如 outputs/sj/SJ 原始)
    proj_folders = [f for f in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, f))]
    if len(proj_folders) == 0:
        print(f"提示: 資料夾 {base_dir} 內無任何專案子資料夾。")
        return
        
    for proj in proj_folders:
        proj_path = os.path.join(base_dir, proj)
        # 遍歷受試者資料夾 (例如 outputs/sj/SJ 原始/001)
        subject_folders = [s for s in os.listdir(proj_path) if os.path.isdir(os.path.join(proj_path, s))]
        
        for subject in subject_folders:
            subject_dir = os.path.join(proj_path, subject)
            # 尋找該受試者資料夾下的 CSV 力量數據檔
            csv_files = [f for f in os.listdir(subject_dir) if f.endswith('.csv')]
            if len(csv_files) == 0:
                continue
                
            for file in csv_files:
                print(f"\n分析檔案: {os.path.join(proj, subject, file)}")
                try:
                    df = pd.read_csv(os.path.join(subject_dir, file))
                except Exception as e:
                    print(f"  -> 讀取檔案失敗: {e}")
                    continue
                file_id = file.split('.')[0]
                
                # 計算 CSV 中包含幾個 Run (每兩個 Columns 為一組：Normal Force 和另一欄)
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
                    
                    if len(total_f) < 1000: 
                        continue
                    
                    try:
                        # 執行主要物理運動學與特徵點計算 (Details Sheet)
                        res, extra_curves = process_single_run(total_f, config)
                        
                        # 格式化 Details DataFrame
                        res.columns = res.iloc[0]
                        res_output = res.drop(res.index[0])
                        
                        # 將 Details 結果轉化為 dict，以供進階指標計算使用
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
                        
                        # 計算進階肌力指標 (SJ Sheet)
                        df_sj = calculate_sj_metrics(
                            event_vals=event_vals,
                            force_series=total_f,
                            p_series=extra_curves["power_curve"],
                            bw=extra_curves["bw"],
                            fs=config.fs,
                            height=170.0,  # 比照對照組預設身高
                            age=24.9       # 比照對照組預設年齡
                        )
                        
                        # 與 CSV 力量數據檔輸出在同一個受試者資料夾下
                        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                            res_output.to_excel(writer, sheet_name="Details", index=False)
                            df_sj.to_excel(writer, sheet_name="SJ", index=False)
                        
                        # 進行 SJ 頁面合併儲存格與大標題格式化後處理
                        format_sj_sheet(output_path)
                        
                        print(f"  -> Run {r} 計算並寫入 Excel 完成")
                        
                        # 診斷繪圖
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
