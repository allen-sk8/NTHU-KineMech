import zipfile
import struct

def read_first_val(file_path, binary_name):
    with zipfile.ZipFile(file_path, 'r') as z:
        with z.open(binary_name.replace('\\', '/')) as f:
            data = f.read(12)
            val = struct.unpack('<d', data[4:12])[0]
            return val

if __name__ == "__main__":
    v1 = read_first_val('inputs\\002.cap', 'data\\Z_1986c57fe80_320.tmp')
    v2 = read_first_val('inputs\\002.cap', 'data\\Z_1986c572680_326.tmp')
    print(f"NF 1 Run 1: {v1}")
    print(f"NF 2 Run 1: {v2}")
