import pandas as pd

# 讀取 001-1 的對照組數據
df_ref = pd.read_excel("refer_results/final/001-1.xlsx").set_index("Event")

print("對照組 001-1 數據：")
print(df_ref.to_string())

print("\n--- 檢查公式關係 ---")
for event in df_ref.columns:
    f_val = df_ref.loc["F-value (N)", event]
    v_val = df_ref.loc["V-value (m/s)", event]
    p_val = df_ref.loc["P-value (W)", event]
    
    # 測試計算功率的方式
    p_calc_net = f_val * v_val
    # 如果 F-value 是淨力，那麼總力是 F_val + 體重
    # 在 001-1 中，體重約為 733.34 N
    bw = 733.34
    p_calc_total = (f_val + bw) * v_val
    
    print(f"[{event}]")
    print(f"  Ref P-value = {p_val:.2f}")
    print(f"  F * V (淨力) = {p_calc_net:.2f} (誤差: {p_calc_net - p_val:.2f})")
    print(f"  (F + BW) * V (總力) = {p_calc_total:.2f} (誤差: {p_calc_total - p_val:.2f})")
