import os
import glob
import pandas as pd
import numpy as np

def get_max_force_plate_data(player_id, directory, target_metrics=['跳躍高度', '推蹬發力率']):
    """
    從指定資料夾中讀取該球員的所有跳躍 Excel 檔，並提取指定指標的最高值。
    """
    files = glob.glob(os.path.join(directory, f"{player_id}-*.xlsx"))
    max_data = {m: np.nan for m in target_metrics}
    
    for f in files:
        try:
            df = pd.read_excel(f, sheet_name=1, header=None)
            row_header = df.iloc[1].tolist()
            
            for metric in target_metrics:
                if metric in row_header:
                    col_idx = row_header.index(metric)
                    val = float(df.iloc[2, col_idx])
                    if np.isnan(max_data[metric]) or val > max_data[metric]:
                        max_data[metric] = val
        except:
            pass
    return max_data

def process_blast_swings(file_path):
    """
    讀取 Blast Swings CSV 檔並計算每位球員的最大揮棒速度。
    """
    try:
        df = pd.read_csv(file_path)
        # 過濾掉非數字的球員編號（如「打好玩」）
        df = df[pd.to_numeric(df['球員編號'], errors='coerce').notna()].copy()
        df['Player_ID'] = df['球員編號'].astype(int).apply(lambda x: f"{x:03d}")
        df['Swing_Speed'] = pd.to_numeric(df['Swing Speed (mph)'], errors='coerce')
        agg = df.groupby('Player_ID')['Swing_Speed'].max().reset_index()
        return agg
    except Exception as e:
        print(f"Error processing Blast data: {e}")
        return pd.DataFrame()
