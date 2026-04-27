import zipfile
import re

def print_nf_details(file_path):
    with zipfile.ZipFile(file_path, 'r') as z:
        if 'main.xml' in z.namelist():
            with z.open('main.xml') as f:
                content = f.read().decode('utf-8')
                
                # Use a more careful split or regex to find DataSources
                sources = re.findall(r'<DataSource[^>]+MeasurementName="Normal Force"[^>]*>', content)
                for i, s in enumerate(sources):
                    print(f"NF {i+1}: {s}")

if __name__ == "__main__":
    print_nf_details('inputs\\002.cap')
