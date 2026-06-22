import pandas as pd

f_ref1 = pd.read_excel("refer_results/final/001-1.xlsx")
f_ref2 = pd.read_excel("refer_results/final/002-1.xlsx")

try:
    diff = (f_ref1 == f_ref2).all().all()
    print("001-1.xlsx 和 002-1.xlsx 的內容是否完全相同:", diff)
except Exception as e:
    print("比較時發生錯誤:", e)
