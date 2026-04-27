import zipfile
import xml.etree.ElementTree as ET

def read_xml(file_path):
    with zipfile.ZipFile(file_path, 'r') as z:
        if 'main.xml' in z.namelist():
            with z.open('main.xml') as f:
                content = f.read().decode('utf-8')
                return content
    return None

if __name__ == "__main__":
    content = read_xml('inputs/002.cap')
    # Look for patterns that link runs to data files
    # Usually <Run> tags or something similar
    print(content[:5000])
