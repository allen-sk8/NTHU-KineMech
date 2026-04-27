import zipfile
import re

def search_xml(file_path, pattern):
    with zipfile.ZipFile(file_path, 'r') as z:
        content = z.open('main.xml').read().decode('utf-8')
        matches = re.findall(f'.{{0,50}}{pattern}.{{0,50}}', content)
        for m in matches:
            print(m)

if __name__ == "__main__":
    print("Searching for 039/040 in 002.cap:")
    search_xml('inputs\\002.cap', '039|040')
    print("\nSearching for serial-like patterns in 022.cap:")
    # Look for the IDs we found
    search_xml('inputs\\022.cap', '650-003|609-965')
