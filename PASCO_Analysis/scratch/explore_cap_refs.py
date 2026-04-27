import zipfile
import xml.etree.ElementTree as ET
import re

def find_data_refs(file_path):
    with zipfile.ZipFile(file_path, 'r') as z:
        if 'main.xml' in z.namelist():
            with z.open('main.xml') as f:
                content = f.read().decode('utf-8')
                
                # Find all occurrences of data/
                refs = re.findall(r'data/[^"< ]+', content)
                print("Data references found:", len(refs))
                for ref in refs[:10]:
                    print(ref)
                
                # Find the tags containing these refs
                root = ET.fromstring(content)
                for elem in root.iter():
                    for attr_name, attr_val in elem.attrib.items():
                        if 'data/' in attr_val:
                            print(f"Tag: {elem.tag}, Attr: {attr_name}, Value: {attr_val}")
                            # Also check parent or related info
                            pass

if __name__ == "__main__":
    find_data_refs('inputs/002.cap')
