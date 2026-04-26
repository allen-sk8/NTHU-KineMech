"""
運動表現分析主入口：
使用 CMJ RFD (發力協調) & SJ Height (基礎肌力) vs 揮棒速度
"""

import os
import pandas as pd
import numpy as np
from utils.data_processor import get_max_force_plate_data, process_blast_swings
from utils.visualizer import create_interactive_3d_report

# --- 設定路徑 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CMJ_DIR = os.path.join(BASE_DIR, "force_plate", "20260325", "cmj")
SJ_DIR = os.path.join(BASE_DIR, "force_plate", "20260325", "sj") 
BLAST_FILE = os.path.join(BASE_DIR, "blast", "20260325", "blast_baseball_swings.csv")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

print("1. 正在同步力板 (SJ/CMJ) 與揮棒數據...")
# 處理揮棒數據
df_blast = process_blast_swings(BLAST_FILE)

# 處理力板數據
player_ids = df_blast['Player_ID'].unique().tolist()
final_data = []

for pid in player_ids:
    # 提取 CMJ 的最高 RFD (代表神經徵召/發力協調)
    cmj_data = get_max_force_plate_data(pid, CMJ_DIR, target_metrics=['推蹬發力率'])
    # 提取 SJ 的最高跳高 (代表基礎肌肉絕對肌力)
    sj_data = get_max_force_plate_data(pid, SJ_DIR, target_metrics=['跳躍高度'])
    
    final_data.append({
        'Player_ID': pid,
        'CMJ_Max_RFD': cmj_data['推蹬發力率'],
        'SJ_Max_Height': sj_data['跳躍高度']
    })

df_fp = pd.DataFrame(final_data)
# 合併數據
df_final = pd.merge(df_blast, df_fp, on='Player_ID', how='inner').dropna()

# 重新命名欄位以便繪製圖表
df_final.rename(columns={
    'Swing_Speed': 'Max_Swing_Speed_mph',
}, inplace=True)

print(f"   同步成功球員人數: {len(df_final)}")

if len(df_final) == 0:
    print("錯誤：未能找到匹配的球員數據，請檢查資料夾路徑與檔案命名格式。")
else:
    print("2. 進行多變量統計建模與生成 3D 專業報告...")
    output_html = os.path.join(OUTPUT_DIR, "performance_RFD_SJ_Swing.html")

    title_text = "專業表現診斷地圖：SJ絕對肌力與CMJ發力率之轉化效能"

    model, df_results = create_interactive_3d_report(
        df_final,
        x_col='CMJ_Max_RFD',
        y_col='SJ_Max_Height',
        z_col='Max_Swing_Speed_mph',
        x_label='CMJ 推蹬發力率 (N/s)',
        y_label='SJ 跳躍高度 (m)',
        z_label='揮棒速度 (mph)',
        title=title_text,
        output_path=output_html
    )

    # 儲存 Excel 結果報表
    output_excel = os.path.join(OUTPUT_DIR, "final_analysis_report.xlsx")
    df_results.to_excel(output_excel, index=False)

    print(f"3. 分析完成！")
    print(f"   [Excel 報表]: {output_excel}")
    print(f"   [互動式 3D]: {output_html}")
