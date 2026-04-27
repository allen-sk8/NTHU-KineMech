import zipfile
import struct

def check_records(file_path, binary_name, count):
    with zipfile.ZipFile(file_path, 'r') as z:
        with z.open(binary_name.replace('\\', '/')) as f:
            f.seek((count - 1) * 12)
            data = f.read(24) # Read 2 records
            for i in range(0, len(data), 12):
                record = data[i:i+12]
                idx = struct.unpack('<I', record[:4])[0]
                val = struct.unpack('<d', record[4:12])[0]
                print(f"Record {count+i//12}: Index={idx}, Value={val}")

if __name__ == "__main__":
    # 002.cap NF 1 Run 1 has 4407 points in reference? No, 4483 lines in CSV?
    # Wait, the CSV has 4484 lines (including header). So 4483 data rows.
    check_records('inputs\\002.cap', 'data\\Z_1986c57fe80_320.tmp', 4483)
