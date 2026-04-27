import zipfile
import xml.etree.ElementTree as ET
import os

def explore_cap(file_path):
    with zipfile.ZipFile(file_path, 'r') as z:
        print("Files in ZIP:")
        for name in z.namelist():
            if not name.startswith('data/'):
                print(name)
        
        # Try to find main.xml or equivalent
        xml_files = [n for n in z.namelist() if n.endswith('.xml')]
        print("\nXML files:", xml_files)
        
        if 'main.xml' in z.namelist():
            with z.open('main.xml') as f:
                content = f.read().decode('utf-8')
                print("\nContent of main.xml (first 1000 chars):")
                print(content[:1000])

if __name__ == "__main__":
    explore_cap('inputs/002.cap')
