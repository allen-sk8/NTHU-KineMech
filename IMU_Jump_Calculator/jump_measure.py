import os
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import cumulative_trapezoid
from scipy.signal import butter, filtfilt
import sys

# 根據目前腳本所在位置動態取得絕對路徑，確保不論在哪裡點擊執行都不出錯
base_dir = os.path.dirname(os.path.abspath(__file__))

# 設定 DTW 模組路徑 (假設 dtw 模組已被放入相對路徑的資料夾中)
dtw_module_path = os.path.join(base_dir, "dtw")
if dtw_module_path not in sys.path:
    sys.path.append(dtw_module_path)

try:
    from dtw import dtw
except ImportError:
    print("找不到 dtw 模組。請確認 'dtw' 資料夾是否有一起打包至 imotek_jump_measure 目錄下。")
    sys.exit(1)

# --- Step 1 functions: 座標轉換 ---
def quaternion_multiply(q1, q2):
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return np.array([
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2
    ])

def quaternion_inverse(q):
    w, x, y, z = q
    return np.array([w, -x, -y, -z]) / np.linalg.norm(q)**2

def sensor_to_earth(quat, acc):
    acc_quat = np.array([0] + list(acc))
    earth_acc = quaternion_multiply(
        quaternion_multiply(quat, acc_quat),
        quaternion_inverse(quat)
    )
    return earth_acc[1:]

# --- Step 2 functions: 濾波 ---
def butter_filter(data, cutoff, fs, filter_type, order=5):
    nyquist = 0.5 * fs
    normal_cutoff = cutoff / nyquist
    b, a = butter(order, normal_cutoff, btype=filter_type, analog=False)
    data = np.ravel(np.array(data))
    return filtfilt(b, a, data)

# --- Step 3 functions: 跳躍檢測 ---
def load_standard_velocity(file_path):
    data = pd.read_csv(file_path)
    return np.array(data['Velocity_Z'])

def sliding_window_dtw_with_manhattan_filter(standard, target, window_size, manhattan_threshold):
    distance_list = []
    manhattan_distance_list = []
    # 使用一個較大但有限的數值代表無效區間，避免 np.diff(inf) 產生 RuntimeWarning (inf - inf = nan)
    MAX_VAL = 1e6
    
    for start_idx in range(len(target) - window_size + 1):
        sub_target = target[start_idx:start_idx + window_size]
        manhattan_distance = np.sum(np.abs(standard - sub_target))
        manhattan_distance_list.append(manhattan_distance)
        if manhattan_distance > manhattan_threshold:
            distance_list.append(MAX_VAL)
            continue
        max_velocity = np.max(sub_target)
        if max_velocity <= 2:
            distance_list.append(MAX_VAL)
            continue
        distance, _, _, _ = dtw(standard, sub_target, dist=lambda x, y: np.abs(x - y))
        distance_list.append(distance)
    return distance_list, manhattan_distance_list

def find_local_minima(distance_list):
    gradient = np.diff(distance_list)
    local_minima_indices = np.where((gradient[:-1] < 0) & (gradient[1:] > 0))[0] + 1
    return local_minima_indices

def filter_close_indices_by_is_jump(indices, is_jump_values, threshold=20):
    filtered_indices = []
    filtered_is_jump_values = []
    for i, index in enumerate(indices):
        if not filtered_indices or index - filtered_indices[-1] > threshold:
            filtered_indices.append(index)
            filtered_is_jump_values.append(is_jump_values[i])
    return filtered_indices, filtered_is_jump_values

def jump_duration_detection(index, velocity_z, standard_velocity_z):
    window_start = max(0, index - 10)
    window_end = min(len(velocity_z), index + len(standard_velocity_z) + 10)
    
    # 1. 先找起跳點 (最大向上速度)
    take_off_relative_idx = np.argmax(velocity_z[window_start:window_end])
    take_off_index = window_start + take_off_relative_idx
    
    # 2. 限制落地點 (找尋起跳點之後的最大向下速度)
    if take_off_relative_idx + 1 < (window_end - window_start):
        landing_relative_idx = np.argmin(velocity_z[take_off_index:window_end])
        landing_index = take_off_index + landing_relative_idx
    else:
        landing_index = take_off_index
        
    return take_off_index, landing_index

# --- Main process function ---
def process_jump_file(input_csv_path, output_folder, standard_velocity_path):
    print(f"正在處理: {os.path.basename(input_csv_path)}")
    # 建立該檔案專屬的資料夾
    os.makedirs(output_folder, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(input_csv_path))[0]

    # 讀取檔案
    with open(input_csv_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    start_line = next(i for i, line in enumerate(lines) if "PacketCounter" in line)
    data = pd.read_csv(input_csv_path, skiprows=start_line)
    data.columns = [col.strip() for col in data.columns]

    # Step 1: 轉換到地球座標系並計算自由加速度
    acc_data = data[["Acc_X", "Acc_Y", "Acc_Z"]].to_numpy()
    quat_data = data[["Quat_W", "Quat_X", "Quat_Y", "Quat_Z"]].to_numpy()
    earth_acc_data = np.array([sensor_to_earth(quat, acc) for quat, acc in zip(quat_data, acc_data)])
    free_acc_data = earth_acc_data - np.array([0, 0, 9.905768264261473])
    free_acc_z = free_acc_data[:, 2]

    # Step 2: 濾波參數設定
    sampling_rate = 60
    lowpass_cutoff = 25
    highpass_cutoffs = [0.4, 0.5, 0.6]
    
    free_acc_z_lowpass = butter_filter(free_acc_z, lowpass_cutoff, sampling_rate, "low")
    time_arr = np.linspace(0, len(free_acc_z) / sampling_rate, len(free_acc_z), endpoint=False)
    velocity_z = cumulative_trapezoid(free_acc_z_lowpass, time_arr, initial=0)

    standard_velocity = load_standard_velocity(standard_velocity_path)
    
    jump_records = {} # 以 jump_index 為 key 整理同一跳的不同參數結果
    plot_data = {}
    g = 9.81

    # 針對每一種 highpass_cutoff 分別進行處理
    for hp_cutoff in highpass_cutoffs:
        velocity_z_filtered = butter_filter(velocity_z, hp_cutoff, sampling_rate, "high")
        displacement_z = cumulative_trapezoid(velocity_z_filtered, time_arr, initial=0)

        # Step 3: DTW 跳躍檢測
        distance_list, manhattan_distance_list = sliding_window_dtw_with_manhattan_filter(standard_velocity, velocity_z_filtered, len(standard_velocity), 80)
        local_minima_indices = find_local_minima(distance_list)
        local_minima_values = np.array(distance_list)[local_minima_indices]
        filtered_indices, filtered_is_jump_values = filter_close_indices_by_is_jump(local_minima_indices, local_minima_values)

        jumps = [(jump_duration_detection(idx, velocity_z_filtered, standard_velocity)) for idx in filtered_indices]

        # 儲存繪圖所需資訊
        plot_data[hp_cutoff] = {
            'velocity_z_filtered': velocity_z_filtered,
            'displacement_z': displacement_z,
            'distance_list': distance_list,
            'manhattan_distance_list': manhattan_distance_list,
            'local_minima_indices': local_minima_indices,
            'local_minima_values': local_minima_values,
            'filtered_indices': filtered_indices,
            'filtered_is_jump_values': filtered_is_jump_values,
            'jumps': jumps
        }

        # 計算高度
        for i, (take_off, landing) in enumerate(jumps):
            jump_idx = i + 1
            if jump_idx not in jump_records:
                jump_records[jump_idx] = {
                    "jump_index": jump_idx,
                    "timestamp": float(time_arr[take_off]),
                    "take_off_frame": int(take_off),
                    "landing_frame": int(landing)
                }
            
            if landing > take_off:
                disp_max = np.max(displacement_z[take_off:landing+1])
                disp_height = float(disp_max - displacement_z[take_off])
            else:
                disp_height = 0.0

            flight_time = float(time_arr[landing] - time_arr[take_off])
            if flight_time > 0:
                time_height = float((g * (flight_time ** 2)) / 8)
            else:
                time_height = 0.0

            jump_records[jump_idx][f"flight_time_{hp_cutoff}Hz"] = flight_time
            jump_records[jump_idx][f"height_by_disp_{hp_cutoff}Hz"] = disp_height
            jump_records[jump_idx][f"height_by_time_{hp_cutoff}Hz"] = time_height

    # 將整理好的字典轉換成列表
    jump_results = list(jump_records.values())

    # --- 繪製並儲存圖表 ---
    plot_displacement_path = os.path.join(output_folder, f"{base_name}_displacement_comparison.png")

    # (1) 輸出包含各種頻率的總和比較圖 (加速度/速度/位移)
    plt.figure(figsize=(15, 12))
    plt.subplot(3, 1, 1)
    plt.plot(time_arr, free_acc_z, label="Original Acceleration (Z)", linestyle="--", alpha=0.5)
    plt.plot(time_arr, free_acc_z_lowpass, label=f"Low-pass ({lowpass_cutoff} Hz)", linestyle="-")
    plt.title("Acceleration")
    plt.xlabel("Time (s)")
    plt.ylabel("Acceleration (m/s²)")
    plt.legend(loc='upper right')
    plt.grid()

    plt.subplot(3, 1, 2)
    plt.plot(time_arr, velocity_z, label="Original Velocity (Z) (Before High-pass)", linestyle="--", alpha=0.5)
    for hp_cutoff in highpass_cutoffs:
        plt.plot(time_arr, plot_data[hp_cutoff]['velocity_z_filtered'], label=f"Filtered Vel (HP={hp_cutoff} Hz)", linestyle="-")
    plt.title("Velocity Comparison")
    plt.xlabel("Time (s)")
    plt.ylabel("Velocity (m/s)")
    plt.legend(loc='upper right')
    plt.grid()

    plt.subplot(3, 1, 3)
    for hp_cutoff in highpass_cutoffs:
        plt.plot(time_arr, plot_data[hp_cutoff]['displacement_z'], label=f"Displacement (HP={hp_cutoff} Hz)", linestyle="-")
    plt.title("Displacement Comparison")
    plt.xlabel("Time (s)")
    plt.ylabel("Displacement (m)")
    plt.legend(loc='upper right')
    plt.grid()

    plt.tight_layout()
    plt.savefig(plot_displacement_path, dpi=300)
    plt.close()

    # (2) 替每種 filter 分別輸出 DTW 分析報表
    for hp_cutoff in highpass_cutoffs:
        data = plot_data[hp_cutoff]
        plot_dtw_path = os.path.join(output_folder, f"{base_name}_dtw_jumps_{hp_cutoff}Hz.png")
        
        plt.figure(figsize=(15, 12))
        plt.subplot(2, 1, 1)
        plt.plot(range(len(data['distance_list'])), data['distance_list'], label="DTW Distance", linestyle='-', marker='o', markersize=2, color='gray')
        plt.plot(range(len(data['manhattan_distance_list'])), data['manhattan_distance_list'], label="Manhattan Distance", linestyle='--', color='orange')
        plt.scatter(data['local_minima_indices'], data['local_minima_values'], color='red', label="Local Minima", marker='x')
        plt.scatter(data['filtered_indices'], [data['distance_list'][i] for i in data['filtered_indices']], color='blue', label="Filtered Jump Points", marker='*', s=100)
        
        for index, is_jump in zip(data['filtered_indices'], data['filtered_is_jump_values']):
            plt.text(index, data['distance_list'][index] + 0.1, f"{is_jump:.2f}", fontsize=12, ha='center', color='blue')

        plt.xlabel("Sliding Window Start Index")
        plt.ylabel("Distance Values")
        plt.title(f"DTW & Manhattan Distance (High-pass = {hp_cutoff} Hz)")
        plt.legend()
        plt.grid()

        plt.subplot(2, 1, 2)
        plt.plot(time_arr, data['velocity_z_filtered'], label=f"Velocity (Z) (HP={hp_cutoff}Hz)", linestyle="--", color='orange')
        plt.plot(time_arr, data['displacement_z'], label=f"Displacement (Z) (HP={hp_cutoff}Hz)", linestyle="-", color='green')

        if data['jumps']:
            for take_off, landing in data['jumps']:
                plt.axvspan(time_arr[take_off], time_arr[landing], color="lightblue", alpha=0.3, label="Jump" if take_off == data['jumps'][0][0] else "")

        plt.title(f"Jump Detection Results (High-pass = {hp_cutoff} Hz)")
        plt.xlabel("Time (s)")
        plt.ylabel("Values")
        plt.legend()
        plt.grid()

        plt.tight_layout()
        plt.savefig(plot_dtw_path, dpi=300)
        plt.close()

    # 輸出成 CSV 檔案
    output_csv_path = os.path.join(output_folder, f"{base_name}_jump_heights.csv")
    df = pd.DataFrame(jump_results)
    # 使用 utf-8-sig 以保證用 Excel 打開時不會有亂碼
    df.to_csv(output_csv_path, index=False, encoding='utf-8-sig')
    print(f"[{base_name}] 處理完成！產出結果: {output_folder}")

if __name__ == "__main__":
    # 使用相對的目錄抓取資料夾
    input_dir = os.path.join(base_dir, "input")
    output_dir = os.path.join(base_dir, "output")
    standard_vel_path = os.path.join(base_dir, "align_std", "standard_data.csv")

    if not os.path.exists(input_dir):
        print(f"請在同一個資料夾底下建立 input 目錄，並放入要處理的 CSV 檔: {input_dir}")
        sys.exit(1)

    if not os.path.exists(standard_vel_path):
        print(f"找不到 standard_data.csv 模板檔案！請確認: {standard_vel_path}")
        sys.exit(1)

    csv_files = glob.glob(os.path.join(input_dir, "*.csv"))
    if not csv_files:
        print(f"在 {input_dir} 找不到任何 CSV 檔案。")
        sys.exit(1)

    # 遍歷 input 資料夾內所有的 CSV 檔
    for file_path in csv_files:
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        # 建立同名的 output 資料夾 (例: output\E_D422CD00699B_20241202_125848)
        file_output_dir = os.path.join(output_dir, base_name)
        
        try:
            process_jump_file(file_path, file_output_dir, standard_vel_path)
        except StopIteration:
            print(f"[{base_name}] 檔案格式可能不正確 (找不到 PacketCounter)")
        except Exception as e:
            print(f"[{base_name}] 處理檔案時發生錯誤: {e}")
