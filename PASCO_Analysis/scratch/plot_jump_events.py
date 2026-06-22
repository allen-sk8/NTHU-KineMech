import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from jumpmetrics.signal_processing.filters import butterworth_filter

# 設定 matplotlib 支援中文顯示
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'DFKai-SB', 'Segoe UI', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

def get_kinematic_curves(total_f, filtered_f, fs, takeoff_frame):
    """
    依據物理公式計算速度、位移與功率曲線 (與 analyze_jump_v2 同步的優化演算法)
    """
    # 1. 估算體重與尋找最大失重
    peak_rough = np.argmax(filtered_f[:takeoff_frame])
    max_unweight_rough = np.argmin(filtered_f[:peak_rough])
    
    # 體重平均區間上限：min(1.5秒, 最大失重 - 200ms)
    weight_end = min(int(1.5 * fs), max(0, max_unweight_rough - 200))
    if weight_end <= 0:
        weight_end = max(1, max_unweight_rough - 50)
        
    # 計算基準體重
    bw = np.mean(total_f[:weight_end])
    mass = bw / 9.81
    
    # 2. 逆向回溯搜尋 SoM (動作開始)
    som_threshold = bw * 0.025
    som = -1
    search_start = max(0, max_unweight_rough - 250)
    for idx in range(max_unweight_rough, search_start - 1, -1):
        if abs(filtered_f[idx] - bw) < som_threshold:
            som = idx + 1
            break
    if som == -1:
        som = search_start
        
    # 3. 計算加速度與積分
    acc = (filtered_f - bw) / mass
    dt = 1.0 / fs
    
    v_orig = np.zeros_like(acc)
    v_orig[1:] = np.cumsum(0.5 * (acc[1:] + acc[:-1]) * dt)
    
    v_corrected = v_orig - v_orig[som]
    v_corrected[:som] = 0.0
    
    s_corrected = np.zeros_like(v_corrected)
    s_corrected[som:] = np.cumsum(0.5 * (v_corrected[som:] + np.roll(v_corrected, 1)[som:]) * dt)
    s_corrected[:som] = 0.0
    
    power = total_f * v_corrected
    power[:som] = 0.0
    
    return v_corrected, s_curve_corrected(s_corrected), power, bw, som, weight_end, max_unweight_rough

def s_curve_corrected(s):
    return s

def load_events(trial_id):
    """
    讀取我們程式與對照組的事件結果
    """
    our_path = f"outputs/final/{trial_id}.xlsx"
    ref_path = f"refer_results/final/{trial_id}.xlsx"
    
    our_events = {}
    ref_events = {}
    
    if os.path.exists(our_path):
        df_our = pd.read_excel(our_path).set_index("Event")
        for col in df_our.columns:
            our_events[col] = {
                "Frame": int(df_our.loc["Frame", col]),
                "F": df_our.loc["F-value (N)", col],
                "S": df_our.loc["S-value (m)", col],
                "P": df_our.loc["P-value (W)", col],
                "V": df_our.loc["V-value (m/s)", col]
            }
            
    if os.path.exists(ref_path):
        df_ref = pd.read_excel(ref_path).set_index("Event")
        for col in df_ref.columns:
            ref_events[col] = {
                "Frame": int(df_ref.loc["Frame", col]),
                "F": df_ref.loc["F-value (N)", col],
                "S": df_ref.loc["S-value (m)", col],
                "P": df_ref.loc["P-value (W)", col],
                "V": df_ref.loc["V-value (m/s)", col]
            }
            
    return our_events, ref_events

def plot_jump_stacked_timeline(trial_id, save_dir=None):
    """
    上方繪製三線疊加的大圖，下方繪製事件對齊時間軸
    """
    # 1. 載入原始力量與事件
    try:
        parts = trial_id.split("-")
        file_prefix = parts[0]
        run_num = int(parts[1])
        csv_path = f"outputs/force/{file_prefix}.csv"
        df_raw = pd.read_csv(csv_path)
        f1 = df_raw.iloc[:, (run_num-1)*2]
        f2 = df_raw.iloc[:, (run_num-1)*2+1]
        total_f = (f1 + f2).dropna().values
        fs = 1000
    except Exception as e:
        print(f"錯誤 (載入 {trial_id} 失敗): {e}")
        return False
        
    our_events, ref_events = load_events(trial_id)
    if not our_events and not ref_events:
        print(f"警告: 找不到 {trial_id} 的事件數據。")
        return False
        
    # 2. 計算運動學曲線
    takeoff_frame = our_events.get("離地瞬間", {}).get("Frame", -1)
    if takeoff_frame == -1:
        takeoff_frame = ref_events.get("離地瞬間", {}).get("Frame", -1)
    if takeoff_frame == -1:
        takeoff_frame = len(total_f) - 1
        
    filtered_f = butterworth_filter(arr=total_f, cutoff_frequency=20, fps=fs, padding=fs)
    v_curve, s_curve, p_curve, bw, som_detected, weight_end, max_unweight_rough = get_kinematic_curves(total_f, filtered_f, fs, takeoff_frame)
    time_sec = np.arange(len(total_f)) / fs
    
    # 為了在同一個圖表上完美呈現，我們對曲線進行等比縮放以利疊加
    # 縮放係數
    scale_v = 500.0   # 速度 * 500
    scale_s = 3000.0  # 位移 * 3000
    scale_p = 0.5     # 功率 / 2
    
    v_scaled = v_curve * scale_v
    s_scaled = s_curve * scale_s
    p_scaled = p_curve * scale_p
    
    # 3. 建立畫布：上方大圖，下方時間軸
    fig, (ax_curve, ax_timeline) = plt.subplots(
        2, 1, figsize=(15, 12), 
        gridspec_kw={'height_ratios': [2.8, 1.8]},
        sharex=True
    )
    
    # 4. 上方子圖：多線疊加大圖
    # 繪製曲線
    ax_curve.plot(time_sec, total_f, color='#2C3E50', alpha=0.25, label='原始力量 (Raw Force)')
    ax_curve.plot(time_sec, filtered_f, color='#2C3E50', linewidth=2.5, label='濾波力量 (Filtered Force)')
    ax_curve.plot(time_sec, v_scaled, color='#2980B9', linewidth=2.0, label=f'重心速度 (Velocity × {int(scale_v)})')
    ax_curve.plot(time_sec, s_scaled, color='#8E44AD', linewidth=2.0, label=f'重心位移 (Displacement × {int(scale_s)})')
    ax_curve.plot(time_sec, p_scaled, color='#27AE60', linewidth=1.5, label=f'機械功率 (Power × {scale_p})')
    
    # 畫體重線
    ax_curve.axhline(bw, color='#E74C3C', linestyle='--', alpha=0.5, label=f'體重基準線 ({bw:.1f} N)')
    ax_curve.axhline(0, color='#7F8C8D', linestyle='-', alpha=0.3)
    
    # 畫防呆窗口背景陰影 (與底層優化演算法對齊)
    # 1. 體重平均窗口 (0 到 weight_end)
    t_w_end = weight_end / fs
    ax_curve.axvspan(0, t_w_end, color='#3498DB', alpha=0.1, zorder=1)
    ax_curve.text(t_w_end / 2, bw * 1.5, "體重計算區間", color='#2980B9', fontsize=8.5, fontweight='bold', ha='center', alpha=0.7)
    
    # 2. SoM 搜尋窗口 (最大失重往回推 250ms)
    t_search_start = max(0, max_unweight_rough - 250) / fs
    t_search_end = max_unweight_rough / fs
    ax_curve.axvspan(t_search_start, t_search_end, color='#E67E22', alpha=0.1, zorder=1)
    ax_curve.text((t_search_start + t_search_end) / 2, bw * 1.65, "SoM 搜尋區間\n(往回 250ms)", color='#D35400', fontsize=8.5, fontweight='bold', ha='center', alpha=0.7)

    ax_curve.grid(True, linestyle=':', alpha=0.5)
    ax_curve.set_ylabel("物理量幅值 (已等比縮放對齊)", fontsize=11, fontweight='bold')
    ax_curve.set_title(f"垂直跳躍分析特徵圖 (上: 曲線疊加 / 下: 事件對齊) - Trial: {trial_id}", fontsize=15, fontweight='bold', pad=15)
    
    # 5. 定義事件判定所對應的「縮放後曲線」
    # 這樣我們畫點時，點會剛好落在該曲線波形上！
    event_curves = {
        "動作開始": (filtered_f, "Force"),
        "最大失重": (filtered_f, "Force"),
        "制動開始": (v_scaled, "Velocity"),
        "重心最低": (s_scaled, "Displacement"),
        "最大推蹬力": (filtered_f, "Force"),
        "離地瞬間": (filtered_f, "Force"),
        "著地瞬間": (total_f, "Force"),
        "最大離心功率": (p_scaled, "Power"),
        "最大向心功率": (p_scaled, "Power"),
        "攤還期開始": (s_scaled, "Displacement"),
        "攤還期結束": (s_scaled, "Displacement")
    }
    
    # 6. 下方子圖：11 個事件的時間軸對比
    event_names = ["動作開始", "最大失重", "制動開始", "重心最低", "最大推蹬力", "離地瞬間", "著地瞬間", "最大離心功率", "最大向心功率", "攤還期開始", "攤還期結束"]
    colors = {
        "動作開始": "#1ABC9C", "最大失重": "#2ECC71", "制動開始": "#3498DB",
        "重心最低": "#9B59B6", "最大推蹬力": "#E74C3C", "離地瞬間": "#E67E22",
        "著地瞬間": "#D35400", "最大離心功率": "#1F3A60", "最大向心功率": "#27AE60",
        "攤還期開始": "#F1C40F", "攤還期結束": "#F39C12"
    }
    
    ax_timeline.set_ylim(-0.5, len(event_names) - 0.5)
    ax_timeline.set_yticks(range(len(event_names)))
    ax_timeline.set_yticklabels(event_names, fontsize=10, fontweight='bold')
    ax_timeline.grid(True, linestyle=':', alpha=0.5)
    
    # 遍歷事件進行雙圖標記
    for i, name in enumerate(event_names):
        color = colors.get(name, "#7F8C8D")
        curve_data, curve_name = event_curves.get(name, (filtered_f, "Force"))
        
        our_fr = our_events.get(name, {}).get("Frame", -1)
        ref_fr = ref_events.get(name, {}).get("Frame", -1)
        
        our_t = our_fr / fs if our_fr >= 0 else np.nan
        ref_t = ref_fr / fs if ref_fr >= 0 else np.nan
        
        our_val = curve_data[our_fr] if (our_fr >= 0 and our_fr < len(curve_data)) else np.nan
        ref_val = curve_data[ref_fr] if (ref_fr >= 0 and ref_fr < len(curve_data)) else np.nan
        
        # 6a. 繪製於上方「疊加曲線圖」中，點落在各自對應的波形線上
        if not np.isnan(our_t) and not np.isnan(our_val):
            ax_curve.scatter(our_t, our_val, color=color, edgecolor='blue', marker='o', s=70, zorder=5)
        if not np.isnan(ref_t) and not np.isnan(ref_val):
            ax_curve.scatter(ref_t, ref_val, color='red', marker='x', s=100, linewidth=2, zorder=4)
            
        # 若是核心事件，畫垂直線連通上下圖以便對齊檢視
        if name in ["動作開始", "重心最低", "離地瞬間", "著地瞬間"]:
            if not np.isnan(our_t):
                ax_curve.axvline(our_t, color=color, linestyle='--', alpha=0.3, linewidth=1.2)
                ax_timeline.axvline(our_t, color=color, linestyle='--', alpha=0.3, linewidth=1.2)
            if not np.isnan(ref_t):
                ax_curve.axvline(ref_t, color=color, linestyle=':', alpha=0.3, linewidth=1.2)
                ax_timeline.axvline(ref_t, color=color, linestyle=':', alpha=0.3, linewidth=1.2)

        # 6b. 繪製於下方「時間軸對齊圖」中
        y_val = i
        diff = (our_fr - ref_fr) if (our_fr >= 0 and ref_fr >= 0) else np.nan
        
        # 畫連通線
        if not np.isnan(our_t) and not np.isnan(ref_t):
            ax_timeline.plot([our_t, ref_t], [y_val, y_val], color='#BDC3C7', linestyle='-', linewidth=2, zorder=1)
            
        # 畫程式偵測點 (藍圈)
        if not np.isnan(our_t):
            ax_timeline.scatter(our_t, y_val, color=color, edgecolor='blue', marker='o', s=100, zorder=3, label='我們程式' if i==0 else "")
        # 畫對照組點 (紅叉)
        if not np.isnan(ref_t):
            ax_timeline.scatter(ref_t, y_val, color='red', marker='x', s=120, linewidth=2, zorder=2, label='對照組' if i==0 else "")
            
        # 標註毫秒偏差
        if not np.isnan(diff):
            txt_color = 'green' if abs(diff) <= 2 else ('orange' if abs(diff) <= 10 else 'red')
            label_pos = max(our_t, ref_t) + 0.05 if not np.isnan(our_t) else ref_t + 0.05
            ax_timeline.text(label_pos, y_val, f"Δ: {int(diff):+d} 毫秒", va='center', ha='left', fontsize=9, color=txt_color, fontweight='bold')

    # 7. 特別標註：攤還期 (垂直陰影)
    our_amort_start = our_events.get("攤還期開始", {}).get("Frame", -1)
    our_amort_end = our_events.get("攤還期結束", {}).get("Frame", -1)
    if our_amort_start >= 0 and our_amort_end >= 0:
        t_start = our_amort_start / fs
        t_end = our_amort_end / fs
        ax_curve.axvspan(t_start, t_end, color='#F1C40F', alpha=0.1, zorder=1)
        ax_timeline.axvspan(t_start, t_end, color='#F1C40F', alpha=0.1, zorder=1)
        ax_curve.text((t_start + t_end)/2, bw*0.2, "攤還期", color='#D68910', fontsize=10, fontweight='bold', ha='center')

    # 8. 建立精緻圖例與說明文字
    # 說明文字方塊：簡介不同曲線算法 (中文字不要放在 LaTeX $ 內以避免字型警告)
    props = dict(boxstyle='round,pad=0.4', facecolor='#FDFEFE', edgecolor='#BDC3C7', alpha=0.9)
    formula_intro = (
        "【曲線計算公式簡介】\n"
        "• 力量 (Force): 雙側力板加總 $F = F_1 + F_2$。濾波採 Butterworth 20Hz。\n"
        "• 速度 (Velocity): 加速度 $a = (F_{filtered} - BW)/m$ 的數值積分，以 SoM 點歸零校正。\n"
        "• 位移 (Displacement): 對速度再次進行數值積分，代表重心相對於起跳前之位移。\n"
        "• 功率 (Power): 原始力乘以速度 $P = F_{raw} \times V$。"
    )
    # 在上方大圖的左下角放置這個文字框
    ax_curve.text(0.01, 0.03, formula_intro, transform=ax_curve.transAxes, fontsize=9, verticalalignment='bottom', bbox=props)
    
    # 圖例
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color='#2C3E50', lw=2, label='力量 (Force, N)'),
        Line2D([0], [0], color='#2980B9', lw=2, label='速度 × 500 (Velocity, m/s)'),
        Line2D([0], [0], color='#8E44AD', lw=2, label='位移 × 3000 (Displacement, m)'),
        Line2D([0], [0], color='#27AE60', lw=1.5, label='功率 × 0.5 (Power, W)'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='none', markeredgecolor='blue', markersize=9, label='我們程式 (o)'),
        Line2D([0], [0], marker='x', color='w', markeredgecolor='red', markersize=10, markeredgewidth=2, label='對照組 (x)'),
    ]
    ax_curve.legend(handles=legend_elements, loc='upper right', framealpha=0.9, shadow=True, fontsize=9)
    
    # 軸設定
    ax_timeline.set_xlabel("時間 (秒, seconds)", fontsize=11, fontweight='bold')
    
    plt.tight_layout()
    
    # 9. 存檔與顯示
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, f"{trial_id}_comparison.png")
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"成功儲存三線疊加對比圖: {save_path}")
    else:
        plt.show()
        
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用說明:")
        print("  python scratch/plot_jump_events.py <trial_id>   (例: python scratch/plot_jump_events.py 001-1)")
        print("  python scratch/plot_jump_events.py all          (批次繪製並儲存所有對比圖)")
        sys.exit(1)
        
    target = sys.argv[1]
    
    if target.lower() == "all":
        ref_dir = "refer_results/final"
        files = sorted(os.listdir(ref_dir))
        excluded_files = {"002-1.xlsx", "002-2.xlsx", "002-3.xlsx"}
        clean_files = [f.replace(".xlsx", "") for f in files if f.endswith('.xlsx') and f not in excluded_files]
        
        plot_dir = "outputs/plots"
        print(f"開始批次繪製 {len(clean_files)} 個運動學對比圖，儲存至 {plot_dir}...")
        
        success_count = 0
        for trial in clean_files:
            if plot_jump_stacked_timeline(trial, save_dir=plot_dir):
                success_count += 1
                
        print(f"批次繪製完成！成功: {success_count}/{len(clean_files)}")
    else:
        print(f"開始繪製 Trial: {target} ...")
        plot_jump_stacked_timeline(target, save_dir="outputs/plots")
        print("圖片已儲存至 outputs/plots 目錄，請點擊查看。")
