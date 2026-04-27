import zipfile
import re

def find_context_lines(file_path, filename):
    with zipfile.ZipFile(file_path, 'r') as z:
        if 'main.xml' in z.namelist():
            with z.open('main.xml') as f:
                content = f.read().decode('utf-8')
                match = re.search(f'.{{0,1000}}{re.escape(filename)}.{{0,1000}}', content, re.DOTALL)
                if match:
                    print(match.group(0))

if __name__ == "__main__":
    find_context_lines('inputs/002.cap', 'Z_1986c57a6c0_316.tmp')
