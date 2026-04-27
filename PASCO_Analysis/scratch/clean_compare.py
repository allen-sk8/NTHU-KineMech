import pandas as pd
import os
import numpy as np

output_dir = 'outputs/final'
ref_dir = 'refer_results/final'
files = sorted([f for f in os.listdir(ref_dir) if f.endswith('.xlsx')])[:20]
maes = []
for f in files:
    p1 = os.path.join(output_dir, f)
    p2 = os.path.join(ref_dir, f)
    if os.path.exists(p1):
        d1 = pd.read_excel(p1).set_index('Event')
        d2 = pd.read_excel(p2).set_index('Event')
        common = d1.index.intersection(d2.index)
        diff = (d1.loc[common].apply(pd.to_numeric, errors='coerce') - d2.loc[common].apply(pd.to_numeric, errors='coerce')).abs()
        maes.append(diff.mean(axis=0))

res = pd.DataFrame(maes).mean()
print("MAE Analysis (N=20)")
print("-" * 30)
print(res.to_string())
