import zipfile
import struct

def read_binary(file_path, binary_name):
    with zipfile.ZipFile(file_path, 'r') as z:
        if binary_name.replace('\\', '/') in z.namelist():
            with z.open(binary_name.replace('\\', '/')) as f:
                data = f.read(120) # 10 records
                for i in range(0, len(data), 12):
                    record = data[i:i+12]
                    # Unpack 4-byte int and 8-byte double
                    idx = struct.unpack('<I', record[:4])[0]
                    val = struct.unpack('<d', record[4:12])[0]
                    print(f"Index: {idx}, Value: {val}")

if __name__ == "__main__":
    # From previous exploration: data\Z_1986c57a6c0_316.tmp
    read_binary('inputs/002.cap', 'data/Z_1986c57a6c0_316.tmp')
