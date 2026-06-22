import pandas as pd

f1 = pd.read_csv("outputs/force/001.csv")
f2 = pd.read_csv("outputs/force/002.csv")

print("001.csv columns:", list(f1.columns))
print("002.csv columns:", list(f2.columns))

# 檢查數據內容是否相同
if f1.shape == f2.shape:
    diff = (f1 - f2).abs().max().max()
    print(f"兩者形狀相同，最大絕對差值為: {diff}")
else:
    print(f"兩者形狀不同: 001.csv 是 {f1.shape}, 002.csv 是 {f2.shape}")
