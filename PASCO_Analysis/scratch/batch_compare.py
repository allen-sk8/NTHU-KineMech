import pandas as pd
import os
import numpy as np

def batch_compare(count=20):
    output_dir = 'outputs/final'
    ref_dir = 'refer_results/final'
    
    # 獲取共同檔案列表
    ref_files = sorted([f for f in os.listdir(ref_dir) if f.endswith('.xlsx')])
    
    comparisons = []
    processed_count = 0
    
    for f in ref_files:
        p_mine = os.path.join(output_dir, f)
        p_ref = os.path.join(ref_dir, f)
        
        if os.path.exists(p_mine):
            try:
                d_mine = pd.read_excel(p_mine).set_index('Event')
                d_ref = pd.read_excel(p_ref).set_index('Event')
                
                # 找出共同事件
                common_events = d_mine.index.intersection(d_ref.index)
                if len(common_events) == 0: continue
                
                d_m = d_mine.loc[common_events]
                d_r = d_ref.loc[common_events]
                
                # 確保數值型
                d_m = d_m.apply(pd.to_numeric, errors='coerce')
                d_r = d_r.apply(pd.to_numeric, errors='coerce')
                
                diff = (d_m - d_r).abs()
                comparisons.append(diff.mean())
                processed_count += 1
                
                if processed_count >= count:
                    break
            except Exception as e:
                print(f"處理 {f} 失敗: {e}")
                
    if not comparisons:
        print("沒有找到可比對的檔案")
        return
        
    summary_df = pd.DataFrame(comparisons)
    mae = summary_df.mean()
    std = summary_df.std()
    
    print(f"=== 已成功比對 {processed_count} 個樣本 ===")
    print("\n平均絕對誤差 (MAE):")
    print(mae.to_string())
    print("\n誤差標準差 (STD):")
    print(std.to_string())
    
    # 詳細分項分析
    print("\n--- 詳細分項 (各檔案平均誤差) ---")
    summary_df.index = ref_files[:processed_count]
    print(summary_df.to_string())

if __name__ == "__main__":
    batch_compare(20)
