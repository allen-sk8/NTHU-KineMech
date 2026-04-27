import numpy as np
import matplotlib.pyplot as plt
from dtw import dtw
import pandas as pd
import os
path_to_data = "/home/allen/dtw/sens_data"
output_path = "/home/allen/dtw/runs/output.png"
f1 = "logfile_20241018_1638_D4-22-CD-00-69-6A"
f2 = "logfile_20241018_1639_D4-22-CD-00-69-6A"

path_to_f1 = os.path.join(path_to_data,f"{f1}.csv")
path_to_f2 = os.path.join(path_to_data,f"{f2}.csv")
df1 = pd.read_csv(path_to_f1, skiprows=1)
df2 = pd.read_csv(path_to_f2, skiprows=1)

# 定義數列 x 和 y
x = df1['FreeAcc_Z'].to_numpy().reshape(-1, 1)
y = df2['FreeAcc_Z'].to_numpy().reshape(-1, 1)
x = x[::2]  # 每隔 5 個點取一個
y = y[::2]
# 曼哈頓距離函數
manhattan_distance = lambda x, y: np.abs(x - y)

window_size = 30  # 這個數值可以根據數據調整
d, cost_matrix, acc_cost_matrix, path = dtw(x, y, dist=manhattan_distance, w=window_size)
print(d)
# 畫出兩個序列的折線圖
plt.figure(figsize=(15, 6))  # 寬度設置為15，高度設置為6
plt.plot(x+10, label="vec1", color='blue', marker='o', markersize=2)  # 序列 x 的折線圖
plt.plot(y, label="vec2", color='black', marker='o', markersize=2) # 序列 y 的折線圖

# 繪製 DTW 對應的路徑
for (map_x, map_y) in zip(path[0], path[1]):
    plt.plot([map_x, map_y], [x[map_x]+10, y[map_y]], color='red', linewidth = 0.5)  # 用紅線連接對應點

# 添加圖例和標題
plt.title('DTW alignment')
plt.legend()
plt.grid()

plt.savefig(output_path)
