import zipfile
import xml.etree.ElementTree as ET
import struct
import os
import pandas as pd
import numpy as np

# 感測器 EUID 到名稱的動態映射 (會自動在執行時建立)
EUID_TO_NAME = {}

def get_plate_label(euid):
    """根據 EUID 獲取穩定標籤 (Plate 01, 02...)"""
    if euid not in EUID_TO_NAME:
        # 分配下一個可用的號碼
        next_num = len(EUID_TO_NAME) + 1
        EUID_TO_NAME[euid] = f"Plate {next_num:02d}"
    return EUID_TO_NAME[euid]

def parse_binary_data(z, filename, count):
    """解析 12-byte records 的二進位檔案，僅讀取 count 個點"""
    with z.open(filename.replace('\\', '/')) as f:
        content = f.read(count * 12)
        records_count = len(content) // 12
        data = []
        for i in range(records_count):
            record = content[i*12 : (i+1)*12]
            # 前 4 bytes 是索引 (Little Endian Unsigned Int)
            # 後 8 bytes 是數值 (Little Endian Double)
            val = struct.unpack('<d', record[4:12])[0]
            data.append(val)
        return data

def convert_cap_to_csv(cap_path, output_path):
    print(f"正在處理: {cap_path}")
    
    with zipfile.ZipFile(cap_path, 'r') as z:
        if 'main.xml' not in z.namelist():
            print(f"錯誤: {cap_path} 中找不到 main.xml")
            return

        with z.open('main.xml') as f:
            xml_content = f.read().decode('utf-8')
            root = ET.fromstring(xml_content)
            
            # 儲存結構: {run_number: {sensor_id: [data]}}
            all_runs = {}
            
            # 找到所有的 DataSource (測量項)
            for source in root.findall('.//DataSource'):
                m_name = source.get('MeasurementName')
                c_id = source.get('ChannelIDName')
                
                # 我們只關心 Normal Force
                if m_name == "Normal Force":
                    euid = source.get('EUID')
                    sensor_label = get_plate_label(euid)
                    
                    # 找到該測量項下的所有 DataSet (代表不同的 Run)
                    for dataset in source.findall('.//DataSet'):
                        group_num = int(dataset.get('DataGroupNumber', 1))
                        
                        # 從 XML 中獲取該數據集的點數
                        storage_elem = dataset.find('.//DataSegmentElement')
                        count = 0
                        if storage_elem is not None:
                            ind_storage = storage_elem.find('.//IndependentStorageElement')
                            if ind_storage is not None:
                                count = int(ind_storage.get('CacheDataCount', 0))

                        storage = dataset.find('.//DependentStorageElement')
                        if storage is not None and count > 0:
                            bin_file = storage.get('FileName')
                            data_points = parse_binary_data(z, bin_file, count)
                            
                            if group_num not in all_runs:
                                all_runs[group_num] = {}
                            all_runs[group_num][sensor_label] = data_points

            # 整理成 DataFrame
            # 需要先確定所有的 Run 編號並排序
            sorted_run_nums = sorted(all_runs.keys())
            
            # 獲取檔案中出現的所有感測器標籤並排序，確保輸出順序穩定
            # 如果是已知感測器會排在前面 (xxx-039, xxx-040)
            all_found_sensors = set()
            for r_data in all_runs.values():
                all_found_sensors.update(r_data.keys())
            
            # 優先權排序: 確保 Plate 01, Plate 02 的順序
            sensor_order = sorted(list(all_found_sensors))
            
            data_to_pad = []
            header = []
            max_len = 0
            
            for run_num in sorted_run_nums:
                for sensor in sensor_order:
                    data = all_runs[run_num].get(sensor, [])
                    data_to_pad.append(data)
                    max_len = max(max_len, len(data))
                    header.append(f"Normal Force, {sensor} (N) Run #{run_num}")

            # 填充數據使其長度一致
            padded_data = {}
            for i, data in enumerate(data_to_pad):
                col_name = header[i]
                padded = data + [np.nan] * (max_len - len(data))
                padded_data[col_name] = padded
            
            df = pd.DataFrame(padded_data)
            
            # 輸出 CSV
            # 參考格式只有 header 有引號，數值沒有。且帶有 UTF-8 BOM。
            df.to_csv(output_path, index=False, float_format='%.2f', quoting=0, encoding='utf-8-sig')
            print(f"已儲存至: {output_path}")

def batch_process(input_dir, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    for file in os.listdir(input_dir):
        if file.endswith('.cap'):
            cap_path = os.path.join(input_dir, file)
            csv_name = file.replace('.cap', '.csv')
            output_path = os.path.join(output_dir, csv_name)
            convert_cap_to_csv(cap_path, output_path)

if __name__ == "__main__":
    batch_process('inputs', 'outputs/force')
