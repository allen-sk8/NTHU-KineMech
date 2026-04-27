import zipfile
import re

def find_sensor_ids(file_path):
    with zipfile.ZipFile(file_path, 'r') as z:
        if 'main.xml' in z.namelist():
            with z.open('main.xml') as f:
                content = f.read().decode('utf-8')
                match39 = re.search(r'.{0,100}039.{0,100}', content)
                match40 = re.search(r'.{0,100}40.{0,100}', content)
                if match39:
                    print(f"039 match: {match39.group(0)}")
                if match40:
                    print(f"040 match: {match40.group(0)}")

if __name__ == "__main__":
    find_sensor_ids('inputs\\002.cap')
