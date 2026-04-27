import zipfile
import xml.etree.ElementTree as ET

def find_context(file_path, filename):
    with zipfile.ZipFile(file_path, 'r') as z:
        if 'main.xml' in z.namelist():
            with z.open('main.xml') as f:
                content = f.read().decode('utf-8')
                root = ET.fromstring(content)
                for elem in root.iter():
                    for attr_name, attr_val in elem.attrib.items():
                        if filename in attr_val:
                            print(f"Tag: {elem.tag}, Attr: {attr_name}, Value: {attr_val}")
                            # Print parent or siblings if possible
                            # ElementTree doesn't have parent links easily, but we can search again
                            pass

if __name__ == "__main__":
    find_context('inputs/002.cap', 'Z_1986c57a6c0_316.tmp')
