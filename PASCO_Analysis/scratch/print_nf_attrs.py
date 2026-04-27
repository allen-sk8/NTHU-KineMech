import zipfile
import re

def print_nf_attrs(file_path):
    with zipfile.ZipFile(file_path, 'r') as z:
        if 'main.xml' in z.namelist():
            with z.open('main.xml') as f:
                content = f.read().decode('utf-8')
                
                # Find all Normal Force DataSources
                matches = re.findall(r'<DataSource[^>]+MeasurementName="Normal Force"[^>]*>', content)
                for m in matches:
                    print(m)

if __name__ == "__main__":
    print_nf_attrs('inputs\\002.cap')
