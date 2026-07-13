import os
import sys
import time
import shutil
import threading
import webbrowser
import json
import urllib.parse
from http.server import SimpleHTTPRequestHandler, HTTPServer
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np

# 嘗試載入 watchdog 套件，若未安裝則自動在背景進行安裝
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError:
    print("偵測到未安裝 watchdog 套件，正在自動為您安裝...")
    os.system(f'"{sys.executable}" -m pip install watchdog')
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

import matplotlib
matplotlib.use('Agg')

def plot_force_and_power_separate(trial_id, force_series, extra_curves, config, save_dir):
    """
    額外繪製兩張供 HTML 報表使用的簡明關係圖：
    1. 力量-時間圖 (Force-Time)
    2. 功率-時間圖 (Power-Time)
    不包含下半部的時間軸子圖，更簡潔大氣。
    """
    import matplotlib.pyplot as plt
    import numpy as np
    
    plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'Segoe UI', 'Arial']
    plt.rcParams['axes.unicode_minus'] = False
    
    filtered_force = extra_curves.get("filtered_force", force_series)
    power_curve = extra_curves.get("power_curve", np.zeros_like(force_series))
    events_map = extra_curves.get("events_map", {})
    bw = extra_curves.get("bw", None)
    
    fs = config.fs
    time_sec = np.arange(len(force_series)) / fs
    
    # 1. 繪製力量圖
    fig1, ax1 = plt.subplots(figsize=(8, 4))
    ax1.plot(time_sec, force_series, color='#2C3E50', alpha=0.25, label='原始力量 (Raw Force)')
    ax1.plot(time_sec, filtered_force, color='#1E3D59', linewidth=2.5, label='濾波力量 (Filtered Force)')
    if bw is not None:
        ax1.axhline(bw, color='#E74C3C', linestyle='--', linewidth=1.5, label=f'體重線 (BW: {bw:.1f} N)')
        
    # 標註事件點 (垂直線與點)
    colors_dict = {
        "Start": "#1ABC9C", "Unweight": "#E67E22", "Unweight_Peak": "#D35400", 
        "Braking": "#3498DB", "Propulsive": "#9B59B6", "Flight": "#E74C3C", 
        "Peak": "#27AE60", "Landing": "#F1C40F", "End": "#7F8C8D",
        "Jump_Start": "#1ABC9C", "Take_off": "#E74C3C", "Landing_Start": "#F1C40F"
    }
    for event_name, frame in events_map.items():
        if frame is not None and not np.isnan(frame) and 0 <= int(frame) < len(time_sec):
            t_val = time_sec[int(frame)]
            f_val = filtered_force[int(frame)]
            color = colors_dict.get(event_name, "#7F8C8D")
            ax1.axvline(t_val, color=color, linestyle=':', alpha=0.8, linewidth=1.5)
            ax1.scatter(t_val, f_val, color=color, s=60, zorder=5)
            # 在圖上標示事件英文
            ax1.annotate(event_name, (t_val, f_val), textcoords="offset points", 
                         xytext=(4,4), ha='left', fontsize=8, fontweight='bold',
                         bbox=dict(boxstyle="round,pad=0.2", fc="yellow", alpha=0.25))
            
    ax1.set_title(f"力量-時間關係圖 (Force-Time)", fontsize=11, fontweight='bold', pad=8)
    ax1.set_xlabel("時間 (s)", fontsize=9)
    ax1.set_ylabel("力量 (N)", fontsize=9)
    ax1.grid(True, linestyle='--', alpha=0.5)
    ax1.legend(loc='upper right', fontsize=8, framealpha=0.8)
    plt.tight_layout()
    force_path = os.path.join(save_dir, f"{trial_id}_force.png")
    fig1.savefig(force_path, dpi=120)
    plt.close(fig1)
    
    # 2. 繪製功率圖
    fig2, ax2 = plt.subplots(figsize=(8, 4))
    ax2.plot(time_sec, power_curve, color='#27AE60', linewidth=2.5, label='機械功率 (Power)')
    
    # 標註功率圖中的事件點
    for event_name, frame in events_map.items():
        if frame is not None and not np.isnan(frame) and 0 <= int(frame) < len(time_sec):
            t_val = time_sec[int(frame)]
            p_val = power_curve[int(frame)]
            color = colors_dict.get(event_name, "#7F8C8D")
            ax2.axvline(t_val, color=color, linestyle=':', alpha=0.8, linewidth=1.5)
            ax2.scatter(t_val, p_val, color=color, s=60, zorder=5)
            ax2.annotate(event_name, (t_val, p_val), textcoords="offset points", 
                         xytext=(4,4), ha='left', fontsize=8, fontweight='bold',
                         bbox=dict(boxstyle="round,pad=0.2", fc="yellow", alpha=0.25))
            
    ax2.set_title(f"功率-時間關係圖 (Power-Time)", fontsize=11, fontweight='bold', pad=8)
    ax2.set_xlabel("時間 (s)", fontsize=9)
    ax2.set_ylabel("功率 (W)", fontsize=9)
    ax2.grid(True, linestyle='--', alpha=0.5)
    ax2.legend(loc='upper right', fontsize=8, framealpha=0.8)
    plt.tight_layout()
    power_path = os.path.join(save_dir, f"{trial_id}_power.png")
    fig2.savefig(power_path, dpi=120)
    plt.close(fig2)

# 匯入現有的運算與分析模組（完全不修改原模組程式碼）
from convert_cap_to_csv import convert_cap_to_csv
import analyze_cmj
import analyze_sj
from metrics_calculator import calculate_advanced_metrics, calculate_sj_metrics

# 強制將目前工作目錄切換至本腳本所在資料夾，確保所有相對路徑（如 inputs, outputs, 參考對照數據）均正確鎖定
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

# ==========================================
# 全域狀態管理與組態設定
# ==========================================
class MonitorState:
    def __init__(self):
        self.latest_html = ""          # 最新生成的報表 HTML
        self.latest_image_path = ""    # 最新診斷圖的實體檔案路徑
        self.has_new_update = False    # 是否有新分析結果（用於通知網頁重整）
        self.latest_update_time = 0.0  # 最新更新時間戳記 (強固輪詢防丟失)
        self.lock = threading.RLock()
        self.log_messages = []         # 即時日誌訊息

    def update_result(self, html_content, image_path):
        with self.lock:
            self.latest_html = html_content
            self.latest_image_path = image_path
            self.latest_update_time = time.time()
            self.has_new_update = True
            self.add_log("成功更新即時報表與 PDF")

    def add_log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        with self.lock:
            self.log_messages.append(log_entry)
            if len(self.log_messages) > 100:
                self.log_messages.pop(0)

STATE = MonitorState()

# 設定 Edge 的安裝路徑以供 PDF 轉存使用
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if not os.path.exists(EDGE_PATH):
    # 若找不到預設路徑，嘗試使用系統 PATH 中的 msedge
    EDGE_PATH = "msedge"

# ==========================================
# 檔名解析與基本資料防呆提取
# ==========================================
def parse_subject_info_from_filename(filename, default_weight=None):
    """
    從檔名解析受試者基本資料，格式：姓名_性別_年齡_身高_體重.cap
    若格式不符（例如純編號），則只保留姓名/編號，其餘個人資訊（性別、身高、年齡）設為 None/'-'，
    體重保留給後續從力板力量數據中自動算出。
    """
    base_name = os.path.splitext(filename)[0]
    parts = base_name.split('_')
    
    # 預設值 (略過立板測不到的個人資訊)
    info = {
        "name": base_name,
        "gender": "-",
        "age": None,
        "height": None,
        "weight": default_weight
    }
    
    if len(parts) >= 5:
        try:
            info["name"] = parts[0]
            # 性別轉換防呆
            gender_part = parts[1]
            if gender_part in ["女", "女性", "F", "f"]:
                info["gender"] = "女性"
            elif gender_part in ["男", "男性", "M", "m"]:
                info["gender"] = "男性"
            else:
                info["gender"] = gender_part
                
            info["age"] = float(parts[2])
            
            # 身高判定 (公尺或公分相容)
            h_val = float(parts[3])
            if h_val > 3.0:
                info["height"] = h_val / 100.0 # 若輸入如 168 則轉為 1.68
            else:
                info["height"] = h_val
                
            info["weight"] = float(parts[4])
        except Exception as e:
            STATE.add_log(f"解析檔名基本資料發生微小錯誤: {e}，改用部分預設值。")
            
    return info

# ==========================================
# HTML 報表模板渲染器
# ==========================================
def render_report_html(action_type, info, metrics_df, image_name, num_runs=None, best_run_num=None):
    """
    依據運動科學同學現有報表版面 (張華臻-1 / 張丞葳-1)，以 HTML + CSS 渲染精美報表
    """
    title = "ProGRF-CMJ 下肢動態肌力檢測報表" if action_type == "cmj" else "ProGRF-SJ 下肢動態肌力檢測報表"
    
    # 根據 image_name 推導力量圖與功率圖的相對路徑檔名
    base_img_name = image_name.replace("_comparison.png", "")
    force_img_name = f"{base_img_name}_force.png"
    power_img_name = f"{base_img_name}_power.png"
    
    # 判斷是否為綜合平均報表，是的話在表格尾端多一行「量測次數」
    avg_row_html = ""
    if num_runs is not None and best_run_num is not None:
        title = f"ProGRF-{'CMJ' if action_type == 'cmj' else 'SJ'} 下肢動態肌力檢測報表 (綜合平均)"
        avg_row_html = f"""
        <tr><td>量測次數</td><td>{num_runs} 次 (最佳: Run {best_run_num})</td></tr>
        """

    # 將 DataFrame 資料結構轉為更易讀的字典
    metrics = {}
    for col in metrics_df.columns:
        metrics[col] = {
            "raw": metrics_df.iloc[0][col],
            "std": metrics_df.iloc[1][col]
        }

    # 針對數值進行 Null/NaN 的格式化處理
    def fmt(val, is_pct=False):
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return "-"
        if is_pct:
            return f"{val:.2f}%" if isinstance(val, (int, float)) else str(val)
        return f"{val:.2f}" if isinstance(val, (int, float)) else str(val)

    # 格式化基本資料，若無資料則顯示 "-" 略過
    gender_str = info.get('gender', '-')
    if not gender_str:
        gender_str = "-"
        
    age_val = info.get('age')
    age_str = f"{age_val:.1f}" if isinstance(age_val, (int, float)) and not np.isnan(age_val) else "-"
    
    height_val = info.get('height')
    height_str = f"{height_val:.2f} m" if isinstance(height_val, (int, float)) and not np.isnan(height_val) else "-"
    
    weight_val = info.get('weight')
    weight_str = f"{weight_val:.2f} kg" if isinstance(weight_val, (int, float)) and not np.isnan(weight_val) else "-"

    if action_type == "cmj":
        # CMJ HTML 結構
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>
        @page {{
            size: A4;
            margin: 15mm 15mm 15mm 15mm;
        }}
        body {{
            font-family: 'Segoe UI', 'SF Pro Display', 'Microsoft JhengHei', sans-serif;
            margin: 0;
            padding: 0;
            background-color: #ffffff;
            color: #1e293b;
        }}
        .container {{
            width: 100%;
            max-width: 800px;
            margin: 0 auto;
        }}
        h1 {{
            text-align: center;
            font-size: 24px;
            color: #0f172a;
            margin-top: 5px;
            margin-bottom: 25px;
            font-weight: 700;
            letter-spacing: 0.5px;
            border-bottom: 3px solid #3b82f6;
            display: inline-block;
            padding-bottom: 8px;
            width: 100%;
        }}
        .flex-row {{
            display: flex;
            gap: 20px;
            margin-bottom: 15px;
        }}
        .basic-info-box {{
            width: 28%;
            flex-shrink: 0;
        }}
        .metrics-tables-box {{
            flex-grow: 1;
            width: 72%;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 16px;
            font-size: 11.5px;
            background-color: #ffffff;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
            border-radius: 6px;
            overflow: hidden;
        }}
        th, td {{
            border: 1px solid #cbd5e1;
            text-align: center;
            padding: 8px 6px;
        }}
        th {{
            background-color: #1e3d59; /* 高雅深靛藍 */
            color: #ffffff;
            font-weight: 600;
            font-size: 13px;
            letter-spacing: 0.5px;
        }}
        .sub-header {{
            background-color: #f1f5f9; /* 輕薄灰底 */
            color: #334155;
            font-weight: 600;
        }}
        .info-table td {{
            padding: 8px 10px;
        }}
        .info-table td:first-child {{
            background-color: #f8fafc;
            color: #475569;
            font-weight: 500;
            width: 45%;
        }}
        .info-table td strong {{
            color: #0f172a;
        }}
        .chart-flex-row {{
            display: flex;
            gap: 15px;
            margin-top: 15px;
            width: 100%;
        }}
        .chart-sub-box {{
            flex: 1;
            border: 1px solid #cbd5e1;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.04);
            background-color: #ffffff;
        }}
        .chart-sub-box img {{
            width: 100%;
            height: auto;
            display: block;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        
        <div class="flex-row">
            <!-- 左側受試者基本資料 -->
            <div class="basic-info-box">
                <table class="info-table">
                    <tr><th colspan="2">受試者基本資料</th></tr>
                    <tr><td>姓名/編號</td><td><strong>{info['name']}</strong></td></tr>
                    <tr><td>性別</td><td>{gender_str}</td></tr>
                    <tr><td>年齡</td><td>{age_str}</td></tr>
                    <tr><td>身高</td><td>{height_str}</td></tr>
                    <tr><td>體重</td><td>{weight_str}</td></tr>
                    {avg_row_html}
                </table>
                
                <table class="info-table" style="margin-top: 15px;">
                    <tr><th colspan="2">總衝量</th></tr>
                    <tr><td class="sub-header">評估指標</td><td class="sub-header">衝量</td></tr>
                    <tr><td>原始</td><td>{fmt(metrics['衝量']['raw'])}</td></tr>
                    <tr><td>標準化</td><td>{fmt(metrics['衝量']['std'])}</td></tr>
                </table>
            </div>
            
            <!-- 右側特徵報表區 -->
            <div class="metrics-tables-box">
                <!-- 動作時宜與下肢勁度特徵報表 -->
                <table>
                    <tr><th colspan="7">動作時宜與下肢勁度特徵報表</th></tr>
                    <tr class="sub-header">
                        <td></td><td>下蹲期時間</td><td>制動期時間</td><td>推蹬期時間</td><td>攤還期時間</td><td>總動作時間</td><td>下肢勁度</td>
                    </tr>
                    <tr>
                        <td>原始</td>
                        <td>{fmt(metrics['下蹲期時間']['raw'])}</td>
                        <td>{fmt(metrics['制動期時間']['raw'])}</td>
                        <td>{fmt(metrics['推蹬期時間']['raw'])}</td>
                        <td>{fmt(metrics['攤還期時間']['raw'])}</td>
                        <td>{fmt(metrics['總動作時間']['raw'])}</td>
                        <td>{fmt(metrics['下肢勁度']['raw'])}</td>
                    </tr>
                    <tr>
                        <td>%標準化</td>
                        <td>{fmt(metrics['下蹲期時間']['std'], True)}</td>
                        <td>{fmt(metrics['制動期時間']['std'], True)}</td>
                        <td>{fmt(metrics['推蹬期時間']['std'], True)}</td>
                        <td>{fmt(metrics['攤還期時間']['std'], True)}</td>
                        <td>{fmt(metrics['總動作時間']['std'], True)}</td>
                        <td>{fmt(metrics['下肢勁度']['std'])}</td>
                    </tr>
                </table>

                <!-- 下肢動態肌力特徵報表 -->
                <table>
                    <tr><th colspan="7">下肢動態肌力特徵報表</th></tr>
                    <tr class="sub-header">
                        <td></td><td>跳躍高度</td><td>推蹬力峰值</td><td>推蹬發力率</td><td>反應力指數</td><td>向心功率峰值</td><td>向心做功量</td>
                    </tr>
                    <tr>
                        <td>原始</td>
                        <td>{fmt(metrics['跳躍高度']['raw'])}</td>
                        <td>{fmt(metrics['推蹬力峰值']['raw'])}</td>
                        <td>{fmt(metrics['推蹬發力率']['raw'])}</td>
                        <td>{fmt(metrics['反應力指數']['raw'])}</td>
                        <td>{fmt(metrics['向心功率峰值']['raw'])}</td>
                        <td>{fmt(metrics['向心做功量']['raw'])}</td>
                    </tr>
                    <tr>
                        <td>%標準化</td>
                        <td>{fmt(metrics['跳躍高度']['std'])}</td>
                        <td>{fmt(metrics['推蹬力峰值']['std'])}</td>
                        <td>{fmt(metrics['推蹬發力率']['std'])}</td>
                        <td>{fmt(metrics['反應力指數']['std'])}</td>
                        <td>{fmt(metrics['向心功率峰值']['std'])}</td>
                        <td>{fmt(metrics['向心做功量']['std'])}</td>
                    </tr>
                </table>

                <!-- 離心牽張肌力特徵報表 -->
                <table>
                    <tr><th colspan="7">離心牽張肌力特徵報表</th></tr>
                    <tr class="sub-header">
                        <td></td><td>下蹲力峰值</td><td>下蹲發力率</td><td>制動末力值</td><td>制動發力率</td><td>離心功率峰值</td><td>離心做功量</td>
                    </tr>
                    <tr>
                        <td>原始</td>
                        <td>{fmt(metrics['下蹲力峰值']['raw'])}</td>
                        <td>{fmt(metrics['下蹲發力率']['raw'])}</td>
                        <td>{fmt(metrics['制動末力值']['raw'])}</td>
                        <td>{fmt(metrics['制動發力率']['raw'])}</td>
                        <td>{fmt(metrics['離心功率峰值']['raw'])}</td>
                        <td>{fmt(metrics['離心做功量']['raw'])}</td>
                    </tr>
                    <tr>
                        <td>%標準化</td>
                        <td>{fmt(metrics['下蹲力峰值']['std'])}</td>
                        <td>{fmt(metrics['下蹲發力率']['std'])}</td>
                        <td>{fmt(metrics['制動末力值']['std'])}</td>
                        <td>{fmt(metrics['制動發力率']['std'])}</td>
                        <td>{fmt(metrics['離心功率峰值']['std'])}</td>
                        <td>{fmt(metrics['離心做功量']['std'])}</td>
                    </tr>
                </table>
            </div>
        </div>

        <!-- 下方物理診斷圖表 (力量與功率並排) -->
        <div class="chart-flex-row">
            <div class="chart-sub-box">
                <img src="{force_img_name}" alt="力量-時間關係圖">
            </div>
            <div class="chart-sub-box">
                <img src="{power_img_name}" alt="功率-時間關係圖">
            </div>
        </div>
    </div>
</body>
</html>"""
    else:
        # SJ HTML 結構
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>
        @page {{
            size: A4;
            margin: 15mm 15mm 15mm 15mm;
        }}
        body {{
            font-family: 'Segoe UI', 'SF Pro Display', 'Microsoft JhengHei', sans-serif;
            margin: 0;
            padding: 0;
            background-color: #ffffff;
            color: #1e293b;
        }}
        .container {{
            width: 100%;
            max-width: 800px;
            margin: 0 auto;
        }}
        h1 {{
            text-align: center;
            font-size: 24px;
            color: #0f172a;
            margin-top: 5px;
            margin-bottom: 25px;
            font-weight: 700;
            letter-spacing: 0.5px;
            border-bottom: 3px solid #3b82f6;
            display: inline-block;
            padding-bottom: 8px;
            width: 100%;
        }}
        .flex-row {{
            display: flex;
            gap: 20px;
            margin-bottom: 15px;
        }}
        .basic-info-box {{
            width: 28%;
            flex-shrink: 0;
        }}
        .metrics-tables-box {{
            flex-grow: 1;
            width: 72%;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 16px;
            font-size: 11.5px;
            background-color: #ffffff;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
            border-radius: 6px;
            overflow: hidden;
        }}
        th, td {{
            border: 1px solid #cbd5e1;
            text-align: center;
            padding: 8px 6px;
        }}
        th {{
            background-color: #1e3d59; /* 高雅深靛藍 */
            color: #ffffff;
            font-weight: 600;
            font-size: 13px;
            letter-spacing: 0.5px;
        }}
        .sub-header {{
            background-color: #f1f5f9; /* 輕薄灰底 */
            color: #334155;
            font-weight: 600;
        }}
        .info-table td {{
            padding: 8px 10px;
        }}
        .info-table td:first-child {{
            background-color: #f8fafc;
            color: #475569;
            font-weight: 500;
            width: 45%;
        }}
        .info-table td strong {{
            color: #0f172a;
        }}
        .chart-flex-row {{
            display: flex;
            gap: 15px;
            margin-top: 15px;
            width: 100%;
        }}
        .chart-sub-box {{
            flex: 1;
            border: 1px solid #cbd5e1;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.04);
            background-color: #ffffff;
        }}
        .chart-sub-box img {{
            width: 100%;
            height: auto;
            display: block;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        
        <div class="flex-row">
            <!-- 左側受試者基本資料 -->
            <div class="basic-info-box">
                <table class="info-table">
                    <tr><th colspan="2">受試者基本資料</th></tr>
                    <tr><td>姓名/編號</td><td><strong>{info['name']}</strong></td></tr>
                    <tr><td>性別</td><td>{gender_str}</td></tr>
                    <tr><td>年齡</td><td>{age_str}</td></tr>
                    <tr><td>身高</td><td>{height_str}</td></tr>
                    <tr><td>體重</td><td>{weight_str}</td></tr>
                    {avg_row_html}
                </table>
                
                <table class="info-table" style="margin-top: 15px;">
                    <tr><th colspan="3">總衝量與總動作時間</th></tr>
                    <tr class="sub-header"><td>評估指標</td><td>衝量</td><td>動作時間</td></tr>
                    <tr><td>原始</td><td>{fmt(metrics['衝量']['raw'])}</td><td>{fmt(metrics['總動作時間']['raw'])}</td></tr>
                    <tr><td>標準化</td><td>{fmt(metrics['衝量']['std'])}</td><td>{fmt(metrics['總動作時間']['std'], True)}</td></tr>
                </table>
            </div>
            
            <!-- 右側特徵報表區 -->
            <div class="metrics-tables-box">
                <!-- 下肢動態肌力特徵報表 -->
                <table>
                    <tr><th colspan="7">下肢動態肌力特徵報表</th></tr>
                    <tr class="sub-header">
                        <td></td><td>跳躍高度</td><td>推蹬力峰值</td><td>推蹬發力率</td><td>反應力指數</td><td>向心功率峰值</td><td>向心做功量</td>
                    </tr>
                    <tr>
                        <td>原始</td>
                        <td>{fmt(metrics['跳躍高度']['raw'])}</td>
                        <td>{fmt(metrics['推蹬力峰值']['raw'])}</td>
                        <td>{fmt(metrics['推蹬發力率']['raw'])}</td>
                        <td>{fmt(metrics['反應力指數']['raw'])}</td>
                        <td>{fmt(metrics['向心功率峰值']['raw'])}</td>
                        <td>{fmt(metrics['向心做功量']['raw'])}</td>
                    </tr>
                    <tr>
                        <td>%標準化</td>
                        <td>{fmt(metrics['跳躍高度']['std'])}</td>
                        <td>{fmt(metrics['推蹬力峰值']['std'])}</td>
                        <td>{fmt(metrics['推蹬發力率']['std'])}</td>
                        <td>{fmt(metrics['反應力指數']['std'])}</td>
                        <td>{fmt(metrics['向心功率峰值']['std'])}</td>
                        <td>{fmt(metrics['向心做功量']['std'])}</td>
                    </tr>
                </table>
            </div>
        </div>

        <!-- 下方物理診斷圖表 (力量與功率並排) -->
        <div class="chart-flex-row">
            <div class="chart-sub-box">
                <img src="{force_img_name}" alt="力量-時間關係圖">
            </div>
            <div class="chart-sub-box">
                <img src="{power_img_name}" alt="功率-時間關係圖">
            </div>
        </div>
    </div>
</body>
</html>"""

    return html_content

# ==========================================
# 檔案寫入與防鎖定等待機制
# ==========================================
def wait_for_file_to_be_ready(file_path, timeout=5.0):
    """
    Windows 下檔案可能被寫入鎖定，需輪詢直到檔案完全寫入完成。
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # 嘗試以讀寫模式開啟，若成功代表鎖定已解除
            with open(file_path, 'r+b'):
                return True
        except IOError:
            time.sleep(0.2)
    return False

# ==========================================
# 單一檔案處理核心邏輯 (支援遍歷該 cap 底下 3 筆跳躍)
# ==========================================
def process_new_cap_file(cap_path):
    """
    即時檔案分析流程：
    1. 轉換 .cap ➡️ CSV，防重複移入 outputs
    2. 使用與原本 analyze_cmj / analyze_sj 相同的底層物理計算產生成果
    3. 遍歷分析所有 Run (每 2 欄為一個 Run，通常 3 個 Run)
    4. 渲染各 Run 的 HTML 報表檔並轉存向量 PDF
    5. 更新 Web State (以最後一個成功分析的 Run 為主，即 Run 3)
    """
    STATE.add_log(f"開始處理新檔案: {cap_path}")
    
    # 1. 解析路徑與決定動作類型
    normalized_path = cap_path.replace('\\', '/')
    path_parts = normalized_path.split('/')
    
    action_type = None
    if "cmj" in path_parts:
        action_type = "cmj"
    elif "sj" in path_parts:
        action_type = "sj"
        
    if not action_type:
        STATE.add_log("警告: 無法由檔案路徑判定動作類型，跳過處理。")
        return

    # 取得專案名稱與檔名
    filename = os.path.basename(normalized_path)
    file_id = os.path.splitext(filename)[0]
    
    # 專案名稱 (inputs/cmj/專案名稱/檔名.cap)
    try:
        inputs_idx = path_parts.index("inputs")
        project_name = path_parts[inputs_idx + 2]
    except Exception:
        project_name = "未命名專案"

    # 2. 準備輸出目標資料夾 (例如 outputs/cmj/自動報表測試/001/)
    subject_dir = os.path.join("outputs", action_type, project_name, file_id)
    os.makedirs(subject_dir, exist_ok=True)
    
    csv_output_path = os.path.join(subject_dir, f"{file_id}.csv")
    
    # 執行轉 CSV (這是一段既有邏輯的封裝呼叫)
    try:
        convert_cap_to_csv(cap_path, csv_output_path)
    except Exception as e:
        STATE.add_log(f"轉換 CSV 發生錯誤: {e}")
        return

    # 自動移動原始檔到輸出目錄以防重複轉換
    target_cap_path = os.path.join(subject_dir, filename)
    try:
        if os.path.exists(target_cap_path):
            os.remove(target_cap_path)
        shutil.move(cap_path, target_cap_path)
        STATE.add_log(f"原始檔案已移動至: {target_cap_path}")
    except Exception as e:
        STATE.add_log(f"移動檔案失敗: {e}")

    # 3. 讀取 CSV 並執行物理計算與繪圖
    try:
        df = pd.read_csv(csv_output_path)
    except Exception as e:
        STATE.add_log(f"讀取 CSV 失敗: {e}")
        return

    # 計算總共包含幾個 Run (每 2 欄為一個 Run，例如 3 個跳躍共有 6 欄)
    num_runs = len(df.columns) // 2
    if num_runs == 0:
        STATE.add_log("警告: CSV 欄位不足，無法進行分析。")
        return

    STATE.add_log(f"偵測到檔案包含 {num_runs} 次跳躍 (Runs)，開始依序分析...")

    # 用以收集所有成功 Run 的計算結果，以進行後續平均與最佳表現篩選
    metrics_list = []
    plots_list = []
    infos_list = []
    heights_list = []
    trial_ids_list = []

    # 進行基本資料檔名提取 (立板測不到個人資訊就略過，只在檔名解析失敗時給予預設值)
    info = parse_subject_info_from_filename(filename, default_weight=None)

    # 遍歷分析所有的 Run
    for r in range(1, num_runs + 1):
        trial_id = f"{file_id}-{r}"
        excel_path = os.path.join(subject_dir, f"{trial_id}.xlsx")
        plot_path = os.path.join(subject_dir, f"{trial_id}_comparison.png")
        
        f1 = df.iloc[:, (r-1)*2]
        f2 = df.iloc[:, (r-1)*2+1]
        total_f = (f1 + f2).dropna().values
        
        if len(total_f) < 1000:
            STATE.add_log(f"Run {r} 力量點數過少，跳過。")
            continue

        try:
            # 建立這個 Run 的基本資料複本，以防相互干擾
            run_info = info.copy()

            if action_type == "cmj":
                # CMJ 計算與畫圖
                config = analyze_cmj.JumpAnalysisConfig()
                res, extra_curves = analyze_cmj.process_single_run(total_f, config)
                
                # 從力量數據提取精確體重 (如果檔名中未指定，則實測算出的體重覆蓋)
                calculated_weight = round(extra_curves["bw"] / 9.81, 2)
                if run_info["weight"] is None:
                    run_info["weight"] = calculated_weight
                
                res.columns = res.iloc[0]
                res_output = res.drop(res.index[0])
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
                    
                metrics_df = calculate_advanced_metrics(
                    event_vals=event_vals,
                    force_series=total_f,
                    p_series=extra_curves["power_curve"],
                    bw=extra_curves["bw"],
                    fs=config.fs,
                    height=run_info["height"] * 100.0 if run_info["height"] else np.nan, # 轉公分
                    age=run_info["age"] if run_info["age"] else np.nan
                )
                
                # 寫入 Excel
                with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                    res_output.to_excel(writer, sheet_name="Details", index=False)
                    metrics_df.to_excel(writer, sheet_name="CMJ", index=False)
                analyze_cmj.format_cmj_sheet(excel_path)
                
                # 繪製診斷圖
                analyze_cmj.plot_jump_events_integrated(trial_id, total_f, extra_curves, config, plot_path)
                plot_force_and_power_separate(trial_id, total_f, extra_curves, config, subject_dir)
                
            else:
                # SJ 計算與畫圖
                config = analyze_sj.JumpAnalysisConfig()
                res, extra_curves = analyze_sj.process_single_run(total_f, config)
                
                # 從力量數據提取精確體重
                calculated_weight = round(extra_curves["bw"] / 9.81, 2)
                if run_info["weight"] is None:
                    run_info["weight"] = calculated_weight

                res.columns = res.iloc[0]
                res_output = res.drop(res.index[0])
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
                    
                metrics_df = calculate_sj_metrics(
                    event_vals=event_vals,
                    force_series=total_f,
                    p_series=extra_curves["power_curve"],
                    bw=extra_curves["bw"],
                    fs=config.fs,
                    height=run_info["height"] * 100.0 if run_info["height"] else np.nan, # 轉公分
                    age=run_info["age"] if run_info["age"] else np.nan
                )
                
                # 寫入 Excel
                with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                    res_output.to_excel(writer, sheet_name="Details", index=False)
                    metrics_df.to_excel(writer, sheet_name="SJ", index=False)
                analyze_sj.format_sj_sheet(excel_path)
                
                # 繪製診斷圖
                analyze_sj.plot_jump_events_integrated(trial_id, total_f, extra_curves, config, plot_path)
                plot_force_and_power_separate(trial_id, total_f, extra_curves, config, subject_dir)
                
            # 生成該 Run 的 HTML / PDF 報表 (此為單一 Run 的獨立存檔)
            html_filename = f"{trial_id}_report.html"
            pdf_filename = f"{trial_id}_report.pdf"
            html_path = os.path.join(subject_dir, html_filename)
            pdf_path = os.path.join(subject_dir, pdf_filename)
            
            html_content = render_report_html(action_type, run_info, metrics_df, f"{trial_id}_comparison.png")
            
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
                
            # 執行 Edge headless 將 HTML 轉存為向量 PDF (改用 subprocess 避免 Windows 空格路徑引號解析 bug)
            abs_html_path = os.path.abspath(html_path)
            abs_pdf_path = os.path.abspath(pdf_path)
            import subprocess
            subprocess.run([
                EDGE_PATH, 
                "--headless", 
                "--disable-gpu", 
                f"--print-to-pdf={abs_pdf_path}", 
                f"file:///{abs_html_path}"
            ])
            STATE.add_log(f"Run {r} 向量 PDF 已儲存: {pdf_path}")

            # 暫存為列表，以供後續計算平均與最優值
            metrics_list.append(metrics_df)
            plots_list.append(plot_path)
            infos_list.append(run_info)
            trial_ids_list.append(trial_id)
            
            # 提取跳躍高度以進行最佳表現排序
            h_val = metrics_df.iloc[0]["跳躍高度"]
            heights_list.append(h_val if isinstance(h_val, (int, float)) and not np.isnan(h_val) else 0.0)
            
        except Exception as e:
            import traceback
            STATE.add_log(f"分析 Run {r} 時發生非預期錯誤: {e}")
            traceback.print_exc()

    # 所有 Run 分析完畢後，計算綜合平均報表
    try:
        if len(metrics_list) > 0:
            # 1. 建立一個與原 metrics_df 同樣結構的 DataFrame
            avg_metrics_df = metrics_list[0].copy()
            for col in avg_metrics_df.columns:
                try:
                    raw_vals = [float(m.iloc[0][col]) for m in metrics_list if col in m.columns and not pd.isna(m.iloc[0][col])]
                    std_vals = [float(m.iloc[1][col]) for m in metrics_list if col in m.columns and not pd.isna(m.iloc[1][col])]
                    avg_metrics_df.iloc[0, avg_metrics_df.columns.get_loc(col)] = np.mean(raw_vals) if raw_vals else np.nan
                    avg_metrics_df.iloc[1, avg_metrics_df.columns.get_loc(col)] = np.mean(std_vals) if std_vals else np.nan
                except (ValueError, TypeError):
                    # 若無法轉為浮點數（例如文字欄位 Event），則直接使用第一個 Run 的文字值，不予平均
                    avg_metrics_df.iloc[0, avg_metrics_df.columns.get_loc(col)] = metrics_list[0].iloc[0][col]
                    avg_metrics_df.iloc[1, avg_metrics_df.columns.get_loc(col)] = metrics_list[0].iloc[1][col]

            # 2. 找出跳躍高度最高的 Run 索引 (作為圖表選用)
            best_idx = int(np.argmax(heights_list))
            best_run_num = best_idx + 1
            best_plot_path = plots_list[best_idx]
            best_trial_id = trial_ids_list[best_idx]
            
            # 3. 計算平均體重
            avg_info = infos_list[0].copy()
            weights = [info["weight"] for info in infos_list if info["weight"] is not None]
            avg_info["weight"] = np.mean(weights) if weights else None

            # 4. 產生綜合報告的 HTML 和 PDF 檔案
            summary_html_filename = f"{file_id}_summary_report.html"
            summary_pdf_filename = f"{file_id}_summary_report.pdf"
            summary_html_path = os.path.join(subject_dir, summary_html_filename)
            summary_pdf_path = os.path.join(subject_dir, summary_pdf_filename)
            
            # 綜合 HTML 引用最佳表現 Run 的對應曲線圖檔名
            best_plot_filename = f"{best_trial_id}_comparison.png"
            
            summary_html_content = render_report_html(
                action_type, 
                avg_info, 
                avg_metrics_df, 
                best_plot_filename, 
                num_runs=len(metrics_list), 
                best_run_num=best_run_num
            )
            
            with open(summary_html_path, 'w', encoding='utf-8') as f:
                f.write(summary_html_content)
                
            # 執行 Edge headless 將綜合 HTML 轉存為向量 PDF (改用 subprocess 避免 Windows 空格路徑引號解析 bug)
            abs_html_path = os.path.abspath(summary_html_path)
            abs_pdf_path = os.path.abspath(summary_pdf_path)
            import subprocess
            subprocess.run([
                EDGE_PATH, 
                "--headless", 
                "--disable-gpu", 
                f"--print-to-pdf={abs_pdf_path}", 
                f"file:///{abs_html_path}"
            ])
            
            STATE.add_log(f"已產出綜合平均 PDF 報表並儲存至: {summary_pdf_path}")
            
            # 5. 更新本地 Web 狀態以同步彈出綜合平均報表 (圖片帶入 Web 虛擬路徑 /image 配合最佳圖檔實體路徑)
            web_html = render_report_html(
                action_type, 
                avg_info, 
                avg_metrics_df, 
                "/image", 
                num_runs=len(metrics_list), 
                best_run_num=best_run_num
            )
            STATE.update_result(web_html, best_plot_path)
            
            # 主動呼叫 webbrowser 彈出或聚焦瀏覽器視窗至最前台
            try:
                def open_browser():
                    webbrowser.open("http://localhost:5000")
                threading.Thread(target=open_browser, daemon=True).start()
            except Exception as e:
                STATE.add_log(f"嘗試彈出瀏覽器失敗: {e}")
                
            STATE.add_log(f"檔案 {filename} 分析完成，彈窗已自動同步更新為綜合平均報表 (最佳表現 Run {best_run_num})")
    except Exception as e:
        import traceback
        STATE.add_log(f"計算綜合平均報表時發生錯誤: {e}")
        traceback.print_exc()

# ==========================================
# 檔案監控 Handler
# ==========================================
class PascoFileHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        
        file_path = event.src_path
        if file_path.endswith('.cap'):
            STATE.add_log(f"檢測到新檔案: {file_path}")
            # 等待檔案解除寫入鎖定
            if wait_for_file_to_be_ready(file_path):
                # 啟動背景執行緒來處理，避免阻塞監控主線程
                t = threading.Thread(target=process_new_cap_file, args=(file_path,))
                t.start()
            else:
                STATE.add_log(f"錯誤: 檔案 {file_path} 寫入超時，跳過處理。")

# ==========================================
# 本地極簡 Web 伺服器
# ==========================================
class ReportHTTPHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        # 覆蓋以防控制台被 GET 請求刷屏
        pass

    def do_GET(self):
        url_parts = urllib.parse.urlparse(self.path)
        
        # 1. 狀態查詢 API (AJAX 輪詢)
        if url_parts.path == "/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            # 強制禁止瀏覽器快取狀態 API
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.end_headers()
            
            with STATE.lock:
                response = {
                    "reload": STATE.has_new_update,
                    "update_time": STATE.latest_update_time
                }
                STATE.has_new_update = False
                
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        # 2. 獲取診斷圖表圖檔
        elif url_parts.path == "/image":
            image_path = ""
            with STATE.lock:
                image_path = STATE.latest_image_path
                
            if image_path and os.path.exists(image_path):
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.end_headers()
                with open(image_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "Chart Not Found")
                
        # 3. 獲取日誌列表 API
        elif url_parts.path == "/logs":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            # 強制禁止瀏覽器快取日誌 API
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.end_headers()
            with STATE.lock:
                self.wfile.write(json.dumps({"logs": STATE.log_messages}).encode('utf-8'))
                
        # 4. 主報表頁面與歡迎頁面
        elif url_parts.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            # 強制禁止瀏覽器快取 HTML 網頁
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.end_headers()
            
            html_to_serve = ""
            with STATE.lock:
                html_to_serve = STATE.latest_html
                
            if not html_to_serve:
                # 歡迎引導頁面
                html_to_serve = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>PASCO 力板即時監控系統</title>
    <style>
        body {
            font-family: 'Segoe UI', 'Microsoft JhengHei', sans-serif;
            background-color: #2c3e50;
            color: #ecf0f1;
            margin: 0;
            padding: 50px;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 80vh;
        }
        .welcome-card {
            background-color: #34495e;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            max-width: 600px;
            width: 100%;
        }
        h1 {
            color: #e67e22;
            margin-top: 0;
            border-bottom: 2px solid #e67e22;
            padding-bottom: 10px;
        }
        .status-badge {
            background-color: #2ecc71;
            color: white;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 14px;
            display: inline-block;
            margin-bottom: 20px;
        }
        ol {
            padding-left: 20px;
            line-height: 1.8;
        }
        .log-box {
            background-color: #1a252f;
            border-radius: 4px;
            padding: 15px;
            height: 150px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 12px;
            color: #2ecc71;
            margin-top: 20px;
        }
    </style>
    <script>
        let currentUpdateTime = null;
        // 每秒檢查一次是否有新數據分析完成
        setInterval(function() {
            // 加入時間戳記避免瀏覽器快取
            fetch('/status?t=' + Date.now())
                .then(response => response.json())
                .then(data => {
                    // 如果是第一次載入，先記錄最新更新時間
                    if (currentUpdateTime === null) {
                        currentUpdateTime = data.update_time;
                        return;
                    }
                    // 如果後端有新的更新時間，且不等於當前記錄的時間
                    if (data.update_time > 0 && data.update_time !== currentUpdateTime) {
                        window.location.href = window.location.pathname + '?t=' + Date.now();
                    }
                });
            
            // 同時更新背景日誌
            fetch('/logs?t=' + Date.now())
                .then(response => response.json())
                .then(data => {
                    const logBox = document.getElementById('log-box');
                    if (logBox) {
                        logBox.innerHTML = data.logs.join('<br>');
                        logBox.scrollTop = logBox.scrollHeight;
                    }
                });
        }, 1000);
    </script>
</head>
<body>
    <div class="welcome-card">
        <h1>PASCO 力板即時監控系統已啟動</h1>
        <div class="status-badge">● 正在背景監控 inputs/ 目錄...</div>
        <p><strong>使用說明：</strong></p>
        <ol>
            <li>在 <code>inputs/cmj/</code> 或 <code>inputs/sj/</code> 下建立專案資料夾（例如：<code>關西棒球檢測</code>）。</li>
            <li>將 PASCO 產出的 <code>.cap</code> 檔案存檔至該資料夾。</li>
            <li><strong>推薦檔名格式：</strong><code>姓名_性別_年齡_身高_體重.cap</code>（例如：<code>張華臻_女_13.6_1.68_44.72.cap</code>）以自動提取受試者資訊。</li>
            <li>分析將會自動完成，此網頁會<strong>無感重整</strong>並顯示精美報表與自動儲存 PDF！</li>
        </ol>
        <div id="log-box" class="log-box">正在等待新量測數據...</div>
    </div>
</body>
</html>"""
            # 插入通用輪詢更新腳本，即使在報表畫面也保持自動更新
            if "window.location.reload()" not in html_to_serve:
                inject_script = """
                <script>
                    let currentUpdateTime = null;
                    setInterval(function() {
                        fetch('/status?t=' + Date.now())
                            .then(response => response.json())
                            .then(data => {
                                if (currentUpdateTime === null) {
                                    currentUpdateTime = data.update_time;
                                    return;
                                }
                                if (data.update_time > 0 && data.update_time !== currentUpdateTime) {
                                    window.location.href = window.location.pathname + '?t=' + Date.now();
                                }
                            });
                    }, 1000);
                </script>
                """
                if "</body>" in html_to_serve:
                    html_to_serve = html_to_serve.replace("</body>", inject_script + "</body>")
                else:
                    html_to_serve += inject_script
                    
            self.wfile.write(html_to_serve.encode('utf-8'))
            
        else:
            self.send_error(404, "Page Not Found")

def run_web_server():
    server_address = ('', 5000)
    httpd = HTTPServer(server_address, ReportHTTPHandler)
    STATE.add_log("本地 Web 伺服器已在 http://localhost:5000 啟動")
    httpd.serve_forever()

def scan_existing_files():
    """
    啟動時掃描 inputs/ 目錄下是否殘留未處理之 .cap 歷史檔案，
    避免「先放檔案再啟動程式」或「重啟後檔案無反應」的問題。
    """
    STATE.add_log("正在掃描 inputs/ 目錄下是否存在尚未處理的歷史檔案...")
    has_files = False
    for root, dirs, files in os.walk("inputs"):
        for file in files:
            if file.endswith('.cap'):
                cap_path = os.path.join(root, file)
                STATE.add_log(f"發現未處理檔案: {cap_path}，正在進行背景補處理...")
                has_files = True
                # 直接進行分析與移動
                process_new_cap_file(cap_path)
    if not has_files:
        STATE.add_log("未發現任何殘存檔案，即時監控準備就緒。")

# ==========================================
# 主程式進入點
# ==========================================
def main():
    print("==================================================")
    print("       PASCO 力板即時監控與自動分析系統           ")
    print("==================================================")
    
    # 確保 inputs 目錄結構存在
    os.makedirs("inputs/cmj", exist_ok=True)
    os.makedirs("inputs/sj", exist_ok=True)
    os.makedirs("outputs", exist_ok=True)

    # 1. 啟動背景 Web 伺服器
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()

    # 2. 自動在預設瀏覽器（Edge / Chrome）中開啟報表頁面
    time.sleep(1.0)
    threading.Thread(target=lambda: webbrowser.open("http://localhost:5000"), daemon=True).start()

    # 2.5 掃描並處理已存在的歷史檔案
    scan_existing_files()

    # 3. 設置並啟動 Watchdog 監控
    event_handler = PascoFileHandler()
    observer = Observer()
    # 遞迴監控 inputs/ 資料夾變動
    observer.schedule(event_handler, path='inputs', recursive=True)
    observer.start()
    STATE.add_log("資料夾監控已啟動，正在監控 inputs/ 目錄...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        STATE.add_log("正在停止監控...")
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()
