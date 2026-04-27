import zipfile
import re

def find_xxx_refs(file_path):
    with zipfile.ZipFile(file_path, 'r') as z:
        if 'main.xml' in z.namelist():
            with z.open('main.xml') as f:
                content = f.read().decode('utf-8')
                match = re.search(r'.{0,200}xxx-.{0,200}', content)
                if match:
                    print(match.group(0))

if __name__ == "__main__":
    find_xxx_refs('inputs\\002.cap')
