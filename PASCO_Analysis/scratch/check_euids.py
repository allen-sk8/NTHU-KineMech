import zipfile
import re

def check_euid(file_path):
    print(f"Checking EUIDs in: {file_path}")
    with zipfile.ZipFile(file_path, 'r') as z:
        content = z.open('main.xml').read().decode('utf-8')
        matches = re.finditer(r'<DataSource[^>]+MeasurementName="Normal Force"[^>]*>', content)
        for i, m in enumerate(matches):
            block = m.group(0)
            euid = re.search(r'EUID="([^"]+)"', block).group(1)
            print(f"NF {i+1}: EUID={euid}")

if __name__ == "__main__":
    check_euid('inputs\\002.cap')
    check_euid('inputs\\022.cap')
