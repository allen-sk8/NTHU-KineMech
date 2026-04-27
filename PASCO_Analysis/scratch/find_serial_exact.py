import zipfile
import re

def find_serial(file_path):
    print(f"\nSearching for identifiers in: {file_path}")
    with zipfile.ZipFile(file_path, 'r') as z:
        content = z.open('main.xml').read().decode('utf-8')
        # Search for any string that looks like a serial number or contains 039/040
        matches = re.findall(r'[^"< ]*039[^"< ]*|[^"< ]*040[^"< ]*', content)
        for m in sorted(list(set(matches))):
            print(f"Match: {m}")

if __name__ == "__main__":
    find_serial('inputs\\002.cap')
