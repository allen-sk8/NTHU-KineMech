import zipfile
import re

def find_counts(file_path):
    with zipfile.ZipFile(file_path, 'r') as z:
        if 'main.xml' in z.namelist():
            with z.open('main.xml') as f:
                content = f.read().decode('utf-8')
                matches = re.findall(r'CacheDataCount="(\d+)"', content)
                print("CacheDataCounts:", matches)

if __name__ == "__main__":
    find_counts('inputs\\002.cap')
