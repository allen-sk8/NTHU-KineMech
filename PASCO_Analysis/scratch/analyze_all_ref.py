import os
import pandas as pd
import numpy as np

def main():
    excel_dir = r"c:\Users\allensk8\vscode-all-in-one\Local_workspace\NTHU-KineMech\PASCO_Analysis\refer_results\sj\SJ Excel"
    if not os.path.exists(excel_dir):
        print("Directory does not exist")
        return
        
    files = sorted([f for f in os.listdir(excel_dir) if f.endswith('.xlsx')])
    
    results = []
    
    for f in files:
        path = os.path.join(excel_dir, f)
        try:
            xl = pd.ExcelFile(path)
            # Details sheet
            df_details = xl.parse("Details").set_index("Event")
            
            # SJ sheet
            df_sj = xl.parse("SJ")
            # 獲取體重
            bw_kg = float(df_sj.iloc[1, 2]) # 原始體重公斤
            
            som_frame = float(df_details.loc["Frame", "動作開始"])
            peak_frame = float(df_details.loc["Frame", "最大推蹬力"])
            takeoff_frame = float(df_details.loc["Frame", "離地瞬間"])
            landing_frame = float(df_details.loc["Frame", "著地瞬間"])
            
            som_f = float(df_details.loc["F-value (N)", "動作開始"])
            peak_f = float(df_details.loc["F-value (N)", "最大推蹬力"])
            takeoff_f = float(df_details.loc["F-value (N)", "離地瞬間"])
            
            results.append({
                "File": f,
                "BW (kg)": bw_kg,
                "BW (N)": bw_kg * 9.81,
                "SoM_Frame": som_frame,
                "Peak_Frame": peak_frame,
                "Takeoff_Frame": takeoff_frame,
                "Landing_Frame": landing_frame,
                "SoM_F_net": som_f,
                "Peak_F_net": peak_f,
                "Takeoff_F_net": takeoff_f,
                "SoM_F_ratio": som_f / (bw_kg * 9.81)
            })
        except Exception as e:
            print(f"Error reading {f}: {e}")
            
    df_res = pd.DataFrame(results)
    print(df_res.to_string(index=False))
    
    # 算一下平均 SoM_F_ratio
    print(f"\nAverage SoM F_net: {df_res['SoM_F_net'].mean():.2f} N")
    print(f"Average SoM F_ratio: {df_res['SoM_F_ratio'].mean()*100:.3f}% BW")

if __name__ == "__main__":
    main()
