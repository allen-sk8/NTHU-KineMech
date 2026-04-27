import zipfile
import re

def find_z_refs(file_path):
    with zipfile.ZipFile(file_path, 'r') as z:
        if 'main.xml' in z.namelist():
            with z.open('main.xml') as f:
                content = f.read().decode('utf-8')
                
                # Find all occurrences of Z_
                refs = re.findall(r'Z_[a-f0-9_]+\.tmp', content)
                print("Z_ references found:", len(refs))
                for ref in refs[:10]:
                    print(ref)

if __name__ == "__main__":
    find_z_refs('inputs/002.cap')
