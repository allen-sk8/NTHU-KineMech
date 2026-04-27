import zipfile
import re

def print_normal_force_block(file_path):
    with zipfile.ZipFile(file_path, 'r') as z:
        if 'main.xml' in z.namelist():
            with z.open('main.xml') as f:
                content = f.read().decode('utf-8')
                
                # Find the Normal Force DataSource
                match = re.search(r'<DataSource[^>]+MeasurementName="Normal Force".*?</DataSource>', content, re.DOTALL)
                if match:
                    print(match.group(0))
                else:
                    print("Normal Force DataSource not found")

if __name__ == "__main__":
    print_normal_force_block('inputs\\002.cap')
