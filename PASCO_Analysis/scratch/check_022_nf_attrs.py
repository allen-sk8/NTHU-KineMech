import zipfile
import re

def print_nf_attrs(file_path):
    with zipfile.ZipFile(file_path, 'r') as z:
        if 'main.xml' in z.namelist():
            with z.open('main.xml') as f:
                content = f.read().decode('utf-8')
                matches = re.finditer(r'<DataSource[^>]+MeasurementName="Normal Force"[^>]*>', content)
                for i, m in enumerate(matches):
                    print(f"NF {i+1}: {m.group(0)}")

if __name__ == "__main__":
    print_nf_attrs('inputs\\022.cap')
