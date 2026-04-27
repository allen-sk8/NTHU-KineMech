import pandas as pd
import numpy as np

def compare(f1, f2):
    try:
        d1 = pd.read_csv(f1)
        d2 = pd.read_csv(f2)
        # Use np.allclose for float comparison to handle precision issues, 
        # though equals() should work if formatting is identical.
        if d1.shape != d2.shape:
            print(f"Shape mismatch: {f1} {d1.shape} vs {f2} {d2.shape}")
            return False
        # Compare columns
        if list(d1.columns) != list(d2.columns):
            print(f"Column mismatch: {list(d1.columns)} vs {list(d2.columns)}")
            return False
        # Compare values (handling NaNs)
        return np.allclose(d1.fillna(0), d2.fillna(0), atol=1e-2)
    except Exception as e:
        print(f"Error comparing {f1} and {f2}: {e}")
        return False

for i in ['002', '003', '004']:
    match = compare(f'outputs/{i}.csv', f'refer_results/{i}.csv')
    print(f'{i} match: {match}')
