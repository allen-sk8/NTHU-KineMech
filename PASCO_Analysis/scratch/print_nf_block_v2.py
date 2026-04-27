import zipfile
import re

def print_nf_block_full(file_path):
    with zipfile.ZipFile(file_path, 'r') as z:
        if 'main.xml' in z.namelist():
            with z.open('main.xml') as f:
                content = f.read().decode('utf-8')
                match = re.search(r'<DataSource[^>]+MeasurementName="Normal Force".*?</DataSource>', content, re.DOTALL)
                if match:
                    print(match.group(0)[:2000])

if __name__ == "__main__":
    print_nf_block_full('inputs\\002.cap')
